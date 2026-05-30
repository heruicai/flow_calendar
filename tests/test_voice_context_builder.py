from datetime import date

from src.voice_context_builder import build_asr_prompt, build_voice_context, get_context_terms


def test_context_builder_collects_and_deduplicates_task_titles():
    tasks = [
        {"title": "算法面试", "date": "2026-06-01"},
        {"title": "算法面试", "date": "2026-06-02"},
        {"title": "组会", "date": "2026-06-03"},
    ]

    terms = get_context_terms(tasks, today=date(2026, 5, 30))

    assert terms.count("算法面试") == 1
    assert "组会" in terms
    assert "截止时间" in terms


def test_context_builder_limits_terms_and_prompt_length():
    context = build_voice_context(
        [],
        extra_terms=[f"term-{index}" for index in range(100)],
        max_terms=5,
        initial_prompt="FlowCal",
    )

    assert len(context["terms"]) == 5
    assert len(build_asr_prompt(context["terms"], max_chars=20)) <= 20
