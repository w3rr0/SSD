from collections.abc import Collection
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count

from src.environment.layout import Coordinate, WarehouseLayout


class NoPathError(RuntimeError):
    """Raised when a destination cannot be reached on the warehouse layout."""


@dataclass(frozen=True, slots=True)
class TrafficRules:
    """Extra step costs that steer robots away from head-on meetings.

    * Corridor rows and columns (at least 60% aisle) get alternating
      directions, like one-way streets. A step against the direction costs
      ``against_lane_cost`` more; it stays allowed, so dead ends and the last
      cells before a goal remain reachable.
    * Stepping onto a rack slot costs ``rack_cell_cost`` more, so empty
      robots, which may drive under racks, still prefer the aisles.
    * Stepping onto the front cell of a station or charger that is not the
      goal costs ``front_cell_cost`` more, so passing traffic keeps the only
      way out of a busy station free.
    """

    row_direction: dict[int, int]
    column_direction: dict[int, int]
    rack_cells: frozenset[Coordinate]
    front_of: dict[Coordinate, frozenset[Coordinate]]
    against_lane_cost: int = 10
    rack_cell_cost: int = 3
    front_cell_cost: int = 6

    @classmethod
    def from_layout(
        cls,
        layout: WarehouseLayout,
        against_lane_cost: int = 10,
        rack_cell_cost: int = 3,
        front_cell_cost: int = 6,
    ) -> "TrafficRules":
        fixed = (
            set(layout.racks.values())
            | set(layout.stations.values())
            | set(layout.chargers.values())
        )

        def aisle(cell: Coordinate) -> bool:
            return cell not in layout.blocked and cell not in fixed

        rows = [
            y
            for y in range(layout.height)
            if sum(aisle((x, y)) for x in range(layout.width)) >= 0.6 * layout.width
        ]
        columns = [
            x
            for x in range(layout.width)
            if sum(aisle((x, y)) for y in range(layout.height))
            >= 0.6 * layout.height
        ]
        front_of: dict[Coordinate, set[Coordinate]] = {}
        for target in (*layout.stations.values(), *layout.chargers.values()):
            for cell in layout.neighbors(target):
                if layout.is_walkable(cell):
                    front_of.setdefault(cell, set()).add(target)
        return cls(
            row_direction={y: 1 if k % 2 == 0 else -1 for k, y in enumerate(rows)},
            column_direction={
                x: 1 if k % 2 == 0 else -1 for k, x in enumerate(columns)
            },
            rack_cells=frozenset(layout.racks.values()),
            front_of={cell: frozenset(t) for cell, t in front_of.items()},
            against_lane_cost=against_lane_cost,
            rack_cell_cost=rack_cell_cost,
            front_cell_cost=front_cell_cost,
        )

    def step_cost(self, current: Coordinate, nxt: Coordinate, goal: Coordinate) -> int:
        cost = 1
        dx, dy = nxt[0] - current[0], nxt[1] - current[1]
        row = self.row_direction.get(current[1])
        if dx and row is not None and dx != row:
            cost += self.against_lane_cost
        column = self.column_direction.get(current[0])
        if dy and column is not None and dy != column:
            cost += self.against_lane_cost
        if nxt != goal:
            if nxt in self.rack_cells:
                cost += self.rack_cell_cost
            targets = self.front_of.get(nxt)
            if targets is not None and goal not in targets:
                cost += self.front_cell_cost
        return cost


def astar_path(
    layout: WarehouseLayout,
    start: Coordinate,
    goal: Coordinate,
    obstacles: Collection[Coordinate] | None = None,
    rules: TrafficRules | None = None,
) -> tuple[Coordinate, ...]:
    """Return a cheapest four-directional route, including start and goal.

    ``obstacles`` are cells occupied right now (e.g. racks standing in the
    warehouse). When omitted, the static rack and station positions from the
    layout (racks, stations, chargers) are used. The start and goal cells are
    never treated as obstacles. Without ``rules`` every step costs 1 (the
    shortest route); with ``rules`` the extra costs of :class:`TrafficRules`
    apply. The heuristic (Manhattan distance) stays admissible either way.
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
            step = 1 if rules is None else rules.step_cost(current, neighbor, goal)
            new_cost = cost_so_far[current] + step
            if new_cost >= cost_so_far.get(neighbor, float("inf")):
                continue
            cost_so_far[neighbor] = new_cost
            came_from[neighbor] = current
            heappush(
                frontier,
                (new_cost + heuristic(neighbor), next(sequence), neighbor),
            )

    raise NoPathError(f"Cannot route from {start} to {goal}")
