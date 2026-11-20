# Spike S2: Audio loop — mic to speaker round trip, VAD, echo, latency

## Purpose
Measure the audio pipeline on your PC: mic input, speaker output, VAD behavior, echo cancellation (speakers vs headphones), and end-to-end latency.

## What this tells us
- Mic-to-speaker round-trip latency
- Whether VAD correctly detects speech vs silence
- Echo behavior: does Jarvis hearing itself cause loops (speakers) vs clean (headphones)
- Whether WebRTC AEC is needed or half-duplex suffices

## Prerequisites
- Windows 10 or 11
- Python 3.12+ with `pip install pyaudio numpy`
- Microphone and speakers or headphones

## Steps

1. Open this folder:
   ```powershell
   cd owner-spikes/S2_audio_loop
   ```
2. Install dependencies:
   ```powershell
   pip install pyaudio numpy
   ```
3. Run the script:
   ```powershell
   python s2_audio_loop.py
   ```
4. Follow the prompts: speak into the mic, listen for echo, switch between speakers and headphones.
5. Press Ctrl+C when done.
6. The script writes `s2_result.json`.

## Result file
`owner-spikes/S2_audio_loop/s2_result.json` — paste this back.

## Notes
- Speak clearly into the mic; the script measures VAD speech detection.
- Test with speakers first (echo likely), then headphones (echo should be minimal).
- This is read-only — no data leaves your PC.
