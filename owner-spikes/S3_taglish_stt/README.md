# Spike S3: Taglish STT word-error rate

## Purpose
Measure STT accuracy on Taglish (Tagalog-English code-switching) speech using fixed prompts.

## What this tells us
- Which STT engine handles Taglish best (faster-whisper, Google Cloud STT Chirp, etc.)
- Word-error rate for each engine
- Whether local faster-whisper is sufficient or cloud STT is needed

## Prerequisites
- Windows 10 or 11
- Python 3.12+
- Microphone
- fixed_prompts.txt (provided) — record yourself reading these prompts

## Steps

1. Open this folder.
2. Read `fixed_prompts.txt` — these are the test phrases in English, Filipino, and Taglish.
3. Record yourself reading each prompt (use your phone or any recorder).
4. Install faster-whisper: `pip install faster-whisper`
5. Run the script:
   ```powershell
   python s3_taglish_stt.py --audio-folder <path-to-your-recordings>
   ```
6. The script transcribes each recording and computes WER against the reference text.
7. Result written to `s3_result.json`.

## Result file
`owner-spikes/S3_taglish_stt/s3_result.json` — paste this back.

## Notes
- Record in a quiet environment.
- Each prompt should be a separate audio file named matching the prompt ID.
- WER = (substitutions + deletions + insertions) / total words.
