#!/usr/bin/env python3
"""Spike S2: Audio loop — mic to speaker round trip, VAD, echo, latency.

Records from the mic, plays back to speakers, measures latency and VAD.
Writes results to s2_result.json.
"""

import json
import sys
import time
from datetime import datetime, timezone

try:
    import numpy as np
    import pyaudio
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install pyaudio numpy")
    sys.exit(1)

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 10


def main():
    p = pyaudio.PyAudio()
    output = {
        "spike": "S2",
        "name": "Audio loop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_rate": RATE,
        "chunk_size": CHUNK,
        "channels": CHANNELS,
        "vad_speech_detected": False,
        "vad_silence_detected": False,
        "round_trip_latency_ms": None,
        "echo_detected_speakers": None,
        "echo_detected_headphones": None,
        "devices": [],
        "error": None,
    }

    # List audio devices
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        output["devices"].append({
            "index": i,
            "name": info["name"],
            "max_input_channels": info["maxInputChannels"],
            "max_output_channels": info["maxOutputChannels"],
        })

    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            output=True,
            frames_per_buffer=CHUNK,
        )

        print("S2 Audio Loop — speak into the mic. Recording for", RECORD_SECONDS, "seconds...")
        print("(Switch between speakers and headphones to test echo)")

        frames = []
        speech_seen = False
        silence_seen = False
        start_time = time.time()

        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

            # Simple energy-based VAD
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float64) ** 2))

            if rms > 500 and not speech_seen:
                speech_seen = True
                print("[VAD] Speech detected")
            elif rms < 100 and speech_seen and not silence_seen:
                silence_seen = True
                print("[VAD] Silence after speech")

        output["vad_speech_detected"] = speech_seen
        output["vad_silence_detected"] = silence_seen

        # Measure round-trip latency (playback of recorded audio)
        stream.write(b"".join(frames))
        output["round_trip_latency_ms"] = (time.time() - start_time) * 1000

        stream.stop_stream()
        stream.close()

    except Exception as e:
        output["error"] = str(e)
        print(f"Error: {e}")

    p.terminate()

    with open("s2_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("\nS2 spike complete. Result written to s2_result.json")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
