"""Scenarios of the project: replicated simulation days on Olist orders.

The reasoning behind every choice here (load scale, Monday, a whole day,
common random numbers, how failed runs count) is in
``docs/decyzje_dane_olist.md``, section 9.

One run = one scenario + one seed = one simulated Monday:

* orders from the Olist generator, profile x ``volume_factor``,
* products placed randomly or by ABC, racks returned home or to the
  nearest free slot,
* the model runs until every order is done, at most ``DRAIN_LIMIT_S``
  after midnight.

A run ends with status ``ok``, ``failed`` (deadlock or time limit) or
``error`` (any other exception, i.e. a bug).
"""

import math
import time
from dataclasses import asdict, dataclass, fields, replace
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from src.core.config import (
    SECONDS_PER_HOUR,
    AssignmentParams,
    PickingParams,
    RobotParams,
    SimulationConfig,
)
from src.core.model import Warehouse
from src.data.olist import OlistStats
from src.environment.layout import WarehouseLayout
from src.orders.olist_generator import generate_orders
from src.pipeline.reservations import DeadlockError
from src.strategies.placement import NearestFreeSlot, abc_placement, random_placement
from src.validation.queueing import confidence_interval

# Load scale (option B): an ordinary day is the Olist profile x BASE_VOLUME,
# the peak is that x PEAK_MULTIPLIER (Black Friday 2017 vs an average day).
# BASE_VOLUME is the estimate from the plan; the pilot calibrates it.
BASE_VOLUME = 10.0
PEAK_MULTIPLIER = 9.5

DAY_START = pd.Timestamp("2018-03-05 00:00")  # a Monday, the busiest weekday
DAY_S = 24 * SECONDS_PER_HOUR
DRAIN_LIMIT_S = 2 * SECONDS_PER_HOUR  # time to finish orders after midnight
UNRELIABLE_FAILED_SHARE = 0.10

# Reference speed of the battery definition: "2 h of driving" means 2 h at
# 1.3 m/s, i.e. a fixed distance. Changing the speed keeps that distance.
REFERENCE_SPEED_M_PER_S = 1.3


@dataclass(frozen=True, slots=True)
class Scenario:
    """One configuration; every field not given keeps the reference value."""

    group: str
    day: Literal["normal", "peak"] = "normal"
    robots: int = 4
    placement: Literal["random", "ABC"] = "random"
    return_policy: Literal["home", "nearest"] = "home"
    stations: int = 2
    chargers: int = 2
    speed_m_per_s: float = 1.3
    lines_per_hour: float = 600.0
    battery_hours: float = 2.0
    assignment: Literal["nearest", "deadline_battery"] = "nearest"

    @property
    def key(self) -> str:
        """Stable text id, used to skip runs that are already saved."""
        return "|".join(f"{f.name}={getattr(self, f.name)}" for f in fields(self))

    @property
    def volume_factor(self) -> float:
        peak = PEAK_MULTIPLIER if self.day == "peak" else 1.0
        return BASE_VOLUME * peak

    def config(self) -> SimulationConfig:
        battery_m = self.battery_hours * SECONDS_PER_HOUR * REFERENCE_SPEED_M_PER_S
        return SimulationConfig(
            robot=RobotParams(
                speed_m_per_s=self.speed_m_per_s,
                battery_drain_pct_per_m=100.0 / battery_m,
            ),
            # One unit is one line (as in the robot parameters, section 8).
            picking=PickingParams(fixed_s=0.0, per_item_s=SECONDS_PER_HOUR / self.lines_per_hour),
            assignment=AssignmentParams(strategy=self.assignment),
        )


# Fleet sizes and the "knee" of S1 are placeholders until the pilot.
ROBOT_GRID = {"normal": (2, 4, 6, 8, 12), "peak": (8, 12, 16, 20, 24, 32)}
REFERENCE_ROBOTS = {"normal": 4, "peak": 16}
PLACEMENTS = (("random", "home"), ("ABC", "home"), ("random", "nearest"))


