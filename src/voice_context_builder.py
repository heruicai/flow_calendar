"""Build bounded local vocabulary context for speech recognition."""

from __future__ import annotations

from datetime import date

from src.voice_adapter import normalize_chinese_text


CALENDAR_TERMS = (
    "提醒我",
    "截止时间",
    "明天",
    "后天",
    "下周一",
    "周五",
    "下午",
    "上午",
    "晚上",
    "组会",
    "面试",
    "复习",
    "提交",
    "报告",
    "简历",
    "投递",
    "弹性任务",
    "固定任务",
)

PROJECT_TERMS = (
    "算法面试",
    "多元统计",
    "kernelPCA",
    "RAG",
    "GLM",
    "Codex",
    "FlowCal",
)


def get_context_terms(
    tasks: list[dict] | None = None,
    *,
    extra_terms: list[str] | None = None,
    max_terms: int = 80,
    today: date | None = None,
) -> list[str]:
    """Return de-duplicated task and domain vocabulary for local ASR."""
    current_date = (today or date.today()).isoformat()
    task_items = [task for task in (tasks or []) if isinstance(task, dict)]
    recent_tasks = sorted(
        task_items,
        key=lambda task: str(task.get("updated_at") or task.get("created_at") or ""),
        reverse=True,
    )
    future_tasks = [
        task for task in task_items
        if not task.get("date") or str(task.get("date")) >= current_date
    ]
    values = [
        *(task.get("title") for task in task_items),
        *(task.get("title") for task in future_tasks),
        *(task.get("title") for task in recent_tasks[:20]),
        *CALENDAR_TERMS,
        *PROJECT_TERMS,
        *(extra_terms or []),
    ]
    return _dedupe_terms(values, max_terms=max_terms)


def build_asr_prompt(context_terms: list[str], *, initial_prompt: str = "", max_chars: int = 500) -> str:
    """Build a compact Whisper prompt without leaking full task records."""
    parts = [initial_prompt.strip(), "，".join(context_terms)]
    return "。".join(part for part in parts if part)[:max_chars]


def build_voice_context(
    tasks: list[dict] | None = None,
    *,
    extra_terms: list[str] | None = None,
    max_terms: int = 80,
    initial_prompt: str = "",
) -> dict:
    """Build the context object shared by adapters and post-processing."""
    terms = get_context_terms(tasks, extra_terms=extra_terms, max_terms=max_terms)
    return {
        "terms": terms,
        "prompt": build_asr_prompt(terms, initial_prompt=initial_prompt),
        "hotwords": terms,
    }


def _dedupe_terms(values, *, max_terms: int) -> list[str]:
    seen = set()
    terms = []
    for value in values:
        term = normalize_chinese_text(str(value or "")).strip()
        key = term.casefold()
        if not term or key in seen:
            continue
        seen.add(key)
        terms.append(term)
        if len(terms) >= max_terms:
            break
    return terms
