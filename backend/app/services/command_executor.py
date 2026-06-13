from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import CommandLog, Reminder, Scene, User
from app.services.command_parser import CommandParser, ParseResult
from app.services.home_actions import (
    BusinessError,
    apply_device_state,
    find_device,
    get_weather,
    list_room_devices,
    run_scene_actions,
    validate_value_range,
)


class CommandExecutor:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.parser = CommandParser()

    def execute(self, command: str | None) -> dict[str, Any]:
        parsed = self.parser.parse(command)
        if not parsed.valid:
            self._write_log(command, parsed, None, False, parsed.message)
            raise BusinessError(parsed.error_code, parsed.message, data=parsed.to_dict())

        try:
            result = self._execute_parsed(parsed)
        except BusinessError as exc:
            self._write_log(command, parsed, exc.data, False, exc.message)
            raise

        self._write_log(command, parsed, result, True, None)
        self.db.commit()
        return self._build_execute_response(parsed, result)

    def _execute_parsed(self, parsed: ParseResult) -> dict[str, Any]:
        if parsed.intent == "turn_on":
            return self._set_power(parsed, True)
        if parsed.intent == "turn_off":
            return self._set_power(parsed, False)
        if parsed.intent == "set_temperature":
            return self._set_property(parsed, "air_conditioner", "temperature", 16, 30, "温度")
        if parsed.intent == "set_brightness":
            return self._set_property(parsed, "light", "brightness", 0, 100, "亮度")
        if parsed.intent == "set_volume":
            return self._set_property(parsed, "tv", "volume", 0, 100, "音量")
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
        device = find_device(self.db, self.user, parsed.room, parsed.device_type)
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
        expected_device_type: str,
        property_name: str,
        minimum: int,
        maximum: int,
        label: str,
    ) -> dict[str, Any]:
        if parsed.device_type != expected_device_type:
            raise BusinessError("UNSUPPORTED_ACTION", f"该设备不支持设置{label}")
        value = validate_value_range(parsed.value, minimum, maximum, label)
        device = find_device(self.db, self.user, parsed.room, parsed.device_type)
        return apply_device_state(
            db=self.db,
            device=device,
            user=self.user,
            state_update={"properties": {property_name: value}},
            change_source="command",
        )

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

    def _build_execute_response(self, parsed: ParseResult, result: dict[str, Any]) -> dict[str, Any]:
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
        return response

    def _write_log(
        self,
        command: str | None,
        parsed: ParseResult,
        execution_result: dict[str, Any] | None,
        success: bool,
        error_message: str | None,
    ) -> None:
        self.db.add(
            CommandLog(
                user_id=self.user.id,
                raw_command=command or "",
                parsed_result=parsed.to_dict(),
                execution_result=execution_result,
                success=success,
                error_message=error_message,
            )
        )
        if not success:
            self.db.commit()
