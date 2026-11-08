from dataclasses import dataclass, field
from typing import Literal

import numpy as np

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True, slots=True)
class RobotParams:
    """Physical robot parameters shared by the whole fleet.

    ``initial_battery_pct`` is the charge every robot starts a run with; change
    it here to exercise the charging path without touching individual robots.

    Defaults come from Kiva publications; sources and conversions are listed
    in ``docs/zrodla_parametry_robota.md``.
    """

    # IEEE Spectrum 2008: "travel at 1.3 meters per second".
    speed_m_per_s: float = 1.3
    battery_capacity_pct: float = 100.0
    initial_battery_pct: float = 100.0
    # MWPVL 2012: robots charge "every couple of hours". Assuming 2 h of
    # continuous driving at 1.3 m/s: 100 % / 9360 m.
    battery_drain_pct_per_m: float = 100.0 / (2 * SECONDS_PER_HOUR * 1.3)
    charge_threshold_pct: float = 20.0
    # MWPVL 2012: "a 5-minute battery re-charge", taken as threshold -> full:
    # 80 % in 300 s.
    charge_rate_pct_per_s: float = (100.0 - 20.0) / 300.0

    def __post_init__(self) -> None:
        if self.speed_m_per_s <= 0:
            raise ValueError("Robot speed must be positive")
        if self.battery_capacity_pct <= 0:
            raise ValueError("Battery capacity must be positive")
        if not 0 <= self.initial_battery_pct <= self.battery_capacity_pct:
            raise ValueError(
                "Initial battery must be between zero and the battery capacity"
            )
        if self.battery_drain_pct_per_m < 0:
            raise ValueError("Battery drain cannot be negative")
        if not 0 <= self.charge_threshold_pct < self.battery_capacity_pct:
            raise ValueError(
                "Charge threshold must be between zero and the battery capacity"
            )
        if self.charge_rate_pct_per_s <= 0:
            raise ValueError("Charge rate must be positive")

    def charge_duration_s(self, battery_pct: float) -> float:
        """Seconds needed to charge ``battery_pct`` back to full capacity."""
        missing = max(0.0, self.battery_capacity_pct - battery_pct)
        return missing / self.charge_rate_pct_per_s


@dataclass(frozen=True, slots=True)
class PickingParams:
    """Time a picker needs at a station for one rack visit.

    Mean service time = ``fixed_s + per_item_s * items``. With
    ``distribution="exponential"`` the actual time is drawn from an
    exponential distribution with that mean (M/M/1 validation); with
    ``"deterministic"`` it is exactly the mean (M/D/1).
    """

    # Wurman et al. 2007: "a new pod face every six seconds ... 600 lines
    # per hour". One unit is treated as one line.
    fixed_s: float = 0.0
    per_item_s: float = 6.0
    distribution: Literal["deterministic", "exponential"] = "deterministic"

    def __post_init__(self) -> None:
        if self.fixed_s < 0 or self.per_item_s < 0:
            raise ValueError("Picking times cannot be negative")
        if self.distribution not in ("deterministic", "exponential"):
            raise ValueError(f"Unknown distribution: {self.distribution}")

    def mean_duration(self, items: int) -> float:
        return self.fixed_s + self.per_item_s * items

    def sample(self, items: int, rng: np.random.Generator) -> float:
        """Draw the service time of one rack visit with ``items`` units."""
        mean = self.mean_duration(items)
        if self.distribution == "exponential" and mean > 0:
            return float(rng.exponential(mean))
        return mean


@dataclass(frozen=True, slots=True)
class FailureParams:
    """Failure and repair process of the fleet.

    ``mean_time_to_failure_s`` is the mean time between failures of one robot;
    draws are exponential, so failures form a Poisson process. ``None``
    disables failures, which keeps the baseline comparable. Once a robot has
    failed, ``mean_repair_time_s`` is the mean time until it is repaired.

    ``retry_interval_s`` is how long a failure event waits when it arrives
    while the robot is picking, queueing or charging. Those states are atomic
    in the model, so the failure is retried after the robot is free again.
    """

    mean_time_to_failure_s: float | None = None
    mean_repair_time_s: float = 300.0
    retry_interval_s: float = 10.0

    def __post_init__(self) -> None:
        if (
            self.mean_time_to_failure_s is not None
            and self.mean_time_to_failure_s <= 0
        ):
            raise ValueError("Mean time to failure must be positive")
        if self.mean_repair_time_s <= 0:
            raise ValueError("Mean repair time must be positive")
        if self.retry_interval_s <= 0:
            raise ValueError("Failure retry interval must be positive")


@dataclass(frozen=True, slots=True)
class AssignmentParams:
    """Weights for the robot-to-task assignment rules.

    ``strategy`` picks the rule: ``nearest`` keeps the original behaviour and
    ``deadline_battery`` trades travel time against battery level.
    ``deadline_horizon_s`` is the slack at which the shipment deadline stops
    influencing the choice. ``battery_weight_s`` is the extra travel time
    charged to a robot with an empty battery compared to a full one; it is
    only fully applied when the deadline is not tight.
    """

    strategy: Literal["nearest", "deadline_battery"] = "nearest"
    deadline_horizon_s: float = 1800.0
    battery_weight_s: float = 300.0

    def __post_init__(self) -> None:
        if self.strategy not in ("nearest", "deadline_battery"):
            raise ValueError(f"Unknown assignment strategy: {self.strategy}")
        if self.deadline_horizon_s <= 0:
            raise ValueError("Deadline horizon must be positive")
        if self.battery_weight_s < 0:
            raise ValueError("Battery weight cannot be negative")


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Units of the simulation.

    Model time (``Warehouse.time``) is measured in seconds. One Mesa step
    advances the clock by ``TICK_S`` seconds and moves robots; a grid cell is
    ``cell_size_m`` metres wide.

    ``reservation_lookahead`` is the number of cells ahead of its current
    cell a robot reserves. A robot following another robot in the same
    direction only reserves ``follow_lookahead`` cells ahead, so a convoy
    keeps a one-cell headway instead of leaving the full lookahead gap empty.
    ``deadlock_timeout_s`` is how long a cycle of robots waiting for each
    other may persist before the model reports it. ``failures`` controls the
    optional failure/repair process; it is disabled by default. ``assignment``
    selects the robot-to-task rule and its weights.
    """

    TICK_S = 1.0

    cell_size_m: float = 1.0
    robot: RobotParams = field(default_factory=RobotParams)
    picking: PickingParams = field(default_factory=PickingParams)
    failures: FailureParams = field(default_factory=FailureParams)
    assignment: AssignmentParams = field(default_factory=AssignmentParams)
    reservation_lookahead: int = 3
    follow_lookahead: int = 1
    deadlock_timeout_s: float = 60.0

    def __post_init__(self) -> None:
        if self.cell_size_m <= 0:
            raise ValueError("Cell size must be positive")
        if self.reservation_lookahead < 1:
            raise ValueError("Reservation lookahead must be at least one cell")
        if not 1 <= self.follow_lookahead <= self.reservation_lookahead:
            raise ValueError(
                "Follow lookahead must be between one cell and the "
                "reservation lookahead"
            )
        if self.deadlock_timeout_s <= 0:
            raise ValueError("Deadlock timeout must be positive")

    @property
    def cells_per_tick(self) -> float:
        """How many cells a robot covers during one tick."""
        return self.robot.speed_m_per_s * self.TICK_S / self.cell_size_m

    @property
    def seconds_per_cell(self) -> float:
        return self.cell_size_m / self.robot.speed_m_per_s
