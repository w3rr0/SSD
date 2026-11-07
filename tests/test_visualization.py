import unittest

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib.lines import Line2D

from src.agents.robot import RobotState
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.visualization.portals import (
    RouteSpaceRenderer,
    agent_portrayal,
    route_color,
)


class ReservationOverlayTests(unittest.TestCase):
    def _model(self) -> Warehouse:
        layout = WarehouseLayout(
            width=10,
            height=3,
            blocked=frozenset((x, y) for x in range(10) for y in (0, 2)),
            robot_starts={"robot-1": (2, 1)},
        )
        model = Warehouse(layout=layout, num_robots=1, orders=[])
        robot = model.robots[0]
        robot.set_route(((3, 1), (4, 1), (5, 1)))
        robot.transition(RobotState.TO_RACK)
        return model

    @staticmethod
    def _render(model: Warehouse) -> RouteSpaceRenderer:
        renderer = RouteSpaceRenderer(model).setup_agents(agent_portrayal)
        renderer.draw_structure()
        renderer.draw_agents()
        return renderer

    def test_reserved_window_is_drawn_as_a_path(self):
        renderer = self._render(self._model())

        route_lines = [
            line
            for line in renderer.canvas.lines
            if line.get_color() == route_color(0)
        ]
        self.assertEqual(len(route_lines), 1)
        line: Line2D = route_lines[0]
        self.assertEqual(list(line.get_xdata()), [2, 3, 4, 5])
        self.assertEqual(list(line.get_ydata()), [1, 1, 1, 1])

    def test_reserved_cells_get_markers(self):
        renderer = self._render(self._model())
        expected = np.array(route_color(0)[:3])

        marked = any(
            collection.get_facecolor().size
            and np.allclose(collection.get_facecolor()[0, :3], expected, atol=0.05)
            for collection in renderer.canvas.collections
        )
        self.assertTrue(marked, "no marker collection uses the reserved-route colour")

    def test_a_window_with_one_cell_is_not_drawn(self):
        model = self._model()
        model.robots[0].clear_assignment()
        renderer = self._render(model)

        route_lines = [
            line
            for line in renderer.canvas.lines
            if line.get_color() == route_color(0)
        ]
        self.assertEqual(route_lines, [])


if __name__ == "__main__":
    unittest.main()
