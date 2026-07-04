from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RoadSegment, TrafficHistory
from backend.schemas import RouteRecommendationResponse, TrafficAlertResponse
from backend.simulator.generator import build_current_snapshot
from backend.simulator.insights import DISTRICT_OPTIONS, predict_traffic_alerts, recommend_routes

router = APIRouter(tags=["insights"])


@router.get("/alerts", response_model=TrafficAlertResponse)
def get_alerts(
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    current_time = datetime.now()
    roads = db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
    current_items = [build_current_snapshot(road, current_time) for road in roads]
    recent_history = (
        db.query(TrafficHistory)
        .filter(TrafficHistory.timestamp >= current_time - timedelta(hours=1))
        .order_by(TrafficHistory.road_id.asc(), TrafficHistory.timestamp.asc())
        .all()
    )
    alerts = predict_traffic_alerts(roads, current_items, recent_history, current_time, limit=limit)
    return {"generated_at": current_time, "alerts": alerts}


@router.get("/routes", response_model=RouteRecommendationResponse)
def get_routes(
    origin: str = Query("鼓楼区"),
    destination: str = Query("铜山区"),
    db: Session = Depends(get_db),
):
    if origin not in DISTRICT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported origin district: {origin}")
    if destination not in DISTRICT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported destination district: {destination}")

    current_time = datetime.now()
    roads = db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
    current_items = [build_current_snapshot(road, current_time) for road in roads]
    options = recommend_routes(origin, destination, current_items)
    return {
        "generated_at": current_time,
        "origin": origin,
        "destination": destination,
        "options": options,
    }
