import re
import unicodedata
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any

from app.services.device_capabilities import (
    PropertyCapability,
    all_option_aliases,
    all_property_aliases,
    get_device_capabilities,
    get_property_capability,
    legacy_intent_for_property,
    option_aliases,
)


ROOM_KEYWORDS = ["客厅", "卧室", "厨房", "书房", "阳台", "卫生间"]
ROOM_ALIASES = {
    "客厅": ["客厅", "大厅"],
    "卧室": ["卧室", "房间", "睡房"],
    "厨房": ["厨房"],
    "书房": ["书房"],
    "阳台": ["阳台"],
    "卫生间": ["卫生间", "厕所", "洗手间"],
}
DEVICE_ALIASES = {
    "desk_lamp": ["台灯", "书桌灯"],
    "bedside_lamp": ["床头灯", "床边灯"],
    "light": ["灯", "灯光", "电灯", "等"],
    "air_conditioner": ["空调", "冷气"],
    "tv": ["电视", "电视机"],
    "curtain": ["窗帘", "帘子"],
    "fan": ["排风扇", "风扇"],
    "robot_vacuum": ["扫地机器人", "扫地机"],
    "speaker": ["音箱", "音响", "智能音箱"],
    "humidifier": ["加湿器"],
    "air_purifier": ["空气净化器", "净化器"],
    "smart_plug": ["智能插座", "插座"],
    "fridge": ["冰箱"],
    "smoke_sensor": ["烟雾传感器", "烟感", "烟雾报警器"],
}
DEVICE_CANONICAL_NAME = {
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
SCENE_KEYWORDS = ["睡眠模式", "回家模式", "离家模式"]
CITY_KEYWORDS = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "重庆", "西安", "武汉"]
FILLER_WORDS = ["帮我", "请", "麻烦", "一下", "可以", "现在", "给我"]
PUNCTUATION_PATTERN = re.compile(r"[\s，。！？、；：,.!?;\"'“”‘’（）()\[\]【】]")
LOW_CONFIDENCE_THRESHOLD = 0.6
CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
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
class NormalizedCommand:
    original_text: str = ""
    normalized_text: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    intent: str | None = None
    room: str | None = None
    device_type: str | None = None
    value: int | None = None
    property_name: str | None = None
    property_value: Any = None
    scene: str | None = None
    reminder_time: str | None = None
    reminder_content: str | None = None
    city: str | None = None
    valid: bool = False
    message: str = "无法识别指令"
    original_text: str = ""
    normalized_text: str = ""
    confidence: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    match_type: str | None = None
    parse_detail: dict[str, Any] = field(default_factory=dict)
    error_code: str = "INVALID_COMMAND"

    def to_dict(self) -> dict:
        return asdict(self)


