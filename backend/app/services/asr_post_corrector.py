import re
import unicodedata
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.models import Device, DeviceAlias, Room, Scene, User
from app.services.command_parser import DEVICE_ALIASES, ROOM_ALIASES, SCENE_KEYWORDS
from app.services.device_capabilities import all_option_aliases, all_property_aliases


STATIC_CORRECTIONS = {
    "冰香": "冰箱",
    "冰霜": "冰箱",
    "冰想": "冰箱",
    "派风扇": "排风扇",
    "拍风扇": "排风扇",
    "排风山": "排风扇",
    "空气进化器": "空气净化器",
    "空气净话器": "空气净化器",
    "空气清化器": "空气净化器",
    "扫地机气人": "扫地机器人",
    "扫地机人": "扫地机器人",
    "窗连": "窗帘",
    "窗帘儿": "窗帘",
    "加湿气": "加湿器",
    "加时器": "加湿器",
    "烟物传感器": "烟雾传感器",
    "烟雾转感器": "烟雾传感器",
    "电是": "电视",
    "智能查座": "智能插座",
}

ACTION_CONTEXT_PATTERN = re.compile(r"(打开|开启|启动|关闭|关掉|停止|设置|设为|调到|调成|调整|查询|查看|换到|切到)")
MIN_FUZZY_SCORE = 0.86
MIN_FUZZY_GAP = 0.04


@dataclass(frozen=True)
class CorrectionItem:
    source: str
    target: str
    correction_type: str
    score: float
    reason: str


@dataclass
class CorrectionResult:
    original_text: str = ""
    corrected_text: str = ""
    corrections: list[CorrectionItem] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.corrected_text != self.original_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "corrected_text": self.corrected_text,
            "changed": self.changed,
            "corrections": [asdict(item) for item in self.corrections],
        }


@dataclass(frozen=True)
class LexiconTerm:
    text: str
    term_type: str
    source: str


