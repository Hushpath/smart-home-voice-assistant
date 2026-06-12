from app.core.security import verify_password
from app.models import Device, DeviceStatusHistory, User


def test_register_user(client, testing_session_factory):
    response = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "newpass123", "nickname": "新用户"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["username"] == "newuser"

    db = testing_session_factory()
    try:
        user = db.query(User).filter(User.username == "newuser").one()
        assert user.password_hash != "newpass123"
        assert verify_password("newpass123", user.password_hash)
    finally:
        db.close()


def test_login_returns_jwt_token(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "test123456"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["access_token"].count(".") == 2
    assert data["user"]["username"] == "testuser"


def test_get_current_user(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["username"] == "testuser"


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/rooms")

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "UNAUTHORIZED"


def test_validation_error_uses_unified_response(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "x", "password": "short"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "INVALID_REQUEST"
    assert isinstance(body["data"], list)


def test_unknown_path_uses_unified_response(client):
    response = client.get("/api/not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "NOT_FOUND"


def test_list_rooms(client, auth_headers):
    response = client.get("/api/rooms", headers=auth_headers)

    assert response.status_code == 200
    rooms = response.json()["data"]
    assert len(rooms) == 4
    assert {room["name"] for room in rooms} == {"客厅", "卧室", "厨房", "书房"}


def test_list_devices_and_filter_by_room(client, auth_headers):
    rooms = client.get("/api/rooms", headers=auth_headers).json()["data"]
    living_room_id = next(room["id"] for room in rooms if room["name"] == "客厅")

    all_response = client.get("/api/devices", headers=auth_headers)
    filtered_response = client.get(f"/api/devices?room_id={living_room_id}", headers=auth_headers)

    assert all_response.status_code == 200
    assert len(all_response.json()["data"]) == 11
    assert filtered_response.status_code == 200
    assert {device["room_name"] for device in filtered_response.json()["data"]} == {"客厅"}


def test_get_device_detail(client, auth_headers):
    response = client.get("/api/devices/1", headers=auth_headers)

    assert response.status_code == 200
    device = response.json()["data"]
    assert device["id"] == 1
    assert device["room_name"] == "客厅"


def test_update_device_state_persists_and_writes_history(client, auth_headers, testing_session_factory):
    response = client.patch(
        "/api/devices/1/state",
        headers=auth_headers,
        json={"is_on": True, "properties": {"brightness": 88}},
    )

    assert response.status_code == 200
    device = response.json()["data"]
    assert device["is_on"] is True
    assert device["properties"]["brightness"] == 88

    db = testing_session_factory()
    try:
        stored_device = db.query(Device).filter(Device.id == 1).one()
        history = db.query(DeviceStatusHistory).filter(DeviceStatusHistory.device_id == 1).all()
        assert stored_device.is_on is True
        assert stored_device.properties["brightness"] == 88
        assert len(history) == 1
        assert history[0].before_state["is_on"] is False
        assert history[0].after_state["is_on"] is True
    finally:
        db.close()


def test_get_device_history(client, auth_headers):
    client.patch(
        "/api/devices/1/state",
        headers=auth_headers,
        json={"is_on": True},
    )

    response = client.get("/api/devices/1/history", headers=auth_headers)

    assert response.status_code == 200
    history = response.json()["data"]
    assert len(history) == 1
    assert history[0]["device_id"] == 1
    assert history[0]["change_source"] == "manual"


def test_dashboard(client, auth_headers):
    response = client.get("/api/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["room_count"] == 4
    assert data["device_count"] == 11
    assert data["online_device_count"] == 11
    assert data["on_device_count"] == 0
