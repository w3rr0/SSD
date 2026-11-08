import unittest

from src.pipeline.reservations import (
    ReservationConflict,
    ReservationTable,
    lowest_id_wins,
)


class ConflictPolicyTests(unittest.TestCase):
    def test_lowest_id_wins(self):
        self.assertEqual(lowest_id_wins("robot-2", "robot-1"), "robot-1")
        self.assertEqual(lowest_id_wins("robot-1", "robot-2"), "robot-1")

    def test_lowest_id_wins_compares_numeric_suffixes(self):
        self.assertEqual(lowest_id_wins("robot-10", "robot-2"), "robot-2")
        self.assertEqual(lowest_id_wins("robot-2", "robot-10"), "robot-2")

    def test_custom_policy_can_be_used(self):
        table = ReservationTable(resolve_conflict=lambda a, b: b)

        self.assertEqual(table.resolve("robot-1", "robot-2"), "robot-2")

    def test_invalid_policy_result_is_rejected(self):
        table = ReservationTable(resolve_conflict=lambda a, b: "someone-else")

        with self.assertRaises(ValueError):
            table.resolve("robot-1", "robot-2")

    def test_lookahead_must_be_positive(self):
        with self.assertRaises(ValueError):
            ReservationTable(lookahead=0)


class ReservationWindowTests(unittest.TestCase):
    def setUp(self):
        self.table = ReservationTable(lookahead=2)

    def test_reserves_current_cell_and_lookahead(self):
        newly = self.table.try_extend(
            "robot-1", [(0, 0), (1, 0), (2, 0), (3, 0)]
        )

        self.assertEqual(newly, ((0, 0), (1, 0), (2, 0)))
        self.assertEqual(
            self.table.window("robot-1"), ((0, 0), (1, 0), (2, 0))
        )
        self.assertEqual(self.table.owner((1, 0)), "robot-1")
        self.assertIsNone(self.table.owner((3, 0)))

    def test_explicit_window_size_limits_reservations(self):
        newly = self.table.try_extend(
            "robot-1", [(0, 0), (1, 0), (2, 0)], max_window=2
        )

        self.assertEqual(newly, ((0, 0), (1, 0)))

    def test_window_stops_at_a_foreign_cell(self):
        self.table.try_extend("robot-1", [(1, 0), (2, 0)])

        newly = self.table.try_extend("robot-2", [(0, 1), (1, 0), (3, 0)])

        self.assertEqual(newly, ((0, 1),))
        self.assertEqual(self.table.window("robot-2"), ((0, 1),))

    def test_conflict_reports_requester_holder_and_cell(self):
        self.table.try_extend("robot-1", [(1, 0)])

        conflict = self.table.conflict("robot-2", (1, 0))

        self.assertEqual(
            conflict, ReservationConflict("robot-2", "robot-1", (1, 0))
        )
        self.assertIsNone(self.table.conflict("robot-1", (1, 0)))

    def test_repeated_extension_keeps_the_window_contiguous(self):
        self.table.try_extend("robot-1", [(0, 0), (1, 0), (2, 0)])
        self.table.release_passed("robot-1", (0, 0))

        newly = self.table.try_extend("robot-1", [(1, 0), (2, 0), (3, 0)])

        self.assertEqual(newly, ((3, 0),))
        self.assertEqual(
            self.table.window("robot-1"),
            ((1, 0), (2, 0), (3, 0)),
        )

    def test_full_window_does_not_grow(self):
        self.table.try_extend("robot-1", [(0, 0), (1, 0), (2, 0)])

        newly = self.table.try_extend("robot-1", [(3, 0)])

        self.assertEqual(newly, ())
        self.assertEqual(
            self.table.window("robot-1"),
            ((0, 0), (1, 0), (2, 0)),
        )


class ReservationReleaseTests(unittest.TestCase):
    def setUp(self):
        self.table = ReservationTable(lookahead=3)
        self.table.try_extend(
            "robot-1", [(0, 0), (1, 0), (2, 0), (3, 0)]
        )

    def test_release_passed_frees_the_prefix(self):
        released = self.table.release_passed("robot-1", (1, 0))

        self.assertEqual(released, ((0, 0), (1, 0)))
        self.assertEqual(self.table.window("robot-1"), ((2, 0), (3, 0)))
        self.assertIsNone(self.table.owner((0, 0)))
        self.assertIsNone(self.table.owner((1, 0)))
        self.assertEqual(self.table.owner((2, 0)), "robot-1")

    def test_release_from_frees_the_suffix(self):
        released = self.table.release_from("robot-1", (2, 0))

        self.assertEqual(released, ((2, 0), (3, 0)))
        self.assertEqual(self.table.window("robot-1"), ((0, 0), (1, 0)))
        self.assertIsNone(self.table.owner((2, 0)))
        self.assertEqual(self.table.owner((1, 0)), "robot-1")

    def test_release_all_clears_every_cell(self):
        released = self.table.release_all("robot-1")

        self.assertEqual(released, ((0, 0), (1, 0), (2, 0), (3, 0)))
        self.assertEqual(self.table.window("robot-1"), ())
        self.assertIsNone(self.table.owner((0, 0)))

    def test_releasing_an_unknown_cell_changes_nothing(self):
        released = self.table.release_passed("robot-1", (9, 9))

        self.assertEqual(released, ())
        self.assertEqual(len(self.table.window("robot-1")), 4)


class PreemptionTests(unittest.TestCase):
    def setUp(self):
        self.table = ReservationTable(lookahead=3)

    def test_higher_priority_can_take_a_later_cell(self):
        self.table.try_extend("robot-1", [(0, 0), (1, 0)])
        self.table.try_extend("robot-2", [(1, 1), (2, 0), (3, 0)])

        newly = self.table.try_extend("robot-1", [(2, 0)], preempt=True)

        self.assertEqual(newly, ((2, 0),))
        self.assertEqual(self.table.owner((2, 0)), "robot-1")
        self.assertEqual(self.table.window("robot-2"), ((1, 1),))

    def test_immediate_next_cell_is_protected_from_preemption(self):
        self.table.try_extend("robot-2", [(1, 0), (2, 0)])

        newly = self.table.try_extend("robot-1", [(0, 0), (1, 0)], preempt=True)

        self.assertEqual(newly, ((0, 0),))
        self.assertEqual(self.table.owner((1, 0)), "robot-2")
        self.assertEqual(self.table.window("robot-2"), ((1, 0), (2, 0)))

    def test_lower_priority_cannot_preempt(self):
        self.table.try_extend("robot-1", [(1, 1), (2, 0), (3, 0)])

        newly = self.table.try_extend(
            "robot-2", [(0, 0), (1, 0), (2, 0)], preempt=True
        )

        self.assertEqual(newly, ((0, 0), (1, 0)))
        self.assertEqual(self.table.owner((2, 0)), "robot-1")

    def test_preemption_is_off_by_default(self):
        self.table.try_extend("robot-1", [(1, 1), (2, 0)])

        newly = self.table.try_extend("robot-2", [(0, 0), (2, 0)])

        self.assertEqual(newly, ((0, 0),))
        self.assertEqual(self.table.owner((2, 0)), "robot-1")


if __name__ == "__main__":
    unittest.main()
