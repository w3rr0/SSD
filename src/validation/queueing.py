"""Queueing-theory formulas used to validate the simulation.

A picking station is a single-server FIFO queue. When robots arrive as a
Poisson process (rate ``lambda``) and service times S are independent, the
station is an M/G/1 queue and the mean wait in the queue (before picking
starts) is the Pollaczek-Khinchine formula::

    Wq = lambda * E[S^2] / (2 * (1 - rho)),   rho = lambda * E[S]

Special cases: constant service (M/D/1) gives rho * E[S] / (2 * (1 - rho)),
exponential service (M/M/1) twice that.
"""

from collections.abc import Sequence
from statistics import mean, stdev

from scipy import stats

from src.core.config import PickingParams


def mg1_wait(arrival_rate: float, mean_service: float, second_moment: float) -> float:
    """Mean wait in the queue of an M/G/1 system (Pollaczek-Khinchine)."""
    if arrival_rate <= 0 or mean_service <= 0:
        raise ValueError("Arrival rate and service time must be positive")
    rho = arrival_rate * mean_service
    if rho >= 1:
        raise ValueError(f"Unstable queue: utilisation {rho:.2f} >= 1")
    return arrival_rate * second_moment / (2 * (1 - rho))


def service_moments(picking: PickingParams, items: int) -> tuple[float, float]:
    """E[S] and E[S^2] of one rack visit with ``items`` units."""
    mean_s = picking.mean_duration(items)
    if picking.distribution == "exponential":
        return mean_s, 2 * mean_s**2
    return mean_s, mean_s**2


def arrival_rate_for(utilisation: float, mean_service: float) -> float:
    """Arrivals per second that keep the station busy ``utilisation`` of the time."""
    if not 0 < utilisation < 1:
        raise ValueError("Utilisation must be between 0 and 1")
    return utilisation / mean_service


def confidence_interval(values: Sequence[float], level: float = 0.95) -> tuple[float, float]:
    """Mean of independent replications and the half-width of its t interval."""
    if len(values) < 2:
        raise ValueError("Need at least two replications")
    t = stats.t.ppf((1 + level) / 2, df=len(values) - 1)
    return mean(values), t * stdev(values) / len(values) ** 0.5
