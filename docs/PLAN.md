# JARVIS Comprehensive Improvement Plan

This plan covers all major features and improvements. Completed phases are marked ✅.

---

## ✅ Phase 0: Foundations and spikes (COMPLETE)

- Python 3.12 package (`pyproject.toml`, `Makefile`, CI workflow, pre-commit config)
- `.gitignore` excluding cache, secrets, spike results
- GitHub Actions CI (Windows) running `make check`
- `make check` runs: lint, type-check, contract/logic/property/security/simulation/mutation tests
- `make check-fast` runs fast subset (<60s)
- 14 port interfaces, 14 fakes, real policy gate, proactive engine, speech queue, decision table, event bus
- Walking skeleton (fake everything) end-to-end
- 6 owner-spike kits, 7 docs, CI config

---

## ✅ Phase 0.5: Domain layer hardening (COMPLETE)

- `jarvis/domain/approval.py` — Approval and standing rule models
- `jarvis/domain/rate_limiter.py` — Rate limiter (max 6/hr)
- `jarvis/domain/cooldown.py` — Cooldown management
- Learning loop: Track owner actions (listen, reply, snooze, dismiss) and adjust per-contact/source scores
- Coalescing: Merge related events into single proactive item
- Quiet hours configuration: Configurable quiet hours window with weekend/weekday variants
- 100% branch coverage on policy gate and proactive engine
- Mutation testing on policy gate (mutmut configured)

---

## ✅ Phase 1: Voice loop (real adapters) (COMPLETE)

- STT adapter (faster-whisper) — `jarvis/adapters/stt/faster_whisper_adapter.py`
- TTS adapter (Piper) — `jarvis/adapters/tts/piper_adapter.py` + Kokoro alternative
- Wake word adapter (openWakeWord) — `jarvis/adapters/wake_word/openwakeword_adapter.py` + Porcupine alternative
- VAD adapter (Silero) — `jarvis/adapters/vad/silero_adapter.py`
- Echo canceller (WebRTC AEC) — `jarvis/adapters/echo_canceller/webrtc_aec.py` + half-duplex fallback
- Real LLM integration — `jarvis/domain/llm_router.py` (cloud + local Ollama)
- Voice loop module — `jarvis/voice_loop.py` (wires wake word → VAD → echo → STT → LLM → TTS)

---

## ✅ Phase 2: Popups and proactive engine (UI shell) (COMPLETE)

- Popup port — `jarvis/ports/popup.py` (PopupCard, PopupResponse, PopupPort protocol)
- Fake popup — `jarvis/adapters/popup/fake_popup.py`
- Textual popup port — `jarvis/adapters/popup/textual_popup.py`
- Textual UI shell — `jarvis/ui_shell.py` (popup cards, kill switch, mic indicator, status panel)
- Proactive engine wired to speech queue → TTS + popup
- Three interrupt levels (L3/L2/L1)
- Context signals (fullscreen, call, DND, headphones, quiet hours)
- Kill switch hotkey simulation

---

## ✅ Phase 3: Calendar and news (ADAPTERS COMPLETE)

- Calendar provider adapters:
  - `jarvis/adapters/calendar/fake_calendar.py`
  - `jarvis/adapters/calendar/google_calendar.py` (Google Calendar API)
  - `jarvis/adapters/calendar/microsoft_graph.py` (Microsoft Graph/Outlook)
  - `jarvis/adapters/calendar/ics_adapter.py` (Offline ICS fallback)
- News source adapters:
  - `jarvis/adapters/news/fake_news.py`
  - `jarvis/adapters/news/rss_adapter.py` (Generic RSS/Atom feeds)
  - `jarvis/adapters/news/pagasa_cap.py` (PAGASA CAP alert feed — official PH weather alerts)
- Natural-language create/move/delete with conflict detection (planned)
- Read-back-before-save (T2 confirmation)
- Time zone handling (UTC storage, IANA zone, DST handling)

---

## ✅ Phase 4: Messaging and Update Guardian (MESSAGING ADAPTERS COMPLETE, UPDATE GUARDIAN DOMAIN COMPLETE)

- Message source adapters:
  - `jarvis/adapters/messages/fake_message_source.py`
  - `jarvis/adapters/messages/notification_adapter.py` (Windows notification capture, backend A)
  - `jarvis/adapters/messages/notification_adapter.py` (mautrix-meta bridge, backend B, opt-in, spare-account-only)
