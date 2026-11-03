from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from src.orders.models import Order


@dataclass(frozen=True, slots=True)
class SimulationMetrics:
    completed_orders: int
    average_completion_time: float | None
    longest_completion_time: int | None
    total_distance: int

    @classmethod
    def from_orders(cls, orders: Iterable[Order], total_distance: int) -> SimulationMetrics:
        durations = [
            order.completion_time
            for order in orders
            if order.completion_time is not None
        ]
        return cls(
            completed_orders=len(durations),
            average_completion_time=mean(durations) if durations else None,
            longest_completion_time=max(durations) if durations else None,
            total_distance=total_distance,
        )
