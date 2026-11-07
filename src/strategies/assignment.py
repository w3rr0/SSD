"""Robot-to-task assignment strategies.

The model asks a strategy to pick one robot from the robots that are free
right now. The strategy sees the pick task, the order behind it and the
physical state of every candidate, so rules can trade travel distance against
battery level or a shipment deadline.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.agents.robot import Robot
from src.core.config import AssignmentParams
from src.environment.layout import Coordinate
from src.orders.models import Order, PickTask
from src.pipeline.reservations import natural_key


@dataclass(frozen=True, slots=True)
class AssignmentRequest:
    """Everything a strategy needs to choose a robot for one pick task."""

    task: PickTask
    order: Order
    rack_position: Coordinate
    now: float
    seconds_per_cell: float
    battery_capacity_pct: float
    params: AssignmentParams


AssignmentStrategy = Callable[[AssignmentRequest, Sequence[Robot]], Robot]
"""Return the robot that should serve the task. Must return a candidate."""


def _manhattan(first: Coordinate, second: Coordinate) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def nearest_robot(
    request: AssignmentRequest, robots: Sequence[Robot]
) -> Robot:
    """Default rule: the free robot closest to the rack by grid distance."""
    return min(
        robots,
        key=lambda robot: (
            _manhattan(robot.pos, request.rack_position),
            natural_key(robot.robot_id),
        ),
    )


def deadline_battery_robot(
    request: AssignmentRequest, robots: Sequence[Robot]
) -> Robot:
    """Trade travel time against battery level using the shipment deadline.

    A tight deadline (or an urgent order) makes the rule behave like
    ``nearest_robot``: speed wins and the battery is ignored. When there is
    slack, a robot with a low battery is charged an extra travel time, because
    it may have to break off and charge before the next task. ``due_time``
    being absent means unlimited slack, so battery health dominates.
    """
    if request.order.urgent:
        deadline_pressure = 1.0
    elif request.order.due_time is None:
        deadline_pressure = 0.0
    else:
        slack = request.order.due_time - request.now
        if math.isinf(slack):
            deadline_pressure = 0.0
        else:
            deadline_pressure = min(
                1.0,
                max(0.0, 1.0 - slack / request.params.deadline_horizon_s),
            )

    def score(robot: Robot) -> tuple[float, tuple[int, str, int]]:
        travel_s = (
            _manhattan(robot.pos, request.rack_position)
            * request.seconds_per_cell
        )
        battery_ratio = robot.battery / request.battery_capacity_pct
        battery_penalty_s = (
            (1.0 - battery_ratio)
            * request.params.battery_weight_s
            * (1.0 - deadline_pressure)
        )
        return (travel_s + battery_penalty_s, natural_key(robot.robot_id))

    return min(robots, key=score)


_STRATEGIES: dict[str, AssignmentStrategy] = {
    "nearest": nearest_robot,
    "deadline_battery": deadline_battery_robot,
}


def strategy_for(name: str) -> AssignmentStrategy:
    """Return the assignment strategy registered under ``name``."""
    try:
        return _STRATEGIES[name]
    except KeyError:
        known = ", ".join(sorted(_STRATEGIES))
        raise ValueError(
            f"Unknown assignment strategy {name!r}; choose one of {known}"
        ) from None
