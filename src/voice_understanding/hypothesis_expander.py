"""Generate contextual alternatives instead of silently rewriting text."""

from __future__ import annotations

from difflib import SequenceMatcher

from src.voice_understanding.schema import Expansion, TextHypothesis
from src.voice_understanding.text_normalizer import normalize_text


TIME_SLOT_TERMS = tuple(f"{value}\u70b9" for value in "\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341")


def expand_hypotheses(text: str, *, asr_confidence: float = 0.5, source: str = "unknown", context_terms=None, max_candidates: int = 12) -> list[TextHypothesis]:
    normalized = normalize_text(text)
    result = [TextHypothesis(normalized, normalized, asr_confidence, source)]
    terms = _dedupe([*(context_terms or []), *TIME_SLOT_TERMS])
    for target in terms:
        for source_text, score in _matching_segments(normalized, target):
            if source_text == target or score < 0.72:
                continue
            replacement = normalized.replace(source_text, target, 1)
            if replacement == normalized:
                continue
            slot = "time" if target in TIME_SLOT_TERMS else "context"
            if slot == "time" and (len(source_text) != 2 or not source_text.endswith("\u70b9")):
                continue
            reason = "phonetic_match_and_valid_time_slot" if slot == "time" else "phonetic_match_and_context_slot"
            result.append(TextHypothesis(
                replacement,
                normalized,
                asr_confidence,
                source,
                [Expansion(source_text, target, reason, round(score, 3), slot)],
            ))
            if len(result) >= max_candidates:
                return _dedupe_hypotheses(result)
    return _dedupe_hypotheses(result)


def _matching_segments(text: str, target: str):
    if not target or target in text:
        return []
    matches = []
    for size in range(max(2, len(target) - 1), min(len(text), len(target) + 1) + 1):
        for start in range(len(text) - size + 1):
            source = text[start:start + size]
            score = _phonetic_similarity(source, target)
            if score >= 0.72:
                matches.append((source, score))
    return sorted(matches, key=lambda item: item[1], reverse=True)[:1]


def _phonetic_similarity(source: str, target: str) -> float:
    try:
        from pypinyin import lazy_pinyin
        left = "".join(lazy_pinyin(source))
        right = "".join(lazy_pinyin(target))
    except ImportError:
        left, right = source, target
    return SequenceMatcher(None, left.casefold(), right.casefold()).ratio()


def _dedupe(values):
    return list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))


def _dedupe_hypotheses(values):
    seen = set()
    result = []
    for item in values:
        if item.text not in seen:
            result.append(item)
            seen.add(item.text)
    return result
