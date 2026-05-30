from src.asr_postprocessor import postprocess_asr_text
from src.glm_semantic_parser import parse_user_command


def test_postprocessor_normalizes_opencc_and_full_width_text():
    result = postprocess_asr_text(" 週五　處理專案進度 ")

    assert result["normalized_text"] == "周五处理专案进度"


def test_postprocessor_corrects_context_supported_homophone_task_title():
    result = postprocess_asr_text(
        "提醒我明天下午三点蒜粉面试",
        context_terms=["算法面试"],
        known_task_titles=["算法面试"],
    )

    assert result["corrected_text"] == "提醒我明天下午三点算法面试"
    assert result["confidence"] >= 0.85


def test_postprocessor_corrects_domain_terms_with_context():
    meeting = postprocess_asr_text("明天下午组灰", context_terms=["组会"])
    deadline = postprocess_asr_text("把报告接止时间改到周五", context_terms=["截止时间"])

    assert meeting["corrected_text"] == "明天下午组会"
    assert deadline["corrected_text"] == "把报告截止时间改到周五"


def test_postprocessor_uses_edit_distance_for_context_term():
    result = postprocess_asr_text("复习kernelPC", context_terms=["kernelPCA"])

    assert result["corrected_text"] == "复习kernelPCA"


def test_postprocessor_does_not_apply_low_confidence_guess():
    result = postprocess_asr_text(
        "明天下午算法笔试",
        context_terms=["算法面试"],
        correction_threshold=0.85,
        confirmation_threshold=0.4,
    )

    assert result["corrected_text"] == "明天下午算法笔试"
    assert result["needs_confirmation"] is True


def test_corrected_text_can_still_be_parsed():
    result = postprocess_asr_text(
        "提醒我明天下午三点蒜粉面试",
        context_terms=["算法面试"],
    )

    parsed = parse_user_command(result["corrected_text"], use_ai=False)

    assert parsed["intent"] == "add_event"
    assert parsed["task"]["title"] == "算法面试"
