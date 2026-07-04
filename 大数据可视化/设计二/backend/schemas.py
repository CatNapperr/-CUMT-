from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoadSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    free_flow_speed: int
    capacity: int


class CurrentTrafficItem(BaseModel):
    road_id: int
    road_name: str
    volume: int
    speed: float
    occupancy: float
    timestamp: datetime


class CurrentTrafficResponse(BaseModel):
    timestamp: datetime
    items: list[CurrentTrafficItem]


class TrendResponse(BaseModel):
    hours: int
    road_id: int | None
    timestamps: list[datetime]
    volumes: list[float]
    speeds: list[float]
    occupancies: list[float]


class HealthResponse(BaseModel):
    status: str
    database: str


class TrafficAlertItem(BaseModel):
    road_id: int
    road_name: str
    district: str
    risk_level: str
    risk_score: float
    predicted_volume: int
    predicted_speed: float
    reason: str
    recommendation: str


class TrafficAlertResponse(BaseModel):
    generated_at: datetime
    alerts: list[TrafficAlertItem]


class RouteOption(BaseModel):
    route_name: str
    districts: list[str]
    corridors: list[str]
    estimated_minutes: float
    risk_score: float
    summary: str


class RouteRecommendationResponse(BaseModel):
    generated_at: datetime
    origin: str
    destination: str
    options: list[RouteOption]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class TrafficChatRequest(BaseModel):
    question: str
    history: list[ChatTurn] = Field(default_factory=list)


class TrafficChatResponse(BaseModel):
    generated_at: datetime
    provider: str
    model: str
    answer: str
