import unittest
from datetime import datetime
from xml.etree import ElementTree

from src.agents.robot import RobotState
from src.core.model import Warehouse
from src.environment.layout import WarehouseLayout
from src.orders.models import Order
from src.visualization import panels
from src.visualization.live_stats import (
    FLEET_CATEGORIES,
    snapshot,
)
from src.visualization.svg import render_svg

LAYOUT = WarehouseLayout.from_ascii(
    [
        "  ######",
        "  #....C",
        "###.RR.#",
        "S......#",
        "#BB.RR.#",
        "########",
    ],
    top_down=True,
)
START = datetime(2018, 3, 5, 8, 0)


def make_model(orders=None):
    rack_skus = {rack: frozenset({f"sku-{rack}"}) for rack in LAYOUT.racks}
    if orders is None:
        orders = [
            Order(f"o{i}", [f"sku-rack-{i % 4 + 1}"], created_time=float(5 * i))
            for i in range(6)
        ]
    return Warehouse(
        layout=LAYOUT, num_robots=2, orders=orders, rack_skus=rack_skus, rng=1
    )


class SnapshotTests(unittest.TestCase):
    def test_counts_follow_the_orders(self):
        model = make_model()
        model.run_until_complete(max_time=2_000)

        snap = snapshot(model)

        self.assertEqual(snap.orders_total, 6)
        self.assertEqual(snap.completed, 6)
        self.assertEqual(snap.waiting + snap.in_progress, 0)
        self.assertEqual(snap.upcoming, 0)
        self.assertIsNotNone(snap.average_completion_s)
        last = max(model.orders, key=lambda o: o.completed_time)
        self.assertEqual(snap.last_order_id, last.order_id)
        self.assertAlmostEqual(snap.last_order_duration_s, last.completion_time)

    def test_upcoming_orders_are_not_yet_in_the_list(self):
        model = make_model()
        model.step()  # t = 1: only o0 (t = 0) has arrived

        snap = snapshot(model)

        self.assertEqual(snap.arrived, 1)
        self.assertEqual(snap.upcoming, 5)
        self.assertEqual([row.order_id for row in snap.recent_orders], ["o0"])

    def test_recent_orders_are_newest_first(self):
        model = make_model()
        model.run_for(30)

        ids = [row.order_id for row in snapshot(model).recent_orders]

        self.assertEqual(ids, sorted(ids, key=lambda i: int(i[1:]), reverse=True))

    def test_fleet_time_adds_up_to_robot_time(self):
        model = make_model()
        model.run_for(200)

        snap = snapshot(model)

        self.assertEqual(set(snap.fleet_time), {key for key, _ in FLEET_CATEGORIES})
        self.assertAlmostEqual(
            sum(snap.fleet_time.values()), 2 * float(model.time), places=6
        )
        self.assertTrue(all(value >= 0 for value in snap.fleet_time.values()))

    def test_robot_rows_report_battery_and_idle_time(self):
        model = make_model(orders=[])
        model.run_for(10)

        rows = snapshot(model).robots

        self.assertEqual([row.number for row in rows], [1, 2])
        self.assertTrue(all(row.state is RobotState.IDLE for row in rows))
        self.assertTrue(all(row.idle_s == 10 for row in rows))
        self.assertTrue(all(row.battery == 100 for row in rows))


class SvgTests(unittest.TestCase):
    def test_svg_is_well_formed_and_shows_every_object(self):
        model = make_model()
        model.run_for(20)

        svg = render_svg(model, alert_robots=frozenset({"robot-1"}))
        root = ElementTree.fromstring(svg)

        self.assertTrue(root.tag.endswith("svg"))
        titles = [
            element.text
            for element in root.iter()
            if element.tag.endswith("title") and element.text
        ]
        for name in ("robot-1", "robot-2", "station-1", "charger-1", "rack-1"):
            self.assertTrue(any(t.startswith(name) for t in titles), name)
        self.assertIn('class="pulse"', svg)

    def test_outside_cells_are_not_drawn_as_floor_or_wall(self):
        model = make_model(orders=[])
        svg = render_svg(model)
        root = ElementTree.fromstring(svg)
        # The top-left two cells are outside the building (top row, x = 0..1).
        for rect in root.iter():
            if not rect.tag.endswith("rect"):
                continue
            if rect.get("y") == "0" and rect.get("x") == "0":
                self.fail("A cell outside the building was drawn")

    def test_heat_colours_and_hidden_routes(self):
        model = make_model()
        model.run_for(60)

        plain = render_svg(model, show_routes=True)
        hidden = render_svg(model, show_routes=False, rack_colors="heat")

        self.assertIn("polyline", plain)
        self.assertNotIn("polyline", hidden)


class PanelTests(unittest.TestCase):
    def test_duration_and_clock_formats(self):
        self.assertEqual(panels.duration(None), "–")
        self.assertEqual(panels.duration(42.4), "42 s")
        self.assertEqual(panels.duration(185), "3 min 05 s")
        self.assertEqual(panels.duration(3720), "1 h 02 min")
        self.assertEqual(panels.clock(START, 90), "08:01:30")

    def test_panels_render_for_a_running_model(self):
        model = make_model()
        model.run_for(60)
        snap = snapshot(model)

        html = (
            panels.kpi_html(snap, START)
            + panels.fleet_html(snap)
            + panels.stations_html(snap)
            + panels.robots_html(snap)
            + panels.orders_html(snap, START)
            + panels.legend_html()
        )

        self.assertIn("Zrealizowane", html)
        self.assertIn("o0", html)
        self.assertIn("08:00:", html)


class VisualModelTests(unittest.TestCase):
    def make(self, **kwargs):
        from src.visualization.app import VisualWarehouse

        params = dict(orders="demo", num_robots=3, hours=1, volume=1.0, seed=2)
        params.update(kwargs)
        return VisualWarehouse(**params)

    def test_demo_run_finishes_with_a_message(self):
        model = self.make()
        while model.running and model.time < 20_000:
            model.step()

        self.assertFalse(model.running)
        self.assertEqual(model.stop_kind, "done")
        self.assertTrue(all(o.completed_time is not None for o in model.orders))

    def test_deadlock_stops_the_run_instead_of_crashing(self):
        from unittest import mock

        from src.pipeline.reservations import DeadlockError

        model = self.make()
        with mock.patch.object(
            Warehouse, "step", side_effect=DeadlockError("robot-2 made no progress")
        ):
            model.step()
            model.step()  # stays stopped, does not raise again

        self.assertFalse(model.running)
        self.assertEqual(model.stop_kind, "alert")
        self.assertIn("Zakleszczenie", model.stop_reason)
        self.assertIn("robot-2", model.alert_robots)

    def test_more_robots_than_starts_get_extra_starts(self):
        model = self.make(layout="hala_L", num_robots=12)

        self.assertEqual(len(model.robots), 12)

    def test_abc_without_olist_data_explains_itself(self):
        model = self.make(placement="ABC")

        self.assertTrue(any("ABC" in notice for notice in model.notices))


if __name__ == "__main__":
    unittest.main()
