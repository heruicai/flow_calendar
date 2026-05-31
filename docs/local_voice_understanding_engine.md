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
VOICE_ASR_ENGINE=whisper
VOICE_ALLOW_CLOUD=0
VOICE_ENABLE_TRACE=1
VOICE_TRACE_DIR=outputs/voice_traces
VOICE_AUTO_EXECUTE_THRESHOLD=0.88
VOICE_CONFIRM_MARGIN_THRESHOLD=0.12
VOICE_REJECT_AUDIO_QUALITY_THRESHOLD=0.35
VOICE_SAVE_RAW_AUDIO=0
```

`VOICE_ASR_ENGINE=funasr` enables local FunASR when its optional dependency and
model are already installed. `VOICE_ASR_ENGINE=sensevoice` enables the separate
local SenseVoice adapter under the same explicit opt-in rule. Missing optional
dependencies fall back to local Whisper. Tests use `MockASRAdapter` and never
download model weights.

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

## Push the feature branch

After reviewing the local commit:

```bash
git remote add origin https://github.com/heruicai/flow_calendar 2>/dev/null || git remote set-url origin https://github.com/heruicai/flow_calendar
git push -u origin feature/local-voice-understanding-engine
```
