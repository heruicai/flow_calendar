"""Score local ASR hypotheses using calendar-domain evidence."""

from __future__ import annotations

import re

from src.asr_adapter import ASRCandidate
from src.asr_postprocessor import postprocess_asr_text
from src.command_parser import parse_command


def rerank_asr_candidates(
    candidates: list[ASRCandidate],
    *,
    context_terms: list[str] | None = None,
    known_task_titles: list[str] | None = None,
    correction_threshold: float = 0.85,
    confirmation_threshold: float = 0.65,
) -> list[dict]:
    """Return highest-value candidate first with post-processing metadata."""
    ranked = []
    for candidate in candidates:
        processed = postprocess_asr_text(
            candidate.text,
            context_terms=context_terms,
            known_task_titles=known_task_titles,
            correction_threshold=correction_threshold,
            confirmation_threshold=confirmation_threshold,
        )
        parsed = parse_command(processed["corrected_text"])
        score = _candidate_score(candidate, processed, parsed, context_terms or [], known_task_titles or [])
        ranked.append({"candidate": candidate, "postprocess": processed, "score": round(score, 3)})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def _candidate_score(candidate, processed, parsed, context_terms, known_task_titles) -> float:
    text = processed["corrected_text"]
    score = 0.25 if candidate.confidence is None else 0.35 * candidate.confidence
    if any(term and term in text for term in known_task_titles):
        score += 0.2
    if any(term and term in text for term in context_terms):
        score += 0.12
    if parsed.get("intent") and not parsed.get("need_clarification"):
        score += 0.18
    if re.search(r"(今天|明天|后天|周[一二三四五六日天]|上午|下午|晚上|\d{1,2}[:点])", text):
        score += 0.1
    if (parsed.get("task") or {}).get("title") or (parsed.get("target") or {}).get("keyword"):
        score += 0.1
    if processed.get("needs_confirmation"):
        score -= 0.08
    return max(0.0, min(score, 1.0))
