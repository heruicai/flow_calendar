"""Pluggable local ASR adapters with lazy model loading."""

from __future__ import annotations

import re
from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from typing import Any

from src.voice_config import VoiceConfig


@dataclass(frozen=True)
class ASRCandidate:
    """One text hypothesis returned by a speech recognizer."""

    text: str
    confidence: float | None = None
    source: str = "unknown"
    raw_text: str | None = None
    metadata_tags_removed: tuple[str, ...] = ()


class OptionalASRDependencyError(ModuleNotFoundError):
    """Explain how to enable an optional local ASR engine."""

    def __init__(self, engine: str):
        self.engine = engine
        super().__init__(
            f"Local {engine} dependencies are missing. Install with: "
            "pip install funasr modelscope"
        )


class LocalASRModelError(RuntimeError):
    """Explain how to prepare an opt-in local model without silent downloads."""


SENSEVOICE_TAG_PATTERN = re.compile(r"<\|([^|>]+)\|>")


def clean_sensevoice_text(text: str) -> str:
    """Remove arbitrary SenseVoice metadata tags from natural-language text."""
    return SENSEVOICE_TAG_PATTERN.sub("", str(text or "")).strip()


def get_sensevoice_metadata_tags(text: str) -> tuple[str, ...]:
    """Return removed SenseVoice metadata tags for local diagnostics."""
    return tuple(SENSEVOICE_TAG_PATTERN.findall(str(text or "")))


class BaseASRAdapter:
    """Base interface implemented by local ASR engines."""

    def transcribe(self, audio_path, *, prompt: str = "", hotwords: list[str] | None = None) -> list[ASRCandidate]:
        raise NotImplementedError


class WhisperASRAdapter(BaseASRAdapter):
    """Local faster-whisper adapter. Models are loaded on first use."""

    _models: dict[tuple[str, str, str], Any] = {}

    def __init__(self, config: VoiceConfig):
        self.config = config

    def transcribe(self, audio_path, *, prompt: str = "", hotwords: list[str] | None = None) -> list[ASRCandidate]:
        model = self._get_model()
        kwargs = {
            "language": self.config.language,
            "vad_filter": True,
            "beam_size": 5,
            "temperature": 0,
            "initial_prompt": prompt or None,
            "hotwords": " ".join(hotwords or []) or None,
        }
        supported = signature(model.transcribe).parameters
        segments, info = model.transcribe(
            str(audio_path),
            **{key: value for key, value in kwargs.items() if key in supported and value is not None},
        )
        text = "".join(segment.text for segment in segments).strip()
        confidence = getattr(info, "language_probability", None)
        return [ASRCandidate(text=text, confidence=confidence, source="whisper")]

    def _get_model(self):
        model_path = Path(self.config.whisper_model_path).expanduser() if self.config.whisper_model_path else None
        if model_path and not model_path.exists():
            raise LocalASRModelError(f"Local Whisper model path does not exist: {model_path}")
        if not model_path and not self.config.whisper_allow_download:
            raise LocalASRModelError(
                "Local Whisper fallback is disabled because VOICE_WHISPER_ALLOW_DOWNLOAD=0 "
                "and VOICE_WHISPER_MODEL_PATH is not configured."
            )
        model_ref = str(model_path) if model_path else self.config.whisper_model
        key = (model_ref, self.config.device, self.config.compute_type)
        if key not in self._models:
            from faster_whisper import WhisperModel

            self._models[key] = WhisperModel(
                model_ref,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        return self._models[key]


class FunASRAdapter(BaseASRAdapter):
    """Optional local FunASR adapter. Import and model download remain opt-in."""

    engine_name = "FunASR"

    def __init__(self, config: VoiceConfig):
        self.config = config
        self._model = None

    def transcribe(self, audio_path, *, prompt: str = "", hotwords: list[str] | None = None) -> list[ASRCandidate]:
        model = self._get_model()
        result = model.generate(input=str(audio_path), hotword=" ".join(hotwords or []))
        text = result[0].get("text", "") if result else ""
        return [ASRCandidate(text=text, source="funasr")]

    def _get_model(self):
        if self._model is None:
            try:
                from funasr import AutoModel
            except ModuleNotFoundError as exc:
                raise OptionalASRDependencyError(self.engine_name) from exc

            self._model = AutoModel(model=self.config.asr_model)
        return self._model


class SenseVoiceASRAdapter(FunASRAdapter):
    """Optional local SenseVoice adapter with an explicit opt-in engine name."""

    engine_name = "SenseVoice"

    def transcribe(self, audio_path, *, prompt: str = "", hotwords: list[str] | None = None) -> list[ASRCandidate]:
        model = self._get_model()
        result = model.generate(input=str(audio_path), hotword=" ".join(hotwords or []))
        raw_text = result[0].get("text", "") if result else ""
        text = clean_sensevoice_text(raw_text)
        return [
            ASRCandidate(
                text=text,
                source="sensevoice",
                raw_text=raw_text,
                metadata_tags_removed=get_sensevoice_metadata_tags(raw_text),
            )
        ]

    def _get_model(self):
        if self._model is None:
            try:
                from funasr import AutoModel
            except ModuleNotFoundError as exc:
                raise OptionalASRDependencyError(self.engine_name) from exc
            model_path = Path(self.config.sensevoice_model_path).expanduser()
            if model_path.exists():
                self._model = AutoModel(model=str(model_path), disable_update=True)
            elif self.config.sensevoice_allow_download:
                self._model = AutoModel(model=self.config.asr_model)
            else:
                raise LocalASRModelError(
                    f"Local SenseVoice model path does not exist: {model_path}. "
                    "Set VOICE_SENSEVOICE_MODEL_PATH or explicitly allow downloads with "
                    "VOICE_SENSEVOICE_ALLOW_DOWNLOAD=1."
                )
        return self._model


class MockASRAdapter(BaseASRAdapter):
    """Deterministic adapter for pure-function tests."""

    def __init__(self, candidates: list[ASRCandidate] | None = None):
        self.candidates = candidates or []

    def transcribe(self, audio_path, *, prompt: str = "", hotwords: list[str] | None = None) -> list[ASRCandidate]:
        return list(self.candidates)


def create_asr_adapter(config: VoiceConfig) -> BaseASRAdapter:
    """Create the configured local adapter without loading a model."""
    if config.asr_engine == "mock":
        return MockASRAdapter()
    if config.asr_engine == "sensevoice":
        return SenseVoiceASRAdapter(config)
    if config.asr_engine == "funasr":
        return FunASRAdapter(config)
    return WhisperASRAdapter(config)
