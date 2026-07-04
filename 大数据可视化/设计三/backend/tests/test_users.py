def test_get_users_me(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["displayName"] == "王志豪"
    assert data["isTestUser"] is True
    assert "id" in data


def test_get_user_profile(client):
    response = client.get("/api/v1/users/me/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "王志豪"
    assert data["gender"] == "male"
    assert data["age"] == 22
    assert data["heightCm"] == 175.0
    assert data["weightKg"] == 70.0
    assert data["activityLevel"] == "moderate"
    assert data["healthGoal"] == "fat_loss"


def test_update_user_profile(client):
    response = client.put(
        "/api/v1/users/me/profile",
        json={
            "nickname": "测试用户",
            "gender": "female",
            "age": 25,
            "heightCm": 160,
            "weightKg": 55,
            "bodyFatRate": 22,
            "activityLevel": "light",
            "healthGoal": "maintain",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "测试用户"
    assert data["gender"] == "female"
    assert data["age"] == 25
    assert data["heightCm"] == 160.0
    assert data["weightKg"] == 55.0
    assert data["bodyFatRate"] == 22.0
    assert data["activityLevel"] == "light"
    assert data["healthGoal"] == "maintain"

    # Verify persistence by reading again
    response = client.get("/api/v1/users/me/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "测试用户"
