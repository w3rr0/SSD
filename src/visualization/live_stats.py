"""Live statistics of a running warehouse, for the visualisation panel.

Everything here reads the model and returns plain data; nothing changes the
simulation. Times are seconds of simulation time.
"""

from dataclasses import dataclass, field
from statistics import mean

from src.agents.robot import RobotState
from src.core.model import Warehouse
from src.orders.models import Order, OrderStatus

STATE_LABELS: dict[RobotState, str] = {
    RobotState.IDLE: "bezczynny",
    RobotState.TO_RACK: "jedzie po regał",
    RobotState.TO_STATION: "wiezie regał",
    RobotState.QUEUED: "w kolejce",
    RobotState.PICKING: "kompletacja",
    RobotState.RETURNING_RACK: "odwozi regał",
    RobotState.TO_CHARGER: "jedzie ładować",
    RobotState.CHARGING: "ładuje się",
    RobotState.FAILED: "awaria",
}

ORDER_STATUS_LABELS: dict[str, str] = {
    "upcoming": "nadchodzi",
    "waiting": "czeka na robota",
    "in_progress": "w realizacji",
    "completed": "gotowe",
}

# Order of the fleet time bar; the labels are what the panel shows.
FLEET_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("picking", "Kompletacja"),
    ("loaded", "Jazda z regałem"),
    ("empty", "Jazda pusta"),
    ("waiting", "Korki i kolejki"),
    ("idle", "Bezczynność"),
    ("charging", "Ładowanie"),
    ("failed", "Awaria"),
)

LAST_HOUR_S = 3600.0


@dataclass(frozen=True, slots=True)
class RobotRow:
    robot_id: str
    number: int
    state: RobotState
    label: str
    battery: float
    order_id: str | None
    carrying: bool
    blocked: bool
    yielding: bool
    idle_s: float
    traffic_s: float
    queue_s: float


@dataclass(frozen=True, slots=True)
class OrderRow:
    order_id: str
    created_time: float
    status: str
    lines: int
    items: int
    station_id: str | None
    robots: tuple[str, ...]
    elapsed_s: float
    urgent: bool


@dataclass(frozen=True, slots=True)
class StationRow:
    station_id: str
    serving: str | None
    waiting: int
    served: int
    utilisation: float


@dataclass(frozen=True, slots=True)
class Snapshot:
    time: float
    orders_total: int
    arrived: int
    completed: int
    waiting: int
    in_progress: int
    upcoming: int
    average_completion_s: float | None
    longest_completion_s: float | None
    average_first_robot_s: float | None
    last_order_id: str | None
    last_order_duration_s: float | None
    last_order_ago_s: float | None
    orders_per_hour: float | None
    completed_last_hour: int
    battery_mean: float | None
    battery_min: float | None
    robots: tuple[RobotRow, ...]
    fleet_time: dict[str, float] = field(default_factory=dict)
    stations: tuple[StationRow, ...] = ()
    chargers_busy: int = 0
    chargers_total: int = 0
    recent_orders: tuple[OrderRow, ...] = ()


def robot_number(robot_id: str) -> int:
    """``robot-12`` -> 12; other IDs -> 0."""
    suffix = robot_id.rsplit("-", 1)[-1]
    return int(suffix) if suffix.isdigit() else 0


def current_queue_wait(model: Warehouse, robot_id: str, now: float) -> float:
    """Station queue time of a wait that has not ended yet."""
    since = model._station_wait_started.get(robot_id)
    if since is None:
        for station in model.stations.values():
            since = station._queued_at.get(robot_id)
            if since is not None:
                break
    return max(0.0, now - since) if since is not None else 0.0


def robot_rows(model: Warehouse) -> tuple[RobotRow, ...]:
    now = float(model.time)
    rows = []
    for robot in model.robots:
        task = model._task_of(robot)
        rows.append(
            RobotRow(
                robot_id=robot.robot_id,
                number=robot_number(robot.robot_id),
                state=robot.state,
                label=STATE_LABELS[robot.state],
                battery=robot.battery,
                order_id=task.order_id if task is not None else None,
                carrying=robot.carrying_rack_id is not None,
                blocked=robot.blocked,
                yielding=robot.yielding,
                idle_s=robot.time_in_state()[RobotState.IDLE],
                traffic_s=robot.traffic_wait_s,
                queue_s=sum(
                    station.wait_by_robot.get(robot.robot_id, 0.0)
                    for station in model.stations.values()
                )
                + current_queue_wait(model, robot.robot_id, now),
            )
        )
    return tuple(rows)


