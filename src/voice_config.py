"""Environment-backed configuration for the local voice pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceConfig:
    """Runtime options with local, no-cost defaults."""

    asr_engine: str = "whisper"
    asr_model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "zh"
    initial_prompt: str = ""
    hotwords: str = ""
    enable_context_bias: bool = True
    enable_semantic_correction: bool = True
    enable_confirmation: bool = True
    correction_threshold: float = 0.85
    confirmation_threshold: float = 0.65
    max_context_terms: int = 80
    privacy_mode: str = "local"


def get_voice_config() -> VoiceConfig:
    """Read voice settings from environment variables."""
    return VoiceConfig(
        asr_engine=os.getenv("VOICE_ASR_ENGINE", "whisper").strip().lower(),
        asr_model=os.getenv("VOICE_ASR_MODEL", os.getenv("FLOWCAL_WHISPER_MODEL", "base")).strip(),
        device=os.getenv("VOICE_ASR_DEVICE", "cpu").strip(),
        compute_type=os.getenv("VOICE_ASR_COMPUTE_TYPE", "int8").strip(),
        language=os.getenv("VOICE_ASR_LANGUAGE", "zh").strip(),
        initial_prompt=os.getenv("VOICE_ASR_INITIAL_PROMPT", "").strip(),
        hotwords=os.getenv("VOICE_ASR_HOTWORDS", "").strip(),
        enable_context_bias=_read_bool("VOICE_ENABLE_CONTEXT_BIAS", True),
        enable_semantic_correction=_read_bool("VOICE_ENABLE_SEMANTIC_CORRECTION", True),
        enable_confirmation=_read_bool("VOICE_ENABLE_CONFIRMATION", True),
        correction_threshold=_read_float("VOICE_CORRECTION_THRESHOLD", 0.85),
        confirmation_threshold=_read_float("VOICE_CONFIRMATION_THRESHOLD", 0.65),
        max_context_terms=_read_int("VOICE_MAX_CONTEXT_TERMS", 80),
        privacy_mode=os.getenv("VOICE_PRIVACY_MODE", "local").strip().lower(),
    )


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _read_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _read_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default
