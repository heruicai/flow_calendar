"""Calendar view grouping, styling, and Streamlit rendering helpers."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from html import escape
from typing import Callable

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

WINDOW_RANGES = {
    "morning": ("07:00", "12:00"),
    "afternoon": ("12:00", "18:00"),
    "evening": ("18:00", "22:00"),
    "night": ("20:00", "23:00"),
}


def build_month_calendar(year: int, month: int, tasks: list) -> list:
    """Return month calendar data grouped by week."""
    calendar.setfirstweekday(calendar.MONDAY)
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        weeks.append(
            [
                {
                    "date": day.isoformat(),
                    "day": day.day,
                    "in_month": day.month == month,
                    "indicators": get_task_indicators_for_date(tasks, day.isoformat()),
                }
                for day in week
            ]
        )
    return weeks


def get_task_indicators_for_date(tasks: list, date: str) -> dict:
    """Count visual task indicators for one date."""
    indicators = {
        "fixed_event": 0,
        "deadline_task": 0,
        "essential_task": 0,
        "flexible_plan": 0,
        "completed": 0,
    }

    for task in tasks:
        task_type = task.get("type")
        appears_on_date = _task_appears_on_date(task, date)
        if appears_on_date and task_type in indicators:
            indicators[task_type] += 1
        if appears_on_date and task.get("status") == "completed":
            indicators["completed"] += 1

    return indicators


def build_day_timeline(tasks: list, selected_date: str) -> list:
    """Build visual timeline entries for one day."""
    entries = []
    selected_day = date.fromisoformat(selected_date)

    for task in tasks:
        task_type = task.get("type")
        if task_type == "fixed_event" and task.get("date") == selected_date:
            entries.append(
                _timeline_entry(
                    task,
                    start_time=task.get("start_time") or "00:00",
                    end_time=task.get("end_time") or task.get("start_time") or "23:59",
                )
            )
        elif task_type == "deadline_task" and _deadline_visible_on_date(task, selected_day):
            deadline_dt = _parse_datetime(task.get("deadline"))
            deadline_date = deadline_dt.date() if deadline_dt else selected_day
            end_time = deadline_dt.strftime("%H:%M") if deadline_dt and deadline_date == selected_day else "23:59"
            entries.append(_timeline_entry(task, start_time="00:00", end_time=end_time))
        elif task_type == "essential_task" and task.get("date") == selected_date:
            start_time, end_time = _essential_time_range(task)
            entries.append(_timeline_entry(task, start_time=start_time, end_time=end_time))

    entries.sort(key=lambda entry: (entry["start_time"], entry["end_time"], entry["title"]))
    return entries


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


def render_month_calendar(
    year: int,
    month: int,
    tasks: list,
    selected_date: str,
    key_prefix: str = "month_calendar",
) -> str | None:
    """Render a clickable Streamlit month calendar and return clicked date."""
    _render_calendar_styles()
    weeks = build_month_calendar(year, month, tasks)
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    header_columns = st.columns(7)
    for column, weekday in zip(header_columns, weekdays):
        column.markdown(f"**{weekday}**")

    clicked_date = None
    for week_index, week in enumerate(weeks):
        columns = st.columns(7)
        for day_index, day_info in enumerate(week):
            with columns[day_index]:
                day_date = day_info["date"]
                selected_marker = "selected" if day_date == selected_date else ""
                month_marker = "" if day_info["in_month"] else "muted"
                st.markdown(
                    _month_cell_html(day_info, selected_marker, month_marker),
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Select",
                    key=f"{key_prefix}_{week_index}_{day_index}_{day_date}",
                    use_container_width=True,
                    disabled=not day_info["in_month"],
                ):
                    clicked_date = day_date

    return clicked_date


def render_day_timeline(
    tasks: list,
    selected_date: str,
    action_renderer: Callable[[dict], None] | None = None,
) -> None:
    """Render the selected day's fixed, deadline, and essential timeline."""
    _render_calendar_styles()
    entries = build_day_timeline(tasks, selected_date)
    st.markdown(f"#### Day Timeline: {selected_date}")

    if not entries:
        st.markdown(
            "<div class='flowcal-section-note'>No timeline tasks for this day.</div>",
            unsafe_allow_html=True,
        )
        return

    for entry in entries:
        st.markdown(render_timeline_entry_html(entry), unsafe_allow_html=True)
        if action_renderer:
            action_renderer(entry["task"])


