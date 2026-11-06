from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from src.environment.layout import Coordinate

ConflictResolver = Callable[[str, str], str]
"""Return the ID of the robot that wins a conflict between two robots."""


class DeadlockError(RuntimeError):
    """Raised when robots wait for each other in a cycle."""


def natural_key(identifier: str) -> tuple[int, str, int]:
    """Sort ``robot-2`` before ``robot-10``; other IDs lexicographically."""
    prefix, separator, suffix = identifier.rpartition("-")
    if separator and suffix.isdigit():
        return (0, prefix, int(suffix))
    return (1, identifier, 0)


def lowest_id_wins(first: str, second: str) -> str:
    """Default conflict policy: the robot with the lower natural ID wins."""
    return min(first, second, key=natural_key)


@dataclass(frozen=True, slots=True)
class ReservationConflict:
    """A cell that one robot wants while another robot holds it."""

    requester_id: str
    holder_id: str
    cell: Coordinate


class ReservationTable:
    """Exclusive, short-window reservations of warehouse grid cells.

    Each robot owns a contiguous window of cells along its planned route: the
    cell it occupies now and up to ``lookahead`` cells ahead. A robot may only
    enter a cell reserved for it, so two robots never share a cell.

    The window is sliding: ``release_passed`` frees cells the robot has left,
    and ``try_extend`` appends new cells from the route. A conflict stops the
    window at the first cell held by another robot, unless ``preempt=True``
    and the configured conflict policy gives the requester priority.

    Conflict policy is a callable ``(requester_id, holder_id) -> winner_id``.
    The default is ``lowest_id_wins``; replace it with a task-aware policy
    later without touching the movement code.

    ``lookahead`` counts cells *ahead* of the current one, so a full window
    holds ``lookahead + 1`` cells. The immediate next cell of a robot is
    always protected from preemption: otherwise a higher-priority robot could
    leave another robot without a safe next step.
    """

    def __init__(
        self,
        lookahead: int = 3,
        resolve_conflict: ConflictResolver = lowest_id_wins,
    ):
        if lookahead < 1:
            raise ValueError("Reservation lookahead must be at least one cell")
        self.lookahead = lookahead
        self._resolve_conflict = resolve_conflict
        self._owners: dict[Coordinate, str] = {}
        self._windows: dict[str, list[Coordinate]] = {}

    def owner(self, cell: Coordinate) -> str | None:
        """Robot currently holding ``cell``, if any."""
        return self._owners.get(cell)

    def window(self, robot_id: str) -> tuple[Coordinate, ...]:
        """Cells reserved for ``robot_id``, in route order."""
        return tuple(self._windows.get(robot_id, ()))

    def is_reserved_by(self, robot_id: str, cell: Coordinate) -> bool:
        return self._owners.get(cell) == robot_id

    def resolve(self, first_id: str, second_id: str) -> str:
        """Return the winner of a conflict under the configured policy."""
        winner = self._resolve_conflict(first_id, second_id)
        if winner not in (first_id, second_id):
            raise ValueError(
                f"Conflict resolver returned {winner!r}, expected "
                f"{first_id!r} or {second_id!r}"
            )
        return winner

    def conflict(self, robot_id: str, cell: Coordinate) -> ReservationConflict | None:
        """Return the conflict blocking ``robot_id`` at ``cell``, if any."""
        holder_id = self._owners.get(cell)
        if holder_id is None or holder_id == robot_id:
            return None
        return ReservationConflict(robot_id, holder_id, cell)

    def try_extend(
        self,
        robot_id: str,
        cells: Sequence[Coordinate],
        *,
        max_window: int | None = None,
        preempt: bool = False,
    ) -> tuple[Coordinate, ...]:
        """Reserve the longest prefix of ``cells`` that is available.

        Cells already reserved by ``robot_id`` are skipped, not re-added.
        Returns only the newly reserved cells. With ``preempt=True``, a cell
        held by a lower-priority robot is taken over, but only when it is not
        that robot's immediate next cell.
        """
        max_window = self.lookahead + 1 if max_window is None else max_window
        if max_window < 1:
            raise ValueError("Window size must be positive")
        window = self._windows.setdefault(robot_id, [])
        newly_reserved: list[Coordinate] = []
        for cell in cells:
            if len(window) >= max_window:
                break
            holder_id = self._owners.get(cell)
            if holder_id == robot_id:
                continue
            if holder_id is not None:
                if not preempt or not self._can_preempt(robot_id, holder_id, cell):
                    break
                self.release_from(holder_id, cell)
            self._owners[cell] = robot_id
            window.append(cell)
            newly_reserved.append(cell)
        return tuple(newly_reserved)

    def release_passed(self, robot_id: str, cell: Coordinate) -> tuple[Coordinate, ...]:
        """Release ``cell`` and all earlier cells of the robot's window."""
        window = self._windows.get(robot_id)
        if not window:
            return ()
        try:
            index = window.index(cell)
        except ValueError:
            return ()
        return self._remove(robot_id, window[: index + 1])

    def release_from(self, robot_id: str, cell: Coordinate) -> tuple[Coordinate, ...]:
        """Release ``cell`` and all later cells of the robot's window."""
        window = self._windows.get(robot_id)
        if not window:
            return ()
        try:
            index = window.index(cell)
        except ValueError:
            return ()
        return self._remove(robot_id, window[index:])

    def release_all(self, robot_id: str) -> tuple[Coordinate, ...]:
        """Release every cell reserved for ``robot_id``."""
        window = self._windows.get(robot_id)
        if not window:
            return ()
        return self._remove(robot_id, window)

    def _can_preempt(
        self, requester_id: str, holder_id: str, cell: Coordinate
    ) -> bool:
        if self.resolve(requester_id, holder_id) != requester_id:
            return False
        holder_window = self._windows.get(holder_id, [])
        return not holder_window or holder_window[0] != cell

    def _remove(
        self, robot_id: str, cells: Iterable[Coordinate]
    ) -> tuple[Coordinate, ...]:
        window = self._windows.get(robot_id)
        if not window:
            return ()
        to_remove = set(cells)
        removed = tuple(cell for cell in window if cell in to_remove)
        if not removed:
            return ()
        for cell in removed:
            if self._owners.get(cell) == robot_id:
                del self._owners[cell]
        remaining = [cell for cell in window if cell not in to_remove]
        if remaining:
            self._windows[robot_id] = remaining
        else:
            self._windows.pop(robot_id, None)
        return removed
