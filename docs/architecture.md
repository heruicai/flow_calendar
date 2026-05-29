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

## Voice Adapter

`src/voice_adapter.py` sits between the Streamlit UI and the parser for voice-like input. Text input and simulated voice input both pass through voice normalization before entering `src/command_parser.py`, so future ASR integrations can reuse the same command parsing pipeline.

For replies, `src/response_generator.py` produces the system response text. The voice adapter then converts that text into a shorter spoken response and exposes a mock `text_to_speech` interface. This keeps the app runnable without API keys, network services, or unstable local audio dependencies.

## Storage

Runtime task data will be stored in `data/tasks.json`. This file is ignored by Git to avoid committing private schedules. Public sample data lives in `data/sample_tasks.json`.
