import os
import time
import json
import base64
import hashlib
import hmac
from email.utils import formatdate
from urllib.parse import urlencode, urlparse
from io import BytesIO
import wave
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.asr_providers.base import ASRProvider, ASRProviderError, ASRRecognitionResult


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class CloudASRConfig:
    provider: str
    base_url: str
    api_key: str
    secret_key: str
    app_id: str
    timeout_seconds: float
    enable_cloud: bool

    @classmethod
    def from_env(cls) -> "CloudASRConfig":
        raw_timeout = os.getenv("ASR_TIMEOUT_SECONDS", "10").strip()
        try:
            timeout_seconds = max(1.0, float(raw_timeout))
        except ValueError:
            timeout_seconds = 10.0
        provider = os.getenv("ASR_PROVIDER", "cloud").strip().lower() or "cloud"
        base_url = os.getenv("ASR_BASE_URL", "").strip()
        if provider in {"xunfei", "iflytek"} and not base_url:
            base_url = "wss://iat-api.xfyun.cn/v2/iat"
        return cls(
            provider=provider,
            base_url=base_url,
            api_key=os.getenv("ASR_API_KEY", "").strip(),
            secret_key=os.getenv("ASR_SECRET_KEY", "").strip(),
            app_id=os.getenv("ASR_APP_ID", "").strip(),
            timeout_seconds=timeout_seconds,
            enable_cloud=_env_bool("ASR_ENABLE_CLOUD", False),
        )

    @property
    def provider_kind(self) -> str:
        if self.provider in {"xunfei", "iflytek"}:
            return "xunfei"
        return "cloud"

    @property
    def has_credentials(self) -> bool:
        if self.provider_kind == "xunfei":
            return bool(self.api_key and self.secret_key and self.app_id)
        return bool(self.api_key or self.secret_key or self.app_id)

    @property
    def missing_fields(self) -> list[str]:
        fields: list[str] = []
        if self.provider_kind not in {"cloud", "xunfei"}:
            fields.append("ASR_PROVIDER=cloud 或 xunfei")
        if not self.enable_cloud:
            fields.append("ASR_ENABLE_CLOUD=true")
        if not self.base_url:
            fields.append("ASR_BASE_URL")
        if self.provider_kind == "xunfei":
            if not self.app_id:
                fields.append("ASR_APP_ID")
            if not self.api_key:
                fields.append("ASR_API_KEY")
            if not self.secret_key:
                fields.append("ASR_SECRET_KEY")
        elif not self.has_credentials:
            fields.append("ASR_API_KEY/ASR_SECRET_KEY/ASR_APP_ID")
        return fields

    @property
    def is_configured(self) -> bool:
        return not self.missing_fields


