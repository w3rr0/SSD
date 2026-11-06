from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from src.core.config import SECONDS_PER_HOUR
from src.orders.models import Order


@dataclass(frozen=True, slots=True)
class SimulationMetrics:
    """Summary of a run. Times are in seconds, distances in metres."""

    completed_orders: int
    average_completion_time: float | None
    longest_completion_time: float | None
    average_waiting_time: float | None
    orders_per_hour: float | None
    total_distance_m: float
    simulated_time: float

    @classmethod
    def from_orders(
        cls,
        orders: Iterable[Order],
        total_distance_m: float,
        simulated_time: float,
    ) -> SimulationMetrics:
        completed = [order for order in orders if order.completion_time is not None]
        durations = [order.completion_time for order in completed]
        waits = [order.waiting_time for order in completed]
        return cls(
            completed_orders=len(completed),
            average_completion_time=mean(durations) if durations else None,
            longest_completion_time=max(durations) if durations else None,
            average_waiting_time=mean(waits) if waits else None,
            orders_per_hour=(
                len(completed) * SECONDS_PER_HOUR / simulated_time
                if simulated_time > 0
                else None
            ),
            total_distance_m=total_distance_m,
            simulated_time=simulated_time,
        )
