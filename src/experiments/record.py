"""Run a configured warehouse and record its live data as DataFrames.

:func:`run_and_record` drives the model with :meth:`Warehouse.step` and calls
:func:`src.visualization.live_stats.snapshot` at a fixed sampling interval, so
the recorded time series is exactly what the browser visualisation shows, plus
the final :class:`SimulationMetrics` and the full per-order lifecycle.

The result is a :class:`RecordedRun` holding pandas DataFrames, which can be
written to CSV/JSON (:meth:`RecordedRun.write_outputs`) or used directly in a
notebook. Every table carries a ``run_id`` column so several runs can be
concatenated and compared.
"""

import json
import time as _time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from src.core.model import Warehouse
from src.metrics.baseline import SimulationMetrics
from src.pipeline.reservations import DeadlockError, LivelockError
from src.visualization.live_stats import (
    FLEET_CATEGORIES,
    Snapshot,
    order_status,
    snapshot,
)

ModelFactory = Callable[[], Warehouse]

# Columns of each table, so readers and writers agree on the schema.
SNAPSHOT_COLUMNS = (
    "time",
    "orders_total",
    "arrived",
    "completed",
    "waiting",
    "in_progress",
    "upcoming",
    "average_completion_s",
    "longest_completion_s",
    "average_first_robot_s",
    "orders_per_hour",
    "completed_last_hour",
    "battery_mean",
    "battery_min",
    "chargers_busy",
    "chargers_total",
) + tuple(f"fleet_{key}" for key, _ in FLEET_CATEGORIES)

ROBOT_COLUMNS = (
    "time",
    "robot_id",
    "number",
    "state",
    "label",
    "battery",
    "order_id",
    "carrying",
    "blocked",
    "yielding",
    "idle_s",
    "traffic_s",
    "queue_s",
)

STATION_COLUMNS = (
    "time",
    "station_id",
    "serving",
    "waiting",
    "served",
    "utilisation",
)

ORDER_COLUMNS = (
    "order_id",
    "created_time",
    "status",
    "lines",
    "items",
    "station_id",
    "urgent",
    "waiting_time",
    "completion_time",
)