def _s1() -> list[Scenario]:
    """Robots x placement, on an ordinary day and at the peak (S1 + S2)."""
    return [
        Scenario("S1", day=day, robots=robots, placement=placement, return_policy=policy)
        for day, grid in ROBOT_GRID.items()
        for placement, policy in PLACEMENTS
        for robots in grid
    ]


def _s3() -> list[Scenario]:
    """Stations and chargers, one at a time, at the peak."""
    base = Scenario("S3", day="peak", robots=REFERENCE_ROBOTS["peak"])
    return (
        [base]
        + [replace(base, stations=n) for n in (1, 3, 4)]
        + [replace(base, chargers=n) for n in (1, 3, 4)]
    )


def _s5() -> list[Scenario]:
    """Robot parameters, one at a time around the reference, on both days."""
    out = []
    for day, robots in REFERENCE_ROBOTS.items():
        base = Scenario("S5", day=day, robots=robots)
        out.append(base)
        out += [replace(base, speed_m_per_s=v) for v in (1.0, 1.5)]
        out += [replace(base, lines_per_hour=v) for v in (200.0, 400.0, 700.0)]
        out += [replace(base, battery_hours=v) for v in (1.0, 4.0)]
    return out


def _s6() -> list[Scenario]:
    """Task assignment rules at the peak."""
    base = Scenario("S6", day="peak", robots=REFERENCE_ROBOTS["peak"])
    return [base, replace(base, assignment="deadline_battery")]


# S4 (failures vs urgent orders) waits for a definition of an urgent order.
GROUPS = {"S1": _s1, "S3": _s3, "S5": _s5, "S6": _s6}


def scenarios(groups=None) -> list[Scenario]:
    chosen = GROUPS if groups is None else {g: GROUPS[g] for g in groups}
    return [scenario for build in chosen.values() for scenario in build()]


def streams(seed: int) -> tuple[np.random.Generator, np.random.Generator, int]:
    """Independent random streams for orders, placement and the model.

    The same seed gives the same orders in every scenario (common random
    numbers), whatever the model does with its own stream.
    """
    orders, placement, model = np.random.SeedSequence(seed).spawn(3)
    return (
        np.random.default_rng(orders),
        np.random.default_rng(placement),
        int(model.generate_state(1)[0]),
    )


class ScenarioWarehouse(Warehouse):
    """The model with an optional nearest-free-slot return policy."""

    def __init__(self, *args, return_policy: str = "home", **kwargs):
        super().__init__(*args, **kwargs)
        self.nearest_free_slot = (
            NearestFreeSlot(self.layout) if return_policy == "nearest" else None
        )

    def return_location(self, rack):
        if self.nearest_free_slot is None:
            return super().return_location(rack)
        return self.nearest_free_slot.choose(self, rack)


def build_model(scenario: Scenario, seed: int, stats: OlistStats) -> ScenarioWarehouse:
    order_rng, placement_rng, model_seed = streams(seed)
    layout = WarehouseLayout.generate(
        num_stations=scenario.stations,
        num_chargers=scenario.chargers,
        num_robots=scenario.robots,
    )
    if scenario.placement == "ABC":
        rack_skus = abc_placement(stats.product_popularity, layout, placement_rng)
    else:
        products = list(stats.product_popularity.index)
        rack_skus = random_placement(products, layout, placement_rng)
    orders = generate_orders(
        stats, order_rng, DAY_START, DAY_S, volume_factor=scenario.volume_factor
    )
    return ScenarioWarehouse(
        layout=layout,
        num_robots=scenario.robots,
        orders=orders,
        rack_skus=rack_skus,
        config=scenario.config(),
        rng=model_seed,
        return_policy=scenario.return_policy,
    )


def _flatten(metrics) -> dict[str, object]:
    """Every metric field; per-station/charger dicts become mean and max."""
    row: dict[str, object] = {}
    for name, value in asdict(metrics).items():
        if isinstance(value, dict):
            values = list(value.values())
            row[f"{name}_mean"] = float(np.mean(values)) if values else None
            row[f"{name}_max"] = max(values) if values else None
        else:
            row[name] = value
    return row


