"""Uniform local semantic frame parser."""

from __future__ import annotations

from datetime import datetime

from src.command_parser import parse_command
from src.voice_understanding.schema import SemanticFrame


RISK_BY_INTENT = {
    "add_event": "low",
    "query_schedule": "low",
    "update_event": "high",
    "delete_event": "high",
    "mark_completed": "medium",
}


def parse_semantic_frame(text: str, *, now: datetime | None = None) -> SemanticFrame:
    parsed = parse_command(text, now=now)
    intent = parsed.get("intent", "unknown")
    frame = SemanticFrame(
        intent=intent,
        operation_risk=RISK_BY_INTENT.get(intent, "medium"),
        need_clarification=bool(parsed.get("need_clarification")),
        clarification_question=str(parsed.get("clarification_question") or ""),
        task=parsed.get("task"),
        query=parsed.get("query") or {},
        target=parsed.get("target") or {},
        updates=parsed.get("updates") or {},
        normalized_text=text,
        confidence=float(parsed.get("confidence") or 0.0),
        parse_reason=str(parsed.get("parse_reason") or ""),
    )
    frame.completeness = _completeness(frame)
    frame.time_source = "explicit_expression" if _has_time(frame) else "uncertain"
    return frame


def _completeness(frame: SemanticFrame) -> float:
    if frame.need_clarification or frame.intent == "unknown":
        return 0.35
    if frame.intent == "query_schedule":
        return 1.0 if frame.query.get("date") else 0.4
    if frame.intent in {"delete_event", "mark_completed"}:
        return 0.9 if frame.query.get("keyword") else 0.35
    if frame.intent == "update_event":
        return 0.9 if frame.target.get("keyword") and frame.updates else 0.35
    task = frame.task or {}
    if task.get("type") == "fixed_event":
        return 1.0 if task.get("title") and task.get("date") and task.get("start_time") else 0.45
    return 0.9 if task.get("title") else 0.4


def _has_time(frame: SemanticFrame) -> bool:
    task = frame.task or {}
    return bool(task.get("start_time") or task.get("deadline") or frame.updates.get("start_time"))
