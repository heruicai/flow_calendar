# FlowCal Architecture

FlowCal is planned as a small local-first Streamlit application.

## Components

- `app.py`: Streamlit entry point and page composition.
- `src/task_store.py`: JSON-backed task persistence.
- `src/command_parser.py`: natural-language command parsing.
- `src/calendar_view.py`: visual task rendering helpers.
- `src/voice_adapter.py`: simulated voice input and future ASR/TTS interfaces.
- `src/response_generator.py`: user-facing response text.

## Data Flow

1. User enters text or simulated voice input.
2. Voice adapter returns transcript text.
3. Command parser extracts intent, task type, time fields, and clarification needs.
4. Task store persists changes to local JSON.
5. Calendar view renders fixed, deadline, essential, and flexible tasks.
6. Response generator summarizes the result.

## Storage

Runtime task data will be stored in `data/tasks.json`. This file is ignored by Git to avoid committing private schedules. Public sample data lives in `data/sample_tasks.json`.
