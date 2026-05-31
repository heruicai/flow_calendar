from src.voice_understanding.reranker import rank_hypotheses
from src.voice_understanding.schema import Expansion, SemanticFrame, TextHypothesis


def test_reranker_prefers_complete_context_supported_interpretation():
    incomplete = TextHypothesis("raw", "raw", 0.95, "mock", semantic_frame=SemanticFrame(intent="add_event", completeness=0.35))
    complete = TextHypothesis(
        "\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u7ec4\u4f1a",
        "raw",
        0.8,
        "mock",
        [Expansion("raw", "\u7ec4\u4f1a", "context", 0.9)],
        SemanticFrame(intent="add_event", completeness=1.0),
    )

    ranked = rank_hypotheses([incomplete, complete], context_terms=["\u7ec4\u4f1a"])

    assert ranked[0] is complete
    assert ranked[0].scores["final"] > ranked[1].scores["final"]
