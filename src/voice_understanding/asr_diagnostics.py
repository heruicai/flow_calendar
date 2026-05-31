"""Structured local ASR diagnostics for accuracy investigations."""

from __future__ import annotations

import json
import importlib.util
import shutil


def build_asr_diagnostic(
    *,
    engine: str,
    model: str,
    language: str,
    audio_duration: float | None,
    raw_text: str,
    fallback_text: str = "",
    prompt: str = "",
    model_path: str = "",
    enable_dual_asr: bool = False,
    fallback_engine: str = "none",
    cleaned_text: str = "",
    metadata_tags_removed=(),
    fallback_used: bool = False,
    warning: str = "",
) -> dict:
    return {
        "engine": engine,
        "model": model,
        "model_path": model_path,
        "language": language,
        "beam_size": 5 if engine == "whisper" else None,
        "vad_enabled": True,
        "initial_prompt_injected": bool(prompt),
        "torchaudio_available": importlib.util.find_spec("torchaudio") is not None,
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "dual_asr_enabled": enable_dual_asr,
        "fallback_engine": fallback_engine,
        "fallback_used": fallback_used,
        "audio_duration": audio_duration,
        "raw_text": raw_text,
        "cleaned_text": cleaned_text or raw_text,
        "metadata_tags_removed": list(metadata_tags_removed),
        "fallback_asr_text": fallback_text,
        "warning": warning,
    }


def print_asr_diagnostic(payload: dict) -> None:
    """Print one JSON line so local runs can be inspected or redirected."""
    print("[flowcal-asr] " + json.dumps(payload, ensure_ascii=False, sort_keys=True))
