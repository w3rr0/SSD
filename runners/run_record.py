"""Run one configured warehouse and record its live data to CSV/JSON.

Usage (from the repository root):

    uv run runners/run_record.py --placement random --seed 1 --hours 4
    uv run runners/run_record.py --layout hala_L --num-robots 12 --orders demo

The parameters are the same as the visualisation sidebar. Results are written
to ``output/runs/<run_id>/`` (ignored by git).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiments.build import make_warehouse  # noqa: E402
from src.experiments.record import run_and_record  # noqa: E402

OUT_ROOT = ROOT / "output" / "runs"


def run_id_of(params: dict) -> str:
    """A short, file-safe name summarising the run's key parameters."""
    return "_".join(
        f"{key}={params[key]}"
        for key in (
            "layout",
            "num_robots",
            "orders",
            "placement",
            "return_policy",
            "volume",
            "hours",
            "seed",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--layout", default="kiva_standard")
    parser.add_argument("--num-robots", type=int, default=8)
    parser.add_argument("--orders", choices=["olist", "demo"], default="olist")
    parser.add_argument("--placement", choices=["random", "ABC"], default="random")
    parser.add_argument("--return-policy", choices=["home", "nearest"], default="home")
    parser.add_argument("--volume", type=float, default=1.0)
    parser.add_argument("--hours", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--duration", type=float, default=None,
                        help="Simulated seconds; default = hours * 3600")
    parser.add_argument("--sample-every", type=float, default=10.0,
                        help="Record a snapshot every this many seconds")
    parser.add_argument("--warm-up", type=float, default=0.0,
                        help="Simulated seconds to run before recording")
    parser.add_argument("--out", default=None,
                        help="Output directory; default = output/runs/<run-id>")
    args = parser.parse_args()

    params = {
        "layout": args.layout,
        "num_robots": args.num_robots,
        "orders": args.orders,
        "placement": args.placement,
        "return_policy": args.return_policy,
        "volume": args.volume,
        "hours": args.hours,
        "seed": args.seed,
    }
    run_id = run_id_of(params)
    duration = args.duration if args.duration is not None else args.hours * 3600
    out_dir = (Path(args.out) if args.out else OUT_ROOT / run_id).resolve()

    recorded = run_and_record(
        factory=lambda: make_warehouse(**params),
        duration=duration,
        sample_every=args.sample_every,
        warm_up=args.warm_up,
        run_id=run_id,
        params=params,
    )
    recorded.write_outputs(out_dir)

    metrics = recorded.metrics
    print(f"run_id       {run_id}")
    print(f"status       {recorded.status}"
          + (f" ({recorded.stop_reason})" if recorded.stop_reason else ""))
    print(f"wall time    {recorded.wall_s:.1f} s")
    print(f"simulated    {metrics.simulated_time:.0f} s")
    print(f"completed    {metrics.completed_orders}")
    print(f"avg complet. {metrics.average_completion_time}")
    print(f"avg waiting  {metrics.average_waiting_time}")
    print(f"saved        {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
