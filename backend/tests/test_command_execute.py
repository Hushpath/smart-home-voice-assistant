from app.models import CommandLog, Device, DeviceStatusHistory, Reminder
from app.services import home_actions


def execute_command(client, auth_headers, command):
    return client.post("/api/commands/execute", headers=auth_headers, json={"command": command})


def get_device_by_room_and_type(db, room_name, device_type):
    return (
        db.query(Device)
        .join(Device.room)
        .filter(Device.device_type == device_type, Device.room.has(name=room_name))
        .one()
    )


def test_execute_turn_on_living_room_light(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "打开客厅灯")

    assert response.status_code == 200
    result = response.json()["data"]["result"]
    assert result["before_state"]["is_on"] is False
    assert result["after_state"]["is_on"] is True

    db = testing_session_factory()
    try:
        device = get_device_by_room_and_type(db, "客厅", "light")
        assert device.is_on is True
        assert db.query(DeviceStatusHistory).filter(DeviceStatusHistory.device_id == device.id).count() == 1
        assert db.query(CommandLog).filter(CommandLog.raw_command == "打开客厅灯", CommandLog.success.is_(True)).count() == 1
    finally:
        db.close()


def test_execute_turn_off_bedroom_air_conditioner(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "关闭卧室空调")

    assert response.status_code == 200
    assert response.json()["data"]["result"]["after_state"]["is_on"] is False

    db = testing_session_factory()
    try:
        device = get_device_by_room_and_type(db, "卧室", "air_conditioner")
        assert device.is_on is False
        assert db.query(DeviceStatusHistory).filter(DeviceStatusHistory.device_id == device.id).count() == 1
    finally:
        db.close()


def test_execute_set_temperature(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "把卧室空调调到二十六度")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["result"]["after_state"]["properties"]["temperature"] == 26
    assert data["device_after"]["properties"]["temperature"] == 26

    db = testing_session_factory()
    try:
        device = get_device_by_room_and_type(db, "卧室", "air_conditioner")
        assert device.properties["temperature"] == 26
    finally:
        db.close()


def test_execute_set_brightness(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "将客厅灯亮度调到80")

    assert response.status_code == 200
    assert response.json()["data"]["result"]["after_state"]["properties"]["brightness"] == 80

    db = testing_session_factory()
    try:
        device = get_device_by_room_and_type(db, "客厅", "light")
        assert device.properties["brightness"] == 80
    finally:
        db.close()


def test_execute_set_volume(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "把电视音量调到30")

    assert response.status_code == 200
    assert response.json()["data"]["result"]["after_state"]["properties"]["volume"] == 30

    db = testing_session_factory()
    try:
        device = get_device_by_room_and_type(db, "客厅", "tv")
        assert device.properties["volume"] == 30
    finally:
        db.close()


def test_execute_sleep_scene(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "开启睡眠模式")

    assert response.status_code == 200
    result = response.json()["data"]["result"]
    assert result["scene"]["name"] == "睡眠模式"
    assert len(result["changes"]) == 3

    db = testing_session_factory()
    try:
        bedroom_ac = get_device_by_room_and_type(db, "卧室", "air_conditioner")
        assert bedroom_ac.is_on is True
        assert bedroom_ac.properties["mode"] == "睡眠"
        assert db.query(DeviceStatusHistory).count() == 3
    finally:
        db.close()


def test_execute_create_reminder(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "提醒我晚上八点吃药")

    assert response.status_code == 200
    reminder = response.json()["data"]["result"]["reminder"]
    assert reminder["title"] == "吃药"
    assert "T20:00:00" in reminder["remind_time"]

    db = testing_session_factory()
    try:
        stored = db.query(Reminder).one()
        assert stored.title == "吃药"
    finally:
        db.close()


def test_execute_query_weather(client, auth_headers):
    response = execute_command(client, auth_headers, "查询北京天气")

    assert response.status_code == 200
    weather = response.json()["data"]["result"]["weather"]
    assert weather["city"] == "北京"
    assert weather["weather"] == "晴"
    assert weather["source"] == "mock"


def test_command_logs_api(client, auth_headers):
    execute_command(client, auth_headers, "打开客厅灯")

    response = client.get("/api/commands/logs", headers=auth_headers)

    assert response.status_code == 200
    logs = response.json()["data"]
    assert logs[0]["raw_command"] == "打开客厅灯"
    assert logs[0]["success"] is True
    assert logs[0]["parsed_result"]["confidence"] >= 0.6
    assert "intent_scores" in logs[0]["parsed_result"]["parse_detail"]


def test_device_history_after_command(client, auth_headers):
    execute_command(client, auth_headers, "打开客厅灯")

    response = client.get("/api/devices/1/history", headers=auth_headers)

    assert response.status_code == 200
    history = response.json()["data"]
    assert len(history) == 1
    assert history[0]["change_source"] == "command"


