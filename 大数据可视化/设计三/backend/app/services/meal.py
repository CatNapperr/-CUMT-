from datetime import date
from sqlalchemy.orm import Session
from app.models.meal import Meal
from app.models.meal_item import MealItem
from app.models.meal_item_alternative import MealItemAlternative
from app.schemas.meal import (
    meal_type_label,
    format_date_string,
    MealListItem,
    MealDetail,
    MealItemOut,
    AlternativeOut,
)


def recalculate_meal_totals(db: Session, meal: Meal) -> None:
    items = db.query(MealItem).filter(MealItem.meal_id == meal.id).all()
    meal.calories = sum(i.calories for i in items)
    meal.protein = sum(i.protein for i in items)
    meal.carbs = sum(i.carbs for i in items)
    meal.fat = sum(i.fat for i in items)
    db.commit()
    db.refresh(meal)


def build_meal_list_item(meal: Meal) -> MealListItem:
    return MealListItem(
        id=meal.id,
        title=meal.title,
        meal_type=meal.meal_type,
        meal_type_label=meal_type_label(meal.meal_type),
        meal_date=meal.meal_date.isoformat(),
        date_string=format_date_string(meal.meal_date),
        time_string=meal.time_string,
        calories=meal.calories,
        protein=meal.protein,
        carbs=meal.carbs,
        fat=meal.fat,
        image_url=meal.image_url,
    )


def _item_out_with_alts(item: MealItem, alts: list[MealItemAlternative]) -> MealItemOut:
    return MealItemOut(
        id=item.id,
        name=item.name,
        calories=item.calories,
        protein=item.protein,
        carbs=item.carbs,
        fat=item.fat,
        weight_grams=item.weight_grams,
        weight_string=item.weight_string or "",
        alternatives=[
            AlternativeOut(
                id=a.id,
                name=a.name,
                calories=a.calories,
                weight_string=a.weight_string,
            )
            for a in alts
        ],
    )


def build_meal_detail(db: Session, meal: Meal) -> MealDetail:
    items = (
        db.query(MealItem)
        .filter(MealItem.meal_id == meal.id)
        .order_by(MealItem.sort_order)
        .all()
    )
    return MealDetail(
        id=meal.id,
        title=meal.title,
        meal_type=meal.meal_type,
        meal_type_label=meal_type_label(meal.meal_type),
        meal_date=meal.meal_date.isoformat(),
        date_string=format_date_string(meal.meal_date),
        time_string=meal.time_string,
        calories=meal.calories,
        protein=meal.protein,
        carbs=meal.carbs,
        fat=meal.fat,
        notes=meal.notes,
        image_id=meal.image_id,
        image_url=meal.image_url,
        multiplier=meal.multiplier,
        is_collected=meal.is_collected,
        is_liked=meal.is_liked,
        health_score=meal.health_score,
        health_message=meal.health_message,
        source=meal.source,
        items=[
            _item_out_with_alts(
                i,
                db.query(MealItemAlternative)
                .filter(MealItemAlternative.meal_item_id == i.id)
                .order_by(MealItemAlternative.sort_order)
                .all(),
            )
            for i in items
        ],
    )


def duplicate_meal(db: Session, source_meal: Meal, new_date: date,
                   new_time_string: str, new_source: str) -> Meal:
    """Clone a meal (with all items and alternatives) to a new date."""
    meal = Meal(
        user_id=source_meal.user_id,
        title=source_meal.title,
        meal_type=source_meal.meal_type,
        meal_date=new_date,
        time_string=new_time_string,
        notes=source_meal.notes,
        image_id=source_meal.image_id,
        image_url=source_meal.image_url,
        multiplier=source_meal.multiplier,
        is_collected=False,
        is_liked=None,
        health_score=source_meal.health_score,
        health_message=source_meal.health_message,
        source=new_source,
    )
    db.add(meal)
    db.flush()

    source_items = (
        db.query(MealItem)
        .filter(MealItem.meal_id == source_meal.id)
        .order_by(MealItem.sort_order)
        .all()
    )
    for item in source_items:
        alts = (
            db.query(MealItemAlternative)
            .filter(MealItemAlternative.meal_item_id == item.id)
            .order_by(MealItemAlternative.sort_order)
            .all()
        )
        new_item = MealItem(
            meal_id=meal.id,
            name=item.name,
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat,
            weight_grams=item.weight_grams,
            weight_string=item.weight_string,
            sort_order=item.sort_order,
        )
        db.add(new_item)
        db.flush()
        for alt in alts:
            db.add(MealItemAlternative(
                meal_item_id=new_item.id,
                name=alt.name,
                calories=alt.calories,
                weight_string=alt.weight_string,
                sort_order=alt.sort_order,
            ))

    recalculate_meal_totals(db, meal)
    return meal
