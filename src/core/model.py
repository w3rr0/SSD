from __future__ import annotations

from collections.abc import Iterable, Sequence

from mesa import Model
from mesa.space import MultiGrid
from mesa.time import Priority

from src.agents.robot import Robot, RobotConfig
from src.agents.warehouse_objects import PickingStation, Rack
from src.core.config import SimulationConfig
from src.environment.layout import Coordinate, WarehouseLayout
from src.metrics.baseline import SimulationMetrics
from src.orders.models import Order, OrderStatus
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

        self.racks = {
            rack_id: Rack(self, rack_id)
            for rack_id in self.layout.racks
        }
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
        self.released_orders.extend(due)

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

    def _default_orders(self) -> list[Order]:
        if not self.layout.racks or not self.layout.stations:
            return []
        rack_id = next(iter(self.layout.racks))
        station_id = next(iter(self.layout.stations))
        return [Order("order-1", rack_id, station_id)]

    def _validate_order(self, order: Order) -> None:
        if order.rack_id not in self.racks:
            raise ValueError(f"Unknown rack in order {order.order_id}: {order.rack_id}")
        if order.station_id not in self.stations:
            raise ValueError(
                f"Unknown station in order {order.order_id}: {order.station_id}"
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
        self._assign_pending_orders()

        for robot in self.robots:
            self._advance_order_state(robot)
            robot.step()
            self._sync_carried_rack(robot)
            self._advance_order_state(robot)

        self.running = not self.all_orders_completed

    def _assign_pending_orders(self) -> None:
        available = [robot for robot in self.robots if robot.is_available]
        busy_racks = {
            order.rack_id
            for order in self.orders
            if order.status is OrderStatus.IN_PROGRESS
        }
        for order in self.released_orders:
            if order.status is not OrderStatus.PENDING or not available:
                continue
            if order.rack_id in busy_racks:
                continue
            rack_position = self.racks[order.rack_id].pos
            robot = min(
                available,
                key=lambda candidate: self._manhattan(candidate.pos, rack_position),
            )
            route = self._route(robot.pos, rack_position)
            order.start(robot.robot_id, self.time)
            robot.assign_order(order.order_id, route)
            available.remove(robot)
            busy_racks.add(order.rack_id)

    def _obstacles(self) -> set[Coordinate]:
        """Cells blocked right now: standing (not carried) racks and stations."""
        standing_racks = {
            rack.pos for rack in self.racks.values() if rack.carried_by is None
        }
        return standing_racks | set(self.layout.stations.values())

    def _route(self, start: Coordinate, goal: Coordinate) -> tuple[Coordinate, ...]:
        return astar_path(self.layout, start, goal, obstacles=self._obstacles())

    def _advance_order_state(self, robot: Robot) -> None:
        if robot.assigned_order_id is None:
            return
        order = self.orders_by_id[robot.assigned_order_id]
        rack = self.racks[order.rack_id]

        if robot.carrying_rack_id is None and robot.pos == rack.pos:
            robot.carrying_rack_id = rack.rack_id
            rack.carried_by = robot.robot_id
            station_position = self.layout.stations[order.station_id]
            robot.set_route(self._route(robot.pos, station_position))
            return

        if robot.carrying_rack_id == rack.rack_id:
            station_position = self.layout.stations[order.station_id]
            if robot.pos == station_position:
                rack.carried_by = None
                rack.delivered = True
                order.complete(self.time)
                robot.clear_assignment()

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
