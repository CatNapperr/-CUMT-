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
    "title": "晚餐",
    "mealType": "dinner",
    "mealDate": "2026-05-25",
    "timeString": "18:30",
    "notes": "",
    "multiplier": 1.0,
    "isCollected": False,
    "source": "mock_image",
    "items": [SAMPLE_ITEM],
}

WEEK_URL = "/api/v1/analytics/week"
WEEK_START = "2026-05-25"
WEEK_END = "2026-05-31"  # Monday to Sunday


class TestWeekAnalytics:

    def _create_meal(self, client, date_str: str, calories: int = 180,
                     protein: int = 20, carbs: int = 0, fat: int = 10):
        item = {**SAMPLE_ITEM, "calories": calories, "protein": protein,
                "carbs": carbs, "fat": fat}
        payload = {**SAMPLE_MEAL, "mealDate": date_str, "items": [item]}
        return client.post("/api/v1/meals", json=payload)

    def test_empty_week(self, client):
        """No meals in the week should return zeros."""
        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        assert resp.status_code == 200
        data = resp.json()
        assert data["recordedDays"] == 0
        assert data["averageValue"] == 0
        assert data["targetValue"] > 0  # still has target from profile
        assert len(data["days"]) == 7
        for day in data["days"]:
            assert day["calories"] == 0
            assert day["metricValue"] == 0

    def test_with_meals(self, client):
        """Meals on some days should be reflected."""
        self._create_meal(client, "2026-05-25", calories=500, protein=30, carbs=40, fat=20)
        self._create_meal(client, "2026-05-27", calories=300, protein=20, carbs=10, fat=15)

        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        assert resp.status_code == 200
        data = resp.json()
        assert data["recordedDays"] == 2
        # averageValue = (500 + 300) / 2 = 400
        assert data["averageValue"] == 400
        assert data["days"][0]["date"] == "2026-05-25"
        assert data["days"][0]["calories"] == 500
        assert data["days"][0]["metricValue"] == 500
        assert data["days"][2]["date"] == "2026-05-27"
        assert data["days"][2]["calories"] == 300
        assert data["days"][1]["calories"] == 0  # 2026-05-26 no meals

    def test_metric_protein(self, client):
        self._create_meal(client, "2026-05-25", calories=500, protein=30, carbs=40, fat=20)
        self._create_meal(client, "2026-05-26", calories=200, protein=10, carbs=5, fat=8)

        resp = client.get(WEEK_URL, params={
            "start": WEEK_START, "end": WEEK_END, "metric": "protein",
        })
        data = resp.json()
        assert data["metric"] == "protein"
        assert data["metricLabel"] == "蛋白质"
        assert data["metricUnit"] == "克"
        # averageValue = (30 + 10) / 2 = 20
        assert data["averageValue"] == 20
        # targetValue should match protein target from profile
        assert data["targetValue"] > 0
        # metricValue should be protein per day
        assert data["days"][0]["metricValue"] == 30
        assert data["days"][1]["metricValue"] == 10
        assert data["days"][2]["metricValue"] == 0

    def test_metric_carbs(self, client):
        self._create_meal(client, "2026-05-25", calories=500, protein=30, carbs=40, fat=20)

        resp = client.get(WEEK_URL, params={
            "start": WEEK_START, "end": WEEK_END, "metric": "carbs",
        })
        data = resp.json()
        assert data["metric"] == "carbs"
        assert data["metricLabel"] == "碳水"
        assert data["days"][0]["metricValue"] == 40

    def test_metric_fat(self, client):
        self._create_meal(client, "2026-05-25", calories=500, protein=30, carbs=40, fat=20)

        resp = client.get(WEEK_URL, params={
            "start": WEEK_START, "end": WEEK_END, "metric": "fat",
        })
        data = resp.json()
        assert data["metric"] == "fat"
        assert data["metricLabel"] == "脂肪"
        assert data["days"][0]["metricValue"] == 20

    def test_invalid_date_range(self, client):
        """Less or more than 7 days should be rejected."""
        resp = client.get(WEEK_URL, params={
            "start": "2026-05-25", "end": "2026-05-28",  # only 4 days
        })
        assert resp.status_code == 422

    def test_invalid_metric(self, client):
        resp = client.get(WEEK_URL, params={
            "start": WEEK_START, "end": WEEK_END, "metric": "invalid",
        })
        assert resp.status_code == 422

    def test_day_labels(self, client):
        """Day labels should have Chinese weekday and date format."""
        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        data = resp.json()
        assert len(data["days"]) == 7
        # 2026-05-25 is a Monday
        assert data["days"][0]["dayLabel"] == "周一\n5/25"
        assert data["days"][1]["dayLabel"] == "周二\n5/26"
        assert data["days"][2]["dayLabel"] == "周三\n5/27"
        assert data["days"][3]["dayLabel"] == "周四\n5/28"
        assert data["days"][4]["dayLabel"] == "周五\n5/29"
        assert data["days"][5]["dayLabel"] == "周六\n5/30"
        assert data["days"][6]["dayLabel"] == "周日\n5/31"

    def test_date_range_label(self, client):
        """Date range label should be properly formatted."""
        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        data = resp.json()
        assert data["dateRangeLabel"] == "2026年5月25日 - 2026年5月31日"

    def test_daily_percentages(self, client):
        """Daily macro percentages should be computed."""
        self._create_meal(client, "2026-05-25", calories=500, protein=30, carbs=40, fat=20)
        # total = 20 + 40 + 30 = 90
        # fat% = 20/90*100 = 22, carbs% = 40/90*100 = 44, protein% = 30/90*100 = 33
        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        data = resp.json()
        day0 = data["days"][0]
        assert day0["fatPercent"] == 22
        assert day0["carbsPercent"] == 44
        assert day0["proteinPercent"] == 33

    def test_zero_percentages(self, client):
        """Zero macros on empty days should have 0% for all."""
        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        day0 = resp.json()["days"][0]
        assert day0["fatPercent"] == 0
        assert day0["carbsPercent"] == 0
        assert day0["proteinPercent"] == 0

    def test_weekly_average_percentages(self, client):
        """Weekly average macro percentages over the full week."""
        self._create_meal(client, "2026-05-25", calories=500, protein=30, carbs=40, fat=20)
        # total = 20+40+30 = 90
        resp = client.get(WEEK_URL, params={"start": WEEK_START, "end": WEEK_END})
        wa = resp.json()["weeklyAverage"]
        assert wa["fatPercent"] == 22
        assert wa["carbsPercent"] == 44
        assert wa["proteinPercent"] == 33
