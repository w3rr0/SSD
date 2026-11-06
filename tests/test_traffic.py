import unittest

from src.agents.robot import RobotState
from src.core.config import PickingParams, SimulationConfig
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order
from src.pipeline.reservations import DeadlockError


class CollisionFreeTrafficTests(unittest.TestCase):
    def test_robots_never_share_a_cell_or_enter_walls(self):
        model = Warehouse(num_robots=5, num_orders=15, rng=7)

        for _ in range(600):
            model.step()
            positions = [robot.pos for robot in model.robots]
            self.assertEqual(
                len(positions),
                len(set(positions)),
                f"two robots share a cell at t={model.time}: {positions}",
            )
            for robot in model.robots:
                self.assertTrue(
                    model.layout.is_walkable(robot.pos),
                    f"{robot.robot_id} entered a blocked cell at {robot.pos}",
                )
            if model.all_orders_completed:
                break

    def test_custom_conflict_policy_is_used_by_the_warehouse(self):
        model = Warehouse(
            num_robots=2,
            resolve_conflict=lambda first, second: second,
        )

        self.assertEqual(
            model.reservations.resolve("robot-1", "robot-2"), "robot-2"
        )


class DeadlockDetectionTests(unittest.TestCase):
    def test_two_robot_cycle_is_detected(self):
        waits = {"robot-1": "robot-2", "robot-2": "robot-1"}

        cycle = Warehouse._find_deadlock_cycle(waits)

        self.assertEqual(cycle, frozenset({"robot-1", "robot-2"}))

    def test_chain_without_a_cycle_is_not_reported(self):
        waits = {"robot-1": "robot-2", "robot-2": "robot-3"}

        self.assertIsNone(Warehouse._find_deadlock_cycle(waits))

    def test_unavoidable_deadlock_raises_in_a_single_cell_corridor(self):
        corridor = WarehouseLayout(
            width=5,
            height=3,
            blocked=frozenset(
                (x, y) for x in range(5) for y in (0, 2)
            ),
            racks={"rack-1": (0, 1)},
            stations={"station-1": (4, 1)},
            robot_starts={"robot-1": (1, 1), "robot-2": (2, 1)},
        )
        model = Warehouse(
            layout=corridor,
            num_robots=2,
            orders=[],
            config=SimulationConfig(deadlock_timeout_s=5.0),
        )
        first, second = model.robots
        first.set_route(((2, 1), (3, 1), (4, 1)))
        first.transition(RobotState.TO_RACK)
        second.set_route(((1, 1), (0, 1)))
        second.transition(RobotState.TO_RACK)

        with self.assertRaises(DeadlockError):
            for _ in range(50):
                model.step()


class IdleBlockerTests(unittest.TestCase):
    def test_idle_robot_steps_aside_for_a_working_one(self):
        layout = WarehouseLayout(
            width=6,
            height=3,
            racks={"rack-1": (5, 1)},
            stations={"station-1": (0, 1)},
            robot_starts={"robot-1": (2, 0), "robot-2": (3, 0)},
        )
        model = Warehouse(layout=layout, num_robots=2, orders=[])
        idle, working = model.robots
        working.set_route(((2, 0), (1, 0), (0, 0)))
        working.transition(RobotState.TO_RACK)

        model.step()
        self.assertTrue(idle.yielding)
        self.assertNotEqual(idle.route, ())

        model.step()
        self.assertNotEqual(idle.pos, (2, 0))
        self.assertNotEqual(working.pos, (3, 0))


class StationApproachWaitTests(unittest.TestCase):
    def test_waiting_before_the_station_cell_counts_as_queue_time(self):
        layout = WarehouseLayout(
            width=5,
            height=3,
            racks={"rack-1": (1, 1), "rack-2": (3, 1)},
            stations={"station-1": (2, 1)},
            robot_starts={"robot-1": (1, 0), "robot-2": (3, 0)},
        )
        picking = PickingParams(fixed_s=10.0, per_item_s=0.0)
        orders = [Order("o1", ["sku-1"]), Order("o2", ["sku-2"])]
        model = Warehouse(
            layout=layout,
            num_robots=2,
            orders=orders,
            config=SimulationConfig(picking=picking),
        )

        model.run_until_complete()

        station = model.stations["station-1"]
        self.assertEqual(station.served, 2)
        self.assertTrue(
            any(wait >= 5.0 for wait in station.wait_times),
            f"expected a robot to wait for the station, got {station.wait_times}",
        )
        self.assertFalse(model._station_wait_started)


if __name__ == "__main__":
    unittest.main()
