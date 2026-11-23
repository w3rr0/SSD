"""Queueing validation, part B: the whole warehouse with one station.

Orders of one unit of one product arrive as a Poisson process with a
constant rate. Robots fetch the racks and bring them to the single picking
station, so the station sees robot arrivals shaped by driving, not by us.
The mean wait in the station queue is compared with the M/G/1 formula
(Pollaczek-Khinchine) for several utilisations and both service-time
distributions.

Each setting is run REPLICATIONS times with different seeds; the start of
every run (an empty warehouse) is left out. The result agrees when the
formula lies inside the 95% confidence interval of the mean.

A busy station needs much longer runs: its queue takes long to build up
from empty and swings widely, so short runs underestimate the wait. Run
lengths therefore grow with the utilisation (RUN_LENGTHS). Runs are spread
over all CPU cores.

A run that ends in a deadlock or livelock does not stop the batch: it is
counted as failed and left out of the mean, as in the scenario runner.

Result codes:

* ``OK`` / ``NOT OK``: the formula lies inside / outside the 95% interval;
* ``LIMIT``: the station reached clearly less than the target utilisation.
  The traffic rules let only ``station_queue_limit`` robots bring racks to a
  station at once, so the rest wait under their racks and the station is
  not an M/G/1 queue any more; the comparison is not meaningful there.
* ``⚠`` after the code: more than 10% of the runs failed.

Part A (the station alone, Poisson arrivals, no driving) is checked in
``tests/test_queueing.py``. Why part B differs under the traffic rules is
explained in ``docs/decyzje_dane_olist.md`` (queueing validation section).

Usage (from the repository root):

    uv run runners/queue_validation.py
"""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import PickingParams, SimulationConfig  # noqa: E402
from src.core.model import Warehouse  # noqa: E402
from src.environment.layout import WarehouseLayout  # noqa: E402
from src.orders.models import Order, OrderLine  # noqa: E402
from src.pipeline.reservations import DeadlockError  # noqa: E402
from src.validation.queueing import (  # noqa: E402
    arrival_rate_for,
    confidence_interval,
    mg1_wait,
    service_moments,
)

UTILISATIONS = (0.3, 0.5, 0.7, 0.9)
DISTRIBUTIONS = ("deterministic", "exponential")
REPLICATIONS = 20
# utilisation -> (warm-up left out, measured time), in seconds
RUN_LENGTHS = {
    0.3: (2_000.0, 20_000.0),
    0.5: (2_000.0, 20_000.0),
    0.7: (5_000.0, 40_000.0),
    0.9: (10_000.0, 80_000.0),
}
NUM_ROBOTS = 40
PICKING = dict(fixed_s=5.0, per_item_s=10.0)  # the model's defaults
# The station counts as not keeping up below target utilisation - this.
UTILISATION_TOLERANCE = 0.05
UNRELIABLE_FAILED_SHARE = 0.10


def make_layout() -> WarehouseLayout:
    """160 racks in 4 x 4 blocks, one station, no chargers."""
    return WarehouseLayout.generate(
        block_columns=4,
        block_rows=4,
        block_length=5,
        block_depth=2,
        num_stations=1,
        num_chargers=0,
        num_robots=NUM_ROBOTS,
    )


def poisson_orders(
    rng: np.random.Generator, rate: float, until: float, skus: list[str]
) -> list[Order]:
    """One unit of a uniformly chosen product per order, Poisson arrivals."""
    orders = []
    time = 0.0
    while True:
        time += float(rng.exponential(1 / rate))
        if time >= until:
            return orders
        sku = skus[int(rng.integers(len(skus)))]
        orders.append(Order(f"order-{len(orders) + 1}", (OrderLine(sku),), created_time=time))


