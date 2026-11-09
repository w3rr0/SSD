"""Draw the warehouse as an SVG image (walls, racks, robots, stations).

The drawing works in grid units: one cell is one SVG unit, so the image
scales to any size without losing sharpness. Cell ``(x, y)`` with ``y = 0``
at the bottom is drawn with its top-left corner at ``(x, height - 1 - y)``.

``render_svg`` is called on every frame. The parts that never change during
a run (floor, walls, outline, rack slots) are cached per layout.
"""

from html import escape

from src.agents.robot import Robot, RobotState
from src.core.model import Warehouse
from src.environment.layout import Coordinate, WarehouseLayout

# Palette. The map keeps its own light "floor plan" look in both themes.
FLOOR = "#eef1f4"
GRID = "#d9dfe6"
WALL = "#3d4754"
OUTLINE = "#262d36"
SLOT = "#b9c2cc"
RACK = "#c99a62"
RACK_EDGE = "#8a6236"
RACK_SHELF = "#a87a45"
STATION = "#3f51b5"
STATION_LIGHT = "#c5cae9"
CHARGER = "#2e7d32"
CHARGER_LIGHT = "#c8e6c9"
ALERT = "#d32f2f"
YIELD = "#ef6c00"
TEXT_DARK = "#1b1f24"

# Robot colours: distinct, readable with white text.
ROBOT_COLORS = (
    "#1e88e5", "#e53935", "#43a047", "#8e24aa", "#fb8c00",
    "#00897b", "#5e35b1", "#c0ca33", "#d81b60", "#3949ab",
    "#6d4c41", "#00acc1", "#7cb342", "#f4511e", "#546e7a",
)

HEAT = ("#fff3e0", "#ffcc80", "#ffa726", "#f57c00", "#e65100", "#bf360c")

_STATIC_CACHE: dict[int, tuple[WarehouseLayout, str]] = {}


def robot_color(index: int) -> str:
    return ROBOT_COLORS[index % len(ROBOT_COLORS)]


def _top(layout: WarehouseLayout, y: int) -> int:
    return layout.height - 1 - y


def _runs(layout: WarehouseLayout, cells: frozenset[Coordinate]):
    """Horizontal runs of ``cells``: (x, top, length) in SVG units."""
    for y in range(layout.height):
        x = 0
        while x < layout.width:
            if (x, y) in cells:
                start = x
                while x < layout.width and (x, y) in cells:
                    x += 1
                yield start, _top(layout, y), x - start
            else:
                x += 1


def _outline_path(layout: WarehouseLayout) -> str:
    """Edges between the building and the outside (or the grid border)."""
    inside = {
        (x, y)
        for x in range(layout.width)
        for y in range(layout.height)
        if (x, y) not in layout.outside
    }
    parts = []
    for x, y in inside:
        top = _top(layout, y)
        if (x, y + 1) not in inside:
            parts.append(f"M{x} {top}h1")
        if (x, y - 1) not in inside:
            parts.append(f"M{x} {top + 1}h1")
        if (x - 1, y) not in inside:
            parts.append(f"M{x} {top}v1")
        if (x + 1, y) not in inside:
            parts.append(f"M{x + 1} {top}v1")
    return "".join(sorted(parts))


def static_layer(layout: WarehouseLayout) -> str:
    """Floor, grid, walls and building outline of ``layout`` (cached)."""
    cached = _STATIC_CACHE.get(id(layout))
    if cached is not None and cached[0] is layout:
        return cached[1]
    floor = layout.floor
    out = [
        "<defs>"
        '<pattern id="grid" width="1" height="1" patternUnits="userSpaceOnUse">'
        f'<path d="M1 0H0V1" fill="none" stroke="{GRID}" stroke-width="0.03"/>'
        "</pattern>"
        '<filter id="lift" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0.04" dy="0.07" stdDeviation="0.05" '
        'flood-color="#000" flood-opacity="0.35"/></filter>'
        "</defs>"
    ]
    for x, top, length in _runs(layout, floor):
        out.append(
            f'<rect x="{x}" y="{top}" width="{length}" height="1" fill="{FLOOR}"/>'
            f'<rect x="{x}" y="{top}" width="{length}" height="1" fill="url(#grid)"/>'
        )
    for x, top, length in _runs(layout, layout.walls):
        out.append(
            f'<rect x="{x}" y="{top}" width="{length}" height="1" fill="{WALL}"/>'
        )
    out.append(
        f'<path d="{_outline_path(layout)}" stroke="{OUTLINE}" '
        'stroke-width="0.12" stroke-linecap="square" fill="none"/>'
    )
    svg = "".join(out)
    if len(_STATIC_CACHE) > 16:
        _STATIC_CACHE.clear()
    _STATIC_CACHE[id(layout)] = (layout, svg)
    return svg


