from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from heapq import nsmallest
from typing import Any

from backend.simulator.generator import build_current_snapshot

ROAD_CITY_PROFILE = {
    1: {"name": "徐贾快速路", "district": "铜山区", "coordinate": [117.115, 34.198]},
    2: {"name": "淮海东路", "district": "云龙区", "coordinate": [117.285, 34.245]},
    3: {"name": "中山北路", "district": "鼓楼区", "coordinate": [117.191, 34.288]},
    4: {"name": "泉山南路", "district": "泉山区", "coordinate": [117.173, 34.206]},
    5: {"name": "贾汪连接线", "district": "贾汪区", "coordinate": [117.452, 34.442]},
    6: {"name": "丰县东环路", "district": "丰县", "coordinate": [116.600, 34.700]},
    7: {"name": "沛县迎宾大道", "district": "沛县", "coordinate": [116.930, 34.730]},
    8: {"name": "邳州运河路", "district": "邳州市", "coordinate": [118.020, 34.330]},
    9: {"name": "睢宁中央大街", "district": "睢宁县", "coordinate": [117.950, 33.890]},
    10: {"name": "新沂新安大道", "district": "新沂市", "coordinate": [118.350, 34.380]},
}

DISTRICT_OPTIONS = ["鼓楼区", "云龙区", "泉山区", "铜山区", "贾汪区", "丰县", "沛县", "邳州市", "睢宁县", "新沂市"]

DISTRICT_GRAPH = {
    "鼓楼区": [
        {"to": "云龙区", "corridor": "中山北路", "minutes": 12.0},
        {"to": "泉山区", "corridor": "彭城路", "minutes": 14.0},
        {"to": "贾汪区", "corridor": "北三环快速路", "minutes": 28.0},
        {"to": "沛县", "corridor": "丰沛快速通道", "minutes": 42.0},
    ],
    "云龙区": [
        {"to": "鼓楼区", "corridor": "中山北路", "minutes": 12.0},
        {"to": "泉山区", "corridor": "解放南路", "minutes": 10.0},
        {"to": "铜山区", "corridor": "徐贾快速路", "minutes": 18.0},
    ],
    "泉山区": [
        {"to": "鼓楼区", "corridor": "彭城路", "minutes": 14.0},
        {"to": "云龙区", "corridor": "解放南路", "minutes": 10.0},
        {"to": "铜山区", "corridor": "泉山南路", "minutes": 16.0},
    ],
    "铜山区": [
        {"to": "云龙区", "corridor": "徐贾快速路", "minutes": 18.0},
        {"to": "泉山区", "corridor": "泉山南路", "minutes": 16.0},
        {"to": "贾汪区", "corridor": "铜山北连接线", "minutes": 24.0},
        {"to": "睢宁县", "corridor": "徐宿淮盐高速", "minutes": 40.0},
    ],
    "贾汪区": [
        {"to": "鼓楼区", "corridor": "北三环快速路", "minutes": 28.0},
        {"to": "铜山区", "corridor": "铜山北连接线", "minutes": 24.0},
        {"to": "新沂市", "corridor": "京沪高速联络线", "minutes": 55.0},
    ],
    "丰县": [
        {"to": "沛县", "corridor": "丰沛快速通道", "minutes": 18.0},
    ],
    "沛县": [
        {"to": "丰县", "corridor": "丰沛快速通道", "minutes": 18.0},
        {"to": "鼓楼区", "corridor": "沛城联络线", "minutes": 42.0},
    ],
    "邳州市": [
        {"to": "新沂市", "corridor": "邳新快速路", "minutes": 28.0},
    ],
    "睢宁县": [
        {"to": "铜山区", "corridor": "徐宿淮盐高速", "minutes": 40.0},
    ],
    "新沂市": [
        {"to": "邳州市", "corridor": "邳新快速路", "minutes": 28.0},
        {"to": "贾汪区", "corridor": "京沪高速联络线", "minutes": 55.0},
    ],
}


@dataclass(slots=True)
class RoadTrafficProfile:
    road_id: int
    road_name: str
    district: str
    coordinate: list[float]


def get_city_profile(road_id: int) -> RoadTrafficProfile:
    profile = ROAD_CITY_PROFILE.get(road_id)
    if profile is None:
        return RoadTrafficProfile(road_id=road_id, road_name=f"路段 {road_id}", district="未知", coordinate=[117.18, 34.25])
    return RoadTrafficProfile(
        road_id=road_id,
        road_name=profile["name"],
        district=profile["district"],
        coordinate=list(profile["coordinate"]),
    )


def build_city_district_load(current_items: list[dict[str, Any]]) -> dict[str, float]:
    district_load: dict[str, float] = {district: 0.0 for district in DISTRICT_OPTIONS}
    district_counts: dict[str, int] = {district: 0 for district in DISTRICT_OPTIONS}

    for item in current_items:
        profile = get_city_profile(int(item["road_id"]))
        district_load[profile.district] += float(item["occupancy"])
        district_counts[profile.district] += 1

    for district, total in district_load.items():
        if district_counts[district] > 0:
            district_load[district] = total / district_counts[district]

    return district_load


