from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque

from mesa import Agent

from src.environment.layout import Coordinate


@dataclass(frozen=True, slots=True)
class RobotConfig:
    robot_id: str
    start: Coordinate
    battery: float = 100.0


class Robot(Agent):
    def __init__(self, model, config: RobotConfig):
        super().__init__(model)
        self.robot_id = config.robot_id
        self.battery = config.battery
        self.distance_travelled_m = 0.0
        self._move_progress = 0.0
        self.assigned_order_id: str | None = None
        self.carrying_rack_id: str | None = None
        self._route: Deque[Coordinate] = deque()

    @property
    def is_available(self) -> bool:
        return self.assigned_order_id is None

    @property
    def route(self) -> tuple[Coordinate, ...]:
        return tuple(self._route)

    def assign_order(self, order_id: str, route: tuple[Coordinate, ...]) -> None:
        if not self.is_available:
            raise ValueError(f"Robot {self.robot_id} is already assigned")
        self.assigned_order_id = order_id
        self.set_route(route)

    def set_route(self, route: tuple[Coordinate, ...]) -> None:
        if route and route[0] == self.pos:
            route = route[1:]
        self._route = deque(route)

    def clear_assignment(self) -> None:
        self.assigned_order_id = None
        self.carrying_rack_id = None
        self._route.clear()

    def step(self) -> None:
        """Drive along the route for one tick.

        Speed is converted to cells with ``SimulationConfig``; the fractional
        part of a cell is carried over to the next tick.
        """
        if not self._route:
            self._move_progress = 0.0
            return
        config = self.model.config
        self._move_progress += config.cells_per_tick
        while self._route and self._move_progress >= 1.0:
            next_position = self._route.popleft()
            self.model.grid.move_agent(self, next_position)
            self._move_progress -= 1.0
            self.distance_travelled_m += config.cell_size_m
            self.battery = max(
                0.0,
                self.battery
                - config.robot.battery_drain_pct_per_m * config.cell_size_m,
            )
        if not self._route:
            self._move_progress = 0.0