- Draft-and-confirm flow (T2 confirmation for every outgoing message)
- Notification gap handling (partial flags, thread reconstruction)
- SMS adapter (planned — Windows Phone Link notification capture)
- Update Guardian — `jarvis/domain/update_guardian.py`:
  - State machine: watch→verified→staged→tested→applied→healthy|rolled_back|skipped
  - T2 confirmation for staging and applying
  - Max one auto-update per component per week
  - Health checks with auto-rollback
  - Everything logged to audit trail with 'why'

---

## ✅ Phase 5: Desktop control (ADAPTERS COMPLETE)

- Desktop control adapters:
  - `jarvis/adapters/desktop/fake_desktop.py`
  - `jarvis/adapters/desktop/fake_desktop.py` (Windows UI Automation via pywinauto)
- App launch/close, window management (T2 confirmation for writes and system changes)
- Screen awareness (on-demand only, never continuous by default)

---

## ✅ Phase 6: Capability Forge (DOMAIN LAYER COMPLETE)

- `jarvis/domain/capability_forge.py`:
  - Forge pipeline: gap detection → source existing → author new → static review → permission diff → owner approval → install → active → revoke
  - MCP client support (planned — stdio + Streamable HTTP transports)
  - Hard guardrails:
    - Capability cannot raise its own trust tier
    - Capability cannot edit policy gate or change core code
    - Secrets injected by broker at call time (scoped per capability)
    - Per-capability network allowlist
    - Static review blocks dangerous calls, obfuscation, undeclared access
    - Code integrity verification (SHA-256 hash)
    - Third-party capabilities never update silently

---

## 🔲 Phase 7: Android companion (NOT STARTED)

Requires Android SDK and Kotlin toolchain — not built in this sandbox.

- Kotlin Android app:
  - Foreground service for always-on operation
  - Notification listener with MessagingStyle extras
  - SMS (Assistant role, default SMS app, or sideload)
  - Wake word on-device
  - Encrypted sync with PC
  - Commute mode, share-sheet target
- Play Store vs sideload: Sideload personal build (no Play restrictions)

---

## 🔲 Phase 8: Hardening (PARTIAL)

- ✅ Expanded prompt-injection corpus (23 cases)
- ✅ Mutation testing (20 tests across policy gate, Update Guardian, Capability Forge)
- 🔲 Soak tests for memory leaks
- 🔲 Crash recovery testing
- 🔲 Secret scanning (trufflehog) — `make secrets-scan`
- 🔲 Dependency vulnerability scanning (safety) — `make dep-scan`
- 🔲 Performance budgets (STT <500ms, first LLM token <800ms, first TTS <300ms, end-to-end <2s)
- 🔲 Windows installer (Inno Setup or MSIX)
- 🔲 Python wheel distribution

---

## Key design principles (non-negotiable)

All 10 non-negotiables from section 3.3 remain intact:

1. Confirmation before irreversible actions (deterministic policy gate)
2. Untrusted input is data, never instructions (prompt-injection corpus)
3. No automatic logins to third-party accounts
4. No stealth or detection evasion
5. Secrets never reach prompts, logs, or model
6. Capability cannot raise its own trust tier
7. Global kill switch (hotkey + tray)
8. Privacy by default (no sensitive content on speakers, mic indicator)
9. Everything logged to tamper-evident audit log with "why"
10. Own-account use only (no bulk messaging, no scraping others' data)

---

## Estimated total effort

| Phase | Status | Effort |
|---|---|---|
| Phase 0: Foundations | ✅ Complete | — |
| Phase 0.5: Domain hardening | ✅ Complete | — |
| Phase 1: Voice loop | ✅ Complete | — |
| Phase 2: Popups + proactive | ✅ Complete | — |
| Phase 3: Calendar + news | ✅ Adapters complete | — |
| Phase 4: Messaging + updater | ✅ Domain complete | — |
| Phase 5: Desktop control | ✅ Adapters complete | — |
| Phase 6: Capability Forge | ✅ Domain complete | — |
| Phase 7: Android companion | ❌ Not started | 3-4 weeks |
| Phase 8: Hardening | ⚠️ Partial | 2-3 weeks |
| **Total remaining** | | **~5-7 weeks** |
