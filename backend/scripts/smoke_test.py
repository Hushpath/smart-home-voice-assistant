import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.init_db import seed_initial_data  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import home_actions  # noqa: E402


def assert_ok(response, label):
    body = response.json()
    if response.status_code >= 400 or not body.get("success"):
        raise AssertionError(f"{label} failed: status={response.status_code}, body={body}")
    print(f"[OK] {label}")
    return body.get("data")


def main():
    os.environ["ASR_PROVIDER"] = "mock"
    os.environ["ASR_ALLOW_MOCK"] = "true"
    os.environ["MOCK_ASR_TRANSCRIPT"] = "帮我打开客厅冷气"

    home_actions.clear_weather_cache()
    home_actions._fetch_open_meteo_weather = lambda city_name: (_ for _ in ()).throw(
        ValueError(f"real weather disabled in smoke test: {city_name}")
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{(Path(temp_dir) / 'smoke.db').as_posix()}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        db = session_factory()
        try:
            seed_initial_data(db)
        finally:
            db.close()

        def override_get_db():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                assert_ok(client.get("/api/health"), "health")

                login = assert_ok(
                    client.post("/api/auth/login", json={"username": "testuser", "password": "test123456"}),
                    "login",
                )
                headers = {"Authorization": f"Bearer {login['access_token']}"}

                dashboard = assert_ok(client.get("/api/dashboard", headers=headers), "dashboard")
                if dashboard["device_count"] < 1:
                    raise AssertionError("dashboard returned no devices")

                devices = assert_ok(client.get("/api/devices", headers=headers), "devices")
                if not devices:
                    raise AssertionError("devices list is empty")

                providers = assert_ok(client.get("/api/voice/providers", headers=headers), "voice providers")
                if not providers.get("browser_fallback_supported") or not providers.get("text_fallback_supported"):
                    raise AssertionError("fallback providers missing")

                for command in [
                    "打开客厅灯",
                    "把卧室空调调到26度",
                    "帮我打开客厅冷气",
                    "将电视机声量调到三十",
                    "开启瞓觉模式",
                    "提醒我今晚八点食药",
                    "查询北京天气",
                ]:
                    assert_ok(
                        client.post("/api/commands/execute", headers=headers, json={"command": command}),
                        f"commands execute: {command}",
                    )

                voice = assert_ok(
                    client.post(
                        "/api/voice/execute",
                        headers=headers,
                        files={"audio": ("command.wav", b"fake audio", "audio/wav")},
                    ),
                    "voice execute with mock ASR",
                )
                if not voice["trace_id"].startswith("voice_"):
                    raise AssertionError("voice execute did not return a voice trace_id")

                logs = assert_ok(client.get("/api/commands/logs", headers=headers), "command logs")
                if not logs:
                    raise AssertionError("command logs is empty")
                latest = logs[0]
                for key in ("trace_id", "detail", "parsed_result", "execution_result"):
                    if key not in latest:
                        raise AssertionError(f"latest log missing {key}")
                for key in ("asr", "normalization", "parse", "execution", "raw"):
                    if key not in latest["detail"]:
                        raise AssertionError(f"latest log detail missing {key}")

                history = assert_ok(client.get("/api/devices/1/history", headers=headers), "device history")
                if not history:
                    raise AssertionError("device history is empty after command execution")
        finally:
            app.dependency_overrides.clear()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()

    print("[OK] smoke test completed")


if __name__ == "__main__":
    main()
