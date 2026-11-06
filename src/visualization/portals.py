from mesa.visualization.components import AgentPortrayalStyle

from src.agents.robot import Robot
from src.agents.warehouse_objects import Charger, PickingStation, Rack


def agent_portrayal(agent):
    if isinstance(agent, Robot):
        return AgentPortrayalStyle(
            color="green" if agent.carrying_rack_id else "blue",
            marker="o",
            size=50,
        )
    if isinstance(agent, Rack):
        return AgentPortrayalStyle(
            color="orange" if agent.carried_by is None else "gray",
            marker="s",
            size=70,
        )
    if isinstance(agent, PickingStation):
        return AgentPortrayalStyle(
            color="red",
            marker="X",
            size=80,
        )
    if isinstance(agent, Charger):
        return AgentPortrayalStyle(
            color="purple",
            marker="P",
            size=80,
        )
    return AgentPortrayalStyle()
