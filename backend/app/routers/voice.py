import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.voice import ASRConfigUpdateRequest
from app.services.asr_providers import ASRProviderError, ASRRecognitionResult
from app.services.asr_config_store import (
    DEFAULT_XUNFEI_BASE_URL,
    delete_asr_file_config,
    load_asr_file_config,
    public_asr_config,
    required_xunfei_fields_missing,
    save_asr_file_config,
)
from app.services.asr_post_corrector import correct_asr_text
from app.services.command_executor import CommandExecutor
from app.services.home_actions import BusinessError
from app.services.personalization import get_or_create_preferences
from app.services.speech_recognition_service import SpeechRecognitionService, generate_voice_trace_id
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/voice", tags=["语音识别"])


def get_speech_recognition_service() -> SpeechRecognitionService:
    return SpeechRecognitionService()


@router.get("/providers", summary="查询语音识别配置状态")
def get_voice_providers(
    current_user: User = Depends(get_current_user),
    service: SpeechRecognitionService = Depends(get_speech_recognition_service),
):
    return success_response(data=service.provider_status(), message="语音识别配置状态")


@router.get("/asr-config", summary="查询本地 ASR 配置")
def get_asr_config(
    current_user: User = Depends(get_current_user),
    service: SpeechRecognitionService = Depends(get_speech_recognition_service),
):
    return success_response(
        data={
            "config": public_asr_config(),
            "provider_status": service.provider_status(),
        },
        message="ASR 配置状态",
    )


@router.post("/asr-config", summary="保存本地 ASR 配置")
def save_asr_config(
    payload: ASRConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    provider = payload.provider.strip().lower()
    if provider == "iflytek":
        provider = "xunfei"
    if provider != "xunfei":
        raise HTTPException(
            status_code=400,
            detail=error_response("ASR_PROVIDER_UNSUPPORTED", "当前前端配置仅支持讯飞 ASR。"),
        )

    existing = load_asr_file_config()
    values = {
        "provider": provider,
        "base_url": payload.base_url or existing.get("base_url") or DEFAULT_XUNFEI_BASE_URL,
        "app_id": payload.app_id,
        "api_key": payload.api_key,
        "secret_key": payload.secret_key,
        "timeout_seconds": payload.timeout_seconds,
        "enable_cloud": payload.enable_cloud,
    }
    merged_preview = {**existing, **{key: value for key, value in values.items() if value not in {None, ""}}}
    missing = required_xunfei_fields_missing(merged_preview)
    if missing or not payload.enable_cloud:
        raise HTTPException(
            status_code=400,
            detail=error_response(
                "ASR_CONFIG_INCOMPLETE",
                "讯飞 ASR 配置不完整，请填写 AppID、APIKey 和 APISecret。",
                {"missing_fields": missing + ([] if payload.enable_cloud else ["ASR_ENABLE_CLOUD=true"])},
            ),
        )

    saved = save_asr_file_config(values)
    return success_response(
        data={
            "config": public_asr_config(saved),
            "provider_status": SpeechRecognitionService().provider_status(),
        },
        message="ASR 配置已保存，云端语音识别已可用。",
    )


@router.delete("/asr-config", summary="清除本地 ASR 配置")
def clear_asr_config(
    current_user: User = Depends(get_current_user),
):
    removed = delete_asr_file_config()
    return success_response(
        data={"removed": removed, "config": public_asr_config({})},
        message="ASR 本地配置已清除。",
    )


@router.post("/recognize", summary="音频转文字")
async def recognize_voice(
    audio: UploadFile | None = File(default=None),
    dialect: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: SpeechRecognitionService = Depends(get_speech_recognition_service),
):
    trace_id = generate_voice_trace_id()
    preference = get_or_create_preferences(db, current_user)
    dialect = dialect or preference.preferred_dialect or "auto"
    audio_bytes = await _read_audio_file(audio)
    try:
        result = service.recognize(
            audio_bytes=audio_bytes,
            filename=audio.filename if audio else None,
            content_type=audio.content_type if audio else None,
            dialect=dialect,
            trace_id=trace_id,
        )
    except ASRProviderError as exc:
        raise _asr_http_exception(exc, trace_id) from exc

    correction = correct_asr_text(result.transcript, db=db, user=current_user)
    return success_response(
        data=_serialize_recognition(result, trace_id, audio.content_type if audio else None, correction.to_dict()),
        message="语音识别成功",
    )


@router.post("/execute", summary="识别并执行语音指令")
async def execute_voice(
    audio: UploadFile | None = File(default=None),
    dialect: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: SpeechRecognitionService = Depends(get_speech_recognition_service),
):
    trace_id = generate_voice_trace_id()
    preference = get_or_create_preferences(db, current_user)
    dialect = dialect or preference.preferred_dialect or "auto"
    audio_bytes = await _read_audio_file(audio)
    try:
        recognition = service.recognize(
            audio_bytes=audio_bytes,
            filename=audio.filename if audio else None,
            content_type=audio.content_type if audio else None,
            dialect=dialect,
            trace_id=trace_id,
        )
    except ASRProviderError as exc:
        raise _asr_http_exception(exc, trace_id) from exc

    correction = correct_asr_text(recognition.transcript, db=db, user=current_user)
    context = _build_voice_context(recognition, trace_id, audio)
    context["dialect"] = dialect
    if correction.changed:
        context["asr_post_correction"] = correction.to_dict()
    executor = CommandExecutor(db=db, user=current_user)
    try:
        execution = executor.execute(recognition.transcript, context=context)
    except BusinessError as exc:
        data = {
            "trace_id": trace_id,
            "recognition": _serialize_recognition(recognition, trace_id, audio.content_type if audio else None, correction.to_dict()),
            "parser_or_execution": exc.data,
        }
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, data),
        ) from exc

    data = {
        "trace_id": trace_id,
        "recognition": _serialize_recognition(recognition, trace_id, audio.content_type if audio else None, correction.to_dict()),
        "execution": execution,
    }
    if execution.get("is_batch") and execution.get("code") != "OK":
        return error_response(execution.get("code", "PARTIAL_SUCCESS"), execution.get("message", "语音批量指令部分成功"), data)
    return success_response(data=data, message=execution.get("message", "语音指令执行成功") if execution.get("is_batch") else "语音指令执行成功")


