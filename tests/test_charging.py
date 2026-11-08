import unittest

from src.agents.robot import RobotState
from src.core.config import RobotParams, SimulationConfig
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order


def two_aisle_layout(
    *,
    chargers: dict[str, tuple[int, int]] | None = None,
    robot_starts: dict[str, tuple[int, int]] | None = None,
) -> WarehouseLayout:
    """Two open aisles with one rack, one station and optional chargers."""
    return WarehouseLayout(
        width=9,
        height=4,
        blocked=frozenset((x, y) for x in range(9) for y in (0, 3)),
        racks={"rack-1": (1, 2)},
        stations={"station-1": (7, 2)},
        chargers=chargers or {},
        robot_starts=robot_starts or {"robot-1": (4, 1)},
    )


def charging_config(
    *,
    initial_battery: float = 100.0,
    threshold: float = 20.0,
    rate: float = 10.0,
) -> SimulationConfig:
    return SimulationConfig(
        robot=RobotParams(
            initial_battery_pct=initial_battery,
            charge_threshold_pct=threshold,
            charge_rate_pct_per_s=rate,
        )
    )


class ChargingTests(unittest.TestCase):
    def test_low_battery_robot_charges_before_starting_work(self):
        model = Warehouse(
            layout=two_aisle_layout(chargers={"charger-1": (1, 1)}),
            num_robots=1,
            orders=[Order("o1", ["sku-1"])],
            config=charging_config(initial_battery=10.0),
        )
        robot = model.robots[0]
        charger = model.chargers["charger-1"]

        for _ in range(400):
            model.step()
            if charger.charging_times:
                break

        self.assertEqual(len(charger.charging_times), 1)
        self.assertGreaterEqual(robot.battery, 99.0)
        states = [state for _, state in robot.state_history]
        self.assertLess(
            states.index(RobotState.CHARGING),
            states.index(RobotState.TO_RACK),
        )

    def test_robot_finishes_its_task_before_charging(self):
        order = Order("o1", ["sku-1"])
        model = Warehouse(
            layout=two_aisle_layout(chargers={"charger-1": (1, 1)}),
            num_robots=1,
            orders=[order],
            config=charging_config(initial_battery=20.5),
        )
        robot = model.robots[0]
        charger = model.chargers["charger-1"]

        for _ in range(400):
            model.step()
            if charger.charging_times:
                break

        states = [state for _, state in robot.state_history]
        self.assertLess(
            states.index(RobotState.RETURNING_RACK),
            states.index(RobotState.TO_CHARGER),
        )
        charging_at = next(
            moment
            for moment, state in robot.state_history
            if state is RobotState.CHARGING
        )
        self.assertGreater(charging_at, order.completion_time)

    def test_robot_above_threshold_keeps_working(self):
        order = Order("o1", ["sku-1"])
        model = Warehouse(
            layout=two_aisle_layout(chargers={"charger-1": (1, 1)}),
            num_robots=1,
            orders=[order],
            config=charging_config(initial_battery=80.0),
        )
        robot = model.robots[0]
        charger = model.chargers["charger-1"]

        for _ in range(400):
            model.step()
            if model.all_orders_completed:
                break

        self.assertEqual(order.status.value, "completed")
        self.assertEqual(charger.charging_times, [])
        self.assertNotIn(
            RobotState.CHARGING,
            [state for _, state in robot.state_history],
        )

    def test_one_charger_serves_robots_one_at_a_time(self):
        layout = two_aisle_layout(
            chargers={"charger-1": (1, 1)},
            robot_starts={"robot-1": (4, 1), "robot-2": (6, 1)},
        )
        model = Warehouse(
            layout=layout,
            num_robots=2,
            orders=[],
            config=charging_config(initial_battery=10.0),
        )
        charger = model.chargers["charger-1"]

        for _ in range(800):
            model.step()
            charging = sum(
                robot.state is RobotState.CHARGING for robot in model.robots
            )
            self.assertLessEqual(charging, 1)
            if len(charger.charging_times) == 2:
                break

        self.assertEqual(len(charger.charging_times), 2)
        self.assertTrue(all(robot.battery >= 99.0 for robot in model.robots))

    def test_charger_utilisation_and_charging_metrics(self):
        model = Warehouse(
            layout=two_aisle_layout(chargers={"charger-1": (1, 1)}),
            num_robots=1,
            orders=[],
            config=charging_config(initial_battery=10.0),
        )
        charger = model.chargers["charger-1"]

        for _ in range(400):
            model.step()
            if charger.charging_times:
                break

        metrics = model.metrics
        self.assertGreater(metrics.charger_utilisation["charger-1"], 0.0)
        self.assertEqual(
            metrics.total_charging_time_s, sum(charger.charging_times)
        )
        self.assertAlmostEqual(
            metrics.average_charging_time, charger.charging_times[0]
        )

    def test_in_progress_charge_counts_towards_total_time(self):
        model = Warehouse(
            layout=two_aisle_layout(chargers={"charger-1": (1, 1)}),
            num_robots=1,
            orders=[],
            config=charging_config(initial_battery=10.0),
        )
        robot = model.robots[0]

        while robot.state is not RobotState.CHARGING:
            model.step()
        model.step()

        metrics = model.metrics
        self.assertGreater(metrics.total_charging_time_s, 0.0)
        self.assertGreater(metrics.charger_utilisation["charger-1"], 0.0)
        self.assertIsNone(metrics.average_charging_time)

    def test_layout_without_chargers_keeps_robots_working(self):
        order = Order("o1", ["sku-1"])
        model = Warehouse(
            layout=two_aisle_layout(),
            num_robots=1,
            orders=[order],
            config=charging_config(initial_battery=10.0),
        )
        robot = model.robots[0]

        metrics = model.run_until_complete(max_time=600)

        self.assertEqual(metrics.completed_orders, 1)
        self.assertNotIn(
            RobotState.TO_CHARGER,
            [state for _, state in robot.state_history],
        )

    def test_initial_battery_comes_from_config(self):
        model = Warehouse(
            layout=two_aisle_layout(chargers={"charger-1": (1, 1)}),
            num_robots=1,
            orders=[],
            config=charging_config(initial_battery=35.0),
        )

        self.assertEqual(model.robots[0].battery, 35.0)


class ChargeParameterTests(unittest.TestCase):
    def test_charge_duration_follows_the_rate(self):
        params = RobotParams(charge_rate_pct_per_s=0.5)

        self.assertAlmostEqual(params.charge_duration_s(20.0), 160.0)
        self.assertEqual(params.charge_duration_s(100.0), 0.0)

    def test_threshold_must_be_below_capacity(self):
        with self.assertRaises(ValueError):
            RobotParams(charge_threshold_pct=-1.0)
        with self.assertRaises(ValueError):
            RobotParams(charge_threshold_pct=100.0)

    def test_charge_rate_must_be_positive(self):
        with self.assertRaises(ValueError):
            RobotParams(charge_rate_pct_per_s=0.0)

    def test_initial_battery_must_fit_capacity(self):
        with self.assertRaises(ValueError):
            RobotParams(initial_battery_pct=-1.0)
        with self.assertRaises(ValueError):
            RobotParams(initial_battery_pct=101.0)


if __name__ == "__main__":
    unittest.main()
