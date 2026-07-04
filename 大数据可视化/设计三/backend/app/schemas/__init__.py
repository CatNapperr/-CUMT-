from app.schemas.common import CamelCaseModel
from app.schemas.user import UserOut
from app.schemas.user_profile import UserProfileOut, UserProfileUpdate
from app.schemas.nutrition_targets import NutritionTargetsOut
from app.schemas.media import MediaUploadResponse
from app.schemas.summary import DaySummary
from app.schemas.analytics import WeekAnalytics, DayItem, WeeklyAverage
from app.schemas.meal import (
    AlternativeOut, AlternativeCreate,
    MealItemOut, MealItemCreate, MealItemUpdate,
    MealCreate, MealUpdate, DuplicateRequest,
    MealListItem, MealDetail, MealListResponse,
)

__all__ = [
    "CamelCaseModel",
    "UserOut", "UserProfileOut", "UserProfileUpdate",
    "NutritionTargetsOut",
    "AlternativeOut", "AlternativeCreate",
    "MealItemOut", "MealItemCreate", "MealItemUpdate",
    "MealCreate", "MealUpdate", "DuplicateRequest",
    "MealListItem", "MealDetail", "MealListResponse",
    "MediaUploadResponse",
    "DaySummary",
    "WeekAnalytics", "DayItem", "WeeklyAverage",
]
