# Local Voice Understanding Engine

FlowCal's product voice path is local-first and zero-cost by default. It does
not call GLM, OpenAI, cloud ASR, cloud TTS, or any API-key-backed service.

## Why ASR text is not enough

Chinese calendar commands are sensitive to homophones, segmentation, numbers,
dates, times, task titles, and existing task names. A fixed replacement table
cannot distinguish a valid title such as `参数学习` from an invalid time-like
fragment such as `参点`. Silent correction is unsafe because a plausible text
string can still describe the wrong calendar mutation.

The engine therefore works with interpretations:

```text
audio quality
-> local ASR candidates
-> bounded local context
-> normalized text hypotheses
-> contextual and phonetic expansions
-> local semantic frames
-> explainable reranking
-> execute / confirm / clarify / reject
-> local JSONL trace
```

Each expansion records its source fragment, target fragment, reason, slot, and
confidence. The original ASR text remains a candidate. An expansion never
silently authorizes a mutation.

## Risk policy

Low-risk, high-confidence additions and schedule queries may execute directly.
Deletes and updates always require confirmation. Voice-based completion
commands require confirmation. Ambiguous or incomplete frames ask a focused
question. Empty, unreadable, or clearly unsuitable audio is rejected early.

## Configuration

Defaults:

```text
VOICE_ASR_ENGINE=sensevoice
VOICE_ASR_MODEL=iic/SenseVoiceSmall
VOICE_SENSEVOICE_MODEL_PATH=C:\Users\xjy\.cache\modelscope\hub\models\iic\SenseVoiceSmall
VOICE_SENSEVOICE_ALLOW_DOWNLOAD=0
VOICE_ENABLE_DUAL_ASR=0
VOICE_ASR_FALLBACK_ENGINE=none
VOICE_WHISPER_MODEL=large-v3-turbo
VOICE_WHISPER_MODEL_PATH=
VOICE_WHISPER_ALLOW_DOWNLOAD=0
VOICE_ALLOW_CLOUD=0
VOICE_ENABLE_TRACE=1
VOICE_TRACE_DIR=outputs/voice_traces
VOICE_AUTO_EXECUTE_THRESHOLD=0.88
VOICE_CONFIRM_MARGIN_THRESHOLD=0.12
VOICE_REJECT_AUDIO_QUALITY_THRESHOLD=0.35
VOICE_SAVE_RAW_AUDIO=0
VOICE_ENABLE_ASR_DIAGNOSTICS=1
```

The default Chinese path uses the prepared local SenseVoiceSmall directory.
SenseVoice metadata tags such as `<|zh|>` and `<|NEUTRAL|>` are removed before
semantic parsing while the original tagged text remains available in trace
diagnostics. `VOICE_ASR_ENGINE=funasr` selects the local FunASR adapter. Install
optional dependencies with:

```powershell
pip install torch torchaudio funasr modelscope
```

Missing optional dependencies or a missing local SenseVoice directory produce
a preparation hint. Nothing is downloaded by default.

Whisper `large-v3-turbo` remains available as an explicit fallback. Enable it
only with:

```powershell
$env:VOICE_ENABLE_DUAL_ASR="1"
$env:VOICE_ASR_FALLBACK_ENGINE="whisper"
$env:VOICE_WHISPER_MODEL_PATH="D:\models\large-v3-turbo"
```

Alternatively, explicitly set `VOICE_WHISPER_ALLOW_DOWNLOAD=1` to allow
`faster-whisper` to fetch the configured model. Whisper uses `language="zh"`,
`beam_size=5`, `temperature=0`, `vad_filter=True`, and a dynamic local prompt.
Tests use `MockASRAdapter` and never download weights.

Every recognition prints a `[flowcal-asr]` JSON line containing engine, model,
language, beam size, VAD state, prompt injection state, audio duration, raw
text, cleaned text, removed tags, local model path, torchaudio availability,
ffmpeg availability, dual-ASR state, and fallback state. When explicitly
enabled independent ASR outputs diverge, or only one candidate yields a
complete calendar frame, the risk policy requires confirmation.

SenseVoice can use `torchaudio` when ffmpeg is absent. Installing ffmpeg remains
recommended for wider audio-format compatibility.

The existing GLM semantic parser remains a legacy optional path for typed
commands. The productized voice understanding pipeline does not invoke it, even
when `ZHIPU_API_KEY` or `OPENAI_API_KEY` exists in the environment. The UI only
enables that legacy parser when `VOICE_ALLOW_CLOUD=1` is also set explicitly.

## Traces and privacy

Local traces are appended to:

```text
outputs/voice_traces/YYYYMMDD.jsonl
```

Trace files are gitignored. They include quality metadata, sanitized text
hypotheses, semantic frames, scores, decision, and trace ID. Raw audio is not
stored by default. Enabling `VOICE_SAVE_RAW_AUDIO=1` must only be used for
local debugging with explicit attention to privacy; raw audio remains outside
Git.

## Tests

Run:

```powershell
python -m pytest -q
python scripts/voice_pipeline_smoke_test.py
```

The suite uses fake ASR candidates, covers more than 80 local text cases, and
fails if the product voice pipeline attempts to use the legacy cloud parser.

Real local audio regression is opt-in:

```powershell
python scripts/voice_samples_regression.py
python scripts/voice_samples_regression.py --run-local-asr
```

The first command validates `examples/voice_samples/manifest.json` without
loading models. The second command runs installed local models after their
files have been prepared locally.

## Push the feature branch

After reviewing the local commit:

```bash
git remote add origin https://github.com/heruicai/flow_calendar 2>/dev/null || git remote set-url origin https://github.com/heruicai/flow_calendar
git push -u origin feature/local-voice-understanding-engine
```
