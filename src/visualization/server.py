from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from src.core.model import WarehouseModel
from src.visualization.portals import agent_portrayal

grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)

server = ModularServer(
    WarehouseModel,
    [grid],
    "Symulacja Magazynu",
    {"width": 20, "height": 20, "num_robots": 5}
)
server.port = 8521 # Default mesa port
