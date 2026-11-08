"""Visualise the warehouse on Olist orders (in the browser).

Usage (from the repository root):

    uv run runners/run_visual_olist.py

Run as a script, this file starts Solara on itself; Solara then imports it
and shows ``page``. It reuses the robot and rack drawing of the standard
visualisation (``src/visualization/portals.py``) and only changes the input:

* orders from the Olist generator (calibrated on 2017),
* products placed on racks randomly or by ABC,
* racks returned home or to the nearest free slot.

Change the settings in the sidebar and press Reset.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PORT = "8522"
# Solara also runs this file as __main__; the flag stops it from starting again.
CHILD_FLAG = "SSD_OLIST_VISUAL_SERVER"

if __name__ == "__main__" and not os.environ.get(CHILD_FLAG):
    os.environ[CHILD_FLAG] = "1"
    os.execv(
        sys.executable,
        [sys.executable, "-m", "solara", "run", str(Path(__file__).resolve()), "--port", PORT],
    )

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import solara  # noqa: E402
from mesa.visualization import SpaceRenderer  # noqa: E402
from mesa.visualization.solara_viz import (  # noqa: E402
    ModelController,
    ModelCreator,
    ShowSteps,
    SpaceRendererComponent,
)

from src.core.model import Warehouse  # noqa: E402
from src.data import olist  # noqa: E402
from src.environment.layout import WarehouseLayout  # noqa: E402
from src.orders.olist_generator import generate_orders  # noqa: E402
from src.strategies.placement import (  # noqa: E402
    NearestFreeSlot,
    abc_placement,
    random_placement,
)
from src.visualization.portals import agent_portrayal, legend_handles  # noqa: E402

START = pd.Timestamp("2018-03-06 08:00")  # an ordinary Tuesday morning
STATS = olist.compute_stats(olist.year(olist.load_orders(), 2017))


class OlistWarehouse(Warehouse):
    """The standard model fed with Olist orders and a placement strategy."""

    def __init__(
        self,
        num_robots: int = 8,
        placement: str = "random",
        return_policy: str = "home",
        volume_factor: float = 5.0,
        hours: int = 4,
        seed: int = 1,
    ):
        layout = WarehouseLayout.generate(num_robots=num_robots)
        rng = np.random.default_rng(seed)
        if placement == "ABC":
            rack_skus = abc_placement(STATS.product_popularity, layout, rng)
        else:
            rack_skus = random_placement(list(STATS.product_popularity.index), layout, rng)
        orders = generate_orders(
            STATS, rng, START, hours * 3600.0, volume_factor=volume_factor
        )
        super().__init__(
            layout=layout,
            num_robots=num_robots,
            orders=orders,
            rack_skus=rack_skus,
            rng=seed,
        )
        self.nearest_free_slot = (
            NearestFreeSlot(layout) if return_policy == "nearest free slot" else None
        )

    def return_location(self, rack):
        if self.nearest_free_slot is None:
            return super().return_location(rack)
        return self.nearest_free_slot.choose(self, rack)


model_params = {
    "num_robots": {"type": "SliderInt", "value": 8, "min": 1, "max": 30, "step": 1, "label": "Robots"},
    "placement": {"type": "Select", "value": "random", "values": ["random", "ABC"], "label": "Placement"},
    "return_policy": {
        "type": "Select",
        "value": "home",
        "values": ["home", "nearest free slot"],
        "label": "Rack return",
    },
    "volume_factor": {
        "type": "SliderFloat", "value": 5.0, "min": 0.5, "max": 20.0, "step": 0.5,
        "label": "Order volume (x normal day)",
    },
    "hours": {"type": "SliderInt", "value": 4, "min": 1, "max": 12, "step": 1, "label": "Hours of orders"},
    "seed": {"type": "SliderInt", "value": 1, "min": 1, "max": 100, "step": 1, "label": "Seed"},
}


def create_renderer(model):
    return SpaceRenderer(model, backend="matplotlib").setup_agents(agent_portrayal).render()


def configure_renderer(renderer, model):
    figure = renderer.canvas.get_figure()
    figure.set_size_inches(10, 6)
    axes = renderer.canvas
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlim(-0.5, model.grid.width - 0.5)
    axes.set_ylim(-0.5, model.grid.height - 0.5)
    if axes.get_legend() is not None:
        axes.get_legend().remove()
    axes.legend(
        handles=legend_handles(),
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        title="Legend",
        framealpha=0.9,
    )


def summary(model) -> str:
    metrics = model.metrics
    arrived = len(model.released_orders)
    lines = [
        f"Time: {model.time / 3600:.2f} h",
        f"Orders: {len(model.orders)} planned, {arrived} arrived, "
        f"{metrics.completed_orders} completed",
        f"Distance driven: {metrics.total_distance_m:.0f} m",
    ]
    if metrics.completed_orders:
        lines.append(f"Mean completion time: {metrics.average_completion_time:.0f} s")
    return "  \n".join(lines)


model = OlistWarehouse()
renderer = create_renderer(model)
configure_renderer(renderer, model)


@solara.component
def OlistPage():
    reactive_model = solara.use_reactive(model)
    reactive_renderer = solara.use_reactive(renderer)
    model_parameters = solara.use_reactive({})
    play_interval = solara.use_reactive(50)
    render_interval = solara.use_reactive(5)
    use_threads = solara.use_reactive(False)

    configure_renderer(reactive_renderer.value, reactive_model.value)

    with solara.AppBar():
        solara.AppBarTitle("Warehouse on Olist orders")

    with solara.Sidebar(), solara.Column():
        with solara.Card("Controls"):
            ModelController(
                reactive_model,
                renderer=reactive_renderer,
                model_parameters=model_parameters,
                play_interval=play_interval,
                render_interval=render_interval,
                use_threads=use_threads,
            )
        with solara.Card("Settings (press Reset)"):
            ModelCreator(reactive_model, model_params, model_parameters=model_parameters)
        with solara.Card("Information"):
            ShowSteps(reactive_model.value)
            solara.Markdown(summary(reactive_model.value))

    SpaceRendererComponent(reactive_model.value, reactive_renderer.value)


page = OlistPage
