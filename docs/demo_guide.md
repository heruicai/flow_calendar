# FlowCal Demo Guide

This guide is written for a 2-4 minute competition demo video.

## Setup

```powershell
conda run -n flow_calendar streamlit run app.py --server.port 8501 --server.headless true
```

Open the local Streamlit page and allow browser microphone access. Prepare the Whisper model before recording the final demo so the first download does not interrupt the video.

## Real Voice Demo Script

1. Introduce FlowCal as a voice-first calendar tool with local speech recognition and local speech output.

2. Add a fixed event.
   - Click the first recording control.
   - Say: `明天下午三点到四点参加算法面试`
   - Show the editable ASR transcription and click `Continue / Parse`.
   - Let FlowCal speak the confirmation prompt.
   - Record a second answer: `确认`
   - Submit the confirmation and hear: `已添加算法面试。`
   - Show the new calendar task.

3. Add an essential task.
   - Start a new voice command.
   - Say: `今天必须洗衣服`
   - Confirm by voice.
   - Show the green `essential_task` bar.

4. Query tomorrow's schedule.
   - Start a new voice command.
   - Say: `我明天有什么安排`
   - Show that a query does not require confirmation.
   - Hear the spoken schedule summary.

5. Complete laundry.
   - Start a new voice command.
   - Say: `洗衣服完成了`
   - Confirm by voice.
   - Show that the completed task turns gray.

6. Mention the fallback.
   - Open `Text Command fallback`.
   - Explain that typed commands remain available when a microphone is unavailable.

## Notes

- Recordings are transcribed locally and are not uploaded to an external speech service.
- Generated WAV replies are runtime files under `outputs/audio/` and must not be committed.
- Use only fictional demo tasks.
