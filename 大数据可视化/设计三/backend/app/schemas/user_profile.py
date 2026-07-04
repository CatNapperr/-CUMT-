from app.schemas.common import CamelCaseModel


class UserProfileOut(CamelCaseModel):
    nickname: str
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    body_fat_rate: float | None = None
    activity_level: str
    health_goal: str


class UserProfileUpdate(CamelCaseModel):
    nickname: str
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    body_fat_rate: float | None = None
    activity_level: str
    health_goal: str
