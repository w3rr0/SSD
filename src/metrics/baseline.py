from dataclasses import dataclass, field
from statistics import mean
from typing import Iterable

from src.core.config import SECONDS_PER_HOUR
from src.orders.models import Order


@dataclass(frozen=True, slots=True)
class SimulationMetrics:
    """Summary of a run. Times are in seconds, distances in metres.

    Two kinds of standing time are reported separately:

    * **traffic wait** - a tick in which a robot did not move because another
      robot held the next cell (a jam in an aisle or at a junction),
    * **queue wait** - time a robot waited for its picking station, from the
      moment it first stood in the approach lane until service started.

    ``traffic_wait_share`` and ``queue_wait_share`` divide the totals by the
    robot-time available in the run (robots x simulated seconds), so they show
    which part of the fleet's capacity was lost to jams and to station queues.
    ``average_traffic_wait_s`` is per robot, while ``average_station_wait`` is
    per station visit.

    ``charger_utilisation`` is the share of the run each charger spent
    charging; ``average_charging_time`` is the mean length of a completed
    session.

    ``failure_count`` counts failures started during the run.
    ``total_repair_time_s`` includes repairs still in progress at the end,
    while ``average_repair_time`` covers completed repairs only.

    ``total_return_distance_m`` is the distance robots covered while carrying
    a rack back; ``average_return_distance_m`` divides it by the number of
    completed returns. ``racks_returned_home_share`` is the fraction of those
    returns that ended on the rack's ``home`` cell (1.0 until a placement
    strategy is wired in). ``rack_slot_utilisation`` is the share of the
    original rack slots occupied by standing racks at the end of the run.
    """

    completed_orders: int
    average_completion_time: float | None
    longest_completion_time: float | None
    average_waiting_time: float | None
    orders_per_hour: float | None
    total_distance_m: float
    simulated_time: float
    station_utilisation: dict[str, float] = field(default_factory=dict)
    average_station_wait: float | None = None
    total_traffic_wait_s: float = 0.0
    average_traffic_wait_s: float | None = None
    traffic_wait_share: float | None = None
    total_queue_wait_s: float = 0.0
    queue_wait_share: float | None = None
    charger_utilisation: dict[str, float] = field(default_factory=dict)
    total_charging_time_s: float = 0.0
    average_charging_time: float | None = None
    failure_count: int = 0
    total_repair_time_s: float = 0.0
    average_repair_time: float | None = None
    total_return_distance_m: float = 0.0
    average_return_distance_m: float | None = None
    return_trips: int = 0
    racks_returned_home_share: float | None = None
    rack_slot_utilisation: float = 0.0

    @classmethod
    def from_orders(
        cls,
        orders: Iterable[Order],
        total_distance_m: float,
        simulated_time: float,
        station_utilisation: dict[str, float] | None = None,
        station_wait_times: Iterable[float] = (),
        traffic_wait_times: Iterable[float] = (),
        charger_utilisation: dict[str, float] | None = None,
        charging_times: Iterable[float] = (),
        total_charging_time_s: float | None = None,
        failure_count: int = 0,
        repair_times: Iterable[float] = (),
        total_repair_time_s: float | None = None,
        total_return_distance_m: float = 0.0,
        return_trips: int = 0,
        racks_returned_home: int = 0,
        rack_slot_utilisation: float = 0.0,
    ) -> SimulationMetrics:
        station_wait_times = list(station_wait_times)
        traffic_wait_times = list(traffic_wait_times)
        charging_times = list(charging_times)
        repair_times = list(repair_times)
        completed = [order for order in orders if order.completion_time is not None]
        durations = [order.completion_time for order in completed]
        waits = [order.waiting_time for order in completed]
        total_queue_wait = sum(station_wait_times)
        total_traffic_wait = sum(traffic_wait_times)
        robot_time = simulated_time * len(traffic_wait_times)
        return cls(
            completed_orders=len(completed),
            average_completion_time=mean(durations) if durations else None,
            longest_completion_time=max(durations) if durations else None,
            average_waiting_time=mean(waits) if waits else None,
            orders_per_hour=(
                len(completed) * SECONDS_PER_HOUR / simulated_time
                if simulated_time > 0
                else None
            ),
            total_distance_m=total_distance_m,
            simulated_time=simulated_time,
            station_utilisation=dict(station_utilisation or {}),
            average_station_wait=(
                mean(station_wait_times) if station_wait_times else None
            ),
            total_traffic_wait_s=total_traffic_wait,
            average_traffic_wait_s=(
                mean(traffic_wait_times) if traffic_wait_times else None
            ),
            traffic_wait_share=(
                total_traffic_wait / robot_time if robot_time > 0 else None
            ),
            total_queue_wait_s=total_queue_wait,
            queue_wait_share=(
                total_queue_wait / robot_time if robot_time > 0 else None
            ),
            charger_utilisation=dict(charger_utilisation or {}),
            total_charging_time_s=(
                sum(charging_times)
                if total_charging_time_s is None
                else total_charging_time_s
            ),
            average_charging_time=(
                mean(charging_times) if charging_times else None
            ),
            failure_count=failure_count,
            total_repair_time_s=(
                sum(repair_times)
                if total_repair_time_s is None
                else total_repair_time_s
            ),
            average_repair_time=(
                mean(repair_times) if repair_times else None
            ),
            total_return_distance_m=total_return_distance_m,
            average_return_distance_m=(
                total_return_distance_m / return_trips if return_trips else None
            ),
            return_trips=return_trips,
            racks_returned_home_share=(
                racks_returned_home / return_trips if return_trips else None
            ),
            rack_slot_utilisation=rack_slot_utilisation,
        )
