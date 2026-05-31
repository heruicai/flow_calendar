from src.voice_understanding.risk_policy import decide
from src.voice_understanding.schema import AudioQuality, Expansion, SemanticFrame, TextHypothesis


def _hypothesis(intent="add_event", *, score=0.95, complete=1.0, expansions=None):
    return TextHypothesis("text", "raw", 0.95, "mock", expansions or [], SemanticFrame(intent=intent, completeness=complete), {"final": score})


def test_bad_audio_is_rejected():
    assert decide([], AudioQuality(0.0, False, "empty")).action == "reject"


def test_delete_update_and_voice_completion_never_auto_execute():
    for intent in ("delete_event", "update_event", "mark_completed"):
        assert decide([_hypothesis(intent)], AudioQuality()).action == "confirm"


def test_expansion_requires_confirmation():
    expansion = Expansion("x", "y", "context", 0.9)
    assert decide([_hypothesis(expansions=[expansion])], AudioQuality()).action == "confirm"


def test_high_confidence_low_risk_add_can_execute():
    assert decide([_hypothesis()], AudioQuality()).action == "execute"
