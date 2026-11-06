import unittest

from src.core.config import RobotParams, SimulationConfig
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
        self.assertGreater(metrics.total_distance_m, 0)
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

    def test_second_order_for_the_same_rack_is_completed(self):
        orders = [
            Order("order-1", "rack-1", "station-1"),
            Order("order-2", "rack-1", "station-1"),
        ]
        model = Warehouse(layout=self.layout, orders=orders)

        model.run_until_complete(max_time=200)

        self.assertTrue(all(o.status is OrderStatus.COMPLETED for o in orders))

    def test_completion_time_includes_waiting_for_a_robot(self):
        layout = WarehouseLayout(
            width=7,
            height=5,
            racks={"rack-1": (5, 2), "rack-2": (5, 4)},
            stations={"station-1": (1, 0)},
            robot_starts={"robot-1": (1, 2)},
        )
        first = Order("order-1", "rack-1", "station-1")
        second = Order("order-2", "rack-2", "station-1")
        model = Warehouse(layout=layout, orders=[first, second])

        model.run_until_complete(max_time=200)

        self.assertGreater(second.waiting_time, first.waiting_time)
        self.assertEqual(
            second.completion_time,
            second.completed_time - second.created_time,
        )
        self.assertGreater(second.completion_time, first.completion_time)

    def test_clock_is_in_seconds_and_speed_controls_travel(self):
        slow = Warehouse(
            layout=self.layout,
            config=SimulationConfig(
                cell_size_m=1.0, robot=RobotParams(speed_m_per_s=0.5)
            ),
        )
        fast = Warehouse(layout=self.layout)

        slow_metrics = slow.run_until_complete()
        fast_metrics = fast.run_until_complete()

        self.assertEqual(fast.time, fast.steps * SimulationConfig.TICK_S)
        self.assertEqual(slow_metrics.total_distance_m, fast_metrics.total_distance_m)
        self.assertAlmostEqual(
            slow_metrics.average_completion_time,
            2 * fast_metrics.average_completion_time,
            delta=2,
        )

    def test_visualization_uses_a_page_for_the_space_component(self):
        from src.visualization.server import page, renderer

        self.assertIsNotNone(page)
        self.assertIsNotNone(renderer)
        self.assertEqual(renderer.canvas.get_figure().get_size_inches().tolist(), [9.0, 9.0])
        self.assertEqual(renderer.canvas.get_xlim(), (-0.5, 19.5))
        self.assertEqual(renderer.canvas.get_ylim(), (-0.5, 19.5))
