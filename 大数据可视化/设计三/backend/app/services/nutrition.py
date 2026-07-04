from app.models.user_profile import UserProfile

GENDER_COEFFICIENTS = {
    "male": 5,
    "female": -161,
    "other": -78,
}

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

HEALTH_GOAL_CALORIES_FACTOR = {
    "fat_loss": 0.85,
    "maintain": 1.0,
    "muscle_gain": 1.1,
}

PROTEIN_FACTOR = {
    "fat_loss": 1.8,
    "maintain": 1.6,
    "muscle_gain": 2.0,
}

VALID_GENDERS = set(GENDER_COEFFICIENTS.keys())
VALID_ACTIVITY_LEVELS = set(ACTIVITY_FACTORS.keys())
VALID_HEALTH_GOALS = set(HEALTH_GOAL_CALORIES_FACTOR.keys())


def calculate_bmr(gender: str, weight_kg: float, height_cm: float, age: int) -> int:
    coeff = GENDER_COEFFICIENTS.get(gender)
    if coeff is None:
        raise ValueError(f"Invalid gender '{gender}'; must be one of {VALID_GENDERS}")
    return round(10 * weight_kg + 6.25 * height_cm - 5 * age + coeff)


def calculate_tdee(bmr: int, activity_level: str) -> int:
    factor = ACTIVITY_FACTORS.get(activity_level)
    if factor is None:
        raise ValueError(
            f"Invalid activity_level '{activity_level}'; "
            f"must be one of {VALID_ACTIVITY_LEVELS}"
        )
    return round(bmr * factor)


def adjust_calories_for_goal(tdee: int, health_goal: str) -> int:
    factor = HEALTH_GOAL_CALORIES_FACTOR.get(health_goal)
    if factor is None:
        raise ValueError(
            f"Invalid health_goal '{health_goal}'; "
            f"must be one of {VALID_HEALTH_GOALS}"
        )
    return round(tdee * factor)


def calculate_protein(health_goal: str, weight_kg: float) -> int:
    factor = PROTEIN_FACTOR.get(health_goal)
    if factor is None:
        raise ValueError(
            f"Invalid health_goal '{health_goal}'; "
            f"must be one of {VALID_HEALTH_GOALS}"
        )
    return round(factor * weight_kg)


def calculate_fat(target_calories: int) -> int:
    return round(target_calories * 0.25 / 9)


def calculate_carbs(target_calories: int, protein: int, fat: int) -> int:
    carbs = (target_calories - protein * 4 - fat * 9) / 4
    return max(0, round(carbs))


def calculate_targets(profile: UserProfile) -> dict:
    bmr = calculate_bmr(profile.gender, profile.weight_kg, profile.height_cm, profile.age)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_for_goal(tdee, profile.health_goal)
    protein = calculate_protein(profile.health_goal, profile.weight_kg)
    fat = calculate_fat(target_calories)
    carbs = calculate_carbs(target_calories, protein, fat)
    return {
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": target_calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }
