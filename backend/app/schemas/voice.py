from typing import Any

from pydantic import BaseModel, Field


class VoiceProviderStatus(BaseModel):
    current_provider: str
    cloud_configured: bool
    available_providers: list[str]
    browser_fallback_supported: bool = True
    text_fallback_supported: bool = True
    notes: str


class VoiceRecognitionData(BaseModel):
    trace_id: str
    provider: str
    transcript: str
    confidence: float | None = None
    duration: float | None = None
    latency_ms: int | None = None
    dialect: str | None = None
    content_type: str | None = None
    raw_result: dict[str, Any] | None = None


class VoiceExecuteData(BaseModel):
    trace_id: str
    recognition: VoiceRecognitionData
    execution: dict[str, Any] = Field(default_factory=dict)
