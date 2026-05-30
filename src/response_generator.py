"""Response generation helpers for FlowCal."""

from __future__ import annotations


def build_welcome_message() -> str:
    """Return the default message shown before a command is submitted."""
    return "Record a voice command or use the text fallback to update FlowCal."


def build_schedule_summary(tasks: list[dict], selected_date: str) -> str:
    """Build a short summary for the selected date."""
    fixed_count = sum(
        1
        for task in tasks
        if task.get("type") == "fixed_event" and task.get("date") == selected_date
    )
    essential_count = sum(
        1
        for task in tasks
        if task.get("type") == "essential_task" and task.get("date") == selected_date
    )
    return (
        f"{selected_date}: {fixed_count} fixed event(s), "
        f"{essential_count} essential task(s)."
    )


def build_parse_response(parsed: dict) -> str:
    """Return a human-readable response for parser output."""
    if parsed.get("need_clarification"):
        return parsed.get("clarification_question") or "Please provide more details."

    response_text = parsed.get("response_text")
    if response_text:
        return response_text

    intent = parsed.get("intent")
    if intent == "add_event":
        task = parsed.get("task") or {}
        return f"Added task: {task.get('title', 'Untitled task')}"
    if intent == "query_schedule":
        date = (parsed.get("query") or {}).get("date")
        return f"Showing schedule for {date}."
    if intent == "delete_event":
        return "Delete command parsed."
    if intent == "mark_completed":
        return "Completion command parsed."
    return "Command parsed."
