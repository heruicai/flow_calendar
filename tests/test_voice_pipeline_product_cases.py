import pytest

from src.asr_adapter import ASRCandidate, MockASRAdapter
from src.voice_config import VoiceConfig
from src.voice_pipeline import transcribe_audio


CASES = [
    "\u4eca\u5929", "\u660e\u5929", "\u540e\u5929", "\u5468\u4e09", "\u661f\u671f\u4e09", "\u4e0b\u5468\u4e09", "\u4e09\u53f7", "\u4e09\u5929\u540e",
    "\u4e00\u70b9", "\u4e8c\u70b9", "\u4e09\u70b9", "\u56db\u70b9", "\u4e94\u70b9", "\u516d\u70b9", "\u4e03\u70b9", "\u516b\u70b9", "\u4e5d\u70b9", "\u5341\u70b9",
    "\u4e24\u70b9", "\u4e09\u70b9\u534a", "\u4e09\u70b9\u4e00\u523b", "\u4e0a\u5348\u4e09\u70b9", "\u4e0b\u5348\u4e09\u70b9", "\u665a\u4e0a\u4e09\u70b9",
    "\u53c2\u6570\u5b66\u4e60", "\u53c2\u52a0\u9879\u76ee\u4f1a", "\u4e09\u4f53\u8bfb\u4e66\u4f1a", "\u7b2c\u4e09\u7ae0\u590d\u4e60",
    "\u7ec4\u4f1a", "\u7ec4\u7070", "\u4f1a\u8bae", "\u4f1a\u610f", "\u5f00\u4f1a", "\u5f00\u706b", "\u622a\u6b62", "\u63a5\u6b62",
    "\u5f85\u529e", "\u4ee3\u529e", "\u7b97\u6cd5", "\u849c\u7c89", "\u9762\u8bd5", "\u9762\u662f", "\u62a5\u544a", "\u4f5c\u4e1a",
    "\u6d17\u8863\u670d", "\u5403\u996d", "\u4e70\u836f", "\u53d6\u5feb\u9012", "\u590d\u4e60", "\u8bfb\u4e66", "\u953b\u70bc", "\u5199\u4ee3\u7801",
    "\u4eca\u5929\u6709\u4ec0\u4e48\u5b89\u6392", "\u660e\u5929\u6709\u54ea\u4e9b\u4efb\u52a1", "\u5220\u9664\u660e\u5929\u7ec4\u4f1a", "\u7ec4\u4f1a\u5b8c\u6210\u4e86",
    "\u628a\u7ec4\u4f1a\u6539\u5230\u660e\u5929\u4e0b\u5348\u56db\u70b9", "\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u7ec4\u4f1a",
]
CASES += [f"\u660e\u5929\u4e0b\u5348{hour}\u70b9\u4efb\u52a1{index}" for index, hour in enumerate("\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341", 1)]
CASES += [f"\u590d\u4e60\u7b2c{index}\u7ae0" for index in range(1, 21)]


@pytest.mark.parametrize("text", CASES)
def test_at_least_eighty_voice_text_candidates_remain_locally_processable(text):
    assert len(CASES) >= 80
    result = transcribe_audio("unused.wav", adapter=MockASRAdapter([ASRCandidate(text, 0.8, "mock")]), config=VoiceConfig(enable_trace=False))

    assert result["trace_id"]
    assert result["semantic_frame"]
    assert result["decision"]["action"] in {"execute", "confirm", "clarify", "reject"}


def test_pipeline_exposes_structured_fields_and_confirmed_expansion():
    result = transcribe_audio(
        "unused.wav",
        tasks=[{"title": "\u7b97\u6cd5\u9762\u8bd5"}],
        adapter=MockASRAdapter([ASRCandidate("\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u849c\u7c89\u9762\u8bd5", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False),
    )

    assert result["text"].endswith("\u7b97\u6cd5\u9762\u8bd5")
    assert result["decision"]["action"] == "confirm"
    assert result["top_hypotheses"]
