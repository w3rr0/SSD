"""Reproducible baseline for comparing Person 1 stages.

Usage::

    uv run runners/run_baseline.py
    uv run runners/run_baseline.py --robots 5 --orders 40 --seed 42

The script prints the current ``SimulationMetrics`` as JSON. Run it before
and after each stage; the same seed and parameters make the numbers directly
comparable. It is intentionally not a test: stages are expected to change the
results, not to preserve exact values.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.model import Warehouse  # noqa: E402
from src.pipeline.reservations import DeadlockError  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robots", type=int, default=5)
    parser.add_argument("--orders", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-time", type=float, default=36_000.0)
    args = parser.parse_args()

    model = Warehouse(
        num_robots=args.robots,
        num_orders=args.orders,
        rng=args.seed,
    )
    try:
        metrics = model.run_until_complete(max_time=args.max_time)
    except (DeadlockError, TimeoutError) as error:
        print(f"baseline did not finish: {error}")
        metrics = model.metrics
    print(json.dumps(asdict(metrics), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
