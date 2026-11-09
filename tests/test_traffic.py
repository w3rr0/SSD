import unittest

from src.agents.robot import RobotState
from src.core.config import PickingParams, SimulationConfig
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order, OrderLine, PickTask
from src.pipeline.reservations import DeadlockError, LivelockError


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


class LivelockDetectionTests(unittest.TestCase):
    def make_model(self, limit=3):
        return Warehouse(
            num_robots=2,
            orders=[],
            config=SimulationConfig(livelock_yield_limit=limit),
        )

    def detour(self, robot):
        return (robot.pos,)

    def test_endless_giving_way_on_one_leg_raises(self):
        model = self.make_model(limit=3)
        robot = model.robots[0]
        robot.transition(RobotState.TO_RACK)
        for _ in range(3):
            model._begin_yield(robot, self.detour(robot))

        with self.assertRaises(LivelockError):
            model._begin_yield(robot, self.detour(robot))

    def test_livelock_is_a_deadlock_for_callers(self):
        self.assertTrue(issubclass(LivelockError, DeadlockError))

    def test_a_new_leg_starts_counting_again(self):
        model = self.make_model(limit=3)
        robot = model.robots[0]
        robot.transition(RobotState.TO_RACK)
        for _ in range(3):
            model._begin_yield(robot, self.detour(robot))
        robot.transition(RobotState.TO_STATION)

        model._begin_yield(robot, self.detour(robot))

        self.assertEqual(robot.yields_this_leg, 1)

    def test_a_failure_does_not_reset_the_leg(self):
        model = self.make_model(limit=3)
        robot = model.robots[0]
        robot.transition(RobotState.TO_RACK)
        model._begin_yield(robot, self.detour(robot))
        robot.fail()
        robot.repair()

        self.assertEqual(robot.yields_this_leg, 1)

    def test_idle_robots_making_room_are_not_counted(self):
        model = self.make_model(limit=1)
        robot = model.robots[0]
        for _ in range(5):
            model._begin_yield(robot, self.detour(robot))

        self.assertEqual(robot.yields_this_leg, 0)


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


