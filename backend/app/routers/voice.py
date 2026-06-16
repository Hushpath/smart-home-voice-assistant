import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.asr_providers import ASRProviderError, ASRRecognitionResult
from app.services.command_executor import CommandExecutor
from app.services.home_actions import BusinessError
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


@router.post("/recognize", summary="音频转文字")
async def recognize_voice(
    audio: UploadFile | None = File(default=None),
    dialect: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    service: SpeechRecognitionService = Depends(get_speech_recognition_service),
):
    trace_id = generate_voice_trace_id()
    dialect = dialect or "auto"
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

    return success_response(
        data=_serialize_recognition(result, trace_id, audio.content_type if audio else None),
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
    dialect = dialect or "auto"
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

    context = _build_voice_context(recognition, trace_id, audio)
    executor = CommandExecutor(db=db, user=current_user)
    try:
        execution = executor.execute(recognition.transcript, context=context)
    except BusinessError as exc:
        data = {
            "trace_id": trace_id,
            "recognition": _serialize_recognition(recognition, trace_id, audio.content_type if audio else None),
            "parser_or_execution": exc.data,
        }
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, data),
        ) from exc

    return success_response(
        data={
            "trace_id": trace_id,
            "recognition": _serialize_recognition(recognition, trace_id, audio.content_type if audio else None),
            "execution": execution,
        },
        message="语音指令执行成功",
    )


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
) -> dict:
    return {
        "trace_id": trace_id,
        "provider": result.provider,
        "transcript": result.transcript,
        "confidence": result.confidence,
        "duration": result.duration,
        "latency_ms": result.latency_ms,
        "dialect": result.dialect,
        "content_type": content_type,
        "raw_result": result.raw_result,
        "error": result.error,
    }


def _build_voice_context(
    recognition: ASRRecognitionResult,
    trace_id: str,
    audio: UploadFile | None,
) -> dict:
    return {
        "trace_id": trace_id,
        "input_source": "cloud_asr" if recognition.provider == "cloud" else "mock_asr",
        "audio_filename": audio.filename if audio else None,
        "audio_content_type": audio.content_type if audio else None,
        "asr_provider": recognition.provider,
        "transcript": recognition.transcript,
        "asr_confidence": recognition.confidence,
        "audio_duration": recognition.duration,
        "asr_latency_ms": recognition.latency_ms,
        "dialect": recognition.dialect,
        "raw_asr_result": recognition.raw_result,
        "asr_raw_result": recognition.raw_result,
    }
