import unittest

from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order, OrderStatus


class WarehouseModelTests(unittest.TestCase):
    def setUp(self):
        self.layout = WarehouseLayout(
            width=7,
            height=5,
            blocked=frozenset({(3, 0), (3, 1), (3, 2), (3, 3)}),
            racks={"rack-1": (5, 2)},
            stations={"station-1": (1, 0)},
            robot_starts={"robot-1": (1, 2)},
        )
        self.model = Warehouse(layout=self.layout)

    def test_single_order_is_completed_and_measured(self):
        metrics = self.model.run_until_complete()
        order = self.model.orders[0]

        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertEqual(metrics.completed_orders, 1)
        self.assertEqual(metrics.average_completion_time, order.completion_time)
        self.assertEqual(metrics.longest_completion_time, order.completion_time)
        self.assertGreater(metrics.total_distance, 0)
        self.assertTrue(self.model.racks["rack-1"].delivered)

    def test_robot_does_not_move_through_blocked_cells(self):
        self.model.step()

        robot = self.model.robots[0]
        self.assertNotIn(robot.pos, self.layout.blocked)

    def test_demo_layout_keeps_existing_five_robot_visual_configuration(self):
        model = Warehouse(num_robots=5)

        self.assertEqual(len(model.robots), 5)

    def test_external_order_is_used_without_demo_defaults(self):
        order = Order("olist-order-1", "rack-1", "station-1")
        model = Warehouse(layout=self.layout, orders=[order])

        model.run_until_complete()

        self.assertEqual(model.orders, [order])
        self.assertEqual(order.status, OrderStatus.COMPLETED)

    def test_explicit_empty_orders_are_preserved(self):
        model = Warehouse(layout=self.layout, orders=[])

        self.assertEqual(model.orders, [])
        self.assertEqual(model.metrics.completed_orders, 0)

    def test_visualization_uses_a_page_for_the_space_component(self):
        from src.visualization.server import page, renderer

        self.assertIsNotNone(page)
        self.assertIsNotNone(renderer)
        self.assertEqual(renderer.canvas.get_figure().get_size_inches().tolist(), [9.0, 9.0])
        self.assertEqual(renderer.canvas.get_xlim(), (-0.5, 19.5))
        self.assertEqual(renderer.canvas.get_ylim(), (-0.5, 19.5))