def _rack_shape(x: float, y: float, fill: str, edge: str, *, size: float = 0.84,
                edge_width: float = 0.05, shadow: bool = False) -> str:
    """A rack seen from above: a frame with two shelves."""
    inset = (1 - size) / 2
    left, top = x + inset, y + inset
    shelf_a = top + size / 3
    shelf_b = top + 2 * size / 3
    style = ' filter="url(#lift)"' if shadow else ""
    return (
        f'<g{style}><rect x="{left:.3f}" y="{top:.3f}" width="{size}" height="{size}" '
        f'rx="0.08" fill="{fill}" stroke="{edge}" stroke-width="{edge_width}"/>'
        f'<path d="M{left + 0.06:.3f} {shelf_a:.3f}h{size - 0.12:.3f}'
        f'M{left + 0.06:.3f} {shelf_b:.3f}h{size - 0.12:.3f}" '
        f'stroke="{RACK_SHELF}" stroke-width="0.04"/></g>'
    )


def _heat_color(trips: int, most: int) -> str:
    if most <= 0 or trips <= 0:
        return HEAT[0]
    index = 1 + min(len(HEAT) - 2, int((len(HEAT) - 2) * trips / most))
    return HEAT[index]


def _racks(model: Warehouse, colors: str, robot_index: dict[str, int]) -> str:
    layout = model.layout
    out = []
    standing = {rack.pos for rack in model.racks.values() if rack.carried_by is None}
    for slot in layout.racks.values():
        if slot in standing:
            continue
        x, y = slot[0], _top(layout, slot[1])
        out.append(
            f'<rect x="{x + 0.1}" y="{y + 0.1}" width="0.8" height="0.8" rx="0.08" '
            f'fill="none" stroke="{SLOT}" stroke-width="0.05" stroke-dasharray="0.12 0.08"/>'
        )
    most = max((rack.trips for rack in model.racks.values()), default=0)
    for rack in model.racks.values():
        if rack.carried_by is not None:
            continue
        x, y = rack.pos[0], _top(layout, rack.pos[1])
        fill = _heat_color(rack.trips, most) if colors == "heat" else RACK
        edge, edge_width = RACK_EDGE, 0.05
        task = model.tasks_by_id.get(rack.reserved_by_task) if rack.reserved_by_task else None
        if task is not None and task.robot_id in robot_index:
            # The rack a robot is driving to: framed in that robot's colour.
            edge, edge_width = robot_color(robot_index[task.robot_id]), 0.1
        skus = len(rack.skus)
        out.append(
            f"<g><title>{escape(rack.rack_id)}: {skus} produktów, kursów: {rack.trips}"
            f"</title>{_rack_shape(x, y, fill, edge, edge_width=edge_width)}</g>"
        )
    return "".join(out)


def _station(model: Warehouse, station_id: str, waiting: int) -> str:
    layout = model.layout
    cx, cy = layout.stations[station_id]
    x, y = cx, _top(layout, cy)
    station = model.stations[station_id]
    busy = station.serving is not None
    number = station_id.rsplit("-", 1)[-1]
    out = [
        f"<g><title>{escape(station_id)}: obsłużono {station.served}, "
        f"czeka {waiting}</title>",
        f'<rect x="{x + 0.04}" y="{y + 0.04}" width="0.92" height="0.92" rx="0.12" '
        f'fill="{STATION if busy else STATION_LIGHT}" stroke="{STATION}" stroke-width="0.06"/>',
        # The picker: head and shoulders.
        f'<circle cx="{x + 0.5}" cy="{y + 0.36}" r="0.13" '
        f'fill="{"#fff" if busy else STATION}"/>',
        f'<path d="M{x + 0.24} {y + 0.8}q0.26 -0.36 0.52 0" '
        f'fill="{"#fff" if busy else STATION}"/>',
        f'<text x="{x + 0.5}" y="{y - 0.1}" font-size="0.34" text-anchor="middle" '
        f'font-weight="700" fill="{STATION}" stroke="#fff" stroke-width="0.1" '
        f'paint-order="stroke">S{escape(number)}</text>',
    ]
    if waiting:
        out.append(
            f'<circle cx="{x + 0.9}" cy="{y + 0.1}" r="0.24" fill="{ALERT}"/>'
            f'<text x="{x + 0.9}" y="{y + 0.19}" font-size="0.28" text-anchor="middle" '
            f'font-weight="700" fill="#fff">{waiting}</text>'
        )
    out.append("</g>")
    return "".join(out)


