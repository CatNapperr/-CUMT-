from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.analytics import WeekAnalytics, VALID_METRICS
from app.schemas.meal import validate_date_str
from app.services.analytics import get_week_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/week", response_model=WeekAnalytics)
def week_analytics(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    metric: str = Query("calories", description="Metric: calories/protein/carbs/fat"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Validate date formats
    try:
        validate_date_str(start)
        validate_date_str(end)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    start_date = date_type.fromisoformat(start)
    end_date = date_type.fromisoformat(end)

    # Must be exactly 7 days
    if (end_date - start_date).days != 6:
        raise HTTPException(
            status_code=422,
            detail="Date range must be exactly 7 days (start to end inclusive)",
        )

    # Validate metric
    if metric not in VALID_METRICS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid metric '{metric}'; allowed: {', '.join(sorted(VALID_METRICS))}",
        )

    try:
        return get_week_analytics(db, current_user_id, start_date, end_date, metric)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
