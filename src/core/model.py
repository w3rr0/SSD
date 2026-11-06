from collections import deque
from collections.abc import Iterable, Mapping, Sequence

from mesa import Model
from mesa.space import MultiGrid
from mesa.time import Priority

from src.agents.robot import MOVING_STATES, Robot, RobotConfig, RobotState
from src.agents.warehouse_objects import Charger, PickingStation, Rack
from src.core.config import SimulationConfig
from src.environment.layout import Coordinate, WarehouseLayout
from src.metrics.baseline import SimulationMetrics
from src.orders.models import Order, OrderLine, OrderStatus, PickTask, TaskStatus
from src.orders.generator import random_orders
from src.pipeline.pathfinding import NoPathError, astar_path
from src.pipeline.reservations import (
    ConflictResolver,
    DeadlockError,
    ReservationTable,
    lowest_id_wins,
    natural_key,
)


class Warehouse(Model):
    """Mesa orchestration layer around replaceable warehouse domain components.

    Time is hybrid (Mesa 3.5 event scheduling):

    * ``self.time`` is the simulation clock in seconds,
    * a recurring tick (Mesa's default ``step`` every ``SimulationConfig.TICK_S``)
      moves robots and assigns work,
    * everything else is a discrete event scheduled with
      ``Model.schedule_event`` at its exact time: order arrivals now, pick
      completion, charging and failures as they are added.

    Use ``step()`` for one tick, ``run_for(seconds)`` / ``run_until(time)`` for
    longer runs.
    """

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        num_robots: int = 1,
        num_orders: int = 1,
        layout: WarehouseLayout | None = None,
        robot_configs: Sequence[RobotConfig] | None = None,
        orders: Iterable[Order] | None = None,
        rack_skus: Mapping[str, Iterable[str]] | None = None,
        config: SimulationConfig | None = None,
        rng: int | None = None,
        resolve_conflict: ConflictResolver = lowest_id_wins,
    ):
        super().__init__(rng=rng)
        self.config = config or SimulationConfig()
        self.layout = layout or WarehouseLayout.demo(
            width=width,
            height=height,
            num_robots=num_robots,
        )
        self.grid = MultiGrid(self.layout.width, self.layout.height, torus=False)
        self.reservations = ReservationTable(
            lookahead=self.config.reservation_lookahead,
            resolve_conflict=resolve_conflict,
        )

        configs = tuple(
            self._default_robot_configs(num_robots)
            if robot_configs is None
            else robot_configs
        )
        self.robots = tuple(Robot(self, config) for config in configs)
        self.robot_by_id = {robot.robot_id: robot for robot in self.robots}
        for robot, config in zip(self.robots, configs, strict=True):
            self.grid.place_agent(robot, config.start)
            self.reservations.try_extend(robot.robot_id, (robot.pos,))

        if rack_skus is None:
            rack_skus = self._default_rack_skus()
        unknown = set(rack_skus) - set(self.layout.racks)
        if unknown:
            raise ValueError(f"SKUs assigned to unknown racks: {sorted(unknown)}")
        self.racks = {
            rack_id: Rack(
                self,
                rack_id,
                home=self.layout.racks[rack_id],
                skus=rack_skus.get(rack_id, ()),
            )
            for rack_id in self.layout.racks
        }
        self.racks_by_sku: dict[str, list[str]] = {}
        for rack_id, rack in self.racks.items():
            for sku in rack.skus:
                self.racks_by_sku.setdefault(sku, []).append(rack_id)
        self.stations = {
            station_id: PickingStation(self, station_id)
            for station_id in self.layout.stations
        }
        self.station_by_position = {
            position: station_id
            for station_id, position in self.layout.stations.items()
        }
        for rack_id, rack in self.racks.items():
            self.grid.place_agent(rack, self.layout.racks[rack_id])
        for station_id, station in self.stations.items():
            self.grid.place_agent(station, self.layout.stations[station_id])
        self.chargers = {
            charger_id: Charger(self, charger_id) for charger_id in self.layout.chargers
        }
        for charger_id, charger in self.chargers.items():
            self.grid.place_agent(charger, self.layout.chargers[charger_id])

        self.orders: list[Order] = []
        self.orders_by_id: dict[str, Order] = {}
        self.released_orders: list[Order] = []
        self._unreleased: list[Order] = []
        self.tasks: list[PickTask] = []
        self.tasks_by_id: dict[str, PickTask] = {}
        self._station_wait_started: dict[str, float] = {}
        self._deadlock_since: float | None = None
        self._deadlock_cycle: frozenset[str] = frozenset()
        self._yield_cycle: frozenset[str] = frozenset()
        self._yield_last_attempt = float("-inf")
        self._progress_since: dict[str, float] = {}
        self._progress_signature: dict[str, tuple[object, ...]] = {}
        if orders is None:
            orders = self._default_orders(num_orders)
        for order in orders:
            self.add_order(order)

    def add_order(self, order: Order) -> None:
        """Register an order; it enters the system at ``order.created_time``.

        The arrival is a discrete event, so orders from the future (e.g. a
        generated stream) stay invisible to robots until their time comes.
        """
        if order.order_id in self.orders_by_id:
            raise ValueError(f"Duplicate order ID: {order.order_id}")
        if order.created_time < self.time:
            raise ValueError(
                f"Order {order.order_id} was created in the past "
                f"({order.created_time} < {self.time})"
            )
        self._validate_order(order)
        self.orders.append(order)
        self.orders_by_id[order.order_id] = order
        self._unreleased.append(order)
        self.schedule_event(
            self._release_due_orders,
            at=order.created_time,
            priority=Priority.HIGH,
        )

    def _release_due_orders(self) -> None:
        due = [o for o in self._unreleased if o.created_time <= self.time]
        if not due:
            return
        self._unreleased = [o for o in self._unreleased if o.created_time > self.time]
        due.sort(key=lambda order: order.created_time)
        for order in due:
            self._plan_tasks(order)
        self.released_orders.extend(due)

    def _plan_tasks(self, order: Order) -> None:
        """Split an order into pick tasks, one per rack it needs.

        Greedy set cover: repeatedly take the rack holding the most remaining
        lines (ties: closer to the station, then rack ID).
        """
        station_id = order.station_id or self._choose_station()
        order.station_id = station_id
        station_position = self.layout.stations[station_id]
        remaining = {line.sku: line for line in order.lines}
        while remaining:
            candidates = {
                rack_id
                for sku in remaining
                for rack_id in self.racks_by_sku[sku]
            }
            rack_id = min(
                candidates,
                key=lambda rid: (
                    -len(self.racks[rid].skus & remaining.keys()),
                    self._manhattan(self.racks[rid].pos, station_position),
                    rid,
                ),
            )
            covered = self.racks[rack_id].skus & remaining.keys()
            lines = tuple(remaining.pop(sku) for sku in sorted(covered))
            task = PickTask(
                task_id=f"{order.order_id}/{len(order.tasks) + 1}",
                order_id=order.order_id,
                rack_id=rack_id,
                station_id=station_id,
                lines=lines,
                created_time=self.time,
            )
            order.tasks.append(task)
            self.tasks.append(task)
            self.tasks_by_id[task.task_id] = task

    def _choose_station(self) -> str:
        """Station with the fewest unfinished tasks (ties: station ID)."""
        open_tasks = {station_id: 0 for station_id in self.stations}
        for task in self.tasks:
            if task.status is not TaskStatus.COMPLETED:
                open_tasks[task.station_id] += 1
        return min(open_tasks, key=lambda sid: (open_tasks[sid], sid))

    def _default_robot_configs(self, num_robots: int) -> tuple[RobotConfig, ...]:
        if num_robots <= 0:
            raise ValueError("num_robots must be positive")
        starts = list(self.layout.robot_starts.items())
        if len(starts) < num_robots:
            raise ValueError("Layout does not define enough robot start positions")
        return tuple(
            RobotConfig(robot_id=robot_id, start=position)
            for robot_id, position in starts[:num_robots]
        )

    def _default_rack_skus(self) -> dict[str, frozenset[str]]:
        """One product per rack: ``rack-7`` holds ``sku-7``."""
        return {
            rack_id: frozenset({"sku-" + rack_id.removeprefix("rack-")})
            for rack_id in self.layout.racks
        }

    def _default_orders(self, num_orders: int) -> list[Order]:
        """One order for the first SKU, or a random stream for the demo."""
        if not self.stations or not self.racks_by_sku or num_orders <= 0:
            return []
        if num_orders == 1:
            first_rack = next(iter(self.racks.values()))
            sku = min(first_rack.skus) if first_rack.skus else min(self.racks_by_sku)
            return [Order("order-1", (OrderLine(sku),))]
        return random_orders(
            self.rng,
            skus=sorted(self.racks_by_sku),
            count=num_orders,
            mean_interarrival_s=30.0,
        )

    def _validate_order(self, order: Order) -> None:
        if order.station_id is not None and order.station_id not in self.stations:
            raise ValueError(
                f"Unknown station in order {order.order_id}: {order.station_id}"
            )
        if not self.stations:
            raise ValueError("The layout has no picking stations")
        missing = sorted(sku for sku in order.skus if sku not in self.racks_by_sku)
        if missing:
            raise ValueError(
                f"Order {order.order_id} needs SKUs stored on no rack: {missing}"
            )

    @property
    def all_orders_completed(self) -> bool:
        return not self._unreleased and all(
            order.status is OrderStatus.COMPLETED for order in self.orders
        )

    def step(self) -> None:
        """One movement tick (called by Mesa every ``TICK_S`` seconds)."""
        # Orders due at this exact time may be scheduled after the tick event.
        self._release_due_orders()
        self._assign_pending_tasks()

        for robot in self.robots:
            self._advance_order_state(robot)
            robot.step()
            self._sync_carried_rack(robot)
            self._advance_order_state(robot)
            self._track_progress(robot)

        self._record_station_waits()
        self._clear_idle_blockers()
        self._check_deadlock()
        self.running = not self.all_orders_completed

    def reset_reservation(self, robot: Robot) -> None:
        """Replace the robot's reservation window with its current route."""
        self.reservations.release_all(robot.robot_id)
        self.reservations.try_extend(
            robot.robot_id, (robot.pos, *robot.route)
        )

    def extend_reservation(self, robot: Robot, *, preempt: bool = False) -> None:
        """Top up the robot's reservation window along its remaining route.

        A robot following another robot in the same direction switches to the
        short follow window, so a convoy keeps a one-cell headway instead of
        leaving the full lookahead gap empty. The far end of the previous,
        longer window is released to make that switch effective.
        """
        if not preempt and self._follows_same_direction(robot):
            limit = self.config.follow_lookahead + 1
            self.reservations.trim(robot.robot_id, limit)
            self.reservations.try_extend(
                robot.robot_id,
                (robot.pos, *robot.route),
                max_window=limit,
            )
            return
        self.reservations.try_extend(
            robot.robot_id,
            (robot.pos, *robot.route),
            preempt=preempt,
        )

    def _follows_same_direction(self, robot: Robot) -> bool:
        """Whether ``robot`` is queueing behind a robot heading the same way.

        The first cell of the route held by another robot gives the candidate
        leader. The follower joins the convoy when its remaining route
        continues along the leader's own path for at least two cells, or when
        it is the station cell the leader is currently being served at.
        """
        route = robot.route
        for index, cell in enumerate(route):
            holder_id = self.reservations.owner(cell)
            if holder_id is None or holder_id == robot.robot_id:
                continue
            if index > self.config.reservation_lookahead:
                # The leader is too far ahead to constrain the full window;
                # there is nothing to give back yet.
                return False
            leader = self.robot_by_id.get(holder_id)
            if leader is None or leader.yielding:
                return False
            return self._same_corridor(route[index:], leader) or (
                self._same_station_goal(robot, cell, leader)
            )
        return False

    @staticmethod
    def _same_corridor(tail: tuple[Coordinate, ...], leader: Robot) -> bool:
        """Whether ``tail`` continues along the leader's path for 2+ cells."""
        if leader.state not in MOVING_STATES:
            return False
        leader_path = (leader.pos, *leader.route)
        try:
            index = leader_path.index(tail[0])
        except ValueError:
            return False
        shared = min(len(tail), len(leader_path) - index)
        if shared < 2:
            return False
        return tail[:shared] == leader_path[index : index + shared]

    def _same_station_goal(
        self, robot: Robot, cell: Coordinate, leader: Robot
    ) -> bool:
        """Whether both robots wait for the same station cell, one after one."""
        if robot.state is not RobotState.TO_STATION:
            return False
        if leader.state not in (RobotState.QUEUED, RobotState.PICKING):
            return False
        task = self._task_of(robot)
        leader_task = self._task_of(leader)
        if task is None or leader_task is None:
            return False
        if task.station_id != leader_task.station_id:
            return False
        return cell == self.layout.stations[task.station_id]

    def _task_of(self, robot: Robot) -> PickTask | None:
        if robot.assigned_task_id is None:
            return None
        return self.tasks_by_id.get(robot.assigned_task_id)

    def _record_station_waits(self) -> None:
        """Start the station queue clock when a robot first waits for it.

        A robot may wait in front of the station cell, or behind another robot
        already waiting for the same station. Both cases count as queue time.
        """
        for robot in self.robots:
            if robot.yielding:
                continue
            if robot.robot_id in self._station_wait_started:
                continue
            if not robot.blocked or robot.blocked_cell is None:
                continue
            station_id = self.station_by_position.get(robot.blocked_cell)
            if station_id is None:
                continue
            task = self._task_of(robot)
            if task is None or task.station_id != station_id:
                continue
            self._station_wait_started[robot.robot_id] = float(self.time)

        changed = True
        while changed:
            changed = False
            for robot in self.robots:
                if robot.yielding:
                    continue
                if robot.robot_id in self._station_wait_started:
                    continue
                if not robot.blocked or robot.blocked_by is None:
                    continue
                holder = self.robot_by_id.get(robot.blocked_by)
                if holder is None:
                    continue
                if holder.robot_id not in self._station_wait_started:
                    continue
                robot_task = self._task_of(robot)
                holder_task = self._task_of(holder)
                if robot_task is None or holder_task is None:
                    continue
                if robot_task.station_id != holder_task.station_id:
                    continue
                self._station_wait_started[robot.robot_id] = float(self.time)
                changed = True

    def _clear_idle_blockers(self) -> None:
        """Ask an idle robot to step aside when it blocks a working one.

        Robots are parked on their start cells until the first order reaches
        the station. Without this, a parked robot in a one-cell aisle makes a
        working robot wait for an order that may be minutes away. The idle
        robot is sent to the nearest cell off every working robot's route and
        simply stays there when the detour ends.
        """
        for robot in self.robots:
            if not robot.blocked or robot.blocked_by is None:
                continue
            blocker = self.robot_by_id.get(robot.blocked_by)
            if blocker is None or blocker.assigned_task_id is not None:
                continue
            if blocker.state is not RobotState.IDLE or blocker.route:
                continue
            route = self._yield_path(blocker)
            if route is None:
                continue
            blocker.set_route(route)
            blocker.yielding = True
            blocker.yield_parked_at = None
            blocker.yield_wait_since = None

    def _check_deadlock(self) -> None:
        """Break a waiting cycle by yielding, or raise after the timeout.

        Opposite-direction traffic in a one-cell aisle can form a cycle. The
        lowest-priority robot of the cycle is moved to the nearest free cell
        off the other robot's route; it resumes its task afterwards. If no
        such cell exists, the cycle is reported instead of hanging forever.
        """
        waits = {
            robot.robot_id: robot.blocked_by
            for robot in self.robots
            if robot.blocked and robot.blocked_by is not None
        }
        cycle = self._find_deadlock_cycle(waits)
        if cycle is None:
            self._deadlock_since = None
            self._deadlock_cycle = frozenset()
            self._yield_cycle = frozenset()
            self._yield_last_attempt = float("-inf")
            return
        if cycle != self._deadlock_cycle:
            self._deadlock_cycle = cycle
            self._deadlock_since = float(self.time)
        retry_s = max(2.0, self.config.deadlock_timeout_s / 10)
        if (
            cycle != self._yield_cycle
            or float(self.time) - self._yield_last_attempt >= retry_s
        ):
            if self._start_yield(cycle):
                self._yield_cycle = cycle
            self._yield_last_attempt = float(self.time)
        if self._deadlock_since is None:
            self._deadlock_since = float(self.time)
            return
        waited = float(self.time) - self._deadlock_since
        if waited >= self.config.deadlock_timeout_s:
            raise DeadlockError(
                "Robots are waiting for each other in a cycle: "
                + ", ".join(sorted(cycle, key=natural_key))
            )

    def _start_yield(self, cycle: frozenset[str]) -> bool:
        """Send the lowest-priority robot of ``cycle`` to a free side cell."""
        candidates = [
            self.robot_by_id[robot_id]
            for robot_id in cycle
            if robot_id in self.robot_by_id
            and not self.robot_by_id[robot_id].yielding
        ]
        candidates.sort(key=lambda robot: natural_key(robot.robot_id), reverse=True)
        for robot in candidates:
            route = self._yield_path(robot)
            if route is None:
                continue
            robot.set_route(route)
            robot.yielding = True
            robot.yield_parked_at = None
            robot.yield_wait_since = None
            return True
        return False

    def _yield_path(self, robot: Robot) -> tuple[Coordinate, ...] | None:
        """Nearest path to a free cell that is off every other robot's route.

        The path may follow reserved or planned cells while moving away from
        them; only the stop cell must be clear, so the yielding robot does
        not park in the way of somebody else. Waiting robots keep their
        routes, so planned routes are the best available proxy for traffic.
        """
        blocked = (
            self._obstacles()
            | set(self.layout.blocked)
            | {
                cell
                for other in self.robots
                if other.robot_id != robot.robot_id
                for cell in self.reservations.window(other.robot_id)
            }
        )
        traffic = {
            cell
            for other in self.robots
            if other.robot_id != robot.robot_id
            for cell in other.route
        }

        start = robot.pos
        parents: dict[Coordinate, Coordinate | None] = {start: None}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            if cell != start and cell not in blocked and cell not in traffic:
                path: list[Coordinate] = []
                current: Coordinate | None = cell
                while current is not None:
                    path.append(current)
                    current = parents[current]
                return tuple(reversed(path))
            for neighbor in self.layout.neighbors(cell):
                if neighbor in parents or neighbor in blocked:
                    continue
                parents[neighbor] = cell
                queue.append(neighbor)
        return None

    def _finish_yield(self, robot: Robot) -> None:
        """Resume the original task after the robot reaches its yield cell.

        A yielding robot stays parked for at least one tick, then keeps
        waiting while the first cell of its way back is reserved by another
        robot. That gives the robot it made room for a chance to claim the
        corridor first; otherwise both robots would bounce back and forth.

        The new route itself ignores reservations beyond that first step: it
        is only a plan, and the normal movement gate decides when the robot
        may enter each cell.
        """
        if robot.yield_parked_at is None:
            robot.yield_parked_at = float(self.time)
            return
        if float(self.time) <= robot.yield_parked_at:
            return
        goal = self._goal_for(robot)
        if goal is None:
            robot.yielding = False
            robot.yield_parked_at = None
            return
        holder = self.reservations.owner(goal)
        if holder not in (None, robot.robot_id):
            holder_robot = self.robot_by_id.get(holder)
            if (
                holder_robot is not None
                and holder_robot.blocked_by == robot.robot_id
            ):
                # The robot we made room for is now stuck behind us. Move
                # further away instead of waiting for a cell that cannot free
                # itself while we stand here.
                away = self._yield_path(robot)
                if away is not None:
                    robot.set_route(away)
                    robot.yield_parked_at = None
                    robot.yield_wait_since = None
                    return
            self._mark_waiting(robot, holder, goal)
            return
        try:
            route = astar_path(
                self.layout, robot.pos, goal, obstacles=self._obstacles()
            )
        except NoPathError:
            return
        if len(route) > 1:
            next_holder = self.reservations.owner(route[1])
            if next_holder not in (None, robot.robot_id):
                if robot.yield_wait_since is None:
                    robot.yield_wait_since = float(self.time)
                    self._mark_waiting(robot, next_holder, route[1])
                    return
                retry_s = max(2.0, self.config.deadlock_timeout_s / 10)
                if float(self.time) - robot.yield_wait_since < retry_s:
                    self._mark_waiting(robot, next_holder, route[1])
                    return
        robot.blocked = False
        robot.blocked_cell = None
        robot.blocked_by = None
        robot.yielding = False
        robot.yield_parked_at = None
        robot.yield_wait_since = None
        robot.set_route(route)

    @staticmethod
    def _mark_waiting(robot: Robot, holder_id: str, cell: Coordinate) -> None:
        """Record a parked robot's blocker so cycle detection can see it."""
        robot.blocked = True
        robot.blocked_cell = cell
        robot.blocked_by = holder_id

    def _goal_for(self, robot: Robot) -> Coordinate | None:
        task = self._task_of(robot)
        if task is None:
            return None
        if robot.state is RobotState.TO_RACK:
            return self.racks[task.rack_id].pos
        if robot.state is RobotState.TO_STATION:
            return self.layout.stations[task.station_id]
        if robot.state is RobotState.RETURNING_RACK:
            if robot.carrying_rack_id is None:
                return None
            return self.return_location(self.racks[robot.carrying_rack_id])
        return None

    def _track_progress(self, robot: Robot) -> None:
        """Report a robot that cannot move for the whole deadlock timeout.

        A robot in a moving state with a planned route should make progress:
        either its position or the length of its remaining route changes.
        Waiting in a station queue is not a stall; those robots are in the
        ``QUEUED`` state and are ignored here. The timeout catches liveness
        bugs that are not simple cycles, such as a robot parked on the only
        way out of a corridor while nobody is formally blocking it.
        """
        moving = robot.state in MOVING_STATES and bool(robot.route)
        if not moving:
            self._progress_since.pop(robot.robot_id, None)
            self._progress_signature.pop(robot.robot_id, None)
            return
        signature: tuple[object, ...] = (
            robot.pos,
            len(robot.route),
            robot.yielding,
        )
        if self._progress_signature.get(robot.robot_id) != signature:
            self._progress_signature[robot.robot_id] = signature
            self._progress_since[robot.robot_id] = float(self.time)
            return
        since = self._progress_since.get(robot.robot_id, float(self.time))
        if float(self.time) - since >= self.config.deadlock_timeout_s:
            raise DeadlockError(
                f"{robot.robot_id} made no progress for "
                f"{self.config.deadlock_timeout_s:.0f} s at {robot.pos}"
            )

    @staticmethod
    def _find_deadlock_cycle(
        waits: Mapping[str, str],
    ) -> frozenset[str] | None:
        for start in waits:
            path: list[str] = []
            index_by_robot: dict[str, int] = {}
            current = start
            while current in waits:
                if current in index_by_robot:
                    return frozenset(path[index_by_robot[current] :])
                index_by_robot[current] = len(path)
                path.append(current)
                current = waits[current]
        return None

    def _assign_pending_tasks(self) -> None:
        """Nearest free robot for each waiting task, oldest order first."""
        available = [robot for robot in self.robots if robot.is_available]
        for order in self.released_orders:
            if not available:
                return
            if order.status is OrderStatus.COMPLETED:
                continue
            for task in order.tasks:
                if not available:
                    return
                if task.status is not TaskStatus.PENDING:
                    continue
                rack = self.racks[task.rack_id]
                if not rack.is_free:
                    continue
                robot = min(
                    available,
                    key=lambda candidate: (
                        self._manhattan(candidate.pos, rack.pos),
                        candidate.robot_id,
                    ),
                )
                route = self._route(robot.pos, rack.pos)
                task.start(robot.robot_id, self.time)
                order.start(self.time)
                rack.reserved_by_task = task.task_id
                robot.assign_task(task.task_id, route)
                available.remove(robot)

    def _obstacles(self) -> set[Coordinate]:
        """Cells blocked right now: standing racks, stations and chargers."""
        standing_racks = {
            rack.pos for rack in self.racks.values() if rack.carried_by is None
        }
        return (
            standing_racks
            | set(self.layout.stations.values())
            | set(self.layout.chargers.values())
        )

    def _route(self, start: Coordinate, goal: Coordinate) -> tuple[Coordinate, ...]:
        return astar_path(self.layout, start, goal, obstacles=self._obstacles())

    def _advance_order_state(self, robot: Robot) -> None:
        """React to a robot that reached the end of its route."""
        if not robot.route_finished:
            return
        if robot.yielding:
            self._finish_yield(robot)
            return
        if robot.state is RobotState.TO_RACK:
            self._pick_up_rack(robot)
        elif robot.state is RobotState.TO_STATION:
            self._arrive_at_station(robot)
        elif robot.state is RobotState.RETURNING_RACK:
            self._put_down_rack(robot)

    def _pick_up_rack(self, robot: Robot) -> None:
        task = self.tasks_by_id[robot.assigned_task_id]
        rack = self.racks[task.rack_id]
        if robot.pos != rack.pos:
            raise RuntimeError(f"Robot {robot.robot_id} is not under {rack.rack_id}")
        robot.carrying_rack_id = rack.rack_id
        rack.carried_by = robot.robot_id
        station_position = self.layout.stations[task.station_id]
        robot.set_route(self._route(robot.pos, station_position))
        robot.transition(RobotState.TO_STATION)

    def _arrive_at_station(self, robot: Robot) -> None:
        task = self.tasks_by_id[robot.assigned_task_id]
        waiting_since = self._station_wait_started.pop(robot.robot_id, None)
        self.stations[task.station_id].enqueue(
            robot, waiting_since=waiting_since
        )

    def pick_duration(self, robot: Robot) -> float:
        """Service time of the rack visit ``robot`` is bringing."""
        task = self.tasks_by_id[robot.assigned_task_id]
        return self.config.picking.sample(task.items, self.rng)

    def on_pick_finished(self, robot: Robot, station: PickingStation) -> None:
        """Event handler: the picker finished with the rack ``robot`` holds."""
        task = self.tasks_by_id[robot.assigned_task_id]
        task.complete(self.time)
        order = self.orders_by_id[task.order_id]
        if order.all_tasks_completed:
            order.complete(self.time)
        rack = self.racks[task.rack_id]
        rack.trips += 1
        robot.set_route(self._route(robot.pos, self.return_location(rack)))
        robot.transition(RobotState.RETURNING_RACK)

    def return_location(self, rack: Rack) -> Coordinate:
        """Where a rack goes after picking.

        For now every rack returns to its home slot; placement strategies
        (e.g. nearest free slot by the station, P4) will override this.
        """
        return rack.home

    def _put_down_rack(self, robot: Robot) -> None:
        rack = self.racks[robot.carrying_rack_id]
        rack.carried_by = None
        rack.reserved_by_task = None
        robot.clear_assignment()
        robot.transition(RobotState.IDLE)

    def _sync_carried_rack(self, robot: Robot) -> None:
        if robot.carrying_rack_id is None:
            return
        rack = self.racks[robot.carrying_rack_id]
        self.grid.move_agent(rack, robot.pos)

    @staticmethod
    def _manhattan(first: Coordinate, second: Coordinate) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])

    @property
    def metrics(self) -> SimulationMetrics:
        return SimulationMetrics.from_orders(
            self.orders,
            total_distance_m=sum(robot.distance_travelled_m for robot in self.robots),
            simulated_time=self.time,
            station_utilisation={
                station_id: station.utilisation()
                for station_id, station in self.stations.items()
            },
            station_wait_times=[
                wait
                for station in self.stations.values()
                for wait in station.wait_times
            ],
        )

    def run_until_complete(self, max_time: float = 36_000.0) -> SimulationMetrics:
        """Run until every order is completed or ``max_time`` seconds pass."""
        while self.time < max_time:
            if self.all_orders_completed:
                return self.metrics
            self.step()
        if self.all_orders_completed:
            return self.metrics
        raise TimeoutError(
            f"Warehouse did not complete all orders within {max_time} s"
        )
