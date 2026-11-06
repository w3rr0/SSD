from __future__ import annotations

from mesa import Agent


class Rack(Agent):
    def __init__(self, model, rack_id: str):
        super().__init__(model)
        self.rack_id = rack_id
        self.carried_by: str | None = None
        self.delivered = False


class PickingStation(Agent):
    def __init__(self, model, station_id: str):
        super().__init__(model)
        self.station_id = station_id
