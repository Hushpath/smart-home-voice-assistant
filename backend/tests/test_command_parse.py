import pytest

from app.models import Device, DeviceStatusHistory


def parse_command(client, auth_headers, command):
    return client.post("/api/commands/parse", headers=auth_headers, json={"command": command})


def assert_parse(response, expected):
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is True
    assert "confidence" in data
    assert data["confidence"] >= 0.6
    assert "normalized_text" in data
    assert "parse_detail" in data
    breakdown = data["parse_detail"]["confidence_breakdown"]
    assert breakdown["final_confidence"] == data["confidence"]
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


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("把客厅灯色温设置为冷白", {"intent": "set_property", "room": "客厅", "device_type": "light", "property_name": "color_temperature", "property_value": "冷白"}),
        ("把书房台灯色温设置为暖黄", {"intent": "set_property", "room": "书房", "device_type": "desk_lamp", "property_name": "color_temperature", "property_value": "暖黄"}),
        ("把卧室床头灯色温设置为自然光", {"intent": "set_property", "room": "卧室", "device_type": "bedside_lamp", "property_name": "color_temperature", "property_value": "自然光"}),
        ("把客厅空调模式设置为制热", {"intent": "set_property", "room": "客厅", "device_type": "air_conditioner", "property_name": "mode", "property_value": "制热"}),
        ("把客厅空调风量设置为高速", {"intent": "set_property", "room": "客厅", "device_type": "air_conditioner", "property_name": "fan_speed", "property_value": "高速"}),
        ("把客厅电视频道设置为CCTV5", {"intent": "set_property", "room": "客厅", "device_type": "tv", "property_name": "channel", "property_value": "CCTV-5"}),
        ("把客厅窗帘开合比例调整为五十", {"intent": "set_property", "room": "客厅", "device_type": "curtain", "property_name": "open_percent", "property_value": 50, "value": 50}),
        ("把厨房排风扇风速设置为高速", {"intent": "set_property", "room": "厨房", "device_type": "fan", "property_name": "speed", "property_value": "高速"}),
        ("把客厅音箱模式设置为播放", {"intent": "set_property", "room": "客厅", "device_type": "speaker", "property_name": "mode", "property_value": "播放"}),
        ("把卧室加湿器湿度设置为60", {"intent": "set_property", "room": "卧室", "device_type": "humidifier", "property_name": "humidity_target", "property_value": 60, "value": 60}),
        ("把卧室加湿器模式设置为睡眠", {"intent": "set_property", "room": "卧室", "device_type": "humidifier", "property_name": "mode", "property_value": "睡眠"}),
        ("把书房空气净化器模式设置为强力", {"intent": "set_property", "room": "书房", "device_type": "air_purifier", "property_name": "mode", "property_value": "强力"}),
        ("把书房智能插座功率设置为1200瓦", {"intent": "set_property", "room": "书房", "device_type": "smart_plug", "property_name": "power_watt", "property_value": 1200, "value": 1200}),
        ("把厨房冰箱温度设置为5度", {"intent": "set_property", "room": "厨房", "device_type": "fridge", "property_name": "temperature", "property_value": 5, "value": 5}),
        ("把厨房冰箱模式设置为速冷", {"intent": "set_property", "room": "厨房", "device_type": "fridge", "property_name": "mode", "property_value": "速冷"}),
    ],
)
def test_parse_device_property_capabilities(client, auth_headers, command, expected):
    response = parse_command(client, auth_headers, command)

    assert_parse(response, expected)


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
    assert body["data"]["confidence"] < 0.6


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("开一下客厅电灯", {"intent": "turn_on", "room": "客厅", "device_type": "light"}),
        ("帮我打开客厅灯", {"intent": "turn_on", "room": "客厅", "device_type": "light"}),
        ("客厅灯开一下", {"intent": "turn_on", "room": "客厅", "device_type": "light"}),
        ("帮我把卧室空调调到二十六度", {"intent": "set_temperature", "room": "卧室", "device_type": "air_conditioner", "value": 26}),
        ("将客厅灯亮度调到八十", {"intent": "set_brightness", "room": "客厅", "device_type": "light", "value": 80}),
        ("把电视机音量调到三十", {"intent": "set_volume", "room": None, "device_type": "tv", "value": 30}),
        ("打开书房台灯", {"intent": "turn_on", "room": "书房", "device_type": "desk_lamp"}),
        ("把书房台灯亮度调到七十", {"intent": "set_brightness", "room": "书房", "device_type": "desk_lamp", "value": 70}),
        ("把客厅音箱音量调到四十", {"intent": "set_volume", "room": "客厅", "device_type": "speaker", "value": 40}),
        ("关闭卧室床头灯", {"intent": "turn_off", "room": "卧室", "device_type": "bedside_lamp"}),
        ("打开书房空气净化器", {"intent": "turn_on", "room": "书房", "device_type": "air_purifier"}),
        ("麻烦提醒我晚上八点吃药", {"intent": "create_reminder", "reminder_time": "20:00", "reminder_content": "吃药"}),
    ],
)
def test_parse_colloquial_variants(client, auth_headers, command, expected):
    response = parse_command(client, auth_headers, command)

    assert_parse(response, expected)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("打开客厅等", {"intent": "turn_on", "room": "客厅", "device_type": "light"}),
        ("卧室冷气调到二十六度", {"intent": "set_temperature", "room": "卧室", "device_type": "air_conditioner", "value": 26}),
        ("把电视机声音调到30", {"intent": "set_volume", "room": None, "device_type": "tv", "value": 30}),
    ],
)
def test_parse_fuzzy_and_alias_variants(client, auth_headers, command, expected):
    response = parse_command(client, auth_headers, command)

    assert_parse(response, expected)
    data = response.json()["data"]
    assert data["match_type"] in {"alias", "fuzzy", "exact"}


