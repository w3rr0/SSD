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
    chargers: Mapping[str, Coordinate] = MappingProxyType({})

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
        for field_name in ("racks", "stations", "robot_starts", "chargers"):
            object.__setattr__(
                self,
                field_name,
                MappingProxyType(dict(getattr(self, field_name))),
            )

        for position in self.blocked:
            self.validate_position(position)
        for positions in (self.racks, self.stations, self.robot_starts, self.chargers):
            for position in positions.values():
                self.validate_position(position)

        named_positions = (
            list(self.racks.values())
            + list(self.stations.values())
            + list(self.robot_starts.values())
            + list(self.chargers.values())
        )
        if len(named_positions) != len(set(named_positions)):
            raise ValueError(
                "Racks, stations, chargers, and robot starts cannot overlap"
            )
        if set(named_positions) & self.blocked:
            raise ValueError(
                "A rack, station, charger, or robot cannot be on a blocked cell"
            )

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
        """Largest generated layout that fits ``width`` x ``height`` (visual demo)."""
        block_length = 4
        block_depth = 2
        columns = (width - cls._LEFT_MARGIN - 1) // (block_length + 1)
        rows = (height - 1) // (block_depth + 1)
        if columns < 1 or rows < 1:
            raise ValueError("Demo layout needs at least 9 x 4 cells")
        return cls.generate(
            block_columns=columns,
            block_rows=rows,
            block_length=block_length,
            block_depth=block_depth,
            num_stations=min(3, max(1, height // 7)),
            num_chargers=min(3, max(1, height // 7)),
            num_robots=num_robots,
            width=width,
            height=height,
        )

    _LEFT_MARGIN: ClassVar[int] = 3

    @classmethod
    def generate(
        cls,
        block_columns: int = 4,
        block_rows: int = 4,
        block_length: int = 5,
        block_depth: int = 2,
        num_stations: int = 2,
        num_chargers: int = 2,
        num_robots: int = 4,
        width: int | None = None,
        height: int | None = None,
    ) -> WarehouseLayout:
        """Kiva-style grid: blocks of racks separated by one-cell aisles.

        ::

            x=0   stations on the left wall, the rest of the wall blocked
            x=1-2 buffer aisles in front of the stations
            x>=3  rack blocks (block_length x block_depth) with aisles
                  between them on every side
            last  chargers on the right wall, the rest of the wall blocked

        Every rack touches an aisle when ``block_depth <= 2``, so it can be
        reached even though standing racks are obstacles. ``width`` and
        ``height`` may enlarge the grid; the extra cells are aisles. Robots
        start on the bottom aisle row, then the next free aisle cells.
        """
        if min(block_columns, block_rows, block_length, block_depth) <= 0:
            raise ValueError("Block counts and sizes must be positive")
        if block_depth > 2:
            raise ValueError("block_depth > 2 would leave racks without aisle access")
        if num_stations <= 0:
            raise ValueError("At least one picking station is required")
        if num_chargers < 0 or num_robots <= 0:
            raise ValueError("Invalid number of chargers or robots")

        min_width = cls._LEFT_MARGIN + block_columns * (block_length + 1) + 1
        min_height = 1 + block_rows * (block_depth + 1)
        width = min_width if width is None else width
        height = min_height if height is None else height
        if width < min_width or height < min_height:
            raise ValueError(
                f"{block_columns}x{block_rows} blocks need at least "
                f"{min_width}x{min_height} cells"
            )
        if num_stations > height or num_chargers > height:
            raise ValueError("Too many stations or chargers for the wall length")

        racks: dict[str, Coordinate] = {}
        for block_row in range(block_rows):
            y0 = 1 + block_row * (block_depth + 1)
            for dy in range(block_depth):
                for block_column in range(block_columns):
                    x0 = cls._LEFT_MARGIN + block_column * (block_length + 1)
                    for dx in range(block_length):
                        racks[f"rack-{len(racks) + 1}"] = (x0 + dx, y0 + dy)

        def spread(count: int) -> list[int]:
            return [round((i + 1) * (height - 1) / (count + 1)) for i in range(count)]

        stations = {
            f"station-{i + 1}": (0, y) for i, y in enumerate(spread(num_stations))
        }
        charger_x = width - 1
        chargers = {
            f"charger-{i + 1}": (charger_x, y)
            for i, y in enumerate(spread(num_chargers))
        }
        walls = {(0, y) for y in range(height)} | {
            (charger_x, y) for y in range(height)
        }
        blocked = walls - set(stations.values()) - set(chargers.values())

        occupied = set(racks.values()) | walls
        free_cells = [
            (x, y)
            for y in range(height)
            for x in range(width)
            if (x, y) not in occupied
        ]
        if len(free_cells) < num_robots:
            raise ValueError("Not enough aisle cells for the robots")
        robot_starts = {
            f"robot-{i + 1}": position
            for i, position in enumerate(free_cells[:num_robots])
        }
        return cls(
            width=width,
            height=height,
            blocked=frozenset(blocked),
            racks=racks,
            stations=stations,
            robot_starts=robot_starts,
            chargers=chargers,
        )

    @classmethod
    def from_ascii(cls, rows: list[str]) -> WarehouseLayout:
        """Build a layout from ``#`` walls, ``R`` racks, ``S`` stations,
        ``C`` chargers, and ``B`` robots.

        The first row is ``y = 0``.
        """
        if not rows or not rows[0]:
            raise ValueError("ASCII layout cannot be empty")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("All ASCII layout rows must have the same width")

        blocked: set[Coordinate] = set()
        racks: dict[str, Coordinate] = {}
        stations: dict[str, Coordinate] = {}
        robot_starts: dict[str, Coordinate] = {}
        chargers: dict[str, Coordinate] = {}
        counters = {"R": 0, "S": 0, "B": 0, "C": 0}
        supported = {".", "#", "R", "S", "B", "C"}

        for y, row in enumerate(rows):
            for x, symbol in enumerate(row):
                if symbol not in supported:
                    raise ValueError(f"Unsupported layout symbol: {symbol!r}")
                position = (x, y)
                if symbol == "#":
                    blocked.add(position)
                elif symbol in counters:
                    counters[symbol] += 1
                    prefix = {
                        "R": "rack",
                        "S": "station",
                        "B": "robot",
                        "C": "charger",
                    }[symbol]
                    target = {
                        "R": racks,
                        "S": stations,
                        "B": robot_starts,
                        "C": chargers,
                    }[symbol]
                    target[f"{prefix}-{counters[symbol]}"] = position

        return cls(
            width=width,
            height=len(rows),
            blocked=frozenset(blocked),
            racks=racks,
            stations=stations,
            robot_starts=robot_starts,
            chargers=chargers,
        )
