from __future__ import annotations

from typing import Iterable

from mesa import Agent


class Rack(Agent):
    """A movable shelf holding a set of products (SKUs)."""

    def __init__(self, model, rack_id: str, skus: Iterable[str] = ()):
        super().__init__(model)
        self.rack_id = rack_id
        self.skus: frozenset[str] = frozenset(skus)
        self.carried_by: str | None = None
        self.reserved_by_task: str | None = None
        self.delivered = False

    @property
    def is_free(self) -> bool:
        return self.carried_by is None and self.reserved_by_task is None


class PickingStation(Agent):
    def __init__(self, model, station_id: str):
        super().__init__(model)
        self.station_id = station_id
