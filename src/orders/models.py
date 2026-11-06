from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(slots=True)
class Order:
    order_id: str
    rack_id: str
    station_id: str
    status: OrderStatus = OrderStatus.PENDING
    assigned_robot_id: str | None = None
    created_time: float = 0.0
    started_time: float | None = None
    completed_time: float | None = None

    def start(self, robot_id: str, time: float) -> None:
        if self.status is not OrderStatus.PENDING:
            raise ValueError(f"Order {self.order_id} cannot be started twice")
        self.assigned_robot_id = robot_id
        self.started_time = time
        self.status = OrderStatus.IN_PROGRESS

    def complete(self, time: float) -> None:
        if self.status is not OrderStatus.IN_PROGRESS:
            raise ValueError(f"Order {self.order_id} is not in progress")
        self.completed_time = time
        self.status = OrderStatus.COMPLETED

    @property
    def completion_time(self) -> float | None:
        """Seconds from the order entering the system until it is completed."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    @property
    def waiting_time(self) -> float | None:
        """Seconds the order waited for a robot to be assigned."""
        if self.started_time is None:
            return None
        return self.started_time - self.created_time
