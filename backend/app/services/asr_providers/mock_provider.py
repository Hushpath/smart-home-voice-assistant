import os
import time

from app.services.asr_providers.base import ASRProvider, ASRRecognitionResult


class MockASRProvider(ASRProvider):
    """Test/local-only ASR provider.

    It is not advertised as a selectable frontend provider. Tests can enable it
    through dependency injection or `ASR_PROVIDER=mock` plus `ASR_ALLOW_MOCK=true`.
    """

    @property
    def name(self) -> str:
        return "mock"

    def is_configured(self) -> bool:
        return os.getenv("ASR_ALLOW_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}

    def recognize(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        dialect: str | None,
        trace_id: str,
    ) -> ASRRecognitionResult:
        started_at = time.perf_counter()
        transcript = os.getenv("MOCK_ASR_TRANSCRIPT", "").strip()
        if not transcript:
            transcript = self._decode_audio_text(audio_bytes) or "打开客厅灯"
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        return ASRRecognitionResult(
            provider=self.name,
            transcript=transcript,
            duration=0.0,
            latency_ms=latency_ms,
            dialect=dialect,
            raw_result={
                "source": "mock",
                "filename": filename,
                "content_type": content_type,
                "trace_id": trace_id,
            },
            error=None,
        )

    def _decode_audio_text(self, audio_bytes: bytes) -> str:
        try:
            return audio_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            return ""
