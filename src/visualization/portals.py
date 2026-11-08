from matplotlib import colormaps
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from mesa.visualization import SpaceRenderer
from mesa.visualization.components import AgentPortrayalStyle

from src.agents.robot import Robot
from src.agents.warehouse_objects import Charger, PickingStation, Rack
from src.core.model import Warehouse

ROUTE_COLOR_ORDER = (0, 2, 3, 4, 5, 6, 7, 8, 9, 1)
ROUTE_COLORS = tuple(colormaps["tab10"](index) for index in ROUTE_COLOR_ORDER)


def route_color(index: int) -> tuple[float, float, float, float]:
    """Colour that marks the reservation window of the ``index``-th robot."""
    return ROUTE_COLORS[index % len(ROUTE_COLORS)]


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


def draw_reserved_routes(axes: Axes, model: Warehouse) -> None:
    """Draw every robot's reservation window as a coloured path.

    The window is the current cell plus the cells reserved ahead of it, so the
    line shows exactly which part of the aisle a robot has claimed. Cells are
    plotted in route order, which keeps turns and detours visible.
    """
    for index, robot in enumerate(model.robots):
        window = model.reservations.window(robot.robot_id)
        if len(window) < 2:
            continue
        color = route_color(index)
        xs = [x for x, _ in window]
        ys = [y for _, y in window]
        axes.plot(
            xs,
            ys,
            color=color,
            linewidth=3.0,
            alpha=0.75,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=3,
        )
        axes.scatter(
            xs[1:],
            ys[1:],
            color=color,
            marker="o",
            s=26,
            alpha=0.55,
            edgecolors="white",
            linewidths=0.6,
            zorder=3,
        )


def agent_portrayal(agent):
    if isinstance(agent, Robot):
        return AgentPortrayalStyle(
            color="green" if agent.carrying_rack_id else "blue",
            marker="o",
            size=50,
            zorder=5,
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


class RouteSpaceRenderer(SpaceRenderer):
    """Renderer that also shows the cells every robot has reserved."""

    def __init__(self, model: Warehouse, backend: str = "matplotlib"):
        super().__init__(model, backend=backend)
        self.route_model = model

    def draw_agents(self, portrayal=None, **kwargs):
        mesh = super().draw_agents(portrayal, **kwargs)
        draw_reserved_routes(self.canvas, self.route_model)
        return mesh