class CloudASRProvider(ASRProvider):
    """Cloud ASR adapter.

    `ASR_PROVIDER=xunfei` uses Xunfei WebSocket voice dictation. `ASR_PROVIDER=cloud`
    keeps the generic HTTP multipart framework for other vendors or custom proxies.
    """

    @property
    def name(self) -> str:
        return self.config.provider_kind

    @property
    def base_url(self) -> str:
        return self.config.base_url

    @property
    def timeout_seconds(self) -> float:
        return self.config.timeout_seconds

    @property
    def config(self) -> CloudASRConfig:
        return CloudASRConfig.from_env()

    def is_configured(self) -> bool:
        return self.config.is_configured

    def configuration_status(self) -> dict[str, Any]:
        config = self.config
        return {
            "provider": config.provider_kind,
            "configured_provider": config.provider,
            "base_url_configured": bool(config.base_url),
            "credentials_configured": config.has_credentials,
            "app_id_configured": bool(config.app_id),
            "secret_key_configured": bool(config.secret_key),
            "timeout_seconds": config.timeout_seconds,
            "enable_cloud": config.enable_cloud,
            "configured": config.is_configured,
            "missing_fields": config.missing_fields,
        }

    def recognize(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        dialect: str | None,
        trace_id: str,
    ) -> ASRRecognitionResult:
        started_at = time.perf_counter()
        if not self.is_configured():
            raise ASRProviderError(
                "ASR_PROVIDER_NOT_CONFIGURED",
                "云端语音识别服务未配置，请使用浏览器识别或文本输入兜底。",
                status_code=503,
                data={
                    "asr_provider": self.name,
                    "fallback": ["browser_speech", "text_input"],
                    "configuration": self.configuration_status(),
                },
                latency_ms=self._elapsed_ms(started_at),
            )

        if self.name == "xunfei":
            return self._recognize_xunfei(audio_bytes, filename, content_type, dialect, trace_id, started_at)

        try:
            request_kwargs = self._build_request(audio_bytes, filename, content_type, dialect, trace_id)
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(self.base_url, **request_kwargs)
        except httpx.TimeoutException as exc:
            raise ASRProviderError(
                "ASR_TIMEOUT",
                "云端语音识别请求超时，请使用浏览器识别或文本输入兜底。",
                status_code=504,
                data={"asr_provider": self.name, "fallback": ["browser_speech", "text_input"]},
                latency_ms=self._elapsed_ms(started_at),
            ) from exc
        except httpx.HTTPError as exc:
            raise ASRProviderError(
                "ASR_REQUEST_FAILED",
                "云端语音识别请求失败，请稍后重试或使用兜底输入。",
                status_code=502,
                data={"asr_provider": self.name, "fallback": ["browser_speech", "text_input"]},
                latency_ms=self._elapsed_ms(started_at),
            ) from exc

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        self._raise_for_bad_status(response, latency_ms)
        return self._parse_response(response, dialect, latency_ms)

    def _build_request(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        dialect: str | None,
        trace_id: str,
    ) -> dict[str, Any]:
        config = self.config
        headers = {"X-Trace-Id": trace_id}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        if config.app_id:
            headers["X-ASR-App-Id"] = config.app_id

        # TODO: Add vendor-specific signing only after selecting a provider and
        # following its official API documentation.
        return {
            "headers": headers,
            "files": {
                "audio": (
                    filename or "audio",
                    audio_bytes,
                    content_type or "application/octet-stream",
                )
            },
            "data": {
                "dialect": dialect or "",
                "trace_id": trace_id,
                "app_id": config.app_id,
            },
        }

    def _recognize_xunfei(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        dialect: str | None,
        trace_id: str,
        started_at: float,
    ) -> ASRRecognitionResult:
        audio_payload, audio_format, audio_encoding = self._prepare_xunfei_audio(audio_bytes, content_type, started_at)
        try:
            import websocket
        except ImportError as exc:
            raise ASRProviderError(
                "ASR_REQUEST_FAILED",
                "后端缺少讯飞 WebSocket 客户端依赖，请安装 websocket-client。",
                status_code=500,
                data={"asr_provider": self.name},
                latency_ms=self._elapsed_ms(started_at),
            ) from exc

        ws = None
        timeout_errors: tuple[type[BaseException], ...] = (TimeoutError,)
        words: list[str] = []
        raw_messages: list[dict[str, Any]] = []
        try:
            if hasattr(websocket, "WebSocketTimeoutException"):
                timeout_errors = (TimeoutError, websocket.WebSocketTimeoutException)
            ws = websocket.create_connection(self._build_xunfei_url(), timeout=self.timeout_seconds)
            for frame in self._build_xunfei_frames(audio_payload, audio_format, audio_encoding, dialect, trace_id):
                ws.send(json.dumps(frame, ensure_ascii=False))
            while True:
                message = ws.recv()
                payload = json.loads(message)
                raw_messages.append(payload)
                code = payload.get("code", 0)
                if code != 0:
                    raise ASRProviderError(
                        "ASR_REQUEST_FAILED",
                        payload.get("message") or "讯飞语音识别服务返回错误。",
                        status_code=502,
                        data={"asr_provider": self.name, "raw_result": payload},
                        latency_ms=self._elapsed_ms(started_at),
                    )
                result = payload.get("data", {}).get("result", {})
                words.extend(self._extract_xunfei_words(result))
                if payload.get("data", {}).get("status") == 2:
                    break
        except timeout_errors as exc:
            raise ASRProviderError(
                "ASR_TIMEOUT",
                "讯飞语音识别请求超时，请使用浏览器识别或文本输入兜底。",
                status_code=504,
                data={"asr_provider": self.name, "fallback": ["browser_speech", "text_input"]},
                latency_ms=self._elapsed_ms(started_at),
            ) from exc
        except ASRProviderError:
            raise
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ASRProviderError(
                "ASR_INVALID_RESPONSE",
                "讯飞语音识别返回结构不符合预期。",
                status_code=502,
                data={"asr_provider": self.name, "raw_result": raw_messages[-1] if raw_messages else None},
                latency_ms=self._elapsed_ms(started_at),
            ) from exc
        except Exception as exc:
            raise ASRProviderError(
                "ASR_REQUEST_FAILED",
                "讯飞语音识别请求失败，请稍后重试或使用兜底输入。",
                status_code=502,
                data={"asr_provider": self.name, "fallback": ["browser_speech", "text_input"]},
                latency_ms=self._elapsed_ms(started_at),
            ) from exc
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass

        latency_ms = self._elapsed_ms(started_at)
        transcript = "".join(words).strip()
        if not transcript:
            raise ASRProviderError(
                "ASR_EMPTY_TRANSCRIPT",
                "讯飞语音识别未返回有效文本，请使用浏览器识别或文本输入兜底。",
                status_code=422,
                data={"asr_provider": self.name, "raw_result": {"messages": raw_messages}},
                latency_ms=latency_ms,
            )

        return ASRRecognitionResult(
            provider=self.name,
            transcript=transcript,
            confidence=None,
            duration=None,
            latency_ms=latency_ms,
            dialect=dialect,
            raw_result={
                "vendor": "xunfei",
                "sid": raw_messages[-1].get("sid") if raw_messages else None,
                "messages": raw_messages,
                "audio_format": audio_format,
                "audio_encoding": audio_encoding,
            },
            error=None,
        )

    def _prepare_xunfei_audio(
        self,
        audio_bytes: bytes,
        content_type: str | None,
        started_at: float,
    ) -> tuple[bytes, str, str]:
        normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
        if normalized_type == "audio/mpeg":
            return audio_bytes, "audio/L16;rate=16000", "lame"
        if normalized_type == "audio/wav":
            return self._wav_to_pcm(audio_bytes), "audio/L16;rate=16000", "raw"
        raise ASRProviderError(
            "ASR_UNSUPPORTED_AUDIO_FORMAT",
            "讯飞语音听写当前仅支持 wav 或 mp3，请使用浏览器识别或文本输入兜底。",
            status_code=415,
            data={
                "asr_provider": self.name,
                "content_type": content_type,
                "supported_types": ["audio/wav", "audio/mpeg"],
                "fallback": ["browser_speech", "text_input"],
            },
            latency_ms=self._elapsed_ms(started_at),
        )

    def _wav_to_pcm(self, audio_bytes: bytes) -> bytes:
        if not audio_bytes.startswith(b"RIFF"):
            return audio_bytes
        with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
            return wav_file.readframes(wav_file.getnframes())

    def _build_xunfei_url(self) -> str:
        config = self.config
        parsed = urlparse(config.base_url)
        host = parsed.netloc
        path = parsed.path or "/v2/iat"
        date = formatdate(timeval=None, localtime=False, usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            config.secret_key.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{config.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        query = urlencode({"authorization": authorization, "date": date, "host": host})
        return f"{config.base_url}?{query}"

    def _build_xunfei_frames(
        self,
        audio_bytes: bytes,
        audio_format: str,
        audio_encoding: str,
        dialect: str | None,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        config = self.config
        chunk_size = 1280
        chunks = [audio_bytes[index : index + chunk_size] for index in range(0, len(audio_bytes), chunk_size)] or [b""]
        frames: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            status = 0 if index == 0 else 1
            if index == len(chunks) - 1 and index > 0:
                status = 2
            frame: dict[str, Any] = {
                "data": {
                    "status": status,
                    "format": audio_format,
                    "encoding": audio_encoding,
                    "audio": base64.b64encode(chunk).decode("utf-8"),
                }
            }
            if index == 0:
                frame["common"] = {"app_id": config.app_id}
                frame["business"] = {
                    "language": "zh_cn",
                    "domain": "iat",
                    "accent": self._xunfei_accent(dialect),
                    "vinfo": 1,
                    "trace_id": trace_id,
                }
            frames.append(frame)
        if len(frames) == 1:
            frames.append(
                {
                    "data": {
                        "status": 2,
                        "format": audio_format,
                        "encoding": audio_encoding,
                        "audio": "",
                    }
                }
            )
        return frames

    def _xunfei_accent(self, dialect: str | None) -> str:
        if dialect == "cantonese":
            return "cantonese"
        return "mandarin"

    def _extract_xunfei_words(self, result: dict[str, Any]) -> list[str]:
        words: list[str] = []
        for item in result.get("ws", []):
            candidates = item.get("cw", [])
            if candidates:
                words.append(str(candidates[0].get("w", "")))
        return words

    def _raise_for_bad_status(self, response: httpx.Response, latency_ms: int) -> None:
        if response.status_code in {401, 403}:
            raise ASRProviderError(
                "ASR_AUTH_FAILED",
                "云端语音识别认证失败，请检查后端 ASR 配置。",
                status_code=502,
                data={"status_code": response.status_code},
                latency_ms=latency_ms,
            )
        if response.status_code >= 400:
            raise ASRProviderError(
                "ASR_REQUEST_FAILED",
                "云端语音识别服务返回错误，请稍后重试。",
                status_code=502,
                data={"status_code": response.status_code},
                latency_ms=latency_ms,
            )

    def _parse_response(self, response: httpx.Response, dialect: str | None, latency_ms: int) -> ASRRecognitionResult:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ASRProviderError(
                "ASR_INVALID_RESPONSE",
                "云端语音识别返回了无法解析的结果。",
                status_code=502,
                latency_ms=latency_ms,
            ) from exc

        if not isinstance(payload, dict):
            raise ASRProviderError(
                "ASR_INVALID_RESPONSE",
                "云端语音识别返回结构不符合预期。",
                status_code=502,
                data={"raw_result": payload},
                latency_ms=latency_ms,
            )

        if "transcript" not in payload and "text" not in payload:
            raise ASRProviderError(
                "ASR_INVALID_RESPONSE",
                "云端语音识别返回缺少 transcript/text 字段。",
                status_code=502,
                data={"raw_result": payload},
                latency_ms=latency_ms,
            )

        transcript = str(payload.get("transcript") or payload.get("text") or "").strip()
        if not transcript:
            raise ASRProviderError(
                "ASR_EMPTY_TRANSCRIPT",
                "云端语音识别未返回有效文本，请使用浏览器识别或文本输入兜底。",
                status_code=422,
                data={"raw_result": payload},
                latency_ms=latency_ms,
            )

        confidence = payload.get("confidence")
        duration = payload.get("duration")
        return ASRRecognitionResult(
            provider=self.name,
            transcript=transcript,
            confidence=confidence if isinstance(confidence, (int, float)) else None,
            duration=duration if isinstance(duration, (int, float)) else None,
            latency_ms=latency_ms,
            dialect=dialect,
            raw_result=payload,
            error=None,
        )

    def _elapsed_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)
