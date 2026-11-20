"""Configure a warehouse run from the same inputs as the GUI sidebar.

This module holds the solara-free part of ``VisualWarehouse``: turning the
sidebar parameters (layout, robots, order source, placement, return policy,
volume, hours, seed) into a running :class:`Warehouse`. Both the browser
visualisation and the headless recorder build their model through
:func:`build_run` / :class:`ConfiguredWarehouse`, so a run recorded to a file
carries exactly the data the GUI shows.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from functools import cache

import numpy as np
import pandas as pd

from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.environment.layout_io import LayoutFile, available_layouts
from src.orders.generator import random_orders
from src.orders.models import Order
from src.pipeline.reservations import DeadlockError, LivelockError
from src.strategies.placement import (
    NearestFreeSlot,
    RackSkus,
    abc_placement,
    random_placement,
)
from src.visualization.live_stats import robot_number

LAYOUTS = available_layouts()
DEFAULT_LAYOUT = "kiva_standard" if "kiva_standard" in LAYOUTS else next(iter(LAYOUTS))
# A Monday morning: the busiest weekday in Olist, start of the working day.
START = pd.Timestamp("2018-03-05 08:00")
# The "1x" of the volume slider: an ordinary day of the scenarios (Olist x 10).
OLIST_BASE_VOLUME = 10.0
# Demo orders at 1x: one order a minute on average.
DEMO_ORDERS_PER_HOUR = 60.0


@cache
def olist_stats():
    """Olist statistics (2017), or None when the data is not downloaded."""
    try:
        from src.data import olist

        return olist.compute_stats(olist.year(olist.load_orders(), 2017))
    except (FileNotFoundError, OSError):
        return None


def default_rack_skus(layout: WarehouseLayout) -> RackSkus:
    return {
        rack_id: frozenset({"sku-" + rack_id.removeprefix("rack-")})
        for rack_id in layout.racks
    }


@dataclass(frozen=True, slots=True)
class RunInputs:
    """Everything needed to build a :class:`Warehouse` for one run."""

    layout_file: LayoutFile
    floor_plan: WarehouseLayout
    order_list: list[Order]
    rack_skus: RackSkus
    nearest_free_slot: NearestFreeSlot | None
    notices: list[str]
    summary: str
    start: datetime


def build_run(
    layout: str = DEFAULT_LAYOUT,
    num_robots: int = 8,
    orders: str = "olist",
    placement: str = "random",
    return_policy: str = "home",
    volume: float = 1.0,
    hours: int = 4,
    seed: int = 1,
) -> RunInputs:
    """Build the inputs of a run from the sidebar parameters."""
    layout_file = LAYOUTS[layout]
    floor_plan = layout_file.layout.with_robot_starts(num_robots)
    summary = (
        f"Roboty: {num_robots} · zamówienia {orders} ×{volume:g} przez {hours} h · "
        f"rozmieszczenie {placement} · powrót {return_policy} · seed {seed}"
    )
    order_rng = np.random.default_rng(seed)
    notices: list[str] = []
    start = START.to_pydatetime()

    stats = olist_stats() if orders == "olist" else None
    if orders == "olist" and stats is None:
        notices.append(
            "Brak danych Olist w data/raw – użyto zamówień demo "
            "(pobierz: uv run data/download_olist.py)."
        )
    if stats is not None:
        placement_rng = np.random.default_rng([seed, 1])
        if placement == "ABC":
            rack_skus = abc_placement(
                stats.product_popularity, floor_plan, placement_rng
            )
        else:
            rack_skus = random_placement(
                list(stats.product_popularity.index), floor_plan, placement_rng
            )
        from src.orders.olist_generator import generate_orders

        order_list = generate_orders(
            stats,
            order_rng,
            START,
            hours * 3600.0,
            volume_factor=OLIST_BASE_VOLUME * volume,
        )
    else:
        if placement == "ABC" and orders == "demo":
            notices.append(
                "Rozmieszczenie ABC wymaga danych Olist; w trybie demo "
                "każdy regał ma jeden produkt, a produkty są równie popularne."
            )
        rack_skus = default_rack_skus(floor_plan)
        per_hour = DEMO_ORDERS_PER_HOUR * volume
        order_list = random_orders(
            order_rng,
            skus=sorted(sku for skus in rack_skus.values() for sku in skus),
            count=max(1, round(per_hour * hours)),
            mean_interarrival_s=3600.0 / per_hour,
        )

    nearest_free_slot = (
        NearestFreeSlot(floor_plan) if return_policy == "nearest" else None
    )
    return RunInputs(
        layout_file=layout_file,
        floor_plan=floor_plan,
        order_list=order_list,
        rack_skus=rack_skus,
        nearest_free_slot=nearest_free_slot,
        notices=notices,
        summary=summary,
        start=start,
    )


class ConfiguredWarehouse(Warehouse):
    """The warehouse model as configured from the sidebar parameters.

    A deadlock or livelock does not crash the run: the model stops, the robots
    involved are remembered in ``alert_robots`` and ``stop_reason`` explains
    what happened.
    """

    def __init__(
        self,
        layout: str = DEFAULT_LAYOUT,
        num_robots: int = 8,
        orders: str = "olist",
        placement: str = "random",
        return_policy: str = "home",
        volume: float = 1.0,
        hours: int = 4,
        seed: int = 1,
    ):
        inputs = build_run(
            layout=layout,
            num_robots=num_robots,
            orders=orders,
            placement=placement,
            return_policy=return_policy,
            volume=volume,
            hours=hours,
            seed=seed,
        )
        self.layout_file = inputs.layout_file
        self.summary = inputs.summary
        self.notices = list(inputs.notices)
        self.start = inputs.start
        super().__init__(
            layout=inputs.floor_plan,
            num_robots=num_robots,
            orders=inputs.order_list,
            rack_skus=inputs.rack_skus,
            rng=seed,
        )
        self.nearest_free_slot = inputs.nearest_free_slot
        self.stop_reason: str | None = None
        self.stop_kind: str | None = None
        self.alert_robots: frozenset[str] = frozenset()

    def _robots_in(self, exc: DeadlockError) -> frozenset[str]:
        """Robots to highlight: the robots named in the error, the chain of
        robots each of them waits for, and the current waiting cycle."""
        named = [r for r in self.robot_by_id if re.search(rf"\b{r}\b", str(exc))]
        chain: set[str] = set(self._deadlock_cycle)
        for robot_id in named:
            current = self.robot_by_id[robot_id]
            while current.robot_id not in chain:
                chain.add(current.robot_id)
                if current.blocked_by not in self.robot_by_id:
                    break
                current = self.robot_by_id[current.blocked_by]
        return frozenset(chain)

    def return_location(self, rack):
        if self.nearest_free_slot is None:
            return super().return_location(rack)
        return self.nearest_free_slot.choose(self, rack)

    def step(self) -> None:
        if self.stop_reason is not None:
            self.running = False
            return
        try:
            super().step()
        except DeadlockError as exc:
            kind = "Livelock" if isinstance(exc, LivelockError) else "Zakleszczenie"
            self.stop_kind = "alert"
            self.stop_reason = f"{kind} – symulacja zatrzymana. {exc}"
            self.alert_robots = self._robots_in(exc)
            if self.alert_robots:
                names = ", ".join(sorted(self.alert_robots, key=robot_number))
                self.stop_reason += f" Podświetlone roboty: {names}."
            self.running = False
            return
        if self.all_orders_completed:
            self.stop_kind = "done"
            self.stop_reason = "Wszystkie zamówienia zrealizowane."
            self.running = False


def make_warehouse(**params) -> ConfiguredWarehouse:
    """Headless entry point: build a configured model from sidebar parameters."""
    return ConfiguredWarehouse(**params)
