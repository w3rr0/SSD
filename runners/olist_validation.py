"""Validate the Olist order generator on 2018.

The generator is calibrated on 2017 and generates as many days as the 2018
data covers. The same statistics are then computed for the generated orders
and for the real 2018 orders and compared as shares (percent). Volume is
compared separately: Olist grew between the years, so absolute counts are
expected to differ; ``volume_factor`` handles that in scenarios.

A comparison passes when no share differs by more than THRESHOLD_PP
percentage points.

Usage (from the repository root):

    uv run runners/olist_validation.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import olist  # noqa: E402
from src.orders.models import Order  # noqa: E402
from src.orders.olist_generator import generate_orders  # noqa: E402

CALIBRATION_YEAR = 2017
VALIDATION_YEAR = 2018
THRESHOLD_PP = 2.0
SEED = 2018
TOP_PRODUCTS = (10, 100, 1000)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def orders_to_table(orders: list[Order], start: pd.Timestamp) -> pd.DataFrame:
    """Generated orders in the same shape as ``olist.load_orders`` (no deadline)."""
    rows = [
        (order.order_id, line.sku, line.quantity, order.created_time)
        for order in orders
        for line in order.lines
    ]
    table = pd.DataFrame(rows, columns=["order_id", "product_id", "quantity", "offset_s"])
    table["purchase_time"] = start + pd.to_timedelta(table["offset_s"], unit="s")
    table["date"] = table["purchase_time"].dt.normalize()
    table["weekday"] = table["purchase_time"].dt.weekday
    table["hour"] = table["purchase_time"].dt.hour
    return table.drop(columns="offset_s")


def order_share_by(table: pd.DataFrame, column: str) -> pd.Series:
    """Share of orders by an order-level column such as hour or weekday."""
    orders = table.drop_duplicates("order_id")
    return orders[column].value_counts(normalize=True).sort_index()


def concentration(table: pd.DataFrame) -> pd.Series:
    """Share of orders containing at least one of the N most popular products.

    A fixed N, not a percentage of products: the number of different
    products seen grows with the number of orders, so "top 1%" would be a
    different group in a smaller sample.
    """
    popularity = olist.product_popularity(table)
    shares = {}
    for count in TOP_PRODUCTS:
        top = popularity.index[:count]
        covered = table.loc[table["product_id"].isin(top), "order_id"].nunique()
        shares[f"top {count}"] = covered / table["order_id"].nunique()
    return pd.Series(shares)


def compare(title: str, real: pd.Series, generated: pd.Series) -> bool:
    """Print both distributions in percent and whether they agree."""
    frame = pd.DataFrame({"real %": real, "generated %": generated}).fillna(0.0) * 100
    frame.index.name = None
    frame["diff pp"] = frame["generated %"] - frame["real %"]
    worst = frame["diff pp"].abs().max()
    passed = worst <= THRESHOLD_PP
    print(f"\n=== {title} ===")
    print(frame.round(2).to_string())
    print(f"largest difference: {worst:.2f} pp -> {'OK' if passed else 'NOT OK'}")
    return passed


def main() -> None:
    pd.set_option("display.width", 200)
    table = olist.load_orders()
    calibration = olist.year(table, CALIBRATION_YEAR)
    real = olist.year(table, VALIDATION_YEAR)
    stats = olist.compute_stats(calibration)

    real_days = olist.daily_counts(real)
    start = real_days.index.min()
    days = len(real_days)
    orders = generate_orders(
        stats, np.random.default_rng(SEED), start, days * 86400.0
    )
    generated = orders_to_table(orders, start)

    print(f"calibrated on {CALIBRATION_YEAR}, validated on {VALIDATION_YEAR}")
    print(f"period: {start.date()} .. {real_days.index.max().date()} ({days} days)")
    print(f"threshold: {THRESHOLD_PP} percentage points, seed {SEED}")

    hours_real = order_share_by(real, "hour")
    hours_gen = order_share_by(generated, "hour")
    days_real = order_share_by(real, "weekday").rename(dict(enumerate(WEEKDAYS)))
    days_gen = order_share_by(generated, "weekday").rename(dict(enumerate(WEEKDAYS)))

    results = {
        "different products per order": compare(
            "different products per order (share of orders)",
            olist.items_per_order(real),
            olist.items_per_order(generated),
        ),
        "units per line": compare(
            "units per order line (share of lines)",
            olist.quantity_per_line(real),
            olist.quantity_per_line(generated),
        ),
        "hour of day": compare(
            "hour of day (share of orders)", hours_real, hours_gen
        ),
        "weekday": compare("weekday (share of orders)", days_real, days_gen),
        "popularity concentration": compare(
            "orders containing a top N product (share of orders)",
            concentration(real),
            concentration(generated),
        ),
    }

    calibration_per_day = olist.daily_counts(calibration).mean()
    real_per_day = real_days.mean()
    generated_per_day = len(orders) / days
    print("\n=== volume (compared separately) ===")
    print(f"{CALIBRATION_YEAR} real:      {calibration_per_day:.1f} orders/day")
    print(f"{VALIDATION_YEAR} real:      {real_per_day:.1f} orders/day")
    print(f"{VALIDATION_YEAR} generated: {generated_per_day:.1f} orders/day")
    print(f"growth {VALIDATION_YEAR}/{CALIBRATION_YEAR}: x{real_per_day / calibration_per_day:.2f}")

    print("\n=== summary ===")
    for name, passed in results.items():
        print(f"{'OK    ' if passed else 'NOT OK'} {name}")


if __name__ == "__main__":
    main()
