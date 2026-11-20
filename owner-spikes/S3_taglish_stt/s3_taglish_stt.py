#!/usr/bin/env python3
"""Spike S3: Taglish STT word-error rate measurement.

Transcribes audio recordings and computes WER against reference text.
Writes results to s3_result.json.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fixed prompts for Taglish STT testing
FIXED_PROMPTS = {
    "en-01": "Hello, what time is it?",
    "fil-01": "Kumusta ka? Ano ang plano mo ngayon?",
    "taglish-01": "Hey Jarvis, paano po ako papasok sa meeting bukas?",
    "taglish-02": "Can you remind me about my appointment sa mga alas-dose?",
    "taglish-03": "Magandang umaga po. Ano ang balita ngayon?",
}


def wer(reference: str, hypothesis: str) -> float:
    """Simple word-error rate."""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    # Levenshtein distance on word level
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # deletion
                    dp[i][j - 1],      # insertion
                    dp[i - 1][j - 1],  # substitution
                )

    return dp[m][n] / max(m, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-folder", required=True, help="Folder with recordings")
    parser.add_argument("--engine", default="faster-whisper", choices=["faster-whisper"])
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Install faster-whisper: pip install faster-whisper")
        sys.exit(1)

    audio_folder = Path(args.audio_folder)
    model = WhisperModel("base", device="cpu", compute_type="int8")

    output = {
        "spike": "S3",
        "name": "Taglish STT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": args.engine,
        "model": "base",
        "device": "cpu",
        "results": [],
        "average_wer": None,
        "error": None,
    }

    wers = []
    for prompt_id, reference in FIXED_PROMPTS.items():
        audio_file = audio_folder / f"{prompt_id}.wav"
        if not audio_file.exists():
            output["results"].append({
                "prompt_id": prompt_id,
                "reference": reference,
                "hypothesis": "FILE NOT FOUND",
                "wer": None,
            })
            continue

        segments, _ = model.transcribe(str(audio_file), language=None)
        hypothesis = " ".join(seg.text for seg in segments)
        error_rate = wer(reference, hypothesis)
        wers.append(error_rate)

        output["results"].append({
            "prompt_id": prompt_id,
            "reference": reference,
            "hypothesis": hypothesis,
            "wer": round(error_rate, 4),
        })

    if wers:
        output["average_wer"] = round(sum(wers) / len(wers), 4)

    with open("s3_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
