from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import CommandLog, User
from app.schemas.command import CommandExecuteRequest, CommandParseRequest
from app.services.command_executor import CommandExecutor
from app.services.command_parser import CommandParser
from app.services.dialect_normalizer import normalize_and_parse_command
from app.services.home_actions import BusinessError
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/commands", tags=["中文指令"])
parser = CommandParser()
DEVICE_TYPE_LABELS = {
    "light": "灯",
    "air_conditioner": "空调",
    "tv": "电视",
    "curtain": "窗帘",
    "fan": "排风扇",
}


@router.post("/parse", summary="解析中文指令")
def parse_command(
    payload: CommandParseRequest,
    current_user: User = Depends(get_current_user),
):
    result, normalization = normalize_and_parse_command(payload.command, parser=parser, dialect="auto")
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(result.error_code, result.message, result.to_dict()),
        )
    data = result.to_dict()
    data["normalization"] = normalization.to_dict()
    return success_response(data=data, message="解析成功")


def serialize_command_log(log: CommandLog) -> dict:
    parsed_result = log.parsed_result or {}
    execution_result = log.execution_result or {}
    context = _extract_log_context(parsed_result, execution_result)
    normalization = _extract_normalization(parsed_result, context)
    parse_detail = parsed_result.get("parse_detail") or {}
    execution_detail = _build_execution_detail(log, execution_result)
    trace_id = context.get("trace_id")
    confidence = parsed_result.get("confidence")
    message = execution_detail.get("message") or log.error_message or parsed_result.get("message")
    command_text = parsed_result.get("original_text") or log.raw_command
    intent = parsed_result.get("intent")
    device_type = parsed_result.get("device_type")

    return {
        "id": log.id,
        "user_id": log.user_id,
        "trace_id": trace_id,
        "command_text": command_text,
        "input_source": context.get("input_source", "text"),
        "asr_provider": context.get("asr_provider"),
        "intent": intent,
        "room": parsed_result.get("room"),
        "device_type": DEVICE_TYPE_LABELS.get(device_type, device_type),
        "confidence": confidence,
        "message": message,
        "raw_command": log.raw_command,
        "parsed_result": parsed_result,
        "execution_result": execution_result,
        "success": log.success,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "detail": {
            "asr": _build_asr_detail(context),
            "normalization": normalization,
            "parse": _build_parse_detail(parsed_result, parse_detail),
            "execution": execution_detail,
            "raw": {
                "parsed_result": parsed_result,
                "execution_result": execution_result,
                "context": context,
            },
        },
    }


def _extract_log_context(parsed_result: dict, execution_result: dict) -> dict:
    parsed_context = parsed_result.get("context") if isinstance(parsed_result, dict) else None
    execution_context = execution_result.get("context") if isinstance(execution_result, dict) else None
    context = {}
    if isinstance(parsed_context, dict):
        context.update(parsed_context)
    if isinstance(execution_context, dict):
        context.update(execution_context)
    return context


def _extract_normalization(parsed_result: dict, context: dict) -> dict:
    parse_detail = parsed_result.get("parse_detail") or {}
    normalization = context.get("normalization") or parse_detail.get("dialect_normalization") or {}
    return normalization if isinstance(normalization, dict) else {}


def _build_asr_detail(context: dict) -> dict:
    raw_result = context.get("raw_asr_result", context.get("asr_raw_result"))
    return {
        "trace_id": context.get("trace_id"),
        "input_source": context.get("input_source", "text"),
        "asr_provider": context.get("asr_provider"),
        "transcript": context.get("transcript"),
        "asr_confidence": context.get("asr_confidence"),
        "audio_duration": context.get("audio_duration"),
        "asr_latency_ms": context.get("asr_latency_ms"),
        "raw_asr_result": raw_result,
    }


def _build_parse_detail(parsed_result: dict, parse_detail: dict) -> dict:
    return {
        "intent": parsed_result.get("intent"),
        "room": parsed_result.get("room"),
        "device_type": parsed_result.get("device_type"),
        "value": parsed_result.get("value"),
        "scene": parsed_result.get("scene"),
        "reminder_time": parsed_result.get("reminder_time"),
        "reminder_content": parsed_result.get("reminder_content"),
        "city": parsed_result.get("city"),
        "intent_scores": parse_detail.get("intent_scores"),
        "parser_confidence": parsed_result.get("confidence"),
        "matched_keywords": parsed_result.get("matched_keywords") or [],
        "match_type": parsed_result.get("match_type"),
        "message": parsed_result.get("message"),
    }


def _build_execution_detail(log: CommandLog, execution_result: dict) -> dict:
    result = execution_result if isinstance(execution_result, dict) else {}
    changes = result.get("changes") or []
    affected_devices = []
    if result.get("device"):
        affected_devices.append(result["device"])
    if changes:
        affected_devices.extend([change.get("device") for change in changes if change.get("device")])
    return {
        "success": log.success,
        "code": result.get("code") or ("OK" if log.success else result.get("error_code") or "ERROR"),
        "message": result.get("message") or log.error_message or ("指令执行成功" if log.success else "指令执行失败"),
        "device_before": result.get("before_state"),
        "device_after": result.get("after_state"),
        "affected_devices": affected_devices,
        "error_code": result.get("error_code"),
        "error_message": result.get("error_message") or log.error_message,
        "execution_latency_ms": result.get("execution_latency_ms"),
    }


@router.post("/execute", summary="执行中文指令")
def execute_command(
    payload: CommandExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    executor = CommandExecutor(db=db, user=current_user)
    try:
        result = executor.execute(payload.command)
    except BusinessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, exc.data),
        ) from exc
    return success_response(data=result, message="指令执行成功")


@router.get("/logs", summary="查询指令执行日志")
def list_command_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = (
        db.query(CommandLog)
        .filter(CommandLog.user_id == current_user.id)
        .order_by(CommandLog.id.desc())
        .all()
    )
    return success_response(data=[serialize_command_log(log) for log in logs])
