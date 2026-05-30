"""Streamlit entry point for FlowCal."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from src.calendar_view import (
    group_tasks_for_view,
    render_day_timeline,
    render_month_calendar,
    render_task_card_html,
)
from src.command_parser import parse_command
from src.dialog_manager import (
    apply_confirmed_action,
    build_confirmation_prompt,
    cancel_pending_action,
    create_pending_action,
)
from src.response_generator import build_parse_response, build_schedule_summary, build_welcome_message
from src.task_store import delete_task, load_tasks, mark_task_completed, mark_task_postponed
from src.voice_adapter import (
    build_spoken_response,
    get_voice_input_mode_description,
    normalize_voice_text,
    speech_to_text,
    text_to_speech,
)


SAMPLE_COMMANDS = [
    "明天下午三点到四点参加算法面试",
    "今天必须洗衣服",
    "我明天有什么安排",
    "洗衣服完成了",
]


def main() -> None:
    st.set_page_config(page_title="FlowCal", page_icon="F", layout="wide")
    _init_session_state()
    _render_page_styles()

    st.title("FlowCal")
    st.caption("Voice-first visual calendar assistant")

    tasks = load_tasks()
    left, right = st.columns([1, 2.1], gap="medium")

    with left:
        _render_voice_conversation()
        st.subheader("Assistant Text Reply")
        st.info(st.session_state.system_response)
        st.subheader("Assistant Voice Reply")
        _render_voice_reply("final_response")
        st.subheader("Flexible Task Pool")
        _render_flexible_pool(tasks)

    with right:
        _render_month_and_day_views(tasks)


def _render_page_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1680px;
            padding-top: 1.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        div[data-testid="stButton"] button {
            min-height: 2rem;
            padding: 0.25rem 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    today = date.today()
    welcome_message = build_welcome_message()
    defaults = {
        "selected_date": today.isoformat(),
        "calendar_year": today.year,
        "calendar_month": today.month,
        "system_response": welcome_message,
        "spoken_response": build_spoken_response(welcome_message),
        "voice_reply": None,
        "dialog_state": "idle",
        "pending_action": None,
        "command_audio_digest": "",
        "command_text": "",
        "command_audio_nonce": 0,
        "asr_message": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _render_voice_conversation() -> None:
    st.subheader("Voice Conversation")
    st.caption("主流程：录音指令 -> 本地转写 -> 语音提示 -> 按钮确认 -> 执行 -> 语音回复")
    st.caption(get_voice_input_mode_description())

    state = st.session_state.dialog_state
    if state == "idle":
        _render_voice_command_step()
    elif state == "awaiting_confirmation":
        _render_confirmation_step()
    else:
        st.success("本轮语音交互已结束。")
        if st.button(
            "Start new voice command",
            key="start_new_voice_command",
            type="primary",
            use_container_width=True,
        ):
            _reset_voice_round()
            st.rerun()

    with st.expander("Text Command fallback"):
        st.caption("麦克风不可用时，可直接输入同样的日历指令。")
        typed_command = st.text_area("Text command", key="text_fallback_command", height=90)
        if st.button("Parse text command", key="parse_text_command", use_container_width=True):
            _handle_command(typed_command)
            st.rerun()

    with st.expander("Demo examples", expanded=False):
        for sample in SAMPLE_COMMANDS:
            st.code(sample, language=None)


def _render_voice_command_step() -> None:
    st.markdown("#### 1. Record a calendar command")
    audio_file = st.audio_input(
        "点击录音并说出日历指令",
        key=f"command_audio_{st.session_state.command_audio_nonce}",
    )
    if audio_file is not None:
        _transcribe_new_audio(
            audio_file,
            digest_key="command_audio_digest",
            text_key="command_text",
            message_key="asr_message",
        )

    if st.session_state.asr_message:
        st.caption(st.session_state.asr_message)
    command_text = st.text_area(
        "ASR text (editable)",
        key="command_text",
        placeholder="录音转写结果会显示在这里，也可以手动修正。",
        height=90,
    )
    if st.button(
        "Continue / Parse",
        key="continue_parse_voice_command",
        type="primary",
        use_container_width=True,
    ):
        _handle_command(command_text)
        st.rerun()


def _render_confirmation_step() -> None:
    st.markdown("#### 2. Confirm the pending change")
    prompt = st.session_state.system_response
    st.markdown("##### Assistant Text Reply")
    st.warning(prompt)
    st.markdown("##### Assistant Voice Reply")
    _render_voice_reply("confirmation_prompt")

    columns = st.columns(2)
    if columns[0].button(
        _confirmation_button_label(st.session_state.pending_action),
        key="confirm_pending_action",
        type="primary",
        use_container_width=True,
    ):
        _handle_confirmation_button()
        st.rerun()
    if columns[1].button(
        "取消本次操作",
        key="cancel_pending_action",
        use_container_width=True,
    ):
        _handle_cancel_button()
        st.rerun()


def _handle_command(command: str) -> None:
    normalized_command = normalize_voice_text(command)
    if not normalized_command:
        _set_system_response("请先录音，或输入一条日历指令。")
        return

    parsed = parse_command(normalized_command)
    if parsed.get("need_clarification"):
        _set_system_response(build_parse_response(parsed), speak=True)
        return

    intent = parsed.get("intent")
    if intent == "query_schedule":
        query_date = (parsed.get("query") or {}).get("date")
        if query_date:
            _set_selected_date(query_date)
            _complete_voice_round(build_schedule_summary(load_tasks(), query_date))
        return

    if intent in {"mark_completed", "delete_event"}:
        task = _find_single_matching_task(parsed)
        if not task:
            return
        pending_action = create_pending_action(parsed, matched_task=task)
    else:
        pending_action = create_pending_action(parsed)

    st.session_state.pending_action = pending_action
    st.session_state.dialog_state = "awaiting_confirmation"
    _set_system_response(build_confirmation_prompt(pending_action), speak=True)


def _handle_confirmation_button() -> None:
    result = apply_confirmed_action(st.session_state.pending_action or {})
    task = result.get("task") or {}
    if result["success"] and task.get("date"):
        _set_selected_date(task["date"])
    _complete_voice_round(result["response_text"])


def _handle_cancel_button() -> None:
    result = cancel_pending_action()
    _complete_voice_round(result["response_text"])


def _confirmation_button_label(pending_action: dict | None) -> str:
    intent = (pending_action or {}).get("intent")
    return {
        "add_event": "确认添加",
        "delete_event": "确认删除",
        "mark_completed": "确认完成",
    }.get(intent, "确认操作")


def _find_single_matching_task(parsed: dict) -> dict | None:
    query = parsed.get("query") or {}
    keyword = query.get("keyword") or ""
    query_date = query.get("date")
    candidates = _find_matching_tasks(load_tasks(), keyword, query_date)

    if not candidates:
        _complete_voice_round(f"没有找到匹配任务：{keyword}。")
        return None
    if len(candidates) > 1:
        _complete_voice_round(f"找到 {len(candidates)} 个匹配任务，请说出更具体的任务名称。")
        return None
    return candidates[0]


def _transcribe_new_audio(audio_file, digest_key: str, text_key: str, message_key: str) -> None:
    audio_digest = hashlib.sha256(audio_file.getvalue()).hexdigest()
    if st.session_state[digest_key] == audio_digest:
        return

    with st.spinner("正在本机识别语音..."):
        result = speech_to_text(audio_file)
    st.session_state[digest_key] = audio_digest
    st.session_state[message_key] = result["message"]
    if result["success"]:
        st.session_state[text_key] = result["text"]


def _complete_voice_round(message: str) -> None:
    st.session_state.dialog_state = "completed"
    st.session_state.pending_action = None
    _set_system_response(message, speak=True)


def _set_system_response(message: str, speak: bool = False) -> None:
    st.session_state.system_response = message
    st.session_state.spoken_response = build_spoken_response(message)
    if speak:
        with st.spinner("正在本机生成语音回复..."):
            st.session_state.voice_reply = text_to_speech(message)


def _render_voice_reply(render_location: str) -> None:
    voice_reply = st.session_state.voice_reply
    if not voice_reply:
        st.caption("等待语音回复。")
        return

    audio_path = voice_reply.get("audio_path")
    if voice_reply.get("success") and audio_path and Path(audio_path).exists():
        # Streamlit 1.58 st.audio has no key parameter. A stable per-location
        # width keeps simultaneous confirmation and final players distinct.
        audio_width = "stretch" if render_location == "confirmation_prompt" else 360
        st.audio(
            audio_path,
            format="audio/wav",
            autoplay=True,
            width=audio_width,
        )
    st.caption(voice_reply.get("message") or "")


def _reset_voice_round() -> None:
    st.session_state.dialog_state = "idle"
    st.session_state.pending_action = None
    st.session_state.command_audio_digest = ""
    st.session_state.command_text = ""
    st.session_state.command_audio_nonce += 1
    st.session_state.asr_message = ""
    st.session_state.voice_reply = None
    st.session_state.system_response = build_welcome_message()


def _render_month_and_day_views(tasks: list[dict]) -> None:
    st.subheader("Month Calendar")
    control_columns = st.columns([1, 1, 2])
    year = control_columns[0].number_input(
        "Year",
        key="calendar_year_input",
        min_value=2000,
        max_value=2100,
        value=int(st.session_state.calendar_year),
    )
    month = control_columns[1].selectbox(
        "Month",
        key="calendar_month_select",
        options=list(range(1, 13)),
        index=int(st.session_state.calendar_month) - 1,
        format_func=lambda value: datetime(2000, value, 1).strftime("%B"),
    )
    st.session_state.calendar_year = int(year)
    st.session_state.calendar_month = int(month)

    clicked_date = render_month_calendar(int(year), int(month), tasks, selected_date=st.session_state.selected_date)
    if clicked_date:
        _set_selected_date(clicked_date)
        st.rerun()

    st.divider()
    render_day_timeline(
        tasks,
        st.session_state.selected_date,
        action_renderer=lambda task: _render_task_actions(task, context="timeline"),
    )


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


def _render_flexible_pool(tasks: list[dict]) -> None:
    groups = group_tasks_for_view(tasks, st.session_state.selected_date)
    if not groups["todo_pool"]:
        st.caption("No flexible plans yet.")
    for task in groups["todo_pool"]:
        st.markdown(render_task_card_html(task), unsafe_allow_html=True)
        _render_task_actions(task, context="pool")


def _task_action_specs(task: dict, context: str) -> list[tuple[str, str]]:
    task_id = task.get("id")
    if not task_id:
        return []

    actions = []
    if task.get("status") != "completed":
        actions.append(("complete", f"{context}_complete_{task_id}"))
    actions.append(("delete", f"{context}_delete_{task_id}"))
    if task.get("status") != "completed" and task.get("type") in {
        "deadline_task",
        "essential_task",
        "flexible_plan",
    }:
        actions.append(("postpone", f"{context}_postpone_{task_id}"))
    return actions


def _render_task_actions(task: dict, context: str) -> None:
    task_id = task.get("id")
    if not task_id:
        return
    action_specs = _task_action_specs(task, context)
    columns = st.columns(len(action_specs))
    controls = {
        action: (column, key)
        for column, (action, key) in zip(columns, action_specs)
    }
    if "complete" in controls and controls["complete"][0].button(
        "Mark completed",
        key=controls["complete"][1],
        use_container_width=True,
    ):
        updated = mark_task_completed(task_id)
        _complete_voice_round(f"已将{updated['title']}标记为完成。")
        st.rerun()
    if controls["delete"][0].button("Delete", key=controls["delete"][1], use_container_width=True):
        delete_task(task_id)
        _complete_voice_round(f"已删除{task.get('title', '任务')}。")
        st.rerun()
    if "postpone" in controls and controls["postpone"][0].button(
        "Postpone",
        key=controls["postpone"][1],
        use_container_width=True,
    ):
        new_date = _next_task_date(task)
        updated = mark_task_postponed(task_id, new_date)
        _complete_voice_round(f"已将{updated['title']}推迟到{new_date}。")
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


if __name__ == "__main__":
    main()
