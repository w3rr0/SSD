import unittest

import numpy as np

from src.agents.robot import RobotState
from src.core.config import FailureParams, PickingParams, SimulationConfig
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.generator import random_orders
from src.orders.models import Order, TaskStatus


def aisle_layout() -> WarehouseLayout:
    """One long corridor with a rack in the middle and a station at the end."""
    return WarehouseLayout(
        width=10,
        height=3,
        blocked=frozenset((x, 0) for x in range(10))
        | frozenset((x, 2) for x in range(10)),
        racks={"rack-1": (5, 1)},
        stations={"station-1": (9, 1)},
        robot_starts={"robot-1": (1, 1)},
    )


def open_layout() -> WarehouseLayout:
    """Open grid with two racks, used to test assignment priority."""
    return WarehouseLayout(
        width=9,
        height=3,
        blocked=frozenset(),
        racks={"rack-1": (2, 1), "rack-2": (4, 1)},
        stations={"station-1": (8, 1)},
        robot_starts={"robot-1": (1, 0)},
    )


class FailureMechanicsTests(unittest.TestCase):
    def test_fail_and_repair_restore_the_route(self):
        model = Warehouse(
            layout=aisle_layout(),
            num_robots=1,
            orders=[Order("o1", ["sku-1"])],
        )
        robot = model.robots[0]
        model.step()

        self.assertIs(robot.state, RobotState.TO_RACK)
        state_before = robot.state
        route_before = robot.route
        task_id = robot.assigned_task_id
        self.assertTrue(route_before)

        robot.fail()

        self.assertIs(robot.state, RobotState.FAILED)
        self.assertEqual(robot.route, ())
        self.assertEqual(robot.assigned_task_id, task_id)

        robot.repair()

        self.assertIs(robot.state, state_before)
        self.assertEqual(robot.route, route_before)

    def test_failure_and_repair_are_scheduled_events(self):
        config = SimulationConfig(
            failures=FailureParams(
                mean_time_to_failure_s=1.0,
                mean_repair_time_s=1.0,
            )
        )
        model = Warehouse(
            layout=aisle_layout(),
            num_robots=1,
            orders=[],
            config=config,
            rng=1,
        )
        robot = model.robots[0]

        for _ in range(200):
            model.step()

        states = [state for _, state in robot.state_history]
        self.assertIn(RobotState.FAILED, states)
        self.assertGreaterEqual(model.failure_count, 1)
        self.assertGreater(model.metrics.total_repair_time_s, 0.0)

    def test_failures_are_disabled_by_default(self):
        model = Warehouse(layout=aisle_layout(), num_robots=1, orders=[])

        for _ in range(100):
            model.step()

        self.assertEqual(model.failure_count, 0)
        self.assertEqual(model.metrics.total_repair_time_s, 0.0)

    def test_failure_stream_does_not_change_order_generation(self):
        base = Warehouse(num_robots=5, num_orders=10, rng=7)
        failing = Warehouse(
            num_robots=5,
            num_orders=10,
            rng=7,
            config=SimulationConfig(
                failures=FailureParams(mean_time_to_failure_s=10.0)
            ),
        )

        self.assertEqual(
            [(order.order_id, order.lines, order.created_time) for order in base.orders],
            [
                (order.order_id, order.lines, order.created_time)
                for order in failing.orders
            ],
        )

    def test_waiting_behind_a_failed_robot_is_expected_downtime(self):
        layout = WarehouseLayout(
            width=6,
            height=2,
            blocked=frozenset(),
            racks={"rack-1": (4, 0)},
            stations={"station-1": (0, 0)},
            robot_starts={"robot-1": (1, 0), "robot-2": (2, 0)},
        )
        config = SimulationConfig(
            deadlock_timeout_s=20.0,
            failures=FailureParams(mean_repair_time_s=10_000.0),
        )
        model = Warehouse(
            layout=layout,
            num_robots=2,
            orders=[Order("o1", ["sku-1"])],
            config=config,
            rng=0,
        )
        blocker = model.robots[1]
        model.handle_failure(blocker)
        self.assertIs(blocker.state, RobotState.FAILED)

        for _ in range(30):
            model.step()

        self.assertIs(blocker.state, RobotState.FAILED)
        self.assertGreater(model.failure_count, 0)

    def test_failure_is_deferred_while_picking(self):
        config = SimulationConfig(picking=PickingParams(fixed_s=100.0))
        model = Warehouse(
            layout=aisle_layout(),
            num_robots=1,
            orders=[Order("o1", ["sku-1"])],
            config=config,
        )
        robot = model.robots[0]
        while robot.state is not RobotState.PICKING:
            model.step()

        model.handle_failure(robot)
        self.assertIs(robot.state, RobotState.PICKING)

        for _ in range(20):
            model.step()

        self.assertIs(robot.state, RobotState.PICKING)
        self.assertEqual(model.failure_count, 0)


class UrgentOrderTests(unittest.TestCase):
    def test_urgent_order_gets_the_robot_before_a_normal_one(self):
        normal = Order("normal", ["sku-1"], created_time=0.0)
        urgent = Order("urgent", ["sku-2"], created_time=0.0, urgent=True)
        model = Warehouse(
            layout=open_layout(),
            num_robots=1,
            orders=[normal, urgent],
        )

        model.step()

        self.assertEqual(urgent.started_time, model.time)
        self.assertIsNone(normal.started_time)
        self.assertIs(urgent.tasks[0].status, TaskStatus.IN_PROGRESS)
        self.assertIs(normal.tasks[0].status, TaskStatus.PENDING)

    def test_generator_marks_a_share_of_orders_urgent(self):
        orders = random_orders(
            np.random.default_rng(0),
            ["sku-1", "sku-2"],
            count=100,
            mean_interarrival_s=1.0,
            urgent_share=0.5,
        )

        urgent = sum(order.urgent for order in orders)
        self.assertGreater(urgent, 0)
        self.assertLess(urgent, len(orders))


class FailureParameterTests(unittest.TestCase):
    def test_mean_time_to_failure_must_be_positive(self):
        with self.assertRaises(ValueError):
            FailureParams(mean_time_to_failure_s=0.0)

    def test_mean_repair_time_must_be_positive(self):
        with self.assertRaises(ValueError):
            FailureParams(mean_repair_time_s=0.0)

    def test_retry_interval_must_be_positive(self):
        with self.assertRaises(ValueError):
            FailureParams(retry_interval_s=0.0)

    def test_urgent_share_must_be_a_fraction(self):
        with self.assertRaises(ValueError):
            random_orders(
                np.random.default_rng(0),
                ["sku-1"],
                count=1,
                mean_interarrival_s=1.0,
                urgent_share=1.5,
            )


if __name__ == "__main__":
    unittest.main()
