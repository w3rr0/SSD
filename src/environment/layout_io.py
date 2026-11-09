"""Warehouse layouts stored as JSON files (see ``layouts/README.md``).

A file holds either a drawn map::

    {
      "name": "Small hall",
      "description": "Two rack blocks, one station.",
      "map": [
        "##########",
        "S....RR..C",
        "#..B.....#",
        "##########"
      ]
    }

or the parameters of the Kiva-style generator::

    {"name": "Generated 4x4", "generator": {"block_columns": 4, "block_rows": 4}}

Map symbols: ``#`` wall, `` `` (space) outside the building, ``.`` floor,
``R`` rack, ``S`` picking station, ``C`` charger, ``B`` robot start. The
first map row is the top of the hall, as on screen.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from src.environment.layout import WarehouseLayout

LAYOUTS_DIR = Path(__file__).resolve().parents[2] / "layouts"

_GENERATOR_KEYS = frozenset(
    {
        "block_columns",
        "block_rows",
        "block_length",
        "block_depth",
        "num_stations",
        "num_chargers",
        "num_robots",
        "width",
        "height",
    }
)


@dataclass(frozen=True, slots=True)
class LayoutFile:
    """A layout read from disk, with the text shown to the user."""

    key: str
    name: str
    description: str
    layout: WarehouseLayout


def layout_from_dict(data: dict) -> WarehouseLayout:
    """Build a layout from the parsed JSON of a layout file."""
    if not isinstance(data, dict):
        raise ValueError("A layout file must contain a JSON object")
    has_map = "map" in data
    has_generator = "generator" in data
    if has_map == has_generator:
        raise ValueError('A layout needs exactly one of "map" or "generator"')

    if has_map:
        rows = data["map"]
        if not isinstance(rows, list) or not all(isinstance(r, str) for r in rows):
            raise ValueError('"map" must be a list of strings')
        layout = WarehouseLayout.from_ascii(rows, top_down=True)
    else:
        params = data["generator"]
        if not isinstance(params, dict):
            raise ValueError('"generator" must be an object')
        unknown = set(params) - _GENERATOR_KEYS
        if unknown:
            raise ValueError(f"Unknown generator parameters: {sorted(unknown)}")
        layout = WarehouseLayout.generate(**params)

    if not layout.stations:
        raise ValueError("The layout has no picking station (S)")
    if not layout.racks:
        raise ValueError("The layout has no racks (R)")
    problems = layout.unreachable()
    if problems:
        shown = ", ".join(problems[:8]) + (" ..." if len(problems) > 8 else "")
        raise ValueError(f"Robots cannot reach: {shown}")
    return layout


def load_layout(path: Path | str) -> LayoutFile:
    """Read and validate one layout file."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid JSON ({exc})") from None
    try:
        layout = layout_from_dict(data)
    except ValueError as exc:
        raise ValueError(f"{path.name}: {exc}") from None
    return LayoutFile(
        key=path.stem,
        name=str(data.get("name", path.stem)),
        description=str(data.get("description", "")),
        layout=layout,
    )


def available_layouts(directory: Path | str = LAYOUTS_DIR) -> dict[str, LayoutFile]:
    """Every valid layout file in ``directory``, keyed by file name (no .json).

    Broken files are skipped so that one bad file does not take the
    visualisation down; ``load_layout`` reports what is wrong with them.
    """
    directory = Path(directory)
    layouts: dict[str, LayoutFile] = {}
    if not directory.is_dir():
        return layouts
    for path in sorted(directory.glob("*.json")):
        try:
            layouts[path.stem] = load_layout(path)
        except ValueError:
            continue
    return layouts
