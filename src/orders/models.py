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
    created_step: int = 0
    started_step: int | None = None
    completed_step: int | None = None

    def start(self, robot_id: str, step: int) -> None:
        if self.status is not OrderStatus.PENDING:
            raise ValueError(f"Order {self.order_id} cannot be started twice")
        self.assigned_robot_id = robot_id
        self.started_step = step
        self.status = OrderStatus.IN_PROGRESS

    def complete(self, step: int) -> None:
        if self.status is not OrderStatus.IN_PROGRESS:
            raise ValueError(f"Order {self.order_id} is not in progress")
        self.completed_step = step
        self.status = OrderStatus.COMPLETED

    @property
    def completion_time(self) -> int | None:
        """Time from the order entering the system until it is completed."""
        if self.completed_step is None:
            return None
        return self.completed_step - self.created_step

    @property
    def waiting_time(self) -> int | None:
        """Time the order waited for a robot to be assigned."""
        if self.started_step is None:
            return None
        return self.started_step - self.created_step