@dataclass(slots=True)
class RecordedRun:
    """One headless run: its parameters, time series and final metrics."""

    run_id: str
    params: dict
    snapshots_df: pd.DataFrame
    robots_df: pd.DataFrame
    stations_df: pd.DataFrame
    orders_df: pd.DataFrame
    metrics: SimulationMetrics
    status: str
    stop_reason: str | None
    wall_s: float

    def write_outputs(self, directory: Path | str) -> Path:
        """Write the run to ``directory`` as CSV files and a ``run.json``."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.snapshots_df.to_csv(directory / "snapshots.csv", index=False)
        self.robots_df.to_csv(directory / "robots.csv", index=False)
        self.stations_df.to_csv(directory / "stations.csv", index=False)
        self.orders_df.to_csv(directory / "orders.csv", index=False)
        (directory / "run.json").write_text(
            json.dumps(
                {
                    "run_id": self.run_id,
                    "params": self.params,
                    "status": self.status,
                    "stop_reason": self.stop_reason,
                    "wall_s": self.wall_s,
                    "metrics": asdict(self.metrics),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return directory


def _snapshot_row(snap: Snapshot) -> dict:
    row: dict = {
        "time": snap.time,
        "orders_total": snap.orders_total,
        "arrived": snap.arrived,
        "completed": snap.completed,
        "waiting": snap.waiting,
        "in_progress": snap.in_progress,
        "upcoming": snap.upcoming,
        "average_completion_s": snap.average_completion_s,
        "longest_completion_s": snap.longest_completion_s,
        "average_first_robot_s": snap.average_first_robot_s,
        "orders_per_hour": snap.orders_per_hour,
        "completed_last_hour": snap.completed_last_hour,
        "battery_mean": snap.battery_mean,
        "battery_min": snap.battery_min,
        "chargers_busy": snap.chargers_busy,
        "chargers_total": snap.chargers_total,
    }
    for key, _ in FLEET_CATEGORIES:
        row[f"fleet_{key}"] = snap.fleet_time.get(key, 0.0)
    return row


def _robot_rows(snap: Snapshot) -> list[dict]:
    return [
        {
            "time": snap.time,
            "robot_id": robot.robot_id,
            "number": robot.number,
            "state": robot.state.value,
            "label": robot.label,
            "battery": robot.battery,
            "order_id": robot.order_id,
            "carrying": robot.carrying,
            "blocked": robot.blocked,
            "yielding": robot.yielding,
            "idle_s": robot.idle_s,
            "traffic_s": robot.traffic_s,
            "queue_s": robot.queue_s,
        }
        for robot in snap.robots
    ]


def _station_rows(snap: Snapshot) -> list[dict]:
    return [
        {
            "time": snap.time,
            "station_id": station.station_id,
            "serving": station.serving,
            "waiting": station.waiting,
            "served": station.served,
            "utilisation": station.utilisation,
        }
        for station in snap.stations
    ]


def _orders_table(model: Warehouse) -> pd.DataFrame:
    rows = [
        {
            "order_id": order.order_id,
            "created_time": order.created_time,
            "status": order_status(order),
            "lines": len(order.lines),
            "items": order.items,
            "station_id": order.station_id,
            "urgent": order.urgent,
            "waiting_time": order.waiting_time,
            "completion_time": order.completion_time,
        }
        for order in model.released_orders
    ]
    return pd.DataFrame(rows, columns=ORDER_COLUMNS)


def _final_status(model: Warehouse) -> tuple[str, str | None]:
    stop_reason = getattr(model, "stop_reason", None)
    if model.all_orders_completed:
        return "done", stop_reason
    if stop_reason is not None:
        status = "deadlock" if "Zakleszczenie" in stop_reason else "livelock"
        return status, stop_reason
    return "ok", None


def run_and_record(
    factory: ModelFactory,
    duration: float,
    sample_every: float = 10.0,
    warm_up: float = 0.0,
    run_id: str = "run",
    params: dict | None = None,
) -> RecordedRun:
    """Run ``factory()`` for ``duration`` seconds and record its live data.

    Snapshots are taken every ``sample_every`` seconds of simulated time
    (after an optional ``warm_up`` that is not recorded) and always at the
    end. The run stops early when every order is completed or a deadlock
    stops the model.
    """
    if duration <= 0:
        raise ValueError("Duration must be positive")
    if sample_every <= 0:
        raise ValueError("Sample interval must be positive")

    started = _time.perf_counter()
    model = factory()
    snapshots: list[dict] = []
    robot_rows: list[dict] = []
    station_rows: list[dict] = []

    def collect() -> None:
        snap = snapshot(model)
        snapshots.append(_snapshot_row(snap))
        robot_rows.extend(_robot_rows(snap))
        station_rows.extend(_station_rows(snap))

    # Warm-up: advance without recording (mirrors the queueing validation).
    while warm_up > 0 and model.time < warm_up and model.running:
        model.step()

    next_sample = model.time + sample_every
    try:
        while model.time < duration and model.running:
            model.step()
            if model.time >= next_sample:
                collect()
                next_sample += sample_every
    except (DeadlockError, LivelockError) as exc:
        model.stop_reason = str(exc)
        model.running = False
    if not snapshots or snapshots[-1]["time"] < model.time:
        collect()  # always keep the final state, without duplicating a sample

    wall_s = _time.perf_counter() - started
    status, stop_reason = _final_status(model)
    return RecordedRun(
        run_id=run_id,
        params=dict(params or {}),
        snapshots_df=_tag(pd.DataFrame(snapshots, columns=SNAPSHOT_COLUMNS), run_id),
        robots_df=_tag(pd.DataFrame(robot_rows, columns=ROBOT_COLUMNS), run_id),
        stations_df=_tag(pd.DataFrame(station_rows, columns=STATION_COLUMNS), run_id),
        orders_df=_tag(_orders_table(model), run_id),
        metrics=model.metrics,
        status=status,
        stop_reason=stop_reason,
        wall_s=wall_s,
    )


def _tag(frame: pd.DataFrame, run_id: str) -> pd.DataFrame:
    return frame.assign(run_id=run_id)


def load(directory: Path | str) -> RecordedRun:
    """Read a run previously written with :meth:`RecordedRun.write_outputs`."""
    directory = Path(directory)
    meta = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    return RecordedRun(
        run_id=meta["run_id"],
        params=meta["params"],
        snapshots_df=pd.read_csv(directory / "snapshots.csv"),
        robots_df=pd.read_csv(directory / "robots.csv"),
        stations_df=pd.read_csv(directory / "stations.csv"),
        orders_df=pd.read_csv(directory / "orders.csv"),
        metrics=SimulationMetrics(**meta["metrics"]),
        status=meta["status"],
        stop_reason=meta["stop_reason"],
        wall_s=meta["wall_s"],
    )
