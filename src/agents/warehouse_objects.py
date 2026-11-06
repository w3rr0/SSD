from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Iterable

from mesa import Agent

if TYPE_CHECKING:
    from src.agents.robot import Robot
    from src.environment.layout import Coordinate


class Rack(Agent):
    """A movable shelf holding a set of products (SKUs)."""

    def __init__(
        self,
        model,
        rack_id: str,
        home: Coordinate,
        skus: Iterable[str] = (),
    ):
        super().__init__(model)
        self.rack_id = rack_id
        self.home = home
        self.skus: frozenset[str] = frozenset(skus)
        self.carried_by: str | None = None
        self.reserved_by_task: str | None = None
        self.trips = 0

    @property
    def is_free(self) -> bool:
        return self.carried_by is None and self.reserved_by_task is None


class PickingStation(Agent):
    """A picker serving robots one at a time in FIFO order.

    Arrival puts the robot in the queue; the end of picking is a discrete
    event scheduled with ``Model.schedule_event``.
    """

    def __init__(self, model, station_id: str):
        super().__init__(model)
        self.station_id = station_id
        self.queue: deque[Robot] = deque()
        self.serving: Robot | None = None
        self.served = 0
        self.wait_times: list[float] = []
        self._busy_time = 0.0
        self._busy_since: float | None = None
        self._queued_at: dict[str, float] = {}

    @property
    def queue_length(self) -> int:
        return len(self.queue)

    def enqueue(self, robot: Robot) -> None:
        from src.agents.robot import RobotState

        robot.transition(RobotState.QUEUED)
        self.queue.append(robot)
        self._queued_at[robot.robot_id] = float(self.model.time)
        self._start_next()

    def _start_next(self) -> None:
        from src.agents.robot import RobotState

        if self.serving is not None or not self.queue:
            return
        robot = self.queue.popleft()
        now = float(self.model.time)
        self.wait_times.append(now - self._queued_at.pop(robot.robot_id))
        robot.transition(RobotState.PICKING)
        self.serving = robot
        self._busy_since = now
        duration = self.model.pick_duration(robot)
        self.model.schedule_event(self.finish_pick, after=duration)

    def finish_pick(self) -> None:
        robot = self.serving
        if robot is None:
            raise RuntimeError(f"{self.station_id} finished picking with no robot")
        self._busy_time += float(self.model.time) - self._busy_since
        self._busy_since = None
        self.serving = None
        self.served += 1
        self.model.on_pick_finished(robot, self)
        self._start_next()

    def busy_time(self) -> float:
        """Seconds spent picking so far, including the visit in progress."""
        if self._busy_since is None:
            return self._busy_time
        return self._busy_time + float(self.model.time) - self._busy_since

    def utilisation(self) -> float:
        now = float(self.model.time)
        return self.busy_time() / now if now > 0 else 0.0
