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
    duration: float | None = None
    latency_ms: int | None = None
    dialect: str | None = None
    content_type: str | None = None
    raw_result: dict[str, Any] | None = None


class VoiceExecuteData(BaseModel):
    trace_id: str
    recognition: VoiceRecognitionData
    execution: dict[str, Any] = Field(default_factory=dict)


class ASRConfigUpdateRequest(BaseModel):
    provider: str = Field(default="xunfei", max_length=30)
    base_url: str | None = Field(default=None, max_length=300)
    app_id: str | None = Field(default=None, max_length=120)
    api_key: str | None = Field(default=None, max_length=200)
    secret_key: str | None = Field(default=None, max_length=240)
    timeout_seconds: float = Field(default=10, ge=1, le=60)
    enable_cloud: bool = True
