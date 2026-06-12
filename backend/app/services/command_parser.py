import re
from dataclasses import asdict, dataclass


ROOM_KEYWORDS = ["客厅", "卧室", "厨房", "书房", "阳台", "卫生间"]
DEVICE_KEYWORDS = {
    "灯": "light",
    "空调": "air_conditioner",
    "电视": "tv",
    "窗帘": "curtain",
    "排风扇": "fan",
}
SCENE_KEYWORDS = ["睡眠模式", "回家模式", "离家模式"]
CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


@dataclass
class ParseResult:
    intent: str | None = None
    room: str | None = None
    device_type: str | None = None
    value: int | None = None
    scene: str | None = None
    reminder_time: str | None = None
    reminder_content: str | None = None
    city: str | None = None
    valid: bool = False
    message: str = "无法识别指令"

    def to_dict(self) -> dict:
        return asdict(self)


class CommandParser:
    def parse(self, command: str | None) -> ParseResult:
        text = self._normalize(command)
        if not text:
            return ParseResult(message="指令不能为空")

        for parser in (
            self._parse_reminder,
            self._parse_weather,
            self._parse_scene,
            self._parse_query_status,
            self._parse_temperature,
            self._parse_brightness,
            self._parse_volume,
            self._parse_turn_on,
            self._parse_turn_off,
        ):
            result = parser(text)
            if result.valid:
                return result

        return ParseResult(message="暂不支持该中文指令")

    def _normalize(self, command: str | None) -> str:
        if command is None:
            return ""
        return re.sub(r"[\s，。！？,.!?]", "", command.strip())

    def _find_room(self, text: str) -> str | None:
        return next((room for room in ROOM_KEYWORDS if room in text), None)

    def _find_device_type(self, text: str) -> str | None:
        for keyword, device_type in DEVICE_KEYWORDS.items():
            if keyword in text:
                return device_type
        return None

    def _find_number(self, text: str) -> int | None:
        match = re.search(r"\d+", text)
        return int(match.group()) if match else None

    def _parse_turn_on(self, text: str) -> ParseResult:
        if not re.search(r"(打开|开启|开一下|开|启动)", text):
            return ParseResult()
        device_type = self._find_device_type(text)
        if device_type is None:
            return ParseResult()
        return ParseResult(
            intent="turn_on",
            room=self._find_room(text),
            device_type=device_type,
            valid=True,
            message="解析成功",
        )

    def _parse_turn_off(self, text: str) -> ParseResult:
        if not re.search(r"(关闭|关掉|关一下|关)", text):
            return ParseResult()
        device_type = self._find_device_type(text)
        if device_type is None:
            return ParseResult()
        return ParseResult(
            intent="turn_off",
            room=self._find_room(text),
            device_type=device_type,
            valid=True,
            message="解析成功",
        )

    def _parse_temperature(self, text: str) -> ParseResult:
        if "空调" not in text or "度" not in text:
            return ParseResult()
        value = self._find_number(text)
        if value is None:
            return ParseResult()
        return ParseResult(
            intent="set_temperature",
            room=self._find_room(text),
            device_type="air_conditioner",
            value=value,
            valid=True,
            message="解析成功",
        )

    def _parse_brightness(self, text: str) -> ParseResult:
        if "亮度" not in text:
            return ParseResult()
        value = self._find_number(text)
        if value is None:
            return ParseResult()
        device_type = self._find_device_type(text) or "light"
        return ParseResult(
            intent="set_brightness",
            room=self._find_room(text),
            device_type=device_type,
            value=value,
            valid=True,
            message="解析成功",
        )

    def _parse_volume(self, text: str) -> ParseResult:
        if "音量" not in text:
            return ParseResult()
        value = self._find_number(text)
        if value is None:
            return ParseResult()
        device_type = self._find_device_type(text) or "tv"
        return ParseResult(
            intent="set_volume",
            room=self._find_room(text),
            device_type=device_type,
            value=value,
            valid=True,
            message="解析成功",
        )

    def _parse_query_status(self, text: str) -> ParseResult:
        if not re.search(r"(查看|查询).*(状态|设备)", text):
            return ParseResult()
        return ParseResult(
            intent="query_status",
            room=self._find_room(text),
            device_type=self._find_device_type(text),
            valid=True,
            message="解析成功",
        )

    def _parse_scene(self, text: str) -> ParseResult:
        if not re.search(r"(开启|打开|启动|执行)", text):
            return ParseResult()
        scene = next((scene_name for scene_name in SCENE_KEYWORDS if scene_name in text), None)
        if scene is None:
            return ParseResult()
        return ParseResult(intent="run_scene", scene=scene, valid=True, message="解析成功")

    def _parse_reminder(self, text: str) -> ParseResult:
        if not text.startswith("提醒我"):
            return ParseResult()

        content_text = text.removeprefix("提醒我")
        reminder_time = self._extract_time(content_text)
        if reminder_time is None:
            return ParseResult()

        reminder_content = self._remove_time_text(content_text).strip()
        if not reminder_content:
            return ParseResult()

        return ParseResult(
            intent="create_reminder",
            reminder_time=reminder_time,
            reminder_content=reminder_content,
            valid=True,
            message="解析成功",
        )

    def _parse_weather(self, text: str) -> ParseResult:
        if "天气" not in text:
            return ParseResult()

        city = None
        match = re.search(r"(?:查询|查看)?(.+?)天气", text)
        if match:
            candidate = match.group(1).replace("今天的", "").replace("今天", "")
            city = candidate or None

        return ParseResult(intent="query_weather", city=city, valid=True, message="解析成功")

    def _extract_time(self, text: str) -> str | None:
        digital_match = re.search(r"(\d{1,2}):(\d{2})", text)
        if digital_match:
            hour = int(digital_match.group(1))
            minute = int(digital_match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
            return None

        chinese_match = re.search(
            r"(上午|早上|中午|下午|晚上|夜里)?([零一二两三四五六七八九十\d]{1,3})点(半|[零一二两三四五六七八九十\d]{1,3}分?)?",
            text,
        )
        if not chinese_match:
            return None

        period, hour_text, minute_text = chinese_match.groups()
        hour = self._to_int(hour_text)
        if hour is None:
            return None

        minute = 0
        if minute_text == "半":
            minute = 30
        elif minute_text:
            minute = self._to_int(minute_text.removesuffix("分")) or 0

        if period in {"下午", "晚上", "夜里"} and hour < 12:
            hour += 12
        if period == "中午" and hour < 11:
            hour += 12

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return None

    def _remove_time_text(self, text: str) -> str:
        text = re.sub(r"\d{1,2}:\d{2}", "", text, count=1)
        return re.sub(
            r"(上午|早上|中午|下午|晚上|夜里)?[零一二两三四五六七八九十\d]{1,3}点(半|[零一二两三四五六七八九十\d]{1,3}分?)?",
            "",
            text,
            count=1,
        )

    def _to_int(self, text: str) -> int | None:
        if text.isdigit():
            return int(text)
        if text == "十":
            return 10
        if "十" in text:
            left, right = text.split("十", 1)
            tens = CHINESE_DIGITS.get(left, 1) if left else 1
            ones = CHINESE_DIGITS.get(right, 0) if right else 0
            return tens * 10 + ones
        return CHINESE_DIGITS.get(text)
