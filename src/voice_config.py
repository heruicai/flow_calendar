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
    allow_cloud: bool = False
    enable_trace: bool = True
    trace_dir: str = "outputs/voice_traces"
    auto_execute_threshold: float = 0.88
    confirm_margin_threshold: float = 0.12
    reject_audio_quality_threshold: float = 0.35
    save_raw_audio: bool = False


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
        allow_cloud=_read_bool("VOICE_ALLOW_CLOUD", False),
        enable_trace=_read_bool("VOICE_ENABLE_TRACE", True),
        trace_dir=os.getenv("VOICE_TRACE_DIR", "outputs/voice_traces").strip(),
        auto_execute_threshold=_read_float("VOICE_AUTO_EXECUTE_THRESHOLD", 0.88),
        confirm_margin_threshold=_read_float("VOICE_CONFIRM_MARGIN_THRESHOLD", 0.12),
        reject_audio_quality_threshold=_read_float("VOICE_REJECT_AUDIO_QUALITY_THRESHOLD", 0.35),
        save_raw_audio=_read_bool("VOICE_SAVE_RAW_AUDIO", False),
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
