import pytest

from app.models import CommandLog, Device, DeviceStatusHistory, User
from app.services.asr_post_corrector import correct_asr_text


def get_test_user(db):
    return db.query(User).filter(User.username == "testuser").one()


def execute_command(client, auth_headers, command):
    return client.post("/api/commands/execute", headers=auth_headers, json={"command": command})


def parse_command(client, auth_headers, command):
    return client.post("/api/commands/parse", headers=auth_headers, json={"command": command})


def audio_file(content: bytes = b"fake audio", content_type: str = "audio/wav"):
    return {"audio": ("command.wav", content, content_type)}


@pytest.mark.parametrize(
    ("category", "command", "expected_text", "changed"),
    [
        ("标准说法", "打开客厅灯", "打开客厅灯", False),
        ("口语/参数说法", "把客厅窗帘开合比例调整为五十", "把客厅窗帘开合比例调整为五十", False),
        ("方言说法", "帮我打开客厅冷气", "帮我打开客厅冷气", False),
        ("ASR错字说法", "把厨房冰香温度设置为5度", "把厨房冰箱温度设置为5度", True),
        ("动态领域词表", "打开书房空气净化", "打开书房空气净化器", True),
        ("无效/歧义保护", "等一下再打开客厅灯", "等一下再打开客厅灯", False),
    ],
)
def test_asr_post_corrector_regression_table(testing_session_factory, category, command, expected_text, changed):
    db = testing_session_factory()
    try:
        result = correct_asr_text(command, db=db, user=get_test_user(db))
    finally:
        db.close()

    assert category
    assert result.corrected_text == expected_text
    assert result.changed is changed


def test_parse_uses_post_corrected_text(client, auth_headers):
    response = parse_command(client, auth_headers, "把厨房冰香温度设置为5度")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["original_text"] == "把厨房冰香温度设置为5度"
    assert data["normalized_text"] == "把厨房冰箱温度设置5度"
    assert data["asr_post_correction"]["changed"] is True
    assert data["asr_post_correction"]["corrected_text"] == "把厨房冰箱温度设置为5度"
    assert data["device_type"] == "fridge"
    assert data["property_name"] == "temperature"
    assert data["property_value"] == 5


def test_execute_logs_post_correction_and_updates_device(client, auth_headers, testing_session_factory):
    response = execute_command(client, auth_headers, "把厨房冰香温度设置为5度")

    assert response.status_code == 200
    data = response.json()["data"]
    correction = data["parsed"]["parse_detail"]["asr_post_correction"]
    assert correction["corrected_text"] == "把厨房冰箱温度设置为5度"
    assert data["result"]["after_state"]["properties"]["temperature"] == 5

    db = testing_session_factory()
    try:
        device = db.query(Device).filter(Device.device_type == "fridge").one()
        assert device.properties["temperature"] == 5
        assert db.query(DeviceStatusHistory).filter(DeviceStatusHistory.device_id == device.id).count() == 1
        log = db.query(CommandLog).one()
        assert log.raw_command == "把厨房冰香温度设置为5度"
        assert log.parsed_result["context"]["asr_post_correction"]["corrected_text"] == "把厨房冰箱温度设置为5度"
        assert log.execution_result["context"]["asr_post_correction"]["corrections"][0]["source"] == "冰香"
    finally:
        db.close()


def test_post_corrector_does_not_overcorrect_short_common_words(client, auth_headers):
    response = parse_command(client, auth_headers, "等一下再打开客厅灯")

    assert response.status_code == 200
    data = response.json()["data"]
    assert "asr_post_correction" not in data
    assert data["is_batch"] is True
    assert data["sub_commands"][1]["device_type"] == "light"
    assert data["sub_commands"][1]["intent"] == "turn_on"


def test_voice_recognize_returns_corrected_transcript(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "mock")
    monkeypatch.setenv("ASR_ALLOW_MOCK", "true")
    monkeypatch.setenv("MOCK_ASR_TRANSCRIPT", "打开书房空气进化器")

    response = client.post("/api/voice/recognize", headers=auth_headers, files=audio_file())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["transcript"] == "打开书房空气进化器"
    assert data["corrected_transcript"] == "打开书房空气净化器"
    assert data["asr_post_correction"]["corrections"][0]["source"] == "空气进化器"
