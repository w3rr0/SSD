import json
import tempfile
import unittest
from pathlib import Path

from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.environment.layout_io import (
    LAYOUTS_DIR,
    available_layouts,
    layout_from_dict,
    load_layout,
)


class AsciiTopDownTests(unittest.TestCase):
    def test_first_row_is_the_top(self):
        layout = WarehouseLayout.from_ascii(["S..", "..R"], top_down=True)

        self.assertEqual(layout.stations["station-1"], (0, 1))
        self.assertEqual(layout.racks["rack-1"], (2, 0))

    def test_spaces_are_outside_and_blocked(self):
        layout = WarehouseLayout.from_ascii(["#####", "#S.R#", "### "], top_down=True)

        self.assertEqual(layout.outside, frozenset({(3, 0), (4, 0)}))
        self.assertTrue(layout.outside <= layout.blocked)
        self.assertNotIn((3, 0), layout.walls)
        self.assertIn((0, 0), layout.walls)

    def test_short_rows_are_padded_with_outside(self):
        layout = WarehouseLayout.from_ascii(["#####", "#S.R#", "###"], top_down=True)

        self.assertEqual(layout.width, 5)
        self.assertIn((4, 0), layout.outside)

    def test_bottom_up_maps_still_need_equal_rows(self):
        with self.assertRaises(ValueError):
            WarehouseLayout.from_ascii(["S..", "."])


class RobotStartTests(unittest.TestCase):
    def test_missing_starts_are_taken_from_free_aisles(self):
        layout = WarehouseLayout.from_ascii(["S.R.", "B..."], top_down=True)

        bigger = layout.with_robot_starts(3)

        self.assertEqual(len(bigger.robot_starts), 3)
        self.assertEqual(bigger.robot_starts["robot-1"], layout.robot_starts["robot-1"])
        starts = set(bigger.robot_starts.values())
        self.assertTrue(starts <= bigger.aisles())

    def test_too_many_robots_is_an_error(self):
        layout = WarehouseLayout.from_ascii(["S.R"], top_down=True)

        with self.assertRaises(ValueError):
            layout.with_robot_starts(5)


class ReachabilityTests(unittest.TestCase):
    def test_walled_in_rack_is_reported(self):
        layout = WarehouseLayout.from_ascii(
            ["#####", "S..##", "B.#R#", "#####"], top_down=True
        )

        self.assertEqual(layout.unreachable(), ["rack-1"])

    def test_reachable_layout_has_no_problems(self):
        layout = WarehouseLayout.from_ascii(["S..R", "B..."], top_down=True)

        self.assertEqual(layout.unreachable(), [])


class LayoutFileTests(unittest.TestCase):
    def test_map_and_generator_are_exclusive(self):
        with self.assertRaises(ValueError):
            layout_from_dict({"map": ["S.R"], "generator": {}})
        with self.assertRaises(ValueError):
            layout_from_dict({"name": "nothing"})

    def test_generator_parameters_are_checked(self):
        with self.assertRaises(ValueError):
            layout_from_dict({"generator": {"aisles": 3}})

    def test_layout_without_station_is_rejected(self):
        with self.assertRaises(ValueError):
            layout_from_dict({"map": ["..R", "B.."]})

    def test_unreachable_rack_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "rack-1"):
            layout_from_dict({"map": ["#####", "S..##", "B.#R#", "#####"]})

    def test_broken_files_are_skipped_in_the_list(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "good.json").write_text(
                json.dumps({"name": "Good", "map": ["S..R", "B..."]}), encoding="utf-8"
            )
            (folder / "bad.json").write_text("{not json", encoding="utf-8")

            layouts = available_layouts(folder)

            self.assertEqual(list(layouts), ["good"])
            self.assertEqual(layouts["good"].name, "Good")
            with self.assertRaises(ValueError):
                load_layout(folder / "bad.json")


class BundledLayoutTests(unittest.TestCase):
    def test_every_bundled_layout_loads_and_runs(self):
        files = sorted(LAYOUTS_DIR.glob("*.json"))
        self.assertGreater(len(files), 0)
        for path in files:
            with self.subTest(layout=path.name):
                layout_file = load_layout(path)
                layout = layout_file.layout.with_robot_starts(3)
                model = Warehouse(layout=layout, num_robots=3, num_orders=5, rng=1)
                model.run_until_complete(max_time=5_000)
                self.assertEqual(model.metrics.completed_orders, 5)


if __name__ == "__main__":
    unittest.main()
