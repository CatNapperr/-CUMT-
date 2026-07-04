from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RoadSegment
from backend.schemas import RoadSegmentRead

router = APIRouter(prefix="/roads", tags=["roads"])


@router.get("", response_model=list[RoadSegmentRead])
def list_roads(db: Session = Depends(get_db)):
    return db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
