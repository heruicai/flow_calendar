"""Explainable multi-factor ranking for semantic hypotheses."""

from __future__ import annotations

from src.voice_understanding.schema import TextHypothesis


def rank_hypotheses(hypotheses: list[TextHypothesis], *, context_terms=None) -> list[TextHypothesis]:
    terms = [str(term) for term in (context_terms or []) if term]
    for item in hypotheses:
        frame = item.semantic_frame
        if frame is None:
            continue
        context_match = 1.0 if any(term in item.text for term in terms) else 0.4
        calendar_validity = 1.0 if frame.intent != "unknown" else 0.0
        language_fluency = 0.85 if item.text else 0.0
        temporal_consistency = 1.0 if frame.completeness >= 0.8 else 0.4
        risk_penalty = 0.12 if frame.operation_risk == "high" else 0.04 if frame.operation_risk == "medium" else 0.0
        supported_context_expansion = any(expansion.slot == "context" for expansion in item.expansions)
        unsupported_change_penalty = 0.04 if item.expansions else 0.0
        final = (
            0.20 * item.asr_confidence
            + 0.25 * frame.completeness
            + 0.15 * calendar_validity
            + 0.15 * context_match
            + 0.10 * language_fluency
            + 0.10 * temporal_consistency
            + 0.05 * 0.5
            + (0.06 if supported_context_expansion else 0.0)
            - risk_penalty
            - unsupported_change_penalty
        )
        item.scores = {
            "asr": round(item.asr_confidence, 3),
            "semantic_completeness": round(frame.completeness, 3),
            "calendar_validity": round(calendar_validity, 3),
            "context_match": round(context_match, 3),
            "language_fluency": round(language_fluency, 3),
            "temporal_consistency": round(temporal_consistency, 3),
            "risk_penalty": round(risk_penalty, 3),
            "unsupported_change_penalty": round(unsupported_change_penalty, 3),
            "final": round(max(0.0, min(final, 1.0)), 3),
        }
    return sorted(hypotheses, key=lambda item: item.scores.get("final", 0.0), reverse=True)
