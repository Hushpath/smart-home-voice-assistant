def _register_and_login(client, username: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"username": username, "password": "pass123456", "nickname": username},
    )
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "pass123456"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _device_id(client, headers, room_name: str, device_type: str) -> int:
    response = client.get("/api/devices", headers=headers)
    devices = response.json()["data"]
    return next(
        device["id"]
        for device in devices
        if device["room_name"] == room_name and device["device_type"] == device_type
    )


def test_command_logs_are_isolated_between_users(client, auth_headers):
    other_headers = _register_and_login(client, "otherlogs")

    command_response = client.post(
        "/api/commands/execute",
        headers=auth_headers,
        json={"command": "打开客厅灯"},
    )
    default_logs_response = client.get("/api/commands/logs", headers=auth_headers)
    other_logs_response = client.get("/api/commands/logs", headers=other_headers)

    assert command_response.status_code == 200
    assert default_logs_response.status_code == 200
    assert [log["raw_command"] for log in default_logs_response.json()["data"]] == ["打开客厅灯"]
    assert other_logs_response.status_code == 200
    assert other_logs_response.json()["data"] == []


def test_reminders_are_isolated_between_users(client, auth_headers):
    other_headers = _register_and_login(client, "otherreminders")

    create_response = client.post(
        "/api/reminders",
        headers=auth_headers,
        json={"title": "喝水", "remind_time": "2026-06-20T20:00:00"},
    )
    default_list_response = client.get("/api/reminders", headers=auth_headers)
    other_list_response = client.get("/api/reminders", headers=other_headers)

    assert create_response.status_code == 200
    assert default_list_response.status_code == 200
    assert [item["title"] for item in default_list_response.json()["data"]] == ["喝水"]
    assert other_list_response.status_code == 200
    assert other_list_response.json()["data"] == []


def test_device_aliases_are_isolated_between_users(client, auth_headers):
    other_headers = _register_and_login(client, "otheraliases")
    device_id = _device_id(client, auth_headers, "客厅", "light")

    create_response = client.post(
        "/api/user/device-aliases",
        headers=auth_headers,
        json={"device_id": device_id, "alias": "小灯"},
    )
    default_aliases_response = client.get("/api/user/device-aliases", headers=auth_headers)
    other_aliases_response = client.get("/api/user/device-aliases", headers=other_headers)

    assert create_response.status_code == 200
    assert default_aliases_response.status_code == 200
    assert [item["alias"] for item in default_aliases_response.json()["data"]] == ["小灯"]
    assert other_aliases_response.status_code == 200
    assert other_aliases_response.json()["data"] == []
