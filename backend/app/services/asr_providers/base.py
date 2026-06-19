from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ASRRecognitionResult:
    provider: str
    transcript: str = ""
    duration: float | None = None
    latency_ms: int | None = None
    dialect: str | None = None
    raw_result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ASRProviderError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        data: dict[str, Any] | None = None,
        latency_ms: int | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        self.latency_ms = latency_ms


class ASRProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def recognize(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        dialect: str | None,
        trace_id: str,
    ) -> ASRRecognitionResult:
        raise NotImplementedError
