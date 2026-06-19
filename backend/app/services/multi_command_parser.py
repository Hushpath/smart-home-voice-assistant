import re
import unicodedata
from dataclasses import dataclass, field, replace
from typing import Any

from app.services.command_parser import (
    DEVICE_ALIASES,
    DEVICE_CANONICAL_NAME,
    ROOM_ALIASES,
    CommandParser,
    ParseResult,
)
from app.services.dialect_normalizer import DialectNormalizer, normalize_and_parse_command


SEQUENCE_CONNECTOR_PATTERN = re.compile(r"(?:并且|然后|接着|之后|随后|顺便|同时|并|再|，|,|；|;|。)")
ACTION_WORDS = ("打开", "关闭")
SET_WORDS = ("设置", "调到", "调成", "调整到")
STATE_CHANGING_INTENTS = {"turn_on", "turn_off", "set_temperature", "set_brightness", "set_volume"}


@dataclass
class SubCommandResult:
    index: int
    text: str
    parsed: ParseResult

    def to_dict(self) -> dict[str, Any]:
        data = self.parsed.to_dict()
        data["index"] = self.index
        data["text"] = self.text
        return data


@dataclass
class MultiCommandParseResult:
    is_batch: bool
    original_text: str
    normalized_text: str
    command_count: int
    sub_commands: list[SubCommandResult] = field(default_factory=list)
    normalization: dict[str, Any] = field(default_factory=dict)
    split_detail: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        if not self.sub_commands:
            return False
        return all(item.parsed.valid for item in self.sub_commands)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_batch": self.is_batch,
            "valid": self.valid,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "command_count": self.command_count,
            "sub_commands": [item.to_dict() for item in self.sub_commands],
            "normalization": self.normalization,
            "split_detail": self.split_detail,
        }