def predict_traffic_alerts(roads: list[Any], current_items: list[dict[str, Any]], history_rows: list[Any], current_time: datetime, limit: int = 5) -> list[dict[str, Any]]:
    history_by_road: dict[int, list[Any]] = defaultdict(list)
    for row in history_rows:
        history_by_road[int(row.road_id)].append(row)

    current_by_road = {int(item["road_id"]): item for item in current_items}
    alerts: list[dict[str, Any]] = []

    for road in roads:
        road_id = int(road.id)
        profile = get_city_profile(road_id)
        current = current_by_road.get(road_id)
        if current is None:
            current = build_current_snapshot(road, current_time)

        history = history_by_road.get(road_id, [])
        if len(history) >= 2:
            first = history[0]
            last = history[-1]
            volume_trend = (float(last.volume) - float(first.volume)) / max(float(first.volume), 1.0)
            speed_trend = float(first.speed) - float(last.speed)
        else:
            volume_trend = 0.0
            speed_trend = 0.0

        volume_ratio = float(current["volume"]) / max(float(road.capacity), 1.0) * 100
        speed_drop_ratio = max(0.0, (float(road.free_flow_speed) - float(current["speed"])) / max(float(road.free_flow_speed), 1.0) * 100)
        trend_factor = max(0.0, min(30.0, volume_trend * 35.0 + speed_trend * 1.8))
        risk_score = min(100.0, max(0.0, 0.35 * float(current["occupancy"]) + 0.35 * volume_ratio + 0.2 * speed_drop_ratio + 0.1 * trend_factor))

        if risk_score >= 80:
            risk_level = "严重"
        elif risk_score >= 60:
            risk_level = "高"
        elif risk_score >= 40:
            risk_level = "中"
        else:
            risk_level = "低"

        reasons = []
        if float(current["occupancy"]) >= 70:
            reasons.append("占有率偏高")
        if volume_trend > 0.08:
            reasons.append("近一小时流量持续上升")
        if speed_drop_ratio >= 25:
            reasons.append("速度较自由流明显下降")
        if not reasons:
            reasons.append("交通状态总体平稳")

        recommendation = {
            "严重": "建议尽快分流并优先选择绕行路线。",
            "高": "建议提前出行并关注实时路况。",
            "中": "建议保持当前路线，但注意避开高峰时段。",
            "低": "当前路段运行正常，可继续按计划通行。",
        }[risk_level]

        predicted_volume = int(round(float(current["volume"]) * (1 + min(0.25, volume_trend * 0.12))))
        predicted_speed = round(max(0.0, float(current["speed"]) - speed_drop_ratio * 0.12), 2)

        alerts.append(
            {
                "road_id": road_id,
                "road_name": current["road_name"],
                "district": profile.district,
                "risk_level": risk_level,
                "risk_score": round(risk_score, 2),
                "predicted_volume": predicted_volume,
                "predicted_speed": predicted_speed,
                "reason": "，".join(reasons),
                "recommendation": recommendation,
            }
        )

    return sorted(alerts, key=lambda item: item["risk_score"], reverse=True)[:limit]


def _edge_pressure(district: str, district_load: dict[str, float]) -> float:
    return district_load.get(district, 0.0)


def _enumerate_paths(origin: str, destination: str, max_depth: int = 4) -> list[list[str]]:
    paths: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        if len(path) > max_depth + 1:
            return
        if node == destination:
            paths.append(path.copy())
            return
        for edge in DISTRICT_GRAPH.get(node, []):
            next_node = edge["to"]
            if next_node in path:
                continue
            dfs(next_node, path + [next_node])

    dfs(origin, [origin])
    return paths


def recommend_routes(origin: str, destination: str, current_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    district_load = build_city_district_load(current_items)
    all_paths = _enumerate_paths(origin, destination)
    if not all_paths:
        return []

    scored_routes: list[dict[str, Any]] = []

    for path in all_paths:
        corridors: list[str] = []
        estimated_minutes = 0.0
        risk_score = 0.0

        for start, end in zip(path, path[1:]):
            edge = next((item for item in DISTRICT_GRAPH.get(start, []) if item["to"] == end), None)
            if edge is None:
                continue
            pressure = (_edge_pressure(start, district_load) + _edge_pressure(end, district_load)) / 2
            adjusted_minutes = float(edge["minutes"]) * (1 + pressure / 120.0)
            estimated_minutes += adjusted_minutes
            risk_score += pressure / 2.4 + float(edge["minutes"]) / 3.2
            corridors.append(edge["corridor"])

        if not corridors:
            continue

        route_name = "快速线路"
        if risk_score >= 70:
            route_name = "避堵线路"
        elif risk_score >= 45:
            route_name = "均衡线路"

        summary = f"经过{len(path) - 1}段道路，从{' → '.join(path)}"
        scored_routes.append(
            {
                "route_name": route_name,
                "districts": path,
                "corridors": corridors,
                "estimated_minutes": round(estimated_minutes, 1),
                "risk_score": round(min(100.0, risk_score), 2),
                "summary": summary,
            }
        )

    ranked = sorted(scored_routes, key=lambda item: (item["estimated_minutes"], item["risk_score"]))
    top_three = ranked[:3]

    if top_three:
        top_three[0]["route_name"] = "推荐优先线路"
    if len(top_three) > 1:
        top_three[1]["route_name"] = "平衡通行线路"
    if len(top_three) > 2:
        top_three[2]["route_name"] = "备用绕行线路"

    return top_three
