"""Order generator calibrated on Olist statistics.

Arrivals follow a non-homogeneous Poisson process: in every clock hour the
expected number of orders is the Olist mean for that weekday and hour
(``arrival_profile``), times ``volume_factor``. The number of orders in the
hour is drawn from a Poisson distribution and their moments are spread
uniformly over the hour.

Each order then gets:

* a number of different products drawn from ``items_per_order``,
* that many distinct products, chosen with probability ``order_share``
  (popular products appear in more orders),
* a quantity per product drawn from ``quantity_per_line``,
* a due time = arrival + a lead time drawn from the Olist lead times.
"""

import numpy as np
import pandas as pd
uv run python -m unittest tests.test_olist
from src.data.olist import OlistStats
from src.orders.models import Order, OrderLine

SECONDS_PER_HOUR = 3600.0


def _hour_slots(
    start: pd.Timestamp, duration_s: float
) -> list[tuple[pd.Timestamp, float, float]]:
    """Split [start, start + duration) into pieces that stay inside one clock hour.

    Returns (clock hour, piece start in seconds from ``start``, piece length).
    """
    slots = []
    offset = 0.0
    hour = start.floor("h")
    while offset < duration_s:
        hour_end = (hour - start).total_seconds() + SECONDS_PER_HOUR
        length = min(hour_end, duration_s) - offset
        slots.append((hour, offset, length))
        offset += length
        hour += pd.Timedelta(hours=1)
    return slots


def generate_orders(
    stats: OlistStats,
    rng: np.random.Generator,
    start: pd.Timestamp,
    duration_s: float,
    volume_factor: float = 1.0,
    id_prefix: str = "olist",
) -> list[Order]:
    """Orders arriving in [start, start + duration_s), sorted by arrival.

    ``start`` is a calendar moment; it decides the weekday and hour of each
    arrival. ``created_time`` and ``due_time`` are seconds from ``start``.
    Product ids are the Olist ``product_id`` values, used as SKUs.
    """
    if duration_s <= 0:
        raise ValueError("Duration must be positive")
    if volume_factor < 0:
        raise ValueError("Volume factor cannot be negative")

    products = stats.product_popularity.index.to_numpy()
    product_p = stats.product_popularity["order_share"].to_numpy(dtype=float)
    product_p = product_p / product_p.sum()

    sizes = stats.items_per_order.index.to_numpy()
    sizes_p = stats.items_per_order.to_numpy(dtype=float)
    quantities = stats.quantity_per_line.index.to_numpy()
    quantities_p = stats.quantity_per_line.to_numpy(dtype=float)
    lead_times = stats.lead_time.to_numpy(dtype=float)

    orders: list[Order] = []
    for hour, offset, length in _hour_slots(start, duration_s):
        mean = stats.arrival_profile.loc[hour.weekday(), hour.hour]
        expected = mean * volume_factor * length / SECONDS_PER_HOUR
        count = int(rng.poisson(expected))
        for moment in np.sort(rng.uniform(offset, offset + length, size=count)):
            size = min(int(rng.choice(sizes, p=sizes_p)), len(products))
            chosen = rng.choice(len(products), size=size, replace=False, p=product_p)
            lines = tuple(
                OrderLine(str(products[i]), int(rng.choice(quantities, p=quantities_p)))
                for i in chosen
            )
            created = float(moment)
            orders.append(
                Order(
                    f"{id_prefix}-{len(orders) + 1}",
                    lines,
                    created_time=created,
                    due_time=created + float(rng.choice(lead_times)),
                )
            )
    return orders
