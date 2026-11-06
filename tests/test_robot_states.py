import unittest

from src.agents.robot import InvalidTransitionError, RobotState
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout


class RobotStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.layout = WarehouseLayout(
            width=7,
            height=5,
            blocked=frozenset({(3, 0), (3, 1), (3, 2), (3, 3)}),
            racks={"rack-1": (5, 2)},
            stations={"station-1": (1, 0)},
            robot_starts={"robot-1": (1, 2)},
        )

    def test_robot_goes_through_the_order_cycle(self):
        model = Warehouse(layout=self.layout)
        robot = model.robots[0]

        model.run_until_complete()

        visited = [state for _, state in robot.state_history]
        self.assertEqual(
            visited,
            [
                RobotState.IDLE,
                RobotState.TO_RACK,
                RobotState.TO_STATION,
                RobotState.IDLE,
            ],
        )
        self.assertIs(robot.state, RobotState.IDLE)

    def test_time_in_states_adds_up_to_the_clock(self):
        model = Warehouse(layout=self.layout)
        robot = model.robots[0]

        model.run_until_complete()
        model.run_for(5)

        totals = robot.time_in_state()
        self.assertAlmostEqual(sum(totals.values()), model.time)
        self.assertGreater(totals[RobotState.TO_RACK], 0)
        self.assertGreater(totals[RobotState.TO_STATION], 0)

    def test_forbidden_transition_raises(self):
        model = Warehouse(layout=self.layout, orders=[])
        robot = model.robots[0]

        with self.assertRaises(InvalidTransitionError):
            robot.transition(RobotState.PICKING)

    def test_idle_robot_does_not_move(self):
        model = Warehouse(layout=self.layout, orders=[])
        robot = model.robots[0]
        start = robot.pos

        model.run_for(10)

        self.assertEqual(robot.pos, start)
        self.assertEqual(robot.distance_travelled_m, 0)


if __name__ == "__main__":
    unittest.main()
