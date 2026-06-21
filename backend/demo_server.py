import os
import sys
from pathlib import Path

import uvicorn


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RUNTIME_DIR = _runtime_dir()

os.environ.setdefault("SMART_HOME_DATA_DIR", str(RUNTIME_DIR / "data"))
os.environ.setdefault("SMART_HOME_STATIC_DIR", str(RUNTIME_DIR / "frontend-dist"))

from app.db.seed_demo_data import seed_demo_data  # noqa: E402
from app.main import app  # noqa: E402


if __name__ == "__main__":
    seed_demo_data()
    uvicorn.run(app, host="127.0.0.1", port=8000)
