import pytest

from app.models import Device, DeviceStatusHistory


def parse_command(client, auth_headers, command):
    return client.post("/api/commands/parse", headers=auth_headers, json={"command": command})


def assert_parse(response, expected):
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is True
    for key, value in expected.items():
        assert data[key] == value


def test_parse_turn_on_living_room_light(client, auth_headers):
    response = parse_command(client, auth_headers, "打开客厅灯")

    assert_parse(
        response,
        {"intent": "turn_on", "room": "客厅", "device_type": "light", "value": None},
    )


def test_parse_turn_off_bedroom_air_conditioner(client, auth_headers):
    response = parse_command(client, auth_headers, "关闭卧室空调")

    assert_parse(
        response,
        {"intent": "turn_off", "room": "卧室", "device_type": "air_conditioner"},
    )


def test_parse_set_temperature(client, auth_headers):
    response = parse_command(client, auth_headers, "把卧室空调调到26度")

    assert_parse(
        response,
        {"intent": "set_temperature", "room": "卧室", "device_type": "air_conditioner", "value": 26},
    )


def test_parse_set_brightness(client, auth_headers):
    response = parse_command(client, auth_headers, "将客厅灯亮度调到80")

    assert_parse(
        response,
        {"intent": "set_brightness", "room": "客厅", "device_type": "light", "value": 80},
    )


def test_parse_set_volume(client, auth_headers):
    response = parse_command(client, auth_headers, "把电视音量调到30")

    assert_parse(
        response,
        {"intent": "set_volume", "room": None, "device_type": "tv", "value": 30},
    )


def test_parse_query_status(client, auth_headers):
    response = parse_command(client, auth_headers, "查看客厅设备状态")

    assert_parse(
        response,
        {"intent": "query_status", "room": "客厅", "device_type": None},
    )


def test_parse_run_scene(client, auth_headers):
    response = parse_command(client, auth_headers, "开启睡眠模式")

    assert_parse(response, {"intent": "run_scene", "scene": "睡眠模式"})


def test_parse_create_reminder_with_chinese_time(client, auth_headers):
    response = parse_command(client, auth_headers, "提醒我晚上八点吃药")

    assert_parse(
        response,
        {
            "intent": "create_reminder",
            "reminder_time": "20:00",
            "reminder_content": "吃药",
        },
    )


def test_parse_query_weather_with_city(client, auth_headers):
    response = parse_command(client, auth_headers, "查询北京天气")

    assert_parse(response, {"intent": "query_weather", "city": "北京"})


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("开一下客厅灯", {"intent": "turn_on", "room": "客厅", "device_type": "light"}),
        ("关掉卧室空调", {"intent": "turn_off", "room": "卧室", "device_type": "air_conditioner"}),
        ("空调设置为26度", {"intent": "set_temperature", "room": None, "device_type": "air_conditioner", "value": 26}),
        ("客厅灯调到80亮度", {"intent": "set_brightness", "room": "客厅", "device_type": "light", "value": 80}),
        ("查询卧室设备状态", {"intent": "query_status", "room": "卧室", "device_type": None}),
        ("开启回家模式", {"intent": "run_scene", "scene": "回家模式"}),
        ("开启离家模式", {"intent": "run_scene", "scene": "离家模式"}),
        ("提醒我20:00吃药", {"intent": "create_reminder", "reminder_time": "20:00", "reminder_content": "吃药"}),
        ("查询今天的天气", {"intent": "query_weather", "city": None}),
    ],
)
def test_parse_required_variants(client, auth_headers, command, expected):
    response = parse_command(client, auth_headers, command)

    assert_parse(response, expected)


def test_parse_empty_command(client, auth_headers):
    response = parse_command(client, auth_headers, "")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "INVALID_COMMAND"
    assert body["data"]["valid"] is False
    assert body["data"]["message"] == "指令不能为空"


def test_parse_invalid_command(client, auth_headers):
    response = parse_command(client, auth_headers, "随便说一句")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "INVALID_COMMAND"
    assert body["data"]["valid"] is False


def test_parse_requires_login(client):
    response = client.post("/api/commands/parse", json={"command": "打开客厅灯"})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_parse_does_not_change_device_state(client, auth_headers, testing_session_factory):
    response = parse_command(client, auth_headers, "打开客厅灯")

    assert response.status_code == 200
    db = testing_session_factory()
    try:
        device = db.query(Device).filter(Device.id == 1).one()
        history_count = db.query(DeviceStatusHistory).count()
        assert device.is_on is False
        assert history_count == 0
    finally:
        db.close()
