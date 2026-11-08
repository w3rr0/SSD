import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order
from src.strategies.placement import (
    NearestFreeSlot,
    abc_classes,
    abc_placement,
    fill_racks,
    random_placement,
    racks_by_distance,
)

# Station at (0, 0); two rows of racks, each touching an aisle.
#   x: 0 1 2 3 4 5
#      S . R R R R     y = 0   rack-1 .. rack-4
#      . . . . . .     y = 1
#      . . R R R R     y = 2   rack-5 .. rack-8
#      B B . . . .     y = 3
LAYOUT = WarehouseLayout.from_ascii(
    [
        "S.RRRR",
        "......",
        "..RRRR",
        "BB....",
    ]
)
PRODUCTS = [f"p{i}" for i in range(16)]


def popularity(orders: list[int]) -> pd.DataFrame:
    """Products p0, p1, ... with the given number of orders each."""
    return pd.DataFrame(
        {"orders": orders}, index=[f"p{i}" for i in range(len(orders))]
    )


class PlacementTests(unittest.TestCase):
    def assert_every_product_once(self, rack_skus, products):
        placed = [sku for skus in rack_skus.values() for sku in skus]
        self.assertEqual(sorted(placed), sorted(products))

    def test_racks_by_distance(self):
        order = racks_by_distance(LAYOUT)
        distances = [
            abs(LAYOUT.racks[r][0]) + abs(LAYOUT.racks[r][1]) for r in order
        ]
        self.assertEqual(distances, sorted(distances))
        self.assertEqual(LAYOUT.racks[order[0]], (2, 0))

    def test_fill_racks_puts_the_same_number_on_each_rack(self):
        rack_skus = fill_racks(PRODUCTS[:10], ["r1", "r2", "r3", "r4"])
        self.assertEqual([len(rack_skus[r]) for r in ("r1", "r2", "r3", "r4")], [3, 3, 3, 1])
        self.assertEqual(rack_skus["r1"], frozenset({"p0", "p1", "p2"}))

    def test_fill_racks_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            fill_racks(["p0", "p0"], ["r1"])

    def test_random_placement_places_every_product_once(self):
        rack_skus = random_placement(PRODUCTS, LAYOUT, np.random.default_rng(1))
        self.assert_every_product_once(rack_skus, PRODUCTS)
        self.assertEqual({len(skus) for skus in rack_skus.values()}, {2})

    def test_random_placement_depends_only_on_the_seed(self):
        first = random_placement(PRODUCTS, LAYOUT, np.random.default_rng(1))
        again = random_placement(PRODUCTS, LAYOUT, np.random.default_rng(1))
        other = random_placement(PRODUCTS, LAYOUT, np.random.default_rng(2))
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)

    def test_abc_classes_follow_cumulative_share(self):
        # shares 50, 30, 10, 5, 5 -> cumulative 50, 80, 90, 95, 100 %
        classes = abc_classes(popularity([50, 30, 10, 5, 5]))
        self.assertEqual(classes.to_dict(), {"p0": "A", "p1": "A", "p2": "B", "p3": "B", "p4": "C"})

    def test_abc_puts_class_a_closest_to_the_station(self):
        # 16 products on 8 racks: p0-p3 are A, p4-p5 B, the rest C
        orders = [40, 20, 10, 10, 8, 7] + [1] * 5 + [0] * 5
        pop = popularity(orders)
        classes = abc_classes(pop)
        rack_skus = abc_placement(pop, LAYOUT, np.random.default_rng(3))
        self.assert_every_product_once(rack_skus, list(pop.index))

        rank = {rack: i for i, rack in enumerate(racks_by_distance(LAYOUT))}
        rack_of = {sku: rack for rack, skus in rack_skus.items() for sku in skus}
        worst_a = max(rank[rack_of[p]] for p in classes.index[classes == "A"])
        best_b = min(rank[rack_of[p]] for p in classes.index[classes == "B"])
        worst_b = max(rank[rack_of[p]] for p in classes.index[classes == "B"])
        best_c = min(rank[rack_of[p]] for p in classes.index[classes == "C"])
        self.assertLessEqual(worst_a, best_b)
        self.assertLessEqual(worst_b, best_c)


class ReturningWarehouse(Warehouse):
    """The model with the nearest-free-slot return policy plugged in."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.return_policy = NearestFreeSlot(self.layout)

    def return_location(self, rack):
        return self.return_policy.choose(self, rack)


class NearestFreeSlotTests(unittest.TestCase):
    def make_model(self, orders):
        rack_skus = {rack: frozenset({f"sku-{rack}"}) for rack in LAYOUT.racks}
        return ReturningWarehouse(
            layout=LAYOUT, num_robots=2, orders=orders, rack_skus=rack_skus, rng=1
        )

    def state(self, away):
        """Racks in ``away`` are carried after picking at station-1; the rest stand home."""
        racks = {
            rack_id: SimpleNamespace(
                rack_id=rack_id,
                pos=pos,
                carried_by="robot" if rack_id in away else None,
                reserved_by_task=f"task-{rack_id}" if rack_id in away else None,
            )
            for rack_id, pos in LAYOUT.racks.items()
        }
        tasks = {f"task-{r}": SimpleNamespace(station_id="station-1") for r in away}
        return SimpleNamespace(layout=LAYOUT, racks=racks, tasks_by_id=tasks)

    def test_rack_goes_to_the_free_slot_nearest_the_station(self):
        # rack-1 (2, 0) and rack-4 (5, 0) are both away from their slots:
        # rack-4 takes rack-1's slot, the nearest free one.
        model = self.state(away={"rack-1", "rack-4"})
        policy = NearestFreeSlot(LAYOUT)
        self.assertEqual(policy.choose(model, model.racks["rack-4"]), (2, 0))

    def test_a_reserved_slot_is_not_given_twice(self):
        model = self.state(away={"rack-1", "rack-4"})
        policy = NearestFreeSlot(LAYOUT)
        policy.choose(model, model.racks["rack-4"])
        self.assertEqual(policy.choose(model, model.racks["rack-1"]), (5, 0))

    def test_racks_never_share_a_slot(self):
        orders = [
            Order(f"o{i}", [f"sku-rack-{(i % 8) + 1}"], created_time=float(i * 3))
            for i in range(30)
        ]
        model = self.make_model(orders)
        model.run_until_complete()
        model.run_for(300)
        positions = [rack.pos for rack in model.racks.values()]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertTrue(set(positions) <= set(LAYOUT.racks.values()))
        self.assertTrue(all(rack.carried_by is None for rack in model.racks.values()))


if __name__ == "__main__":
    unittest.main()
