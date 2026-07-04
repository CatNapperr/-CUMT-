from __future__ import annotations

from datetime import datetime, time
from random import uniform
from typing import Any

import numpy as np


def _get_value(road: Any, key: str) -> Any:
    if hasattr(road, key):
        return getattr(road, key)
    if isinstance(road, dict):
        return road[key]
    raise AttributeError(f"road does not provide attribute '{key}'")


def _is_weekend(current_time: datetime) -> bool:
    return current_time.weekday() >= 5


def _is_between(current_time: datetime, start: time, end: time) -> bool:
    current_time_only = current_time.time()
    if start <= end:
        return start <= current_time_only < end
    return current_time_only >= start or current_time_only < end


def _base_flow_factor(current_time: datetime) -> float:
    if _is_weekend(current_time):
        if _is_between(current_time, time(10, 0), time(12, 0)) or _is_between(current_time, time(16, 0), time(18, 0)):
            return 0.7
        return 0.3

    if _is_between(current_time, time(7, 0), time(9, 0)):
        return 0.85
    if _is_between(current_time, time(17, 0), time(19, 0)):
        return 0.9
    if _is_between(current_time, time(22, 0), time(23, 59, 59)) or _is_between(current_time, time(0, 0), time(5, 0)):
        return 0.05
    return 0.4


def calculate_current_traffic(road: Any, current_time: datetime) -> tuple[int, float, float]:
    capacity = max(int(_get_value(road, "capacity")), 1)
    free_flow_speed = float(_get_value(road, "free_flow_speed"))
    road_type = str(_get_value(road, "type")) if hasattr(road, "type") or isinstance(road, dict) else "arterial"

    road_type_factor = {
        "expressway": 1.15,
        "arterial": 1.0,
        "branch": 0.82,
    }.get(road_type, 1.0)

    hour_angle = (current_time.hour + current_time.minute / 60.0) / 24.0 * 2 * np.pi
    minute_angle = current_time.minute / 60.0 * 2 * np.pi
    temporal_wave = 1.0 + 0.18 * np.sin(hour_angle - np.pi / 3) + 0.05 * np.sin(minute_angle * 2 + capacity / 10000.0)

    base_flow = capacity * _base_flow_factor(current_time) * road_type_factor * temporal_wave
    noise_sigma = base_flow * 0.1
    volume = int(round(max(0.0, np.random.normal(base_flow, noise_sigma))))

    congestion_ratio = min(0.9, volume / capacity)
    speed = max(0.0, free_flow_speed * (1 - congestion_ratio))
    occupancy = min(99.99, max(0.0, (volume / capacity) * 100 * uniform(0.8, 1.2)))

    return volume, round(speed, 2), round(occupancy, 2)


def build_current_snapshot(road: Any, current_time: datetime) -> dict[str, Any]:
    volume, speed, occupancy = calculate_current_traffic(road, current_time)
    return {
        "road_id": _get_value(road, "id"),
        "road_name": _get_value(road, "name"),
        "volume": volume,
        "speed": speed,
        "occupancy": occupancy,
        "timestamp": current_time,
    }
