"""Orchestrate local ASR, context bias, correction, and candidate reranking."""

from __future__ import annotations

import re

from src.asr_adapter import WhisperASRAdapter, create_asr_adapter
from src.asr_reranker import rerank_asr_candidates
from src.voice_config import get_voice_config
from src.voice_context_builder import build_voice_context


def transcribe_audio(audio_path, *, tasks: list[dict] | None = None, adapter=None, config=None) -> dict:
    """Transcribe one local recording and return traceable correction metadata."""
    settings = config or get_voice_config()
    context = build_voice_context(
        tasks,
        extra_terms=[term for term in re.split(r"[,，;；\s]+", settings.hotwords) if term],
        max_terms=settings.max_context_terms,
        initial_prompt=settings.initial_prompt,
    )
    recognizer = adapter or create_asr_adapter(settings)
    try:
        candidates = recognizer.transcribe(
            audio_path,
            prompt=context["prompt"] if settings.enable_context_bias else settings.initial_prompt,
            hotwords=context["hotwords"] if settings.enable_context_bias else [],
        )
    except (ImportError, ModuleNotFoundError):
        if isinstance(recognizer, WhisperASRAdapter):
            raise
        candidates = WhisperASRAdapter(settings).transcribe(
            audio_path,
            prompt=context["prompt"],
            hotwords=context["hotwords"],
        )
    if not candidates:
        raise ValueError("No clear speech was recognized.")

    known_titles = [str(task.get("title") or "") for task in (tasks or []) if isinstance(task, dict)]
    ranked = rerank_asr_candidates(
        candidates,
        context_terms=context["terms"] if settings.enable_semantic_correction else [],
        known_task_titles=known_titles if settings.enable_semantic_correction else [],
        correction_threshold=settings.correction_threshold,
        confirmation_threshold=settings.confirmation_threshold,
    )
    best = ranked[0]
    processed = best["postprocess"]
    parser_confidence = best["score"]
    high_risk_change = processed["corrected_text"] != processed["normalized_text"]
    should_auto_execute = (
        processed["confidence"] >= settings.correction_threshold
        and parser_confidence >= 0.75
        and not high_risk_change
    )
    return {
        **processed,
        "text": processed["corrected_text"],
        "mode": best["candidate"].source,
        "parser_confidence": parser_confidence,
        "should_auto_execute": should_auto_execute,
        "needs_confirmation": settings.enable_confirmation and (
            processed["needs_confirmation"] or high_risk_change or not should_auto_execute
        ),
        "candidates": ranked,
    }
