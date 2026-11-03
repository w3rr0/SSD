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
        self.distance_travelled = 0
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
        if not self._route:
            return
        next_position = self._route.popleft()
        self.model.grid.move_agent(self, next_position)
        self.distance_travelled += 1
        self.battery = max(0.0, self.battery - 1.0)
