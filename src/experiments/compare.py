"""Run many short headless runs in parallel and collect one row per run.

Used by ``notebooks/porownania.ipynb``. Every run is built with
:func:`src.experiments.build.make_warehouse` (the same parameters as the
visualisation sidebar) and recorded with :func:`run_and_record`, so a row
shows the same numbers as the live view at the end of the run.

Results are cached in a CSV next to the notebook output: running the
notebook again only computes runs that are not in the file yet.
"""

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from src.environment.layout import WarehouseLayout
from src.experiments.build import make_warehouse
from src.experiments.record import run_and_record

# Parameters that identify a run; anything else in a spec is a label.
PARAMS = (
    "layout",
    "num_robots",
    "orders",
    "placement",
    "return_policy",
    "volume",
    "hours",
    "seed",
    "assignment",
    "traffic",
)
DEFAULTS = {
    "layout": "kiva_standard",
    "num_robots": 8,
    "orders": "olist",
    "placement": "random",
    "return_policy": "home",
    "volume": 1.0,
    "hours": 4,
    "seed": 1,
    "assignment": "nearest",
    "traffic": "new",
}


def full(spec: dict) -> dict:
    """``spec`` with every run parameter filled in from ``DEFAULTS``."""
    return {**DEFAULTS, **spec}


def run_one(spec: dict) -> dict:
    """One run; never raises, the outcome is in ``status``."""
    spec = full(spec)
    params = {key: spec[key] for key in PARAMS}
    try:
        rec = run_and_record(
            factory=lambda: make_warehouse(**params),
            duration=params["hours"] * 3600.0,
            sample_every=600.0,
        )
    except Exception as exc:  # noqa: BLE001 - one bad run must not stop a grid
        return {**spec, "status": "error", "stop_reason": f"{type(exc).__name__}: {exc}"}
    m = rec.metrics
    completed = m.completed_orders or 0
    utilisation = list(m.station_utilisation.values())
    return {
        **spec,
        "status": rec.status,
        "stop_reason": rec.stop_reason or "",
        "simulated_h": m.simulated_time / 3600.0,
        "released": len(rec.orders_df),
        "completed": completed,
        "orders_per_hour": m.orders_per_hour,
        "avg_completion_s": m.average_completion_time,
        "max_completion_s": m.longest_completion_time,
        "avg_wait_for_robot_s": m.average_waiting_time,
        "avg_station_queue_s": m.average_station_wait,
        "distance_per_order_m": m.total_distance_m / completed if completed else None,
        "traffic_share_pct": None
        if m.traffic_wait_share is None
        else 100 * m.traffic_wait_share,
        "station_utilisation_pct": 100 * sum(utilisation) / len(utilisation)
        if utilisation
        else None,
        "racks_home_pct": None
        if m.racks_returned_home_share is None
        else 100 * m.racks_returned_home_share,
        "wall_s": rec.wall_s,
    }


def run_grid(specs: list[dict], cache: Path | str, jobs: int = 4) -> pd.DataFrame:
    """Run every spec not yet in ``cache`` (in parallel) and return all rows."""
    cache = Path(cache)
    done = pd.read_csv(cache) if cache.exists() else pd.DataFrame()
    key = lambda row: tuple(str(full(row)[p]) for p in PARAMS)  # noqa: E731
    have = {key(r) for r in done.to_dict("records")} if len(done) else set()
    todo = [spec for spec in specs if key(spec) not in have]
    if todo:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            rows = list(pool.map(run_one, todo))
        done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        done.to_csv(cache, index=False)
    wanted = {key(spec) for spec in specs}
    return done[[key(r) in wanted for r in done.to_dict("records")]].reset_index(drop=True)


def summary(frame: pd.DataFrame, by: list[str], metrics: list[str]) -> pd.DataFrame:
    """Mean and 95% half-width (t) of each metric over seeds, plus run counts.

    Only runs that did not stop on a deadlock are averaged; ``ok`` and
    ``runs`` show how many that is.
    """
    from scipy import stats

    rows = []
    for values, group in frame.groupby(by, sort=False):
        values = values if isinstance(values, tuple) else (values,)
        good = group[~group["status"].isin(["deadlock", "livelock", "error"])]
        row = dict(zip(by, values))
        row["ok"] = len(good)
        row["runs"] = len(group)
        for metric in metrics:
            series = good[metric].dropna().astype(float)
            row[metric] = series.mean() if len(series) else None
            if len(series) > 1:
                half = stats.t.ppf(0.975, len(series) - 1) * series.std(ddof=1)
                row[metric + "_ci"] = half / len(series) ** 0.5
            else:
                row[metric + "_ci"] = None
        rows.append(row)
    return pd.DataFrame(rows)


def layout_geometry(layout: WarehouseLayout) -> dict:
    """Size of a layout and how far its racks are from the stations.

    ``rack_to_station_cells`` is the mean shortest drive, in cells, from a
    rack slot to the nearest picking station along aisles (racks, stations
    and chargers are obstacles). It tells whether a layout is quicker
    because of its traffic or simply because its racks are closer.
    """
    obstacles = (
        set(layout.racks.values())
        | set(layout.stations.values())
        | set(layout.chargers.values())
    )
    from_station = []
    for station in layout.stations.values():
        dist = {station: 0}
        queue = deque([station])
        while queue:
            cell = queue.popleft()
            for nxt in layout.neighbors(cell):
                if nxt in dist or nxt in layout.blocked or nxt in obstacles:
                    continue
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
        from_station.append(dist)
    nearest = []
    for rack in layout.racks.values():
        reach = [
            d[cell] + 1
            for d in from_station
            for cell in layout.neighbors(rack)
            if cell in d
        ]
        nearest.append(min(reach))
    return {
        "racks": len(layout.racks),
        "stations": len(layout.stations),
        "floor_cells": len(layout.floor),
        "rack_to_station_cells": sum(nearest) / len(nearest),
        "rack_to_station_max": max(nearest),
    }
