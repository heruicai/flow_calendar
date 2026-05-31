# Local Voice Samples

Place private local regression audio files in this directory and list them in
`manifest.json`. Do not commit recordings that contain private information.

Example entry:

```json
{
  "file": "meeting-tomorrow.wav",
  "expected_text": "明天下午三点组会",
  "expected_intent": "add_event"
}
```

Validate the manifest without loading a model:

```powershell
python scripts/voice_samples_regression.py
```

Run real local ASR only after preparing model files locally:

```powershell
python scripts/voice_samples_regression.py --run-local-asr
```
