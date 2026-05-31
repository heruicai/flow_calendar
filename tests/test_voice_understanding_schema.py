from dataclasses import asdict

from src.voice_understanding.schema import AudioQuality, SemanticFrame, TextHypothesis, VoiceDecision, VoiceUnderstandingResult


def test_result_schema_serializes_structured_fields():
    hypothesis = TextHypothesis("text", "raw", 0.9, "mock", semantic_frame=SemanticFrame(intent="query_schedule"))
    result = VoiceUnderstandingResult("trace-1", AudioQuality(), VoiceDecision("execute", "ok"), [hypothesis])

    payload = result.to_dict()

    assert payload["trace_id"] == "trace-1"
    assert payload["decision"]["action"] == "execute"
    assert payload["top_hypotheses"][0]["semantic_frame"]["intent"] == "query_schedule"
