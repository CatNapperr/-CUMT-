from app.schemas.common import CamelCaseModel


VALID_METRICS = {"calories", "protein", "carbs", "fat"}

METRIC_LABELS = {
    "calories": ("卡路里", "千卡"),
    "protein": ("蛋白质", "克"),
    "carbs": ("碳水", "克"),
    "fat": ("脂肪", "克"),
}

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class DayItem(CamelCaseModel):
    date: str
    date_string: str
    day_label: str
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0
    metric_value: int = 0
    fat_percent: int = 0
    carbs_percent: int = 0
    protein_percent: int = 0


class WeeklyAverage(CamelCaseModel):
    fat_percent: int = 0
    carbs_percent: int = 0
    protein_percent: int = 0


class WeekAnalytics(CamelCaseModel):
    date_range_label: str
    metric: str
    metric_label: str
    metric_unit: str
    recorded_days: int = 0
    average_value: int = 0
    target_value: int = 0
    days: list[DayItem] = []
    weekly_average: WeeklyAverage = WeeklyAverage()
