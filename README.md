# FlowCal

FlowCal is a voice-driven visual calendar assistant. It helps users add, remove, view, and complete reminders through voice-like commands or text input, then responds with text, future voice output, and a calendar-oriented visual view.

This repository is developed in staged feature branches so the commit and PR history clearly shows how the project evolves.

## Project Goals

- Support both voice and text input.
- Provide text, voice, and calendar-view feedback.
- Visualize four task categories:
  - `fixed_event`: fixed appointments such as interviews, meetings, and exams.
  - `deadline_task`: tasks with a due time such as reports and submissions.
  - `essential_task`: daily necessary tasks such as meals, laundry, and medicine.
  - `flexible_plan`: flexible plans such as review, reading, and practice.
- Store task data locally as JSON.
- Keep real ASR and TTS integrations optional behind adapter interfaces.

## Current Stage

Stage 2 adds a persistent JSON task storage system. Later branches will add command parsing, calendar visualization, and voice adapters.

## Project Structure

```text
flow_calendar/
  app.py
  README.md
  requirements.txt
  .gitignore
  src/
    __init__.py
    task_store.py
    command_parser.py
    calendar_view.py
    voice_adapter.py
    response_generator.py
  data/
    sample_tasks.json
  docs/
    architecture.md
    demo_guide.md
  examples/
    sample_commands.md
  tests/
    .gitkeep
```

## Environment

Use the project conda environment:

```powershell
conda activate flow_calendar
python --version
pip install -r requirements.txt
```

Do not install project dependencies into the system Python environment.

## Run

```powershell
conda activate flow_calendar
streamlit run app.py
```

## Task Storage

FlowCal stores tasks in local JSON files:

- `data/tasks.json`: local runtime task data. This file is created automatically when needed and is ignored by Git because it may contain private schedules.
- `data/sample_tasks.json`: public sample data with fictional tasks for demos and tests.

The storage layer lives in `src/task_store.py` and supports loading, saving, adding, updating, deleting, querying by date, listing pending tasks, marking tasks completed, and postponing tasks. JSON is saved with `ensure_ascii=False` and indentation so Chinese task titles remain readable.

## Development Plan

- Stage 1: project structure initialization.
- Stage 2: JSON-backed task storage.
- Stage 3: natural-language command parsing.
- Stage 4: Streamlit interface and visual calendar view.
- Stage 5: voice interaction adapter.
- Stage 6: README, architecture, and demo documentation.

## Data Safety

FlowCal should not commit `.env`, API keys, or real private calendar data. Runtime task data will use `data/tasks.json`, which is intentionally ignored by Git. Public demo data should go in `data/sample_tasks.json`.

## Third-Party Libraries

- Streamlit: app UI framework.
- pytest: test runner for future stages.

## Original Work

Core FlowCal functionality is implemented for this project. If any external code snippets are introduced later, their source must be documented in this README or related docs.
