# FlowCal

## 1. Project Overview

FlowCal is a voice-driven visual calendar management assistant for the theme "voice version of a calendar tool". It supports microphone or text commands to add, delete, query, and complete calendar reminders, then returns text, local speech audio, and a visual calendar view.

## 2. User Needs

FlowCal is designed for users who manage plans under real time pressure:

- They need to add events quickly without opening several forms.
- They want to ask for today's or tomorrow's schedule with natural language or voice.
- Their plans often change, so they need to see which time ranges are already occupied.
- Different tasks have different time constraints: fixed events, deadlines, life-essential tasks, and flexible plans.
- They need more than natural-language replies; they also need a visual calendar view.

## 3. Core Features

- Push-to-talk microphone input with editable transcription.
- Add calendar tasks.
- Delete tasks.
- Query schedule.
- Mark tasks completed.
- Undo completed tasks from their task cards.
- Edit task schedules, deadlines, and task types from compact card controls.
- Offline voice confirmation and final response.
- Visual calendar view.
- Local JSON task storage.

## 4. Task Model

FlowCal separates tasks into four visual categories:

- `fixed_event`: fixed-time tasks such as interviews, meetings, exams, and classes. Displayed as blue calendar time blocks.
- `deadline_task`: deadline-driven tasks such as reports, homework, and submissions. Displayed as orange timeline cards.
- `essential_task`: life-essential tasks such as laundry, meals, medicine, and package pickup. Displayed as green daily task bars.
- `flexible_plan`: flexible plans such as coding practice, review, reading, and preparation. Displayed in the todo pool instead of being forced into the calendar.
- `completed`: completed tasks are displayed in gray across all categories.

## 5. Voice Interaction Design

FlowCal uses a push-to-talk voice conversation as the primary flow:

1. The browser records microphone audio through Streamlit `st.audio_input`.
2. `faster-whisper` transcribes the recording locally. The transcription remains editable before parsing.
3. Add, delete, and completion commands produce a spoken and written confirmation question.
4. The user clicks the matching confirmation button or `取消本次操作`. This avoids a second ASR round causing an accidental mutation.
5. Confirmed changes are written to the local task store and the final result is spoken aloud.
6. Schedule queries return concrete task details immediately in text and speech without a confirmation round.

`pyttsx3` generates local WAV voice replies. Audio recordings are not uploaded to an external speech service, and no API key is required. The first ASR run downloads the selected Whisper model if it is not already cached; after that, transcription runs locally. Text command input remains available as a fallback.

## 6. Calendar Visualization Design

FlowCal uses visual rules to match task intent:

- `fixed_event`: blue time block for fixed, non-movable calendar occupation.
- `deadline_task`: orange timeline card for deadline pressure and latest start time.
- `essential_task`: green daily bar for must-do life tasks outside fixed meetings.
- `flexible_plan`: todo-pool item that does not automatically enter the calendar, avoiding unnecessary pressure.
- `completed`: gray style so finished tasks remain visible but visually de-emphasized.

## 7. System Architecture

Main modules:

- `app.py`: Streamlit entry point, compact two-column layout, command execution, and UI actions.
- `src/task_store.py`: JSON-backed local persistence for tasks and completion state.
- `src/command_parser.py`: rule-based natural-language command parser.
- `src/calendar_view.py`: task grouping, style mapping, and visual calendar rendering helpers.
- `src/voice_adapter.py`: microphone recording transcription and local WAV speech output.
- `src/dialog_manager.py`: pending-action confirmation prompts and confirmed mutations.
- `src/response_generator.py`: text response and schedule summary helpers.

Flow:

```text
Microphone/Text Input
-> local ASR adapter
-> dynamic task vocabulary context
-> ASR postprocessor
-> candidate reranker
-> optional GLM parser or local rule parser
-> dialog_manager confirmation
-> task_store
-> calendar_view
-> response_generator / voice_adapter
-> Text / Voice / Calendar Response
```

Voice modules:

