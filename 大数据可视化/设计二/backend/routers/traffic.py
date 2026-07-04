from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RoadSegment, TrafficHistory
from backend.schemas import CurrentTrafficResponse, TrendResponse
from backend.simulator.generator import build_current_snapshot

router = APIRouter(tags=["traffic"])


@router.get("/current", response_model=CurrentTrafficResponse)
def get_current_traffic(db: Session = Depends(get_db)):
    roads = db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
    current_time = datetime.now()
    items = [build_current_snapshot(road, current_time) for road in roads]
    return {"timestamp": current_time, "items": items}


@router.get("/trend", response_model=TrendResponse)
def get_trend(
    hours: int = Query(24, ge=1, le=168),
    road_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    current_time = datetime.now()
    start_time = current_time - timedelta(hours=hours)

    query = db.query(
        TrafficHistory.timestamp.label("timestamp"),
        func.sum(TrafficHistory.volume).label("volume"),
        func.avg(TrafficHistory.speed).label("speed"),
        func.avg(TrafficHistory.occupancy).label("occupancy"),
    ).filter(
        TrafficHistory.timestamp >= start_time,
        TrafficHistory.timestamp <= current_time,
    )

    if road_id is not None:
        query = query.filter(TrafficHistory.road_id == road_id)

    rows = query.group_by(TrafficHistory.timestamp).order_by(TrafficHistory.timestamp.asc()).all()

    return {
        "hours": hours,
        "road_id": road_id,
        "timestamps": [row.timestamp for row in rows],
        "volumes": [float(row.volume) for row in rows],
        "speeds": [float(row.speed) for row in rows],
        "occupancies": [float(row.occupancy) for row in rows],
    }
