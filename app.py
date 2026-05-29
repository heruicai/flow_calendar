"""Streamlit entry point for FlowCal."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from src.calendar_view import (
    group_tasks_for_view,
    render_calendar_day,
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
    left, middle, right = st.columns([1.05, 1.65, 1.15], gap="large")

    with left:
        _render_command_panel()

    selected_date = st.session_state.selected_date
    selected_date_obj = datetime.fromisoformat(selected_date).date()

    with middle:
        st.subheader("Calendar View")
        chosen_date = st.date_input(
            "Select date",
            value=selected_date_obj,
            key="calendar_date_input",
        )
        if chosen_date.isoformat() != st.session_state.selected_date:
            st.session_state.selected_date = chosen_date.isoformat()
            selected_date = st.session_state.selected_date
        render_calendar_day(tasks, selected_date)
        _render_calendar_actions(tasks, selected_date)

    with right:
        st.subheader("Task Panels")
        _render_task_panels(tasks)
        st.subheader("System Response")
        st.info(st.session_state.system_response)


def _init_session_state() -> None:
    today = date.today().isoformat()
    st.session_state.setdefault("selected_date", today)
    st.session_state.setdefault("calendar_date_input", date.fromisoformat(today))
    st.session_state.setdefault("system_response", build_welcome_message())
    st.session_state.setdefault("command_text", "")


def _render_command_panel() -> None:
    st.subheader("Voice / Text Command")
    st.caption("Typed text is treated as simulated speech-to-text output. Real ASR can be connected later.")

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
        _handle_command(command)


def _handle_command(command: str) -> None:
    if not command.strip():
        st.session_state.system_response = "Please enter a command first."
        return

    parsed = parse_command(command)
    if parsed.get("need_clarification"):
        st.session_state.system_response = build_parse_response(parsed)
        return

    intent = parsed.get("intent")
    if intent == "add_event":
        stored_task = add_task(parsed["task"])
        if stored_task.get("date"):
            _set_selected_date(stored_task["date"])
        st.session_state.system_response = f"Added: {stored_task['title']}"
        return

    if intent == "query_schedule":
        query_date = (parsed.get("query") or {}).get("date")
        if query_date:
            _set_selected_date(query_date)
            tasks = load_tasks()
            st.session_state.system_response = build_schedule_summary(tasks, query_date)
        return

    if intent in {"mark_completed", "delete_event"}:
        _handle_task_action_from_query(parsed)
        return

    st.session_state.system_response = build_parse_response(parsed)


def _handle_task_action_from_query(parsed: dict) -> None:
    query = parsed.get("query") or {}
    keyword = query.get("keyword") or ""
    query_date = query.get("date")
    candidates = _find_matching_tasks(load_tasks(), keyword, query_date)

    if not candidates:
        st.session_state.system_response = f"No matching task found for: {keyword}"
        return

    if len(candidates) > 1:
        st.session_state.system_response = (
            f"Found {len(candidates)} matching tasks for '{keyword}'. "
            "Please use the task card buttons to choose one."
        )
        return

    task = candidates[0]
    if parsed.get("intent") == "mark_completed":
        updated = mark_task_completed(task["id"])
        st.session_state.system_response = f"Marked completed: {updated['title']}"
    else:
        delete_task(task["id"])
        st.session_state.system_response = f"Deleted: {task['title']}"


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


def _render_calendar_actions(tasks: list[dict], selected_date: str) -> None:
    groups = group_tasks_for_view(tasks, selected_date)
    action_tasks = groups["calendar_blocks"] + groups["essential_bars"]
    if not action_tasks:
        return

    st.markdown("#### Quick Actions")
    for task in action_tasks:
        _render_task_actions(task, allow_postpone=task.get("type") == "essential_task")


def _render_task_panels(tasks: list[dict]) -> None:
    groups = group_tasks_for_view(tasks, st.session_state.selected_date)

    st.markdown("#### Deadline Timeline")
    if groups["deadline_timeline"]:
        for task in groups["deadline_timeline"]:
            st.markdown(render_task_card_html(task), unsafe_allow_html=True)
            _render_task_actions(task, allow_postpone=False)
    else:
        st.caption("No deadline tasks yet.")

    st.markdown("#### Flexible Task Pool")
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
        st.session_state.system_response = f"Marked completed: {updated['title']}"
        st.rerun()

    if columns[1].button("Delete", key=f"delete_{task_id}", use_container_width=True):
        delete_task(task_id)
        st.session_state.system_response = f"Deleted: {task.get('title', 'task')}"
        st.rerun()

    if allow_postpone and columns[2].button("Postpone", key=f"postpone_{task_id}", use_container_width=True):
        new_date = _next_task_date(task)
        updated = mark_task_postponed(task_id, new_date)
        st.session_state.system_response = f"Postponed: {updated['title']} to {new_date}"
        st.rerun()


def _next_task_date(task: dict) -> str:
    current_date = task.get("date")
    if current_date:
        return (datetime.fromisoformat(current_date).date() + timedelta(days=1)).isoformat()
    return (date.today() + timedelta(days=1)).isoformat()


def _set_selected_date(value: str) -> None:
    st.session_state.selected_date = value
    st.session_state.calendar_date_input = date.fromisoformat(value)


if __name__ == "__main__":
    main()
