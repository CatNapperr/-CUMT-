from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.summary import DaySummary
from app.schemas.meal import validate_date_str
from app.services.summary import get_day_summary

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/day", response_model=DaySummary)
def daily_summary(
    date: str = Query(..., description="ISO date YYYY-MM-DD"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        validate_date_str(date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    target_date = date_type.fromisoformat(date)

    try:
        return get_day_summary(db, current_user_id, target_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