def test_parse_confidence_breakdown_exact_command(client, auth_headers):
    response = parse_command(client, auth_headers, "打开客厅灯")

    assert response.status_code == 200
    data = response.json()["data"]
    breakdown = data["parse_detail"]["confidence_breakdown"]
    assert breakdown == {
        "base_score": 0.75,
        "room_bonus": 0.06,
        "device_bonus": 0.06,
        "value_bonus": 0.0,
        "fuzzy_penalty": 0.0,
        "asr_correction_penalty": 0.0,
        "multi_fuzzy_penalty": 0.0,
        "final_confidence": data["confidence"],
    }


def test_parse_confidence_breakdown_asr_correction(client, auth_headers):
    response = parse_command(client, auth_headers, "打开客厅等")

    assert response.status_code == 200
    data = response.json()["data"]
    breakdown = data["parse_detail"]["confidence_breakdown"]
    assert breakdown["asr_correction_penalty"] == 0.04
    assert breakdown["multi_fuzzy_penalty"] == 0.04
    assert breakdown["final_confidence"] == data["confidence"]


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("把卧室空调调到80度", "温度必须在 16-30 范围内"),
        ("将客厅灯亮度调到120", "亮度必须在 0-100 范围内"),
        ("把电视音量调到150", "音量必须在 0-100 范围内"),
        ("把厨房冰箱温度设置为20度", "冷藏温度必须在 2-8 范围内"),
        ("把客厅窗帘开合比例调整为一百二十", "开合比例必须在 0-100 范围内"),
    ],
)
def test_parse_value_out_of_range(client, auth_headers, command, message):
    response = parse_command(client, auth_headers, command)

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALUE_OUT_OF_RANGE"
    assert body["message"] == message
    assert body["data"]["valid"] is False


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("把厨房排风扇风速设置为自动", "风速仅支持 低速、中速、高速"),
        ("把客厅音箱模式设置为自动", "模式仅支持 待机、播放、静音"),
    ],
)
def test_parse_invalid_enum_property_value(client, auth_headers, command, message):
    response = parse_command(client, auth_headers, command)

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_PROPERTY_VALUE"
    assert body["message"] == message
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