def fleet_time(model: Warehouse, rows: tuple[RobotRow, ...]) -> dict[str, float]:
    """Robot-seconds of the whole fleet by activity, keyed as FLEET_CATEGORIES.

    Waiting in jams and station queues happens while a robot is in a moving
    state, so it is taken out of the driving time (split between loaded and
    empty driving in proportion to their size).
    """
    totals = {key: 0.0 for key, _ in FLEET_CATEGORIES}
    for robot in model.robots:
        spent = robot.time_in_state()
        totals["picking"] += spent[RobotState.QUEUED] + spent[RobotState.PICKING]
        totals["loaded"] += (
            spent[RobotState.TO_STATION] + spent[RobotState.RETURNING_RACK]
        )
        totals["empty"] += spent[RobotState.TO_RACK] + spent[RobotState.TO_CHARGER]
        totals["idle"] += spent[RobotState.IDLE]
        totals["charging"] += spent[RobotState.CHARGING]
        totals["failed"] += spent[RobotState.FAILED]
    waiting = sum(row.traffic_s + row.queue_s for row in rows)
    driving = totals["loaded"] + totals["empty"]
    if driving > 0:
        taken = min(waiting, driving)
        for key in ("loaded", "empty"):
            totals[key] -= taken * totals[key] / driving
        totals["waiting"] = taken
    return totals


def order_status(order: Order) -> str:
    if order.status is OrderStatus.COMPLETED:
        return "completed"
    if order.status is OrderStatus.IN_PROGRESS:
        return "in_progress"
    return "waiting"


def order_row(order: Order, now: float) -> OrderRow:
    status = order_status(order)
    if status == "completed":
        elapsed = order.completion_time or 0.0
    else:
        elapsed = max(0.0, now - order.created_time)
    robots = tuple(
        sorted(
            {task.robot_id for task in order.tasks if task.robot_id is not None},
            key=robot_number,
        )
    )
    return OrderRow(
        order_id=order.order_id,
        created_time=order.created_time,
        status=status,
        lines=len(order.lines),
        items=order.items,
        station_id=order.station_id,
        robots=robots,
        elapsed_s=elapsed,
        urgent=order.urgent,
    )


def recent_orders(model: Warehouse, limit: int = 30) -> tuple[OrderRow, ...]:
    """Newest released orders first: the live list of incoming orders."""
    now = float(model.time)
    newest = model.released_orders[-limit:]
    return tuple(order_row(order, now) for order in reversed(newest))


def station_rows(model: Warehouse) -> tuple[StationRow, ...]:
    waiting: dict[str, int] = {station_id: 0 for station_id in model.stations}
    for robot_id in model._station_wait_started:
        task = model._task_of(model.robot_by_id[robot_id])
        if task is not None:
            waiting[task.station_id] += 1
    rows = []
    for station_id, station in model.stations.items():
        rows.append(
            StationRow(
                station_id=station_id,
                serving=station.serving.robot_id if station.serving else None,
                waiting=waiting[station_id] + station.queue_length,
                served=station.served,
                utilisation=station.utilisation(),
            )
        )
    return tuple(rows)


def snapshot(model: Warehouse, order_limit: int = 30) -> Snapshot:
    now = float(model.time)
    completed = [o for o in model.released_orders if o.completed_time is not None]
    durations = [o.completion_time for o in completed]
    first_robot = [
        o.waiting_time for o in model.released_orders if o.waiting_time is not None
    ]
    last = max(completed, key=lambda o: o.completed_time, default=None)
    waiting = sum(
        1 for o in model.released_orders if o.status is OrderStatus.PENDING
    )
    in_progress = sum(
        1 for o in model.released_orders if o.status is OrderStatus.IN_PROGRESS
    )
    rows = robot_rows(model)
    batteries = [row.battery for row in rows]
    return Snapshot(
        time=now,
        orders_total=len(model.orders),
        arrived=len(model.released_orders),
        completed=len(completed),
        waiting=waiting,
        in_progress=in_progress,
        upcoming=len(model.orders) - len(model.released_orders),
        average_completion_s=mean(durations) if durations else None,
        longest_completion_s=max(durations) if durations else None,
        average_first_robot_s=mean(first_robot) if first_robot else None,
        last_order_id=last.order_id if last else None,
        last_order_duration_s=last.completion_time if last else None,
        last_order_ago_s=now - last.completed_time if last else None,
        orders_per_hour=len(completed) * 3600.0 / now if now > 0 else None,
        completed_last_hour=sum(
            1 for o in completed if o.completed_time >= now - LAST_HOUR_S
        ),
        battery_mean=mean(batteries) if batteries else None,
        battery_min=min(batteries) if batteries else None,
        robots=rows,
        fleet_time=fleet_time(model, rows),
        stations=station_rows(model),
        chargers_busy=sum(1 for c in model.chargers.values() if not c.is_free),
        chargers_total=len(model.chargers),
        recent_orders=recent_orders(model, order_limit),
    )

