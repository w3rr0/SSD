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
    # A repaired robot resumes the state it had when it failed. Only states
    # that can be interrupted are listed; picking, queueing and charging are
    # atomic from the model's point of view and are never failed mid-way.
    RobotState.FAILED: frozenset(
        {
            RobotState.IDLE,
            RobotState.TO_RACK,
            RobotState.TO_STATION,
            RobotState.RETURNING_RACK,
            RobotState.TO_CHARGER,
        }
    ),
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
        self.return_distance_m = 0.0
        self.traffic_wait_s = 0.0
        self._move_progress = 0.0
        self.assigned_task_id: str | None = None
        self.carrying_rack_id: str | None = None
        self.charger_id: str | None = None
        self._route: Deque[Coordinate] = deque()
        self.blocked = False
        self.blocked_cell: Coordinate | None = None
        self.blocked_by: str | None = None
        self.yielding = False
        self.yield_parked_at: float | None = None
        self.yield_wait_since: float | None = None
        self._pre_failure_state: RobotState | None = None
        self._pre_failure_route: tuple[Coordinate, ...] = ()
        self._pre_failure_yielding = False
        self._pre_failure_yield_parked_at: float | None = None
        self._pre_failure_yield_wait_since: float | None = None
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
        self.yielding = False
        self.yield_parked_at = None
        self.yield_wait_since = None
        self.set_route(route)
        self.transition(RobotState.TO_RACK)

    def set_route(self, route: tuple[Coordinate, ...]) -> None:
        if route and route[0] == self.pos:
            route = route[1:]
        self._route = deque(route)
        self.model.reset_reservation(self)

    def assign_charger(self, charger_id: str, route: tuple[Coordinate, ...]) -> None:
        """Leave for ``charger_id``; the charger must already be reserved."""
        if not self.is_available:
            raise ValueError(f"Robot {self.robot_id} is already assigned")
        self.charger_id = charger_id
        self.yielding = False
        self.yield_parked_at = None
        self.yield_wait_since = None
        self.set_route(route)
        self.transition(RobotState.TO_CHARGER)

    def finish_charging(self) -> None:
        """End the charge and become available for work again."""
        self.charger_id = None
        self._route.clear()
        self.model.reset_reservation(self)
        self.transition(RobotState.IDLE)

    def clear_assignment(self) -> None:
        self.assigned_task_id = None
        self.carrying_rack_id = None
        self.yielding = False
        self.yield_parked_at = None
        self.yield_wait_since = None
        self._route.clear()
        self.model.reset_reservation(self)

    @property
    def can_fail(self) -> bool:
        """Whether a failure may interrupt the robot right now.

        Picking, queueing and charging are atomic from the model's point of
        view: their completion events would not know how to resume a failed
        robot, so failures wait until the robot is moving or idle again.
        """
        return self.state in {
            RobotState.IDLE,
            RobotState.TO_RACK,
            RobotState.TO_STATION,
            RobotState.RETURNING_RACK,
            RobotState.TO_CHARGER,
        }

    def on_failure_event(self) -> None:
        """Mesa event handler: ask the model to fail this robot."""
        self.model.handle_failure(self)

    def on_repair_event(self) -> None:
        """Mesa event handler: the repair is complete."""
        self.model.handle_repair(self)

    def fail(self) -> None:
        """Stop the robot and remember what it was doing.

        The current cell stays reserved so other robots do not drive into a
        stopped robot. The route is dropped; ``repair`` restores it.
        """
        if self.state is RobotState.FAILED:
            return
        self._pre_failure_state = self.state
        self._pre_failure_route = self.route
        self._pre_failure_yielding = self.yielding
        self._pre_failure_yield_parked_at = self.yield_parked_at
        self._pre_failure_yield_wait_since = self.yield_wait_since
        self.yielding = False
        self.yield_parked_at = None
        self.yield_wait_since = None
        self.blocked = False
        self.blocked_cell = None
        self.blocked_by = None
        self.set_route(())
        self.transition(RobotState.FAILED)

    def repair(self) -> None:
        """Return to the state and route the robot had before the failure."""
        if self.state is not RobotState.FAILED:
            return
        state = self._pre_failure_state or RobotState.IDLE
        route = self._pre_failure_route
        self.yielding = self._pre_failure_yielding
        self.yield_parked_at = self._pre_failure_yield_parked_at
        self.yield_wait_since = self._pre_failure_yield_wait_since
        self._pre_failure_state = None
        self._pre_failure_route = ()
        self._pre_failure_yielding = False
        self._pre_failure_yield_parked_at = None
        self._pre_failure_yield_wait_since = None
        self.transition(state)
        self.set_route(route)

    def step(self) -> None:
        """Drive along the route for one tick.

        Only robots in a moving state drive. Speed is converted to cells with
        ``SimulationConfig``; the fractional part of a cell is carried over to
        the next tick.

        A robot may only enter a cell reserved for it. When the next cell is
        held by another robot, the robot stops for this tick and records the
        blocker, so the model can report a deadlock instead of hanging.
        """
        self.blocked = False
        self.blocked_cell = None
        self.blocked_by = None
        driving = self.state in MOVING_STATES or (
            self.state is RobotState.IDLE and self.yielding
        )
        if not driving or not self._route:
            self._move_progress = 0.0
            return
        config = self.model.config
        self._move_progress += config.cells_per_tick
        while self._route and self._move_progress >= 1.0:
            next_position = self._route[0]
            self.model.extend_reservation(self)
            if not self.model.reservations.is_reserved_by(
                self.robot_id, next_position
            ):
                conflict = self.model.reservations.conflict(
                    self.robot_id, next_position
                )
                if (
                    conflict is not None
                    and self.model.reservations.resolve(
                        self.robot_id, conflict.holder_id
                    )
                    == self.robot_id
                ):
                    self.model.extend_reservation(self, preempt=True)
                if not self.model.reservations.is_reserved_by(
                    self.robot_id, next_position
                ):
                    self.blocked = True
                    self.blocked_cell = next_position
                    self.blocked_by = self.model.reservations.owner(
                        next_position
                    )
                    self._move_progress = 0.0
                    return
            old_position = self.pos
            self._route.popleft()
            self.model.grid.move_agent(self, next_position)
            self.model.reservations.release_passed(
                self.robot_id, old_position
            )
            self._move_progress -= 1.0
            self.distance_travelled_m += config.cell_size_m
            if self.state is RobotState.RETURNING_RACK:
                self.return_distance_m += config.cell_size_m
            self.battery = max(
                0.0,
                self.battery
                - config.robot.battery_drain_pct_per_m * config.cell_size_m,
            )
        if not self._route:
            self._move_progress = 0.0
