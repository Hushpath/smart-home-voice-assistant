from app.models import CommandLog, Device, Room


COMMAND_TURN_ON_LIVING_ROOM_LIGHT = "\u6253\u5f00\u5ba2\u5385\u706f"
DEVICE_LIGHT = "\u706f"
ROOM_LIVING_ROOM = "\u5ba2\u5385"
FALLBACK_MESSAGE_FRAGMENT = "\u6d4f\u89c8\u5668\u8bc6\u522b\u6216\u6587\u672c\u8f93\u5165\u515c\u5e95"


def audio_file(content: bytes = b"fake audio", content_type: str = "audio/wav"):
    return {"audio": ("command.wav", content, content_type)}


def enable_mock_asr(monkeypatch, transcript: str = COMMAND_TURN_ON_LIVING_ROOM_LIGHT):
    monkeypatch.setenv("ASR_PROVIDER", "mock")
    monkeypatch.setenv("ASR_ALLOW_MOCK", "true")
    monkeypatch.setenv("MOCK_ASR_TRANSCRIPT", transcript)


def test_voice_providers_requires_auth(client):
    response = client.get("/api/voice/providers")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_voice_providers_success(client, auth_headers, monkeypatch):
    monkeypatch.delenv("ASR_ENABLE_CLOUD", raising=False)
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)

    response = client.get("/api/voice/providers", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["cloud_configured"] is False
    assert body["data"]["available_providers"] == []
    assert body["data"]["browser_fallback_supported"] is True
    assert body["data"]["text_fallback_supported"] is True


def test_asr_config_requires_auth(client):
    response = client.get("/api/voice/asr-config")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_save_asr_config_and_provider_status(client, auth_headers):
    response = client.post(
        "/api/voice/asr-config",
        headers=auth_headers,
        json={
            "provider": "xunfei",
            "app_id": "test-app-id",
            "api_key": "test-api-key-1234",
            "secret_key": "test-secret-key-5678",
            "timeout_seconds": 12,
            "enable_cloud": True,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    config = data["config"]
    assert config["provider"] == "xunfei"
    assert config["app_id_configured"] is True
    assert config["api_key_configured"] is True
    assert config["secret_key_configured"] is True
    assert config["api_key_masked"] == "test****1234"
    assert "test-api-key-1234" not in str(data)
    assert data["provider_status"]["cloud_configured"] is True
    assert data["provider_status"]["current_provider"] == "xunfei"

    providers_response = client.get("/api/voice/providers", headers=auth_headers)
    assert providers_response.status_code == 200
    providers = providers_response.json()["data"]
    assert providers["cloud_configured"] is True
    assert providers["current_provider"] == "xunfei"


def test_save_asr_config_incomplete_returns_friendly_error(client, auth_headers):
    response = client.post(
        "/api/voice/asr-config",
        headers=auth_headers,
        json={
            "provider": "xunfei",
            "app_id": "test-app-id",
            "timeout_seconds": 10,
            "enable_cloud": True,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "ASR_CONFIG_INCOMPLETE"
    assert "ASR_API_KEY" in body["data"]["missing_fields"]
    assert "ASR_SECRET_KEY" in body["data"]["missing_fields"]


def test_get_asr_config_returns_masked_values(client, auth_headers):
    client.post(
        "/api/voice/asr-config",
        headers=auth_headers,
        json={
            "provider": "xunfei",
            "app_id": "appid-123456",
            "api_key": "apikey-abcdef",
            "secret_key": "secret-xyz987",
            "timeout_seconds": 10,
            "enable_cloud": True,
        },
    )

    response = client.get("/api/voice/asr-config", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["config"]["api_key_masked"] == "apik****cdef"
    assert "apikey-abcdef" not in str(body)
    assert "secret-xyz987" not in str(body)


def test_save_asr_config_preserves_existing_secrets_when_blank(client, auth_headers):
    first = client.post(
        "/api/voice/asr-config",
        headers=auth_headers,
        json={
            "provider": "xunfei",
            "app_id": "appid-123456",
            "api_key": "apikey-abcdef",
            "secret_key": "secret-xyz987",
            "timeout_seconds": 10,
            "enable_cloud": True,
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/voice/asr-config",
        headers=auth_headers,
        json={
            "provider": "xunfei",
            "app_id": "",
            "api_key": "",
            "secret_key": "",
            "timeout_seconds": 20,
            "enable_cloud": True,
        },
    )

    assert second.status_code == 200
    data = second.json()["data"]
    assert data["config"]["timeout_seconds"] == 20.0
    assert data["provider_status"]["cloud_configured"] is True


def test_voice_recognize_with_mock_provider(client, auth_headers, monkeypatch):
    enable_mock_asr(monkeypatch, COMMAND_TURN_ON_LIVING_ROOM_LIGHT)

    response = client.post(
        "/api/voice/recognize",
        headers=auth_headers,
        files=audio_file(),
        data={"dialect": "cantonese"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trace_id"].startswith("voice_")
    assert data["provider"] == "mock"
    assert data["transcript"] == COMMAND_TURN_ON_LIVING_ROOM_LIGHT
    assert data["content_type"] == "audio/wav"
    assert data["dialect"] == "cantonese"


def test_voice_execute_with_mock_provider_success(client, auth_headers, testing_session_factory, monkeypatch):
    enable_mock_asr(monkeypatch, COMMAND_TURN_ON_LIVING_ROOM_LIGHT)

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trace_id"].startswith("voice_")
    assert data["recognition"]["transcript"] == COMMAND_TURN_ON_LIVING_ROOM_LIGHT
    assert data["execution"]["parsed"]["intent"] == "turn_on"

    db = testing_session_factory()
    try:
        device = (
            db.query(Device)
            .join(Room)
            .filter(Room.name == ROOM_LIVING_ROOM, Device.name == DEVICE_LIGHT)
            .first()
        )
        assert device.is_on is True
    finally:
        db.close()


def test_voice_execute_log_contains_trace_id(client, auth_headers, testing_session_factory, monkeypatch):
    enable_mock_asr(monkeypatch, COMMAND_TURN_ON_LIVING_ROOM_LIGHT)

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())
    trace_id = response.json()["data"]["trace_id"]

    db = testing_session_factory()
    try:
        log = db.query(CommandLog).order_by(CommandLog.id.desc()).first()
        assert log.raw_command == COMMAND_TURN_ON_LIVING_ROOM_LIGHT
        assert log.parsed_result["context"]["trace_id"] == trace_id
        assert log.execution_result["context"]["trace_id"] == trace_id
        assert log.execution_result["context"]["asr_provider"] == "mock"
    finally:
        db.close()


def test_voice_recognize_cloud_not_configured(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "cloud")
    monkeypatch.setenv("ASR_ENABLE_CLOUD", "false")
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)

    response = client.post("/api/voice/recognize", headers=auth_headers, files=audio_file())

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "ASR_PROVIDER_NOT_CONFIGURED"
    assert FALLBACK_MESSAGE_FRAGMENT in body["message"]
    assert body["data"]["trace_id"].startswith("voice_")
    assert body["data"]["input_source"] == "cloud_asr"
    assert body["data"]["asr_provider"] == "cloud"
    assert body["data"]["fallback"] == ["browser_speech", "text_input"]


def test_voice_recognize_empty_audio(client, auth_headers, monkeypatch):
    enable_mock_asr(monkeypatch)

    response = client.post("/api/voice/recognize", headers=auth_headers, files=audio_file(b""))

    assert response.status_code == 400
    assert response.json()["code"] == "ASR_EMPTY_AUDIO"


def test_voice_recognize_missing_audio(client, auth_headers, monkeypatch):
    enable_mock_asr(monkeypatch)

    response = client.post("/api/voice/recognize", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["code"] == "ASR_AUDIO_REQUIRED"


def test_voice_recognize_unsupported_audio_format(client, auth_headers, monkeypatch):
    enable_mock_asr(monkeypatch)

    response = client.post(
        "/api/voice/recognize",
        headers=auth_headers,
        files=audio_file(b"fake audio", "audio/ogg"),
    )

    assert response.status_code == 415
    body = response.json()
    assert body["code"] == "ASR_UNSUPPORTED_AUDIO_FORMAT"
    assert body["data"]["content_type"] == "audio/ogg"
