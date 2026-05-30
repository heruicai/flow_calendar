import wave

from streamlit.testing.v1 import AppTest


def test_page_has_one_primary_voice_input_area():
    app = AppTest.from_file("app.py").run(timeout=20)

    assert len(app.exception) == 0
    assert len(app.get("audio_input")) == 1


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