class GroupCoordinationTests(unittest.TestCase):
    @staticmethod
    def _corridor(starts: dict[str, tuple[int, int]]) -> WarehouseLayout:
        return WarehouseLayout(
            width=20,
            height=3,
            blocked=frozenset((x, y) for x in range(20) for y in (0, 2)),
            robot_starts=starts,
        )

    def test_follower_shares_the_corridor_with_a_short_window(self):
        layout = self._corridor({"robot-1": (5, 1), "robot-2": (2, 1)})
        model = Warehouse(layout=layout, num_robots=2, orders=[])
        leader, follower = model.robots
        leader.set_route(tuple((x, 1) for x in range(6, 13)))
        leader.transition(RobotState.TO_RACK)
        follower.set_route(tuple((x, 1) for x in range(3, 13)))
        follower.transition(RobotState.TO_RACK)

        self.assertTrue(model._follows_same_direction(follower))
        model.extend_reservation(follower)

        self.assertEqual(
            model.reservations.window(follower.robot_id),
            ((2, 1), (3, 1)),
        )
        self.assertEqual(len(model.reservations.window(leader.robot_id)), 4)

    def test_opposite_direction_is_not_a_convoy(self):
        layout = self._corridor({"robot-1": (5, 1), "robot-2": (8, 1)})
        model = Warehouse(layout=layout, num_robots=2, orders=[])
        leader, oncoming = model.robots
        leader.set_route(tuple((x, 1) for x in range(6, 13)))
        leader.transition(RobotState.TO_RACK)
        oncoming.set_route(tuple((x, 1) for x in range(7, 0, -1)))
        oncoming.transition(RobotState.TO_RACK)

        self.assertFalse(model._follows_same_direction(oncoming))

    def test_leaders_beyond_the_window_do_not_shrink_it(self):
        layout = self._corridor({"robot-1": (10, 1), "robot-2": (0, 1)})
        model = Warehouse(layout=layout, num_robots=2, orders=[])
        leader, follower = model.robots
        leader.set_route(tuple((x, 1) for x in range(11, 19)))
        leader.transition(RobotState.TO_RACK)
        follower.set_route(tuple((x, 1) for x in range(1, 19)))
        follower.transition(RobotState.TO_RACK)

        self.assertFalse(model._follows_same_direction(follower))
        model.extend_reservation(follower)
        self.assertEqual(len(model.reservations.window(follower.robot_id)), 4)

    def test_follow_lookahead_must_fit_the_reservation_window(self):
        with self.assertRaises(ValueError):
            SimulationConfig(reservation_lookahead=2, follow_lookahead=3)
        with self.assertRaises(ValueError):
            SimulationConfig(follow_lookahead=0)

    def test_follower_pulls_up_behind_a_robot_serving_the_same_station(self):
        layout = WarehouseLayout(
            width=10,
            height=3,
            blocked=frozenset((x, y) for x in range(10) for y in (0, 2)),
            stations={"station-1": (0, 1)},
            robot_starts={"robot-1": (2, 1), "robot-2": (3, 1)},
        )
        model = Warehouse(layout=layout, num_robots=2, orders=[])
        leader, follower = model.robots
        for robot, rack_id in ((leader, "rack-1"), (follower, "rack-2")):
            task = PickTask(
                task_id=f"task-{robot.robot_id}",
                order_id="order-1",
                rack_id=rack_id,
                station_id="station-1",
                lines=(OrderLine("sku-1"),),
                created_time=0.0,
            )
            model.tasks_by_id[task.task_id] = task
            robot.assigned_task_id = task.task_id

        leader.transition(RobotState.TO_RACK)
        leader.transition(RobotState.TO_STATION)
        leader.transition(RobotState.QUEUED)
        model.grid.move_agent(leader, (0, 1))
        model.reservations.release_all(leader.robot_id)
        model.reservations.try_extend(leader.robot_id, ((0, 1),))

        follower.set_route(((2, 1), (1, 1), (0, 1)))
        follower.transition(RobotState.TO_RACK)
        follower.transition(RobotState.TO_STATION)

        self.assertTrue(model._follows_same_direction(follower))
        model.extend_reservation(follower)

        self.assertEqual(
            model.reservations.window(follower.robot_id),
            ((3, 1), (2, 1)),
        )

    def test_two_robots_are_served_one_after_another_at_one_station(self):
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
        self.assertEqual(len(station.wait_times), 2)
        self.assertGreaterEqual(max(station.wait_times), 5.0)


class WaitingTimeTests(unittest.TestCase):
    def test_standing_behind_another_robot_is_traffic_wait(self):
        layout = WarehouseLayout(
            width=5,
            height=3,
            blocked=frozenset((x, y) for x in range(5) for y in (0, 2)),
            racks={"rack-1": (0, 1)},
            stations={"station-1": (4, 1)},
            robot_starts={"robot-1": (1, 1), "robot-2": (2, 1)},
        )
        model = Warehouse(
            layout=layout,
            num_robots=2,
            orders=[],
            config=SimulationConfig(deadlock_timeout_s=100.0),
        )
        first, second = model.robots
        first.set_route(((2, 1), (3, 1), (4, 1)))
        first.transition(RobotState.TO_RACK)
        second.set_route(((1, 1), (0, 1)))
        second.transition(RobotState.TO_RACK)

        for _ in range(5):
            model.step()

        metrics = model.metrics
        self.assertEqual(first.traffic_wait_s, 5.0)
        self.assertEqual(second.traffic_wait_s, 5.0)
        self.assertEqual(metrics.total_traffic_wait_s, 10.0)
        self.assertAlmostEqual(metrics.average_traffic_wait_s, 5.0)
        self.assertAlmostEqual(metrics.traffic_wait_share, 1.0)

    def test_station_queue_wait_is_not_counted_as_traffic(self):
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

        metrics = model.run_until_complete()

        self.assertEqual(metrics.total_traffic_wait_s, 0.0)
        self.assertGreater(metrics.total_queue_wait_s, 0.0)
        self.assertEqual(
            metrics.total_queue_wait_s,
            sum(model.stations["station-1"].wait_times),
        )
        self.assertGreater(metrics.queue_wait_share, 0.0)
        self.assertLessEqual(metrics.queue_wait_share, 1.0)


