"""Product placement strategies: which products sit on which rack.

Three strategies from the project description:

* random: products shuffled and dealt to racks,
* ABC: the products giving most orders (class A) on the racks closest to the
  stations, then class B, then class C,
* nearest free slot: after every trip the rack is put down at the free rack
  slot nearest to the station it came from (``NearestFreeSlot``). It only
  decides where racks go back, so it combines with either initial placement.

Every product is stored on exactly one rack; a rack holds about
``products / racks`` products. Distances are Manhattan distances to the
nearest station, as in the model's own rack choice.
"""

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.environment.layout import Coordinate, WarehouseLayout

# Cumulative share of orders closing class A and class B (classic 80/15/5).
ABC_THRESHOLDS = (0.80, 0.95)

RackSkus = dict[str, frozenset[str]]


def manhattan(first: Coordinate, second: Coordinate) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def distance_to_station(layout: WarehouseLayout, position: Coordinate) -> int:
    """Manhattan distance from ``position`` to the nearest picking station."""
    return min(manhattan(position, station) for station in layout.stations.values())


def racks_by_distance(layout: WarehouseLayout) -> list[str]:
    """Rack IDs from the closest to a station to the farthest (ties: rack ID)."""
    return sorted(
        layout.racks,
        key=lambda rack_id: (
            distance_to_station(layout, layout.racks[rack_id]),
            _rack_number(rack_id),
        ),
    )


def _rack_number(rack_id: str) -> tuple[int, str]:
    suffix = rack_id.rsplit("-", 1)[-1]
    return (int(suffix), rack_id) if suffix.isdigit() else (0, rack_id)


def fill_racks(products: Sequence[str], racks: Sequence[str]) -> RackSkus:
    """Put products on racks in the given orders, the same number per rack.

    The first ``ceil(products / racks)`` products go to the first rack, the
    next ones to the second rack, and so on; the last racks may hold fewer.
    """
    if not racks:
        raise ValueError("No racks to fill")
    if len(set(products)) != len(products):
        raise ValueError("A product would be placed twice")
    per_rack = max(1, math.ceil(len(products) / len(racks)))
    return {
        rack_id: frozenset(products[index * per_rack : (index + 1) * per_rack])
        for index, rack_id in enumerate(racks)
    }


def random_placement(
    products: Sequence[str], layout: WarehouseLayout, rng: np.random.Generator
) -> RackSkus:
    """Products shuffled and dealt evenly to the racks."""
    shuffled = [products[i] for i in rng.permutation(len(products))]
    return fill_racks(shuffled, list(layout.racks))


def abc_classes(popularity: pd.DataFrame) -> pd.Series:
    """Class A, B or C of every product from its number of orders.

    Products are taken from the most popular; a product belongs to class A
    while the cumulative share of orders (including it) is at most 80%, to B
    up to 95%, the rest to C.
    """
    ordered = popularity.sort_values("orders", ascending=False, kind="stable")
    cumulative = ordered["orders"].cumsum() / ordered["orders"].sum()
    a_limit, b_limit = ABC_THRESHOLDS
    classes = np.where(cumulative <= a_limit, "A", np.where(cumulative <= b_limit, "B", "C"))
    return pd.Series(classes, index=ordered.index, name="abc_class")


def abc_placement(
    popularity: pd.DataFrame, layout: WarehouseLayout, rng: np.random.Generator
) -> RackSkus:
    """Class A on the racks closest to a station, then B, then C.

    Within a class the order is random, so ABC does not sort products by
    popularity inside a class.
    """
    classes = abc_classes(popularity)
    products: list[str] = []
    for label in ("A", "B", "C"):
        members = list(classes.index[classes == label])
        products.extend(members[i] for i in rng.permutation(len(members)))
    return fill_racks(products, racks_by_distance(layout))


class NearestFreeSlot:
    """Return policy: put a rack down at the free slot nearest to its station.

    Slots are the rack positions of the layout. A slot is free when no rack
    stands on it and no other returning rack is heading there. Meant to be
    called from ``Warehouse.return_location(rack)`` after picking, while the
    rack still belongs to its task::

        def return_location(self, rack):
            return self.return_policy.choose(self, rack)
    """

    def __init__(self, layout: WarehouseLayout):
        self.slots: tuple[Coordinate, ...] = tuple(sorted(layout.racks.values()))
        # rack_id -> (slot, task the reservation was made for)
        self._reservations: dict[str, tuple[Coordinate, str]] = {}

    @property
    def reserved(self) -> dict[str, Coordinate]:
        """Slots claimed by racks that were heading to them (may be stale)."""
        return {rack_id: slot for rack_id, (slot, _) in self._reservations.items()}

    def _live_reservations(self, model) -> set[Coordinate]:
        """Slots held by racks that are still on the trip they reserved for.

        A reservation ends when the rack is put down (it then occupies the
        slot as a standing rack) or picked up for a new task. Without this
        check the slot a rack left would stay blocked for every other rack
        while it is away, so racks would mostly return to their own slot.
        """
        live = set()
        for rack_id, (slot, task_id) in list(self._reservations.items()):
            other = model.racks[rack_id]
            if other.carried_by is not None and other.reserved_by_task == task_id:
                live.add(slot)
            else:
                del self._reservations[rack_id]
        return live

    def choose(self, model, rack) -> Coordinate:
        task_id = rack.reserved_by_task
        task = model.tasks_by_id[task_id]
        station = model.layout.stations[task.station_id]
        # A rack heads to one slot at a time; its old reservation is done.
        self._reservations.pop(rack.rack_id, None)
        taken = {
            other.pos for other in model.racks.values() if other.carried_by is None
        } | self._live_reservations(model)
        free = [slot for slot in self.slots if slot not in taken]
        if not free:
            raise RuntimeError(f"No free slot for {rack.rack_id}")
        best = min(free, key=lambda slot: (manhattan(slot, station), slot))
        self._reservations[rack.rack_id] = (best, task_id)
        return best
