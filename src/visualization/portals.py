from src.agents.robot import Robot


def agent_portrayal(agent):
    if isinstance(agent, Robot):
        return {
            "Shape": "circle",
            "Color": "blue",
            "Filled": "true",
            "Layer": 0,
            "r": 0.5,
        }
    return {}
