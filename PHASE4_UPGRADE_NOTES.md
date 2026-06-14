# VisualAgro Phase 4 Upgrade Notes

## What changed
- Added a vision analytics layer for detection frequency, present stock, missing items, and top-selling items.
- Wired microphone-based voice capture into the desktop app.
- Wired laptop webcam capture into the desktop app for detection and freshness scoring.
- Implemented real STT transcription support in the voice assistant abstraction using optional local Whisper backends.
- Added a new backend endpoint: `/vision/summary`.
- Expanded copilot reasoning to answer vision/presence/movement questions.
- Kept the existing Phase 3 dashboard and buy-list flow backward compatible.

## Camera flow
- Capture a webcam frame locally with OpenCV.
- Send the image to `/detect` or `/freshness`.
- Persist detections and freshness assessments in SQLite for later analytics.

## Voice flow
- Record a 5-second WAV clip from the laptop microphone.
- Send the WAV file to `/voice`.
- Transcribe using `faster-whisper` or `whisper` when available.
- Fall back safely to typed text if STT is unavailable.

## New dependency expectations
- `sounddevice` for microphone recording.
- `faster-whisper` for offline transcription.
- `edge-tts` for spoken responses.
- `ultralytics` + `opencv-python-headless` for computer vision.

## Next recommended step
- Add a lightweight live camera preview panel if the desktop UI should show continuous inventory monitoring instead of single-frame capture.
