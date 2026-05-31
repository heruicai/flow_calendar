"""Conservative execute / confirm / clarify / reject policy."""

from __future__ import annotations

from src.voice_understanding.schema import AudioQuality, TextHypothesis, VoiceDecision


def decide(hypotheses: list[TextHypothesis], audio_quality: AudioQuality, *, execute_threshold: float = 0.88, margin_threshold: float = 0.12) -> VoiceDecision:
    if not audio_quality.acceptable:
        return VoiceDecision("reject", audio_quality.reason)
    if not hypotheses or hypotheses[0].semantic_frame is None:
        return VoiceDecision("reject", "no_parseable_hypothesis")
    top = hypotheses[0]
    frame = top.semantic_frame
    if frame.need_clarification or frame.completeness < 0.6:
        question = frame.clarification_question or "\u8bf7\u8865\u5145\u65e5\u7a0b\u7684\u5173\u952e\u4fe1\u606f\u3002"
        return VoiceDecision("clarify", "missing_or_ambiguous_fields", clarification_question=question)
    if frame.intent in {"delete_event", "update_event", "mark_completed"}:
        return VoiceDecision("confirm", f"{frame.intent}_requires_confirmation", _confirmation_prompt(frame))
    margin = top.scores.get("final", 0.0) - (hypotheses[1].scores.get("final", 0.0) if len(hypotheses) > 1 else 0.0)
    if top.expansions:
        return VoiceDecision("confirm", "expanded_hypothesis_requires_confirmation", _confirmation_prompt(frame))
    if top.scores.get("final", 0.0) >= execute_threshold and margin >= margin_threshold:
        return VoiceDecision("execute", "high_confidence_low_risk")
    return VoiceDecision("confirm", "confidence_or_margin_requires_confirmation", _confirmation_prompt(frame))


def _confirmation_prompt(frame) -> str:
    task = frame.task or {}
    title = task.get("title") or frame.query.get("keyword") or frame.target.get("keyword") or "\u8be5\u65e5\u7a0b"
    return f"\u6211\u7406\u89e3\u4e3a\uff1a{title}\u3002\u662f\u5426\u786e\u8ba4\uff1f"
