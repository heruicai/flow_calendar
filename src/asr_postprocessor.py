"""Context-aware local cleanup for ASR text."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from src.voice_adapter import normalize_chinese_text


KNOWN_ASR_ALIASES = {
    "蒜粉面试": "算法面试",
    "算粉面试": "算法面试",
    "算法免试": "算法面试",
    "组灰": "组会",
    "接止时间": "截止时间",
    "结止时间": "截止时间",
    "可nelPCA": "kernelPCA",
    "kernerPCA": "kernelPCA",
}


def postprocess_asr_text(
    raw_text: str,
    context_terms: list[str] | None = None,
    known_task_titles: list[str] | None = None,
    *,
    correction_threshold: float = 0.85,
    confirmation_threshold: float = 0.65,
) -> dict:
    """Normalize ASR output and apply only context-supported corrections."""
    normalized = _normalize_text(raw_text)
    corrected = normalized
    corrections = []
    alternatives = []
    vocabulary = _dedupe([*(known_task_titles or []), *(context_terms or [])])

    for source, target in KNOWN_ASR_ALIASES.items():
        if source not in corrected or target.casefold() not in {term.casefold() for term in vocabulary}:
            continue
        corrected = corrected.replace(source, target)
        corrections.append(_correction(source, target, 0.98, "context-supported ASR alias"))

    for target in vocabulary:
        replacement = _best_context_replacement(corrected, target)
        if not replacement:
            continue
        source, score = replacement
        if score >= correction_threshold:
            corrected = corrected.replace(source, target, 1)
            corrections.append(_correction(source, target, score, "context similarity"))
        elif score >= confirmation_threshold:
            alternatives.append({"from": source, "to": target, "confidence": round(score, 3)})

    correction_confidence = min(
        [item["confidence"] for item in corrections] or [1.0 if corrected == normalized else 0.0]
    )
    needs_confirmation = bool(alternatives) or correction_confidence < correction_threshold
    return {
        "raw_text": str(raw_text or ""),
        "normalized_text": normalized,
        "corrected_text": corrected,
        "corrections": corrections,
        "alternatives": alternatives,
        "confidence": round(correction_confidence, 3),
        "needs_confirmation": needs_confirmation,
    }


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", normalize_chinese_text(str(text or "")))
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.strip("，。？！,.!? ")


def _best_context_replacement(text: str, target: str) -> tuple[str, float] | None:
    target = str(target or "").strip()
    if len(target) < 2 or target.casefold() in text.casefold():
        return None
    best = None
    for size in range(max(2, len(target) - 2), min(len(text), len(target) + 2) + 1):
        for start in range(0, len(text) - size + 1):
            source = text[start:start + size]
            score = _similarity(source, target)
            if best is None or score > best[1]:
                best = (source, score)
    return best


def _similarity(source: str, target: str) -> float:
    text_score = SequenceMatcher(None, source.casefold(), target.casefold()).ratio()
    pinyin_source = _pinyin_signature(source)
    pinyin_target = _pinyin_signature(target)
    pinyin_score = (
        SequenceMatcher(None, pinyin_source, pinyin_target).ratio()
        if pinyin_source and pinyin_target
        else 0.0
    )
    return max(text_score, pinyin_score)


def _pinyin_signature(text: str) -> str:
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return ""
    return "".join(lazy_pinyin(text))


def _dedupe(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        term = normalize_chinese_text(str(value or "")).strip()
        key = term.casefold()
        if not term or key in seen:
            continue
        seen.add(key)
        result.append(term)
    return result


def _correction(source: str, target: str, confidence: float, reason: str) -> dict:
    return {
        "from": source,
        "to": target,
        "confidence": round(confidence, 3),
        "reason": reason,
    }
