import pytest
from app.services.nutrition import (
    calculate_bmr,
    calculate_tdee,
    adjust_calories_for_goal,
    calculate_protein,
    calculate_fat,
    calculate_carbs,
    calculate_targets,
    VALID_GENDERS,
    VALID_ACTIVITY_LEVELS,
    VALID_HEALTH_GOALS,
)


# ── BMR tests ──────────────────────────────────────────────

def test_bmr_male():
    # 10*70 + 6.25*175 - 5*22 + 5 = 1688.75 → 1689
    assert calculate_bmr("male", 70, 175, 22) == 1689


def test_bmr_female():
    # 10*55 + 6.25*160 - 5*25 - 161 = 550 + 1000 - 125 - 161 = 1264
    assert calculate_bmr("female", 55, 160, 25) == 1264


def test_bmr_other():
    # 10*80 + 6.25*180 - 5*30 - 78 = 800 + 1125 - 150 - 78 = 1697
    assert calculate_bmr("other", 80, 180, 30) == 1697


def test_bmr_invalid_gender():
    with pytest.raises(ValueError, match="Invalid gender"):
        calculate_bmr("unknown", 70, 175, 22)


# ── TDEE tests ─────────────────────────────────────────────

@pytest.mark.parametrize("level,factor", [
    ("sedentary", 1.2),
    ("light", 1.375),
    ("moderate", 1.55),
    ("active", 1.725),
    ("very_active", 1.9),
])
def test_tdee_all_levels(level, factor):
    bmr = 2000
    expected = round(2000 * factor)
    assert calculate_tdee(bmr, level) == expected


def test_tdee_invalid_level():
    with pytest.raises(ValueError, match="Invalid activity_level"):
        calculate_tdee(2000, "extreme")


# ── Target calories tests ──────────────────────────────────

@pytest.mark.parametrize("goal,multiplier", [
    ("fat_loss", 0.85),
    ("maintain", 1.0),
    ("muscle_gain", 1.1),
])
def test_target_calories_all_goals(goal, multiplier):
    tdee = 2500
    expected = round(2500 * multiplier)
    assert adjust_calories_for_goal(tdee, goal) == expected


def test_target_calories_invalid_goal():
    with pytest.raises(ValueError, match="Invalid health_goal"):
        adjust_calories_for_goal(2500, "bulk")


# ── Macronutrient tests ────────────────────────────────────

@pytest.mark.parametrize("goal,factor", [
    ("fat_loss", 1.8),
    ("maintain", 1.6),
    ("muscle_gain", 2.0),
])
def test_protein_all_goals(goal, factor):
    assert calculate_protein(goal, 70) == round(factor * 70)


def test_fat_calculation():
    # 2000 * 0.25 / 9 = 55.55... → 56
    assert calculate_fat(2000) == 56


def test_carbs_calculation():
    # 2000 cal, protein=100g, fat=56g
    # (2000 - 100*4 - 56*9) / 4 = (2000 - 400 - 504) / 4 = 274
    assert calculate_carbs(2000, 100, 56) == 274


def test_carbs_non_negative():
    # Extreme low-cal scenario: protein and fat exceed target
    carbs = calculate_carbs(500, 100, 50)
    assert carbs >= 0


# ── Integration: calculate_targets ─────────────────────────

class FakeProfile:
    """Minimal stand-in for UserProfile ORM object."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_calculate_targets_default_profile():
    profile = FakeProfile(
        gender="male",
        age=22,
        height_cm=175.0,
        weight_kg=70.0,
        activity_level="moderate",
        health_goal="fat_loss",
    )
    result = calculate_targets(profile)
    assert result["bmr"] == 1689
    assert result["tdee"] == 2618
    assert result["target_calories"] == 2225
    assert result["protein"] == 126
    assert result["fat"] == 62
    assert result["carbs"] >= 0
    # Verify all fields present
    for key in ("bmr", "tdee", "target_calories", "protein", "carbs", "fat"):
        assert key in result
        assert isinstance(result[key], int)


# ── API integration test ───────────────────────────────────

def test_get_targets_endpoint(client):
    response = client.get("/api/v1/users/me/targets")
    assert response.status_code == 200
    data = response.json()
    assert data["bmr"] == 1689
    assert data["tdee"] == 2618
    assert data["targetCalories"] == 2225
    assert data["protein"] == 126
    assert data["fat"] == 62
    assert data["carbs"] >= 0
    # Verify camelCase field names
    assert "targetCalories" in data
    assert "bmr" in data