def _charger(model: Warehouse, charger_id: str) -> str:
    layout = model.layout
    cx, cy = layout.chargers[charger_id]
    x, y = cx, _top(layout, cy)
    charger = model.chargers[charger_id]
    busy = charger.robot is not None
    state = "ładuje " + charger.robot.robot_id if busy else (
        "zarezerwowana" if charger.reserved_by else "wolna"
    )
    return (
        f"<g><title>{escape(charger_id)}: {escape(state)}</title>"
        f'<rect x="{x + 0.04}" y="{y + 0.04}" width="0.92" height="0.92" rx="0.12" '
        f'fill="{CHARGER if busy else CHARGER_LIGHT}" stroke="{CHARGER}" stroke-width="0.06"/>'
        f'<path d="M{x + 0.56} {y + 0.14}L{x + 0.3} {y + 0.55}H{x + 0.48}L{x + 0.42} {y + 0.86}'
        f'L{x + 0.7} {y + 0.43}H{x + 0.52}Z" fill="{"#fff" if busy else CHARGER}"/></g>'
    )


def _routes(model: Warehouse, robot_index: dict[str, int]) -> str:
    layout = model.layout
    out = []
    for robot in model.robots:
        color = robot_color(robot_index[robot.robot_id])
        path = (robot.pos, *robot.route)
        if len(path) >= 2:
            points = " ".join(f"{x + 0.5},{_top(layout, y) + 0.5}" for x, y in path)
            out.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" '
                'stroke-width="0.07" stroke-dasharray="0.18 0.14" opacity="0.6" '
                'stroke-linejoin="round"/>'
            )
        window = model.reservations.window(robot.robot_id)
        if len(window) >= 2:
            points = " ".join(f"{x + 0.5},{_top(layout, y) + 0.5}" for x, y in window)
            out.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" '
                'stroke-width="0.32" opacity="0.28" stroke-linecap="round" '
                'stroke-linejoin="round"/>'
            )
    return "".join(out)


def _heading(robot: Robot) -> Coordinate | None:
    if not robot.route:
        return None
    nx, ny = robot.route[0]
    return (nx - robot.pos[0], ny - robot.pos[1])


def _battery_color(battery: float) -> str:
    if battery < 20:
        return ALERT
    if battery < 50:
        return "#f9a825"
    return "#43a047"


