"""HTML of the live panels next to the map (statistics, robots, orders).

Each function turns a ``live_stats.Snapshot`` into an HTML fragment styled by
``PANEL_CSS``. Colours that carry meaning (status, battery) are fixed; text
and borders inherit the page theme so the panels work in light and dark mode.
"""

from datetime import datetime, timedelta
from html import escape

from src.agents.robot import RobotState
from src.visualization.live_stats import (
    FLEET_CATEGORIES,
    ORDER_STATUS_LABELS,
    Snapshot,
)
from src.visualization.svg import (
    ALERT,
    CHARGER,
    RACK,
    RACK_EDGE,
    STATION,
    STATION_LIGHT,
    WALL,
    robot_color,
)

FLEET_COLORS = {
    "picking": "#3f51b5",
    "loaded": "#c99a62",
    "empty": "#90a4ae",
    "waiting": "#e53935",
    "idle": "#cfd8dc",
    "charging": "#43a047",
    "failed": "#424242",
}

STATUS_COLORS = {
    "waiting": ("#fff3e0", "#e65100"),
    "in_progress": ("#e3f2fd", "#1565c0"),
    "completed": ("#e8f5e9", "#2e7d32"),
}

STATE_COLORS = {
    RobotState.IDLE: "#90a4ae",
    RobotState.TO_RACK: "#1e88e5",
    RobotState.TO_STATION: "#8d6e63",
    RobotState.QUEUED: "#fb8c00",
    RobotState.PICKING: "#3f51b5",
    RobotState.RETURNING_RACK: "#a1887f",
    RobotState.TO_CHARGER: "#66bb6a",
    RobotState.CHARGING: "#2e7d32",
    RobotState.FAILED: ALERT,
}

PANEL_CSS = """
.kv-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.kv-tile{border:1px solid rgba(128,128,128,.25);border-radius:10px;padding:8px 10px;min-width:0}
.kv-label{font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:.04em}
.kv-value{font-size:20px;font-weight:700;line-height:1.25;font-variant-numeric:tabular-nums}
.kv-sub{font-size:12px;opacity:.75;font-variant-numeric:tabular-nums}
.fleet-bar{display:flex;height:16px;border-radius:8px;overflow:hidden;margin:6px 0}
.fleet-legend{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px}
.dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.live-table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
.live-table th{text-align:left;font-weight:600;font-size:11px;opacity:.7;text-transform:uppercase;
  letter-spacing:.03em;padding:4px 6px;border-bottom:1px solid rgba(128,128,128,.35);position:sticky;top:0;
  background:var(--panel-bg, inherit)}
.live-table td{padding:4px 6px;border-bottom:1px solid rgba(128,128,128,.15);white-space:nowrap}
.live-table tr.fresh td{animation:fresh 1.2s ease-out}
@keyframes fresh{from{background:rgba(255,193,7,.35)}to{background:transparent}}
.num{text-align:right}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600}
.batt{display:inline-block;width:46px;height:8px;border-radius:4px;background:rgba(128,128,128,.25);
  overflow:hidden;vertical-align:middle;margin-right:6px}
.batt>span{display:block;height:100%}
.tag{display:inline-block;margin-left:6px;padding:0 6px;border-radius:8px;font-size:11px;color:#fff}
.scroll{max-height:420px;overflow:auto}
.station-row{display:flex;align-items:center;gap:8px;font-size:13px;margin:4px 0}
.util{flex:1;height:8px;border-radius:4px;background:rgba(128,128,128,.25);overflow:hidden}
.util>span{display:block;height:100%;background:#3f51b5}
.legend-item{display:flex;align-items:center;gap:8px;font-size:13px;margin:3px 0}
.legend-item svg{flex:none}
.banner{border-radius:10px;padding:10px 14px;font-size:14px;margin-bottom:8px}
.banner.alert{background:#ffebee;color:#b71c1c;border:1px solid #ef9a9a}
.banner.info{background:#e3f2fd;color:#0d47a1;border:1px solid #90caf9}
.banner.done{background:#e8f5e9;color:#1b5e20;border:1px solid #a5d6a7}
.warehouse-map{width:100%;height:auto;max-height:calc(100vh - 160px);display:block}
"""


