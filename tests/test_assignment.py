import unittest

from src.agents.robot import RobotConfig
from src.core.config import AssignmentParams, SimulationConfig
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order
from src.strategies.assignment import strategy_for


def assignment_model(
    *,
    strategy: str = "nearest",
    due_time: float | None = None,
    urgent: bool = False,
    battery_weight_s: float = 300.0,
    assign_robot=None,
):
    """One rack, two robots: a far one with a full battery and a near one at 25%."""
    layout = WarehouseLayout(
        width=9,
        height=3,
        blocked=frozenset(),
        racks={"rack-1": (6, 1)},
        stations={"station-1": (8, 1)},
        robot_starts={"robot-far": (1, 1), "robot-near": (5, 1)},
    )
    order = Order(
        "o1",
        ["sku-1"],
        created_time=0.0,
        due_time=due_time,
        urgent=urgent,
    )
    config = SimulationConfig(
        assignment=AssignmentParams(
            strategy=strategy,
            battery_weight_s=battery_weight_s,
        )
    )
    model = Warehouse(
        layout=layout,
        num_robots=2,
        orders=[order],
        robot_configs=[
            RobotConfig("robot-far", (1, 1), battery=100.0),
            RobotConfig("robot-near", (5, 1), battery=25.0),
        ],
        config=config,
        assign_robot=assign_robot,
    )
    model.step()
    return order.tasks[0].robot_id


class AssignmentStrategyTests(unittest.TestCase):
    def test_nearest_robot_is_the_default(self):
        self.assertEqual(assignment_model(), "robot-near")

    def test_deadline_battery_prefers_battery_when_there_is_slack(self):
        self.assertEqual(
            assignment_model(strategy="deadline_battery"),
            "robot-far",
        )

    def test_deadline_battery_prefers_speed_for_urgent_orders(self):
        self.assertEqual(
            assignment_model(strategy="deadline_battery", urgent=True),
            "robot-near",
        )

    def test_deadline_battery_prefers_speed_when_the_deadline_is_tight(self):
        self.assertEqual(
            assignment_model(strategy="deadline_battery", due_time=0.0),
            "robot-near",
        )

    def test_zero_battery_weight_falls_back_to_distance(self):
        self.assertEqual(
            assignment_model(
                strategy="deadline_battery",
                battery_weight_s=0.0,
            ),
            "robot-near",
        )

    def test_strategy_can_be_injected_directly(self):
        self.assertEqual(
            assignment_model(assign_robot=lambda request, robots: robots[0]),
            "robot-far",
        )

    def test_strategy_must_return_a_free_robot(self):
        with self.assertRaises(ValueError):
            assignment_model(assign_robot=lambda request, robots: None)


class AssignmentParameterTests(unittest.TestCase):
    def test_unknown_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            AssignmentParams(strategy="bogus")

    def test_deadline_horizon_must_be_positive(self):
        with self.assertRaises(ValueError):
            AssignmentParams(deadline_horizon_s=0.0)

    def test_battery_weight_cannot_be_negative(self):
        with self.assertRaises(ValueError):
            AssignmentParams(battery_weight_s=-1.0)

    def test_strategy_lookup_rejects_unknown_names(self):
        with self.assertRaises(ValueError):
            strategy_for("bogus")


if __name__ == "__main__":
    unittest.main()
