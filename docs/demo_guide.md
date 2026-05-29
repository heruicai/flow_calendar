# FlowCal Demo Guide

This guide is written for a 2-4 minute competition demo video.

## Demo Video

Demo video: To be updated.

## Setup

```powershell
conda activate flow_calendar
streamlit run app.py
```

Open the local Streamlit page in the browser.

## Script

1. Introduce FlowCal.
   - "FlowCal is a voice-driven visual calendar tool. It lets users manage schedules through voice-like commands or text, then returns text, voice-reply text, and calendar visualization."

2. Show the page layout.
   - Left: Voice / Text Command.
   - Center: Calendar View.
   - Right: Task Panels and System Response.

3. Select `Simulated voice input`.
   - Explain that the current version treats typed text as speech-to-text output.
   - Mention that real ASR can be connected later through `voice_adapter.py`.

4. Add a fixed event.
   - Input: `明天下午三点到四点参加算法面试`
   - Show the blue `fixed_event` block in the calendar view.

5. Add a deadline task.
   - Input: `周五前完成报告，预计三小时`
   - Show the orange Deadline Timeline card.
   - Point out deadline, estimated duration, and latest start time.

6. Add an essential task.
   - Input: `今天必须洗衣服`
   - Show the green essential task card/bar.

7. Add a flexible plan.
   - Input: `添加弹性任务，刷两道 LeetCode`
   - Show the Flexible Task Pool.
   - Explain that flexible plans do not automatically occupy the calendar.

8. Query schedule.
   - Input: `我明天有什么安排`
   - Show that the selected date changes and the system response summarizes the schedule.

9. Mark a task completed.
   - Use `洗衣服完成了` or click `Mark completed`.
   - Show the completed task turning gray.

10. Generate a voice reply.
    - Click `Generate voice reply`.
    - Show the Spoken Response / Voice Reply text.
    - Explain that this is mock TTS now and can be extended later.

11. Summarize original design highlights.
    - Four task categories with different visual expressions.
    - Local JSON task storage.
    - Rule-based voice/text command parser.
    - Streamlit three-column interaction.
    - Voice adapter with future ASR/TTS extension points.

## Notes

- Do not show real private schedules.
- Do not include API keys or `.env` files.
- Use only fictional demo tasks.
