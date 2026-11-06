import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data import olist

# Five orders placed in one week (Mon 2017-01-02 .. Sun 2017-01-08)
# plus one in 2018. Expected values below are counted by hand.
ORDERS_CSV = """order_id,customer_id,order_status,order_purchase_timestamp
o1,c1,delivered,2017-01-02 10:15:00
o2,c2,delivered,2017-01-02 10:45:00
o3,c3,shipped,2017-01-04 18:00:00
o4,c4,canceled,2017-01-05 09:00:00
o5,c5,delivered,2017-01-08 23:30:00
o6,c6,delivered,2018-03-01 12:00:00
"""

# o1: product A x2 (two rows), product B x1, two sellers -> earliest deadline
# o2: product A x1
# o3: product C x1
# o4: canceled -> dropped
# o5: product A x1, product C x3
# o6: product B x1 (2018)
ITEMS_CSV = """order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value
o1,1,A,s1,2017-01-06 10:00:00,10,1
o1,2,A,s1,2017-01-06 10:00:00,10,1
o1,3,B,s2,2017-01-05 10:00:00,20,1
o2,1,A,s1,2017-01-06 11:00:00,10,1
o3,1,C,s3,2017-01-09 18:00:00,30,1
o4,1,B,s2,2017-01-09 09:00:00,20,1
o5,1,A,s1,2017-01-12 00:00:00,10,1
o5,2,C,s3,2017-01-12 00:00:00,30,1
o5,3,C,s3,2017-01-12 00:00:00,30,1
o5,4,C,s3,2017-01-12 00:00:00,30,1
o6,1,B,s2,2018-03-05 12:00:00,20,1
"""


class OlistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        raw = Path(cls._tmp.name)
        (raw / olist.ORDERS_FILE).write_text(ORDERS_CSV)
        (raw / olist.ITEMS_FILE).write_text(ITEMS_CSV)
        cls.table = olist.load_orders(raw)
        cls.y2017 = olist.year(cls.table, 2017)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def line(self, order_id, product_id):
        rows = self.table[
            (self.table["order_id"] == order_id)
            & (self.table["product_id"] == product_id)
        ]
        self.assertEqual(len(rows), 1)
        return rows.iloc[0]

    def test_units_become_quantity(self):
        self.assertEqual(self.line("o1", "A")["quantity"], 2)
        self.assertEqual(self.line("o5", "C")["quantity"], 3)

    def test_canceled_orders_are_dropped(self):
        self.assertNotIn("o4", set(self.table["order_id"]))

    def test_shipping_limit_is_the_earliest_seller_deadline(self):
        expected = pd.Timestamp("2017-01-05 10:00:00")
        self.assertEqual(self.line("o1", "A")["shipping_limit"], expected)
        self.assertEqual(self.line("o1", "B")["shipping_limit"], expected)

    def test_time_columns(self):
        row = self.line("o3", "C")
        self.assertEqual((row["year"], row["weekday"], row["hour"]), (2017, 2, 18))

    def test_year_filter(self):
        self.assertEqual(set(self.y2017["order_id"]), {"o1", "o2", "o3", "o5"})

    def test_items_per_order(self):
        # o1: 2 products, o2: 1, o3: 1, o5: 2
        shares = olist.items_per_order(self.y2017)
        self.assertEqual(shares.to_dict(), {1: 0.5, 2: 0.5})

    def test_quantity_per_line(self):
        # lines: o1A=2, o1B=1, o2A=1, o3C=1, o5A=1, o5C=3
        shares = olist.quantity_per_line(self.y2017)
        self.assertEqual(shares.to_dict(), {1: 4 / 6, 2: 1 / 6, 3: 1 / 6})

    def test_daily_counts_include_empty_days(self):
        counts = olist.daily_counts(self.y2017)
        self.assertEqual(len(counts), 7)  # 2017-01-02 .. 2017-01-08
        self.assertEqual(counts[pd.Timestamp("2017-01-02")], 2)
        self.assertEqual(counts[pd.Timestamp("2017-01-03")], 0)
        self.assertEqual(counts.sum(), 4)

    def test_arrival_profile(self):
        profile = olist.arrival_profile(self.y2017)
        self.assertEqual(profile.shape, (7, 24))
        # one Monday in the period, two orders between 10:00 and 11:00
        self.assertEqual(profile.loc[0, 10], 2.0)
        self.assertEqual(profile.loc[2, 18], 1.0)
        self.assertEqual(profile.loc[6, 23], 1.0)
        self.assertEqual(profile.to_numpy().sum(), 4.0)

    def test_product_popularity_by_orders_and_units(self):
        popularity = olist.product_popularity(self.y2017)
        # A: in o1, o2, o5 (3 orders, 4 units); C: o3, o5 (2 orders, 4 units);
        # B: o1 (1 order, 1 unit). 4 orders and 9 units in total.
        self.assertEqual(list(popularity.index), ["A", "C", "B"])
        self.assertEqual(popularity.loc["A", "orders"], 3)
        self.assertEqual(popularity.loc["A", "order_share"], 3 / 4)
        self.assertEqual(popularity.loc["C", "units"], 4)
        self.assertEqual(popularity.loc["C", "unit_share"], 4 / 9)

    def test_compute_stats_bundles_everything(self):
        stats = olist.compute_stats(self.y2017)
        self.assertEqual(stats.items_per_order.to_dict(), {1: 0.5, 2: 0.5})
        self.assertEqual(stats.product_popularity.index[0], "A")


if __name__ == "__main__":
    unittest.main()
