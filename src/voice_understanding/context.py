"""Build bounded local vocabulary without exposing full private records."""

from __future__ import annotations

from src.voice_context_builder import build_voice_context


def build_local_context(tasks: list[dict] | None = None, *, extra_terms=None, max_terms: int = 80) -> dict:
    context = build_voice_context(tasks, extra_terms=extra_terms or [], max_terms=max_terms)
    return {
        "terms": context["terms"],
        "titles": [str(task.get("title") or "") for task in (tasks or []) if isinstance(task, dict)],
        "prompt": context["prompt"],
        "hotwords": context["hotwords"],
    }