class StationQueueClockTests(unittest.TestCase):
    """Only a robot bringing a rack to the station is in its queue."""

    def _model(self):
        # One-cell corridor: rack slots on the left, the station on the right.
        layout = WarehouseLayout(
            width=7,
            height=3,
            blocked=frozenset((x, y) for x in range(7) for y in (0, 2)),
            racks={"rack-1": (0, 1)},
            stations={"station-1": (6, 1)},
            robot_starts={"robot-1": (5, 1), "robot-2": (4, 1)},
        )
        model = Warehouse(layout=layout, num_robots=2, orders=[])
        for number, robot in enumerate(model.robots, start=1):
            task = PickTask(
                task_id=f"o{number}/1",
                order_id=f"o{number}",
                rack_id="rack-1",
                station_id="station-1",
                lines=(OrderLine("sku-1"),),
                created_time=0.0,
            )
            model.tasks_by_id[task.task_id] = task
            robot.assigned_task_id = task.task_id
        return model

    @staticmethod
    def _block(robot, cell, holder):
        robot.blocked = True
        robot.blocked_cell = cell
        robot.blocked_by = holder

    def test_robot_behind_the_queue_with_a_rack_for_the_station_queues(self):
        model = self._model()
        first, second = model.robots
        first.transition(RobotState.TO_RACK)
        first.transition(RobotState.TO_STATION)
        second.transition(RobotState.TO_RACK)
        second.transition(RobotState.TO_STATION)
        self._block(first, (6, 1), "robot-x")
        self._block(second, (5, 1), "robot-1")

        model._record_station_waits()

        self.assertEqual(set(model._station_wait_started), {"robot-1", "robot-2"})

    def test_robot_taking_a_rack_back_is_not_in_the_queue(self):
        # robot-2 already picked at station-1 and drives its rack home; it
        # only stands behind robot-1, which waits for the same station.
        model = self._model()
        first, second = model.robots
        first.transition(RobotState.TO_RACK)
        first.transition(RobotState.TO_STATION)
        second.transition(RobotState.TO_RACK)
        second.transition(RobotState.TO_STATION)
        second.transition(RobotState.QUEUED)
        second.transition(RobotState.PICKING)
        second.transition(RobotState.RETURNING_RACK)
        self._block(first, (6, 1), "robot-x")
        self._block(second, (5, 1), "robot-1")

        model._record_station_waits()

        self.assertEqual(set(model._station_wait_started), {"robot-1"})

    def test_robot_on_its_way_to_the_rack_is_not_in_the_queue(self):
        model = self._model()
        first, second = model.robots
        first.transition(RobotState.TO_RACK)
        first.transition(RobotState.TO_STATION)
        second.transition(RobotState.TO_RACK)
        self._block(first, (6, 1), "robot-x")
        self._block(second, (5, 1), "robot-1")

        model._record_station_waits()

        self.assertNotIn("robot-2", model._station_wait_started)


class IdleBlockerChainTests(unittest.TestCase):
    def test_boxed_idle_blockers_are_moved_as_a_chain(self):
        # Bottom row with the wall below it (outside the grid), racks directly
        # above the middle robot and idle robots on both sides. This is the
        # layout that produced "robot-4 made no progress ... at (4, 0)": the
        # middle robot cannot move alone, so the whole chain has to shift.
        layout = WarehouseLayout(
            width=10,
            height=2,
            blocked=frozenset(),
            racks={
                "rack-1": (3, 1),
                "rack-2": (4, 1),
                "rack-3": (5, 1),
            },
            stations={"station-1": (9, 0)},
            robot_starts={
                "robot-1": (2, 0),
                "robot-2": (3, 0),
                "robot-3": (4, 0),
                "robot-4": (5, 0),
            },
        )
        model = Warehouse(
            layout=layout,
            num_robots=4,
            orders=[],
            config=SimulationConfig(deadlock_timeout_s=100.0),
        )
        working = model.robots[0]
        working.set_route(((3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0)))
        working.transition(RobotState.TO_RACK)

        for _ in range(20):
            model.step()

        self.assertGreaterEqual(working.pos[0], 5)


if __name__ == "__main__":
    unittest.main()
