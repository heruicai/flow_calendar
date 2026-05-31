"""Compare independent local ASR outputs before semantic execution."""

from __future__ import annotations

from difflib import SequenceMatcher

from src.voice_understanding.semantic_parser import parse_semantic_frame
from src.voice_understanding.text_normalizer import normalize_text


def compare_asr_candidates(candidates) -> dict:
    distinct = []
    for candidate in candidates:
        text = normalize_text(candidate.text)
        if text and text not in {item["text"] for item in distinct}:
            distinct.append({"text": text, "source": candidate.source})
    if len(distinct) < 2:
        return {
            "compared": False,
            "similarity": 1.0,
            "requires_confirmation": False,
            "reason": "single_or_identical_asr_output",
        }
    left, right = distinct[:2]
    similarity = SequenceMatcher(None, left["text"], right["text"]).ratio()
    left_frame = parse_semantic_frame(left["text"])
    right_frame = parse_semantic_frame(right["text"])
    completeness_differs = (left_frame.completeness >= 0.8) != (right_frame.completeness >= 0.8)
    requires_confirmation = similarity < 0.85 or completeness_differs
    reason = (
        "one_asr_candidate_has_more_complete_calendar_semantics"
        if completeness_differs
        else "asr_outputs_diverge"
        if similarity < 0.85
        else "asr_outputs_agree"
    )
    return {
        "compared": True,
        "sources": [left["source"], right["source"]],
        "texts": [left["text"], right["text"]],
        "similarity": round(similarity, 3),
        "requires_confirmation": requires_confirmation,
        "reason": reason,
    }
