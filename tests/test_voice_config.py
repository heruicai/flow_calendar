from src.voice_config import get_voice_config


def test_voice_config_reads_local_asr_environment(monkeypatch):
    monkeypatch.setenv("VOICE_ASR_ENGINE", "funasr")
    monkeypatch.setenv("VOICE_ASR_MODEL", "sensevoice-small")
    monkeypatch.setenv("VOICE_ASR_HOTWORDS", "kernelPCA,FlowCal")
    monkeypatch.setenv("VOICE_ENABLE_SEMANTIC_CORRECTION", "false")
    monkeypatch.setenv("VOICE_CORRECTION_THRESHOLD", "0.9")

    config = get_voice_config()

    assert config.asr_engine == "funasr"
    assert config.asr_model == "sensevoice-small"
    assert config.hotwords == "kernelPCA,FlowCal"
    assert config.enable_semantic_correction is False
    assert config.correction_threshold == 0.9