def run_one(scenario: Scenario, seed: int, stats: OlistStats) -> dict[str, object]:
    """Simulate one day; never raises, the outcome is in ``status``."""
    started = time.perf_counter()
    status, error = "ok", ""
    model = build_model(scenario, seed, stats)
    try:
        model.run_until_complete(max_time=DAY_S + DRAIN_LIMIT_S)
    except (DeadlockError, TimeoutError) as exc:
        status, error = "failed", f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001 - a bug must not stop the batch
        status, error = "error", f"{type(exc).__name__}: {exc}"

    # Orders per hour are counted over the day itself, not over the drain.
    done_in_day = sum(
        1 for o in model.orders if o.completed_time is not None and o.completed_time <= DAY_S
    )
    return {
        "scenario": scenario.key,
        **asdict(scenario),
        "seed": seed,
        "status": status,
        "error": error,
        "wall_s": round(time.perf_counter() - started, 2),
        "orders_generated": len(model.orders),
        "completed_in_day": done_in_day,
        "unfinished_at_day_end": len(model.orders) - done_in_day,
        "orders_per_hour_day": done_in_day * SECONDS_PER_HOUR / DAY_S,
        **_flatten(model.metrics),
    }


SUMMARY_METRICS = (
    "average_completion_time",
    "longest_completion_time",
    "orders_per_hour_day",
    "unfinished_at_day_end",
    "average_traffic_wait_s",
    "average_station_wait",
    "station_utilisation_mean",
    "station_utilisation_max",
    "charger_utilisation_mean",
    "total_distance_m",
)


def summarise(runs: pd.DataFrame) -> pd.DataFrame:
    """One row per scenario: run counts and mean +- 95% half-width per metric.

    Only ``ok`` runs enter the means; the share of failed runs is reported
    next to them and marks a scenario as unreliable above 10%.
    """
    rows = []
    for key, group in runs.groupby("scenario", sort=False):
        ok = group[group["status"] == "ok"]
        failed_share = (group["status"] != "ok").mean()
        row = {
            "scenario": key,
            **{f.name: group.iloc[0][f.name] for f in fields(Scenario)},
            "runs": len(group),
            "ok": len(ok),
            "failed": int((group["status"] == "failed").sum()),
            "errors": int((group["status"] == "error").sum()),
            "unreliable": bool(failed_share > UNRELIABLE_FAILED_SHARE),
        }
        for metric in SUMMARY_METRICS:
            values = ok[metric].dropna().astype(float).tolist() if metric in ok else []
            mean, half = _interval(values)
            row[metric] = mean
            row[f"{metric}_ci"] = half
        rows.append(row)
    return pd.DataFrame(rows)


def _interval(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], None
    return confidence_interval(values)


def paired_difference(
    runs: pd.DataFrame, first: str, second: str, metric: str
) -> tuple[float | None, float | None, int]:
    """Mean of (first - second) over seeds that succeeded in both, its half-width, n."""
    ok = runs[runs["status"] == "ok"]
    a = ok[ok["scenario"] == first].set_index("seed")[metric]
    b = ok[ok["scenario"] == second].set_index("seed")[metric]
    diff = (a - b).dropna().astype(float).tolist()
    mean, half = _interval(diff)
    return mean, half, len(diff)


def replications_needed(values: list[float], relative_precision: float = 0.05) -> int:
    """n for a 95% half-width of ``relative_precision`` x mean, from a pilot."""
    n = len(values)
    if n < 2:
        raise ValueError("Need at least two pilot runs")
    mean = float(np.mean(values))
    if mean == 0:
        raise ValueError("Mean is zero; relative precision is undefined")
    t = scipy_stats.t.ppf(0.975, df=n - 1)
    return max(n, math.ceil((t * float(np.std(values, ddof=1)) / (relative_precision * mean)) ** 2))
