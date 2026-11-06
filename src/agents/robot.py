from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Deque

from mesa import Agent

from src.environment.layout import Coordinate


class RobotState(StrEnum):
    IDLE = "idle"
    TO_RACK = "to_rack"
    TO_STATION = "to_station"
    QUEUED = "queued"
    PICKING = "picking"
    RETURNING_RACK = "returning_rack"
    TO_CHARGER = "to_charger"
    CHARGING = "charging"
    FAILED = "failed"


# Allowed transitions. Anything else is a bug in the control logic and raises.
TRANSITIONS: dict[RobotState, frozenset[RobotState]] = {
    RobotState.IDLE: frozenset(
        {RobotState.TO_RACK, RobotState.TO_CHARGER, RobotState.FAILED}
    ),
    RobotState.TO_RACK: frozenset({RobotState.TO_STATION, RobotState.FAILED}),
    RobotState.TO_STATION: frozenset({RobotState.QUEUED, RobotState.FAILED}),
    RobotState.QUEUED: frozenset({RobotState.PICKING, RobotState.FAILED}),
    RobotState.PICKING: frozenset({RobotState.RETURNING_RACK, RobotState.FAILED}),
    RobotState.RETURNING_RACK: frozenset({RobotState.IDLE, RobotState.FAILED}),
    RobotState.TO_CHARGER: frozenset({RobotState.CHARGING, RobotState.FAILED}),
    RobotState.CHARGING: frozenset({RobotState.IDLE}),
    RobotState.FAILED: frozenset({RobotState.IDLE}),
}

MOVING_STATES = frozenset(
    {
        RobotState.TO_RACK,
        RobotState.TO_STATION,
        RobotState.RETURNING_RACK,
        RobotState.TO_CHARGER,
    }
)


class InvalidTransitionError(RuntimeError):
    """Raised when the control logic requests a transition the robot forbids."""


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
        self.assigned_task_id: str | None = None
        self.carrying_rack_id: str | None = None
        self._route: Deque[Coordinate] = deque()
        self.state = RobotState.IDLE
        self._state_since = float(model.time)
        self._time_in_state: dict[RobotState, float] = {s: 0.0 for s in RobotState}
        self.state_history: list[tuple[float, RobotState]] = [
            (self._state_since, self.state)
        ]

    @property
    def is_available(self) -> bool:
        return self.state is RobotState.IDLE

    def transition(self, new_state: RobotState) -> None:
        """Move to ``new_state`` and account the time spent in the old one."""
        if new_state not in TRANSITIONS[self.state]:
            raise InvalidTransitionError(
                f"Robot {self.robot_id}: {self.state} -> {new_state} is not allowed"
            )
        now = float(self.model.time)
        self._time_in_state[self.state] += now - self._state_since
        self.state = new_state
        self._state_since = now
        self.state_history.append((now, new_state))

    def time_in_state(self) -> dict[RobotState, float]:
        """Seconds spent in each state so far, including the current one."""
        totals = dict(self._time_in_state)
        totals[self.state] += float(self.model.time) - self._state_since
        return totals

    @property
    def route_finished(self) -> bool:
        return not self._route

    @property
    def route(self) -> tuple[Coordinate, ...]:
        return tuple(self._route)

    def assign_task(self, task_id: str, route: tuple[Coordinate, ...]) -> None:
        if not self.is_available:
            raise ValueError(f"Robot {self.robot_id} is already assigned")
        self.assigned_task_id = task_id
        self.set_route(route)
        self.transition(RobotState.TO_RACK)

    def set_route(self, route: tuple[Coordinate, ...]) -> None:
        if route and route[0] == self.pos:
            route = route[1:]
        self._route = deque(route)

    def clear_assignment(self) -> None:
        self.assigned_task_id = None
        self.carrying_rack_id = None
        self._route.clear()

    def step(self) -> None:
        """Drive along the route for one tick.

        Only robots in a moving state drive. Speed is converted to cells with
        ``SimulationConfig``; the fractional part of a cell is carried over to
        the next tick.
        """
        if self.state not in MOVING_STATES or not self._route:
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
