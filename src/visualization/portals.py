from matplotlib.lines import Line2D
from mesa.visualization.components import AgentPortrayalStyle

from src.agents.robot import Robot
from src.agents.warehouse_objects import Charger, PickingStation, Rack


def legend_handles() -> tuple[Line2D, ...]:
    return (
        Line2D(
            [],
            [],
            color="blue",
            marker="o",
            linestyle="None",
            markersize=7,
            label="Robot",
        ),
        Line2D(
            [],
            [],
            color="green",
            marker="o",
            linestyle="None",
            markersize=7,
            label="Robot with a rack",
        ),
        Line2D(
            [],
            [],
            color="orange",
            marker="s",
            linestyle="None",
            markersize=7,
            label="Rack",
        ),
        Line2D(
            [],
            [],
            color="gray",
            marker="s",
            linestyle="None",
            markersize=7,
            label="Transported rack",
        ),
        Line2D(
            [],
            [],
            color="red",
            marker="X",
            linestyle="None",
            markersize=8,
            label="Completing station",
        ),
        Line2D(
            [],
            [],
            color="purple",
            marker="P",
            linestyle="None",
            markersize=8,
            label="Charger",
        ),
    )


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
