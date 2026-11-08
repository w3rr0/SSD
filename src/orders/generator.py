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
    urgent_share: float = 0.0,
) -> list[Order]:
    """Synthetic orders: Poisson arrivals, uniform SKUs, 1..max_lines lines.

    ``urgent_share`` marks that fraction of orders as urgent. The draw is
    skipped when the share is zero, so the default random stream is unchanged.

    A placeholder for the demo and for tests; calibrated generation from
    the Olist data comes in P6.
    """
    if count < 0 or mean_interarrival_s <= 0 or max_lines <= 0:
        raise ValueError("Invalid order generator parameters")
    if not 0.0 <= urgent_share <= 1.0:
        raise ValueError("Urgent share must be between zero and one")
    if not skus:
        raise ValueError("No SKUs to order")
    orders = []
    time = start_time
    for index in range(count):
        time += float(rng.exponential(mean_interarrival_s))
        lines_count = int(rng.integers(1, min(max_lines, len(skus)) + 1))
        chosen = rng.choice(len(skus), size=lines_count, replace=False)
        urgent = urgent_share > 0.0 and float(rng.random()) < urgent_share
        orders.append(
            Order(
                f"order-{index + 1}",
                tuple(OrderLine(skus[i]) for i in sorted(chosen)),
                created_time=time,
                urgent=urgent,
            )
        )
    return orders
