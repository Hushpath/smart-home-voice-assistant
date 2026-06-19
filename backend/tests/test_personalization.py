from app.models import CommandLog, Device


def execute_command(client, auth_headers, command):
    return client.post("/api/commands/execute", headers=auth_headers, json={"command": command})


def test_preferences_requires_login(client):
    response = client.get("/api/user/preferences")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_get_preferences_creates_defaults(client, auth_headers):
    response = client.get("/api/user/preferences", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["preferred_dialect"] == "auto"
    assert data["preferred_input_mode"] == "browser_speech"


def test_patch_preferences_updates_preferred_dialect(client, auth_headers):
    response = client.patch(
        "/api/user/preferences",
        headers=auth_headers,
        json={"preferred_dialect": "cantonese"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["preferred_dialect"] == "cantonese"


def test_patch_preferences_rejects_invalid_preferred_dialect(client, auth_headers):
    response = client.patch(
        "/api/user/preferences",
        headers=auth_headers,
        json={"preferred_dialect": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["code"] == "INVALID_REQUEST"


def test_create_device_alias(client, auth_headers):
    device_id = _device_id(client, auth_headers, "客厅", "light")

    response = client.post(
        "/api/user/device-aliases",
        headers=auth_headers,
        json={"device_id": device_id, "alias": "小灯"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["alias"] == "小灯"
    assert data["device_name"] == "灯"
    assert data["room_name"] == "客厅"


def test_duplicate_device_alias_is_rejected(client, auth_headers):
    device_id = _device_id(client, auth_headers, "客厅", "light")
    payload = {"device_id": device_id, "alias": "小灯"}
    first = client.post("/api/user/device-aliases", headers=auth_headers, json=payload)
    second = client.post("/api/user/device-aliases", headers=auth_headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["code"] == "DEVICE_ALIAS_EXISTS"


def test_delete_device_alias(client, auth_headers):
    device_id = _device_id(client, auth_headers, "客厅", "light")
    create_response = client.post(
        "/api/user/device-aliases",
        headers=auth_headers,
        json={"device_id": device_id, "alias": "小灯"},
    )
    alias_id = create_response.json()["data"]["id"]

    delete_response = client.delete(f"/api/user/device-aliases/{alias_id}", headers=auth_headers)
    list_response = client.get("/api/user/device-aliases", headers=auth_headers)

    assert delete_response.status_code == 200
    assert list_response.json()["data"] == []


def test_alias_command_opens_real_device_and_logs_match(client, auth_headers, testing_session_factory):
    device_id = _device_id(client, auth_headers, "客厅", "light")
    client.post(
        "/api/user/device-aliases",
        headers=auth_headers,
        json={"device_id": device_id, "alias": "小灯"},
    )

    response = execute_command(client, auth_headers, "打开小灯")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["alias_match"]["alias"] == "小灯"
    assert data["result"]["device"]["id"] == device_id
    db = testing_session_factory()
    try:
        device = db.get(Device, device_id)
        log = db.query(CommandLog).filter(CommandLog.raw_command == "打开小灯").one()
        assert device.is_on is True
        assert log.parsed_result["context"]["alias_match"]["alias"] == "小灯"
        assert log.execution_result["context"]["alias_match"]["device_id"] == device_id
    finally:
        db.close()


def test_preferred_cantonese_dialect_executes_cantonese_command(client, auth_headers):
    client.patch("/api/user/preferences", headers=auth_headers, json={"preferred_dialect": "cantonese"})

    response = execute_command(client, auth_headers, "将电视机声量调到三十")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["parsed"]["intent"] == "set_volume"
    assert data["parsed"]["value"] == 30
    assert data["preference_used"]["preferred_dialect"] == "cantonese"


def test_frequent_commands_returns_successful_commands(client, auth_headers):
    execute_command(client, auth_headers, "打开客厅灯")
    execute_command(client, auth_headers, "打开客厅灯")
    execute_command(client, auth_headers, "查询北京天气")

    response = client.get("/api/user/frequent-commands?limit=5", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data[0]["command"] == "打开客厅灯"
    assert data[0]["count"] == 2
    assert data[0]["last_success"] is True


def test_preference_suggestions_learn_cantonese_dialect(client, auth_headers):
    execute_command(client, auth_headers, "帮我打开客厅冷气")
    execute_command(client, auth_headers, "将电视机声量调到三十")
    execute_command(client, auth_headers, "开启瞓觉模式")

    response = client.get("/api/user/preference-suggestions", headers=auth_headers)

    assert response.status_code == 200
    dialect = response.json()["data"]["dialect"]
    assert dialect["suggested"] == "cantonese"
    assert dialect["can_apply"] is True
    assert dialect["apply_payload"] == {"preferred_dialect": "cantonese"}


def test_preference_suggestions_learn_text_input_mode(client, auth_headers):
    execute_command(client, auth_headers, "打开客厅灯")
    execute_command(client, auth_headers, "关闭客厅灯")
    execute_command(client, auth_headers, "查询北京天气")

    response = client.get("/api/user/preference-suggestions", headers=auth_headers)

    assert response.status_code == 200
    input_mode = response.json()["data"]["input_mode"]
    assert input_mode["suggested"] == "text"
    assert input_mode["can_apply"] is True
    assert input_mode["apply_payload"] == {"preferred_input_mode": "text"}


def test_standard_execute_still_works_with_personalization_fields(client, auth_headers):
    response = execute_command(client, auth_headers, "关闭卧室空调")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["parsed"]["intent"] == "turn_off"
    assert data["preference_used"]["preferred_dialect"] == "auto"


def _device_id(client, auth_headers, room_name, device_type):
    response = client.get("/api/devices", headers=auth_headers)
    devices = response.json()["data"]
    return next(device["id"] for device in devices if device["room_name"] == room_name and device["device_type"] == device_type)
