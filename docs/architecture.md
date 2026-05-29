# FlowCal Architecture

FlowCal is a local-first Streamlit application for voice-driven visual calendar management. Its core idea is that voice/text commands and visual calendar feedback should work together: the user can speak or type naturally, while the system responds with text, voice-reply text, and task visualization.

## Module Responsibilities

## `app.py`

`app.py` is the Streamlit entry point. It owns the three-column interface:

- Left: voice/text command input and example commands.
- Center: selected-day calendar view.
- Right: deadline timeline, flexible task pool, system response, and voice reply.

It coordinates parser results with storage actions such as add, query, complete, delete, and postpone.

## `src/voice_adapter.py`

The voice adapter normalizes simulated speech-to-text input before parsing. It also reserves stable ASR and TTS interfaces:

- `normalize_voice_text(text)`: cleans typed or simulated voice text.
- `speech_to_text(audio_file=None)`: future ASR entry point.
- `build_spoken_response(response_text)`: prepares a short spoken response.
- `text_to_speech(response_text)`: mock TTS result for the current version.

Text input and simulated voice input both pass through this adapter before entering the parser, so future voice recognition can reuse the same downstream logic.

## `src/command_parser.py`

The command parser converts normalized natural language into structured commands. It detects:

- Intent: add, delete, query, mark completed.
- Task type: fixed event, deadline task, essential task, flexible plan.
- Time fields: date, start time, end time, deadline, duration, latest start time.
- Clarification needs when important information is missing.

## `src/task_store.py`

The task store persists tasks in local JSON. Runtime data lives in `data/tasks.json`, which is ignored by Git to avoid committing private schedules. Public demo data lives in `data/sample_tasks.json`.

The storage layer supports:

- Loading and saving tasks.
- Adding, updating, deleting, and finding tasks.
- Querying by date.
- Listing pending tasks.
- Marking completed.
- Marking postponed.

This local JSON store supports the calendar view, deadline timeline, flexible task pool, and completed-state rendering.

## `src/calendar_view.py`

The calendar view module groups tasks for visual display:

- `fixed_event` tasks for selected-day calendar blocks.
- `essential_task` tasks for selected-day required-task bars.
- `deadline_task` tasks for the deadline timeline.
- `flexible_plan` tasks for the todo pool.

It also maps completed tasks to gray styles while keeping their original task type.

## `src/response_generator.py`

The response generator creates short system responses and schedule summaries. The voice adapter can then transform those text responses into spoken-response text.

## Data Flow

```text
Voice/Text Input
-> voice_adapter.normalize_voice_text
-> command_parser.parse_command
-> task_store add/update/delete/query
-> calendar_view group/style/render
-> response_generator text response
-> voice_adapter build_spoken_response / text_to_speech
-> Text / Voice / Calendar Response
```

## Voice And Text Input Path

Both input modes use the same parser:

1. `Text input`: typed command is normalized.
2. `Simulated voice input`: typed text is treated as ASR output and normalized.
3. Normalized text is sent to `parse_command`.
4. Parser output drives task storage and UI feedback.

This design keeps the current demo stable while preserving a clean extension point for Whisper, browser speech recognition, or another ASR system.

## Local JSON Storage And View State

Tasks are saved as JSON objects with fields such as `id`, `title`, `type`, `date`, `start_time`, `deadline`, `status`, and `display_mode`.

The UI reads all tasks from `data/tasks.json` and groups them for the selected date:

- Calendar blocks use `date`, `start_time`, and `end_time`.
- Deadline cards use `deadline`, `estimated_duration_minutes`, and `latest_start_time`.
- Essential task bars use `date`, duration, and status.
- Flexible plans stay in the todo pool.
- Completed tasks retain their data but render in gray.

## Safety And Privacy

FlowCal does not require `.env`, API keys, or real private schedule data. Runtime data in `data/tasks.json` is ignored by Git. Demo examples use fictional tasks only.
