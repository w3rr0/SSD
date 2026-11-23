"""Traffic rules that keep robots out of deadlocks (``TrafficParams``)."""

import unittest

from src.agents.robot import RobotState
from src.core.config import SimulationConfig, TrafficParams
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.pipeline.pathfinding import TrafficRules, astar_path

# Two corridor rows (y = 0 and y = 3) around one row of racks, a station on
# the left wall and a charger on the right wall.
LAYOUT = WarehouseLayout.from_ascii(
    [
        "#........#",
        "S.RRRRRR.C",
        "#.RRRRRR.#",
        "#BB......#",
    ],
    top_down=True,
)


def model(traffic=None, num_robots=2, orders=()):
    config = SimulationConfig(traffic=traffic or TrafficParams())
    return Warehouse(layout=LAYOUT, num_robots=num_robots, orders=list(orders), config=config)


class EmptyRobotsUnderRacksTests(unittest.TestCase):
    def test_empty_robot_ignores_standing_racks(self):
        warehouse = model()
        robot = warehouse.robots[0]

        obstacles = warehouse._obstacles(robot)

        self.assertFalse(set(LAYOUT.racks.values()) & obstacles)
        self.assertIn(LAYOUT.stations["station-1"], obstacles)

    def test_loaded_robot_and_old_rules_still_avoid_racks(self):
        warehouse = model()
        robot = warehouse.robots[0]
        robot.carrying_rack_id = "rack-1"
        self.assertTrue(set(LAYOUT.racks.values()) <= warehouse._obstacles(robot))

        old = model(TrafficParams.off())
        self.assertTrue(
            set(LAYOUT.racks.values()) <= old._obstacles(old.robots[0])
        )


class OneWayAisleTests(unittest.TestCase):
    def test_corridor_rows_get_opposite_directions(self):
        rules = TrafficRules.from_layout(LAYOUT)

        self.assertEqual(sorted(rules.row_direction), [0, 3])
        self.assertNotEqual(rules.row_direction[0], rules.row_direction[3])

    def test_driving_against_the_lane_costs_more_but_stays_allowed(self):
        rules = TrafficRules.from_layout(LAYOUT)
        y = 0
        forward = (5 + rules.row_direction[y], y)
        backward = (5 - rules.row_direction[y], y)

        self.assertEqual(rules.step_cost((5, y), forward, goal=(0, 3)), 1)
        self.assertEqual(
            rules.step_cost((5, y), backward, goal=(0, 3)),
            1 + rules.against_lane_cost,
        )
        route = astar_path(
            LAYOUT, (8, 0), (1, 0), set(LAYOUT.racks.values()), rules
        )
        self.assertEqual(route[0], (8, 0))
        self.assertEqual(route[-1], (1, 0))

    def test_passing_traffic_avoids_the_front_of_a_station(self):
        rules = TrafficRules.from_layout(LAYOUT)
        front = (1, 2)  # the only cell next to the station at (0, 2)

        self.assertGreater(rules.step_cost((1, 3), front, goal=(1, 0)), 1)
        self.assertEqual(
            rules.step_cost((1, 3), front, goal=LAYOUT.stations["station-1"]),
            1 + rules.against_lane_cost * (rules.column_direction.get(1) == 1),
        )


class StationRulesTests(unittest.TestCase):
    def test_robot_waits_under_rack_while_the_station_is_full(self):
        warehouse = model(TrafficParams(station_queue_limit=1))
        first, second = warehouse.robots
        first.state = RobotState.TO_STATION
        warehouse.tasks_by_id["t1"] = type(
            "T", (), {"station_id": "station-1"}
        )()
        first.assigned_task_id = "t1"

        self.assertTrue(warehouse._station_is_full("station-1", second))
        self.assertFalse(
            model(TrafficParams(station_queue_limit=0))._station_is_full(
                "station-1", second
            )
        )

    def test_charged_robot_leaves_the_charger(self):
        warehouse = model()
        robot = warehouse.robots[0]
        charger = warehouse.chargers["charger-1"]
        warehouse.grid.move_agent(robot, LAYOUT.chargers["charger-1"])
        warehouse.reset_reservation(robot)
        robot.state = RobotState.CHARGING

        warehouse.on_charge_finished(robot, charger)

        self.assertTrue(robot.yielding)
        self.assertTrue(robot.route)
        self.assertNotEqual(robot.route[-1], LAYOUT.chargers["charger-1"])


if __name__ == "__main__":
    unittest.main()