def run_once(
    distribution: str, utilisation: float, seed: int
) -> dict[str, float]:
    """Mean station wait (and diagnostics) of one run after the warm-up."""
    picking = PickingParams(**PICKING, distribution=distribution)
    mean_s, _ = service_moments(picking, items=1)
    rate = arrival_rate_for(utilisation, mean_s)
    warm_up, measured_s = RUN_LENGTHS[utilisation]

    layout = make_layout()
    rng = np.random.default_rng(seed)
    skus = ["sku-" + rack_id.removeprefix("rack-") for rack_id in layout.racks]
    orders = poisson_orders(rng, rate, warm_up + measured_s, skus)
    model = Warehouse(
        layout=layout,
        num_robots=NUM_ROBOTS,
        orders=orders,
        config=SimulationConfig(picking=picking),
        rng=seed,
    )
    station = next(iter(model.stations.values()))

    model.run_until(warm_up)
    first = len(station.wait_times)
    busy_before = station.busy_time()
    model.run_until(warm_up + measured_s)

    waits = station.wait_times[first:]
    robot_waits = [
        o.waiting_time
        for o in orders
        if warm_up <= o.created_time and o.waiting_time is not None
    ]
    return {
        "wait": sum(waits) / len(waits),
        "utilisation": (station.busy_time() - busy_before) / measured_s,
        "wait_for_robot": sum(robot_waits) / len(robot_waits),
    }


def _run(args: tuple[str, float, int]) -> dict[str, float] | None:
    """One run, or None when it ends in a deadlock or livelock."""
    try:
        return run_once(*args)
    except DeadlockError:
        return None


def summarise(
    distribution: str, utilisation: float, runs: list[dict[str, float] | None]
) -> dict[str, object]:
    """One table row: formula, mean wait of the successful runs, result code."""
    picking = PickingParams(**PICKING, distribution=distribution)
    mean_s, second = service_moments(picking, items=1)
    expected = mg1_wait(arrival_rate_for(utilisation, mean_s), mean_s, second)
    ok = [run for run in runs if run is not None]
    failed = len(runs) - len(ok)
    row: dict[str, object] = {
        "distribution": distribution,
        "utilisation": utilisation,
        "expected": expected,
        "runs": len(runs),
        "failed": failed,
        "unreliable": bool(runs) and failed / len(runs) > UNRELIABLE_FAILED_SHARE,
    }
    if len(ok) < 2:
        row.update(centre=None, half=None, measured_rho=None, robot_wait=None,
                   result="NO DATA")
        return row
    centre, half = confidence_interval([run["wait"] for run in ok])
    measured_rho = float(np.mean([run["utilisation"] for run in ok]))
    if measured_rho < utilisation - UTILISATION_TOLERANCE:
        result = "LIMIT"
    elif abs(centre - expected) <= half:
        result = "OK"
    else:
        result = "NOT OK"
    row.update(
        centre=centre,
        half=half,
        measured_rho=measured_rho,
        robot_wait=float(np.mean([run["wait_for_robot"] for run in ok])),
        result=result,
    )
    return row


def _format(row: dict[str, object]) -> str:
    flag = " ⚠" if row["unreliable"] else ""
    start = (
        f"{row['distribution']:<14}{row['utilisation']:>5.1f}"
        f"{row['expected']:>11.1f}"
    )
    done = f"{row['runs'] - row['failed']}/{row['runs']}"
    if row["centre"] is None:
        return f"{start}{'-':>17}{'-':>11}{'-':>14}{done:>8}  {row['result']}{flag}"
    return (
        f"{start}{row['centre']:>10.1f} ± {row['half']:<4.1f}"
        f"{row['measured_rho']:>11.2f}{row['robot_wait']:>14.1f}{done:>8}"
        f"  {row['result']}{flag}"
    )


def main() -> None:
    settings = [(d, u) for d in DISTRIBUTIONS for u in UTILISATIONS]
    jobs = [(d, u, seed) for d, u in settings for seed in range(REPLICATIONS)]
    print(
        f"{len(make_layout().racks)} racks, 1 station, {NUM_ROBOTS} robots; "
        f"{REPLICATIONS} runs per setting, {len(jobs)} runs in total"
    )
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(_run, jobs))

    header = (
        f"{'service':<14}{'rho':>5}{'formula s':>11}{'simulated s':>17}"
        f"{'rho meas.':>11}{'robot wait s':>14}{'ok runs':>8}  result"
    )
    print(header)
    print("-" * len(header))
    for index, (distribution, utilisation) in enumerate(settings):
        runs = results[index * REPLICATIONS : (index + 1) * REPLICATIONS]
        print(_format(summarise(distribution, utilisation, runs)))
    print(
        "\nLIMIT = the station stayed clearly below the target utilisation "
        "(station_queue_limit), so M/G/1 does not apply. "
        "⚠ = more than 10% of runs failed."
    )


if __name__ == "__main__":
    main()
