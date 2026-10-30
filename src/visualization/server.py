from mesa.visualization import SolaraViz, make_space_component

from src.core.model import Warehouse
from src.visualization.portals import agent_portrayal

model_params = {
    "width": 20,
    "height": 20,
    "num_robots": 5,
}

model = Warehouse(**model_params)

page = SolaraViz(
    model,
    components=[make_space_component(agent_portrayal)],
    model_params=model_params,
    name="Magazine simulation",
)
