from collections.abc import Collection
from heapq import heappop, heappush
from itertools import count

from src.environment.layout import Coordinate, WarehouseLayout


class NoPathError(RuntimeError):
    """Raised when a destination cannot be reached on the warehouse layout."""


def astar_path(
    layout: WarehouseLayout,
    start: Coordinate,
    goal: Coordinate,
    obstacles: Collection[Coordinate] | None = None,
) -> tuple[Coordinate, ...]:
    """Return a shortest four-directional route, including start and goal.

    ``obstacles`` are cells occupied right now (e.g. racks standing in the
    warehouse). When omitted, the static rack and station positions from the
    layout (racks, stations, chargers) are used. The start and goal cells are never treated as obstacles.
    """
    layout.validate_position(start)
    layout.validate_position(goal)
    if not layout.is_walkable(start) or not layout.is_walkable(goal):
        raise NoPathError(f"Cannot route from {start} to {goal}")
    if start == goal:
        return (start,)

    if obstacles is None:
        obstacles = (
            set(layout.racks.values())
            | set(layout.stations.values())
            | set(layout.chargers.values())
        )
    occupied_cells = set(obstacles)
    occupied_cells.discard(start)
    occupied_cells.discard(goal)

    def traversable(position: Coordinate) -> bool:
        return layout.is_walkable(position) and position not in occupied_cells

    def heuristic(position: Coordinate) -> int:
        return abs(position[0] - goal[0]) + abs(position[1] - goal[1])

    sequence = count()
    frontier: list[tuple[int, int, Coordinate]] = []
    heappush(frontier, (heuristic(start), next(sequence), start))
    came_from: dict[Coordinate, Coordinate | None] = {start: None}
    cost_so_far = {start: 0}

    while frontier:
        _, _, current = heappop(frontier)
        if current == goal:
            path: list[Coordinate] = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            return tuple(reversed(path))

        for neighbor in layout.neighbors(current):
            if not traversable(neighbor):
                continue
            new_cost = cost_so_far[current] + 1
            if new_cost >= cost_so_far.get(neighbor, float("inf")):
                continue
            cost_so_far[neighbor] = new_cost
            came_from[neighbor] = current
            heappush(
                frontier,
                (new_cost + heuristic(neighbor), next(sequence), neighbor),
            )

    raise NoPathError(f"Cannot route from {start} to {goal}")
