"""End-to-end local voice understanding orchestration."""

from __future__ import annotations

from uuid import uuid4

from src.asr_adapter import ASRCandidate, WhisperASRAdapter, create_asr_adapter
from src.voice_config import get_voice_config
from src.voice_understanding.audio_quality import inspect_audio_quality
from src.voice_understanding.context import build_local_context
from src.voice_understanding.hypothesis_expander import expand_hypotheses
from src.voice_understanding.reranker import rank_hypotheses
from src.voice_understanding.risk_policy import decide
from src.voice_understanding.schema import ASRHypothesis, AudioQuality, VoiceUnderstandingResult
from src.voice_understanding.semantic_parser import parse_semantic_frame
from src.voice_understanding.trace import write_trace


def understand_voice(audio_path, tasks=None, config=None, adapter=None, *, check_audio: bool = True) -> VoiceUnderstandingResult:
    settings = config or get_voice_config()
    quality = inspect_audio_quality(audio_path, threshold=settings.reject_audio_quality_threshold) if check_audio else AudioQuality()
    trace_id = uuid4().hex
    if not quality.acceptable:
        result = VoiceUnderstandingResult(trace_id, quality, decide([], quality))
        _maybe_trace(result, settings)
        return result
    context = build_local_context(tasks, max_terms=settings.max_context_terms)
    recognizer = adapter or create_asr_adapter(settings)
    try:
        candidates = recognizer.transcribe(audio_path, prompt=context["prompt"], hotwords=context["hotwords"])
    except (ImportError, ModuleNotFoundError):
        if isinstance(recognizer, WhisperASRAdapter):
            raise
        candidates = WhisperASRAdapter(settings).transcribe(audio_path, prompt=context["prompt"], hotwords=context["hotwords"])
    hypotheses = []
    for candidate in candidates:
        confidence = 0.5 if candidate.confidence is None else float(candidate.confidence)
        hypotheses.extend(expand_hypotheses(candidate.text, asr_confidence=confidence, source=candidate.source, context_terms=context["terms"]))
    for hypothesis in hypotheses:
        hypothesis.semantic_frame = parse_semantic_frame(hypothesis.text)
    ranked = rank_hypotheses(hypotheses, context_terms=context["terms"])
    decision = decide(ranked, quality, execute_threshold=settings.auto_execute_threshold, margin_threshold=settings.confirm_margin_threshold)
    result = VoiceUnderstandingResult(trace_id, quality, decision, ranked)
    _maybe_trace(result, settings)
    return result


def _maybe_trace(result, settings):
    if settings.enable_trace:
        write_trace(result, settings.trace_dir)
