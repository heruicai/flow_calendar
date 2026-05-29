"""Calendar view grouping, styling, and Streamlit rendering helpers."""

from __future__ import annotations

from html import escape

import streamlit as st


TASK_TYPE_LABELS = {
    "fixed_event": "Fixed Event",
    "deadline_task": "Deadline Task",
    "essential_task": "Essential Task",
    "flexible_plan": "Flexible Plan",
}

STYLE_BY_TYPE = {
    "fixed_event": {
        "category": "calendar_block",
        "accent": "#2563eb",
        "background": "#eff6ff",
        "border": "#bfdbfe",
    },
    "deadline_task": {
        "category": "deadline_timeline",
        "accent": "#f97316",
        "background": "#fff7ed",
        "border": "#fed7aa",
    },
    "essential_task": {
        "category": "essential_bar",
        "accent": "#16a34a",
        "background": "#f0fdf4",
        "border": "#bbf7d0",
    },
    "flexible_plan": {
        "category": "todo_pool",
        "accent": "#7c3aed",
        "background": "#f5f3ff",
        "border": "#ddd6fe",
    },
}

COMPLETED_STYLE = {
    "accent": "#6b7280",
    "background": "#f3f4f6",
    "border": "#d1d5db",
}


def group_tasks_for_view(tasks: list[dict], selected_date: str) -> dict[str, list[dict]]:
    """Group tasks into the visual buckets used by the FlowCal UI."""
    groups = {
        "calendar_blocks": [],
        "essential_bars": [],
        "deadline_timeline": [],
        "todo_pool": [],
    }

    for task in tasks:
        task_type = task.get("type")
        if task_type == "fixed_event" and task.get("date") == selected_date:
            groups["calendar_blocks"].append(task)
        elif task_type == "essential_task" and task.get("date") == selected_date:
            groups["essential_bars"].append(task)
        elif task_type == "deadline_task":
            groups["deadline_timeline"].append(task)
        elif task_type == "flexible_plan":
            groups["todo_pool"].append(task)

    groups["calendar_blocks"].sort(key=lambda task: task.get("start_time") or "")
    groups["essential_bars"].sort(key=lambda task: task.get("title") or "")
    groups["deadline_timeline"].sort(key=lambda task: task.get("deadline") or "")
    groups["todo_pool"].sort(key=lambda task: task.get("created_at") or "")
    return groups


def get_task_style(task: dict) -> dict[str, str]:
    """Return style metadata for a task card."""
    base_style = STYLE_BY_TYPE.get(task.get("type"), STYLE_BY_TYPE["flexible_plan"]).copy()
    if task.get("status") == "completed":
        base_style.update(COMPLETED_STYLE)
        base_style["is_completed"] = "true"
    else:
        base_style["is_completed"] = "false"
    return base_style


def render_calendar_day(tasks: list[dict], selected_date: str) -> None:
    """Render the center calendar area for fixed and essential tasks."""
    groups = group_tasks_for_view(tasks, selected_date)

    st.markdown(
        """
        <style>
        .flowcal-day-grid {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
            background: #ffffff;
        }
        .flowcal-hour-row {
            display: grid;
            grid-template-columns: 72px 1fr;
            min-height: 44px;
            border-bottom: 1px solid #f3f4f6;
        }
        .flowcal-hour-label {
            padding: 10px 12px;
            color: #6b7280;
            background: #f9fafb;
            font-size: 13px;
        }
        .flowcal-hour-slot {
            padding: 8px 10px;
        }
        .flowcal-card {
            border-left: 5px solid var(--accent);
            border: 1px solid var(--border);
            border-left-width: 5px;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: var(--background);
        }
        .flowcal-card-title {
            font-weight: 650;
            color: #111827;
            margin-bottom: 4px;
        }
        .flowcal-card-meta {
            color: #4b5563;
            font-size: 13px;
        }
        .flowcal-section-note {
            color: #6b7280;
            padding: 12px;
            border: 1px dashed #d1d5db;
            border-radius: 8px;
            background: #f9fafb;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not groups["calendar_blocks"] and not groups["essential_bars"]:
        st.markdown(
            "<div class='flowcal-section-note'>No fixed or essential tasks for this day.</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("<div class='flowcal-day-grid'>", unsafe_allow_html=True)
    for hour in range(8, 23):
        hour_tasks = [
            task
            for task in groups["calendar_blocks"]
            if (task.get("start_time") or "").startswith(f"{hour:02d}:")
        ]
        slot_html = "".join(render_task_card_html(task) for task in hour_tasks)
        st.markdown(
            f"""
            <div class="flowcal-hour-row">
              <div class="flowcal-hour-label">{hour:02d}:00</div>
              <div class="flowcal-hour-slot">{slot_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### Essential Tasks")
    if groups["essential_bars"]:
        for task in groups["essential_bars"]:
            st.markdown(render_task_card_html(task), unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='flowcal-section-note'>No essential tasks for this day.</div>",
            unsafe_allow_html=True,
        )


def render_task_card_html(task: dict) -> str:
    """Return an HTML card for a task."""
    style = get_task_style(task)
    title = escape(str(task.get("title") or "Untitled task"))
    status = escape(str(task.get("status") or "pending"))
    meta = escape(_build_task_meta(task))
    label = escape(TASK_TYPE_LABELS.get(task.get("type"), "Task"))

    return f"""
    <div class="flowcal-card" style="--accent:{style['accent']};--background:{style['background']};--border:{style['border']};">
      <div class="flowcal-card-title">{title}</div>
      <div class="flowcal-card-meta">{label} · {status}</div>
      <div class="flowcal-card-meta">{meta}</div>
    </div>
    """


def _build_task_meta(task: dict) -> str:
    task_type = task.get("type")
    if task_type == "fixed_event":
        start_time = task.get("start_time") or "Any time"
        end_time = task.get("end_time") or "unspecified end"
        return f"{start_time} - {end_time}"
    if task_type == "deadline_task":
        deadline = task.get("deadline") or "No deadline"
        duration = _format_duration(task.get("estimated_duration_minutes"))
        latest_start = task.get("latest_start_time") or "No latest start"
        return f"Deadline: {deadline} | Duration: {duration} | Latest start: {latest_start}"
    if task_type == "essential_task":
        duration = _format_duration(task.get("estimated_duration_minutes"))
        return f"Must finish today | Duration: {duration}"
    duration = _format_duration(task.get("estimated_duration_minutes"))
    return f"Todo pool | Duration: {duration}"


def _format_duration(minutes: int | None) -> str:
    if not minutes:
        return "unspecified"
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes / 60
    return f"{hours:g} h"
