import re
from datetime import date
from app.schemas.common import CamelCaseModel

# ── helpers ────────────────────────────────────────────────

_MEAL_TYPE_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "加餐",
}


def meal_type_label(meal_type: str) -> str:
    return _MEAL_TYPE_LABELS.get(meal_type, meal_type)


def format_date_string(d: date) -> str:
    return f"{d.month}月{d.day}日"


# ── Alternatives ───────────────────────────────────────────

class AlternativeOut(CamelCaseModel):
    id: str
    name: str
    calories: int | None = None
    weight_string: str | None = None


class AlternativeCreate(CamelCaseModel):
    name: str
    calories: int | None = None
    weight_string: str | None = None


# ── Meal Items ─────────────────────────────────────────────

class MealItemOut(CamelCaseModel):
    id: str
    name: str
    calories: int
    protein: int
    carbs: int
    fat: int
    weight_grams: int | None = None
    weight_string: str
    alternatives: list[AlternativeOut] = []


class MealItemCreate(CamelCaseModel):
    name: str
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0
    weight_grams: int | None = None
    weight_string: str = ""
    alternatives: list[AlternativeCreate] = []


class MealItemUpdate(CamelCaseModel):
    name: str | None = None
    calories: int | None = None
    protein: int | None = None
    carbs: int | None = None
    fat: int | None = None
    weight_grams: int | None = None
    weight_string: str | None = None


# ── Meal ──────────────────────────────────────────────────

class MealCreate(CamelCaseModel):
    title: str
    meal_type: str
    meal_date: str  # YYYY-MM-DD
    time_string: str
    notes: str = ""
    image_id: str | None = None
    image_url: str | None = None
    multiplier: float = 1.0
    is_collected: bool = False
    is_liked: bool | None = None
    health_score: str | None = None
    health_message: str | None = None
    source: str
    items: list[MealItemCreate]


class MealUpdate(CamelCaseModel):
    title: str | None = None
    meal_type: str | None = None
    meal_date: str | None = None
    time_string: str | None = None
    notes: str | None = None
    image_id: str | None = None
    image_url: str | None = None
    multiplier: float | None = None
    is_collected: bool | None = None
    is_liked: bool | None = None
    health_score: str | None = None
    health_message: str | None = None


class DuplicateRequest(CamelCaseModel):
    meal_date: str
    time_string: str
    source: str = "search_history"


# ── Response ──────────────────────────────────────────────

class MealListItem(CamelCaseModel):
    id: str
    title: str
    meal_type: str
    meal_type_label: str
    meal_date: str
    date_string: str
    time_string: str
    calories: int
    protein: int
    carbs: int
    fat: int
    image_url: str | None = None


class MealDetail(CamelCaseModel):
    id: str
    title: str
    meal_type: str
    meal_type_label: str
    meal_date: str
    date_string: str
    time_string: str
    calories: int
    protein: int
    carbs: int
    fat: int
    notes: str
    image_id: str | None = None
    image_url: str | None = None
    multiplier: float
    is_collected: bool
    is_liked: bool | None = None
    health_score: str | None = None
    health_message: str | None = None
    source: str
    items: list[MealItemOut] = []


class MealListResponse(CamelCaseModel):
    items: list[MealListItem]


# ── Input validation ──────────────────────────────────────

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date_str(v: str) -> None:
    if not _DATE_RE.match(v):
        raise ValueError(f"Invalid date format '{v}'; expected YYYY-MM-DD")
