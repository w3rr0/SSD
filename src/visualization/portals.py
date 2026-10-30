from mesa.visualization.components import AgentPortrayalStyle

from src.agents.robot import Robot


def agent_portrayal(agent):
    if isinstance(agent, Robot):
        return AgentPortrayalStyle(
            color="blue",
            marker="o",
            size=50,
        )
    return AgentPortrayalStyle()
