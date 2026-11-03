import solara
from mesa.visualization import SpaceRenderer
from mesa.visualization.solara_viz import (
    ModelCreator,
    ModelController,
    ShowSteps,
    SpaceRendererComponent,
)

from src.core.model import Warehouse
from src.visualization.portals import agent_portrayal

model_params = {
    "width": 20,
    "height": 20,
    "num_robots": 5,
}


def create_renderer(model):
    return (
        SpaceRenderer(model, backend="matplotlib")
        .setup_agents(agent_portrayal)
        .render()
    )


model = Warehouse(**model_params)
renderer = create_renderer(model)


def configure_renderer(renderer, model):
    figure = renderer.canvas.get_figure()
    figure.set_size_inches(9, 9)

    axes = renderer.canvas
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlim(-0.5, model.grid.width - 0.5)
    axes.set_ylim(-0.5, model.grid.height - 0.5)


configure_renderer(renderer, model)


@solara.component
def WarehousePage():
    reactive_model = solara.use_reactive(model)
    reactive_renderer = solara.use_reactive(renderer)
    model_parameters = solara.use_reactive({})
    play_interval = solara.use_reactive(100)
    render_interval = solara.use_reactive(1)
    use_threads = solara.use_reactive(False)

    configure_renderer(reactive_renderer.value, reactive_model.value)

    solara.Style(
        """
        .warehouse-visualization {
            align-items: center;
            display: flex;
            height: calc(100vh - 64px);
            justify-content: center;
            min-height: 400px;
            overflow: auto;
            width: 100%;
        }

        .warehouse-visualization img.widget-image {
            display: block;
            height: auto;
            max-height: calc(100vh - 96px);
            max-width: 100%;
            object-fit: contain;
            width: auto;
        }
        """
    )

    with solara.AppBar():
        solara.AppBarTitle("Magazine simulation")
        solara.lab.ThemeToggle()

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
        with solara.Card("Model Parameters"):
            ModelCreator(
                reactive_model,
                model_params,
                model_parameters=model_parameters,
            )
        with solara.Card("Information"):
            ShowSteps(reactive_model.value)

    with solara.Column(classes=["warehouse-visualization"], gap="0"):
        SpaceRendererComponent(reactive_model.value, reactive_renderer.value)


page = WarehousePage
