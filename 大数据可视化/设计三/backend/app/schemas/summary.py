from app.schemas.common import CamelCaseModel


class DaySummary(CamelCaseModel):
    date: str
    date_string: str
    target_calories: int
    calories: int
    remaining_calories: int
    protein: int
    protein_target: int
    carbs: int
    carbs_target: int
    fat: int
    fat_target: int
    meal_count: int
