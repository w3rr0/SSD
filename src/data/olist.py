"""Order statistics from the Olist e-commerce dataset (Kaggle).

The simulation is calibrated on three things taken from Olist:

* how many different products an order contains (and how many units of each),
* when orders arrive (per weekday and hour, plus counts per calendar day),
* how popular each product is,
* how much time an order has until its shipping deadline.

Statistics are computed on one year (2017 for calibration, 2018 for
validation). Download the raw files with ``uv run data/download_olist.py``.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
ORDERS_FILE = "olist_orders_dataset.csv"
ITEMS_FILE = "olist_order_items_dataset.csv"

# Orders that never reached fulfilment; they often have no items at all.
SKIPPED_STATUSES = frozenset({"canceled", "unavailable"})

# Days with exceptional traffic, left out of the normal-day arrival profile.
# Peaks are simulated with the generator's ``volume_factor`` instead.
EXCEPTIONAL_DAYS = frozenset(
    {
        pd.Timestamp("2017-11-24"),  # Black Friday: 1166 orders, ~9.5x a mean day
    }
)


def load_orders(raw_dir: Path = DEFAULT_RAW_DIR) -> pd.DataFrame:
    """Load Olist orders as one row per (order, product) line.

    Columns:
        order_id, product_id
        quantity        units of this product in the order
        shipping_limit  earliest seller shipping deadline of the whole order
        purchase_time   when the customer placed the order (local Brazil time)
        date, year, weekday (0 = Monday), hour
    """
    orders = pd.read_csv(
        raw_dir / ORDERS_FILE,
        usecols=["order_id", "order_status", "order_purchase_timestamp"],
        parse_dates=["order_purchase_timestamp"],
    )
    items = pd.read_csv(
        raw_dir / ITEMS_FILE,
        usecols=["order_id", "product_id", "shipping_limit_date"],
        parse_dates=["shipping_limit_date"],
    )

    orders = orders[~orders["order_status"].isin(SKIPPED_STATUSES)]

    # Olist stores every unit as its own row; one line = one product + quantity.
    lines = (
        items.groupby(["order_id", "product_id"], as_index=False)
        .agg(quantity=("product_id", "size"))
    )
    # The order must be complete for the earliest of its sellers' deadlines.
    deadlines = (
        items.groupby("order_id", as_index=False)
        .agg(shipping_limit=("shipping_limit_date", "min"))
    )

    table = lines.merge(deadlines, on="order_id").merge(
        orders[["order_id", "order_purchase_timestamp"]], on="order_id"
    )
    table = table.rename(columns={"order_purchase_timestamp": "purchase_time"})
    table["date"] = table["purchase_time"].dt.normalize()
    table["year"] = table["purchase_time"].dt.year
    table["weekday"] = table["purchase_time"].dt.weekday
    table["hour"] = table["purchase_time"].dt.hour
    return table.sort_values(["purchase_time", "order_id", "product_id"]).reset_index(
        drop=True
    )


def year(table: pd.DataFrame, value: int) -> pd.DataFrame:
    """Only the orders placed in the given year."""
    return table[table["year"] == value].reset_index(drop=True)


def _one_row_per_order(table: pd.DataFrame) -> pd.DataFrame:
    return table.drop_duplicates("order_id")


def items_per_order(table: pd.DataFrame) -> pd.Series:
    """Share of orders by number of different products, e.g. {1: 0.9, 2: 0.08}."""
    counts = table.groupby("order_id")["product_id"].nunique()
    return counts.value_counts(normalize=True).sort_index().rename("share")


def quantity_per_line(table: pd.DataFrame) -> pd.Series:
    """Share of order lines by units of one product, e.g. {1: 0.95, 2: 0.04}."""
    return (
        table["quantity"].value_counts(normalize=True).sort_index().rename("share")
    )


def _calendar_days(table: pd.DataFrame) -> pd.DatetimeIndex:
    """Every calendar day from the first to the last order, including empty days."""
    return pd.date_range(table["date"].min(), table["date"].max(), freq="D")


def daily_counts(table: pd.DataFrame) -> pd.Series:
    """Orders per calendar day; days without orders count as 0."""
    counts = _one_row_per_order(table).groupby("date").size()
    return counts.reindex(_calendar_days(table), fill_value=0).rename("orders")


def arrival_profile(
    table: pd.DataFrame, skip_days: frozenset[pd.Timestamp] = EXCEPTIONAL_DAYS
) -> pd.DataFrame:
    """Mean orders per hour on a normal day, rows = weekday (0 = Monday), columns = hour 0-23.

    Each cell is the number of orders placed in that weekday-hour divided by
    how many such weekdays the period has (empty days included). Days in
    ``skip_days`` are left out of both counts.
    """
    orders = _one_row_per_order(table[~table["date"].isin(skip_days)])
    counts = (
        orders.groupby(["weekday", "hour"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=range(7), columns=range(24), fill_value=0)
    )
    calendar = _calendar_days(table)
    calendar = calendar[~calendar.isin(skip_days)]
    days_per_weekday = (
        pd.Series(calendar.weekday)
        .value_counts()
        .reindex(range(7), fill_value=0)
    )
    return counts.div(days_per_weekday.replace(0, pd.NA), axis=0).fillna(0.0)


def product_popularity(table: pd.DataFrame) -> pd.DataFrame:
    """Popularity of each product, most popular first.

    Columns:
        orders       number of orders containing the product (one rack trip each)
        order_share  orders / all orders  -> used for ABC
        units        units sold
        unit_share   units / all units    -> kept for comparison
    """
    total_orders = table["order_id"].nunique()
    total_units = table["quantity"].sum()
    popularity = table.groupby("product_id").agg(
        orders=("order_id", "nunique"),
        units=("quantity", "sum"),
    )
    popularity["order_share"] = popularity["orders"] / total_orders
    popularity["unit_share"] = popularity["units"] / total_units
    return popularity.sort_values(
        ["orders", "units"], ascending=False, kind="stable"
    )[["orders", "order_share", "units", "unit_share"]]


def lead_time(table: pd.DataFrame) -> pd.Series:
    """Seconds from purchase to the shipping deadline, one value per order.

    The generator draws due times from these values (empirical distribution).
    """
    orders = _one_row_per_order(table)
    seconds = (orders["shipping_limit"] - orders["purchase_time"]).dt.total_seconds()
    return seconds.reset_index(drop=True).rename("lead_time_s")


@dataclass(frozen=True)
class OlistStats:
    """All distributions the order generator needs, for one period."""

    items_per_order: pd.Series
    quantity_per_line: pd.Series
    arrival_profile: pd.DataFrame
    daily_counts: pd.Series
    product_popularity: pd.DataFrame
    lead_time: pd.Series


def compute_stats(table: pd.DataFrame) -> OlistStats:
    return OlistStats(
        items_per_order=items_per_order(table),
        quantity_per_line=quantity_per_line(table),
        arrival_profile=arrival_profile(table),
        daily_counts=daily_counts(table),
        product_popularity=product_popularity(table),
        lead_time=lead_time(table),
    )
