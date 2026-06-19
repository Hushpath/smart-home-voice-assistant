import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.command_parser import LOW_CONFIDENCE_THRESHOLD, CommandParser, ParseResult


SUPPORTED_DIALECTS = {"auto", "mandarin", "cantonese", "southwest", "northeast"}
STATE_CHANGING_INTENTS = {
    "turn_on",
    "turn_off",
    "set_temperature",
    "set_brightness",
    "set_volume",
    "set_property",
    "run_scene",
    "create_reminder",
}
PUNCTUATION_PATTERN = re.compile(r"[\s，。！？、；：,.!?;\"'“”‘’（）()\[\]【】]")
CHINESE_NUMBER_PATTERN = re.compile(r"[零〇一二两三四五六七八九十]{1,4}")


@dataclass
class DialectNormalizationResult:
    original_text: str = ""
    normalized_text: str = ""
    detected_dialect: str = "mandarin"
    requested_dialect: str = "auto"
    dialect_matches: list[str] = field(default_factory=list)
    asr_corrections: list[str] = field(default_factory=list)
    removed_fillers: list[str] = field(default_factory=list)
    number_conversions: list[str] = field(default_factory=list)
    normalization_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DialectNormalizer:
    filler_words = ["可不可以", "能不能", "帮我", "麻烦", "请", "一下", "现在", "给我"]
    cantonese_markers = ["冷气", "冷氣", "声量", "聲量", "熄灯", "熄燈", "熄", "睇下", "睇吓", "食药", "食藥", "瞓觉", "瞓覺", "返屋企", "客廳", "燈"]
    southwest_markers = ["开哈", "关哈"]
    northeast_markers = ["开开", "关上"]

    asr_corrections = {
        "客厅等": "客厅灯",
        "卧室等": "卧室灯",
        "空条": "空调",
        "空跳": "空调",
        "电视及": "电视机",
        "音凉": "音量",
        "两度": "亮度",
        "二十留": "二十六",
    }
    common_replacements = {
        "今晚": "晚上",
        "设置为": "设置",
        "调整到": "设置",
        "調到": "设置",
        "调到": "设置",
        "调成": "设置",
        "设为": "设置",
        "整到": "设置",
        "整成": "设置",
        "打开": "打开",
        "关闭": "关闭",
    }
    cantonese_replacements = {
        "返屋企模式": "回家模式",
        "瞓觉模式": "睡眠模式",
        "瞓覺模式": "睡眠模式",
        "开灯": "打开灯",
        "開燈": "打开灯",
        "熄灯": "关闭灯",
        "熄燈": "关闭灯",
        "关灯": "关闭灯",
        "關燈": "关闭灯",
        "电视机": "电视",
        "電視機": "电视",
        "灯光": "灯",
        "燈光": "灯",
        "电灯": "灯",
        "電燈": "灯",
        "燈": "灯",
        "冷气": "空调",
        "冷氣": "空调",
        "电视": "电视",
        "電視": "电视",
        "客厅": "客厅",
        "客廳": "客厅",
        "大厅": "客厅",
        "大廳": "客厅",
        "睡房": "卧室",
        "厨房": "厨房",
        "廚房": "厨房",
        "书房": "书房",
        "書房": "书房",
        "声量": "音量",
        "聲量": "音量",
        "声音": "音量",
        "聲音": "音量",
        "光度": "亮度",
        "温度": "温度",
        "溫度": "温度",
        "度数": "温度",
        "度數": "温度",
        "今日": "今天",
        "听日": "明天",
        "聽日": "明天",
        "睇下": "查询",
        "睇吓": "查询",
        "食药": "吃药",
        "食藥": "吃药",
        "较到": "设置",
        "調到": "设置",
        "调到": "设置",
        "整到": "设置",
        "开启": "打开",
        "开": "打开",
        "開": "打开",
        "关闭": "关闭",
        "关": "关闭",
        "關": "关闭",
        "熄": "关闭",
        "房": "卧室",
    }
    southwest_replacements = {
        "开哈": "打开",
        "关哈": "关闭",
        "整到": "设置",
        "整成": "设置",
        "冷气": "空调",
    }
    northeast_replacements = {
        "整亮点": "设置亮度",
        "开开": "打开",
        "关上": "关闭",
        "整到": "设置",
    }

    def __init__(self):
        self.number_parser = CommandParser()

    def normalize(self, text: str | None, dialect: str | None = "auto") -> DialectNormalizationResult:
        requested_dialect = self._safe_dialect(dialect)
        original_text = "" if text is None else text.strip()
        normalized_text = unicodedata.normalize("NFKC", original_text)
        result = DialectNormalizationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            requested_dialect=requested_dialect,
            detected_dialect=self.detect_dialect(normalized_text, requested_dialect),
        )
        result.normalization_steps.append("统一全角/半角符号")

        normalized_text = PUNCTUATION_PATTERN.sub("", normalized_text)
        result.normalization_steps.append("去除空白和常见标点")

        normalized_text = self._remove_fillers(normalized_text, result)
        normalized_text = self._apply_replacements(normalized_text, self.asr_corrections, result.asr_corrections)

        replacements = dict(self.common_replacements)
        replacements.update(self._dialect_replacements(result.detected_dialect))
        normalized_text = self._apply_replacements(normalized_text, replacements, result.dialect_matches)

        normalized_text = self._convert_numbers(normalized_text, result)
        result.normalized_text = normalized_text
        return result

    def detect_dialect(self, text: str, requested_dialect: str | None = "auto") -> str:
        requested_dialect = self._safe_dialect(requested_dialect)
        if requested_dialect != "auto":
            return requested_dialect
        if any(marker in text for marker in self.cantonese_markers):
            return "cantonese"
        if any(marker in text for marker in self.southwest_markers):
            return "southwest"
        if any(marker in text for marker in self.northeast_markers):
            return "northeast"
        return "mandarin"

    def _safe_dialect(self, dialect: str | None) -> str:
        value = (dialect or "auto").strip().lower()
        return value if value in SUPPORTED_DIALECTS else "auto"

    def _dialect_replacements(self, detected_dialect: str) -> dict[str, str]:
        if detected_dialect == "cantonese":
            return self.cantonese_replacements
        if detected_dialect == "southwest":
            return self.southwest_replacements
        if detected_dialect == "northeast":
            return self.northeast_replacements
        return {}

    def _remove_fillers(self, text: str, result: DialectNormalizationResult) -> str:
        updated = text
        for filler in sorted(self.filler_words, key=len, reverse=True):
            if filler in updated:
                updated = updated.replace(filler, "")
                result.removed_fillers.append(filler)
        if result.removed_fillers:
            result.normalization_steps.append("过滤口语填充词")
        return updated

    def _apply_replacements(self, text: str, replacements: dict[str, str], records: list[str]) -> str:
        if not replacements or not text:
            return text
        ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
        output: list[str] = []
        index = 0
        while index < len(text):
            matched = None
            for source, target in ordered:
                if text.startswith(source, index):
                    matched = (source, target)
                    break
            if matched is None:
                output.append(text[index])
                index += 1
                continue
            source, target = matched
            output.append(target)
            if source != target:
                record = f"{source} -> {target}"
                if record not in records:
                    records.append(record)
            index += len(source)
        return "".join(output)

    def _convert_numbers(self, text: str, result: DialectNormalizationResult) -> str:
        time_info = self.number_parser._extract_time(text)
        if time_info.get("value") and time_info.get("matched_text"):
            result.number_conversions.append(f"{time_info['matched_text']} -> {time_info['value']}")

        def replace(match: re.Match) -> str:
            source = match.group(0)
            value = self.number_parser._to_int(source)
            if value is None:
                return source
            record = f"{source} -> {value}"
            if record not in result.number_conversions:
                result.number_conversions.append(record)
            return str(value)

        updated = CHINESE_NUMBER_PATTERN.sub(replace, text)
        if result.number_conversions:
            result.normalization_steps.append("中文数字转阿拉伯数字")
        return updated


