from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable


class OrderStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


TaskStatus = OrderStatus


@dataclass(frozen=True, slots=True)
class OrderLine:
    """One product (SKU) and how many units of it the customer ordered."""

    sku: str
    quantity: int = 1

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"Quantity of {self.sku} must be positive")


def _normalise_lines(lines: Iterable[OrderLine | str]) -> tuple[OrderLine, ...]:
    """Accept ``OrderLine`` objects or bare SKU strings; merge repeated SKUs."""
    quantities: dict[str, int] = {}
    for line in lines:
        if isinstance(line, str):
            line = OrderLine(line)
        quantities[line.sku] = quantities.get(line.sku, 0) + line.quantity
    return tuple(OrderLine(sku, qty) for sku, qty in quantities.items())


@dataclass(slots=True)
class PickTask:
    """Bring one rack to one station and pick some lines of an order from it."""

    task_id: str
    order_id: str
    rack_id: str
    station_id: str
    lines: tuple[OrderLine, ...]
    created_time: float
    status: TaskStatus = TaskStatus.PENDING
    robot_id: str | None = None
    started_time: float | None = None
    completed_time: float | None = None

    @property
    def items(self) -> int:
        return sum(line.quantity for line in self.lines)

    def start(self, robot_id: str, time: float) -> None:
        if self.status is not TaskStatus.PENDING:
            raise ValueError(f"Task {self.task_id} cannot be started twice")
        self.robot_id = robot_id
        self.started_time = time
        self.status = TaskStatus.IN_PROGRESS

    def complete(self, time: float) -> None:
        if self.status is not TaskStatus.IN_PROGRESS:
            raise ValueError(f"Task {self.task_id} is not in progress")
        self.completed_time = time
        self.status = TaskStatus.COMPLETED


@dataclass(slots=True)
class Order:
    """A customer order: a list of lines that may need several racks.

    ``station_id`` may be left empty; the model then picks a station when the
    order arrives. ``urgent`` orders are offered to robots before normal ones
    with the same arrival time. Times are in seconds of simulation time.
    """

    order_id: str
    lines: tuple[OrderLine, ...]
    created_time: float = 0.0
    due_time: float | None = None
    urgent: bool = False
    station_id: str | None = None
    status: OrderStatus = OrderStatus.PENDING
    started_time: float | None = None
    completed_time: float | None = None
    tasks: list[PickTask] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.lines = _normalise_lines(self.lines)
        if not self.lines:
            raise ValueError(f"Order {self.order_id} has no lines")

    @property
    def skus(self) -> frozenset[str]:
        return frozenset(line.sku for line in self.lines)

    @property
    def items(self) -> int:
        return sum(line.quantity for line in self.lines)

    def start(self, time: float) -> None:
        """Mark the moment the first robot was assigned to the order."""
        if self.status is OrderStatus.COMPLETED:
            raise ValueError(f"Order {self.order_id} is already completed")
        if self.status is OrderStatus.PENDING:
            self.started_time = time
            self.status = OrderStatus.IN_PROGRESS

    def complete(self, time: float) -> None:
        if self.status is not OrderStatus.IN_PROGRESS:
            raise ValueError(f"Order {self.order_id} is not in progress")
        self.completed_time = time
        self.status = OrderStatus.COMPLETED

    @property
    def all_tasks_completed(self) -> bool:
        return bool(self.tasks) and all(
            task.status is TaskStatus.COMPLETED for task in self.tasks
        )

    @property
    def completion_time(self) -> float | None:
        """Seconds from the order entering the system until it is completed."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    @property
    def waiting_time(self) -> float | None:
        """Seconds the order waited for its first robot."""
        if self.started_time is None:
            return None
        return self.started_time - self.created_time
