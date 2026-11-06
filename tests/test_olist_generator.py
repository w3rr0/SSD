import unittest

import numpy as np
import pandas as pd

from src.data.olist import OlistStats
from src.orders.olist_generator import generate_orders

HOUR = 3600.0
MONDAY = pd.Timestamp("2017-01-02 00:00")


def make_stats(rate_per_hour=10.0, active_hours=range(24)):
    """Every weekday has ``rate_per_hour`` orders in ``active_hours``, else 0."""
    profile = pd.DataFrame(0.0, index=range(7), columns=range(24))
    profile.loc[:, list(active_hours)] = rate_per_hour
    popularity = pd.DataFrame(
        {
            "orders": [6, 3, 1, 0],
            "order_share": [0.6, 0.3, 0.1, 0.0],
            "units": [6, 3, 1, 0],
            "unit_share": [0.6, 0.3, 0.1, 0.0],
        },
        index=pd.Index(["A", "B", "C", "Z"], name="product_id"),
    )
    return OlistStats(
        items_per_order=pd.Series({1: 0.5, 2: 0.5}),
        quantity_per_line=pd.Series({1: 0.8, 3: 0.2}),
        arrival_profile=profile,
        daily_counts=pd.Series(dtype=float),
        product_popularity=popularity,
        lead_time=pd.Series([2 * 86400.0, 5 * 86400.0]),
    )


class OlistGeneratorTests(unittest.TestCase):
    def generate(self, stats=None, start=MONDAY, duration_s=24 * HOUR, seed=1, **kw):
        return generate_orders(
            stats or make_stats(), np.random.default_rng(seed), start, duration_s, **kw
        )

    def test_mean_count_follows_profile(self):
        # 10 orders/h for 7 days -> 1680 expected, Poisson sd ~ 41
        orders = self.generate(duration_s=7 * 24 * HOUR)
        self.assertLess(abs(len(orders) - 1680), 4 * 41)

    def test_no_orders_in_hours_with_zero_rate(self):
        orders = self.generate(make_stats(active_hours=[10]), duration_s=7 * 24 * HOUR)
        self.assertTrue(orders)
        hours = {int(o.created_time // HOUR) % 24 for o in orders}
        self.assertEqual(hours, {10})

    def test_volume_factor_scales_arrivals(self):
        self.assertEqual(self.generate(volume_factor=0.0), [])
        base = len(self.generate(duration_s=7 * 24 * HOUR))
        doubled = len(self.generate(duration_s=7 * 24 * HOUR, volume_factor=2.0))
        self.assertAlmostEqual(doubled / base, 2.0, delta=0.15)

    def test_start_in_the_middle_of_an_hour(self):
        # 10:30 for 30 minutes: half of hour 10 -> 5 expected per run
        stats = make_stats(active_hours=[10])
        start = MONDAY + pd.Timedelta(hours=10, minutes=30)
        counts = [
            len(self.generate(stats, start=start, duration_s=1800, seed=s))
            for s in range(400)
        ]
        self.assertAlmostEqual(np.mean(counts), 5.0, delta=0.4)

    def test_times_are_sorted_and_inside_the_window(self):
        orders = self.generate()
        times = [o.created_time for o in orders]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all(0 <= t < 24 * HOUR for t in times))

    def test_due_time_is_arrival_plus_lead_time(self):
        for order in self.generate():
            self.assertIn(order.due_time - order.created_time, {2 * 86400.0, 5 * 86400.0})

    def test_lines_use_distinct_known_products(self):
        orders = self.generate(duration_s=7 * 24 * HOUR)
        sizes = set()
        for order in orders:
            skus = [line.sku for line in order.lines]
            self.assertEqual(len(skus), len(set(skus)))
            self.assertTrue(set(skus) <= {"A", "B", "C"})  # Z has share 0
            self.assertTrue(all(line.quantity in (1, 3) for line in order.lines))
            sizes.add(len(skus))
        self.assertEqual(sizes, {1, 2})

    def test_popular_products_appear_more_often(self):
        orders = self.generate(make_stats(), duration_s=7 * 24 * HOUR)
        counts = {sku: 0 for sku in "ABC"}
        for order in orders:
            for sku in order.skus:
                counts[sku] += 1
        self.assertGreater(counts["A"], counts["B"])
        self.assertGreater(counts["B"], counts["C"])

    def test_same_seed_same_orders(self):
        first = [(o.created_time, o.lines) for o in self.generate(seed=7)]
        second = [(o.created_time, o.lines) for o in self.generate(seed=7)]
        self.assertEqual(first, second)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            self.generate(duration_s=0)
        with self.assertRaises(ValueError):
            self.generate(volume_factor=-1)


if __name__ == "__main__":
    unittest.main()