def normalize_and_parse_command(
    command: str | None,
    parser: CommandParser | None = None,
    dialect: str | None = "auto",
) -> tuple[ParseResult, DialectNormalizationResult]:
    parser = parser or CommandParser()
    normalizer = DialectNormalizer()
    normalization = normalizer.normalize(command, dialect=dialect)
    parsed = parser.parse(normalization.normalized_text)
    _attach_normalization(parsed, normalization)
    _adjust_confidence(parsed, normalization)
    return parsed, normalization


def _attach_normalization(parsed: ParseResult, normalization: DialectNormalizationResult) -> None:
    parser_normalized_text = parsed.normalized_text
    parsed.original_text = normalization.original_text
    parsed.normalized_text = normalization.normalized_text
    parsed.parse_detail["parser_normalized_text"] = parser_normalized_text
    parsed.parse_detail["dialect_normalization"] = normalization.to_dict()


def _adjust_confidence(parsed: ParseResult, normalization: DialectNormalizationResult) -> None:
    adjustments: list[str] = []
    confidence = parsed.confidence
    breakdown = parsed.parse_detail.get("confidence_breakdown")
    if not isinstance(breakdown, dict):
        breakdown = None
    if normalization.asr_corrections:
        if parsed.match_type == "exact":
            parsed.match_type = "fuzzy"
        penalty = min(0.12, len(normalization.asr_corrections) * 0.04)
        confidence -= penalty
        adjustments.append(f"识别文本纠错降低 {penalty:.2f}")
        if breakdown is not None:
            breakdown["asr_correction_penalty"] = round(breakdown.get("asr_correction_penalty", 0.0) + penalty, 2)
    if parsed.match_type == "fuzzy" and len(parsed.matched_keywords) > 1:
        confidence -= 0.04
        adjustments.append("多处模糊匹配降低 0.04")
        if breakdown is not None:
            breakdown["multi_fuzzy_penalty"] = round(breakdown.get("multi_fuzzy_penalty", 0.0) + 0.04, 2)

    parsed.confidence = round(max(0.0, min(confidence, 0.99)), 2)
    if breakdown is not None:
        breakdown["final_confidence"] = parsed.confidence
    if adjustments:
        parsed.parse_detail["confidence_adjustments"] = adjustments

    if parsed.valid and parsed.confidence < LOW_CONFIDENCE_THRESHOLD:
        if parsed.intent in STATE_CHANGING_INTENTS:
            parsed.valid = False
            parsed.error_code = "LOW_CONFIDENCE_COMMAND"
            parsed.message = "指令置信度较低，请换一种说法，或使用文本输入。"
        else:
            parsed.message = f"{parsed.message}，但置信度较低。"
