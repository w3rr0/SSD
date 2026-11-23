"""Browser visualisation of the warehouse (Solara).

Run from the repository root::

    make visual

The page shows the warehouse plan (layouts from ``layouts/*.json``), live
statistics of the fleet, the robots and a live list of incoming orders.
Settings in the sidebar take effect after pressing Reset.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import solara  # noqa: E402
from mesa.visualization.solara_viz import ModelController, ModelCreator  # noqa: E402
from mesa.visualization.utils import update_counter  # noqa: E402

from src.experiments.build import (  # noqa: E402
    DEFAULT_LAYOUT,
    LAYOUTS,
    ConfiguredWarehouse as VisualWarehouse,
)
from src.visualization import panels  # noqa: E402
from src.visualization.live_stats import snapshot, station_rows  # noqa: E402
from src.visualization.svg import render_svg  # noqa: E402


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
        "label": "Natężenie × (1 = zwykły dzień, 9,5 = Black Friday)",
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