def _robot(
    model: Warehouse,
    robot: Robot,
    index: int,
    alert: bool,
    standing_racks: frozenset[Coordinate] = frozenset(),
) -> str:
    layout = model.layout
    x, y = robot.pos[0], _top(layout, robot.pos[1])
    cx, cy = x + 0.5, y + 0.5
    color = robot_color(index)
    failed = robot.state is RobotState.FAILED
    body = "#9e9e9e" if failed else color
    number = robot.robot_id.rsplit("-", 1)[-1]
    out = [f"<g><title>{escape(robot.robot_id)}: {escape(robot.state.value)}, "
           f"bateria {robot.battery:.0f}%</title>"]

    if alert or robot.blocked:
        stroke = ALERT if alert else YIELD
        dash = "" if alert else ' stroke-dasharray="0.15 0.1"'
        cls = ' class="pulse"' if alert else ""
        out.append(
            f'<circle{cls} cx="{cx}" cy="{cy}" r="0.56" fill="none" stroke="{stroke}" '
            f'stroke-width="0.08"{dash}/>'
        )

    # Body: a low square vehicle with rounded corners and a lifting disc.
    under_rack = robot.carrying_rack_id is None and robot.pos in standing_racks
    if under_rack:
        # Parked under a standing rack: the rack stays visible around it.
        out.append(
            f'<rect x="{x + 0.27}" y="{y + 0.27}" width="0.46" height="0.46" rx="0.14" '
            f'fill="{body}" stroke="#1b1f24" stroke-width="0.04"/>'
        )
    else:
        out.append(
            f'<rect x="{x + 0.14}" y="{y + 0.14}" width="0.72" height="0.72" rx="0.2" '
            f'fill="{body}" stroke="#1b1f24" stroke-width="0.04" filter="url(#lift)"/>'
        )
    heading = _heading(robot)
    if heading is not None:
        dx, dy = heading[0], -heading[1]
        hx, hy = cx + 0.27 * dx, cy + 0.27 * dy
        px, py = -dy, dx
        out.append(
            f'<path d="M{hx + 0.12 * dx:.3f} {hy + 0.12 * dy:.3f}'
            f'L{hx + 0.1 * px:.3f} {hy + 0.1 * py:.3f}'
            f'L{hx - 0.1 * px:.3f} {hy - 0.1 * py:.3f}Z" fill="#fff" opacity="0.9"/>'
        )

    if robot.carrying_rack_id is not None:
        out.append(_rack_shape(x, y, RACK, color, size=0.8, edge_width=0.1, shadow=True))
        label_fill = TEXT_DARK
    elif not under_rack:
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="0.2" fill="#ffffff" opacity="0.28"/>'
        )
        label_fill = "#fff"
    else:
        label_fill = "#fff"

    font = 0.26 if under_rack else 0.32
    out.append(
        f'<text x="{cx}" y="{cy + font / 3:.3f}" font-size="{font}" text-anchor="middle" '
        f'font-weight="700" fill="{label_fill}">{escape(number)}</text>'
    )

    # Battery bar under the robot.
    level = max(0.0, min(1.0, robot.battery / 100.0))
    out.append(
        f'<rect x="{x + 0.18}" y="{y + 0.9}" width="0.64" height="0.09" rx="0.03" '
        'fill="#263238" opacity="0.55"/>'
        f'<rect x="{x + 0.18}" y="{y + 0.9}" width="{0.64 * level:.3f}" height="0.09" '
        f'rx="0.03" fill="{_battery_color(robot.battery)}"/>'
    )
    if failed:
        out.append(
            f'<path d="M{x + 0.3} {y + 0.3}l0.4 0.4M{x + 0.7} {y + 0.3}l-0.4 0.4" '
            f'stroke="{ALERT}" stroke-width="0.1" stroke-linecap="round"/>'
        )
    if robot.state is RobotState.CHARGING:
        out.append(
            f'<path d="M{x + 0.86} {y + 0.02}L{x + 0.72} {y + 0.24}H{x + 0.82}L{x + 0.76} '
            f'{y + 0.4}L{x + 0.94} {y + 0.16}H{x + 0.84}Z" fill="#ffeb3b" stroke="#333" '
            'stroke-width="0.02"/>'
        )
    out.append("</g>")
    return "".join(out)


def render_svg(
    model: Warehouse,
    *,
    show_routes: bool = True,
    rack_colors: str = "plain",
    alert_robots: frozenset[str] = frozenset(),
    station_waiting: dict[str, int] | None = None,
) -> str:
    """The whole warehouse as an ``<svg>`` element.

    ``rack_colors`` is ``"plain"`` or ``"heat"`` (colour by number of trips).
    ``alert_robots`` get a red pulsing ring, e.g. the robots of a deadlock.
    ``station_waiting`` is the queue length shown on each station.
    """
    layout = model.layout
    robot_index = {robot.robot_id: i for i, robot in enumerate(model.robots)}
    waiting = station_waiting or {}
    margin = 0.6
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="warehouse-map" '
        f'viewBox="{-margin} {-margin} {layout.width + 2 * margin} {layout.height + 2 * margin}" '
        'font-family="Inter, Segoe UI, Roboto, sans-serif" role="img" '
        'aria-label="Plan magazynu">',
        "<style>.pulse{animation:pulse 1s ease-in-out infinite}"
        "@keyframes pulse{50%{opacity:.25}}</style>",
        static_layer(layout),
        _racks(model, rack_colors, robot_index),
        "".join(_charger(model, c) for c in layout.chargers),
        "".join(_station(model, s, waiting.get(s, 0)) for s in layout.stations),
    ]
    if show_routes:
        parts.append(_routes(model, robot_index))
    standing = frozenset(
        rack.pos for rack in model.racks.values() if rack.carried_by is None
    )
    parts.extend(
        _robot(
            model,
            robot,
            robot_index[robot.robot_id],
            robot.robot_id in alert_robots,
            standing,
        )
        for robot in model.robots
    )
    parts.append("</svg>")
    return "".join(parts)
