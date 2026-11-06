from __future__ import annotations

from dataclasses import dataclass, field

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True, slots=True)
class RobotParams:
    """Physical robot parameters shared by the whole fleet.

    Defaults are placeholders until they are calibrated from manufacturer
    documentation and Kiva publications (P7).
    """

    speed_m_per_s: float = 1.0
    battery_capacity_pct: float = 100.0
    battery_drain_pct_per_m: float = 0.05

    def __post_init__(self) -> None:
        if self.speed_m_per_s <= 0:
            raise ValueError("Robot speed must be positive")
        if self.battery_capacity_pct <= 0:
            raise ValueError("Battery capacity must be positive")
        if self.battery_drain_pct_per_m < 0:
            raise ValueError("Battery drain cannot be negative")


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
