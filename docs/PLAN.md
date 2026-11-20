# JARVIS Comprehensive Improvement Plan

This plan covers all major features and improvements beyond Phase 0. It is organized by milestone with dependencies and estimated effort. "Do not hold back" — this is the full vision.

## Current state: Phase 0 complete

- 14 port interfaces, 14 fakes, real policy gate, proactive engine, speech queue, decision table, event bus
- 122 tests passing, lint/format/type clean
- Walking skeleton (fake everything) end-to-end
- 6 owner-spike kits, 7 docs, CI config

---

## Phase 0.5: Domain layer hardening (immediate, this week)

### 0.5.1: Complete the remaining domain models
- `jarvis/domain/approval.py` — Approval and standing rule models
- `jarvis/domain/rate_limiter.py` — Extract rate limiter from proactive engine
- `jarvis/domain/cooldown.py` — Cooldown management for proactive items

### 0.5.2: Add missing domain logic
- **Learning loop**: Track owner actions (listen, reply, snooze, dismiss) and adjust per-contact/source scores
- **Coalescing**: Merge related events (same thread, same topic) into single proactive item
- **Quiet hours configuration**: Configurable quiet hours window with weekend/weekday variants

### 0.5.3: Test coverage targets
- 100% branch coverage on policy gate and proactive engine
- Mutation testing on policy gate (mutmut configured)
- Property tests for queue invariants (fix the Hypothesis timeout issue)

### Effort: 1-2 days

---

## Phase 1: Voice loop (real adapters)

### 1.1: STT adapter (faster-whisper)
- `jarvis/adapters/stt/faster_whisper.py` — faster-whisper implementation
- Model download and caching
- Taglish support via dominant-language setting
- Configurable latency assertions

### 1.2: TTS adapter (Piper)
- `jarvis/adapters/tts/piper.py` — Piper TTS implementation
- Streaming chunk output with checkpoints
- Voice selection (English, Filipino)
- Kokoro as higher-quality alternative

### 1.3: Wake word adapter (openWakeWord)
- `jarvis/adapters/wake_word/openwakeword.py` — openWakeWord implementation
- Custom "Hey Jarvis" model
- Porcupine as licensed alternative

### 1.4: VAD adapter (Silero)
- `jarvis/adapters/vad/silero.py` — Silero VAD implementation
- Speech/silence segmentation for end-of-speech detection

### 1.5: Echo canceller (WebRTC AEC)
- `jarvis/adapters/echo_canceller/webrtc.py` — WebRTC AEC implementation
- Half-duplex fallback when AEC unavailable

### 1.6: Real LLM integration
- `jarvis/domain/llm_router.py` — LLM provider abstraction (cloud + local Ollama)
- Streaming response with sentence chunking
- Tool calling interface

### Effort: 1-2 weeks

---

## Phase 2: Popups and proactive engine (UI shell)

### 2.1: UI shell (Tauri)
- Always-on-top popup card (Read, Reply, Snooze, Dismiss)
- System tray with settings and kill switch
- WebSocket connection to core agent
- Kill switch hotkey (Ctrl+Alt+K)

### 2.2: Proactive engine wiring
- Connect event bus → proactive engine → speech queue → TTS + popup
- Three interrupt levels (L3/L2/L1)
- Context signals from Windows bridge (fullscreen, call, DND, headphones)
- Quiet hours and rate limiting

### 2.3: Morning briefing and evening wrap-up
- Scheduled events via virtual clock (real clock in production)
- Calendar events + news digest + weather

### Effort: 1-2 weeks

---

## Phase 3: Calendar and news

### 3.1: Calendar provider adapters
- `jarvis/adapters/calendar/google_calendar.py` — Google Calendar API
- `jarvis/adapters/calendar/microsoft_graph.py` — Microsoft Graph (Outlook)
- `jarvis/adapters/calendar/ics.py` — Offline ICS fallback
- Natural-language create/move/delete with conflict detection
- Read-back-before-save (T2 confirmation)

### 3.2: News source adapters
- `jarvis/adapters/news/pagasa_cap.py` — PAGASA CAP alert feed (official)
- `jarvis/adapters/news/phivolcs_scrape.py` — PHIVOLCS bulletin scraping (fallback)
- `jarvis/adapters/news/rss.py` — Generic RSS/Atom feeds
- Dedupe (embeddings), clustering, breaking-news corroboration rule

### 3.3: Time zone handling
- UTC storage with IANA zone (Asia/Manila default)
- DST handling
- Read-back resolved date/time before saving

### Effort: 1-2 weeks

---

## Phase 4: Messaging and Update Guardian

### 4.1: Message source adapters
- `jarvis/adapters/messages/notification.py` — Windows notification capture (backend A)
- `jarvis/adapters/messages/mautrix_meta.py` — mautrix-meta bridge (backend B, opt-in)
- `jarvis/adapters/messages/passive_reader.py` — facebook.com/messages reader (backend C)
- Draft-and-confirm flow (T2 confirmation for every outgoing message)
- Notification gap handling (partial flags, thread reconstruction)

