import unittest
from dataclasses import replace
from unittest import mock

import pandas as pd

from src.data.olist import OlistStats
from src.experiments import scenarios as sc
from src.experiments.scenarios import Scenario
from src.pipeline.reservations import DeadlockError


def make_stats(rate_per_hour=0.2):
    """A tiny catalogue with a flat profile (about 5 orders/day at x1)."""
    profile = pd.DataFrame(rate_per_hour, index=range(7), columns=range(24))
    popularity = pd.DataFrame(
        {"orders": [6, 3, 1], "order_share": [0.6, 0.3, 0.1]},
        index=pd.Index(["A", "B", "C"], name="product_id"),
    )
    return OlistStats(
        items_per_order=pd.Series({1: 1.0}),
        quantity_per_line=pd.Series({1: 1.0}),
        arrival_profile=profile,
        daily_counts=pd.Series(dtype=float),
        product_popularity=popularity,
        lead_time=pd.Series([2 * 86400.0]),
    )


class ScenarioDefinitionTests(unittest.TestCase):
    def test_reference_config_matches_robot_parameters(self):
        config = Scenario("S1").config()
        self.assertAlmostEqual(config.robot.speed_m_per_s, 1.3)
        self.assertAlmostEqual(config.picking.per_item_s, 6.0)
        self.assertAlmostEqual(config.robot.battery_drain_pct_per_m, 100 / 9360)

    def test_battery_is_a_distance_independent_of_speed(self):
        slow = Scenario("S5", speed_m_per_s=1.0).config()
        self.assertAlmostEqual(slow.robot.battery_drain_pct_per_m, 100 / 9360)
        short = Scenario("S5", battery_hours=1.0).config()
        self.assertAlmostEqual(short.robot.battery_drain_pct_per_m, 2 * 100 / 9360)

    def test_peak_is_base_volume_times_multiplier(self):
        self.assertEqual(Scenario("S1").volume_factor, sc.BASE_VOLUME)
        self.assertEqual(
            Scenario("S1", day="peak").volume_factor, sc.BASE_VOLUME * sc.PEAK_MULTIPLIER
        )

    def test_groups_vary_one_parameter_at_a_time(self):
        self.assertEqual(len(sc.scenarios(["S3"])), 7)
        self.assertEqual(len(sc.scenarios(["S5"])), 16)
        self.assertEqual(len(sc.scenarios(["S6"])), 2)
        keys = [s.key for s in sc.scenarios()]
        self.assertEqual(len(keys), len(set(keys)))


class RunTests(unittest.TestCase):
    stats = make_stats()

    def test_same_seed_gives_same_orders_whatever_the_fleet(self):
        small = sc.build_model(Scenario("S1", robots=2), seed=3, stats=self.stats)
        large = sc.build_model(Scenario("S1", robots=6), seed=3, stats=self.stats)
        self.assertEqual(
            [(o.created_time, o.skus) for o in small.orders],
            [(o.created_time, o.skus) for o in large.orders],
        )

    def test_a_quiet_day_finishes(self):
        row = sc.run_one(Scenario("S1", robots=2), seed=1, stats=self.stats)
        self.assertEqual(row["status"], "ok", row["error"])
        self.assertEqual(row["unfinished_at_day_end"], 0)
        self.assertEqual(row["completed_in_day"], row["orders_generated"])
        self.assertIn("station_utilisation_mean", row)

    def test_deadlock_marks_the_run_as_failed(self):
        with mock.patch.object(
            sc.ScenarioWarehouse, "run_until_complete", side_effect=DeadlockError("stuck")
        ):
            row = sc.run_one(Scenario("S1", robots=2), seed=1, stats=self.stats)
        self.assertEqual(row["status"], "failed")
        self.assertIn("DeadlockError", row["error"])

    def test_other_exception_is_an_error_not_a_failure(self):
        with mock.patch.object(
            sc.ScenarioWarehouse, "run_until_complete", side_effect=KeyError("bug")
        ):
            row = sc.run_one(Scenario("S1", robots=2), seed=1, stats=self.stats)
        self.assertEqual(row["status"], "error")

    def test_nearest_free_slot_policy_is_used(self):
        model = sc.build_model(
            Scenario("S1", robots=2, return_policy="nearest"), seed=1, stats=self.stats
        )
        self.assertIsNotNone(model.nearest_free_slot)


class SummaryTests(unittest.TestCase):
    def runs(self):
        first, second = Scenario("S1", robots=2), Scenario("S1", robots=4)
        data = [
            (first, 1, "ok", 30.0), (first, 2, "ok", 32.0), (first, 3, "ok", 34.0),
            (first, 4, "ok", 36.0),
            (second, 1, "ok", 20.0), (second, 2, "ok", 21.0), (second, 3, "ok", 22.0),
            (second, 4, "failed", None),
        ]
        rows = []
        for scenario, seed, status, value in data:
            row = {"scenario": scenario.key, "seed": seed, "status": status}
            row.update({f: getattr(scenario, f) for f in scenario.__dataclass_fields__})
            row.update({metric: value for metric in sc.SUMMARY_METRICS})
            rows.append(row)
        return pd.DataFrame(rows), first.key, second.key

    def test_failed_runs_are_counted_but_left_out_of_means(self):
        runs, _, second = self.runs()
        summary = sc.summarise(runs).set_index("scenario")
        self.assertEqual(summary.loc[second, "ok"], 3)
        self.assertEqual(summary.loc[second, "failed"], 1)
        self.assertAlmostEqual(summary.loc[second, "average_completion_time"], 21.0)
        self.assertTrue(summary.loc[second, "unreliable"])

    def test_paired_difference_uses_seeds_ok_in_both(self):
        runs, first, second = self.runs()
        mean, half, n = sc.paired_difference(runs, first, second, "average_completion_time")
        self.assertEqual(n, 3)
        self.assertAlmostEqual(mean, 11.0)
        self.assertGreater(half, 0)

    def test_replications_needed_grows_with_spread(self):
        tight = sc.replications_needed([100, 101, 99, 100, 100])
        wide = sc.replications_needed([60, 140, 80, 120, 100])
        self.assertEqual(tight, 5)
        self.assertGreater(wide, 20)


if __name__ == "__main__":
    unittest.main()
