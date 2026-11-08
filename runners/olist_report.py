"""Print a summary of the Olist data used to calibrate the simulation.

Usage (from the repository root):

    uv run runners/olist_report.py

Needs the raw files in data/raw/ (``uv run data/download_olist.py``).
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import olist  # noqa: E402

YEARS = (2017, 2018)
TOP = 10


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def year_report(table: pd.DataFrame, year: int) -> olist.OlistStats:
    data = olist.year(table, year)
    stats = olist.compute_stats(data)
    days = stats.daily_counts

    section(f"{year}: overview")
    print(f"orders:            {data['order_id'].nunique()}")
    print(f"order lines:       {len(data)}")
    print(f"products:          {len(stats.product_popularity)}")
    print(f"first / last day:  {days.index.min().date()} / {days.index.max().date()}")
    print(f"orders per day:    mean {days.mean():.1f}, max {days.max()}")

    section(f"{year}: different products per order (share of orders)")
    print(stats.items_per_order.head(TOP).round(4).to_string())

    section(f"{year}: units per order line (share of lines)")
    print(stats.quantity_per_line.head(TOP).round(4).to_string())

    section(f"{year}: mean orders per hour on a normal day (rows: 0 = Monday, columns: hour)")
    print("exceptional days left out:", ", ".join(str(d.date()) for d in sorted(olist.EXCEPTIONAL_DAYS)))
    print(stats.arrival_profile.round(1).to_string())

    section(f"{year}: busiest days")
    print(days.sort_values(ascending=False).head(TOP).to_string())

    section(f"{year}: most popular products")
    print(stats.product_popularity.head(TOP).round(4).to_string())
    top_share = stats.product_popularity["order_share"].head(TOP).sum()
    print(f"top {TOP} products are in {top_share:.1%} of orders")

    return stats


def compare_popularity_measures(stats: olist.OlistStats, year: int) -> None:
    popularity = stats.product_popularity
    by_orders = popularity["orders"].rank(ascending=False)
    by_units = popularity["units"].rank(ascending=False)
    top_orders = set(popularity.head(100).index)
    top_units = set(popularity.sort_values("units", ascending=False).head(100).index)

    section(f"{year}: popularity by orders vs by units")
    print(f"rank correlation:   {by_orders.corr(by_units):.3f}")
    print(f"top 100 in common:  {len(top_orders & top_units)}")


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    table = olist.load_orders()
    for year in YEARS:
        stats = year_report(table, year)
        compare_popularity_measures(stats, year)


if __name__ == "__main__":
    main()