def render_calendar_day(tasks: list[dict], selected_date: str) -> None:
    """Backward-compatible wrapper for the day timeline renderer."""
    render_day_timeline(tasks, selected_date)


def render_timeline_entry_html(entry: dict) -> str:
    """Return an HTML card for a day timeline entry."""
    task = entry["task"]
    style = get_task_style(task)
    title = escape(str(entry.get("title") or "Untitled task"))
    status = escape(str(task.get("status") or "pending"))
    time_range = escape(f"{entry['start_time']} - {entry['end_time']}")
    label = escape(TASK_TYPE_LABELS.get(task.get("type"), "Task"))
    details = escape(entry.get("details") or _build_task_meta(task))

    return f"""
    <div class="flowcal-card" style="--accent:{style['accent']};--background:{style['background']};--border:{style['border']};">
      <div class="flowcal-card-title">{time_range} · {title}</div>
      <div class="flowcal-card-meta">{label} · {status}</div>
      <div class="flowcal-card-meta">{details}</div>
    </div>
    """


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


def _timeline_entry(task: dict, start_time: str, end_time: str) -> dict:
    return {
        "task": task,
        "task_id": task.get("id"),
        "title": task.get("title") or "Untitled task",
        "type": task.get("type"),
        "status": task.get("status") or "pending",
        "start_time": start_time,
        "end_time": end_time,
        "details": _build_task_meta(task),
    }


def _task_appears_on_date(task: dict, target_date: str) -> bool:
    task_type = task.get("type")
    if task_type in {"fixed_event", "essential_task"}:
        return task.get("date") == target_date
    if task_type == "deadline_task":
        deadline_dt = _parse_datetime(task.get("deadline"))
        return bool(deadline_dt and deadline_dt.date().isoformat() == target_date)
    return False


def _deadline_visible_on_date(task: dict, selected_day: date) -> bool:
    deadline_dt = _parse_datetime(task.get("deadline"))
    if not deadline_dt:
        return False

    created_dt = _parse_datetime(task.get("created_at"))
    if created_dt and selected_day < created_dt.date():
        return False

    return selected_day <= deadline_dt.date()


def _essential_time_range(task: dict) -> tuple[str, str]:
    if task.get("start_time") and task.get("end_time"):
        return task["start_time"], task["end_time"]

    preferred_window = task.get("preferred_time_window")
    if preferred_window in WINDOW_RANGES:
        return WINDOW_RANGES[preferred_window]

    return "07:00", "22:00"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _month_cell_html(day_info: dict, selected_marker: str, month_marker: str) -> str:
    indicators = day_info["indicators"]
    selected_class = " flowcal-month-cell-selected" if selected_marker else ""
    muted_class = " flowcal-month-cell-muted" if month_marker else ""
    chips = []
    chip_specs = [
        ("fixed_event", "F", "#2563eb"),
        ("deadline_task", "D", "#f97316"),
        ("essential_task", "E", "#16a34a"),
        ("completed", "C", "#6b7280"),
    ]
    for key, label, color in chip_specs:
        count = indicators.get(key, 0)
        if count:
            chips.append(f"<span style='background:{color}'>{label} {count}</span>")

    chips_html = "".join(chips) or "<span class='flowcal-empty-chip'>No tasks</span>"
    return f"""
    <div class="flowcal-month-cell{selected_class}{muted_class}">
      <div class="flowcal-month-day">{day_info['day']}</div>
      <div class="flowcal-month-chips">{chips_html}</div>
    </div>
    """


def _render_calendar_styles() -> None:
    st.markdown(
        """
        <style>
        .flowcal-month-cell {
            min-height: 84px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 6px;
            background: #ffffff;
            margin-bottom: 4px;
        }
        .flowcal-month-cell-selected {
            border: 2px solid #111827;
            box-shadow: inset 0 0 0 1px #111827;
        }
        .flowcal-month-cell-muted {
            opacity: 0.35;
        }
        .flowcal-month-day {
            font-weight: 700;
            color: #111827;
            margin-bottom: 5px;
        }
        .flowcal-month-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }
        .flowcal-month-chips span {
            color: #ffffff;
            border-radius: 999px;
            padding: 2px 6px;
            font-size: 12px;
            line-height: 1.4;
        }
        .flowcal-empty-chip {
            color: #9ca3af !important;
            background: #f3f4f6 !important;
        }
        .flowcal-card {
            border-left: 5px solid var(--accent);
            border: 1px solid var(--border);
            border-left-width: 5px;
            border-radius: 8px;
            padding: 8px 10px;
            margin-bottom: 6px;
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
