"""Compatibility facade for the productized local voice understanding engine."""

from __future__ import annotations

from dataclasses import asdict

from src.voice_config import get_voice_config
from src.voice_understanding.pipeline import understand_voice


def transcribe_audio(audio_path, *, tasks: list[dict] | None = None, adapter=None, config=None) -> dict:
    """Transcribe locally and preserve the legacy response fields."""
    settings = config or get_voice_config()
    understanding = understand_voice(
        audio_path,
        tasks=tasks,
        config=settings,
        adapter=adapter,
        # Compatibility tests use mock paths. Real recordings are checked.
        check_audio=adapter is None,
    )
    best = understanding.best
    if best is None:
        raise ValueError("No clear speech was recognized.")
    frame = best.semantic_frame
    expansions = [asdict(item) for item in best.expansions]
    alternatives = [
        {"text": item.text, "score": item.scores.get("final", 0.0)}
        for item in understanding.top_hypotheses[1:4]
    ]
    return {
        "raw_text": best.source_text,
        "normalized_text": best.source_text,
        "corrected_text": best.text,
        "text": best.text,
        "mode": best.source,
        "confidence": best.scores.get("final", 0.0),
        "parser_confidence": frame.confidence if frame else 0.0,
        "corrections": expansions,
        "alternatives": alternatives,
        "needs_confirmation": understanding.decision.action in {"confirm", "clarify"},
        "should_auto_execute": understanding.decision.action == "execute",
        "understanding": understanding.to_dict(),
        "decision": asdict(understanding.decision),
        "semantic_frame": asdict(frame) if frame else None,
        "top_hypotheses": [asdict(item) for item in understanding.top_hypotheses[:5]],
        "trace_id": understanding.trace_id,
        "candidates": [asdict(item) for item in understanding.top_hypotheses],
    }
