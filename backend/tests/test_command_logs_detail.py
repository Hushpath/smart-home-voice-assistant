from app.models import CommandLog


COMMAND_CANTONESE_AC = "\u5e2e\u6211\u6253\u5f00\u5ba2\u5385\u51b7\u6c14"


def enable_mock_asr(monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "mock")
    monkeypatch.setenv("ASR_ALLOW_MOCK", "true")
    monkeypatch.delenv("MOCK_ASR_TRANSCRIPT", raising=False)


def test_text_execute_log_summary_detail_and_legacy_fields(client, auth_headers):
    response = client.post("/api/commands/execute", headers=auth_headers, json={"command": "打开客厅灯"})
    assert response.status_code == 200

    logs_response = client.get("/api/commands/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    log = logs_response.json()["data"][0]

    assert log["trace_id"].startswith("cmd_")
    assert log["command_text"] == "打开客厅灯"
    assert log["input_source"] == "text"
    assert log["intent"] == "turn_on"
    assert log["room"] == "客厅"
    assert log["device_type"] == "灯"
    assert log["confidence"] is not None
    assert log["success"] is True
    assert log["message"] == "指令执行成功"
    assert "detail" in log

    assert "raw_command" in log
    assert "parsed_result" in log
    assert "execution_result" in log
    assert "error_message" in log
    assert "created_at" in log

    assert log["detail"]["parse"]["intent"] == "turn_on"
    assert log["detail"]["parse"]["intent_scores"]
    assert log["detail"]["normalization"]["normalized_text"] == "打开客厅灯"
    assert log["detail"]["execution"]["success"] is True
    assert log["detail"]["execution"]["execution_latency_ms"] is not None


def test_voice_execute_log_contains_full_explainable_chain(client, auth_headers, testing_session_factory, monkeypatch):
    enable_mock_asr(monkeypatch)
    db = testing_session_factory()
    try:
        before_count = db.query(CommandLog).count()
    finally:
        db.close()

    response = client.post(
        "/api/voice/execute",
        headers=auth_headers,
        files={"audio": ("command.wav", COMMAND_CANTONESE_AC.encode("utf-8"), "audio/wav")},
    )
    assert response.status_code == 200
    trace_id = response.json()["data"]["trace_id"]

    db = testing_session_factory()
    try:
        logs = db.query(CommandLog).all()
        assert len(logs) == before_count + 1
    finally:
        db.close()

    logs_response = client.get("/api/commands/logs", headers=auth_headers)
    log = logs_response.json()["data"][0]
    detail = log["detail"]

    assert log["trace_id"] == trace_id
    assert log["input_source"] == "mock_asr"
    assert log["asr_provider"] == "mock"
    assert detail["asr"]["trace_id"] == trace_id
    assert detail["asr"]["asr_provider"] == "mock"
    assert detail["asr"]["transcript"] == COMMAND_CANTONESE_AC
    assert detail["asr"]["asr_confidence"] == 0.99
    assert detail["asr"]["asr_latency_ms"] is not None
    assert detail["asr"]["raw_asr_result"]["source"] == "mock"

    assert detail["normalization"]["detected_dialect"] == "cantonese"
    assert detail["normalization"]["normalized_text"] == "打开客厅空调"
    assert "冷气 -> 空调" in detail["normalization"]["dialect_matches"]
    assert "帮我" in detail["normalization"]["removed_fillers"]

    assert detail["parse"]["intent"] == "turn_on"
    assert detail["parse"]["room"] == "客厅"
    assert detail["parse"]["device_type"] == "air_conditioner"
    assert detail["parse"]["parser_confidence"] is not None
    assert detail["parse"]["matched_keywords"]
    assert detail["parse"]["match_type"]

    assert detail["execution"]["success"] is True
    assert detail["execution"]["code"] == "OK"
    assert detail["execution"]["message"] == "指令执行成功"
    assert detail["execution"]["device_before"]
    assert detail["execution"]["device_after"]
    assert detail["execution"]["affected_devices"]
    assert detail["execution"]["execution_latency_ms"] is not None
