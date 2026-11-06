import unittest
from statistics import mean, stdev

import numpy as np

from src.agents.robot import RobotState
from src.core.config import PickingParams, SimulationConfig
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order, OrderLine


class StationQueueTests(unittest.TestCase):
    def setUp(self):
        # Two racks right next to the station, two robots under them.
        self.layout = WarehouseLayout(
            width=5,
            height=3,
            racks={"rack-1": (1, 1), "rack-2": (3, 1)},
            stations={"station-1": (2, 1)},
            robot_starts={"robot-1": (1, 0), "robot-2": (3, 0)},
        )
        self.picking = PickingParams(fixed_s=0.0, per_item_s=30.0)

    def make_model(self, orders, picking=None, rng=None):
        return Warehouse(
            layout=self.layout,
            num_robots=2,
            orders=orders,
            config=SimulationConfig(picking=picking or self.picking),
            rng=rng,
        )

    def test_robots_are_served_one_at_a_time_in_arrival_order(self):
        first = Order("o1", ["sku-1"])
        second = Order("o2", ["sku-2"])
        model = self.make_model([first, second])
        station = model.stations["station-1"]

        model.run_until_complete()

        self.assertEqual(station.served, 2)
        self.assertEqual(len(station.wait_times), 2)
        self.assertGreater(max(station.wait_times), 0)
        finish_times = sorted([first.completed_time, second.completed_time])
        self.assertGreaterEqual(finish_times[1] - finish_times[0], 30.0)

    def test_picking_time_depends_on_items(self):
        order = Order("o1", [OrderLine("sku-1", 3)])
        model = self.make_model([order])
        robot_states = model.robots

        model.run_until_complete()

        picking = sum(r.time_in_state()[RobotState.PICKING] for r in robot_states)
        self.assertAlmostEqual(picking, 90.0)

    def test_order_completes_when_picking_ends_not_on_arrival(self):
        order = Order("o1", ["sku-1"])
        model = self.make_model([order])

        model.run_until_complete()

        robot = next(r for r in model.robots if r.distance_travelled_m > 0)
        arrival = next(t for t, s in robot.state_history if s is RobotState.QUEUED)
        self.assertAlmostEqual(order.completed_time - arrival, 30.0)

    def test_utilisation_is_busy_time_over_clock(self):
        model = self.make_model([Order("o1", ["sku-1"])])

        model.run_until_complete()
        model.run_until(300)

        station = model.stations["station-1"]
        self.assertAlmostEqual(station.utilisation(), 30.0 / 300)
        self.assertAlmostEqual(
            model.metrics.station_utilisation["station-1"], 30.0 / 300
        )

    def test_exponential_picking_has_the_configured_mean(self):
        picking = PickingParams(
            fixed_s=0.0, per_item_s=20.0, distribution="exponential"
        )
        rng = np.random.default_rng(42)

        draws = [picking.sample(1, rng) for _ in range(20_000)]

        self.assertAlmostEqual(mean(draws), 20.0, delta=0.6)
        self.assertGreater(stdev(draws), 15.0)

    def test_deterministic_picking_is_exactly_the_mean(self):
        picking = PickingParams(fixed_s=4.0, per_item_s=6.0)

        self.assertEqual(picking.sample(3, np.random.default_rng(0)), 22.0)


if __name__ == "__main__":
    unittest.main()
