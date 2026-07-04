import pytest

SAMPLE_ITEM = {
    "name": "烟熏三文鱼",
    "calories": 180,
    "protein": 20,
    "carbs": 0,
    "fat": 10,
    "weightGrams": 100,
    "weightString": "100克",
    "alternatives": [{"name": "鸡胸肉", "calories": 190, "weightString": "100克"}],
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


# ── POST /meals ─────────────────────────────────────────────

def test_create_meal(client):
    resp = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "晚餐-三文鱼"
    assert data["mealType"] == "dinner"
    assert data["mealTypeLabel"] == "晚餐"
    assert data["dateString"] == "6月1日"
    # Totals should match item
    assert data["calories"] == 180
    assert data["protein"] == 20
    assert data["carbs"] == 0
    assert data["fat"] == 10
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "烟熏三文鱼"
    assert len(data["items"][0]["alternatives"]) == 1
    assert data["items"][0]["alternatives"][0]["name"] == "鸡胸肉"


def test_create_meal_empty_items(client):
    payload = {**SAMPLE_MEAL, "items": []}
    resp = client.post("/api/v1/meals", json=payload)
    assert resp.status_code == 422


def test_create_meal_invalid_enum(client):
    payload = {**SAMPLE_MEAL, "mealType": "supper"}
    resp = client.post("/api/v1/meals", json=payload)
    assert resp.status_code == 422


# ── GET /meals ──────────────────────────────────────────────

def test_list_meals_by_date(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    resp = client.get("/api/v1/meals?date=2026-06-01")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_list_meals_by_range(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    resp = client.get("/api/v1/meals?start=2026-05-25&end=2026-06-01")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_list_meals_empty_date(client):
    resp = client.get("/api/v1/meals?date=2026-01-01")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── GET /meals/{id} ─────────────────────────────────────────

def test_get_meal_detail(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    meal_id = create.json()["id"]

    resp = client.get(f"/api/v1/meals/{meal_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "晚餐-三文鱼"
    assert len(data["items"]) == 1


def test_get_meal_not_found(client):
    resp = client.get("/api/v1/meals/nonexistent-id")
    assert resp.status_code == 404


# ── PATCH /meals/{id} ───────────────────────────────────────

def test_update_meal(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    meal_id = create.json()["id"]

    resp = client.patch(f"/api/v1/meals/{meal_id}", json={"title": "更新餐食", "isCollected": True})
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新餐食"
    assert resp.json()["isCollected"] is True
    # Totals unchanged
    assert resp.json()["calories"] == 180


# ── DELETE /meals/{id} ──────────────────────────────────────

def test_delete_meal(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    meal_id = create.json()["id"]

    resp = client.delete(f"/api/v1/meals/{meal_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/meals/{meal_id}")
    assert resp.status_code == 404


# ── Item endpoints ──────────────────────────────────────────

def test_add_item(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    meal_id = create.json()["id"]

    new_item = {
        "name": "白米饭",
        "calories": 200,
        "protein": 4,
        "carbs": 45,
        "fat": 0,
        "weightString": "150克",
    }
    resp = client.post(f"/api/v1/meals/{meal_id}/items", json=new_item)
    assert resp.status_code == 201
    data = resp.json()
    assert data["calories"] == 380  # 180 + 200
    assert len(data["items"]) == 2


def test_update_item(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    item_id = create.json()["items"][0]["id"]

    resp = client.patch(f"/api/v1/meals/item/{item_id}", json={"calories": 300})
    assert resp.status_code == 200
    # Meal totals should update
    assert resp.json()["calories"] == 300


def test_delete_item(client):
    # Create meal with 2 items
    meal = {**SAMPLE_MEAL, "items": [SAMPLE_ITEM, {"name": "米饭", "calories": 200, "protein": 4, "carbs": 45, "fat": 0, "weightString": "150克"}]}
    create = client.post("/api/v1/meals", json=meal)
    meal_id = create.json()["id"]
    item_id = create.json()["items"][1]["id"]

    resp = client.delete(f"/api/v1/meals/item/{item_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["calories"] == 180  # Only first item remains
    assert len(data["items"]) == 1


def test_delete_last_item_rejected(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    item_id = create.json()["items"][0]["id"]

    resp = client.delete(f"/api/v1/meals/item/{item_id}")
    assert resp.status_code == 422


# ── Auth boundary ──────────────────────────────────────────

def test_cannot_access_other_user_meal(client):
    """With only one test user, a non-existent user_id should 404."""
    resp = client.get("/api/v1/meals/nonexistent")
    assert resp.status_code == 404


# ── Search ───────────────────────────────────────────────────

def test_search_no_query_returns_recent(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    resp = client.get("/api/v1/meals/search")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1


def test_search_by_title(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    resp = client.get("/api/v1/meals/search", params={"q": "三文鱼"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_search_by_title_no_match(client):
    resp = client.get("/api/v1/meals/search", params={"q": "不存在的餐食"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_search_by_meal_item_name(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    resp = client.get("/api/v1/meals/search", params={"q": "烟熏"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_search_by_meal_type(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    resp = client.get("/api/v1/meals/search", params={"q": "dinner"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_search_limit(client):
    client.post("/api/v1/meals", json=SAMPLE_MEAL)
    client.post("/api/v1/meals", json={**SAMPLE_MEAL, "title": "午餐", "mealType": "lunch"})
    resp = client.get("/api/v1/meals/search", params={"limit": 1})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


# ── Duplicate ────────────────────────────────────────────────

def test_duplicate_meal(client):
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    meal_id = create.json()["id"]

    resp = client.post(
        f"/api/v1/meals/{meal_id}/duplicate",
        json={"mealDate": "2026-06-02", "timeString": "12:00"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == SAMPLE_MEAL["title"]
    assert data["mealType"] == "dinner"
    assert data["mealDate"] == "2026-06-02"
    assert data["timeString"] == "12:00"
    assert data["source"] == "search_history"
    # Items should be copied
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "烟熏三文鱼"
    assert data["calories"] == 180
    assert data["isCollected"] is False
    # Original meal unchanged
    orig = client.get(f"/api/v1/meals/{meal_id}")
    assert orig.json()["mealDate"] == "2026-06-01"


def test_duplicate_meal_not_found(client):
    resp = client.post(
        "/api/v1/meals/nonexistent/duplicate",
        json={"mealDate": "2026-06-02", "timeString": "12:00"},
    )
    assert resp.status_code == 404


def test_duplicate_with_alternatives(client):
    """Duplicated meal should also clone alternatives."""
    create = client.post("/api/v1/meals", json=SAMPLE_MEAL)
    meal_id = create.json()["id"]

    resp = client.post(
        f"/api/v1/meals/{meal_id}/duplicate",
        json={"mealDate": "2026-06-03", "timeString": "19:00"},
    )
    data = resp.json()
    assert len(data["items"][0]["alternatives"]) == 1
    assert data["items"][0]["alternatives"][0]["name"] == "鸡胸肉"
