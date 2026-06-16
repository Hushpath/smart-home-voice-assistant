from app.models import CommandLog
from app.services.command_parser import CommandParser
from app.services.dialect_normalizer import DialectNormalizer, normalize_and_parse_command


def parse(command: str):
    return normalize_and_parse_command(command, parser=CommandParser())


def test_cantonese_cold_air_normalizes_to_air_conditioner():
    parsed, normalization = parse("帮我打开客厅冷气")

    assert normalization.detected_dialect == "cantonese"
    assert normalization.normalized_text == "打开客厅空调"
    assert "冷气 -> 空调" in normalization.dialect_matches
    assert "帮我" in normalization.removed_fillers
    assert parsed.intent == "turn_on"
    assert parsed.device_type == "air_conditioner"


def test_cantonese_turn_off_light_phrases():
    for command in ["熄灯", "熄客廳燈"]:
        parsed, normalization = parse(command)

        assert normalization.detected_dialect == "cantonese"
        assert "关闭" in normalization.normalized_text
        assert parsed.intent == "turn_off"
        assert parsed.device_type == "light"


def test_cantonese_volume_normalizes_to_mandarin_volume():
    parsed, normalization = parse("将电视机声量调到三十")

    assert "声量 -> 音量" in normalization.dialect_matches
    assert "三十 -> 30" in normalization.number_conversions
    assert parsed.intent == "set_volume"
    assert parsed.device_type == "tv"
    assert parsed.value == 30


def test_cantonese_reminder_food_medicine_and_time():
    parsed, normalization = parse("提醒我今晚八点食药")

    assert "食药 -> 吃药" in normalization.dialect_matches
    assert "八 -> 8" in normalization.number_conversions
    assert parsed.intent == "create_reminder"
    assert parsed.reminder_time == "20:00"
    assert parsed.reminder_content == "吃药"


def test_cantonese_sleep_scene():
    parsed, normalization = parse("开启瞓觉模式")

    assert normalization.detected_dialect == "cantonese"
    assert "瞓觉模式 -> 睡眠模式" in normalization.dialect_matches
    assert parsed.intent == "run_scene"
    assert parsed.scene == "睡眠模式"


def test_auto_detects_supported_dialects():
    assert DialectNormalizer().normalize("打开客厅冷气").detected_dialect == "cantonese"
    assert DialectNormalizer().normalize("开哈客厅灯").detected_dialect == "southwest"
    assert DialectNormalizer().normalize("客厅灯开开").detected_dialect == "northeast"
    assert DialectNormalizer().normalize("打开客厅灯").detected_dialect == "mandarin"


def test_southwest_and_northeast_commands_parse():
    parsed, normalization = parse("开哈客厅灯")
    assert normalization.normalized_text == "打开客厅灯"
    assert parsed.intent == "turn_on"
    assert parsed.room == "客厅"

    parsed, normalization = parse("客厅灯开开")
    assert normalization.normalized_text == "客厅灯打开"
    assert parsed.intent == "turn_on"
    assert parsed.room == "客厅"


def test_asr_corrections_and_number_conversion():
    parsed, normalization = parse("打开客厅等")
    assert "客厅等 -> 客厅灯" in normalization.asr_corrections
    assert parsed.intent == "turn_on"
    assert parsed.device_type == "light"

    parsed, normalization = parse("卧室空条调到二十六度")
    assert "空条 -> 空调" in normalization.asr_corrections
    assert "二十六 -> 26" in normalization.number_conversions
    assert parsed.intent == "set_temperature"
    assert parsed.value == 26

    parsed, normalization = parse("将客厅灯光亮度调到八十")
    assert "八十 -> 80" in normalization.number_conversions
    assert parsed.intent == "set_brightness"
    assert parsed.value == 80


def test_standard_mandarin_command_still_works():
    parsed, normalization = parse("打开客厅灯")

    assert normalization.detected_dialect == "mandarin"
    assert parsed.valid is True
    assert parsed.intent == "turn_on"
    assert parsed.room == "客厅"
    assert parsed.device_type == "light"


def test_commands_execute_uses_dialect_normalizer(client, auth_headers):
    response = client.post("/api/commands/execute", headers=auth_headers, json={"command": "开哈客厅灯"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["parsed"]["intent"] == "turn_on"
    assert data["normalization"]["detected_dialect"] == "southwest"


def test_voice_execute_returns_and_logs_normalization(client, auth_headers, testing_session_factory, monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "mock")
    monkeypatch.setenv("ASR_ALLOW_MOCK", "true")
    monkeypatch.delenv("MOCK_ASR_TRANSCRIPT", raising=False)

    response = client.post(
        "/api/voice/execute",
        headers=auth_headers,
        files={"audio": ("command.wav", "帮我打开客厅冷气".encode("utf-8"), "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    normalization = data["execution"]["normalization"]
    assert normalization["detected_dialect"] == "cantonese"
    assert "冷气 -> 空调" in normalization["dialect_matches"]

    db = testing_session_factory()
    try:
        log = db.query(CommandLog).order_by(CommandLog.id.desc()).first()
        log_normalization = log.parsed_result["parse_detail"]["dialect_normalization"]
        assert log_normalization["detected_dialect"] == "cantonese"
        assert "冷气 -> 空调" in log_normalization["dialect_matches"]
        assert log.execution_result["context"]["normalization"]["normalized_text"] == "打开客厅空调"
    finally:
        db.close()
