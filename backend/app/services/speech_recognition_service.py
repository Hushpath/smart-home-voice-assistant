import os
import secrets
from datetime import datetime
from typing import Any

from app.services.asr_providers import (
    ASRProvider,
    ASRProviderError,
    ASRRecognitionResult,
    CloudASRProvider,
    MockASRProvider,
)


SUPPORTED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mpeg"}


def generate_voice_trace_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"voice_{timestamp}_{secrets.token_hex(4)}"


class SpeechRecognitionService:
    def __init__(self, provider: ASRProvider | None = None):
        self.cloud_provider = CloudASRProvider()
        self.provider = provider or self._select_provider()

    def provider_status(self) -> dict[str, Any]:
        cloud_configured = self.cloud_provider.is_configured()
        cloud_status = self.cloud_provider.configuration_status()
        current_provider = os.getenv("ASR_PROVIDER", "cloud").strip().lower() or "cloud"
        provider_name = cloud_status.get("provider") or current_provider
        return {
            "current_provider": provider_name,
            "cloud_configured": cloud_configured,
            "cloud_status": cloud_status,
            "available_providers": [provider_name] if cloud_configured else [],
            "browser_fallback_supported": True,
            "text_fallback_supported": True,
            "fallback": ["browser_speech", "text_input"],
            "notes": (
                f"云端语音识别（{provider_name}）已配置，浏览器识别和文本输入仍可作为兜底。"
                if cloud_configured
                else "云端语音识别服务未配置，请使用浏览器识别或文本输入兜底。"
            ),
        }

    def recognize(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        dialect: str | None,
        trace_id: str,
    ) -> ASRRecognitionResult:
        self._validate_audio(audio_bytes, content_type)
        if not self.provider.is_configured():
            raise ASRProviderError(
                "ASR_PROVIDER_NOT_CONFIGURED",
                "云端语音识别服务未配置，请使用浏览器识别或文本输入兜底。",
                status_code=503,
                data={
                    "fallback": ["browser_speech", "text_input"],
                    "configuration": self.cloud_provider.configuration_status(),
                    "asr_provider": self.cloud_provider.name,
                },
            )
        result = self.provider.recognize(audio_bytes, filename, content_type, dialect, trace_id)
        if not result.transcript.strip():
            raise ASRProviderError(
                "ASR_EMPTY_TRANSCRIPT",
                "云端语音识别未返回有效文本，请使用浏览器识别或文本输入兜底。",
                status_code=422,
                data=result.to_dict(),
            )
        return result

    def _select_provider(self) -> ASRProvider:
        provider_name = os.getenv("ASR_PROVIDER", "cloud").strip().lower()
        if provider_name == "mock" and self._mock_allowed():
            return MockASRProvider()
        return self.cloud_provider

    def _mock_allowed(self) -> bool:
        return os.getenv("ASR_ALLOW_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}

    def _validate_audio(self, audio_bytes: bytes, content_type: str | None) -> None:
        if not audio_bytes:
            raise ASRProviderError("ASR_EMPTY_AUDIO", "上传音频为空，请重新录音后再试。", status_code=400)
        normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
        if normalized_type not in SUPPORTED_AUDIO_TYPES:
            raise ASRProviderError(
                "ASR_UNSUPPORTED_AUDIO_FORMAT",
                "暂不支持该音频格式，请使用 webm、wav 或 mp3 音频。",
                status_code=415,
                data={"content_type": content_type, "supported_types": sorted(SUPPORTED_AUDIO_TYPES)},
            )
