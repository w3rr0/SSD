"""Queueing validation, part A: the picking station on its own.

The station gets robots at Poisson-distributed moments directly, without the
grid, racks or driving, so every assumption of the M/G/1 formula holds and
the measured mean wait has to match it closely.
"""

import unittest

from mesa import Model

from src.agents.warehouse_objects import PickingStation
from src.core.config import PickingParams
from src.validation.queueing import (
    arrival_rate_for,
    confidence_interval,
    mg1_wait,
    service_moments,
)

CUSTOMERS = 100_000
WARM_UP = 2_000  # first visits start with an empty queue, left out


class _Visitor:
    """Stands in for a robot: the station only queues it and asks its ID."""

    def __init__(self, robot_id: str):
        self.robot_id = robot_id

    def transition(self, state) -> None:
        pass


class StationOnlyModel(Model):
    """Just one picking station and Poisson arrivals, nothing else."""

    def __init__(self, picking: PickingParams, utilisation: float, rng: int):
        super().__init__(rng=rng)
        # Pure event-driven run: no movement ticks are needed.
        self._default_schedule.stop()
        self.picking = picking
        self.station = PickingStation(self, "station-1")
        mean_s, _ = service_moments(picking, items=1)
        self.arrival_rate = arrival_rate_for(utilisation, mean_s)
        self.arrived = 0
        self.schedule_event(self.arrive, after=self._gap())

    def _gap(self) -> float:
        return float(self.rng.exponential(1 / self.arrival_rate))

    def arrive(self) -> None:
        self.arrived += 1
        self.station.enqueue(_Visitor(f"visitor-{self.arrived}"))
        if self.arrived < CUSTOMERS:
            self.schedule_event(self.arrive, after=self._gap())

    def pick_duration(self, robot) -> float:
        return self.picking.sample(1, self.rng)

    def on_pick_finished(self, robot, station) -> None:
        pass

    def mean_wait(self) -> float:
        waits = self.station.wait_times[WARM_UP:]
        return sum(waits) / len(waits)


class FormulaTests(unittest.TestCase):
    def test_md1_by_hand(self):
        # S = 15 s, one robot per 30 s -> rho 0.5, Wq = 0.5 * 15 / (2 * 0.5)
        self.assertAlmostEqual(mg1_wait(1 / 30, 15.0, 15.0**2), 7.5)

    def test_mm1_is_twice_md1(self):
        self.assertAlmostEqual(mg1_wait(1 / 30, 15.0, 2 * 15.0**2), 15.0)

    def test_service_moments(self):
        picking = PickingParams(fixed_s=5.0, per_item_s=10.0)
        self.assertEqual(service_moments(picking, 1), (15.0, 225.0))
        exponential = PickingParams(5.0, 10.0, "exponential")
        self.assertEqual(service_moments(exponential, 2), (25.0, 1250.0))

    def test_unstable_queue_is_rejected(self):
        with self.assertRaises(ValueError):
            mg1_wait(1 / 10, 15.0, 225.0)

    def test_confidence_interval(self):
        centre, half = confidence_interval([1.0, 2.0, 3.0])
        self.assertEqual(centre, 2.0)
        self.assertAlmostEqual(half, 2.484, places=3)  # t(0.975, 2) * 1 / sqrt(3)


class StationMatchesFormulaTests(unittest.TestCase):
    """Simulated mean wait close to the formula.

    Tolerances come from 30 seeds: the largest error was 3.5% at
    utilisation 0.5 and 8.8% at 0.8 (a busier queue varies more).
    """

    def check(self, distribution: str, utilisation: float, tolerance: float) -> None:
        picking = PickingParams(fixed_s=5.0, per_item_s=10.0, distribution=distribution)
        model = StationOnlyModel(picking, utilisation, rng=7)
        model.run_for(10**9)
        mean_s, second = service_moments(picking, items=1)
        expected = mg1_wait(model.arrival_rate, mean_s, second)
        self.assertEqual(model.station.served, CUSTOMERS)
        self.assertAlmostEqual(model.mean_wait(), expected, delta=tolerance * expected)

    def test_deterministic_service(self):
        self.check("deterministic", 0.5, tolerance=0.05)

    def test_exponential_service(self):
        self.check("exponential", 0.5, tolerance=0.05)

    def test_busy_station(self):
        self.check("deterministic", 0.8, tolerance=0.10)


if __name__ == "__main__":
    unittest.main()
