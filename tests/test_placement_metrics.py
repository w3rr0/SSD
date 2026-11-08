import unittest

from src.agents.robot import RobotState
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order


def placement_layout() -> WarehouseLayout:
    """One rack far from the station, so the return trip has a real distance."""
    return WarehouseLayout(
        width=9,
        height=3,
        blocked=frozenset(),
        racks={"rack-1": (6, 1)},
        stations={"station-1": (1, 1)},
        robot_starts={"robot-1": (1, 0)},
    )


class PlacementMetricsTests(unittest.TestCase):
    def test_return_metrics_are_recorded_after_the_rack_is_put_down(self):
        model = Warehouse(
            layout=placement_layout(),
            num_robots=1,
            orders=[Order("o1", ["sku-1"])],
        )

        model.run_until_complete()
        self.assertIs(model.robots[0].state, RobotState.RETURNING_RACK)

        model.run_for(100)

        metrics = model.metrics
        self.assertIs(model.robots[0].state, RobotState.IDLE)
        self.assertEqual(metrics.return_trips, 1)
        self.assertGreater(metrics.total_return_distance_m, 0.0)
        self.assertEqual(
            metrics.average_return_distance_m,
            metrics.total_return_distance_m,
        )
        self.assertEqual(metrics.racks_returned_home_share, 1.0)
        self.assertEqual(metrics.rack_slot_utilisation, 1.0)

    def test_carried_rack_leaves_its_slot_empty(self):
        model = Warehouse(
            layout=placement_layout(),
            num_robots=1,
            orders=[Order("o1", ["sku-1"])],
        )

        model.run_until_complete()

        self.assertIs(model.robots[0].state, RobotState.RETURNING_RACK)
        self.assertEqual(model.metrics.rack_slot_utilisation, 0.0)

        model.run_for(100)
        self.assertEqual(model.metrics.rack_slot_utilisation, 1.0)

    def test_average_return_distance_uses_the_number_of_trips(self):
        orders = [
            Order("o1", ["sku-1"]),
            Order("o2", ["sku-1"]),
        ]
        model = Warehouse(
            layout=placement_layout(),
            num_robots=1,
            orders=orders,
        )

        model.run_until_complete(max_time=500)
        model.run_for(100)

        metrics = model.metrics
        self.assertEqual(metrics.return_trips, 2)
        self.assertAlmostEqual(
            metrics.average_return_distance_m,
            metrics.total_return_distance_m / 2,
        )
        self.assertEqual(metrics.racks_returned_home_share, 1.0)


if __name__ == "__main__":
    unittest.main()