- `src/voice_understanding/`: structured local hypotheses, semantic frames, risk decisions, and JSONL traces.
- `src/asr_adapter.py`: lazy-loaded local ASR interface with Whisper, optional FunASR/SenseVoice, and mock adapters.
- `src/voice_context_builder.py`: bounded dynamic vocabulary from local task titles and calendar-domain terms.
- `src/asr_postprocessor.py`: OpenCC normalization plus context-supported similarity correction.
- `src/asr_reranker.py`: ranks one or more ASR hypotheses using task, domain, time, and parser evidence.
- `src/voice_pipeline.py`: orchestrates the local voice pipeline and records correction confidence.

## 8. Installation

Create the project environment:

```powershell
conda create -n flow_calendar python=3.11
conda activate flow_calendar
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

If the environment already exists:

```powershell
conda activate flow_calendar
streamlit run app.py --server.port 8501
```

Do not install project dependencies into the system Python environment.

Open the local URL shown by Streamlit and allow microphone access in the browser. For local development, browsers generally permit microphone access on `localhost`. The default local ASR model is `base`; set `FLOWCAL_WHISPER_MODEL=small` before launching Streamlit when a larger, more accurate local model is preferred.

### Local voice pipeline configuration

The default voice path is local and free: it does not upload audio or call a paid speech API. Settings are optional environment variables:

```powershell
$env:VOICE_ASR_ENGINE="whisper"
$env:VOICE_ASR_MODEL="base"
$env:VOICE_ASR_DEVICE="cpu"
$env:VOICE_ASR_COMPUTE_TYPE="int8"
$env:VOICE_ASR_LANGUAGE="zh"
$env:VOICE_ASR_INITIAL_PROMPT=""
$env:VOICE_ASR_HOTWORDS="kernelPCA,FlowCal"
$env:VOICE_ENABLE_CONTEXT_BIAS="true"
$env:VOICE_ENABLE_SEMANTIC_CORRECTION="true"
$env:VOICE_ENABLE_CONFIRMATION="true"
$env:VOICE_CORRECTION_THRESHOLD="0.85"
$env:VOICE_CONFIRMATION_THRESHOLD="0.65"
$env:VOICE_MAX_CONTEXT_TERMS="80"
$env:VOICE_PRIVACY_MODE="local"
$env:VOICE_ALLOW_CLOUD="0"
$env:VOICE_ENABLE_TRACE="1"
$env:VOICE_TRACE_DIR="outputs/voice_traces"
$env:VOICE_AUTO_EXECUTE_THRESHOLD="0.88"
$env:VOICE_CONFIRM_MARGIN_THRESHOLD="0.12"
$env:VOICE_REJECT_AUDIO_QUALITY_THRESHOLD="0.35"
$env:VOICE_SAVE_RAW_AUDIO="0"
```

See [`docs/local_voice_understanding_engine.md`](docs/local_voice_understanding_engine.md)
for architecture, traces, local SenseVoice/FunASR opt-in behavior, privacy, and
test commands.

`VOICE_ASR_ENGINE=funasr` or `sensevoice` enables the optional local adapter when its package and model are installed. If that optional package is absent, FlowCal falls back to the existing local Whisper path. Models remain lazy-loaded, so importing the application does not download or initialize a large model.

The old fixed typo map remains only as a compatibility fallback for a few recurring ASR mistakes. It is no longer the primary correction strategy. The postprocessor now builds vocabulary from local tasks, converts Traditional Chinese to Simplified Chinese, normalizes full-width text, compares contextual candidates, reranks ASR hypotheses, and flags uncertain corrections for confirmation. False corrections can still occur for short ambiguous phrases, unusual names not present in local context, and noisy recordings.

Run the local text-side smoke test with:

```powershell
conda run -n flow_calendar python -m scripts.voice_pipeline_smoke_test
```

## 9. Example Commands

- 明天下午三点到四点参加算法面试
- 周五前完成报告，预计三小时
- 今天必须洗衣服
- 添加弹性任务，刷两道 LeetCode
- 我明天有什么安排
- 洗衣服完成了
- 删除明天下午的算法面试

More demo commands are available in `examples/sample_commands.md`.

## 10. Demo Video

Demo video: To be updated.

Planned demo content:

- Real microphone voice input.
- Add a `fixed_event`.
- Add a `deadline_task`.
- Add an `essential_task`.
- Add a `flexible_plan`.
- Query schedule.
- Mark a task completed and show the gray completed style.
- Use task-specific timeline buttons directly below each card.
- Hear spoken confirmation and final replies.
- Confirm mutations with buttons after the spoken prompt.

## 11. Dependencies

Third-party dependencies:

- `streamlit`: web app UI framework.
- `pytest`: automated test runner.
- `faster-whisper`: offline ASR inference after the Whisper model has been downloaded locally.
- `pyttsx3`: offline TTS generation; on Windows it uses the installed SAPI voices.
- `openai`: OpenAI-compatible SDK used only by the optional GLM semantic parser.
- `opencc-python-reimplemented`: local Traditional-to-Simplified Chinese conversion.
- `pypinyin`: local pinyin similarity scoring for context-supported ASR corrections.

No external voice API is used. No API key is required. Whisper model preparation requires network access only when the model is not already cached. Generated WAV files live under `outputs/audio/` and are ignored by Git.

## AI Semantic Parser with GLM

FlowCal supports an optional GLM AI semantic parser for more flexible calendar commands and complex task updates. The local rule-based parser remains the default when no API key is configured. If GLM fails, times out, returns invalid JSON, or returns an unsupported structure, FlowCal automatically falls back to the local parser.

When GLM confidently corrects an ASR mistake or typo, FlowCal displays the corrected `Normalized user input` in the conversation panel and uses that text for semantic parsing. Uncertain text is preserved instead of being rewritten aggressively.

All visible Chinese text passes through local OpenCC Traditional-to-Simplified conversion. FlowCal also applies a small local dictionary for recurring ASR homophone mistakes. With GLM enabled, the parser can use minimal task context to correct additional high-confidence homophone errors, especially task names.

Configure GLM with environment variables. Never write API keys into source code or commit them to GitHub.

Windows PowerShell:

```powershell
$env:ZHIPU_API_KEY="your_api_key_here"
$env:ZHIPU_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
$env:ZHIPU_MODEL="glm-4-flash-250414"
```

Linux/macOS:

```bash
export ZHIPU_API_KEY="your_api_key_here"
export ZHIPU_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
export ZHIPU_MODEL="glm-4-flash-250414"
```

`ZHIPU_BASE_URL` and `ZHIPU_MODEL` are optional. When `ZHIPU_API_KEY` is not set, FlowCal continues using the local rule-based parser.

Privacy behavior:

- By default, FlowCal does not call an external semantic model.
- After `ZHIPU_API_KEY` is configured, FlowCal sends only normalized user text and minimal task context to GLM for semantic parsing.
- Audio recordings are never uploaded to GLM.
- FlowCal does not upload the complete local `data/tasks.json` file. Task context is limited to `title`, `date`, `type`, and `status`.
- API keys must remain in local environment variables and must not be committed.

## 12. Original Work

Original FlowCal work includes:

- Task classification model.
- Local JSON task storage system.
- Voice/text command parsing rules.
- Calendar visualization design.
- Voice interaction adapter layer.
- Streamlit two-column interaction page with a left conversation panel and a calendar-focused main panel.
- Test cases for storage, parser, calendar view, and voice adapter.

The core implementation was developed for this project. No previous personal project code was reused.

## 13. Development Record

FlowCal was developed incrementally:

- Feature branches for each stage.
- Pull Requests for review and merge history.
- Incremental commits instead of one large final commit.
- Tests in each major stage.

The repository may remain private during the competition development period and can be made public after submission requirements allow it. The documentation is prepared for public review and does not include `.env`, API keys, or real private schedule data.
