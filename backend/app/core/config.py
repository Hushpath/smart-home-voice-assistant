from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "app.db"


class Settings(BaseModel):
    app_name: str = "智能家居语音交互助手系统"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    jwt_secret_key: str = "dev-secret-key-change-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120


settings = Settings()
