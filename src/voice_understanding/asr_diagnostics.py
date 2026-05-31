"""Structured local ASR diagnostics for accuracy investigations."""

from __future__ import annotations

import json


def build_asr_diagnostic(
    *,
    engine: str,
    model: str,
    language: str,
    audio_duration: float | None,
    raw_text: str,
    fallback_text: str = "",
    prompt: str = "",
) -> dict:
    return {
        "engine": engine,
        "model": model,
        "language": language,
        "beam_size": 5 if engine == "whisper" else None,
        "vad_enabled": True,
        "initial_prompt_injected": bool(prompt),
        "audio_duration": audio_duration,
        "raw_asr_text": raw_text,
        "fallback_asr_text": fallback_text,
    }


def print_asr_diagnostic(payload: dict) -> None:
    """Print one JSON line so local runs can be inspected or redirected."""
    print("[flowcal-asr] " + json.dumps(payload, ensure_ascii=False, sort_keys=True))
