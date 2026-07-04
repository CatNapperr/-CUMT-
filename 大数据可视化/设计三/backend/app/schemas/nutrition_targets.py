from app.schemas.common import CamelCaseModel


class NutritionTargetsOut(CamelCaseModel):
    bmr: int
    tdee: int
    target_calories: int
    protein: int
    carbs: int
    fat: int
