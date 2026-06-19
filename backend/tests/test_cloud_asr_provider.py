import json
from types import SimpleNamespace

import httpx


def audio_file(content: bytes = b"fake audio", content_type: str = "audio/wav"):
    return {"audio": ("command.wav", content, content_type)}


def configure_cloud(monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "cloud")
    monkeypatch.setenv("ASR_ENABLE_CLOUD", "true")
    monkeypatch.setenv("ASR_BASE_URL", "https://asr.example.test/recognize")
    monkeypatch.setenv("ASR_API_KEY", "test-api-key")
    monkeypatch.setenv("ASR_APP_ID", "test-app-id")
    monkeypatch.setenv("ASR_TIMEOUT_SECONDS", "1")


def configure_xunfei(monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "xunfei")
    monkeypatch.setenv("ASR_ENABLE_CLOUD", "true")
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    monkeypatch.setenv("ASR_API_KEY", "test-api-key")
    monkeypatch.setenv("ASR_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ASR_APP_ID", "test-app-id")
    monkeypatch.setenv("ASR_TIMEOUT_SECONDS", "1")


class FakeResponse:
    def __init__(self, payload=None, status_code=200, json_error=False):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self):
        if self.json_error:
            raise ValueError("invalid json")
        return self.payload


class FakeClient:
    response = FakeResponse({"transcript": "打开客厅灯"})
    error = None
    last_timeout = None
    last_url = None
    last_kwargs = None

    def __init__(self, timeout=None):
        FakeClient.last_timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, **kwargs):
        FakeClient.last_url = url
        FakeClient.last_kwargs = kwargs
        if FakeClient.error:
            raise FakeClient.error
        return FakeClient.response


def patch_httpx_client(monkeypatch, response=None, error=None):
    FakeClient.response = response or FakeResponse({"transcript": "打开客厅灯"})
    FakeClient.error = error
    FakeClient.last_timeout = None
    FakeClient.last_url = None
    FakeClient.last_kwargs = None
    monkeypatch.setattr("app.services.asr_providers.cloud_provider.httpx.Client", FakeClient)


