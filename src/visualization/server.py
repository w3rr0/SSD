from mesa.visualization import SolaraViz, SpaceRenderer

from src.core.model import Warehouse
from src.visualization.portals import agent_portrayal

model_params = {
    "width": 20,
    "height": 20,
    "num_robots": 5,
}

model = Warehouse(**model_params)
renderer = (
    SpaceRenderer(model, backend="matplotlib")
    .setup_agents(agent_portrayal)
    .render()
)
renderer.canvas.get_figure().set_size_inches(4, 4)
renderer.canvas.set_aspect("equal", adjustable="box")
renderer.canvas.set_xlim(-0.5, model.grid.width - 0.5)
renderer.canvas.set_ylim(-0.5, model.grid.height - 0.5)

page = SolaraViz(
    model,
    renderer,
    model_params=model_params,
    name="Magazine simulation",
)
