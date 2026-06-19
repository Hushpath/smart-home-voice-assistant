from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CommandLog, Device, DeviceAlias, Room, User, UserPreference
from app.services.command_parser import ParseResult
from app.services.home_actions import BusinessError


DEFAULT_PREFERENCES = {
    "preferred_dialect": "auto",
    "preferred_input_mode": "browser_speech",
}

SUPPORTED_DIALECTS = {"auto", "mandarin", "cantonese", "southwest", "northeast"}
SUPPORTED_INPUT_MODES = {"cloud_asr", "browser_speech", "text"}
SUGGESTION_MIN_COUNT = 3
SUGGESTION_MIN_RATIO = 0.6


def get_or_create_preferences(db: Session, user: User) -> UserPreference:
    preference = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if preference is not None:
        return preference
    preference = UserPreference(user_id=user.id, **DEFAULT_PREFERENCES)
    db.add(preference)
    db.commit()
    db.refresh(preference)
    return preference


def serialize_preferences(preference: UserPreference) -> dict[str, Any]:
    return {
        "id": preference.id,
        "user_id": preference.user_id,
        "preferred_dialect": preference.preferred_dialect or DEFAULT_PREFERENCES["preferred_dialect"],
        "preferred_input_mode": preference.preferred_input_mode or DEFAULT_PREFERENCES["preferred_input_mode"],
        "created_at": preference.created_at.isoformat() if preference.created_at else None,
        "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
    }


def serialize_alias(alias: DeviceAlias) -> dict[str, Any]:
    device = alias.device
    room = device.room if device else None
    return {
        "id": alias.id,
        "device_id": alias.device_id,
        "device_name": device.name if device else None,
        "room_name": room.name if room else None,
        "device_type": device.device_type if device else None,
        "alias": alias.alias,
        "created_at": alias.created_at.isoformat() if alias.created_at else None,
        "updated_at": alias.updated_at.isoformat() if alias.updated_at else None,
    }


def list_aliases_for_user(db: Session, user: User) -> list[DeviceAlias]:
    query = db.query(DeviceAlias).join(Device).join(Room).filter(DeviceAlias.user_id == user.id)
    if user.home_id is not None:
        query = query.filter(Room.home_id == user.home_id)
    return query.order_by(DeviceAlias.id.desc()).all()


def get_device_for_user(db: Session, user: User, device_id: int) -> Device:
    device = db.query(Device).join(Room).filter(Device.id == device_id).first()
    if device is None or (user.home_id is not None and device.room.home_id != user.home_id):
        raise BusinessError("DEVICE_NOT_FOUND", "未找到指定设备", status_code=404)
    return device


def create_device_alias(db: Session, user: User, device_id: int, alias_text: str) -> DeviceAlias:
    alias_text = alias_text.strip()
    get_device_for_user(db, user, device_id)
    existing = (
        db.query(DeviceAlias)
        .filter(DeviceAlias.user_id == user.id, func.lower(DeviceAlias.alias) == alias_text.lower())
        .first()
    )
    if existing is not None:
        raise BusinessError("DEVICE_ALIAS_EXISTS", "该别名已存在")
    alias = DeviceAlias(user_id=user.id, device_id=device_id, alias=alias_text)
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


def delete_device_alias(db: Session, user: User, alias_id: int) -> None:
    alias = db.query(DeviceAlias).filter(DeviceAlias.id == alias_id, DeviceAlias.user_id == user.id).first()
    if alias is None:
        raise BusinessError("DEVICE_ALIAS_NOT_FOUND", "未找到指定设备别名", status_code=404)
    db.delete(alias)
    db.commit()


def match_device_alias(db: Session, user: User, text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    aliases = list_aliases_for_user(db, user)
    for alias in sorted(aliases, key=lambda item: len(item.alias or ""), reverse=True):
        if alias.alias and alias.alias in text:
            device = alias.device
            room = device.room if device else None
            return {
                "alias": alias.alias,
                "device_id": alias.device_id,
                "device_name": device.name if device else None,
                "room": room.name if room else None,
                "device_type": device.device_type if device else None,
                "match_type": "user_alias",
            }
    return None


def apply_alias_to_parsed(parsed: ParseResult, alias_match: dict[str, Any] | None) -> None:
    if not alias_match:
        return
    parsed.room = alias_match.get("room") or parsed.room
    parsed.device_type = alias_match.get("device_type") or parsed.device_type
    parsed.match_type = "user_alias"
    if alias_match.get("alias") not in parsed.matched_keywords:
        parsed.matched_keywords.append(alias_match["alias"])
    parsed.parse_detail["alias_match"] = alias_match


def preference_context(preference: UserPreference) -> dict[str, Any]:
    return {
        "preferred_dialect": preference.preferred_dialect or DEFAULT_PREFERENCES["preferred_dialect"],
        "preferred_input_mode": preference.preferred_input_mode or DEFAULT_PREFERENCES["preferred_input_mode"],
    }


def list_frequent_commands(db: Session, user: User, limit: int = 5) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 10))
    logs = (
        db.query(CommandLog)
        .filter(CommandLog.user_id == user.id, CommandLog.success.is_(True), CommandLog.raw_command != "")
        .order_by(CommandLog.id.desc())
        .all()
    )
    grouped: dict[str, dict[str, Any]] = {}
    for log in logs:
        command = _command_group_key(log)
        if not command:
            continue
        item = grouped.setdefault(
            command,
            {"command": command, "count": 0, "last_used_at": None, "last_success": True},
        )
        item["count"] += 1
        if item["last_used_at"] is None:
            item["last_used_at"] = log.created_at.isoformat() if log.created_at else None
            item["last_success"] = bool(log.success)

    return sorted(grouped.values(), key=lambda item: (item["count"], item["last_used_at"] or ""), reverse=True)[:safe_limit]