class CommandParser:
    def parse(self, command: str | None) -> ParseResult:
        normalized = self.normalize_command(command)
        if not normalized.normalized_text:
            return self._invalid(normalized, "指令不能为空")

        text = normalized.normalized_text
        room_match = self._match_room(text)
        device_match = self._match_device(text)
        value_info = self._extract_value(text)
        property_match = self._match_property(text, device_match.get("device_type"), value_info)
        time_info = self._extract_time(text)
        scene = self._find_scene(text)
        city = self._find_city(text)
        intent_scores = self._score_intents(text, room_match, device_match, value_info, property_match, time_info, scene, city)
        intent = max(intent_scores, key=intent_scores.get)
        score = intent_scores[intent]

        parse_detail = {
            "intent_scores": intent_scores,
            "room_match": room_match,
            "device_match": device_match,
            "value_extract": value_info,
            "property_match": property_match,
            "time_extract": time_info,
            "normalization_steps": normalized.steps,
        }
        matched_keywords = self._merge_keywords(
            normalized.matched_keywords,
            room_match.get("matched_keywords", []),
            device_match.get("matched_keywords", []),
            value_info.get("matched_keywords", []),
            property_match.get("matched_keywords", []),
            time_info.get("matched_keywords", []),
            [scene] if scene else [],
            [city] if city else [],
        )

        if score < 3:
            return self._invalid(
                normalized,
                "我不太确定你的意思，请换一种说法，或使用文本输入。",
                confidence=0.25,
                matched_keywords=matched_keywords,
                parse_detail=parse_detail,
            )

        result = self._build_result(
            normalized=normalized,
            intent=intent,
            room_match=room_match,
            device_match=device_match,
            value_info=value_info,
            property_match=property_match,
            time_info=time_info,
            scene=scene,
            city=city,
            score=score,
            matched_keywords=matched_keywords,
            parse_detail=parse_detail,
        )
        if not result.valid:
            return result

        if result.confidence < LOW_CONFIDENCE_THRESHOLD and result.intent in {
            "turn_on",
            "turn_off",
            "set_temperature",
            "set_brightness",
            "set_volume",
            "set_property",
        }:
            result.valid = False
            result.error_code = "INVALID_COMMAND"
            result.message = "我不太确定你的意思，请换一种说法，或使用文本输入。"
        return result

    def normalize_command(self, command: str | None) -> NormalizedCommand:
        original = "" if command is None else command.strip()
        text = unicodedata.normalize("NFKC", original)
        text = PUNCTUATION_PATTERN.sub("", text)
        steps = ["去除首尾空格", "统一全角/半角符号", "去除空白和常见标点"]
        matched_keywords: list[str] = []

        for filler in FILLER_WORDS:
            if filler in text:
                text = text.replace(filler, "")
                matched_keywords.append(filler)
        if matched_keywords:
            steps.append("弱化口语词")

        replacements = [
            (r"开一下|开启|启动|打开|开(?!合|度)", "打开"),
            (r"关一下|关掉|关闭|停止|关", "关闭"),
            (r"设置为|设为|调到|调成|调整到", "设置"),
            (r"电视机", "电视"),
            (r"灯光|电灯", "灯"),
            (r"冷气", "空调"),
            (r"帘子", "窗帘"),
            (r"声音", "音量"),
        ]
        for pattern, replacement in replacements:
            if re.search(pattern, text):
                matched_keywords.append(re.search(pattern, text).group(0))
                text = re.sub(pattern, replacement, text)
        if replacements:
            steps.append("同义词归一")

        text = self._replace_chinese_numbers(text)
        steps.append("中文数字转阿拉伯数字")
        return NormalizedCommand(original_text=original, normalized_text=text, matched_keywords=matched_keywords, steps=steps)

    def _build_result(
        self,
        normalized: NormalizedCommand,
        intent: str,
        room_match: dict[str, Any],
        device_match: dict[str, Any],
        value_info: dict[str, Any],
        property_match: dict[str, Any],
        time_info: dict[str, Any],
        scene: str | None,
        city: str | None,
        score: int,
        matched_keywords: list[str],
        parse_detail: dict[str, Any],
    ) -> ParseResult:
        text = normalized.normalized_text
        confidence, confidence_breakdown = self._calculate_confidence(intent, score, room_match, device_match, value_info, property_match, time_info)
        parse_detail["confidence_breakdown"] = confidence_breakdown
        base = {
            "original_text": normalized.original_text,
            "normalized_text": text,
            "confidence": confidence,
            "matched_keywords": matched_keywords,
            "match_type": self._overall_match_type(room_match, device_match),
            "parse_detail": parse_detail,
        }

        if intent == "set_property":
            return self._build_property_result(normalized, room_match, device_match, property_match, value_info, base)
        if intent in {"turn_on", "turn_off"}:
            if not device_match.get("device_type"):
                return self._invalid(normalized, "未识别到要控制的设备", confidence, matched_keywords, parse_detail)
            return ParseResult(
                intent=intent,
                room=room_match.get("room"),
                device_type=device_match.get("device_type"),
                valid=True,
                message=self._build_success_message(intent, room_match.get("room"), device_match.get("device_type")),
                **base,
            )

        if intent == "set_temperature":
            if property_match.get("property_name") and property_match.get("property_name") != "temperature":
                return self._build_property_result(normalized, room_match, device_match, property_match, value_info, base)
            if device_match.get("device_type") and device_match.get("device_type") != "air_conditioner":
                return self._build_property_result(normalized, room_match, device_match, property_match, value_info, base)
            return self._build_value_result(normalized, "set_temperature", "air_conditioner", "温度", 16, 30, room_match, device_match, value_info, base)
        if intent == "set_brightness":
            if property_match.get("property_name") and property_match.get("property_name") != "brightness":
                return self._build_property_result(normalized, room_match, device_match, property_match, value_info, base)
            return self._build_value_result(normalized, "set_brightness", "light", "亮度", 0, 100, room_match, device_match, value_info, base)
        if intent == "set_volume":
            if property_match.get("property_name") and property_match.get("property_name") != "volume":
                return self._build_property_result(normalized, room_match, device_match, property_match, value_info, base)
            return self._build_value_result(normalized, "set_volume", "tv", "音量", 0, 100, room_match, device_match, value_info, base)

        if intent == "query_status":
            return ParseResult(
                intent="query_status",
                room=room_match.get("room"),
                device_type=device_match.get("device_type"),
                valid=True,
                message="识别为：查询设备状态",
                **base,
            )

        if intent == "run_scene":
            if scene is None:
                return self._invalid(normalized, "未识别到要执行的场景", confidence, matched_keywords, parse_detail)
            return ParseResult(intent="run_scene", scene=scene, valid=True, message=f"识别为：执行{scene}", **base)

        if intent == "create_reminder":
            reminder_content = self._extract_reminder_content(text)
            if not time_info.get("value") or not reminder_content:
                return self._invalid(normalized, "未识别到完整提醒时间或内容", confidence, matched_keywords, parse_detail)
            return ParseResult(
                intent="create_reminder",
                reminder_time=time_info["value"],
                reminder_content=reminder_content,
                valid=True,
                message=f"识别为：{time_info['value']} 提醒 {reminder_content}",
                **base,
            )

        if intent == "query_weather":
            return ParseResult(
                intent="query_weather",
                city=city,
                valid=True,
                message=f"识别为：查询{city or '本地'}天气",
                **base,
            )

        return self._invalid(normalized, "暂不支持该中文指令", confidence, matched_keywords, parse_detail)

    def _build_property_result(
        self,
        normalized: NormalizedCommand,
        room_match: dict[str, Any],
        device_match: dict[str, Any],
        property_match: dict[str, Any],
        value_info: dict[str, Any],
        base: dict[str, Any],
    ) -> ParseResult:
        device_type = device_match.get("device_type")
        if not device_type:
            return self._invalid(normalized, "未识别到要控制的设备", base["confidence"], base["matched_keywords"], base["parse_detail"])

        property_name = property_match.get("property_name")
        capability = get_property_capability(device_type, property_name)
        if capability is None:
            return self._invalid(normalized, "该设备不支持设置该参数", base["confidence"], base["matched_keywords"], base["parse_detail"], error_code="UNSUPPORTED_ACTION")

        property_value = self._extract_property_value(normalized.normalized_text, capability, value_info)
        if property_value is None and capability.value_type == "enum":
            property_value = self._extract_any_enum_value(normalized.normalized_text)
        if property_value is None:
            return self._invalid(normalized, f"未识别到{capability.label}参数", base["confidence"], base["matched_keywords"], base["parse_detail"])

        error_message = self._validate_property_value(capability, property_value)
        if error_message:
            return self._invalid(
                normalized,
                error_message,
                base["confidence"],
                base["matched_keywords"],
                base["parse_detail"],
                error_code="VALUE_OUT_OF_RANGE" if capability.value_type == "number" else "INVALID_PROPERTY_VALUE",
            )

        intent = legacy_intent_for_property(device_type, capability.property_name) or "set_property"
        value = property_value if isinstance(property_value, int) else value_info.get("value")
        return ParseResult(
            intent=intent,
            room=room_match.get("room"),
            device_type=device_type,
            value=value,
            property_name=capability.property_name,
            property_value=property_value,
            valid=True,
            message=f"识别为：设置{capability.label}为 {property_value}",
            **base,
        )

    def _build_value_result(
        self,
        normalized: NormalizedCommand,
        intent: str,
        expected_device_type: str,
        label: str,
        minimum: int,
        maximum: int,
        room_match: dict[str, Any],
        device_match: dict[str, Any],
        value_info: dict[str, Any],
        base: dict[str, Any],
    ) -> ParseResult:
        value = value_info.get("value")
        if value is None:
            return self._invalid(normalized, f"未识别到{label}参数", base["confidence"], base["matched_keywords"], base["parse_detail"])
        if value < minimum or value > maximum:
            return self._invalid(
                normalized,
                f"{label}必须在 {minimum}-{maximum} 范围内",
                base["confidence"],
                base["matched_keywords"],
                base["parse_detail"],
                error_code="VALUE_OUT_OF_RANGE",
            )
        device_type = device_match.get("device_type") or expected_device_type
        return ParseResult(
            intent=intent,
            room=room_match.get("room"),
            device_type=device_type,
            value=value,
            property_name={
                "set_temperature": "temperature",
                "set_brightness": "brightness",
                "set_volume": "volume",
            }.get(intent),
            property_value=value,
            valid=True,
            message=f"识别为：设置{label}为 {value}",
            **base,
        )

    def _score_intents(
        self,
        text: str,
        room_match: dict[str, Any],
        device_match: dict[str, Any],
        value_info: dict[str, Any],
        property_match: dict[str, Any],
        time_info: dict[str, Any],
        scene: str | None,
        city: str | None,
    ) -> dict[str, int]:
        has_room = bool(room_match.get("room"))
        device_type = device_match.get("device_type")
        has_value = value_info.get("value") is not None
        scores = {
            "turn_on": 0,
            "turn_off": 0,
            "set_temperature": 0,
            "set_brightness": 0,
            "set_volume": 0,
            "set_property": 0,
            "query_status": 0,
            "run_scene": 0,
            "create_reminder": 0,
            "query_weather": 0,
        }

        if "打开" in text:
            scores["turn_on"] += 2
        if "关闭" in text:
            scores["turn_off"] += 2
        if "设置" in text:
            scores["set_temperature"] += 1
            scores["set_brightness"] += 1
            scores["set_volume"] += 1
            scores["set_property"] += 1
        if device_type:
            scores["turn_on"] += 2
            scores["turn_off"] += 2
        if has_room:
            scores["turn_on"] += 1
            scores["turn_off"] += 1
            scores["query_status"] += 1
        if device_type == "air_conditioner":
            scores["set_temperature"] += 2
        if "温度" in text or re.search(r"\d+度", text):
            scores["set_temperature"] += 2
        if "亮度" in text:
            scores["set_brightness"] += 2
        if device_type == "light":
            scores["set_brightness"] += 2
        if "音量" in text:
            scores["set_volume"] += 2
        if device_type == "tv":
            scores["set_volume"] += 2
        if has_value:
            scores["set_temperature"] += 2
            scores["set_brightness"] += 2
            scores["set_volume"] += 2
            scores["set_property"] += 1
        if property_match.get("property_name"):
            scores["set_property"] += 4
            if property_match.get("property_value") is not None:
                scores["set_property"] += 2
            if device_type:
                scores["set_property"] += 1
        if re.search(r"(查看|查询).*(状态|设备)", text):
            scores["query_status"] += 4
        if scene:
            scores["run_scene"] += 4
        if re.search(r"(模式|场景|打开)", text):
            scores["run_scene"] += 1
        if "提醒" in text:
            scores["create_reminder"] += 3
        if time_info.get("value"):
            scores["create_reminder"] += 2
        if "提醒" in text and self._extract_reminder_content(text):
            scores["create_reminder"] += 1
        if "天气" in text:
            scores["query_weather"] += 3
        if city or re.search(r"(查询|查看|今天|本地)", text):
            scores["query_weather"] += 1

        if scores["set_temperature"] >= 5:
            scores["turn_on"] = max(0, scores["turn_on"] - 2)
            scores["turn_off"] = max(0, scores["turn_off"] - 2)
        if scores["set_property"] >= 5:
            scores["turn_on"] = max(0, scores["turn_on"] - 2)
            scores["turn_off"] = max(0, scores["turn_off"] - 2)
        return scores

    def _match_room(self, text: str) -> dict[str, Any]:
        for room, aliases in ROOM_ALIASES.items():
            for alias in aliases:
                if alias in text:
                    return {"room": room, "matched_text": alias, "match_type": "exact" if alias == room else "alias", "score": 1.0, "matched_keywords": [alias]}
        return self._fuzzy_match(text, ROOM_ALIASES, "room")

    def _match_device(self, text: str) -> dict[str, Any]:
        for device_type, aliases in DEVICE_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                position = text.find(alias)
                if position >= 0:
                    if self._overlaps_room_alias(text, position, len(alias)):
                        continue
                    match_type = "exact" if alias == DEVICE_CANONICAL_NAME[device_type] else "alias"
                    if alias == "等":
                        match_type = "fuzzy"
                    return {
                        "device_type": device_type,
                        "device_name": DEVICE_CANONICAL_NAME[device_type],
                        "matched_text": alias,
                        "match_type": match_type,
                        "score": 0.82 if alias == "等" else 1.0,
                        "matched_keywords": [alias],
                    }
        match = self._fuzzy_match(text, DEVICE_ALIASES, "device_type")
        if match.get("device_type"):
            match["device_name"] = DEVICE_CANONICAL_NAME[match["device_type"]]
        return match

    def _overlaps_room_alias(self, text: str, position: int, length: int) -> bool:
        start = position
        end = position + length
        for aliases in ROOM_ALIASES.values():
            for alias in aliases:
                room_start = text.find(alias)
                if room_start < 0:
                    continue
                room_end = room_start + len(alias)
                if start < room_end and end > room_start:
                    return True
        return False

    def _fuzzy_match(self, text: str, aliases: dict[str, list[str]], key: str) -> dict[str, Any]:
        best = {key: None, "matched_text": None, "match_type": None, "score": 0.0, "matched_keywords": []}
        candidates = self._text_candidates(text)
        for target, names in aliases.items():
            for name in names:
                for candidate in candidates:
                    ratio = SequenceMatcher(None, candidate, name).ratio()
                    if ratio > best["score"]:
                        best = {key: target, "matched_text": candidate, "match_type": "fuzzy", "score": round(ratio, 2), "matched_keywords": [candidate]}
        if best["score"] < 0.76:
            return {key: None, "matched_text": None, "match_type": None, "score": best["score"], "matched_keywords": []}
        return best

    def _text_candidates(self, text: str) -> list[str]:
        candidates = set()
        for size in (1, 2, 3):
            for index in range(0, max(0, len(text) - size + 1)):
                candidates.add(text[index : index + size])
        return list(candidates)

    def _extract_value(self, text: str) -> dict[str, Any]:
        match = re.search(r"\d+", text)
        if not match:
            return {"value": None, "matched_text": None, "matched_keywords": []}
        return {"value": int(match.group()), "matched_text": match.group(), "matched_keywords": [match.group()]}

    def _match_property(self, text: str, device_type: str | None, value_info: dict[str, Any]) -> dict[str, Any]:
        empty = {"property_name": None, "matched_text": None, "match_type": None, "property_value": None, "score": 0.0, "matched_keywords": []}
        capabilities = get_device_capabilities(device_type)
        if not capabilities:
            return empty

        for capability in capabilities:
            for alias in sorted(capability.aliases, key=len, reverse=True):
                if alias in text:
                    property_value = self._extract_property_value(text, capability, value_info)
                    matched_keywords = [alias]
                    if property_value is not None:
                        matched_keywords.append(str(property_value))
                    return {
                        "property_name": capability.property_name,
                        "matched_text": alias,
                        "match_type": "exact",
                        "property_value": property_value,
                        "score": 1.0,
                        "matched_keywords": matched_keywords,
                    }

        enum_matches = []
        for capability in capabilities:
            if capability.value_type != "enum":
                continue
            property_value = self._extract_property_value(text, capability, value_info)
            if property_value is not None:
                enum_matches.append((capability, property_value))
        if len(enum_matches) == 1:
            capability, property_value = enum_matches[0]
            return {
                "property_name": capability.property_name,
                "matched_text": str(property_value),
                "match_type": "value_inferred",
                "property_value": property_value,
                "score": 0.86,
                "matched_keywords": [str(property_value)],
            }

        numeric_capabilities = [capability for capability in capabilities if capability.value_type == "number"]
        if (
            len(numeric_capabilities) == 1
            and value_info.get("value") is not None
            and self._looks_like_property_setting(text)
            and not self._has_unsupported_property_alias(text, capabilities)
        ):
            capability = numeric_capabilities[0]
            property_value = self._extract_property_value(text, capability, value_info)
            return {
                "property_name": capability.property_name,
                "matched_text": value_info.get("matched_text"),
                "match_type": "value_inferred",
                "property_value": property_value,
                "score": 0.82,
                "matched_keywords": value_info.get("matched_keywords", []),
            }
        return empty

    def _has_unsupported_property_alias(self, text: str, capabilities: tuple[PropertyCapability, ...]) -> bool:
        supported = {alias for capability in capabilities for alias in capability.aliases}
        for alias in all_property_aliases():
            if alias in text and alias not in supported:
                return True
        return False

    def _extract_property_value(self, text: str, capability: PropertyCapability, value_info: dict[str, Any]) -> Any:
        if capability.value_type == "number":
            if capability.property_name == "open_percent":
                if re.search(r"(全开|完全打开|全部打开)", text):
                    return 100
                if re.search(r"(半开|开一半)", text):
                    return 50
                if re.search(r"(全关|完全关闭|全部关闭)", text):
                    return 0
            return value_info.get("value")

        for alias, option in option_aliases(capability):
            if alias in text:
                return option
        return None

    def _extract_any_enum_value(self, text: str) -> Any:
        for alias, option in all_option_aliases():
            if alias in text:
                return option
        return None

    def _validate_property_value(self, capability: PropertyCapability, value: Any) -> str | None:
        if capability.value_type == "number":
            if not isinstance(value, int) or value < (capability.minimum or 0) or value > (capability.maximum or 0):
                return f"{capability.label}必须在 {capability.minimum}-{capability.maximum} 范围内"
            return None
        if capability.value_type == "enum":
            if value not in capability.options:
                options = "、".join(str(option) for option in capability.options)
                return f"{capability.label}仅支持 {options}"
            return None
        return "暂不支持该参数类型"

    def _looks_like_property_setting(self, text: str) -> bool:
        return "设置" in text or bool(re.search(r"\d+(?:度|%|百分比|瓦)?", text))

    def _extract_time(self, text: str) -> dict[str, Any]:
        digital_match = re.search(r"(\d{1,2}):(\d{2})", text)
        if digital_match:
            hour = int(digital_match.group(1))
            minute = int(digital_match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return {"value": f"{hour:02d}:{minute:02d}", "matched_text": digital_match.group(0), "matched_keywords": [digital_match.group(0)]}
            return {"value": None, "matched_text": digital_match.group(0), "matched_keywords": [digital_match.group(0)]}

        chinese_or_digit = r"[零〇一二两三四五六七八九十\d]{1,3}"
        chinese_match = re.search(
            rf"(明天)?(上午|早上|中午|下午|晚上|夜里)?({chinese_or_digit})点(半|{chinese_or_digit}分?)?",
            text,
        )
        if not chinese_match:
            return {"value": None, "matched_text": None, "matched_keywords": []}

        day_text, period, hour_text, minute_text = chinese_match.groups()
        hour = self._to_int(hour_text)
        if hour is None:
            return {"value": None, "matched_text": chinese_match.group(0), "matched_keywords": [chinese_match.group(0)]}
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
            detail = {"value": f"{hour:02d}:{minute:02d}", "matched_text": chinese_match.group(0), "matched_keywords": [chinese_match.group(0)]}
            if day_text:
                detail["note"] = "当前提醒仅保存时间，日期按创建当天处理"
            return detail
        return {"value": None, "matched_text": chinese_match.group(0), "matched_keywords": [chinese_match.group(0)]}

    def _find_scene(self, text: str) -> str | None:
        return next((scene for scene in SCENE_KEYWORDS if scene in text), None)

    def _find_city(self, text: str) -> str | None:
        city = next((item for item in CITY_KEYWORDS if item in text), None)
        if city:
            return city
        match = re.search(r"(?:查询|查看)?(.+?)天气", text)
        if match:
            candidate = match.group(1).replace("今天的", "").replace("今天", "").replace("本地", "")
            return candidate or None
        return None

    def _extract_reminder_content(self, text: str) -> str | None:
        if "提醒我" not in text:
            return None
        content = text.split("提醒我", 1)[1]
        content = re.sub(r"\d{1,2}:\d{2}", "", content, count=1)
        content = re.sub(r"(明天)?(上午|早上|中午|下午|晚上|夜里)?[零〇一二两三四五六七八九十\d]{1,3}点(半|[零〇一二两三四五六七八九十\d]{1,3}分?)?", "", content, count=1)
        return content.strip() or None

    def _replace_chinese_numbers(self, text: str) -> str:
        pattern = re.compile(r"[零〇一二两三四五六七八九十百]{1,5}")

        def replace(match: re.Match) -> str:
            value = self._to_int(match.group(0))
            return str(value) if value is not None else match.group(0)

        return pattern.sub(replace, text)

    def _to_int(self, text: str) -> int | None:
        if text.isdigit():
            return int(text)
        if text == "百":
            return 100
        if "百" in text:
            left, right = text.split("百", 1)
            hundreds = CHINESE_DIGITS.get(left, 1) if left else 1
            rest = self._to_int(right.lstrip("零")) if right else 0
            if rest is None:
                return None
            return hundreds * 100 + rest
        if text == "十":
            return 10
        if "十" in text:
            left, right = text.split("十", 1)
            tens = CHINESE_DIGITS.get(left, 1) if left else 1
            ones = CHINESE_DIGITS.get(right, 0) if right else 0
            return tens * 10 + ones
        if len(text) == 1:
            return CHINESE_DIGITS.get(text)
        total = 0
        for char in text:
            digit = CHINESE_DIGITS.get(char)
            if digit is None:
                return None
            total = total * 10 + digit
        return total

    def _calculate_confidence(
        self,
        intent: str,
        score: int,
        room_match: dict[str, Any],
        device_match: dict[str, Any],
        value_info: dict[str, Any],
        property_match: dict[str, Any],
        time_info: dict[str, Any],
    ) -> tuple[float, dict[str, float]]:
        base_score = min(0.45 + score * 0.06, 0.92)
        room_bonus = 0.0
        device_bonus = 0.0
        value_bonus = 0.0
        fuzzy_penalty = 0.0

        if room_match.get("room"):
            room_bonus = 0.04 if room_match.get("match_type") == "fuzzy" else 0.06
        if device_match.get("device_type"):
            device_bonus = 0.04 if device_match.get("match_type") == "fuzzy" else 0.06
        if intent in {"set_temperature", "set_brightness", "set_volume", "set_property"} and (
            value_info.get("value") is not None or property_match.get("property_value") is not None
        ):
            value_bonus = 0.05
        if intent == "create_reminder" and time_info.get("value"):
            value_bonus = 0.05
        if room_match.get("match_type") == "fuzzy" or device_match.get("match_type") == "fuzzy":
            fuzzy_penalty = 0.08

        confidence = base_score + room_bonus + device_bonus + value_bonus - fuzzy_penalty
        final_confidence = round(max(0.0, min(confidence, 0.99)), 2)
        breakdown = {
            "base_score": round(base_score, 2),
            "room_bonus": round(room_bonus, 2),
            "device_bonus": round(device_bonus, 2),
            "value_bonus": round(value_bonus, 2),
            "fuzzy_penalty": round(fuzzy_penalty, 2),
            "asr_correction_penalty": 0.0,
            "multi_fuzzy_penalty": 0.0,
            "final_confidence": final_confidence,
        }
        return final_confidence, breakdown

    def _overall_match_type(self, room_match: dict[str, Any], device_match: dict[str, Any]) -> str | None:
        types = [room_match.get("match_type"), device_match.get("match_type")]
        if "fuzzy" in types:
            return "fuzzy"
        if "alias" in types:
            return "alias"
        if "exact" in types:
            return "exact"
        return None

    def _build_success_message(self, intent: str, room: str | None, device_type: str | None) -> str:
        action = "打开" if intent == "turn_on" else "关闭"
        target = f"{room or ''}{DEVICE_CANONICAL_NAME.get(device_type, '设备')}"
        return f"识别为：{action}{target}"

    def _invalid(
        self,
        normalized: NormalizedCommand,
        message: str,
        confidence: float = 0.0,
        matched_keywords: list[str] | None = None,
        parse_detail: dict[str, Any] | None = None,
        error_code: str = "INVALID_COMMAND",
    ) -> ParseResult:
        return ParseResult(
            valid=False,
            message=message,
            original_text=normalized.original_text,
            normalized_text=normalized.normalized_text,
            confidence=confidence,
            matched_keywords=matched_keywords or normalized.matched_keywords,
            parse_detail=parse_detail or {"normalization_steps": normalized.steps},
            error_code=error_code,
        )

    def _merge_keywords(self, *groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                if item and item not in merged:
                    merged.append(item)
        return merged
