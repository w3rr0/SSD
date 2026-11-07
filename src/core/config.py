from dataclasses import dataclass, field
from typing import Literal

import numpy as np

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True, slots=True)
class RobotParams:
    """Physical robot parameters shared by the whole fleet.

    Defaults come from Kiva publications; sources and conversions are listed
    in ``docs/zrodla_parametry_robota.md``.
    """

    # IEEE Spectrum 2008: "travel at 1.3 meters per second".
    speed_m_per_s: float = 1.3
    battery_capacity_pct: float = 100.0
    # MWPVL 2012: robots charge "every couple of hours". Assuming 2 h of
    # continuous driving at 1.3 m/s: 100 % / 9360 m.
    battery_drain_pct_per_m: float = 100.0 / (2 * SECONDS_PER_HOUR * 1.3)

    def __post_init__(self) -> None:
        if self.speed_m_per_s <= 0:
            raise ValueError("Robot speed must be positive")
        if self.battery_capacity_pct <= 0:
            raise ValueError("Battery capacity must be positive")
        if self.battery_drain_pct_per_m < 0:
            raise ValueError("Battery drain cannot be negative")


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
class SimulationConfig:
    """Units of the simulation.

    Model time (``Warehouse.time``) is measured in seconds. One Mesa step
    advances the clock by ``TICK_S`` seconds and moves robots; a grid cell is
    ``cell_size_m`` metres wide.
    """

    TICK_S = 1.0

    cell_size_m: float = 1.0
    robot: RobotParams = field(default_factory=RobotParams)
    picking: PickingParams = field(default_factory=PickingParams)

    def __post_init__(self) -> None:
        if self.cell_size_m <= 0:
            raise ValueError("Cell size must be positive")

    @property
    def cells_per_tick(self) -> float:
        """How many cells a robot covers during one tick."""
        return self.robot.speed_m_per_s * self.TICK_S / self.cell_size_m

    @property
    def seconds_per_cell(self) -> float:
        return self.cell_size_m / self.robot.speed_m_per_s
