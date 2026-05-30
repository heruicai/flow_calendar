import wave
from inspect import getsource

from streamlit.testing.v1 import AppTest

import app as app_module
from app import _render_page_styles, _task_action_specs, main


def test_page_has_one_primary_voice_input_area():
    app = AppTest.from_file("app.py").run(timeout=20)

    assert len(app.exception) == 0
    assert len(app.get("audio_input")) == 1
    assert "Demo examples" in [expander.label for expander in app.expander]


def test_main_uses_compact_two_column_layout_with_task_panels_on_left():
    source = getsource(main)

    assert "left, right = st.columns([1, 2.1], gap=\"medium\")" in source
    assert "left, center, right" not in source
    assert source.index('with left:') < source.index('with st.expander("Flexible Task Pool"')
    assert source.index('with st.expander("Flexible Task Pool"') < source.index('with right:')
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
    assert ("postpone", "timeline_postpone_deadline-1") in first


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
    monkeypatch.setattr(app_module.st, "rerun", lambda: None)

    app_module._render_task_actions(
        {"id": "done-2", "title": "Laundry", "type": "essential_task", "status": "completed"},
        context="timeline",
    )

    assert pending_task_ids == ["done-2"]


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
