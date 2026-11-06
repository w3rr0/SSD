import unittest

from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order, OrderLine, OrderStatus, TaskStatus


class OrderLineTests(unittest.TestCase):
    def test_repeated_skus_are_merged(self):
        order = Order("o", ["sku-1", OrderLine("sku-1", 2), "sku-2"])

        self.assertEqual(order.lines, (OrderLine("sku-1", 3), OrderLine("sku-2", 1)))
        self.assertEqual(order.items, 4)

    def test_order_needs_lines(self):
        with self.assertRaises(ValueError):
            Order("o", [])

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            OrderLine("sku-1", 0)


class MultiRackOrderTests(unittest.TestCase):
    def setUp(self):
        self.layout = WarehouseLayout(
            width=8,
            height=5,
            racks={"rack-a": (6, 1), "rack-b": (6, 3), "rack-c": (4, 3)},
            stations={"station-1": (0, 0), "station-2": (0, 4)},
            robot_starts={"robot-1": (2, 2), "robot-2": (3, 2)},
        )
        self.rack_skus = {
            "rack-a": {"apple", "pear"},
            "rack-b": {"plum"},
            "rack-c": {"apple"},
        }

    def test_order_is_split_into_minimum_number_of_racks(self):
        order = Order("o", ["apple", "pear", "plum"], station_id="station-1")
        model = Warehouse(
            layout=self.layout, orders=[order], rack_skus=self.rack_skus
        )

        model.step()

        self.assertEqual(
            sorted(task.rack_id for task in order.tasks), ["rack-a", "rack-b"]
        )
        rack_a_task = next(t for t in order.tasks if t.rack_id == "rack-a")
        self.assertEqual({line.sku for line in rack_a_task.lines}, {"apple", "pear"})

    def test_order_completes_only_after_all_its_racks_arrive(self):
        order = Order("o", ["pear", "plum"], station_id="station-1")
        model = Warehouse(
            layout=self.layout, orders=[order], rack_skus=self.rack_skus
        )

        metrics = model.run_until_complete()

        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertEqual(len(order.tasks), 2)
        self.assertTrue(all(t.status is TaskStatus.COMPLETED for t in order.tasks))
        self.assertEqual(
            order.completed_time, max(t.completed_time for t in order.tasks)
        )
        self.assertEqual(metrics.completed_orders, 1)

    def test_station_is_chosen_when_order_has_none(self):
        first = Order("o1", ["pear"])
        second = Order("o2", ["plum"])
        model = Warehouse(
            layout=self.layout, orders=[first, second], rack_skus=self.rack_skus
        )

        model.step()

        self.assertEqual({first.station_id, second.station_id}, {"station-1", "station-2"})

    def test_unknown_sku_is_rejected(self):
        with self.assertRaises(ValueError):
            Warehouse(
                layout=self.layout,
                orders=[Order("o", ["banana"])],
                rack_skus=self.rack_skus,
            )


if __name__ == "__main__":
    unittest.main()