def test_temperature_out_of_range_writes_failed_log(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "把卧室空调调到40度")

    assert response.status_code == 400
    assert response.json()["code"] == "VALUE_OUT_OF_RANGE"

    db = testing_session_factory()
    try:
        log = db.query(CommandLog).one()
        assert log.success is False
        assert log.error_message == "温度必须在 16-30 范围内"
    finally:
        db.close()


def test_execute_missing_device(client, auth_headers):
    response = execute_command(client, auth_headers, "打开客厅排风扇")

    assert response.status_code == 404
    assert response.json()["code"] == "DEVICE_NOT_FOUND"


def test_execute_fuzzy_light_typo(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "打开客厅等")

    assert response.status_code == 200
    parsed = response.json()["data"]["parsed"]
    assert parsed["device_type"] == "light"
    assert parsed["match_type"] == "fuzzy"

    db = testing_session_factory()
    try:
        device = get_device_by_room_and_type(db, "客厅", "light")
        assert device.is_on is True
    finally:
        db.close()


def test_execute_air_conditioner_alias(client, auth_headers):
    response = execute_command(client, auth_headers, "卧室冷气调到二十六度")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["parsed"]["device_type"] == "air_conditioner"
    assert data["result"]["after_state"]["properties"]["temperature"] == 26


def test_execute_low_confidence_command(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "帮我处理一下")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_COMMAND"

    db = testing_session_factory()
    try:
        log = db.query(CommandLog).one()
        assert log.success is False
        assert log.parsed_result["confidence"] < 0.6
    finally:
        db.close()


def test_execute_unsupported_action(client, auth_headers):
    response = execute_command(client, auth_headers, "把电视亮度调到80")

    assert response.status_code == 400
    assert response.json()["code"] == "UNSUPPORTED_ACTION"


def test_execute_requires_login(client):
    response = client.post("/api/commands/execute", json={"command": "打开客厅灯"})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_reminder_crud_api(client, auth_headers):
    create_response = client.post(
        "/api/reminders",
        headers=auth_headers,
        json={"title": "喝水", "remind_time": "2026-06-12T20:00:00"},
    )
    reminder_id = create_response.json()["data"]["id"]

    list_response = client.get("/api/reminders", headers=auth_headers)
    update_response = client.patch(
        f"/api/reminders/{reminder_id}",
        headers=auth_headers,
        json={"is_done": True},
    )
    delete_response = client.delete(f"/api/reminders/{reminder_id}", headers=auth_headers)

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1
    assert update_response.status_code == 200
    assert update_response.json()["data"]["is_done"] is True
    assert delete_response.status_code == 200


def test_weather_api_without_login(client):
    response = client.get("/api/weather?city=北京")

    assert response.status_code == 200
    assert response.json()["data"]["city"] == "北京"
    assert response.json()["data"]["source"] == "mock"


def test_weather_api_uses_open_meteo_when_available(client, monkeypatch):
    def fake_weather(city_name):
        return {
            "city": city_name,
            "weather": "多云",
            "temperature": 22.5,
            "humidity": 63,
            "wind_speed": 5.4,
            "advice": "天气较适宜，可根据室内状态通风或调节设备。",
            "source": "open_meteo",
            "updated_at": "2026-06-13T10:00",
        }

    monkeypatch.setattr(home_actions, "_fetch_open_meteo_weather", fake_weather)
    home_actions.clear_weather_cache()

    response = client.get("/api/weather?city=深圳")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["city"] == "深圳"
    assert data["source"] == "open_meteo"
    assert data["wind_speed"] == 5.4
    assert data["updated_at"] == "2026-06-13T10:00"


def test_weather_api_falls_back_to_mock_when_open_meteo_fails(client, monkeypatch):
    def failed_weather(city_name):
        raise ValueError(f"weather unavailable: {city_name}")

    monkeypatch.setattr(home_actions, "_fetch_open_meteo_weather", failed_weather)
    home_actions.clear_weather_cache()

    response = client.get("/api/weather?city=杭州")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["city"] == "杭州"
    assert data["source"] == "mock"
    assert data["weather"] == "多云"


def test_weather_api_falls_back_for_unknown_city(client):
    response = client.get("/api/weather?city=未知城市")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["city"] == "未知城市"
    assert data["source"] == "mock"


def test_scene_api_list_and_run(client, auth_headers, testing_session_factory):
    list_response = client.get("/api/scenes", headers=auth_headers)
    sleep_scene = next(scene for scene in list_response.json()["data"] if scene["name"] == "睡眠模式")
    run_response = client.post(f"/api/scenes/{sleep_scene['id']}/run", headers=auth_headers)

    assert list_response.status_code == 200
    assert run_response.status_code == 200
    assert run_response.json()["data"]["scene"]["name"] == "睡眠模式"

    db = testing_session_factory()
    try:
        assert db.query(DeviceStatusHistory).count() == 3
    finally:
        db.close()


def test_missing_room(client, auth_headers):
    response = execute_command(client, auth_headers, "打开阳台灯")

    assert response.status_code == 404
    assert response.json()["code"] == "ROOM_NOT_FOUND"
