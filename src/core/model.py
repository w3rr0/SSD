from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from mesa import Model
from mesa.space import MultiGrid
from mesa.time import Priority

from src.agents.robot import Robot, RobotConfig, RobotState
from src.agents.warehouse_objects import PickingStation, Rack
from src.core.config import SimulationConfig
from src.environment.layout import Coordinate, WarehouseLayout
from src.metrics.baseline import SimulationMetrics
from src.orders.models import Order, OrderLine, OrderStatus, PickTask, TaskStatus
from src.pipeline.pathfinding import astar_path


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
        layout: WarehouseLayout | None = None,
        robot_configs: Sequence[RobotConfig] | None = None,
        orders: Iterable[Order] | None = None,
        rack_skus: Mapping[str, Iterable[str]] | None = None,
        config: SimulationConfig | None = None,
        rng: int | None = None,
    ):
        super().__init__(rng=rng)
        self.config = config or SimulationConfig()
        self.layout = layout or WarehouseLayout.demo(
            width=width,
            height=height,
            num_robots=num_robots,
        )
        self.grid = MultiGrid(self.layout.width, self.layout.height, torus=False)

        configs = tuple(
            self._default_robot_configs(num_robots)
            if robot_configs is None
            else robot_configs
        )
        self.robots = tuple(Robot(self, config) for config in configs)
        self.robot_by_id = {robot.robot_id: robot for robot in self.robots}
        for robot, config in zip(self.robots, configs, strict=True):
            self.grid.place_agent(robot, config.start)

        if rack_skus is None:
            rack_skus = self._default_rack_skus()
        unknown = set(rack_skus) - set(self.layout.racks)
        if unknown:
            raise ValueError(f"SKUs assigned to unknown racks: {sorted(unknown)}")
        self.racks = {
            rack_id: Rack(self, rack_id, rack_skus.get(rack_id, ()))
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
        for rack_id, rack in self.racks.items():
            self.grid.place_agent(rack, self.layout.racks[rack_id])
        for station_id, station in self.stations.items():
            self.grid.place_agent(station, self.layout.stations[station_id])

        self.orders: list[Order] = []
        self.orders_by_id: dict[str, Order] = {}
        self.released_orders: list[Order] = []
        self._unreleased: list[Order] = []
        self.tasks: list[PickTask] = []
        self.tasks_by_id: dict[str, PickTask] = {}
        for order in self._default_orders() if orders is None else orders:
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

    def _default_orders(self) -> list[Order]:
        if not self.racks or not self.stations:
            return []
        rack = next(iter(self.racks.values()))
        if not rack.skus:
            return []
        return [Order("order-1", (OrderLine(min(rack.skus)),))]

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

        self.running = not self.all_orders_completed

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
        """Cells blocked right now: standing (not carried) racks and stations."""
        standing_racks = {
            rack.pos for rack in self.racks.values() if rack.carried_by is None
        }
        return standing_racks | set(self.layout.stations.values())

    def _route(self, start: Coordinate, goal: Coordinate) -> tuple[Coordinate, ...]:
        return astar_path(self.layout, start, goal, obstacles=self._obstacles())

    def _advance_order_state(self, robot: Robot) -> None:
        """React to a robot that reached the end of its route."""
        if not robot.route_finished:
            return
        if robot.state is RobotState.TO_RACK:
            self._pick_up_rack(robot)
        elif robot.state is RobotState.TO_STATION:
            self._arrive_at_station(robot)

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
        rack = self.racks[task.rack_id]
        rack.carried_by = None
        rack.reserved_by_task = None
        rack.delivered = True
        task.complete(self.time)
        order = self.orders_by_id[task.order_id]
        if order.all_tasks_completed:
            order.complete(self.time)
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
