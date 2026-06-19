from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import CommandLog, User
from app.schemas.command import CommandExecuteRequest, CommandParseRequest
from app.services.asr_post_corrector import correct_asr_text
from app.services.command_executor import CommandExecutor
from app.services.command_parser import CommandParser
from app.services.dialect_normalizer import normalize_and_parse_command
from app.services.home_actions import BusinessError
from app.services.multi_command_parser import MultiCommandParser
from app.services.personalization import get_or_create_preferences
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/commands", tags=["中文指令"])
parser = CommandParser()
multi_parser = MultiCommandParser(parser=parser)
DEVICE_TYPE_LABELS = {
    "desk_lamp": "台灯",
    "bedside_lamp": "床头灯",
    "light": "灯",
    "air_conditioner": "空调",
    "tv": "电视",
    "curtain": "窗帘",
    "fan": "排风扇",
    "robot_vacuum": "扫地机器人",
    "speaker": "音箱",
    "humidifier": "加湿器",
    "air_purifier": "空气净化器",
    "smart_plug": "智能插座",
    "fridge": "冰箱",
    "smoke_sensor": "烟雾传感器",
}


@router.post("/parse", summary="解析中文指令")
def parse_command(
    payload: CommandParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = get_or_create_preferences(db, current_user)
    dialect = payload.dialect or preference.preferred_dialect or "auto"
    correction = correct_asr_text(payload.command, db=db, user=current_user)
    command_for_parse = correction.corrected_text
    batch_result = multi_parser.parse(command_for_parse, dialect=dialect)
    if batch_result.is_batch:
        data = batch_result.to_dict()
        if correction.changed:
            data["original_text"] = payload.command
            data["asr_post_correction"] = correction.to_dict()
        data["preference_used"] = {"preferred_dialect": dialect}
        return success_response(data=data, message="解析成功")

    result, normalization = normalize_and_parse_command(command_for_parse, parser=parser, dialect=dialect)
    if correction.changed:
        result.original_text = payload.command
        result.parse_detail["asr_post_correction"] = correction.to_dict()
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(result.error_code, result.message, result.to_dict()),
        )
    data = result.to_dict()
    if correction.changed:
        data["asr_post_correction"] = correction.to_dict()
    data["normalization"] = normalization.to_dict()
    data["preference_used"] = {"preferred_dialect": dialect}
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
    is_batch = bool(parsed_result.get("is_batch") or execution_result.get("is_batch"))

    return {
        "id": log.id,
        "user_id": log.user_id,
        "trace_id": trace_id,
        "command_text": command_text,
        "input_source": context.get("input_source", "text"),
        "asr_provider": context.get("asr_provider"),
        "intent": "batch" if is_batch else intent,
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
            "batch": _build_batch_detail(parsed_result, execution_result),
            "personalization": _build_personalization_detail(context),
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
    correction = context.get("asr_post_correction") if isinstance(context.get("asr_post_correction"), dict) else {}
    return {
        "trace_id": context.get("trace_id"),
        "input_source": context.get("input_source", "text"),
        "asr_provider": context.get("asr_provider"),
        "transcript": context.get("transcript"),
        "corrected_transcript": correction.get("corrected_text") or context.get("transcript"),
        "asr_post_correction": correction,
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
        "confidence_breakdown": parse_detail.get("confidence_breakdown"),
        "parser_confidence": parsed_result.get("confidence"),
        "matched_keywords": parsed_result.get("matched_keywords") or [],
        "match_type": parsed_result.get("match_type"),
        "message": parsed_result.get("message"),
        "is_batch": parsed_result.get("is_batch", False),
        "command_count": parsed_result.get("command_count"),
        "sub_commands": parsed_result.get("sub_commands") or parse_detail.get("sub_commands") or [],
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
        "is_batch": result.get("is_batch", False),
        "success_count": result.get("success_count"),
        "failed_count": result.get("failed_count"),
        "sub_results": result.get("sub_results") or [],
    }


def _build_batch_detail(parsed_result: dict, execution_result: dict) -> dict:
    return {
        "is_batch": bool(parsed_result.get("is_batch") or execution_result.get("is_batch")),
        "command_count": parsed_result.get("command_count") or execution_result.get("command_count"),
        "success_count": execution_result.get("success_count"),
        "failed_count": execution_result.get("failed_count"),
        "split_detail": (parsed_result.get("parse_detail") or {}).get("batch_split"),
        "sub_commands": parsed_result.get("sub_commands") or [],
        "sub_results": execution_result.get("sub_results") or [],
    }


def _build_personalization_detail(context: dict) -> dict:
    preference_used = context.get("preference_used") if isinstance(context, dict) else {}
    if not isinstance(preference_used, dict):
        preference_used = {}
    return {
        "preference_used": preference_used,
        "preferred_dialect": preference_used.get("preferred_dialect"),
        "alias_match": context.get("alias_match") if isinstance(context, dict) else None,
    }


@router.post("/execute", summary="执行中文指令")
def execute_command(
    payload: CommandExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    executor = CommandExecutor(db=db, user=current_user)
    context = {"dialect": payload.dialect} if payload.dialect else None
    try:
        result = executor.execute(payload.command, context=context)
    except BusinessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, exc.data),
        ) from exc
    if result.get("is_batch"):
        if result.get("code") == "OK":
            return success_response(data=result, message=result.get("message", "批量指令执行成功"))
        return error_response(result.get("code", "PARTIAL_SUCCESS"), result.get("message", "批量指令部分成功"), result)
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
