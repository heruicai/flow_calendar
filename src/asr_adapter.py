"""Pluggable local ASR adapters with lazy model loading."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
from typing import Any

from src.voice_config import VoiceConfig


@dataclass(frozen=True)
class ASRCandidate:
    """One text hypothesis returned by a speech recognizer."""

    text: str
    confidence: float | None = None
    source: str = "unknown"


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
        key = (self.config.asr_model, self.config.device, self.config.compute_type)
        if key not in self._models:
            from faster_whisper import WhisperModel

            self._models[key] = WhisperModel(
                self.config.asr_model,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        return self._models[key]


class FunASRAdapter(BaseASRAdapter):
    """Optional local FunASR adapter. Import and model download remain opt-in."""

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
            from funasr import AutoModel

            self._model = AutoModel(model=self.config.asr_model)
        return self._model


class SenseVoiceASRAdapter(FunASRAdapter):
    """Optional local SenseVoice adapter with an explicit opt-in engine name."""

    def transcribe(self, audio_path, *, prompt: str = "", hotwords: list[str] | None = None) -> list[ASRCandidate]:
        model = self._get_model()
        result = model.generate(input=str(audio_path), hotword=" ".join(hotwords or []))
        text = result[0].get("text", "") if result else ""
        return [ASRCandidate(text=text, source="sensevoice")]


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
