from collections.abc import Sequence

import numpy as np

from src.orders.models import Order, OrderLine


def random_orders(
    rng: np.random.Generator,
    skus: Sequence[str],
    count: int,
    mean_interarrival_s: float,
    max_lines: int = 3,
    start_time: float = 0.0,
) -> list[Order]:
    """Synthetic orders: Poisson arrivals, uniform SKUs, 1..max_lines lines.

    A placeholder for the demo and for tests; calibrated generation from
    the Olist data comes in P6.
    """
    if count < 0 or mean_interarrival_s <= 0 or max_lines <= 0:
        raise ValueError("Invalid order generator parameters")
    if not skus:
        raise ValueError("No SKUs to order")
    orders = []
    time = start_time
    for index in range(count):
        time += float(rng.exponential(mean_interarrival_s))
        lines_count = int(rng.integers(1, min(max_lines, len(skus)) + 1))
        chosen = rng.choice(len(skus), size=lines_count, replace=False)
        orders.append(
            Order(
                f"order-{index + 1}",
                tuple(OrderLine(skus[i]) for i in sorted(chosen)),
                created_time=time,
            )
        )
    return orders
