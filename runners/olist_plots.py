"""Plot the Olist data and the generator validation as PNG files.

Usage (from the repository root):

    uv run runners/olist_plots.py

The plots are written to output/olist/ (ignored by git).
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # files only, no window

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runners.olist_validation import (  # noqa: E402
    CALIBRATION_YEAR,
    SEED,
    VALIDATION_YEAR,
    order_share_by,
    orders_to_table,
)
from src.data import olist  # noqa: E402
from src.orders.olist_generator import generate_orders  # noqa: E402

OUT_DIR = ROOT / "output" / "olist"

REAL = "#2a78d6"  # blue: real data
GENERATED = "#eb6834"  # orange: generator
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

REAL_LABEL = f"prawdziwe {VALIDATION_YEAR}"
GEN_LABEL = f"generator (z {CALIBRATION_YEAR})"
EXAMPLE_DAY = pd.Timestamp("2018-03-06")  # an ordinary Tuesday
DAY_NAMES = ["pn", "wt", "śr", "czw", "pt", "sob", "ndz"]
PLAIN_NUMBER = FuncFormatter(lambda value, _: f"{value:g}")  # 100, not 10^2


def style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK_SECONDARY,
            "axes.titlecolor": INK,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": INK_SECONDARY,
            "ytick.color": INK_SECONDARY,
            "legend.frameon": False,
            "font.size": 10,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    path = OUT_DIR / name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"saved {path.relative_to(ROOT)}")


def paired_bars(ax, labels, real, generated) -> None:
    """Real and generated shares side by side for each category."""
    x = np.arange(len(labels))
    width = 0.38
    ax.bar(x - width / 2 - 0.01, real, width, color=REAL, label=REAL_LABEL)
    ax.bar(x + width / 2 + 0.01, generated, width, color=GENERATED, label=GEN_LABEL)
    ax.set_xticks(x, labels)
    ax.grid(axis="x", visible=False)
    ax.legend()


def plot_hours(real, generated) -> None:
    hours = range(24)
    r = order_share_by(real, "hour").reindex(hours, fill_value=0) * 100
    g = order_share_by(generated, "hour").reindex(hours, fill_value=0) * 100
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(hours, r, color=REAL, lw=2, marker="o", ms=4, label=REAL_LABEL)
    ax.plot(hours, g, color=GENERATED, lw=2, marker="o", ms=4, label=GEN_LABEL)
    ax.set_title("Zamówienia w ciągu doby")
    ax.set_xlabel("godzina")
    ax.set_ylabel("% zamówień dnia")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    save(fig, "1_godziny_doby.png")


def plot_weekdays(real, generated) -> None:
    r = order_share_by(real, "weekday").reindex(range(7), fill_value=0) * 100
    g = order_share_by(generated, "weekday").reindex(range(7), fill_value=0) * 100
    fig, ax = plt.subplots(figsize=(8, 4.5))
    paired_bars(ax, DAY_NAMES, r, g)
    ax.set_title("Zamówienia w ciągu tygodnia")
    ax.set_ylabel("% zamówień tygodnia")
    save(fig, "2_dni_tygodnia.png")


def plot_items_per_order(real, generated) -> None:
    def grouped(table):
        shares = olist.items_per_order(table)
        return pd.Series(
            {
                "1": shares.get(1, 0.0),
                "2": shares.get(2, 0.0),
                "3": shares.get(3, 0.0),
                "4+": shares[shares.index >= 4].sum(),
            }
        ) * 100

    r, g = grouped(real), grouped(generated)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    paired_bars(ax, list(r.index), r, g)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(PLAIN_NUMBER)
    ax.set_title("Liczba różnych produktów w zamówieniu")
    ax.set_xlabel("produktów w zamówieniu")
    ax.set_ylabel("% zamówień (skala logarytmiczna)")
    for i, (a, b) in enumerate(zip(r, g)):
        ax.annotate(f"{a:.2f}%", (i - 0.2, a), ha="center", va="bottom",
                    fontsize=8, color=INK_SECONDARY, xytext=(0, 2),
                    textcoords="offset points")
        ax.annotate(f"{b:.2f}%", (i + 0.2, b), ha="center", va="bottom",
                    fontsize=8, color=INK_SECONDARY, xytext=(0, 2),
                    textcoords="offset points")
    save(fig, "3_produkty_w_zamowieniu.png")


def coverage_curve(table: pd.DataFrame) -> pd.Series:
    """Share of orders containing one of the top N products, for every N."""
    ranking = olist.product_popularity(table).index
    rank = pd.Series(np.arange(1, len(ranking) + 1), index=ranking)
    best_rank = table["product_id"].map(rank).groupby(table["order_id"]).min()
    counts = best_rank.value_counts().sort_index().cumsum()
    return counts / table["order_id"].nunique() * 100


def plot_popularity(real, generated) -> None:
    r, g = coverage_curve(real), coverage_curve(generated)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(r.index, r, color=REAL, lw=2, label=REAL_LABEL)
    ax.plot(g.index, g, color=GENERATED, lw=2, label=GEN_LABEL)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(PLAIN_NUMBER)
    for n in (10, 100, 1000):
        ax.axvline(n, color=GRID, lw=1, zorder=0)
    ax.set_title("Koncentracja popularności produktów")
    ax.set_xlabel("N najpopularniejszych produktów (skala logarytmiczna)")
    ax.set_ylabel("% zamówień z produktem z top N")
    ax.legend(loc="upper left")
    save(fig, "4_popularnosc.png")


def plot_daily(table: pd.DataFrame) -> None:
    days = olist.daily_counts(table[table["year"].isin([CALIBRATION_YEAR, VALIDATION_YEAR])])
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(days.index, days, color=REAL, lw=1)
    for day in sorted(olist.EXCEPTIONAL_DAYS):
        ax.annotate(
            f"Black Friday {day.date()}: {days[day]} zamówień\n(pominięty w profilu zwykłego dnia)",
            (day, days[day]), xytext=(-12, -4), textcoords="offset points",
            ha="right", va="top", fontsize=9, color=INK_SECONDARY,
        )
    ax.set_title(f"Zamówienia dziennie, {CALIBRATION_YEAR}–{VALIDATION_YEAR}")
    ax.set_ylabel("zamówień na dzień")
    ax.grid(axis="x", visible=False)
    save(fig, "5_zamowienia_dziennie.png")


def plot_example_day(stats: olist.OlistStats) -> None:
    orders = generate_orders(stats, np.random.default_rng(SEED), EXAMPLE_DAY, 86400.0)
    per_hour = (
        pd.Series([int(o.created_time // 3600) for o in orders])
        .value_counts()
        .reindex(range(24), fill_value=0)
    )
    expected = stats.arrival_profile.loc[EXAMPLE_DAY.weekday()]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(per_hour.index, per_hour, 0.8, color=GENERATED,
           label=f"wylosowane ({len(orders)} zamówień)")
    ax.plot(expected.index, expected, color=INK, lw=2, marker="o", ms=4,
            label="średnia z profilu (λ)")
    ax.set_title(
        f"Jeden wygenerowany dzień: {DAY_NAMES[EXAMPLE_DAY.weekday()]} {EXAMPLE_DAY.date()}"
    )
    ax.set_xlabel("godzina")
    ax.set_ylabel("zamówień w godzinie")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(axis="x", visible=False)
    ax.legend()
    save(fig, "6_przykladowy_dzien.png")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    style()
    table = olist.load_orders()
    calibration = olist.year(table, CALIBRATION_YEAR)
    real = olist.year(table, VALIDATION_YEAR)
    stats = olist.compute_stats(calibration)

    real_days = olist.daily_counts(real)
    start = real_days.index.min()
    orders = generate_orders(
        stats, np.random.default_rng(SEED), start, len(real_days) * 86400.0
    )
    generated = orders_to_table(orders, start)

    plot_hours(real, generated)
    plot_weekdays(real, generated)
    plot_items_per_order(real, generated)
    plot_popularity(real, generated)
    plot_daily(table)
    plot_example_day(stats)


if __name__ == "__main__":
    main()
