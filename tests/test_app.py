import wave
from inspect import getsource
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

import app as app_module
from app import (
    _cancel_task_editing,
    _render_page_styles,
    _render_task_actions,
    _start_task_editing,
    _task_action_specs,
    _task_editor_specs,
    main,
)


def test_page_has_one_primary_voice_input_area():
    app = AppTest.from_file("app.py").run(timeout=20)

    assert len(app.exception) == 0
    assert len(app.get("audio_input")) == 1
    assert "Demo examples" in [expander.label for expander in app.expander]
    assert "Flexible Task Pool" not in [expander.label for expander in app.expander]
    assert any(subheader.value == "Flexible Task Pool" for subheader in app.subheader)


def test_main_uses_compact_two_column_layout_with_task_panels_on_left():
    source = getsource(main)

    assert "left, right = st.columns([1, 2.1], gap=\"medium\")" in source
    assert "left, center, right" not in source
    assert source.index('with left:') < source.index('st.subheader("Flexible Task Pool")')
    assert source.index('st.subheader("Flexible Task Pool")') < source.index('with right:')
    assert 'st.expander("Flexible Task Pool"' not in source
    assert source.index('with st.expander("Assistant Reply"') < source.index('with right:')


def test_title_and_subtitle_keep_visible_compact_spacing():
    main_source = getsource(main)
    style_source = getsource(_render_page_styles)

    assert 'st.title("FlowCal")' in main_source
    assert 'st.caption("Voice-first visual calendar assistant")' in main_source
    assert "line-height: 1.25 !important;" in style_source
    assert "overflow: visible !important;" in style_source


def test_task_action_specs_bind_unique_keys_to_each_task_id():
    first = _task_action_specs({"id": "deadline-1", "type": "deadline_task"}, "timeline")
    second = _task_action_specs({"id": "deadline-2", "type": "deadline_task"}, "timeline")

    keys = [key for _, key in first + second]
    assert len(keys) == len(set(keys))
    assert ("complete", "timeline_complete_deadline-1") in first
    assert ("delete", "timeline_delete_deadline-1") in first
    assert ("postpone", "timeline_postpone_deadline-1") not in first


def test_task_actions_and_editors_follow_task_type():
    fixed = {"id": "fixed", "type": "fixed_event"}
    deadline = {"id": "deadline", "type": "deadline_task"}
    essential = {"id": "essential", "type": "essential_task"}

    assert "postpone" not in dict(_task_action_specs(fixed, "timeline"))
    assert _task_editor_specs(fixed) == ["edit_time", "edit_type"]
    assert "postpone" not in dict(_task_action_specs(deadline, "timeline"))
    assert _task_editor_specs(deadline) == ["edit_deadline", "edit_type"]
    assert "postpone" in dict(_task_action_specs(essential, "timeline"))
    assert _task_editor_specs(essential) == ["edit_type"]


def test_edit_controls_are_buttons_without_visible_task_ids():
    source = getsource(app_module)

    assert '"Edit time"' in source
    assert '"Edit deadline"' in source
    assert '"Edit type"' in source
    assert '· {task_id}' not in source
    assert 'st.expander(f"Edit time' not in source
    assert 'st.expander(f"Edit deadline' not in source
    assert 'st.expander(f"Edit type' not in source


def test_completed_task_action_specs_offer_undo_and_delete():
    actions = _task_action_specs(
        {"id": "done-1", "type": "essential_task", "status": "completed"},
        "timeline",
    )

    assert actions == [
        ("undo_complete", "timeline_undo_complete_done-1"),
        ("delete", "timeline_delete_done-1"),
    ]


def test_task_action_click_targets_its_own_task_id(monkeypatch):
    deleted_task_ids = []

    class FakeColumn:
        def button(self, label, key, use_container_width):
            return key == "timeline_delete_deadline-2"

    monkeypatch.setattr(app_module.st, "columns", lambda count: [FakeColumn() for _ in range(count)])
    monkeypatch.setattr(app_module, "delete_task", deleted_task_ids.append)
    monkeypatch.setattr(app_module, "_complete_voice_round", lambda message: None)
    monkeypatch.setattr(app_module, "_render_active_task_editor", lambda task, context: None)
    monkeypatch.setattr(app_module.st, "rerun", lambda: None)

    app_module._render_task_actions(
        {"id": "deadline-2", "title": "Report", "type": "deadline_task"},
        context="timeline",
    )

    assert deleted_task_ids == ["deadline-2"]


def test_undo_completed_click_targets_its_own_task_id(monkeypatch):
    pending_task_ids = []

    class FakeColumn:
        def button(self, label, key, use_container_width):
            return key == "timeline_undo_complete_done-2"

    monkeypatch.setattr(app_module.st, "columns", lambda count: [FakeColumn() for _ in range(count)])
    monkeypatch.setattr(
        app_module,
        "mark_task_pending",
        lambda task_id: pending_task_ids.append(task_id) or {"title": "Laundry"},
    )
    monkeypatch.setattr(app_module, "_complete_voice_round", lambda message: None)
    monkeypatch.setattr(app_module, "_render_active_task_editor", lambda task, context: None)
    monkeypatch.setattr(app_module.st, "rerun", lambda: None)

    app_module._render_task_actions(
        {"id": "done-2", "title": "Laundry", "type": "essential_task", "status": "completed"},
        context="timeline",
    )

    assert pending_task_ids == ["done-2"]


