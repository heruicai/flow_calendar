"""Shared data structures for the local voice understanding pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AudioQuality:
    score: float = 1.0
    acceptable: bool = True
    reason: str = "not_checked"
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None


@dataclass(frozen=True)
class ASRHypothesis:
    text: str
    confidence: float = 0.5
    source: str = "unknown"


@dataclass(frozen=True)
class Expansion:
    source: str
    target: str
    reason: str
    confidence: float
    slot: str = "context"


@dataclass
class TextHypothesis:
    text: str
    source_text: str
    asr_confidence: float = 0.5
    source: str = "unknown"
    expansions: list[Expansion] = field(default_factory=list)
    semantic_frame: "SemanticFrame | None" = None
    scores: dict[str, float] = field(default_factory=dict)


@dataclass
class SemanticFrame:
    intent: str = "unknown"
    operation_risk: str = "medium"
    need_clarification: bool = False
    clarification_question: str = ""
    task: dict[str, Any] | None = None
    query: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)
    updates: dict[str, Any] = field(default_factory=dict)
    normalized_text: str = ""
    confidence: float = 0.0
    completeness: float = 0.0
    parse_reason: str = ""
    title_source: str = "original_text"
    time_source: str = "uncertain"


@dataclass(frozen=True)
class VoiceDecision:
    action: str
    reason: str
    confirmation_prompt: str = ""
    clarification_question: str = ""


@dataclass
class VoiceUnderstandingResult:
    trace_id: str
    audio_quality: AudioQuality
    decision: VoiceDecision
    top_hypotheses: list[TextHypothesis] = field(default_factory=list)
    asr_diagnostics: list[dict[str, Any]] = field(default_factory=list)
    asr_comparison: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def best(self) -> TextHypothesis | None:
        return self.top_hypotheses[0] if self.top_hypotheses else None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
