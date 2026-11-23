import importlib.util
import unittest
from pathlib import Path
from unittest import mock

from src.pipeline.reservations import DeadlockError

_PATH = Path(__file__).resolve().parents[1] / "runners" / "queue_validation.py"
_SPEC = importlib.util.spec_from_file_location("queue_validation", _PATH)
qv = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qv)


def run(wait: float, utilisation: float) -> dict[str, float]:
    return {"wait": wait, "utilisation": utilisation, "wait_for_robot": 1.0}


class SummariseTests(unittest.TestCase):
    def test_deadlocked_runs_are_left_out_and_counted(self):
        runs = [run(7.4, 0.5), run(7.6, 0.5), None]

        row = qv.summarise("deterministic", 0.5, runs)

        self.assertEqual(row["failed"], 1)
        self.assertAlmostEqual(row["centre"], 7.5)
        self.assertTrue(row["unreliable"])  # 1 of 3 > 10%

    def test_formula_inside_the_interval_is_ok(self):
        # M/D/1 at rho = 0.5 with a 15 s service: 7.5 s.
        row = qv.summarise("deterministic", 0.5, [run(7.0, 0.5), run(8.0, 0.5)])

        self.assertAlmostEqual(row["expected"], 7.5)
        self.assertEqual(row["result"], "OK")
        self.assertFalse(row["unreliable"])

    def test_station_below_target_utilisation_is_limit(self):
        row = qv.summarise("deterministic", 0.9, [run(26.0, 0.78), run(26.5, 0.78)])

        self.assertEqual(row["result"], "LIMIT")

    def test_all_runs_failed_gives_no_data(self):
        row = qv.summarise("exponential", 0.9, [None, None])

        self.assertEqual(row["result"], "NO DATA")
        self.assertIn("NO DATA", qv._format(row))

    def test_a_deadlock_does_not_stop_the_batch(self):
        with mock.patch.object(qv, "run_once", side_effect=DeadlockError("stuck")):
            self.assertIsNone(qv._run(("deterministic", 0.3, 0)))


if __name__ == "__main__":
    unittest.main()