class MultiCommandParser:
    def __init__(self, parser: CommandParser | None = None):
        self.parser = parser or CommandParser()
        self.normalizer = DialectNormalizer()

    def parse(self, command: str | None, dialect: str | None = "auto") -> MultiCommandParseResult:
        original_text = "" if command is None else command.strip()
        normalized = self.normalizer.normalize(original_text, dialect=dialect)
        candidate_texts, split_detail = self._split(normalized.normalized_text)
        is_batch = len(candidate_texts) > 1
        sub_commands = self._parse_sub_commands(candidate_texts if is_batch else [original_text], dialect)
        return MultiCommandParseResult(
            is_batch=is_batch,
            original_text=original_text,
            normalized_text=normalized.normalized_text,
            command_count=len(sub_commands),
            sub_commands=sub_commands,
            normalization=normalized.to_dict(),
            split_detail=split_detail,
        )

    def _split(self, text: str) -> tuple[list[str], dict[str, Any]]:
        text = unicodedata.normalize("NFKC", text or "").strip()
        if not text:
            return [], {"strategy": "empty"}

        parts = [part.strip("的 ") for part in SEQUENCE_CONNECTOR_PATTERN.split(text) if part.strip("的 ")]
        if len(parts) > 1:
            inherited = self._inherit_context(parts)
            return inherited, {"strategy": "independent_or_context_inherited", "raw_parts": parts}

        same_action_devices = self._expand_same_action_multi_devices(text)
        if same_action_devices:
            return same_action_devices, {"strategy": "same_action_multi_devices"}

        same_action_rooms = self._expand_same_action_multi_rooms(text)
        if same_action_rooms:
            return same_action_rooms, {"strategy": "same_action_multi_rooms"}

        return [text], {"strategy": "single"}

    def _parse_sub_commands(self, texts: list[str], dialect: str | None) -> list[SubCommandResult]:
        sub_commands: list[SubCommandResult] = []
        is_batch = len(texts) > 1
        for index, text in enumerate(texts, start=1):
            parsed, _ = normalize_and_parse_command(text, parser=self.parser, dialect=dialect)
            if is_batch:
                parsed = self._apply_ambiguity_guard(text, parsed)
            sub_commands.append(SubCommandResult(index=index, text=text, parsed=parsed))
        return sub_commands

    def _expand_same_action_multi_devices(self, text: str) -> list[str] | None:
        action, subject_text = self._action_and_subject(text)
        if not action or any(word in text for word in ("设置", "提醒", "天气", "模式", "状态")):
            return None
        room = self._first_room(subject_text)
        if not room:
            return None
        devices = self._ordered_devices(subject_text)
        if len(devices) < 2:
            return None
        return [f"{action}{room}{DEVICE_CANONICAL_NAME[device_type]}" for device_type in devices]

    def _expand_same_action_multi_rooms(self, text: str) -> list[str] | None:
        action, subject_text = self._action_and_subject(text)
        if not action:
            return None
        rooms = self._ordered_rooms(subject_text)
        devices = self._ordered_devices(subject_text)
        if len(rooms) < 2 or len(devices) != 1:
            return None
        device_name = DEVICE_CANONICAL_NAME[devices[0]]
        return [f"{action}{room}{device_name}" for room in rooms]

    def _inherit_context(self, parts: list[str]) -> list[str]:
        completed: list[str] = []
        last_parse: ParseResult | None = None
        for part in parts:
            candidates = self._inherit_part_context(part, last_parse)
            for candidate in candidates:
                parsed, _ = normalize_and_parse_command(candidate, parser=self.parser, dialect="auto")
                completed.append(candidate)
                if parsed.room or parsed.device_type or parsed.intent in STATE_CHANGING_INTENTS:
                    last_parse = parsed
        return completed

    def _inherit_part_context(self, part: str, previous: ParseResult | None) -> list[str]:
        if previous is None:
            return [part]

        devices = self._ordered_devices(part)
        rooms = self._ordered_rooms(part)
        has_action = self._has_action_word(part)
        previous_action = self._action_from_intent(previous.intent)

        if previous_action and not has_action and devices and not self._looks_setting_command(part):
            room = rooms[0] if rooms else previous.room
            if len(devices) > 1:
                return [f"{previous_action}{room or ''}{DEVICE_CANONICAL_NAME[device_type]}" for device_type in devices]
            return [f"{previous_action}{room or ''}{DEVICE_CANONICAL_NAME[devices[0]]}"]

        if devices and not rooms and previous.room:
            return [self._insert_room_after_action(part, previous.room)]

        should_inherit_subject = not devices and not rooms and self._looks_contextual(part)
        if should_inherit_subject:
            inherited = self._with_inherited_subject(part, previous)
            if inherited != part:
                return [inherited]

        return [part]

    def _with_inherited_subject(self, text: str, previous: ParseResult) -> str:
        if not previous.device_type:
            return text
        if self._ordered_devices(text):
            return text
        subject = f"{previous.room or ''}{DEVICE_CANONICAL_NAME.get(previous.device_type, '')}"
        if not subject:
            return text
        if text.startswith(("设置", "调到", "调成", "调整到")) or re.search(r"\d+度?$", text):
            return f"把{subject}{text}"
        return f"{subject}{text}"

    def _looks_contextual(self, text: str) -> bool:
        return text.startswith(SET_WORDS) or bool(re.search(r"\d+(?:度|%|百分比)?$", text))

    def _looks_setting_command(self, text: str) -> bool:
        return any(word in text for word in SET_WORDS) or bool(re.search(r"\d+(?:度|%|百分比)?", text))

    def _apply_ambiguity_guard(self, text: str, parsed: ParseResult) -> ParseResult:
        if parsed.intent not in STATE_CHANGING_INTENTS:
            return parsed
        if not parsed.valid:
            return parsed
        missing: list[str] = []
        if not parsed.room:
            missing.append("房间")
        if not parsed.device_type:
            missing.append("设备")
        if not missing:
            return parsed
        guarded = replace(parsed)
        guarded.valid = False
        guarded.error_code = "AMBIGUOUS_SUB_COMMAND"
        guarded.message = f"子指令“{text}”缺少{'和'.join(missing)}，为避免误执行已跳过。"
        guarded.confidence = min(parsed.confidence, 0.45)
        parse_detail = dict(parsed.parse_detail or {})
        breakdown = parse_detail.get("confidence_breakdown")
        if isinstance(breakdown, dict):
            breakdown = {**breakdown, "ambiguity_guard_cap": 0.45, "final_confidence": guarded.confidence}
            parse_detail["confidence_breakdown"] = breakdown
        guarded.parse_detail = {
            **parse_detail,
            "multi_command_ambiguity": {
                "missing": missing,
                "reason": "batch state-changing sub-command requires explicit or inherited room and device",
            },
        }
        return guarded

    def _leading_action(self, text: str) -> str | None:
        if text.startswith("打开"):
            return "打开"
        if text.startswith("关闭"):
            return "关闭"
        return None

    def _trailing_action(self, text: str) -> tuple[str | None, str]:
        match = re.search(r"(?:都|全|全部)?(打开|关闭)$", text)
        if not match:
            return None, text
        return match.group(1), text[: match.start()].strip("把将都全全部的 ")

    def _action_and_subject(self, text: str) -> tuple[str | None, str]:
        leading = self._leading_action(text)
        if leading:
            return leading, text[len(leading) :]
        return self._trailing_action(text)

    def _has_action_word(self, text: str) -> bool:
        return any(word in text for word in ACTION_WORDS)

    def _action_from_intent(self, intent: str | None) -> str | None:
        if intent == "turn_on":
            return "打开"
        if intent == "turn_off":
            return "关闭"
        return None

    def _insert_room_after_action(self, text: str, room: str) -> str:
        prefix = ""
        body = text
        if body.startswith(("把", "将")):
            prefix = body[0]
            body = body[1:]
        for action in ACTION_WORDS:
            if body.startswith(action):
                return f"{action}{room}{body[len(action):]}"
        return f"{prefix}{room}{body}"

    def _first_room(self, text: str) -> str | None:
        rooms = self._ordered_rooms(text)
        return rooms[0] if rooms else None

    def _ordered_rooms(self, text: str) -> list[str]:
        matches: list[tuple[int, str]] = []
        for room, aliases in ROOM_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                position = text.find(alias)
                if position >= 0:
                    matches.append((position, room))
                    break
        return self._dedupe_ordered(matches)

    def _ordered_devices(self, text: str) -> list[str]:
        matches: list[tuple[int, int, str]] = []
        for device_type, aliases in DEVICE_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                position = text.find(alias)
                if position >= 0:
                    end = position + len(alias)
                    if self._overlaps_room_alias(text, position, end):
                        continue
                    matches.append((position, end, device_type))
                    break
        filtered = [
            item
            for item in matches
            if not any(
                other is not item and other[0] <= item[0] and other[1] >= item[1] and (other[1] - other[0]) > (item[1] - item[0])
                for other in matches
            )
        ]
        return self._dedupe_ordered([(start, device_type) for start, _, device_type in filtered])

    def _overlaps_room_alias(self, text: str, start: int, end: int) -> bool:
        for aliases in ROOM_ALIASES.values():
            for alias in aliases:
                room_start = text.find(alias)
                if room_start < 0:
                    continue
                room_end = room_start + len(alias)
                if start < room_end and end > room_start:
                    return True
        return False

    def _dedupe_ordered(self, matches: list[tuple[int, str]]) -> list[str]:
        ordered: list[str] = []
        for _, value in sorted(matches, key=lambda item: item[0]):
            if value not in ordered:
                ordered.append(value)
        return ordered
