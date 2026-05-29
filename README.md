# FlowCal

## 1. Project Overview

FlowCal is a voice-driven visual calendar management assistant for the theme "voice version of a calendar tool". It supports voice-like or text commands to add, delete, query, and complete calendar reminders, then returns three forms of feedback: text response, voice-reply text, and visual calendar view.

The current version uses stable simulated voice input: typed text can be treated as speech-to-text output. Real ASR and TTS integrations are reserved through adapter interfaces.

## 2. User Needs

FlowCal is designed for users who manage plans under real time pressure:

- They need to add events quickly without opening several forms.
- They want to ask for today's or tomorrow's schedule with natural language or voice.
- Their plans often change, so they need to see which time ranges are already occupied.
- Different tasks have different time constraints: fixed events, deadlines, life-essential tasks, and flexible plans.
- They need more than natural-language replies; they also need a visual calendar view.

## 3. Core Features

- Voice/Text command input.
- Add calendar tasks.
- Delete tasks.
- Query schedule.
- Mark tasks completed.
- Voice-style response.
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

FlowCal currently supports two input modes:

- `Text input`: the user types a command directly.
- `Simulated voice input`: the user types text that is treated as speech-to-text output.

Both modes pass through `src/voice_adapter.py` and then enter the same command parser. The adapter includes reserved interfaces:

- `speech_to_text(audio_file=None)`: reserved ASR entry point.
- `text_to_speech(response_text)`: mock TTS entry point that returns voice-reply metadata.

The current version does not depend on external API keys or cloud voice services. Future versions can connect Whisper, browser speech recognition, or local TTS engines.

## 6. Calendar Visualization Design

FlowCal uses visual rules to match task intent:

- `fixed_event`: blue time block for fixed, non-movable calendar occupation.
- `deadline_task`: orange timeline card for deadline pressure and latest start time.
- `essential_task`: green daily bar for must-do life tasks outside fixed meetings.
- `flexible_plan`: todo-pool item that does not automatically enter the calendar, avoiding unnecessary pressure.
- `completed`: gray style so finished tasks remain visible but visually de-emphasized.

## 7. System Architecture

Main modules:

- `app.py`: Streamlit entry point, three-column layout, command execution, and UI actions.
- `src/task_store.py`: JSON-backed local persistence for tasks and completion state.
- `src/command_parser.py`: rule-based natural-language command parser.
- `src/calendar_view.py`: task grouping, style mapping, and visual calendar rendering helpers.
- `src/voice_adapter.py`: simulated voice input normalization and mock ASR/TTS adapter.
- `src/response_generator.py`: text response and schedule summary helpers.

Flow:

```text
Voice/Text Input
-> voice_adapter
-> command_parser
-> task_store
-> calendar_view
-> response_generator / voice_adapter
-> Text / Voice / Calendar Response
```

## 8. Installation

Create the project environment:

```powershell
conda create -n flow_calendar python=3.11
conda activate flow_calendar
pip install -r requirements.txt
streamlit run app.py
```

If the environment already exists:

```powershell
conda activate flow_calendar
streamlit run app.py
```

Do not install project dependencies into the system Python environment.

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

- Simulated voice input.
- Add a `fixed_event`.
- Add a `deadline_task`.
- Add an `essential_task`.
- Add a `flexible_plan`.
- Query schedule.
- Mark a task completed and show the gray completed style.
- Generate a voice reply.

## 11. Dependencies

Third-party dependencies:

- `streamlit`: web app UI framework.
- `pytest`: automated test runner.

No external voice API is used. No API key is required. No additional voice dependency is introduced in the current version.

## 12. Original Work

Original FlowCal work includes:

- Task classification model.
- Local JSON task storage system.
- Voice/text command parsing rules.
- Calendar visualization design.
- Voice interaction adapter layer.
- Streamlit three-column interaction page.
- Test cases for storage, parser, calendar view, and voice adapter.

The core implementation was developed for this project. No previous personal project code was reused.

## 13. Development Record

FlowCal was developed incrementally:

- Feature branches for each stage.
- Pull Requests for review and merge history.
- Incremental commits instead of one large final commit.
- Tests in each major stage.

The repository may remain private during the competition development period and can be made public after submission requirements allow it. The documentation is prepared for public review and does not include `.env`, API keys, or real private schedule data.
