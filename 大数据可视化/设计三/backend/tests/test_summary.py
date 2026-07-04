import pytest

SAMPLE_ITEM = {
    "name": "烟熏三文鱼",
    "calories": 180,
    "protein": 20,
    "carbs": 0,
    "fat": 10,
    "weightGrams": 100,
    "weightString": "100克",
}

SAMPLE_MEAL = {
    "title": "晚餐-三文鱼",
    "mealType": "dinner",
    "mealDate": "2026-06-01",
    "timeString": "18:30",
    "notes": "mock 保存",
    "multiplier": 1.0,
    "isCollected": False,
    "source": "mock_image",
    "items": [SAMPLE_ITEM],
}

SUMMARY_URL = "/api/v1/summary/day"


class TestDaySummary:

    def test_empty_day(self, client):
        """No meals on the date should return zeros."""
        resp = client.get(SUMMARY_URL, params={"date": "2026-06-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-06-01"
        assert data["dateString"] == "6月1日"
        assert data["calories"] == 0
        assert data["protein"] == 0
        assert data["carbs"] == 0
        assert data["fat"] == 0
        assert data["mealCount"] == 0
        # Targets should be present (from seeded test user profile)
        assert data["targetCalories"] > 0
        assert data["proteinTarget"] > 0
        assert data["remainingCalories"] == data["targetCalories"]

    def test_with_meals(self, client):
        """After creating meals, summary reflects consumed totals."""
        resp = client.post("/api/v1/meals", json=SAMPLE_MEAL)
        assert resp.status_code == 201

        resp2 = client.post(
            "/api/v1/meals",
            json={
                **SAMPLE_MEAL,
                "title": "午餐",
                "mealType": "lunch",
                "items": [
                    {
                        "name": "鸡胸肉",
                        "calories": 300,
                        "protein": 50,
                        "carbs": 10,
                        "fat": 5,
                        "weightGrams": 200,
                        "weightString": "200克",
                    }
                ],
            },
        )
        assert resp2.status_code == 201

        resp3 = client.get(SUMMARY_URL, params={"date": "2026-06-01"})
        assert resp3.status_code == 200
        data = resp3.json()
        assert data["calories"] == 480  # 180 + 300
        assert data["protein"] == 70  # 20 + 50
        assert data["carbs"] == 10  # 0 + 10
        assert data["fat"] == 15  # 10 + 5
        assert data["mealCount"] == 2
        assert data["remainingCalories"] == data["targetCalories"] - 480

    def test_other_date_not_affected(self, client):
        """Meals on one date should not affect another date's summary."""
        client.post("/api/v1/meals", json=SAMPLE_MEAL)  # 2026-06-01

        resp = client.get(SUMMARY_URL, params={"date": "2026-06-02"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["calories"] == 0
        assert data["mealCount"] == 0

    def test_invalid_date(self, client):
        resp = client.get(SUMMARY_URL, params={"date": "invalid"})
        assert resp.status_code == 422

    def test_missing_date_param(self, client):
        resp = client.get(SUMMARY_URL)
        assert resp.status_code == 422

    def test_remaining_calories_negative(self, client):
        """Exceeding target should yield negative remaining."""
        big_meal = {
            **SAMPLE_MEAL,
            "items": [
                {
                    "name": "超大汉堡",
                    "calories": 5000,
                    "protein": 200,
                    "carbs": 300,
                    "fat": 200,
                    "weightGrams": 1000,
                    "weightString": "1000克",
                }
            ],
        }
        client.post("/api/v1/meals", json=big_meal)
        resp = client.get(SUMMARY_URL, params={"date": "2026-06-01"})
        data = resp.json()
        assert data["remainingCalories"] < 0

    def test_summary_changes_after_deleting_meal(self, client):
        resp = client.post("/api/v1/meals", json=SAMPLE_MEAL)
        meal_id = resp.json()["id"]

        # After creation
        resp2 = client.get(SUMMARY_URL, params={"date": "2026-06-01"})
        assert resp2.json()["calories"] == 180

        # After deletion
        client.delete(f"/api/v1/meals/{meal_id}")
        resp3 = client.get(SUMMARY_URL, params={"date": "2026-06-01"})
        assert resp3.json()["calories"] == 0
