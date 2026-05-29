"""Streamlit entry point for FlowCal."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from src.calendar_view import (
    build_day_timeline,
    group_tasks_for_view,
    render_day_timeline,
    render_month_calendar,
    render_task_card_html,
)
from src.command_parser import parse_command
from src.response_generator import (
    build_parse_response,
    build_schedule_summary,
    build_welcome_message,
)
from src.task_store import (
    add_task,
    delete_task,
    load_tasks,
    mark_task_completed,
    mark_task_postponed,
)
from src.voice_adapter import (
    build_spoken_response,
    get_voice_input_mode_description,
    normalize_voice_text,
    text_to_speech,
)


SAMPLE_COMMANDS = [
    "明天下午三点到四点参加算法面试",
    "周五前完成报告，预计三小时",
    "今天必须洗衣服",
    "添加弹性任务，刷两道 LeetCode",
    "我明天有什么安排",
    "洗衣服完成了",
]


def main() -> None:
    st.set_page_config(page_title="FlowCal", page_icon="F", layout="wide")
    _init_session_state()

    st.title("FlowCal")
    st.caption("Voice-driven visual calendar assistant")

    tasks = load_tasks()
    left, center, right = st.columns([1.05, 2.25, 1.15], gap="large")

    with left:
        _render_command_panel()

    with center:
        _render_month_and_day_views(tasks)

    with right:
        st.subheader("Flexible Task Pool")
        _render_flexible_pool(tasks)
        st.subheader("System Response")
        st.info(st.session_state.system_response)
        st.subheader("Spoken Response / Voice Reply")
        st.write(st.session_state.spoken_response)
        if st.button("Generate voice reply", use_container_width=True):
            voice_reply = text_to_speech(st.session_state.system_response)
            st.session_state.spoken_response = voice_reply["spoken_text"]
            st.session_state.voice_reply_message = voice_reply["message"]
            st.rerun()
        st.caption(st.session_state.voice_reply_message)


def _init_session_state() -> None:
    today = date.today()
    welcome_message = build_welcome_message()
    st.session_state.setdefault("selected_date", today.isoformat())
    st.session_state.setdefault("calendar_year", today.year)
    st.session_state.setdefault("calendar_month", today.month)
    st.session_state.setdefault("system_response", welcome_message)
    st.session_state.setdefault("spoken_response", build_spoken_response(welcome_message))
    st.session_state.setdefault("voice_reply_message", "Voice reply has not been generated yet.")
    st.session_state.setdefault("command_text", "")
    st.session_state.setdefault("input_mode", "Text input")


def _render_command_panel() -> None:
    st.subheader("Voice / Text Command")
    input_mode = st.radio(
        "Input mode",
        ["Text input", "Simulated voice input"],
        key="input_mode",
        horizontal=True,
    )
    if input_mode == "Simulated voice input":
        st.caption("Current version treats typed text as speech-to-text output.")
    else:
        st.caption("Type a calendar command directly.")
    st.caption(get_voice_input_mode_description())

    st.markdown("**Examples**")
    for index, sample in enumerate(SAMPLE_COMMANDS):
        if st.button(sample, key=f"sample_{index}", use_container_width=True):
            st.session_state.command_text = sample
            st.rerun()

    command = st.text_area(
        "Command",
        key="command_text",
        placeholder="Example: 明天下午三点到四点参加算法面试",
        height=140,
    )

    if st.button("Parse and Apply", type="primary", use_container_width=True):
        _handle_command(command, input_mode=input_mode)


def _render_month_and_day_views(tasks: list[dict]) -> None:
    st.subheader("Month Calendar")
    control_columns = st.columns([1, 1, 2])
    year = control_columns[0].number_input(
        "Year",
        min_value=2000,
        max_value=2100,
        value=int(st.session_state.calendar_year),
        step=1,
    )
    month = control_columns[1].selectbox(
        "Month",
        options=list(range(1, 13)),
        index=int(st.session_state.calendar_month) - 1,
        format_func=lambda value: datetime(2000, value, 1).strftime("%B"),
    )
    st.session_state.calendar_year = int(year)
    st.session_state.calendar_month = int(month)

    selected_date = st.session_state.selected_date
    clicked_date = render_month_calendar(
        int(year),
        int(month),
        tasks,
        selected_date=selected_date,
    )
    if clicked_date:
        _set_selected_date(clicked_date)
        st.rerun()

    st.divider()
    render_day_timeline(tasks, st.session_state.selected_date)
    _render_day_timeline_actions(tasks, st.session_state.selected_date)


def _handle_command(command: str, input_mode: str = "Text input") -> None:
    if not command.strip():
        _set_system_response("Please enter a command first.")
        return

    normalized_command = normalize_voice_text(command)
    parsed = parse_command(normalized_command)
    if parsed.get("need_clarification"):
        _set_system_response(build_parse_response(parsed))
        return

    intent = parsed.get("intent")
    if intent == "add_event":
        stored_task = add_task(parsed["task"])
        if stored_task.get("date"):
            _set_selected_date(stored_task["date"])
        mode_label = "Voice command" if input_mode == "Simulated voice input" else "Text command"
        _set_system_response(f"{mode_label} applied. Added: {stored_task['title']}")
        return

    if intent == "query_schedule":
        query_date = (parsed.get("query") or {}).get("date")
        if query_date:
            _set_selected_date(query_date)
            tasks = load_tasks()
            _set_system_response(build_schedule_summary(tasks, query_date))
        return

    if intent in {"mark_completed", "delete_event"}:
        _handle_task_action_from_query(parsed)
        return

    _set_system_response(build_parse_response(parsed))


def _handle_task_action_from_query(parsed: dict) -> None:
    query = parsed.get("query") or {}
    keyword = query.get("keyword") or ""
    query_date = query.get("date")
    candidates = _find_matching_tasks(load_tasks(), keyword, query_date)

    if not candidates:
        _set_system_response(f"No matching task found for: {keyword}")
        return

    if len(candidates) > 1:
        _set_system_response(
            f"Found {len(candidates)} matching tasks for '{keyword}'. "
            "Please use the task card buttons to choose one."
        )
        return

    task = candidates[0]
    if parsed.get("intent") == "mark_completed":
        updated = mark_task_completed(task["id"])
        _set_system_response(f"Marked completed: {updated['title']}")
    else:
        delete_task(task["id"])
        _set_system_response(f"Deleted: {task['title']}")


def _find_matching_tasks(tasks: list[dict], keyword: str, query_date: str | None = None) -> list[dict]:
    normalized_keyword = keyword.strip().lower()
    matches = []

    for task in tasks:
        title = str(task.get("title") or "")
        if query_date and task.get("date") not in {query_date, None}:
            continue
        if not normalized_keyword or normalized_keyword in title.lower() or title.lower() in normalized_keyword:
            matches.append(task)

    return matches


def _render_day_timeline_actions(tasks: list[dict], selected_date: str) -> None:
    entries = build_day_timeline(tasks, selected_date)
    if not entries:
        return

    st.markdown("#### Day Actions")
    for entry in entries:
        task = entry["task"]
        _render_task_actions(task, allow_postpone=task.get("type") == "essential_task")


def _render_flexible_pool(tasks: list[dict]) -> None:
    groups = group_tasks_for_view(tasks, st.session_state.selected_date)

    if groups["todo_pool"]:
        for task in groups["todo_pool"]:
            st.markdown(render_task_card_html(task), unsafe_allow_html=True)
            _render_task_actions(task, allow_postpone=True)
    else:
        st.caption("No flexible plans yet.")


def _render_task_actions(task: dict, allow_postpone: bool) -> None:
    task_id = task.get("id")
    if not task_id:
        return

    columns = st.columns(3 if allow_postpone else 2)
    if columns[0].button("Mark completed", key=f"complete_{task_id}", use_container_width=True):
        updated = mark_task_completed(task_id)
        _set_system_response(f"Marked completed: {updated['title']}")
        st.rerun()

    if columns[1].button("Delete", key=f"delete_{task_id}", use_container_width=True):
        delete_task(task_id)
        _set_system_response(f"Deleted: {task.get('title', 'task')}")
        st.rerun()

    if allow_postpone and columns[2].button("Postpone", key=f"postpone_{task_id}", use_container_width=True):
        new_date = _next_task_date(task)
        updated = mark_task_postponed(task_id, new_date)
        _set_system_response(f"Postponed: {updated['title']} to {new_date}")
        st.rerun()


def _next_task_date(task: dict) -> str:
    current_date = task.get("date")
    if current_date:
        return (datetime.fromisoformat(current_date).date() + timedelta(days=1)).isoformat()
    return (date.today() + timedelta(days=1)).isoformat()


def _set_selected_date(value: str) -> None:
    selected = date.fromisoformat(value)
    st.session_state.selected_date = value
    st.session_state.calendar_year = selected.year
    st.session_state.calendar_month = selected.month


def _set_system_response(message: str) -> None:
    st.session_state.system_response = message
    st.session_state.spoken_response = build_spoken_response(message)
    st.session_state.voice_reply_message = "Voice reply text updated. Generate mock voice reply when ready."


if __name__ == "__main__":
    main()
