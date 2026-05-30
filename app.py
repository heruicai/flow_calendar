"""Streamlit entry point for FlowCal."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from src.calendar_view import (
    build_day_timeline,
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
    parse_confirmation_text,
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

    st.title("FlowCal")
    st.caption("Voice-first visual calendar assistant")

    tasks = load_tasks()
    left, center, right = st.columns([1.2, 2.2, 1.15], gap="large")

    with left:
        _render_voice_conversation()

    with center:
        _render_month_and_day_views(tasks)

    with right:
        st.subheader("Flexible Task Pool")
        _render_flexible_pool(tasks)
        st.subheader("Assistant Text Reply")
        st.info(st.session_state.system_response)
        st.subheader("Assistant Voice Reply")
        _render_voice_reply("final_response")


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
        "confirmation_audio_digest": "",
        "command_text": "",
        "confirmation_text": "",
        "command_audio_nonce": 0,
        "confirmation_audio_nonce": 0,
        "asr_message": "",
        "confirmation_asr_message": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _render_voice_conversation() -> None:
    st.subheader("Voice Conversation")
    st.caption("主流程：录音指令 -> 本地转写 -> 语音确认 -> 执行 -> 语音回复")
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

    st.markdown("**Demo examples**")
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

    audio_file = st.audio_input(
        "再次点击录音，请说“确认”或“取消”",
        key=f"confirmation_audio_{st.session_state.confirmation_audio_nonce}",
    )
    if audio_file is not None:
        _transcribe_new_audio(
            audio_file,
            digest_key="confirmation_audio_digest",
            text_key="confirmation_text",
            message_key="confirmation_asr_message",
        )

    if st.session_state.confirmation_asr_message:
        st.caption(st.session_state.confirmation_asr_message)
    confirmation_text = st.text_input(
        "Confirmation ASR text (editable)",
        key="confirmation_text",
        placeholder="确认 / 取消",
    )
    if st.button(
        "Submit confirmation",
        key="submit_voice_confirmation",
        type="primary",
        use_container_width=True,
    ):
        _handle_confirmation(confirmation_text)
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


def _handle_confirmation(text: str) -> None:
    decision = parse_confirmation_text(text)
    if decision == "unknown":
        _set_system_response("我没有听清。请说确认或取消。", speak=True)
        return

    if decision == "cancel":
        result = cancel_pending_action()
    else:
        result = apply_confirmed_action(st.session_state.pending_action or {})
        task = result.get("task") or {}
        if result["success"] and task.get("date"):
            _set_selected_date(task["date"])

    _complete_voice_round(result["response_text"])


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
    st.session_state.confirmation_audio_digest = ""
    st.session_state.command_text = ""
    st.session_state.confirmation_text = ""
    st.session_state.command_audio_nonce += 1
    st.session_state.confirmation_audio_nonce += 1
    st.session_state.asr_message = ""
    st.session_state.confirmation_asr_message = ""
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
    render_day_timeline(tasks, st.session_state.selected_date)
    _render_day_timeline_actions(tasks, st.session_state.selected_date)


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
    if entries:
        st.markdown("#### Day Actions")
    for entry in entries:
        task = entry["task"]
        _render_task_actions(task, allow_postpone=task.get("type") == "essential_task")


def _render_flexible_pool(tasks: list[dict]) -> None:
    groups = group_tasks_for_view(tasks, st.session_state.selected_date)
    if not groups["todo_pool"]:
        st.caption("No flexible plans yet.")
    for task in groups["todo_pool"]:
        st.markdown(render_task_card_html(task), unsafe_allow_html=True)
        _render_task_actions(task, allow_postpone=True)


def _render_task_actions(task: dict, allow_postpone: bool) -> None:
    task_id = task.get("id")
    if not task_id:
        return
    columns = st.columns(3 if allow_postpone else 2)
    if columns[0].button("Mark completed", key=f"complete_{task_id}", use_container_width=True):
        updated = mark_task_completed(task_id)
        _complete_voice_round(f"已将{updated['title']}标记为完成。")
        st.rerun()
    if columns[1].button("Delete", key=f"delete_{task_id}", use_container_width=True):
        delete_task(task_id)
        _complete_voice_round(f"已删除{task.get('title', '任务')}。")
        st.rerun()
    if allow_postpone and columns[2].button("Postpone", key=f"postpone_{task_id}", use_container_width=True):
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
