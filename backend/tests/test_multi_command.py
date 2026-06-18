from app.models import CommandLog, Device, DeviceStatusHistory, Reminder


def post_parse(client, auth_headers, command):
    return client.post("/api/commands/parse", headers=auth_headers, json={"command": command})


def post_execute(client, auth_headers, command):
    return client.post("/api/commands/execute", headers=auth_headers, json={"command": command})


def get_device(db, room_name, device_type):
    return (
        db.query(Device)
        .join(Device.room)
        .filter(Device.device_type == device_type, Device.room.has(name=room_name))
        .one()
    )


def assert_batch_parse(client, auth_headers, command, expected_texts):
    response = post_parse(client, auth_headers, command)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_batch"] is True
    assert data["command_count"] == len(expected_texts)
    assert [item["text"] for item in data["sub_commands"]] == expected_texts
    return data


def test_parse_same_action_same_room_multi_devices(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开客厅灯和空调", ["打开客厅灯", "打开客厅空调"])

    assert [item["device_type"] for item in data["sub_commands"]] == ["light", "air_conditioner"]
    assert all(item["room"] == "客厅" for item in data["sub_commands"])


def test_parse_three_devices_with_punctuation(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开客厅灯、空调和电视", ["打开客厅灯", "打开客厅空调", "打开客厅电视"])

    assert [item["device_type"] for item in data["sub_commands"]] == ["light", "air_conditioner", "tv"]


def test_parse_same_action_multi_rooms_same_device(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开客厅和卧室的灯", ["打开客厅灯", "打开卧室灯"])

    assert [item["room"] for item in data["sub_commands"]] == ["客厅", "卧室"]
    assert all(item["device_type"] == "light" for item in data["sub_commands"])


def test_parse_independent_device_commands(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开客厅灯并把卧室空调调到26度", ["打开客厅灯", "把卧室空调设置26度"])

    assert data["sub_commands"][0]["intent"] == "turn_on"
    assert data["sub_commands"][1]["intent"] == "set_temperature"
    assert data["sub_commands"][1]["value"] == 26


def test_parse_context_inheritance(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开卧室空调并调到26度", ["打开卧室空调", "把卧室空调设置26度"])

    assert data["sub_commands"][0]["intent"] == "turn_on"
    assert data["sub_commands"][1]["intent"] == "set_temperature"
    assert data["sub_commands"][1]["room"] == "卧室"
    assert data["sub_commands"][1]["device_type"] == "air_conditioner"


def test_parse_inherits_action_and_room_for_short_device_clause(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开客厅灯并空调", ["打开客厅灯", "打开客厅空调"])

    assert [item["intent"] for item in data["sub_commands"]] == ["turn_on", "turn_on"]
    assert [item["room"] for item in data["sub_commands"]] == ["客厅", "客厅"]
    assert [item["device_type"] for item in data["sub_commands"]] == ["light", "air_conditioner"]


def test_parse_sequence_connector_does_not_force_same_action(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开客厅灯然后关闭空调", ["打开客厅灯", "关闭客厅空调"])

    assert [item["intent"] for item in data["sub_commands"]] == ["turn_on", "turn_off"]
    assert data["sub_commands"][1]["room"] == "客厅"
    assert data["sub_commands"][1]["device_type"] == "air_conditioner"


def test_parse_trailing_action_multi_devices(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "客厅灯和空调都打开", ["打开客厅灯", "打开客厅空调"])

    assert all(item["valid"] is True for item in data["sub_commands"])


def test_parse_ambiguous_batch_sub_command_marked_invalid(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "打开灯并关闭空调", ["打开灯", "关闭空调"])

    assert data["valid"] is False
    assert all(item["valid"] is False for item in data["sub_commands"])
    assert all(item["error_code"] == "AMBIGUOUS_SUB_COMMAND" for item in data["sub_commands"])


def test_parse_mixed_value_commands(client, auth_headers):
    data = assert_batch_parse(client, auth_headers, "将客厅灯亮度调到80并把电视音量调到30", ["将客厅灯亮度设置80", "把客厅电视音量设置30"])

    assert [item["intent"] for item in data["sub_commands"]] == ["set_brightness", "set_volume"]
    assert [item["value"] for item in data["sub_commands"]] == [80, 30]


def test_execute_scene_and_reminder_batch(client, auth_headers, testing_session_factory):
    response = post_execute(client, auth_headers, "开启睡眠模式并提醒我晚上八点吃药")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["is_batch"] is True
    assert data["success_count"] == 2
    assert data["failed_count"] == 0

    db = testing_session_factory()
    try:
        assert db.query(Reminder).filter(Reminder.title == "吃药").count() == 1
        assert db.query(DeviceStatusHistory).count() == 3
        assert db.query(CommandLog).count() == 1
    finally:
        db.close()


def test_execute_partial_success(client, auth_headers, testing_session_factory):
    response = post_execute(client, auth_headers, "打开客厅灯并打开阳台灯")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "PARTIAL_SUCCESS"
    data = body["data"]
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert data["sub_results"][0]["success"] is True
    assert data["sub_results"][1]["code"] == "ROOM_NOT_FOUND"

    db = testing_session_factory()
    try:
        assert db.query(CommandLog).count() == 1
        assert db.query(DeviceStatusHistory).count() == 1
    finally:
        db.close()


def test_execute_batch_log_detail(client, auth_headers, testing_session_factory):
    response = post_execute(client, auth_headers, "打开客厅灯和空调")
    assert response.status_code == 200

    db = testing_session_factory()
    try:
        log = db.query(CommandLog).one()
        assert log.parsed_result["is_batch"] is True
        assert log.parsed_result["command_count"] == 2
        assert len(log.parsed_result["sub_commands"]) == 2
        assert log.execution_result["is_batch"] is True
        assert len(log.execution_result["sub_results"]) == 2
        assert db.query(DeviceStatusHistory).count() == 2
    finally:
        db.close()

    logs_response = client.get("/api/commands/logs", headers=auth_headers)
    log_data = logs_response.json()["data"][0]
    assert log_data["intent"] == "batch"
    assert log_data["detail"]["batch"]["is_batch"] is True
    assert len(log_data["detail"]["batch"]["sub_commands"]) == 2
    assert len(log_data["detail"]["batch"]["sub_results"]) == 2


def test_execute_multi_room_device_history(client, auth_headers, testing_session_factory):
    response = post_execute(client, auth_headers, "打开客厅和卧室的灯")

    assert response.status_code == 200
    db = testing_session_factory()
    try:
        assert get_device(db, "客厅", "light").is_on is True
        assert get_device(db, "卧室", "light").is_on is True
        assert db.query(DeviceStatusHistory).count() == 2
    finally:
        db.close()


def test_single_command_still_uses_original_shape(client, auth_headers):
    response = post_execute(client, auth_headers, "打开客厅灯")

    assert response.status_code == 200
    data = response.json()["data"]
    assert "is_batch" not in data
    assert data["parsed"]["intent"] == "turn_on"
    assert data["result"]["after_state"]["is_on"] is True
