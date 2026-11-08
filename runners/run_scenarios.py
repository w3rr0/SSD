"""Run the project scenarios with replications and save the results.

Usage (from the repository root)::

    uv run runners/run_scenarios.py                    # all groups, 10 seeds
    uv run runners/run_scenarios.py --group S1 --seeds 20 --jobs 4

Results go to ``output/scenarios/``:

* ``runs.csv``    one row per run (scenario, seed, status, metrics),
* ``summary.csv`` one row per scenario, mean and 95% half-width (``*_ci``),
* ``summary.md``  the main metrics as a Markdown table.

Runs already in ``runs.csv`` (same scenario and seed) are skipped, so an
interrupted batch can be resumed by running the same command again.
Decisions behind the setup: ``docs/decyzje_dane_olist.md``, section 9.
"""

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.data import olist  # noqa: E402
from src.experiments.scenarios import (  # noqa: E402
    GROUPS,
    Scenario,
    run_one,
    scenarios,
    summarise,
)

OUT_DIR = ROOT / "output" / "scenarios"
_STATS = None


def _init_worker() -> None:
    """Each process loads the Olist statistics once."""
    global _STATS
    _STATS = olist.compute_stats(olist.year(olist.load_orders(), 2017))


def _run(scenario: Scenario, seed: int) -> dict:
    return run_one(scenario, seed, _STATS)


def _markdown(summary: pd.DataFrame) -> str:
    def cell(row, metric, digits=1):
        mean, half = row[metric], row[f"{metric}_ci"]
        if pd.isna(mean):
            return "-"
        return f"{mean:.{digits}f}" + ("" if pd.isna(half) else f" ± {half:.{digits}f}")

    lines = [
        "| Grupa | Dzień | Roboty | Rozmieszczenie | Powrót | Stan. | Ład. | Prędkość | Linie/h | Bateria h | Przydział | Udane | Śr. czas [s] | Maks. czas [s] | Zam./h | Korki [s/robot] | Kolejka [s] | Wyk. stanowisk |",
        "|" + " --- |" * 18,
    ]
    for _, r in summary.iterrows():
        flag = " ⚠" if r["unreliable"] else ""
        lines.append(
            f"| {r['group']} | {r['day']} | {r['robots']} | {r['placement']} | "
            f"{r['return_policy']} | {r['stations']} | {r['chargers']} | "
            f"{r['speed_m_per_s']} | {r['lines_per_hour']:g} | {r['battery_hours']:g} | "
            f"{r['assignment']} | {r['ok']}/{r['runs']}{flag} | "
            f"{cell(r, 'average_completion_time')} | {cell(r, 'longest_completion_time')} | "
            f"{cell(r, 'orders_per_hour_day')} | {cell(r, 'average_traffic_wait_s')} | "
            f"{cell(r, 'average_station_wait')} | {cell(r, 'station_utilisation_mean', 2)} |"
        )
    lines.append("")
    lines.append("⚠ = ponad 10% przebiegów nieudanych (zakleszczenie albo limit czasu).")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--group", nargs="+", choices=sorted(GROUPS), default=None)
    parser.add_argument("--seeds", type=int, default=10, help="seeds 1..N")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    runs_path = args.out / "runs.csv"
    existing = pd.read_csv(runs_path) if runs_path.exists() else pd.DataFrame()
    done = set()
    if not existing.empty:
        done = set(zip(existing["scenario"], existing["seed"]))

    todo = [
        (scenario, seed)
        for scenario in scenarios(args.group)
        for seed in range(1, args.seeds + 1)
        if (scenario.key, seed) not in done
    ]
    print(f"{len(todo)} runs to do, {len(done)} already saved in {runs_path}")

    rows = existing.to_dict("records")
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=_init_worker) as pool:
        futures = [pool.submit(_run, scenario, seed) for scenario, seed in todo]
        for number, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            # Saved after every run, so nothing is lost if the batch stops.
            pd.DataFrame(rows).to_csv(runs_path, index=False)
            print(f"[{number}/{len(todo)}] {row['status']:6} seed {row['seed']} {row['scenario']}")

    if not rows:
        return
    summary = summarise(pd.DataFrame(rows))
    summary.to_csv(args.out / "summary.csv", index=False)
    (args.out / "summary.md").write_text(_markdown(summary), encoding="utf-8")
    print(f"Summary: {args.out / 'summary.md'}")


if __name__ == "__main__":
    main()
