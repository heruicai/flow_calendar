"""End-to-end local voice understanding orchestration."""

from __future__ import annotations

from uuid import uuid4

from src.asr_adapter import OptionalASRDependencyError, WhisperASRAdapter, create_asr_adapter
from src.voice_config import get_voice_config
from src.voice_understanding.audio_quality import inspect_audio_quality
from src.voice_understanding.asr_comparison import compare_asr_candidates
from src.voice_understanding.asr_diagnostics import build_asr_diagnostic, print_asr_diagnostic
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
        diagnostic = build_asr_diagnostic(
            engine=settings.asr_engine,
            model=settings.asr_model,
            language=settings.language,
            audio_duration=quality.duration_seconds,
            raw_text="",
        )
        if settings.enable_asr_diagnostics:
            print_asr_diagnostic(diagnostic)
        result = VoiceUnderstandingResult(trace_id, quality, decide([], quality), asr_diagnostics=[diagnostic])
        _maybe_trace(result, settings)
        return result
    context = build_local_context(tasks, max_terms=settings.max_context_terms)
    recognizer = adapter or create_asr_adapter(settings)
    diagnostics = []
    warnings = []
    primary_candidates = []
    fallback_candidates = []
    try:
        primary_candidates = recognizer.transcribe(audio_path, prompt=context["prompt"], hotwords=context["hotwords"])
    except (ImportError, ModuleNotFoundError) as exc:
        if isinstance(recognizer, WhisperASRAdapter):
            raise
        warning = str(exc) or "Optional local ASR engine is unavailable."
        warnings.append(warning)
        fallback_candidates = WhisperASRAdapter(settings).transcribe(
            audio_path,
            prompt=context["prompt"],
            hotwords=context["hotwords"],
        )
    primary_candidates = list(primary_candidates)
    if adapter is None and not isinstance(recognizer, WhisperASRAdapter) and primary_candidates:
        try:
            fallback_candidates = WhisperASRAdapter(settings).transcribe(
                audio_path,
                prompt=context["prompt"],
                hotwords=context["hotwords"],
            )
        except (ImportError, ModuleNotFoundError) as exc:
            warnings.append(f"Local Whisper fallback is unavailable: {exc}")
    candidates = [*primary_candidates, *fallback_candidates]
    fallback_text = fallback_candidates[0].text if fallback_candidates else ""
    for candidate in candidates:
        model = settings.whisper_model if candidate.source == "whisper" else settings.asr_model
        diagnostic = build_asr_diagnostic(
            engine=candidate.source,
            model=model,
            language=settings.language,
            audio_duration=quality.duration_seconds,
            raw_text=candidate.text,
            fallback_text=fallback_text,
            prompt=context["prompt"],
        )
        diagnostics.append(diagnostic)
        if settings.enable_asr_diagnostics:
            print_asr_diagnostic(diagnostic)
    comparison = compare_asr_candidates(candidates)
    hypotheses = []
    for candidate in candidates:
        confidence = 0.5 if candidate.confidence is None else float(candidate.confidence)
        hypotheses.extend(expand_hypotheses(candidate.text, asr_confidence=confidence, source=candidate.source, context_terms=context["terms"]))
    for hypothesis in hypotheses:
        hypothesis.semantic_frame = parse_semantic_frame(hypothesis.text)
    ranked = rank_hypotheses(hypotheses, context_terms=context["terms"])
    decision = decide(
        ranked,
        quality,
        execute_threshold=settings.auto_execute_threshold,
        margin_threshold=settings.confirm_margin_threshold,
        force_confirmation_reason=comparison["reason"] if comparison.get("requires_confirmation") else "",
    )
    result = VoiceUnderstandingResult(trace_id, quality, decision, ranked, diagnostics, comparison, warnings)
    _maybe_trace(result, settings)
    return result


def _maybe_trace(result, settings):
    if settings.enable_trace:
        write_trace(result, settings.trace_dir)