async def _read_audio_file(audio: UploadFile | None) -> bytes:
    if audio is None:
        raise HTTPException(
            status_code=400,
            detail=error_response("ASR_AUDIO_REQUIRED", "请上传音频文件。"),
        )
    return await audio.read()


def _asr_http_exception(exc: ASRProviderError, trace_id: str) -> HTTPException:
    data = exc.data or {}
    provider_name = data.get("asr_provider") or _current_asr_provider()
    data = {
        **data,
        "trace_id": trace_id,
        "input_source": "cloud_asr",
        "asr_provider": provider_name,
        "success": False,
        "error_code": exc.code,
        "error_message": exc.message,
        "latency_ms": exc.latency_ms,
        "fallback": data.get("fallback") or ["browser_speech", "text_input"],
    }
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(exc.code, exc.message, data),
    )


def _current_asr_provider() -> str:
    provider = os.getenv("ASR_PROVIDER", "cloud").strip().lower() or "cloud"
    if provider in {"xunfei", "iflytek"}:
        return "xunfei"
    return "cloud"


def _serialize_recognition(
    result: ASRRecognitionResult,
    trace_id: str,
    content_type: str | None,
    correction: dict | None = None,
) -> dict:
    data = {
        "trace_id": trace_id,
        "provider": result.provider,
        "transcript": result.transcript,
        "duration": result.duration,
        "latency_ms": result.latency_ms,
        "dialect": result.dialect,
        "content_type": content_type,
        "raw_result": result.raw_result,
        "error": result.error,
    }
    if correction:
        data["corrected_transcript"] = correction.get("corrected_text") or result.transcript
        data["asr_post_correction"] = correction
    return data


def _build_voice_context(
    recognition: ASRRecognitionResult,
    trace_id: str,
    audio: UploadFile | None,
) -> dict:
    return {
        "trace_id": trace_id,
        "input_source": "mock_asr" if recognition.provider == "mock" else "cloud_asr",
        "audio_filename": audio.filename if audio else None,
        "audio_content_type": audio.content_type if audio else None,
        "asr_provider": recognition.provider,
        "transcript": recognition.transcript,
        "audio_duration": recognition.duration,
        "asr_latency_ms": recognition.latency_ms,
        "dialect": recognition.dialect,
        "raw_asr_result": recognition.raw_result,
        "asr_raw_result": recognition.raw_result,
    }