def build_preference_suggestions(db: Session, user: User, limit: int = 20) -> dict[str, Any]:
    preference = get_or_create_preferences(db, user)
    safe_limit = max(5, min(limit, 50))
    logs = (
        db.query(CommandLog)
        .filter(CommandLog.user_id == user.id, CommandLog.success.is_(True), CommandLog.raw_command != "")
        .order_by(CommandLog.id.desc())
        .limit(safe_limit)
        .all()
    )
    return {
        "window_size": safe_limit,
        "sample_count": len(logs),
        "dialect": _build_dialect_suggestion(logs, preference),
        "input_mode": _build_input_mode_suggestion(logs, preference),
    }


def _command_group_key(log: CommandLog) -> str:
    parsed = log.parsed_result or {}
    command = parsed.get("normalized_text") or parsed.get("original_text") or log.raw_command
    return command.strip() if isinstance(command, str) else ""


def _build_dialect_suggestion(logs: list[CommandLog], preference: UserPreference) -> dict[str, Any]:
    counts: dict[str, int] = {}
    samples: list[str] = []
    for log in logs:
        dialect = _extract_detected_dialect(log)
        if dialect not in SUPPORTED_DIALECTS:
            continue
        counts[dialect] = counts.get(dialect, 0) + 1
        if len(samples) < 3:
            samples.append(log.raw_command)
    current = preference.preferred_dialect or DEFAULT_PREFERENCES["preferred_dialect"]
    return _build_suggestion(
        kind="dialect",
        current=current,
        counts=counts,
        total=sum(counts.values()),
        samples=samples,
        label_map={
            "auto": "自动",
            "mandarin": "普通话",
            "cantonese": "粤语",
            "southwest": "西南口音",
            "northeast": "东北口语",
        },
        payload_key="preferred_dialect",
    )


def _build_input_mode_suggestion(logs: list[CommandLog], preference: UserPreference) -> dict[str, Any]:
    counts: dict[str, int] = {}
    samples: list[str] = []
    for log in logs:
        input_mode = _extract_input_mode(log)
        if input_mode not in SUPPORTED_INPUT_MODES:
            continue
        counts[input_mode] = counts.get(input_mode, 0) + 1
        if len(samples) < 3:
            samples.append(log.raw_command)
    current = preference.preferred_input_mode or DEFAULT_PREFERENCES["preferred_input_mode"]
    return _build_suggestion(
        kind="input_mode",
        current=current,
        counts=counts,
        total=sum(counts.values()),
        samples=samples,
        label_map={
            "cloud_asr": "云端 ASR",
            "browser_speech": "浏览器识别",
            "text": "文本输入",
        },
        payload_key="preferred_input_mode",
    )


def _build_suggestion(
    kind: str,
    current: str,
    counts: dict[str, int],
    total: int,
    samples: list[str],
    label_map: dict[str, str],
    payload_key: str,
) -> dict[str, Any]:
    if not counts or total == 0:
        return {
            "current": current,
            "suggested": None,
            "confidence": 0,
            "counts": counts,
            "reason": "暂无足够成功日志用于自动学习",
            "can_apply": False,
            "apply_payload": {},
            "samples": samples,
        }
    suggested, matched_count = sorted(counts.items(), key=lambda item: item[1], reverse=True)[0]
    confidence = round(matched_count / total, 2)
    label = label_map.get(suggested, suggested)
    can_apply = matched_count >= SUGGESTION_MIN_COUNT and confidence >= SUGGESTION_MIN_RATIO and suggested != current
    if can_apply:
        reason = f"最近成功指令中 {matched_count}/{total} 条更符合{label}，建议设为{label}"
    elif suggested == current:
        reason = f"当前设置已符合最近使用习惯：{label}"
    else:
        reason = f"最近样本不足或占比不够，暂不建议自动调整{kind}"
    return {
        "current": current,
        "suggested": suggested,
        "confidence": confidence,
        "counts": counts,
        "reason": reason,
        "can_apply": can_apply,
        "apply_payload": {payload_key: suggested} if can_apply else {},
        "samples": samples,
    }


def _extract_detected_dialect(log: CommandLog) -> str | None:
    context = _extract_context(log)
    normalization = context.get("normalization")
    if not isinstance(normalization, dict):
        parse_detail = (log.parsed_result or {}).get("parse_detail") if isinstance(log.parsed_result, dict) else {}
        normalization = parse_detail.get("dialect_normalization") if isinstance(parse_detail, dict) else {}
    if isinstance(normalization, dict):
        detected = normalization.get("detected_dialect")
        if isinstance(detected, str) and detected:
            return detected
    preference_used = context.get("preference_used")
    if isinstance(preference_used, dict):
        dialect = preference_used.get("preferred_dialect")
        if isinstance(dialect, str) and dialect:
            return dialect
    dialect = context.get("dialect")
    return dialect if isinstance(dialect, str) else None


def _extract_input_mode(log: CommandLog) -> str | None:
    context = _extract_context(log)
    source = context.get("input_source")
    if source == "mock_asr":
        return "cloud_asr"
    if source in SUPPORTED_INPUT_MODES:
        return source
    return None


def _extract_context(log: CommandLog) -> dict[str, Any]:
    context: dict[str, Any] = {}
    parsed_context = (log.parsed_result or {}).get("context") if isinstance(log.parsed_result, dict) else None
    execution_context = (log.execution_result or {}).get("context") if isinstance(log.execution_result, dict) else None
    if isinstance(parsed_context, dict):
        context.update(parsed_context)
    if isinstance(execution_context, dict):
        context.update(execution_context)
    return context
