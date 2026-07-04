import logging
from datetime import date as date_type
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.db.session import get_db
from app.models.media_asset import MediaAsset
from app.models.user import User
from app.models.meal import Meal
from app.models.meal_item import MealItem
from app.models.meal_item_alternative import MealItemAlternative
from app.schemas.meal import (
    validate_date_str,
    MealCreate, MealUpdate, DuplicateRequest,
    MealItemCreate, MealItemUpdate,
    MealListItem, MealDetail, MealListResponse,
    AlternativeCreate,
)
from app.services.meal import (
    recalculate_meal_totals, build_meal_list_item, build_meal_detail, duplicate_meal,
)
from app.services.media import (
    validate_image, guess_extension, build_image_url,
    generate_storage_key, MAX_FILE_SIZE,
)
from app.services.gemini import analyze_food_image

router = APIRouter(prefix="/meals", tags=["meals"])

logger = logging.getLogger(__name__)

# ── helpers ────────────────────────────────────────────────

MEAL_TYPE_ENUMS = {"breakfast", "lunch", "dinner", "snack"}
SOURCE_ENUMS = {"manual_mock", "mock_image", "search_history", "manual", "ai_image", "ai_text"}


def _enum_err(field: str, allowed: set) -> HTTPException:
    return HTTPException(status_code=422, detail=f"Invalid {field}; allowed: {', '.join(sorted(allowed))}")


def _assert_meal_owner(meal: Meal, user_id: str) -> None:
    if meal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Meal not found")


def _persist_item(db: Session, meal_id: str, item_in: MealItemCreate, sort: int) -> MealItem:
    item = MealItem(
        meal_id=meal_id,
        name=item_in.name,
        calories=item_in.calories,
        protein=item_in.protein,
        carbs=item_in.carbs,
        fat=item_in.fat,
        weight_grams=item_in.weight_grams,
        weight_string=item_in.weight_string,
        sort_order=sort,
    )
    db.add(item)
    db.flush()
    for i, alt in enumerate(item_in.alternatives or []):
        db.add(MealItemAlternative(
            meal_item_id=item.id,
            name=alt.name,
            calories=alt.calories,
            weight_string=alt.weight_string,
            sort_order=i,
        ))
    return item


# ── CRUD ───────────────────────────────────────────────────

