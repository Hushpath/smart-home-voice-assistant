import os
from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "app.db"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings(BaseModel):
    app_name: str = "智能家居语音交互助手系统"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    jwt_secret_key: str = "dev-secret-key-change-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    asr_provider: str = os.getenv("ASR_PROVIDER", "cloud")
    asr_base_url: str = os.getenv("ASR_BASE_URL", "")
    asr_api_key: str = os.getenv("ASR_API_KEY", "")
    asr_secret_key: str = os.getenv("ASR_SECRET_KEY", "")
    asr_app_id: str = os.getenv("ASR_APP_ID", "")
    asr_timeout_seconds: int = _env_int("ASR_TIMEOUT_SECONDS", 10)
    asr_enable_cloud: bool = os.getenv("ASR_ENABLE_CLOUD", "false").lower() in {"1", "true", "yes", "on"}


settings = Settings()