def test_edit_button_opens_only_its_task_form(monkeypatch):
    rendered_editors = []

    class FakeColumn:
        def button(self, label, key, use_container_width):
            return key == "timeline_edit_time_fixed-1"

    state = SimpleNamespace(editing_task_id=None, editing_mode=None, editing_context=None)
    monkeypatch.setattr(app_module.st, "session_state", state)
    monkeypatch.setattr(app_module.st, "columns", lambda count: [FakeColumn() for _ in range(count)])
    monkeypatch.setattr(app_module.st, "rerun", lambda: None)
    monkeypatch.setattr(
        app_module,
        "_render_active_task_editor",
        lambda task, context: rendered_editors.append((task["id"], context)),
    )

    _render_task_actions({"id": "fixed-1", "type": "fixed_event"}, "timeline")

    assert state.editing_task_id == "fixed-1"
    assert state.editing_mode == "edit_time"
    assert state.editing_context == "timeline"
    assert rendered_editors == [("fixed-1", "timeline")]


def test_cancel_editing_closes_form_without_mutating_task(monkeypatch):
    task = {"id": "fixed-1", "type": "fixed_event", "date": "2026-05-30"}
    state = SimpleNamespace(
        editing_task_id="fixed-1",
        editing_mode="edit_time",
        editing_context="timeline",
    )
    monkeypatch.setattr(app_module.st, "session_state", state)

    _cancel_task_editing()

    assert task == {"id": "fixed-1", "type": "fixed_event", "date": "2026-05-30"}
    assert state.editing_task_id is None
    assert state.editing_mode is None
    assert state.editing_context is None


def test_starting_another_edit_replaces_previous_form(monkeypatch):
    state = SimpleNamespace(editing_task_id=None, editing_mode=None, editing_context=None)
    monkeypatch.setattr(app_module.st, "session_state", state)

    _start_task_editing("fixed-1", "edit_time", "timeline")
    _start_task_editing("deadline-2", "edit_deadline", "timeline")

    assert state.editing_task_id == "deadline-2"
    assert state.editing_mode == "edit_deadline"


def test_confirmation_step_uses_buttons_without_second_voice_input():
    app = AppTest.from_file("app.py")
    app.session_state["dialog_state"] = "awaiting_confirmation"
    app.session_state["pending_action"] = {"intent": "add_event"}
    app.session_state["system_response"] = "请确认添加算法面试。"
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert len(app.get("audio_input")) == 0
    assert app.button(key="confirm_pending_action").label == "确认添加"
    assert app.button(key="cancel_pending_action").label == "取消本次操作"


def test_confirmation_step_can_render_same_voice_reply_in_two_locations(tmp_path):
    audio_path = tmp_path / "reply.wav"
    with wave.open(str(audio_path), "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(8000)
        audio_file.writeframes(b"\x00\x00" * 80)

    app = AppTest.from_file("app.py")
    app.session_state["dialog_state"] = "awaiting_confirmation"
    app.session_state["pending_action"] = {"intent": "add_event"}
    app.session_state["system_response"] = "请确认添加算法面试。"
    app.session_state["voice_reply"] = {
        "success": True,
        "audio_path": str(audio_path),
        "message": "local test",
        "mode": "pyttsx3",
    }
    app.run(timeout=20)

    assert len(app.exception) == 0


def test_tts_failure_keeps_text_reply_visible():
    app = AppTest.from_file("app.py")
    app.session_state["dialog_state"] = "completed"
    app.session_state["system_response"] = "已添加算法面试。"
    app.session_state["voice_reply"] = {
        "success": False,
        "audio_path": "",
        "message": "tts unavailable",
        "mode": "fallback",
    }
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert any(item.value == "已添加算法面试。" for item in app.info)


def test_update_event_builds_pending_update_action(monkeypatch):
    state = SimpleNamespace(
        pending_action=None,
        dialog_state="idle",
        parser_source="rule",
        last_normalized_command="",
    )
    task = {"id": "laundry", "title": "洗衣服", "type": "essential_task", "date": "2026-05-29"}
    responses = []

    monkeypatch.setattr(app_module.st, "session_state", state)
    monkeypatch.setattr(app_module, "load_tasks", lambda: [task])
    monkeypatch.setattr(app_module, "_set_system_response", lambda message, speak=False: responses.append(message))

    app_module._handle_command("把洗衣服改到明天")

    assert state.dialog_state == "awaiting_confirmation"
    assert state.pending_action["intent"] == "update_event"
    assert state.pending_action["update_plan"]["matched_task"]["id"] == "laundry"
    assert state.pending_action["update_plan"]["updates"]["date"]
    assert "我找到任务：洗衣服" in responses[0]


def test_handle_command_keeps_corrected_text_visible(monkeypatch):
    state = SimpleNamespace(parser_source="rule", last_normalized_command="")

    monkeypatch.setattr(app_module.st, "session_state", state)
    monkeypatch.setattr(app_module, "load_tasks", lambda: [])
    monkeypatch.setattr(
        app_module,
        "parse_user_command",
        lambda *args, **kwargs: {
            "intent": "query_schedule",
            "query": {"date": "2026-05-30"},
            "source": "glm",
            "normalized_text": "明天有什么安排",
        },
    )
    monkeypatch.setattr(app_module, "_set_selected_date", lambda value: None)
    monkeypatch.setattr(app_module, "build_schedule_summary", lambda tasks, selected_date: "summary")
    monkeypatch.setattr(app_module, "_complete_voice_round", lambda message: None)

    app_module._handle_command("明天有神么安排")

    assert state.parser_source == "glm"
    assert state.last_normalized_command == "明天有什么安排"
