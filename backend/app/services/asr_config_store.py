import json
import os
from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR


DEFAULT_XUNFEI_BASE_URL = "wss://iat-api.xfyun.cn/v2/iat"
SENSITIVE_FIELDS = {"api_key", "secret_key"}


def get_asr_config_path() -> Path:
    override = os.getenv("ASR_CONFIG_PATH", "").strip()
    if override:
        return Path(override)
    return DATA_DIR / "asr_config.json"


def load_asr_file_config() -> dict[str, Any]:
    path = get_asr_config_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_asr_file_config(values: dict[str, Any]) -> dict[str, Any]:
    current = load_asr_file_config()
    merged = {**current}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value and current.get(key):
                continue
        merged[key] = value

    provider = str(merged.get("provider") or "xunfei").strip().lower() or "xunfei"
    merged["provider"] = "xunfei" if provider == "iflytek" else provider
    merged.setdefault("base_url", DEFAULT_XUNFEI_BASE_URL if merged["provider"] == "xunfei" else "")
    merged.setdefault("enable_cloud", True)
    merged["timeout_seconds"] = _safe_timeout(merged.get("timeout_seconds", 10))

    path = get_asr_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def delete_asr_file_config() -> bool:
    path = get_asr_config_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def public_asr_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config if config is not None else load_asr_file_config()
    provider = str(config.get("provider") or "cloud").strip().lower() or "cloud"
    return {
        "provider": "xunfei" if provider == "iflytek" else provider,
        "base_url_configured": bool(config.get("base_url")),
        "app_id_configured": bool(config.get("app_id")),
        "app_id_masked": _mask(config.get("app_id")),
        "api_key_configured": bool(config.get("api_key")),
        "api_key_masked": _mask(config.get("api_key")),
        "secret_key_configured": bool(config.get("secret_key")),
        "timeout_seconds": _safe_timeout(config.get("timeout_seconds", 10)),
        "enable_cloud": bool(config.get("enable_cloud")),
        "config_file_exists": bool(config),
        "config_path": str(get_asr_config_path()),
    }


def required_xunfei_fields_missing(config: dict[str, Any]) -> list[str]:
    missing = []
    if not config.get("app_id"):
        missing.append("ASR_APP_ID")
    if not config.get("api_key"):
        missing.append("ASR_API_KEY")
    if not config.get("secret_key"):
        missing.append("ASR_SECRET_KEY")
    return missing


def _safe_timeout(value: Any) -> float:
    try:
        return max(1.0, float(value))
    except (TypeError, ValueError):
        return 10.0


def _mask(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= 8:
        return f"{text[:2]}****"
    return f"{text[:4]}****{text[-4:]}"
