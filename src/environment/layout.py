from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Mapping

Coordinate = tuple[int, int]


@dataclass(frozen=True, slots=True)
class WarehouseLayout:
    """Static warehouse geometry independent from Mesa and simulation state."""

    width: int
    height: int
    blocked: frozenset[Coordinate] = frozenset()
    racks: Mapping[str, Coordinate] = MappingProxyType({})
    stations: Mapping[str, Coordinate] = MappingProxyType({})
    robot_starts: Mapping[str, Coordinate] = MappingProxyType({})

    _DIRECTIONS: ClassVar[tuple[Coordinate, ...]] = (
        (1, 0),
        (0, 1),
        (-1, 0),
        (0, -1),
    )

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Warehouse dimensions must be positive")

        object.__setattr__(self, "blocked", frozenset(self.blocked))
        for field_name in ("racks", "stations", "robot_starts"):
            object.__setattr__(
                self,
                field_name,
                MappingProxyType(dict(getattr(self, field_name))),
            )

        for position in self.blocked:
            self.validate_position(position)
        for positions in (self.racks, self.stations, self.robot_starts):
            for position in positions.values():
                self.validate_position(position)

        named_positions = (
            list(self.racks.values())
            + list(self.stations.values())
            + list(self.robot_starts.values())
        )
        if len(named_positions) != len(set(named_positions)):
            raise ValueError("Racks, stations, and robot starts cannot overlap")
        if set(named_positions) & self.blocked:
            raise ValueError("A rack, station, or robot cannot start on a blocked cell")

    def validate_position(self, position: Coordinate) -> None:
        x, y = position
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"Position {position} is outside the warehouse")

    def is_walkable(self, position: Coordinate) -> bool:
        self.validate_position(position)
        return position not in self.blocked

    def neighbors(self, position: Coordinate) -> tuple[Coordinate, ...]:
        self.validate_position(position)
        return tuple(
            (position[0] + dx, position[1] + dy)
            for dx, dy in self._DIRECTIONS
            if 0 <= position[0] + dx < self.width
            and 0 <= position[1] + dy < self.height
        )

    @classmethod
    def demo(
        cls,
        width: int = 20,
        height: int = 20,
        num_robots: int = 1,
    ) -> WarehouseLayout:
        """Create a small deterministic layout used by the visual demo."""
        if num_robots <= 0:
            raise ValueError("num_robots must be positive")
        wall_x = max(2, width // 3)
        blocked = frozenset((wall_x, y) for y in range(1, max(1, height - 1)))
        rack_position = (max(1, width - 3), height // 2)
        station_position = (1, 1)
        candidates = [
            (x, y)
            for y in range(height)
            for x in range(width)
            if (x, y) not in blocked
            and (x, y) not in {rack_position, station_position}
        ]
        if len(candidates) < num_robots:
            raise ValueError("Demo layout does not have enough robot start positions")
        return cls(
            width=width,
            height=height,
            blocked=blocked,
            racks={"rack-1": rack_position},
            stations={"station-1": station_position},
            robot_starts={
                f"robot-{index + 1}": position
                for index, position in enumerate(candidates[:num_robots])
            },
        )

    @classmethod
    def from_ascii(cls, rows: list[str]) -> WarehouseLayout:
        """Build a layout from ``#`` walls, ``R`` racks, ``S`` stations, and ``B`` robots."""
        if not rows or not rows[0]:
            raise ValueError("ASCII layout cannot be empty")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("All ASCII layout rows must have the same width")

        blocked: set[Coordinate] = set()
        racks: dict[str, Coordinate] = {}
        stations: dict[str, Coordinate] = {}
        robot_starts: dict[str, Coordinate] = {}
        counters = {"R": 0, "S": 0, "B": 0}
        supported = {".", "#", "R", "S", "B"}

        for y, row in enumerate(rows):
            for x, symbol in enumerate(row):
                if symbol not in supported:
                    raise ValueError(f"Unsupported layout symbol: {symbol!r}")
                position = (x, y)
                if symbol == "#":
                    blocked.add(position)
                elif symbol in counters:
                    counters[symbol] += 1
                    prefix = {"R": "rack", "S": "station", "B": "robot"}[symbol]
                    target = {
                        "R": racks,
                        "S": stations,
                        "B": robot_starts,
                    }[symbol]
                    target[f"{prefix}-{counters[symbol]}"] = position

        return cls(
            width=width,
            height=len(rows),
            blocked=frozenset(blocked),
            racks=racks,
            stations=stations,
            robot_starts=robot_starts,
        )
