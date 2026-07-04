from datetime import date as date_type

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.user_profile import UserProfile
from app.schemas.summary import DaySummary
from app.schemas.meal import format_date_string
from app.services.nutrition import calculate_targets as compute_targets


def get_day_summary(db: Session, user_id: str, target_date: date_type) -> DaySummary:
    # Aggregate meals for the given date
    row = (
        db.query(
            func.coalesce(func.sum(Meal.calories), 0).label("calories"),
            func.coalesce(func.sum(Meal.protein), 0).label("protein"),
            func.coalesce(func.sum(Meal.carbs), 0).label("carbs"),
            func.coalesce(func.sum(Meal.fat), 0).label("fat"),
            func.count(Meal.id).label("meal_count"),
        )
        .filter(Meal.user_id == user_id, Meal.meal_date == target_date)
        .first()
    )

    # Get nutrition targets from profile
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    if not profile:
        raise ValueError("User profile not found")

    targets = compute_targets(profile)

    return DaySummary(
        date=target_date.isoformat(),
        date_string=format_date_string(target_date),
        target_calories=targets["target_calories"],
        calories=row.calories,
        remaining_calories=targets["target_calories"] - row.calories,
        protein=row.protein,
        protein_target=targets["protein"],
        carbs=row.carbs,
        carbs_target=targets["carbs"],
        fat=row.fat,
        fat_target=targets["fat"],
        meal_count=row.meal_count,
    )
