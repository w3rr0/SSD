"""Browser visualisation of the warehouse (Solara).

Run from the repository root::

    uv run runners/run_visual.py          # or: make visual

The page shows the warehouse plan (layouts from ``layouts/*.json``), live
statistics of the fleet, the robots and a live list of incoming orders.
Settings in the sidebar take effect after pressing Reset.
"""

import re
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import solara  # noqa: E402
from mesa.visualization.solara_viz import ModelController, ModelCreator  # noqa: E402
from mesa.visualization.utils import update_counter  # noqa: E402

from src.core.model import Warehouse  # noqa: E402
from src.environment.layout_io import available_layouts  # noqa: E402
from src.orders.generator import random_orders  # noqa: E402
from src.pipeline.reservations import DeadlockError, LivelockError  # noqa: E402
from src.strategies.placement import (  # noqa: E402
    NearestFreeSlot,
    abc_placement,
    random_placement,
)
from src.visualization import panels  # noqa: E402
from src.visualization.live_stats import (  # noqa: E402
    robot_number,
    snapshot,
    station_rows,
)
from src.visualization.svg import render_svg  # noqa: E402

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


def default_rack_skus(layout) -> dict[str, frozenset[str]]:
    return {
        rack_id: frozenset({"sku-" + rack_id.removeprefix("rack-")})
        for rack_id in layout.racks
    }


