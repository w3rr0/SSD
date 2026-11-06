from __future__ import annotations

from collections.abc import Iterable, Sequence

from mesa import Model
from mesa.space import MultiGrid

from src.agents.robot import Robot, RobotConfig
from src.agents.warehouse_objects import PickingStation, Rack
from src.core.config import SimulationConfig
from src.environment.layout import Coordinate, WarehouseLayout
from src.metrics.baseline import SimulationMetrics
from src.orders.models import Order, OrderStatus
from src.pipeline.pathfinding import astar_path


class Warehouse(Model):
    """Mesa orchestration layer around replaceable warehouse domain components.

    ``self.time`` is the simulation clock in seconds; every ``step()`` advances
    it by ``SimulationConfig.TICK_S``.
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

        self.orders = list(self._default_orders() if orders is None else orders)
        self.orders_by_id = {order.order_id: order for order in self.orders}
        if len(self.orders_by_id) != len(self.orders):
            raise ValueError("Order IDs must be unique")
        self._validate_orders()

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

    def _validate_orders(self) -> None:
        for order in self.orders:
            if order.rack_id not in self.racks:
                raise ValueError(f"Unknown rack in order {order.order_id}: {order.rack_id}")
            if order.station_id not in self.stations:
                raise ValueError(
                    f"Unknown station in order {order.order_id}: {order.station_id}"
                )

    def step(self) -> None:
        self._assign_pending_orders()

        for robot in self.robots:
            self._advance_order_state(robot)
            robot.step()
            self._sync_carried_rack(robot)
            self._advance_order_state(robot)

    def _assign_pending_orders(self) -> None:
        available = [robot for robot in self.robots if robot.is_available]
        busy_racks = {
            order.rack_id
            for order in self.orders
            if order.status is OrderStatus.IN_PROGRESS
        }
        for order in self.orders:
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
            if all(order.status is OrderStatus.COMPLETED for order in self.orders):
                return self.metrics
            self.step()
        if all(order.status is OrderStatus.COMPLETED for order in self.orders):
            return self.metrics
        raise TimeoutError(
            f"Warehouse did not complete all orders within {max_time} s"
        )