### 4.2: SMS adapter
- Windows Phone Link notification capture (read-oriented)
- Android companion SMS path (phase 2)

### 4.3: Update Guardian
- `jarvis/domain/update_guardian.py` — State machine: watch→verified→staged→tested→applied→healthy|rolled-back|skipped
- Staged updates with health checks and auto-rollback
- Never auto-login; no new permissions without approval
- Max one auto-update per component per week

### Effort: 2-3 weeks

---

## Phase 5: Desktop control

### 5.1: Desktop control adapter
- `jarvis/adapters/desktop/windows_ui_automation.py` — UI Automation (structured)
- `jarvis/adapters/desktop/vision_fallback.py` — Vision-based clicking (fallback)
- `jarvis/adapters/desktop/raw_input.py` — Raw input injection (last resort)
- App launch/close, window management, files, clipboard, system controls
- T2 confirmation for writes and system changes

### 5.2: Screen awareness
- On-demand only (never continuous by default)
- Screenshots, OCR, dictation anywhere
- Browser control, media control, macros and routines

### Effort: 1-2 weeks

---

## Phase 6: Capability Forge (self-extension)

### 6.1: MCP client
- MCP stdio transport for local servers
- MCP Streamable HTTP for remote servers
- MCP Registry API discovery (registry.modelcontextprotocol.io)
- server/discover method support (spec 2026-07-28)

### 6.2: Forge pipeline
- Gap detection → source existing → author new
- Sandboxed code generation (restricted job object, no network by default)
- Static review (dangerous calls, undeclared access, obfuscation)
- Permission diff display
- Install into versioned local git repo with manifest hash
- Rollback and monitoring

### 6.3: Hard guardrails
- Capability cannot raise its tier, edit policy gate, or change core code
- Secrets injected by broker at call time (scoped per capability)
- Per-capability network allowlist enforced outside capability code
- Instructions in skills are data, never commands
- Third-party capabilities never update silently

### Effort: 3-4 weeks (highest risk feature)

---

## Phase 7: Android companion (phase 2)

### 7.1: Kotlin Android app
- Foreground service for always-on operation
- Notification listener with MessagingStyle extras
- SMS (Assistant role, default SMS app, or sideload)
- Wake word on-device
- Encrypted sync with PC
- Commute mode, share-sheet target

### 7.2: Play Store vs sideload
- Sideload personal build (no Play restrictions)
- Assistant role registration for SMS permissions

### Effort: 3-4 weeks

---

## Phase 8: Hardening

### 8.1: Security
- Expanded prompt-injection corpus
- Mutation testing thresholds met (policy gate, updater)
- Soak tests for memory leaks
- Crash recovery testing
- Audit log review

### 8.2: Update Guardian extension
- All allowlisted components covered
- Model files manual benchmark before update

### 8.3: Performance
- CPU, memory, battery budgets for always-on parts
- Latency budget assertions (STT <500ms, first LLM token <800ms, first TTS <300ms, end-to-end <2s)

### Effort: 2-3 weeks

---

## Infrastructure additions needed

### CI/CD enhancements
- Secret scanning (trufflehog) — `make secrets-scan`
- Dependency vulnerability scanning (safety) — `make dep-scan`
- Mutation testing (mutmut) — `make test-mutation`
- Windows and Android CI runners

### Packaging
- Windows installer (Inno Setup or MSIX)
- Python wheel distribution
- C# Windows bridge NuGet package
- Android APK/AAB

### Docker
- Core agent container
- mautrix-meta container (for bridge spike S6)
- Update Guardian container

### Monitoring
- Structured logging with correlation IDs
- Metrics (latency, error rates, queue depths)
- Health check endpoints

---

## Estimated total effort

| Phase | Effort | Dependencies |
|---|---|---|
| 0.5 Domain hardening | 1-2 days | Phase 0 |
| 1 Voice loop | 1-2 weeks | 0.5 |
| 2 Popups + proactive | 1-2 weeks | 1 |
| 3 Calendar + news | 1-2 weeks | 2 |
| 4 Messaging + updater | 2-3 weeks | 3 |
| 5 Desktop control | 1-2 weeks | 4 |
| 6 Capability Forge | 3-4 weeks | 5 |
| 7 Android companion | 3-4 weeks | 6 |
| 8 Hardening | 2-3 weeks | 7 |
| **Total** | **~16-24 weeks** | |

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

## Immediate next steps for the owner

1. Run `make check` on their PC
2. Run Spike S1 (Windows notification listener)
3. Run Spike S2 (Audio loop)
4. Run Spike S3 (Taglish STT)
5. Answer the 7 questions in docs/QUESTIONS.md
6. Provide GPU/RAM specs for cloud-vs-local decision