def test_cloud_unconfigured_provider_status(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "cloud")
    monkeypatch.setenv("ASR_ENABLE_CLOUD", "false")
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)

    response = client.get("/api/voice/providers", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["cloud_configured"] is False
    assert data["available_providers"] == []
    assert data["fallback"] == ["browser_speech", "text_input"]
    assert "ASR_ENABLE_CLOUD=true" in data["cloud_status"]["missing_fields"]


def test_cloud_unconfigured_execute_returns_provider_not_configured(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ASR_PROVIDER", "cloud")
    monkeypatch.setenv("ASR_ENABLE_CLOUD", "false")
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "ASR_PROVIDER_NOT_CONFIGURED"
    assert body["data"]["trace_id"].startswith("voice_")
    assert body["data"]["input_source"] == "cloud_asr"
    assert body["data"]["asr_provider"] == "cloud"
    assert body["data"]["success"] is False
    assert body["data"]["error_code"] == "ASR_PROVIDER_NOT_CONFIGURED"
    assert body["data"]["fallback"] == ["browser_speech", "text_input"]


def test_cloud_timeout_returns_asr_timeout(client, auth_headers, monkeypatch):
    configure_cloud(monkeypatch)
    patch_httpx_client(monkeypatch, error=httpx.TimeoutException("timeout"))

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 504
    body = response.json()
    assert body["code"] == "ASR_TIMEOUT"
    assert body["data"]["latency_ms"] is not None


def test_cloud_empty_transcript_returns_asr_empty_transcript(client, auth_headers, monkeypatch):
    configure_cloud(monkeypatch)
    patch_httpx_client(monkeypatch, response=FakeResponse({"transcript": ""}))

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "ASR_EMPTY_TRANSCRIPT"
    assert body["data"]["raw_result"]["transcript"] == ""


def test_cloud_invalid_response_returns_asr_invalid_response(client, auth_headers, monkeypatch):
    configure_cloud(monkeypatch)
    patch_httpx_client(monkeypatch, response=FakeResponse({"unexpected": "shape"}))

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 502
    body = response.json()
    assert body["code"] == "ASR_INVALID_RESPONSE"
    assert body["data"]["raw_result"] == {"unexpected": "shape"}


def test_cloud_auth_failed_returns_asr_auth_failed(client, auth_headers, monkeypatch):
    configure_cloud(monkeypatch)
    patch_httpx_client(monkeypatch, response=FakeResponse({"error": "unauthorized"}, status_code=401))

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 502
    body = response.json()
    assert body["code"] == "ASR_AUTH_FAILED"
    assert body["data"]["status_code"] == 401


def test_cloud_unsupported_audio_format_returns_asr_unsupported_audio_format(client, auth_headers, monkeypatch):
    configure_cloud(monkeypatch)
    patch_httpx_client(monkeypatch)

    response = client.post(
        "/api/voice/execute",
        headers=auth_headers,
        files=audio_file(b"fake audio", "audio/ogg"),
    )

    assert response.status_code == 415
    assert response.json()["code"] == "ASR_UNSUPPORTED_AUDIO_FORMAT"
    assert FakeClient.last_url is None


def test_cloud_success_uses_generic_http_request_framework(client, auth_headers, monkeypatch):
    configure_cloud(monkeypatch)
    patch_httpx_client(monkeypatch, response=FakeResponse({"transcript": "打开客厅灯", "duration": 1.2}))

    response = client.post("/api/voice/execute", headers=auth_headers, files=audio_file())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["recognition"]["provider"] == "cloud"
    assert "confidence" not in data["recognition"]
    assert data["recognition"]["duration"] == 1.2
    assert FakeClient.last_url == "https://asr.example.test/recognize"
    assert FakeClient.last_timeout == 1.0
    assert FakeClient.last_kwargs["headers"]["Authorization"] == "Bearer test-api-key"
    assert FakeClient.last_kwargs["headers"]["X-ASR-App-Id"] == "test-app-id"


def test_xunfei_provider_status_uses_default_endpoint(client, auth_headers, monkeypatch):
    configure_xunfei(monkeypatch)

    response = client.get("/api/voice/providers", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_provider"] == "xunfei"
    assert data["cloud_configured"] is True
    assert data["available_providers"] == ["xunfei"]
    assert data["cloud_status"]["provider"] == "xunfei"
    assert data["cloud_status"]["base_url_configured"] is True


def test_xunfei_rejects_webm_without_calling_provider(client, auth_headers, monkeypatch):
    configure_xunfei(monkeypatch)

    response = client.post(
        "/api/voice/execute",
        headers=auth_headers,
        files=audio_file(b"fake audio", "audio/webm"),
    )

    assert response.status_code == 415
    body = response.json()
    assert body["code"] == "ASR_UNSUPPORTED_AUDIO_FORMAT"
    assert body["data"]["asr_provider"] == "xunfei"


def test_xunfei_success_uses_websocket_and_parses_words(client, auth_headers, monkeypatch):
    configure_xunfei(monkeypatch)
    sent_frames = []
    frame_intervals = []
    opened = {}

    class FakeWebSocket:
        def __init__(self):
            self.read_count = 0

        def send(self, payload):
            sent_frames.append(payload)

        def recv(self):
            self.read_count += 1
            return (
                '{"code":0,"sid":"sid-1","data":{"status":2,'
                '"result":{"ws":[{"cw":[{"w":"打开"}]},{"cw":[{"w":"客厅灯"}]}]}}}'
            )

        def close(self):
            pass

    def create_connection(url, timeout=None):
        opened["url"] = url
        opened["timeout"] = timeout
        return FakeWebSocket()

    fake_websocket = SimpleNamespace(
        create_connection=create_connection,
        WebSocketTimeoutException=TimeoutError,
    )
    monkeypatch.setitem(__import__("sys").modules, "websocket", fake_websocket)
    monkeypatch.setattr("app.services.asr_providers.cloud_provider.time.sleep", frame_intervals.append)

    response = client.post(
        "/api/voice/execute",
        headers=auth_headers,
        files=audio_file(b"fake mp3 audio" * 200, "audio/mpeg"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["recognition"]["provider"] == "xunfei"
    assert data["recognition"]["transcript"] == "打开客厅灯"
    assert "authorization=" in opened["url"]
    assert opened["timeout"] == 1.0
    assert sent_frames
    first_frame = json.loads(sent_frames[0])
    assert first_frame["data"]["status"] == 0
    assert first_frame["business"] == {
        "language": "zh_cn",
        "domain": "iat",
        "accent": "mandarin",
        "vinfo": 1,
    }
    assert all(interval == 0.04 for interval in frame_intervals)