class ASRPostCorrector:
    def correct(self, text: str | None, db: Session | None = None, user: User | None = None) -> CorrectionResult:
        original = "" if text is None else text.strip()
        if not original:
            return CorrectionResult(original_text=original, corrected_text=original)

        corrected = unicodedata.normalize("NFKC", original)
        corrections: list[CorrectionItem] = []
        corrected = self._apply_static_corrections(corrected, corrections)
        corrected = self._apply_fuzzy_corrections(corrected, self._build_lexicon(db, user), corrections)
        return CorrectionResult(original_text=original, corrected_text=corrected, corrections=corrections)

    def _apply_static_corrections(self, text: str, corrections: list[CorrectionItem]) -> str:
        corrected = text
        for source, target in sorted(STATIC_CORRECTIONS.items(), key=lambda item: len(item[0]), reverse=True):
            if source not in corrected:
                continue
            corrected = corrected.replace(source, target)
            corrections.append(
                CorrectionItem(
                    source=source,
                    target=target,
                    correction_type="static",
                    score=1.0,
                    reason="static_asr_correction",
                )
            )
        return corrected

    def _apply_fuzzy_corrections(
        self,
        text: str,
        lexicon: list[LexiconTerm],
        corrections: list[CorrectionItem],
    ) -> str:
        replacements: list[tuple[int, int, LexiconTerm, str, float]] = []
        for start, end, source, term, score in self._find_fuzzy_matches(text, lexicon):
            if any(start < existing_end and end > existing_start for existing_start, existing_end, *_ in replacements):
                continue
            replacements.append((start, end, term, source, score))

        if not replacements:
            return text

        corrected = text
        for start, end, term, source, score in sorted(replacements, key=lambda item: item[0], reverse=True):
            corrected = corrected[:start] + term.text + corrected[end:]
            corrections.append(
                CorrectionItem(
                    source=source,
                    target=term.text,
                    correction_type=term.term_type,
                    score=round(score, 2),
                    reason=term.source,
                )
            )
        return corrected

    def _find_fuzzy_matches(self, text: str, lexicon: list[LexiconTerm]) -> list[tuple[int, int, str, LexiconTerm, float]]:
        matches: list[tuple[int, int, str, LexiconTerm, float]] = []
        for term in lexicon:
            if len(term.text) < 3 or term.text in text:
                continue
            if not self._has_action_context(text, term):
                continue
            best = self._best_match_for_term(text, term)
            if best is None:
                continue
            start, end, source, score, second_score = best
            if score < MIN_FUZZY_SCORE or score - second_score < MIN_FUZZY_GAP:
                continue
            matches.append((start, end, source, term, score))
        return sorted(matches, key=lambda item: (item[0], -(item[1] - item[0])))

    def _best_match_for_term(self, text: str, term: LexiconTerm) -> tuple[int, int, str, float, float] | None:
        best: tuple[int, int, str, float] | None = None
        second_score = 0.0
        term_length = len(term.text)
        for size in range(max(3, term_length - 1), term_length + 2):
            if size > len(text):
                continue
            for start in range(0, len(text) - size + 1):
                source = text[start : start + size]
                if not self._candidate_can_replace(source, term.text):
                    continue
                score = SequenceMatcher(None, source, term.text).ratio()
                if best is None or score > best[3]:
                    second_score = best[3] if best else 0.0
                    best = (start, start + size, source, score)
                elif score > second_score:
                    second_score = score
        if best is None:
            return None
        start, end, source, score = best
        return start, end, source, score, second_score

    def _candidate_can_replace(self, source: str, target: str) -> bool:
        if source == target:
            return False
        if re.search(r"[A-Za-z0-9]", source) or re.search(r"[A-Za-z0-9]", target):
            return False
        if re.search(r"\d", source):
            return False
        return True

    def _has_action_context(self, text: str, term: LexiconTerm) -> bool:
        if term.term_type in {"property", "option"}:
            return "设置" in text or "调" in text or "换" in text or "切" in text
        return bool(ACTION_CONTEXT_PATTERN.search(text))

    def _build_lexicon(self, db: Session | None, user: User | None) -> list[LexiconTerm]:
        terms: list[LexiconTerm] = []
        self._add_static_terms(terms)
        if db is not None and user is not None:
            self._add_database_terms(db, user, terms)
        return self._dedupe_terms(terms)

    def _add_static_terms(self, terms: list[LexiconTerm]) -> None:
        for room, aliases in ROOM_ALIASES.items():
            terms.append(LexiconTerm(room, "room", "static_room"))
            terms.extend(LexiconTerm(alias, "room", "static_room_alias") for alias in aliases)
        for device_type, aliases in DEVICE_ALIASES.items():
            terms.extend(LexiconTerm(alias, "device", f"static_device_alias:{device_type}") for alias in aliases)
        for scene in SCENE_KEYWORDS:
            terms.append(LexiconTerm(scene, "scene", "static_scene"))
        terms.extend(LexiconTerm(alias, "property", "device_capability") for alias in all_property_aliases())
        terms.extend(LexiconTerm(str(alias), "option", "device_capability_option") for alias, _ in all_option_aliases())

    def _add_database_terms(self, db: Session, user: User, terms: list[LexiconTerm]) -> None:
        room_query = db.query(Room)
        if user.home_id is not None:
            room_query = room_query.filter(Room.home_id == user.home_id)
        rooms = room_query.all()
        for room in rooms:
            terms.append(LexiconTerm(room.name, "room", "db_room"))

        device_query = db.query(Device).join(Room)
        if user.home_id is not None:
            device_query = device_query.filter(Room.home_id == user.home_id)
        devices = device_query.all()
        for device in devices:
            room_name = device.room.name if device.room else ""
            terms.append(LexiconTerm(device.name, "device", "db_device"))
            if room_name:
                terms.append(LexiconTerm(f"{room_name}{device.name}", "device", "db_room_device"))

        aliases = db.query(DeviceAlias).filter(DeviceAlias.user_id == user.id).all()
        for alias in aliases:
            if alias.alias:
                terms.append(LexiconTerm(alias.alias, "device_alias", "db_device_alias"))

        scene_query = db.query(Scene)
        if user.home_id is not None:
            scene_query = scene_query.filter(Scene.home_id == user.home_id)
        for scene in scene_query.all():
            terms.append(LexiconTerm(scene.name, "scene", "db_scene"))

    def _dedupe_terms(self, terms: list[LexiconTerm]) -> list[LexiconTerm]:
        deduped: dict[str, LexiconTerm] = {}
        for term in terms:
            text = term.text.strip()
            if len(text) < 2:
                continue
            deduped.setdefault(text, LexiconTerm(text, term.term_type, term.source))
        return sorted(deduped.values(), key=lambda item: len(item.text), reverse=True)


def correct_asr_text(text: str | None, db: Session | None = None, user: User | None = None) -> CorrectionResult:
    return ASRPostCorrector().correct(text, db=db, user=user)
