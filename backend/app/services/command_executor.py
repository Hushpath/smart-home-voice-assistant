import secrets
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import CommandLog, Reminder, Scene, User
from app.services.asr_post_corrector import correct_asr_text
from app.services.command_parser import CommandParser, ParseResult
from app.services.dialect_normalizer import normalize_and_parse_command
from app.services.home_actions import (
    BusinessError,
    apply_device_state,
    find_device,
    get_weather,
    list_room_devices,
    run_scene_actions,
)
from app.services.device_capabilities import get_property_capability
from app.services.multi_command_parser import MultiCommandParser, MultiCommandParseResult
from app.services.personalization import (
    apply_alias_to_parsed,
    get_device_for_user,
    get_or_create_preferences,
    match_device_alias,
    preference_context,
)


class CommandExecutor:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.preference = get_or_create_preferences(db, user)
        self.parser = CommandParser()
        self.multi_parser = MultiCommandParser(parser=self.parser)

    def execute(self, command: str | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        started_at = time.perf_counter()
        context = self._prepare_personal_context(context)
        dialect = context["dialect"]
        corrected_command = self._apply_asr_post_correction(command, context)
        command_for_parse, alias_match = self._rewrite_alias_command(corrected_command)
        if alias_match:
            context["alias_match"] = alias_match
        multi_parsed = self.multi_parser.parse(command_for_parse, dialect=dialect)
        if multi_parsed.is_batch:
            return self._execute_batch(command, multi_parsed, context, started_at)

        parsed, normalization = normalize_and_parse_command(command_for_parse, parser=self.parser, dialect=dialect)
        if command_for_parse != (command or ""):
            parsed.original_text = command or ""
            if corrected_command != (command or ""):
                parsed.parse_detail["asr_post_correction"] = context.get("asr_post_correction")
            if command_for_parse != corrected_command:
                parsed.parse_detail["alias_rewrite"] = {
                    "raw_command": command or "",
                    "corrected_command": corrected_command,
                    "rewritten_command": command_for_parse,
                }
        apply_alias_to_parsed(parsed, alias_match)
        enriched_context = self._merge_normalization_context(context, normalization.to_dict())
        if not parsed.valid:
            self._write_log(
                command,
                parsed,
                None,
                False,
                parsed.message,
                enriched_context,
                code=parsed.error_code,
                message=parsed.message,
                execution_latency_ms=self._elapsed_ms(started_at),
            )
            raise BusinessError(parsed.error_code, parsed.message, data=parsed.to_dict())

        try:
            result = self._execute_parsed(parsed)
        except BusinessError as exc:
            self._write_log(
                command,
                parsed,
                exc.data,
                False,
                exc.message,
                enriched_context,
                code=exc.code,
                message=exc.message,
                execution_latency_ms=self._elapsed_ms(started_at),
            )
            raise

        self._write_log(
            command,
            parsed,
            result,
            True,
            None,
            enriched_context,
            code="OK",
            message="指令执行成功",
            execution_latency_ms=self._elapsed_ms(started_at),
        )
        self.db.commit()
        return self._build_execute_response(parsed, result, enriched_context)

    def _execute_batch(
        self,
        command: str | None,
        multi_parsed: MultiCommandParseResult,
        context: dict[str, Any] | None,
        started_at: float,
    ) -> dict[str, Any]:
        enriched_context = self._merge_normalization_context(context, multi_parsed.normalization)
        enriched_context["batch"] = {
            "is_batch": True,
            "command_count": multi_parsed.command_count,
            "split_detail": multi_parsed.split_detail,
        }

        sub_results: list[dict[str, Any]] = []
        success_count = 0
        failed_count = 0
        for item in multi_parsed.sub_commands:
            parsed = item.parsed
            if not parsed.valid:
                failed_count += 1
                sub_results.append(self._build_failed_sub_result(item.index, item.text, parsed.error_code, parsed.message, parsed))
                continue
            try:
                execution_result = self._execute_parsed(parsed)
                success_count += 1
                sub_results.append(self._build_success_sub_result(item.index, item.text, parsed, execution_result))
            except BusinessError as exc:
                failed_count += 1
                sub_results.append(self._build_failed_sub_result(item.index, item.text, exc.code, exc.message, parsed, exc.data))

        if failed_count == 0:
            code = "OK"
        elif success_count > 0:
            code = "PARTIAL_SUCCESS"
        else:
            code = "BATCH_FAILED"
        message = f"已执行 {multi_parsed.command_count} 条指令，成功 {success_count} 条，失败 {failed_count} 条"
        success = failed_count == 0
        latency_ms = self._elapsed_ms(started_at)

        response = {
            "is_batch": True,
            "code": code,
            "message": message,
            "command_count": multi_parsed.command_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "sub_commands": [item.to_dict() for item in multi_parsed.sub_commands],
            "sub_results": sub_results,
            "trace_id": enriched_context.get("trace_id"),
            "context": enriched_context,
            "normalization": enriched_context.get("normalization"),
        }
        self._write_batch_log(command, multi_parsed, response, success, None if success else message, enriched_context, latency_ms)
        self.db.commit()
        return response

    def _execute_parsed(self, parsed: ParseResult) -> dict[str, Any]:
        if parsed.intent == "turn_on":
            return self._set_power(parsed, True)
        if parsed.intent == "turn_off":
            return self._set_power(parsed, False)
        if parsed.intent == "set_temperature":
            return self._set_property(parsed, "temperature", "温度")
        if parsed.intent == "set_brightness":
            return self._set_property(parsed, "brightness", "亮度")
        if parsed.intent == "set_volume":
            return self._set_property(parsed, "volume", "音量")
        if parsed.intent == "set_property":
            return self._set_property(parsed, parsed.property_name, "参数")
        if parsed.intent == "query_status":
            return {
                "devices": [
                    {
                        "id": device.id,
                        "name": device.name,
                        "device_type": device.device_type,
                        "room_name": device.room.name if device.room else None,
                        "is_on": device.is_on,
                        "is_online": device.is_online,
                        "properties": device.properties or {},
                    }
                    for device in list_room_devices(self.db, self.user, parsed.room)
                ]
            }
        if parsed.intent == "run_scene":
            return self._run_scene(parsed)
        if parsed.intent == "create_reminder":
            return self._create_reminder(parsed)
        if parsed.intent == "query_weather":
            return {"weather": get_weather(parsed.city)}
        raise BusinessError("UNSUPPORTED_ACTION", "暂不支持该操作")

    def _set_power(self, parsed: ParseResult, is_on: bool) -> dict[str, Any]:
        device = self._find_target_device(parsed)
        return apply_device_state(
            db=self.db,
            device=device,
            user=self.user,
            state_update={"is_on": is_on},
            change_source="command",
        )

    def _set_property(
        self,
        parsed: ParseResult,
        property_name: str | None,
        fallback_label: str,
    ) -> dict[str, Any]:
        if not parsed.device_type:
            raise BusinessError("INVALID_COMMAND", "未识别到要控制的设备")
        capability = get_property_capability(parsed.device_type, property_name)
        label = capability.label if capability else fallback_label
        if capability is None:
            raise BusinessError("UNSUPPORTED_ACTION", f"该设备不支持设置{label}")
        value = parsed.property_value if parsed.property_value is not None else parsed.value
        value = self._validate_property_value(capability, value)
        device = self._find_target_device(parsed)
        return apply_device_state(
            db=self.db,
            device=device,
            user=self.user,
            state_update={"properties": {property_name: value}},
            change_source="command",
        )

    def _validate_property_value(self, capability, value: Any) -> Any:
        if capability.value_type == "number":
            if not isinstance(value, int) or value < capability.minimum or value > capability.maximum:
                raise BusinessError("VALUE_OUT_OF_RANGE", f"{capability.label}必须在 {capability.minimum}-{capability.maximum} 范围内")
            return value
        if capability.value_type == "enum":
            if value not in capability.options:
                options = "、".join(str(option) for option in capability.options)
                raise BusinessError("INVALID_PROPERTY_VALUE", f"{capability.label}仅支持 {options}")
            return value
        raise BusinessError("UNSUPPORTED_ACTION", "暂不支持该参数类型")

    def _run_scene(self, parsed: ParseResult) -> dict[str, Any]:
        scene = (
            self.db.query(Scene)
            .filter(Scene.name == parsed.scene, Scene.home_id == self.user.home_id)
            .first()
        )
        if scene is None:
            raise BusinessError("SCENE_NOT_FOUND", "未找到指定场景", status_code=404)
        return {
            "scene": {"id": scene.id, "name": scene.name},
            "changes": run_scene_actions(self.db, self.user, scene, "scene"),
        }

    def _create_reminder(self, parsed: ParseResult) -> dict[str, Any]:
        reminder = Reminder(
            user_id=self.user.id,
            title=parsed.reminder_content or "",
            remind_time=self._time_to_datetime(parsed.reminder_time),
            is_done=False,
        )
        self.db.add(reminder)
        self.db.flush()
        return {
            "reminder": {
                "id": reminder.id,
                "title": reminder.title,
                "remind_time": reminder.remind_time.isoformat() if reminder.remind_time else None,
                "is_done": reminder.is_done,
            }
        }

    def _time_to_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        hour, minute = [int(part) for part in value.split(":", 1)]
        now = datetime.now()
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _build_execute_response(
        self,
        parsed: ParseResult,
        result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response: dict[str, Any] = {
            "parsed": parsed.to_dict(),
            "result": result,
            "device_before": result.get("before_state"),
            "device_after": result.get("after_state"),
            "affected_devices": [],
            "reminder": result.get("reminder"),
            "weather": result.get("weather"),
            "scene": result.get("scene"),
        }
        if result.get("device"):
            response["affected_devices"] = [result["device"]]
        if result.get("changes"):
            response["affected_devices"] = [change.get("device") for change in result["changes"] if change.get("device")]
        if context:
            response["context"] = context
            if context.get("normalization"):
                response["normalization"] = context["normalization"]
            if context.get("trace_id"):
                response["trace_id"] = context["trace_id"]
            preference_used = context.get("preference_used") or {}
            response["alias_match"] = context.get("alias_match")
            response["preference_used"] = preference_used
        return response

    def _write_log(
        self,
        command: str | None,
        parsed: ParseResult,
        execution_result: dict[str, Any] | None,
        success: bool,
        error_message: str | None,
        context: dict[str, Any] | None = None,
        code: str = "OK",
        message: str | None = None,
        execution_latency_ms: int | None = None,
    ) -> None:
        parsed_result = parsed.to_dict()
        if context:
            parsed_result["context"] = context

        log_execution_result = dict(execution_result) if isinstance(execution_result, dict) else {}
        log_execution_result.update(
            {
                "success": success,
                "code": code,
                "message": message or error_message or ("指令执行成功" if success else "指令执行失败"),
                "error_code": None if success else code,
                "error_message": error_message,
                "execution_latency_ms": execution_latency_ms,
            }
        )
        if context and isinstance(execution_result, dict):
            log_execution_result = {**execution_result, "context": context}
            log_execution_result.update(
                {
                    "success": success,
                    "code": code,
                    "message": message or error_message or ("指令执行成功" if success else "指令执行失败"),
                    "error_code": None if success else code,
                    "error_message": error_message,
                    "execution_latency_ms": execution_latency_ms,
                }
            )
        elif context:
            log_execution_result["context"] = context

        self.db.add(
            CommandLog(
                user_id=self.user.id,
                raw_command=command or "",
                parsed_result=parsed_result,
                execution_result=log_execution_result,
                success=success,
                error_message=error_message,
            )
        )
        if not success:
            self.db.commit()

    def _write_batch_log(
        self,
        command: str | None,
        multi_parsed: MultiCommandParseResult,
        execution_result: dict[str, Any],
        success: bool,
        error_message: str | None,
        context: dict[str, Any],
        execution_latency_ms: int,
    ) -> None:
        parsed_result = {
            "intent": "batch",
            "valid": multi_parsed.valid,
            "is_batch": True,
            "command_count": multi_parsed.command_count,
            "original_text": multi_parsed.original_text,
            "normalized_text": multi_parsed.normalized_text,
            "confidence": self._batch_confidence(multi_parsed),
            "message": execution_result["message"],
            "sub_commands": [item.to_dict() for item in multi_parsed.sub_commands],
            "parse_detail": {
                "dialect_normalization": multi_parsed.normalization,
                "batch_split": multi_parsed.split_detail,
                "sub_commands": [item.to_dict() for item in multi_parsed.sub_commands],
            },
            "context": context,
        }
        log_execution_result = {
            **execution_result,
            "success": success,
            "error_code": None if success else execution_result["code"],
            "error_message": error_message,
            "execution_latency_ms": execution_latency_ms,
            "context": context,
        }
        self.db.add(
            CommandLog(
                user_id=self.user.id,
                raw_command=command or "",
                parsed_result=parsed_result,
                execution_result=log_execution_result,
                success=success,
                error_message=error_message,
            )
        )

    def _merge_normalization_context(
        self,
        context: dict[str, Any] | None,
        normalization: dict[str, Any],
    ) -> dict[str, Any]:
        enriched_context = dict(context or {})
        enriched_context.setdefault("trace_id", generate_command_trace_id())
        enriched_context.setdefault("input_source", "text")
        enriched_context["normalization"] = normalization
        return enriched_context

    def _prepare_personal_context(self, context: dict[str, Any] | None) -> dict[str, Any]:
        prepared = dict(context or {})
        explicit_dialect = prepared.get("dialect")
        preferred = preference_context(self.preference)
        dialect = explicit_dialect or preferred["preferred_dialect"] or "auto"
        prepared["dialect"] = dialect
        prepared["preference_used"] = preferred
        prepared["preference_used"]["preferred_dialect"] = dialect
        return prepared

    def _apply_asr_post_correction(self, command: str | None, context: dict[str, Any]) -> str | None:
        existing = context.get("asr_post_correction")
        if isinstance(existing, dict) and existing.get("original_text") == (command or ""):
            return existing.get("corrected_text") or command

        correction = correct_asr_text(command, db=self.db, user=self.user)
        if correction.changed:
            context["asr_post_correction"] = correction.to_dict()
        return correction.corrected_text

    def _rewrite_alias_command(self, command: str | None) -> tuple[str | None, dict[str, Any] | None]:
        alias_match = match_device_alias(self.db, self.user, command)
        if not alias_match or not command:
            return command, alias_match
        target = f"{alias_match.get('room') or ''}{alias_match.get('device_name') or ''}"
        return command.replace(alias_match["alias"], target, 1), alias_match

    def _find_target_device(self, parsed: ParseResult):
        alias_match = (parsed.parse_detail or {}).get("alias_match")
        if isinstance(alias_match, dict) and alias_match.get("device_id"):
            return get_device_for_user(self.db, self.user, alias_match["device_id"])
        return find_device(self.db, self.user, parsed.room, parsed.device_type)

    def _elapsed_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    def _build_success_sub_result(
        self,
        index: int,
        text: str,
        parsed: ParseResult,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._build_execute_response(parsed, result)
        return {
            "index": index,
            "text": text,
            "success": True,
            "code": "OK",
            "message": "指令执行成功",
            "parsed": response["parsed"],
            "result": response["result"],
            "device_before": response.get("device_before"),
            "device_after": response.get("device_after"),
            "affected_devices": response.get("affected_devices") or [],
            "reminder": response.get("reminder"),
            "weather": response.get("weather"),
            "scene": response.get("scene"),
        }

    def _build_failed_sub_result(
        self,
        index: int,
        text: str,
        code: str,
        message: str,
        parsed: ParseResult,
        data: Any = None,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "text": text,
            "success": False,
            "code": code,
            "message": message,
            "parsed": parsed.to_dict(),
            "result": data,
            "device_before": None,
            "device_after": None,
            "affected_devices": [],
        }

    def _batch_confidence(self, multi_parsed: MultiCommandParseResult) -> float | None:
        confidences = [item.parsed.confidence for item in multi_parsed.sub_commands if item.parsed.confidence is not None]
        if not confidences:
            return None
        return round(min(confidences), 2)


def generate_command_trace_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"cmd_{timestamp}_{secrets.token_hex(4)}"