def duration(seconds: float | None) -> str:
    """``42 s``, ``3 min 05 s``, ``1 h 02 min``; ``–`` for None."""
    if seconds is None:
        return "–"
    seconds = max(0, round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min {seconds % 60:02d} s"
    return f"{seconds // 3600} h {seconds % 3600 // 60:02d} min"


def clock(start: datetime, seconds: float) -> str:
    """Wall clock at ``seconds`` after ``start``, e.g. ``08:12:30``."""
    return (start + timedelta(seconds=float(seconds))).strftime("%H:%M:%S")


def _tile(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kv-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kv-tile"><div class="kv-label">{escape(label)}</div>'
        f'<div class="kv-value">{value}</div>{sub_html}</div>'
    )


def kpi_html(snap: Snapshot, start: datetime) -> str:
    in_system = snap.waiting + snap.in_progress
    last = (
        f"{duration(snap.last_order_duration_s)}"
        if snap.last_order_id is not None
        else "–"
    )
    last_sub = (
        f"{escape(snap.last_order_id)}, {duration(snap.last_order_ago_s)} temu"
        if snap.last_order_id is not None
        else "jeszcze brak"
    )
    per_hour = "–" if snap.orders_per_hour is None else f"{snap.orders_per_hour:.0f}"
    battery = "–" if snap.battery_mean is None else f"{snap.battery_mean:.0f}%"
    battery_sub = "" if snap.battery_min is None else f"najniższa {snap.battery_min:.0f}%"
    tiles = [
        _tile("Czas", clock(start, snap.time), f"od startu {duration(snap.time)}"),
        _tile(
            "Zrealizowane",
            f"{snap.completed}",
            f"z {snap.arrived} przyjętych, {snap.upcoming} nadejdzie",
        ),
        _tile("W systemie", f"{in_system}",
              f"{snap.in_progress} w realizacji, {snap.waiting} czeka"),
        _tile("Śr. czas realizacji", duration(snap.average_completion_s),
              f"najdłuższy {duration(snap.longest_completion_s)}"),
        _tile("Ostatnie zamówienie", last, last_sub),
        _tile("Zamówień / h", per_hour, f"ostatnia godzina: {snap.completed_last_hour}"),
        _tile("Czekanie na robota", duration(snap.average_first_robot_s),
              "średnio od przyjęcia"),
        _tile("Bateria floty", battery, battery_sub),
        _tile("Ładowarki", f"{snap.chargers_busy}/{snap.chargers_total}", "zajęte"),
    ]
    return f'<div class="kv-grid">{"".join(tiles)}</div>'


def fleet_html(snap: Snapshot) -> str:
    total = sum(snap.fleet_time.values())
    if total <= 0:
        return '<div class="kv-sub">Brak danych – uruchom symulację.</div>'
    bar, legend = [], []
    for key, label in FLEET_CATEGORIES:
        share = snap.fleet_time.get(key, 0.0) / total
        color = FLEET_COLORS[key]
        if share > 0:
            bar.append(
                f'<span title="{escape(label)} {share:.0%}" '
                f'style="width:{share * 100:.2f}%;background:{color}"></span>'
            )
        legend.append(
            f'<span><i class="dot" style="background:{color}"></i>'
            f"{escape(label)} <b>{share:.0%}</b></span>"
        )
    return (
        f'<div class="fleet-bar">{"".join(bar)}</div>'
        f'<div class="fleet-legend">{"".join(legend)}</div>'
    )


def stations_html(snap: Snapshot) -> str:
    rows = []
    for row in snap.stations:
        number = row.station_id.rsplit("-", 1)[-1]
        serving = escape(row.serving) if row.serving else "wolne"
        rows.append(
            f'<div class="station-row"><b style="width:28px">S{escape(number)}</b>'
            f'<div class="util"><span style="width:{row.utilisation * 100:.1f}%"></span></div>'
            f'<span style="width:44px" class="num">{row.utilisation:.0%}</span>'
            f'<span style="width:120px">kolejka {row.waiting}, obsł. {row.served}</span>'
            f'<span style="width:80px;opacity:.75">{serving}</span></div>'
        )
    return "".join(rows)


def _battery(level: float) -> str:
    color = ALERT if level < 20 else ("#f9a825" if level < 50 else "#43a047")
    return (
        f'<span class="batt"><span style="width:{max(0.0, min(100.0, level)):.0f}%;'
        f'background:{color}"></span></span>{level:.0f}%'
    )


def robots_html(snap: Snapshot) -> str:
    rows = []
    for index, row in enumerate(snap.robots):
        tags = ""
        if row.blocked:
            tags += f'<span class="tag" style="background:{ALERT}">stoi</span>'
        if row.yielding:
            tags += '<span class="tag" style="background:#ef6c00">ustępuje</span>'
        if row.carrying:
            tags += f'<span class="tag" style="background:{RACK_EDGE}">z regałem</span>'
        color = STATE_COLORS[row.state]
        rows.append(
            "<tr>"
            f'<td><i class="dot" style="background:{robot_color(index)}"></i>{row.number}</td>'
            f'<td><span style="color:{color};font-weight:600">{escape(row.label)}</span>{tags}</td>'
            f"<td>{_battery(row.battery)}</td>"
            f"<td>{escape(row.order_id or '–')}</td>"
            f'<td class="num">{duration(row.idle_s)}</td>'
            f'<td class="num">{duration(row.traffic_s)}</td>'
            f'<td class="num">{duration(row.queue_s)}</td>'
            "</tr>"
        )
    return (
        '<div class="scroll"><table class="live-table"><thead><tr>'
        "<th>Robot</th><th>Stan</th><th>Bateria</th><th>Zamówienie</th>"
        '<th class="num">Bezczynny</th><th class="num">W korku</th>'
        '<th class="num">W kolejce</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def orders_html(snap: Snapshot, start: datetime, fresh_s: float = 2.0) -> str:
    rows = []
    for row in snap.recent_orders:
        bg, fg = STATUS_COLORS[row.status]
        label = ORDER_STATUS_LABELS[row.status]
        station = row.station_id.rsplit("-", 1)[-1] if row.station_id else "–"
        robots = (
            ", ".join(r.rsplit("-", 1)[-1] for r in row.robots) if row.robots else "–"
        )
        urgent = (
            f'<span class="tag" style="background:{ALERT}">pilne</span>'
            if row.urgent
            else ""
        )
        fresh = ' class="fresh"' if snap.time - row.created_time <= fresh_s else ""
        time_label = duration(row.elapsed_s)
        rows.append(
            f"<tr{fresh}>"
            f"<td>{escape(row.order_id)}{urgent}</td>"
            f"<td>{clock(start, row.created_time)}</td>"
            f'<td><span class="badge" style="background:{bg};color:{fg}">{label}</span></td>'
            f'<td class="num">{row.lines} / {row.items}</td>'
            f'<td class="num">S{escape(station)}</td>'
            f"<td>{escape(robots)}</td>"
            f'<td class="num">{time_label}</td>'
            "</tr>"
        )
    if not rows:
        return '<div class="kv-sub">Jeszcze nie przyszło żadne zamówienie.</div>'
    return (
        '<div class="scroll"><table class="live-table"><thead><tr>'
        "<th>Zamówienie</th><th>Przyjęte</th><th>Status</th>"
        '<th class="num">Poz. / szt.</th><th class="num">Stan.</th><th>Roboty</th>'
        '<th class="num">Czas</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _legend_icon(body: str) -> str:
    return f'<svg width="22" height="22" viewBox="0 0 1 1">{body}</svg>'


def legend_html() -> str:
    color = robot_color(0)
    items = [
        (
            f'<rect x=".14" y=".14" width=".72" height=".72" rx=".2" fill="{color}" '
            'stroke="#1b1f24" stroke-width=".04"/><path d="M.86 .5L.7 .38V.62Z" fill="#fff"/>',
            "Robot (trójkąt = kierunek jazdy, pasek = bateria)",
        ),
        (
            f'<rect x=".1" y=".1" width=".8" height=".8" rx=".08" fill="{RACK}" '
            f'stroke="{color}" stroke-width=".1"/>',
            "Robot wiozący regał",
        ),
        (
            f'<rect x=".08" y=".08" width=".84" height=".84" rx=".08" fill="{RACK}" '
            f'stroke="{RACK_EDGE}" stroke-width=".05"/>'
            f'<path d="M.14 .36h.72M.14 .64h.72" stroke="#a87a45" stroke-width=".04"/>',
            "Regał",
        ),
        (
            f'<rect x=".08" y=".08" width=".84" height=".84" rx=".08" fill="{RACK}" '
            f'stroke="{color}" stroke-width=".1"/>',
            "Regał, po który jedzie robot (kolor robota)",
        ),
        (
            '<rect x=".1" y=".1" width=".8" height=".8" rx=".08" fill="none" '
            'stroke="#b9c2cc" stroke-width=".06" stroke-dasharray=".12 .08"/>',
            "Puste miejsce na regał",
        ),
        (
            f'<rect x=".04" y=".04" width=".92" height=".92" rx=".12" fill="{STATION_LIGHT}" '
            f'stroke="{STATION}" stroke-width=".06"/><circle cx=".5" cy=".36" r=".13" '
            f'fill="{STATION}"/><path d="M.24 .8q.26 -.36 .52 0" fill="{STATION}"/>',
            "Stanowisko kompletacji (ciemne = obsługuje, czerwona liczba = kolejka)",
        ),
        (
            f'<rect x=".04" y=".04" width=".92" height=".92" rx=".12" fill="#c8e6c9" '
            f'stroke="{CHARGER}" stroke-width=".06"/><path d="M.56 .14L.3 .55H.48L.42 .86'
            f'L.7 .43H.52Z" fill="{CHARGER}"/>',
            "Ładowarka",
        ),
        (
            f'<path d="M.05 .5H.95" stroke="{color}" stroke-width=".3" opacity=".3" '
            f'stroke-linecap="round"/><path d="M.05 .5H.95" stroke="{color}" '
            'stroke-width=".07" stroke-dasharray=".18 .12"/>',
            "Trasa (przerywana) i zarezerwowane pola (szeroki pas)",
        ),
        (
            f'<circle cx=".5" cy=".5" r=".4" fill="none" stroke="{ALERT}" stroke-width=".1"/>',
            "Robot w zakleszczeniu",
        ),
        (f'<rect width="1" height="1" fill="{WALL}"/>', "Ściana / słup"),
    ]
    return "".join(
        f'<div class="legend-item">{_legend_icon(body)}<span>{escape(text)}</span></div>'
        for body, text in items
    )