@router.get("", response_model=MealListResponse)
def list_meals(
    date_param: str | None = Query(None, alias="date"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    q = db.query(Meal).filter(Meal.user_id == current_user_id)

    if date_param:
        validate_date_str(date_param)
        q = q.filter(Meal.meal_date == date_type.fromisoformat(date_param))
    elif start and end:
        validate_date_str(start)
        validate_date_str(end)
        q = q.filter(Meal.meal_date.between(date_type.fromisoformat(start), date_type.fromisoformat(end)))

    meals = q.order_by(Meal.meal_date.desc(), Meal.time_string.desc()).all()
    return MealListResponse(items=[build_meal_list_item(m) for m in meals])


@router.post("", response_model=MealDetail, status_code=201)
def create_meal(
    payload: MealCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not payload.items:
        raise HTTPException(status_code=422, detail="items must not be empty")
    if payload.meal_type not in MEAL_TYPE_ENUMS:
        raise _enum_err("meal_type", MEAL_TYPE_ENUMS)
    if payload.source not in SOURCE_ENUMS:
        raise _enum_err("source", SOURCE_ENUMS)

    validate_date_str(payload.meal_date)

    meal = Meal(
        user_id=current_user_id,
        title=payload.title,
        meal_type=payload.meal_type,
        meal_date=date_type.fromisoformat(payload.meal_date),
        time_string=payload.time_string,
        notes=payload.notes,
        image_id=payload.image_id,
        image_url=payload.image_url,
        multiplier=payload.multiplier,
        is_collected=payload.is_collected,
        is_liked=payload.is_liked,
        health_score=payload.health_score,
        health_message=payload.health_message,
        source=payload.source,
    )
    db.add(meal)
    db.flush()

    for i, item_in in enumerate(payload.items):
        _persist_item(db, meal.id, item_in, i)

    recalculate_meal_totals(db, meal)
    return build_meal_detail(db, meal)


# ── AI Image Analysis ────────────────────────────────────────

MEDIA_SOURCE_ENUMS = {"camera", "gallery", "mock"}


@router.post("/analyze-image", response_model=MealDetail, status_code=201)
async def analyze_meal_image(
    file: UploadFile = File(...),
    source: str = Form("camera"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Accept a food photo, save it, call AI vision API to analyze, create meal, return detail."""
    # 1. Validate source
    if source not in MEDIA_SOURCE_ENUMS:
        allowed = ", ".join(sorted(MEDIA_SOURCE_ENUMS))
        raise HTTPException(status_code=422, detail=f"Invalid source; allowed: {allowed}")

    # 2. Validate image
    try:
        validate_image(file)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit",
        )

    # 3. Save image to disk
    file_ext = guess_extension(file.content_type or "image/jpeg")
    storage_key = generate_storage_key(current_user_id, file_ext)
    upload_path = Path(settings.UPLOAD_DIR) / storage_key
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(contents)

    image_id = Path(storage_key).stem
    image_url = build_image_url(image_id)

    # 4. Create MediaAsset record
    asset = MediaAsset(
        id=image_id,
        user_id=current_user_id,
        file_name=file.filename or f"{image_id}{file_ext}",
        content_type=file.content_type or "image/jpeg",
        storage_key=storage_key,
        image_url=image_url,
        size_bytes=len(contents),
        source=source,
    )
    db.add(asset)
    db.flush()

    # 5. Call AI vision API
    try:
        ai_result = await analyze_food_image(contents, file.content_type or "image/jpeg")
    except Exception as e:
        db.rollback()
        logger.error("AI vision analysis failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}")

    # 6. Map AI meal type
    meal_type_map = {
        "早餐": "breakfast",
        "午餐": "lunch",
        "晚餐": "dinner",
        "加餐": "snack",
    }
    meal_type = meal_type_map.get(ai_result.get("mealType", ""), "lunch")
    now = datetime.now()

    # 7. Create Meal
    meal = Meal(
        user_id=current_user_id,
        title=ai_result.get("title", "AI 分析餐食"),
        meal_type=meal_type,
        meal_date=now.date(),
        time_string=now.strftime("%H:%M"),
        image_id=asset.id,
        image_url=asset.image_url,
        health_score=ai_result.get("healthScore"),
        health_message=ai_result.get("healthMessage"),
        source="ai_image",
    )
    db.add(meal)
    db.flush()

    # 8. Create items & alternatives
    for i, item in enumerate(ai_result.get("items", [])):
        meal_item = MealItem(
            meal_id=meal.id,
            name=item.get("name", ""),
            calories=item.get("calories", 0),
            protein=item.get("protein", 0),
            carbs=item.get("carbs", 0),
            fat=item.get("fat", 0),
            weight_string=item.get("weightString", ""),
            sort_order=i,
        )
        db.add(meal_item)
        db.flush()

        for j, alt_name in enumerate(item.get("alternatives", [])):
            db.add(MealItemAlternative(
                meal_item_id=meal_item.id,
                name=alt_name,
                sort_order=j,
            ))

    recalculate_meal_totals(db, meal)
    return build_meal_detail(db, meal)


# ── Search (must be before /{meal_id}) ───────────────────────

@router.get("/search", response_model=MealListResponse)
def search_meals(
    q: str | None = Query(None, description="Search keyword"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = db.query(Meal).filter(Meal.user_id == current_user_id)

    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            or_(
                Meal.title.like(like_pattern),
                Meal.meal_type.like(like_pattern),
                Meal.id.in_(
                    db.query(MealItem.meal_id).filter(
                        MealItem.name.like(like_pattern)
                    )
                ),
            )
        )

    meals = (
        query.order_by(Meal.updated_at.desc(), Meal.created_at.desc())
        .limit(limit)
        .all()
    )
    return MealListResponse(items=[build_meal_list_item(m) for m in meals])


@router.get("/{meal_id}", response_model=MealDetail)
def get_meal(
    meal_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    _assert_meal_owner(meal, current_user_id)
    return build_meal_detail(db, meal)


@router.patch("/{meal_id}", response_model=MealDetail)
def update_meal(
    meal_id: str,
    payload: MealUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    _assert_meal_owner(meal, current_user_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("meal_type",) and value is not None and value not in MEAL_TYPE_ENUMS:
            raise _enum_err("meal_type", MEAL_TYPE_ENUMS)
        if field == "meal_date" and value is not None:
            validate_date_str(value)
            value = date_type.fromisoformat(value)
        setattr(meal, field, value)

    db.commit()
    db.refresh(meal)
    return build_meal_detail(db, meal)


@router.delete("/{meal_id}", status_code=204)
def delete_meal(
    meal_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    _assert_meal_owner(meal, current_user_id)
    db.delete(meal)
    db.commit()


# ── Item endpoints ─────────────────────────────────────────

@router.post("/{meal_id}/items", response_model=MealDetail, status_code=201)
def create_meal_item(
    meal_id: str,
    payload: MealItemCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    _assert_meal_owner(meal, current_user_id)

    max_sort = (
        db.query(MealItem.sort_order)
        .filter(MealItem.meal_id == meal_id)
        .order_by(MealItem.sort_order.desc())
        .first()
    )
    next_sort = (max_sort[0] + 1) if max_sort else 0
    _persist_item(db, meal.id, payload, next_sort)
    recalculate_meal_totals(db, meal)
    return build_meal_detail(db, meal)


@router.patch("/item/{item_id}", response_model=MealDetail)
def update_meal_item(
    item_id: str,
    payload: MealItemUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = db.query(MealItem).filter(MealItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Meal item not found")
    meal = db.query(Meal).filter(Meal.id == item.meal_id).first()
    _assert_meal_owner(meal, current_user_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    db.commit()

    recalculate_meal_totals(db, meal)
    return build_meal_detail(db, meal)


@router.delete("/item/{item_id}", response_model=MealDetail)
def delete_meal_item(
    item_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = db.query(MealItem).filter(MealItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Meal item not found")
    meal = db.query(Meal).filter(Meal.id == item.meal_id).first()
    _assert_meal_owner(meal, current_user_id)

    # Don't allow deleting the last item
    remaining = db.query(MealItem).filter(MealItem.meal_id == meal.id).count()
    if remaining <= 1:
        raise HTTPException(
            status_code=422,
            detail="Cannot delete the last item; delete the meal instead",
        )

    db.delete(item)
    db.flush()
    recalculate_meal_totals(db, meal)
    return build_meal_detail(db, meal)


# ── Duplicate ────────────────────────────────────────────────

@router.post("/{meal_id}/duplicate", response_model=MealDetail, status_code=201)
def duplicate_existing_meal(
    meal_id: str,
    payload: DuplicateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    source = db.query(Meal).filter(Meal.id == meal_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Meal not found")
    if source.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Meal not found")

    validate_date_str(payload.meal_date)
    new_date = date_type.fromisoformat(payload.meal_date)

    new_meal = duplicate_meal(db, source, new_date, payload.time_string, payload.source)
    return build_meal_detail(db, new_meal)
