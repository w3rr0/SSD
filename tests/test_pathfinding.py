import unittest

from src.environment.layout import WarehouseLayout
from src.pipeline.pathfinding import NoPathError, astar_path


class AStarTests(unittest.TestCase):
    def test_routes_around_blocked_cells(self):
        layout = WarehouseLayout(
            width=5,
            height=5,
            blocked=frozenset({(2, 0), (2, 1), (2, 2), (2, 3)}),
        )

        path = astar_path(layout, (0, 2), (4, 2))

        self.assertEqual(path[0], (0, 2))
        self.assertEqual(path[-1], (4, 2))
        self.assertTrue(all(position not in layout.blocked for position in path))
        self.assertGreater(len(path), 5)

    def test_does_not_cross_another_rack(self):
        layout = WarehouseLayout(
            width=5,
            height=1,
            racks={"other-rack": (2, 0)},
        )

        with self.assertRaises(NoPathError):
            astar_path(layout, (0, 0), (4, 0))

    def test_uses_current_obstacles_instead_of_layout_positions(self):
        layout = WarehouseLayout(
            width=5,
            height=1,
            racks={"moved-rack": (2, 0)},
        )

        path = astar_path(layout, (0, 0), (4, 0), obstacles=set())

        self.assertEqual(path, ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0)))
        with self.assertRaises(NoPathError):
            astar_path(layout, (0, 0), (4, 0), obstacles={(3, 0)})

    def test_reports_unreachable_goal(self):
        layout = WarehouseLayout(
            width=3,
            height=3,
            blocked=frozenset({(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)}),
        )

        with self.assertRaises(NoPathError):
            astar_path(layout, (0, 0), (2, 2))
