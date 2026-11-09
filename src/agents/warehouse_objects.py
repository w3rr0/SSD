from collections import deque
from typing import Iterable

from mesa import Agent


lazy from src.agents.robot import Robot
lazy from src.environment.layout import Coordinate


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


class Charger(Agent):
    """A charging spot serving one robot at a time.

    A robot reserves the charger before it starts driving, so two robots never
    head for the same spot. Charging itself is a discrete event: the robot
    arrives, the model schedules the end of the charge, and the charger stays
    busy for that whole time.
    """

    def __init__(self, model, charger_id: str):
        super().__init__(model)
        self.charger_id = charger_id
        self.reserved_by: str | None = None
        self.robot: Robot | None = None
        self.charging_times: list[float] = []
        self._busy_time = 0.0
        self._busy_since: float | None = None

    @property
    def is_free(self) -> bool:
        return self.reserved_by is None

    def reserve(self, robot_id: str) -> None:
        """Claim the charger for ``robot_id`` while it drives here."""
        if self.reserved_by is not None:
            raise ValueError(
                f"{self.charger_id} is already reserved by {self.reserved_by}"
            )
        self.reserved_by = robot_id

    def occupy(self, robot: Robot) -> None:
        """Start charging ``robot``; the caller schedules the end event."""
        if self.reserved_by != robot.robot_id:
            raise ValueError(
                f"{robot.robot_id} cannot charge at {self.charger_id} "
                f"reserved by {self.reserved_by}"
            )
        self.robot = robot
        self._busy_since = float(self.model.time)

    def finish(self) -> None:
        """Stop charging and free the spot."""
        if self.robot is None or self._busy_since is None:
            raise RuntimeError(f"{self.charger_id} finished with no robot")
        duration = float(self.model.time) - self._busy_since
        self._busy_time += duration
        self.charging_times.append(duration)
        self._busy_since = None
        self.robot = None
        self.reserved_by = None

    def finish_charge(self) -> None:
        """Event handler: the scheduled charge is complete."""
        robot = self.robot
        if robot is None:
            raise RuntimeError(f"{self.charger_id} finished with no robot")
        self.finish()
        self.model.on_charge_finished(robot, self)

    def busy_time(self) -> float:
        """Seconds spent charging so far, including the session in progress."""
        if self._busy_since is None:
            return self._busy_time
        return self._busy_time + float(self.model.time) - self._busy_since

    def utilisation(self) -> float:
        now = float(self.model.time)
        return self.busy_time() / now if now > 0 else 0.0


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
        # Finished queue waits summed per robot (for the live statistics).
        self.wait_by_robot: dict[str, float] = {}
        self._busy_time = 0.0
        self._busy_since: float | None = None
        self._queued_at: dict[str, float] = {}

    @property
    def queue_length(self) -> int:
        return len(self.queue)

    def enqueue(self, robot: Robot, waiting_since: float | None = None) -> None:
        from src.agents.robot import RobotState

        robot.transition(RobotState.QUEUED)
        self.queue.append(robot)
        queued_at = (
            float(self.model.time) if waiting_since is None else waiting_since
        )
        self._queued_at[robot.robot_id] = queued_at
        self._start_next()

    def _start_next(self) -> None:
        from src.agents.robot import RobotState

        if self.serving is not None or not self.queue:
            return
        robot = self.queue.popleft()
        now = float(self.model.time)
        wait = now - self._queued_at.pop(robot.robot_id)
        self.wait_times.append(wait)
        self.wait_by_robot[robot.robot_id] = (
            self.wait_by_robot.get(robot.robot_id, 0.0) + wait
        )
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
