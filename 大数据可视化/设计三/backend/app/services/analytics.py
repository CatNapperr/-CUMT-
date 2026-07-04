from datetime import date as date_type, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.user_profile import UserProfile
from app.schemas.analytics import (
    VALID_METRICS, METRIC_LABELS, WEEKDAY_LABELS,
    DayItem, WeeklyAverage, WeekAnalytics,
)
from app.schemas.meal import format_date_string
from app.services.nutrition import calculate_targets as compute_targets


def _compute_percentages(calories: int, protein: int, carbs: int, fat: int) -> tuple[int, int, int]:
    """Return (fat_percent, carbs_percent, protein_percent)."""
    total = fat + carbs + protein
    if total == 0:
        return 0, 0, 0
    return round(fat / total * 100), round(carbs / total * 100), round(protein / total * 100)


def _day_label(target_date: date_type) -> str:
    """Return e.g. '周一\\n5/25'."""
    wd = target_date.weekday()  # Mon=0 … Sun=6
    return f"{WEEKDAY_LABELS[wd]}\n{target_date.month}/{target_date.day}"


def _date_range_label(start: date_type, end: date_type) -> str:
    """Return e.g. '2026年5月25日 - 2026年5月31日'."""
    def _fmt(d: date_type) -> str:
        return f"{d.year}年{d.month}月{d.day}日"
    return f"{_fmt(start)} - {_fmt(end)}"


def get_week_analytics(
    db: Session,
    user_id: str,
    start: date_type,
    end: date_type,
    metric: str,
) -> WeekAnalytics:
    # Validate metric
    if metric not in VALID_METRICS:
        raise ValueError(f"Invalid metric '{metric}'; allowed: {', '.join(sorted(VALID_METRICS))}")

    # Get target value from profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("User profile not found")

    targets = compute_targets(profile)
    target_map = {
        "calories": targets["target_calories"],
        "protein": targets["protein"],
        "carbs": targets["carbs"],
        "fat": targets["fat"],
    }
    target_value = target_map[metric]

    # Aggregate meals for the date range
    rows = (
        db.query(
            Meal.meal_date,
            func.coalesce(func.sum(Meal.calories), 0).label("calories"),
            func.coalesce(func.sum(Meal.protein), 0).label("protein"),
            func.coalesce(func.sum(Meal.carbs), 0).label("carbs"),
            func.coalesce(func.sum(Meal.fat), 0).label("fat"),
        )
        .filter(
            Meal.user_id == user_id,
            Meal.meal_date.between(start, end),
        )
        .group_by(Meal.meal_date)
        .order_by(Meal.meal_date)
        .all()
    )

    # Build a lookup dict keyed by ISO date
    day_map: dict[str, tuple[int, int, int, int]] = {}
    for r in rows:
        day_map[r.meal_date.isoformat()] = (r.calories, r.protein, r.carbs, r.fat)

    # Build 7 day items (1 per day from start to end)
    days: list[DayItem] = []
    recorded_days = 0
    metric_sum = 0
    fat_sum = 0
    carbs_sum = 0
    protein_sum = 0

    current = start
    while current <= end:
        iso = current.isoformat()
        entry = day_map.get(iso, (0, 0, 0, 0))
        cals, prot, carb, ft = entry

        if cals > 0:
            recorded_days += 1
        metric_sum += _get_metric_value(metric, cals, prot, carb, ft)
        fat_sum += ft
        carbs_sum += carb
        protein_sum += prot

        fat_pct, carbs_pct, protein_pct = _compute_percentages(cals, prot, carb, ft)

        days.append(DayItem(
            date=iso,
            date_string=format_date_string(current),
            day_label=_day_label(current),
            calories=cals,
            protein=prot,
            carbs=carb,
            fat=ft,
            metric_value=_get_metric_value(metric, cals, prot, carb, ft),
            fat_percent=fat_pct,
            carbs_percent=carbs_pct,
            protein_percent=protein_pct,
        ))
        current += timedelta(days=1)

    # Weekly average percentages
    week_fat_pct, week_carbs_pct, week_protein_pct = _compute_percentages(
        0, protein_sum, carbs_sum, fat_sum,
    )

    return WeekAnalytics(
        date_range_label=_date_range_label(start, end),
        metric=metric,
        metric_label=METRIC_LABELS[metric][0],
        metric_unit=METRIC_LABELS[metric][1],
        recorded_days=recorded_days,
        average_value=metric_sum // recorded_days if recorded_days > 0 else 0,
        target_value=target_value,
        days=days,
        weekly_average=WeeklyAverage(
            fat_percent=week_fat_pct,
            carbs_percent=week_carbs_pct,
            protein_percent=week_protein_pct,
        ),
    )


def _get_metric_value(metric: str, calories: int, protein: int, carbs: int, fat: int) -> int:
    mapping = {
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }
    return mapping[metric]
