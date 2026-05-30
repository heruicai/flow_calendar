"""Optional GLM semantic parser with a local rule-based fallback."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Any

from src.command_parser import DISPLAY_MODES_BY_TYPE, SUPPORTED_INTENTS, SUPPORTED_TASK_TYPES, parse_command
from src.voice_adapter import normalize_voice_text


DEFAULT_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
DEFAULT_ZHIPU_MODEL = "glm-4-flash-250414"
MIN_GLM_CONFIDENCE = 0.65


def is_glm_parser_available() -> bool:
    """Return whether the optional GLM parser has an API key."""
    return bool(os.getenv("ZHIPU_API_KEY", "").strip())


def parse_with_glm(text: str, now=None, tasks=None) -> dict:
    """Parse one normalized command with the OpenAI-compatible GLM API."""
    client = _create_glm_client()
    response = client.chat.completions.create(
        model=os.getenv("ZHIPU_MODEL", DEFAULT_ZHIPU_MODEL),
        messages=[
            {
                "role": "system",
                "content": "You are FlowCal's semantic calendar command parser. Return JSON only.",
            },
            {
                "role": "user",
                "content": build_glm_prompt(text, now=now, tasks=tasks),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise ValueError("GLM response content must be a JSON string.")
    return json.loads(content)


def build_glm_prompt(text: str, now=None, tasks=None) -> str:
    """Build a privacy-conscious prompt with minimal task context."""
    current_time = now or datetime.now()
    task_context = _sanitize_tasks(tasks or [])
    return f"""
Parse the user's Chinese calendar command into exactly one JSON object.
Do not include Markdown or natural-language commentary.

Current datetime: {current_time.isoformat(timespec="seconds")}
User command: {text}
Minimal local task context: {json.dumps(task_context, ensure_ascii=False)}

Allowed intents, in priority order:
1. query_schedule
2. delete_event
3. mark_completed
4. update_event
5. add_event

Task model:
- fixed_event: a fixed calendar event with an explicit date and time or time range, such as 明天下午三点面试.
- deadline_task: a task with a deadline, such as 周五前完成报告.
- essential_task: a necessary dated task without a fixed time range, such as 今天洗衣服.
- flexible_plan: a flexible todo that does not enter the calendar, such as 有空复习 kernelPCA.

Display modes:
- fixed_event -> calendar_block
- deadline_task -> deadline_bar
- essential_task -> essential_bar
- flexible_plan -> todo_pool

Requirements:
- Resolve relative dates using the current datetime and emit ISO dates.
- Handle schedule queries, adds, deletes, completions, fixed-event rescheduling,
  deadline changes, and task-type changes.
- Correct obvious ASR mistakes only when confidence is high.
- For update_event, put the existing task clues in target and requested changes in updates.
- If required details are uncertain, set need_clarification=true and ask a specific question.
- confidence must be a number from 0 to 1.
- parse_reason must briefly explain the classification.

Return this compatible shape:
{{
  "intent": "add_event | delete_event | query_schedule | mark_completed | update_event",
  "need_clarification": false,
  "clarification_question": "",
  "task": null,
  "query": {{"date": null, "keyword": ""}},
  "target": {{"keyword": "", "date": null, "start_time": null, "end_time": null}},
  "updates": {{}},
  "confidence": 0.0,
  "parse_reason": "",
  "response_text": ""
}}
""".strip()


def validate_glm_parse_result(result: dict) -> dict:
    """Validate and normalize one GLM JSON parse result."""
    if not isinstance(result, dict):
        raise ValueError("GLM parse result must be a dictionary.")

    validated = deepcopy(result)
    intent = validated.get("intent")
    if intent not in SUPPORTED_INTENTS:
        raise ValueError("GLM parse result has an unsupported intent.")

    confidence = validated.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("GLM parse result confidence must be numeric.")
    if not 0 <= float(confidence) <= 1:
        raise ValueError("GLM parse result confidence must be between 0 and 1.")

    task = validated.get("task")
    if task is not None:
        if not isinstance(task, dict):
            raise ValueError("GLM task must be a dictionary or null.")
        _validate_task_shape(task)

    for field in ("query", "target", "updates"):
        value = validated.get(field)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"GLM {field} must be a dictionary.")
    _validate_display_mode(validated.get("updates") or {})
    if intent == "add_event" and not isinstance(task, dict):
        raise ValueError("GLM add_event requires a task dictionary.")
    if intent == "query_schedule" and not isinstance(validated.get("query"), dict):
        raise ValueError("GLM query_schedule requires a query dictionary.")
    if intent == "update_event":
        if not isinstance(validated.get("target"), dict) or not isinstance(validated.get("updates"), dict):
            raise ValueError("GLM update_event requires target and updates dictionaries.")

    validated.setdefault("need_clarification", False)
    validated.setdefault("clarification_question", "")
    validated.setdefault("task", None)
    validated.setdefault("query", {"date": None, "keyword": ""})
    validated.setdefault("target", {})
    validated.setdefault("updates", {})
    validated.setdefault("parse_reason", "")
    validated.setdefault("response_text", "")
    validated["source"] = "glm"
    return validated


def parse_user_command(text: str, now=None, tasks=None, use_ai=True) -> dict:
    """Parse a user command with GLM when available, otherwise use local rules."""
    normalized = normalize_voice_text(text)
    if use_ai and is_glm_parser_available():
        try:
            parsed = validate_glm_parse_result(parse_with_glm(normalized, now=now, tasks=tasks))
            if parsed["confidence"] >= MIN_GLM_CONFIDENCE:
                return parsed
        except Exception:
            pass
    fallback = parse_command(normalized, now=now)
    fallback["source"] = "rule"
    return fallback


def _create_glm_client():
    from openai import OpenAI

    return OpenAI(
        api_key=os.environ["ZHIPU_API_KEY"],
        base_url=os.getenv("ZHIPU_BASE_URL", DEFAULT_ZHIPU_BASE_URL),
        timeout=12.0,
    )


def _sanitize_tasks(tasks: list[dict]) -> list[dict[str, Any]]:
    allowed_fields = ("title", "date", "type", "status")
    return [
        {field: task.get(field) for field in allowed_fields if task.get(field) is not None}
        for task in tasks
        if isinstance(task, dict)
    ]


def _validate_task_shape(task: dict) -> None:
    task_type = task.get("type")
    if task_type is not None and task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError("GLM task has an unsupported type.")
    _validate_display_mode(task)


def _validate_display_mode(value: dict) -> None:
    display_mode = value.get("display_mode")
    task_type = value.get("type")
    if display_mode is None:
        return
    if display_mode not in DISPLAY_MODES_BY_TYPE.values():
        raise ValueError("GLM result has an unsupported display mode.")
    if task_type in DISPLAY_MODES_BY_TYPE and display_mode != DISPLAY_MODES_BY_TYPE[task_type]:
        raise ValueError("GLM result display mode does not match its task type.")
