import unittest

from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import OrderStatus
from src.pipeline.pathfinding import astar_path


class LayoutGeneratorTests(unittest.TestCase):
    def test_counts_and_size(self):
        layout = WarehouseLayout.generate(
            block_columns=3,
            block_rows=2,
            block_length=4,
            block_depth=2,
            num_stations=2,
            num_chargers=1,
            num_robots=6,
        )

        self.assertEqual(len(layout.racks), 3 * 2 * 4 * 2)
        self.assertEqual(len(layout.stations), 2)
        self.assertEqual(len(layout.chargers), 1)
        self.assertEqual(len(layout.robot_starts), 6)
        self.assertEqual((layout.width, layout.height), (3 + 3 * 5 + 1, 1 + 2 * 3))

    def test_every_rack_is_reachable_from_every_station(self):
        layout = WarehouseLayout.generate(num_robots=1)
        rack_cells = set(layout.racks.values())
        static = rack_cells | set(layout.stations.values()) | set(layout.chargers.values())

        for station in layout.stations.values():
            for rack in layout.racks.values():
                path = astar_path(layout, rack, station, obstacles=static)
                self.assertEqual(path[-1], station)

    def test_every_charger_is_reachable(self):
        layout = WarehouseLayout.generate(num_robots=1)
        start = layout.robot_starts["robot-1"]

        for charger in layout.chargers.values():
            self.assertEqual(astar_path(layout, start, charger)[-1], charger)

    def test_extra_space_becomes_aisles(self):
        layout = WarehouseLayout.generate(
            block_columns=1, block_rows=1, num_robots=1, width=15, height=10
        )

        self.assertEqual((layout.width, layout.height), (15, 10))

    def test_too_small_area_is_rejected(self):
        with self.assertRaises(ValueError):
            WarehouseLayout.generate(block_columns=5, width=10)

    def test_deep_blocks_are_rejected(self):
        with self.assertRaises(ValueError):
            WarehouseLayout.generate(block_depth=3)

    def test_ascii_chargers(self):
        layout = WarehouseLayout.from_ascii(["S.RC", "B..."])

        self.assertEqual(layout.chargers, {"charger-1": (3, 0)})

    def test_demo_fills_the_requested_size(self):
        layout = WarehouseLayout.demo(width=20, height=20, num_robots=5)

        self.assertEqual((layout.width, layout.height), (20, 20))
        self.assertGreater(len(layout.racks), 10)


class DemoRunTests(unittest.TestCase):
    def test_demo_stream_of_orders_completes(self):
        model = Warehouse(num_robots=5, num_orders=40, rng=7)

        metrics = model.run_until_complete(max_time=50_000)

        self.assertTrue(all(o.status is OrderStatus.COMPLETED for o in model.orders))
        self.assertEqual(metrics.completed_orders, 40)
        self.assertGreater(metrics.orders_per_hour, 0)
        self.assertTrue(
            all(0 < u <= 1 for u in metrics.station_utilisation.values())
        )

    def test_same_seed_gives_same_result(self):
        first = Warehouse(num_robots=3, num_orders=15, rng=3).run_until_complete()
        second = Warehouse(num_robots=3, num_orders=15, rng=3).run_until_complete()

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
