# JARVIS Open Questions

Each question has context, options, and a recommended default. Provisional unless it blocks progress.

## Q1: Cloud, local, or hybrid AI?

**Context:** The owner's GPU and RAM are unknown. Cloud LLMs cost money but work on any hardware. Local LLMs are private and free but need a strong GPU.

**Options:**
- **Hybrid (recommended default):** Local voice front end (wake word, VAD, STT, TTS), cloud LLM for reasoning, local Ollama fallback. Owner configures the mix.
- Local-only: everything runs on the PC. Needs strong GPU, more complex setup.
- Cloud-only: simplest to build, but costs money and sends audio/text to third parties.

**Recommended default:** Hybrid. Proceed with hybrid as provisional. Blocks: nothing — the model layer is abstracted behind a port.

---

## Q2: PC's GPU and RAM?

**Context:** Determines whether local LLM and local STT/TTS are viable. I cannot inspect the owner's hardware.

**Options:**
- **Strong GPU (8GB+ VRAM), 16GB+ RAM:** Run local Llama/Ollama + faster-whisper locally.
- **Modest hardware:** Cloud LLM + local faster-whisper + Piper TTS.
- **Unknown / don't want to buy:** Hybrid default; owner confirms at first run.

**Recommended default:** Hybrid with cloud LLM, local voice. Provisional — owner confirms at first run.

---

## Q3: Self-hosted mautrix-meta Messenger bridge on a spare account?

**Context:** Backend B gives full Messenger read/write but carries detection risk (checkpoints, forced password changes). Brief says trial on spare account, never main account.

**Options:**
- **Yes, opt-in (recommended default):** Provide S6 spike kit and runbook. Owner tries on spare account for ~1 week.
- No: Skip bridge entirely, use notification-only (backend A) and passive reader (backend C).
- Yes, on main account: **Not recommended** — violates risk guidance.

**Recommended default:** Yes, opt-in, spare account only. Provisional.

---

## Q4: Android distribution?

**Context:** Phase 2. Google Play requires default SMS/Assistant role for SMS permissions. Sideload avoids Play review but no auto-updates.

**Options:**
- **Sideload personal build (recommended default):** APK installed manually, no Play restrictions, no auto-update via Play.
- Google Play: register as default SMS/Assistant, go through review, slower iteration.
- F-Droid or third-party store: middle ground.

**Recommended default:** Sideload personal build for now. Provisional — phase 2 anyway.

---

## Q5: Always-on home device?

**Context:** If the owner has an always-on device (home server, Raspberry Pi, old PC), mautrix-meta and Update Guardian can run there 24/7. Otherwise everything runs on the Windows PC.

**Options:**
- **Yes:** Host bridge + updater on the home device; PC is the UI/voice client.
- **No / unknown (recommended default):** Everything runs on the Windows PC. Bridge runs only when PC is on.
- Later: add home device when available.

**Recommended default:** No dedicated home device yet; PC runs everything. Provisional.

---

## Q6: UI shell framework?

**Context:** Tauri (Rust + web UI) vs Electron vs WinUI 3.

**Options:**
- **Tauri (recommended default):** Smaller binary, Rust backend, web frontend.
- Electron: familiar web stack, larger binary.
- WinUI 3: native Windows, more platform-specific work.

**Recommended default:** Tauri. Provisional — UI is phase 1-2, not blocking the walking skeleton.

---

## Q7: Voice engine selection (if defaults prove inadequate)?

**Context:** openWakeWord/faster-whisper/Piper are the defaults. If accuracy/quality is insufficient on the owner's hardware, alternatives exist.

**Options:**
- Porcupine (wake word), Google Cloud STT Chirp (STT), Kokoro/Cloud TTS (TTS).
- Keep defaults unless spike results show problems.

**Recommended default:** Keep defaults; revisit after spike S2/S3 results.

---

**How to answer:** Reply with the question IDs and your chosen option (e.g. "Q1: hybrid, Q3: yes-spare"). Unanswered questions stay provisional and I proceed with the defaults above.