class VisualWarehouse(Warehouse):
    """The warehouse model as configured from the sidebar.

    A deadlock or livelock does not crash the page: the run stops, the robots
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
        self.layout_file = LAYOUTS[layout]
        floor_plan = self.layout_file.layout.with_robot_starts(num_robots)
        self.summary = (
            f"Roboty: {num_robots} · zamówienia {orders} ×{volume:g} przez {hours} h · "
            f"rozmieszczenie {placement} · powrót {return_policy} · seed {seed}"
        )
        order_rng = np.random.default_rng(seed)
        self.notices: list[str] = []
        self.start = START.to_pydatetime()

        stats = olist_stats() if orders == "olist" else None
        if orders == "olist" and stats is None:
            self.notices.append(
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
                self.notices.append(
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

        super().__init__(
            layout=floor_plan,
            num_robots=num_robots,
            orders=order_list,
            rack_skus=rack_skus,
            rng=seed,
        )
        self.nearest_free_slot = (
            NearestFreeSlot(floor_plan) if return_policy == "nearest" else None
        )
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


model_params = {
    "layout": {
        "type": "Select",
        "value": DEFAULT_LAYOUT,
        "values": list(LAYOUTS),
        "label": "Magazyn",
    },
    "num_robots": {
        "type": "SliderInt", "value": 8, "min": 1, "max": 40, "step": 1,
        "label": "Roboty",
    },
    "orders": {
        "type": "Select", "value": "olist", "values": ["olist", "demo"],
        "label": "Zamówienia",
    },
    "placement": {
        "type": "Select", "value": "random", "values": ["random", "ABC"],
        "label": "Rozmieszczenie",
    },
    "return_policy": {
        "type": "Select", "value": "home", "values": ["home", "nearest"],
        "label": "Powrót regału",
    },
    "volume": {
        "type": "SliderFloat", "value": 1.0, "min": 0.1, "max": 10.0, "step": 0.1,
        "label": "Natężenie ×",
    },
    "hours": {
        "type": "SliderInt", "value": 4, "min": 1, "max": 24, "step": 1,
        "label": "Godziny",
    },
    "seed": {
        "type": "SliderInt", "value": 1, "min": 1, "max": 100, "step": 1,
        "label": "Seed",
    },
}

show_routes = solara.reactive(True)
heat_racks = solara.reactive(False)
steps_per_frame = solara.reactive(2)
play_interval = solara.reactive(80)


@solara.component
def WarehouseMap(model: VisualWarehouse):
    update_counter.get()
    snap_waiting = {row.station_id: row.waiting for row in station_rows(model)}
    svg = render_svg(
        model,
        show_routes=show_routes.value,
        rack_colors="heat" if heat_racks.value else "plain",
        alert_robots=model.alert_robots,
        station_waiting=snap_waiting,
    )
    solara.HTML(tag="div", unsafe_innerHTML=svg, style={"width": "100%"})


@solara.component
def Banners(model: VisualWarehouse):
    update_counter.get()
    for notice in model.notices:
        solara.HTML(tag="div", unsafe_innerHTML=notice, classes=["banner", "info"])
    if model.stop_reason:
        solara.HTML(
            tag="div",
            unsafe_innerHTML=model.stop_reason,
            classes=["banner", model.stop_kind or "info"],
        )


@solara.component
def StatsPanel(model: VisualWarehouse):
    update_counter.get()
    snap = snapshot(model, order_limit=0)
    with solara.Card("Statystyki na żywo", margin=0, classes=["area-stats"]):
        solara.HTML(tag="div", unsafe_innerHTML=panels.kpi_html(snap, model.start))
        solara.HTML(
            tag="div",
            unsafe_innerHTML="<div class='kv-label' style='margin-top:12px'>"
            "Czas floty</div>" + panels.fleet_html(snap),
        )
        solara.HTML(
            tag="div",
            unsafe_innerHTML="<div class='kv-label' style='margin-top:12px'>"
            "Stanowiska</div>" + panels.stations_html(snap),
        )


@solara.component
def RobotsPanel(model: VisualWarehouse):
    update_counter.get()
    snap = snapshot(model, order_limit=0)
    with solara.Card("Roboty", margin=0, classes=["area-robots"]):
        solara.HTML(tag="div", unsafe_innerHTML=panels.robots_html(snap))


@solara.component
def OrdersPanel(model: VisualWarehouse):
    update_counter.get()
    snap = snapshot(model)
    with solara.Card(
        f"Zamówienia na żywo – przyjęte {snap.arrived}, gotowe {snap.completed}",
        margin=0,
        classes=["area-orders"],
    ):
        solara.HTML(tag="div", unsafe_innerHTML=panels.orders_html(snap, model.start))


@solara.component
def Page():
    initial = solara.use_memo(VisualWarehouse, [])
    model = solara.use_reactive(initial)
    model_parameters = solara.use_reactive({})
    use_threads = solara.use_reactive(False)

    solara.Style(
        panels.PANEL_CSS
        + """
        .dashboard{display:grid;width:100%;gap:12px;align-items:start;
          grid-template-columns:minmax(0,1.5fr) minmax(360px,1fr);
          grid-template-areas:"map stats" "robots orders"}
        .dashboard>*{min-width:0}
        .area-map{grid-area:map}.area-stats{grid-area:stats}
        .area-robots{grid-area:robots}.area-orders{grid-area:orders}
        @media (max-width:1100px){.dashboard{grid-template-columns:minmax(0,1fr);
          grid-template-areas:"map" "stats" "robots" "orders"}}
        """
    )

    with solara.AppBar():
        solara.AppBarTitle("Symulacja magazynu Kiva")
        solara.lab.ThemeToggle()

    with solara.Sidebar(), solara.Column():
        with solara.Card("Sterowanie"):
            ModelController(
                model,
                model_parameters=model_parameters,
                play_interval=play_interval,
                render_interval=steps_per_frame,
                use_threads=use_threads,
            )
            solara.SliderInt(
                f"Tempo: {steps_per_frame.value} s/klatkę",
                value=steps_per_frame,
                min=1,
                max=120,
            )
            solara.SliderInt(
                f"Odstęp: {play_interval.value} ms",
                value=play_interval,
                min=20,
                max=500,
            )
        with solara.Card("Ustawienia", subtitle="Zmiany działają po kliknięciu Reset"):
            ModelCreator(model, model_params, model_parameters=model_parameters)
        with solara.Card("Widok"):
            solara.Switch(label="Pokaż trasy i rezerwacje", value=show_routes)
            solara.Switch(label="Regały: mapa liczby kursów", value=heat_racks)
        with solara.Card("Legenda"):
            solara.HTML(tag="div", unsafe_innerHTML=panels.legend_html())

    current = model.value
    with solara.Div(classes=["dashboard"]):
        with solara.Div(classes=["area-map"]):
            Banners(current)
            with solara.Card(
                current.layout_file.name,
                subtitle=current.summary,
                margin=0,
            ):
                if current.layout_file.description:
                    solara.Text(
                        current.layout_file.description,
                        style={"font-size": "13px", "opacity": 0.75},
                    )
                WarehouseMap(current)
        StatsPanel(current)
        RobotsPanel(current)
        OrdersPanel(current)


page = Page
