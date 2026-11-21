# JARVIS Project Status

**Phase:** 0 (COMPLETE), 0.5 (COMPLETE), 1 (COMPLETE), 2 (COMPLETE), 3-6 (DOMAIN LAYER COMPLETE), 7-8 (PLANNED)
**Branch:** `arena/43c1a44b-jin`
**Date:** 2026-11-20
**Last updated:** 2026-11-20

## What is done

### Repository skeleton
- Python 3.12 package (`pyproject.toml`, `Makefile`, CI workflow)
- `.gitignore` excluding cache, secrets, spike results
- GitHub Actions CI (Windows) running `make check`
- `make check` runs: lint, type-check, contract/logic/property/security/simulation/mutation tests
- `make check-fast` runs fast subset (<60s)
- No `|| true` masking — failures properly fail the build

### Domain layer (15 ports + real implementations)
- **Port interfaces** (`jarvis/ports/`): 15 Protocol-based ports (Clock, PolicyGate, SecretsBroker, AuditLog, MemoryStore, WakeWordSource, SpeechToText, TextToSpeech, VoiceActivityDetector, EchoCanceller, MessageSource, CalendarProvider, NewsSource, NotificationSource, DesktopControl, PopupPort)
- **Real policy gate** (`jarvis/domain/policy_gate.py`): T0-T3 trust tiers, standing rules, approvals, expiry, deterministic allow/ask/deny
- **Proactive engine** (`jarvis/domain/proactive_engine.py`): State machine (Idle→Scoring→ContextCheck→Queued→Speaking→Preempted→Suppressed→Delivered), importance scoring, context signals, rate limiting (6/hr), preemption
- **Importance scorer** (`jarvis/domain/importance_scorer.py`): Configurable weights, deterministic content classification
- **Speech queue** (`jarvis/domain/speech_queue.py`): Priority queue (L3>L2>L1), FIFO within level, chunk checkpoints, preemption, barge-in/kill switch
- **Decision table** (`jarvis/domain/decision_table.py`): Data-driven rows covering importance × context × rate-limit combinations
- **Event bus** (`jarvis/domain/event_bus.py`): Pub/sub backbone with typed subscriptions
- **Event envelope** (`jarvis/domain/events.py`): Versioned envelope matching the brief spec
- **Approval models** (`jarvis/domain/approval/models.py`): StandingRule, ApprovalRecord, ApprovalScope
- **Cooldown manager** (`jarvis/domain/cooldown/manager.py`): Timed cooldowns per key
- **Rate limiter** (`jarvis/domain/rate_limiter/limiter.py`): Max 6 utterances/hour
- **Learning loop** (`jarvis/domain/learning/loop.py`): OwnerAction enum, score adjustment
- **Coalescing engine** (`jarvis/domain/coalescing/engine.py`): Groups same-thread events
- **Quiet hours config** (`jarvis/domain/quiet_hours/config.py`): Time-window suppression
- **LLM router** (`jarvis/domain/llm_router.py`): Cloud + local Ollama fallback
- **Update Guardian** (`jarvis/domain/update_guardian.py`): watch→verified→staged→tested→applied→healthy|rolled_back|skipped
- **Capability Forge** (`jarvis/domain/capability_forge.py`): Gap discovery→source→author→review→approve→install→activate→revoke with hard guardrails

### Phase 1: Voice loop adapters (real + fake)
- STT: faster-whisper adapter + fake
- TTS: Piper adapter + Kokoro adapter + fake
- Wake word: openWakeWord adapter + Porcupine adapter + fake
- VAD: Silero VAD adapter + fake
- Echo canceller: WebRTC AEC adapter + fake
- All adapters have optional dependency imports with runtime availability checks

### Phase 2: Popups + proactive engine UI shell
- **Popup port** (`jarvis/ports/popup.py`): PopupCard, PopupResponse, PopupPort protocol
- **Fake popup** (`jarvis/adapters/popup/fake_popup.py`): Records shown cards for tests
- **Textual UI shell** (`jarvis/ui_shell.py`): Terminal UI with popup cards, kill switch button, mic indicator, status panel
- **Textual popup port** (`jarvis/adapters/popup/textual_popup.py`): Bridges PopupPort to Textual UI

### Phase 3: Calendar + news adapters
- Calendar: fake, Google Calendar, Microsoft Graph, ICS offline
- News: fake, RSS/Atom, PAGASA CAP alert feed

### Phase 4: Messaging + Update Guardian
- Message source: fake, Windows notification listener, mautrix-meta bridge (spare-account-only)
- Update Guardian domain state machine with T2 confirmation, weekly auto-update limits, health checks, rollback

### Phase 5: Desktop control adapters
- Desktop control: fake, Windows UI Automation (pywinauto)

### Phase 6: Capability Forge domain
- Forge pipeline with hard guardrails: no self-tier escalation, no policy gate editing, no core code modification, static review blocks dangerous calls/obfuscation/undeclared access, code integrity verification

### Fakes (15 implementations)
Every port has a fake implementation for tests and the walking skeleton.

### Tests (164 passing)
| Category | Count | Status |
|---|---|---|
| Contract (ports + fakes + import rules + popup) | 26 | ✅ Pass |
| Logic-flow (decision table, policy gate, speech queue, rate limits, Update Guardian, Capability Forge) | 90 | ✅ Pass |
| Property (Hypothesis invariants, parser fuzzing) | 7 | ✅ Pass |
| Security (23 prompt-injection cases, secret leak checks) | 47 | ✅ Pass |
| Simulation (day-in-the-life scenarios) | 6 | ✅ Pass |
| Mutation (policy gate, Update Guardian, Capability Forge) | 20 | ✅ Pass |
| **Total** | **196** | ✅ All pass |

### Static checks
- Ruff lint: clean
- Ruff format: clean
- MyPy strict: clean (all files)

### Walking skeleton
- Fake wake word → STT → LLM → TTS + popup → audit log
- End-to-end cycle verified under `make run-skeleton`

### Docs (7 files)
- ARCHITECTURE.md, DECISIONS.md (ADR-001–009), QUESTIONS.md (7 questions), RESEARCH.md (12 section-14 questions), RUNBOOK.md, STATUS.md, TEST_STRATEGY.md

### Owner-spike kits (6 kits)
S1–S6 each with README, script, and JSON result template

## What works

- `make check` — all 196 tests pass, lint clean, types clean, mutation tests pass
- `make check-fast` — fast subset passes
- `make run-skeleton` — end-to-end fake pipeline works
- Policy gate: T0 auto-allow, T1/T2 ask, T3 deny, standing rules, expiry
- Proactive engine: all decision table rows produce correct decisions
- Speech queue: priority ordering, preemption, barge-in, checkpoints
- Update Guardian: full state machine with T2 confirmation, weekly limits, rollback
- Capability Forge: forge pipeline with hard guardrails, code integrity verification
- Security: 23 prompt-injection patterns never trigger T2/T3, no secret leakage
- Simulation: morning briefing, typhoon alert at 2AM, group chat during call, rate limiting, learned behavior, barge-in

## Deviations from the brief

Documented in DECISIONS.md (ADR-001 through ADR-009). No non-negotiable (section 3.3) weakened.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Messenger bridge detection risk | High | Spare-account trial (S6), notification-only fallback |
| Taglish STT accuracy | High | Spike S3 measures WER; cloud fallback available |
| Windows notification listener | Medium | Spike S1 confirms unpackaged access |
| No real hardware/accounts | High | All platform code behind adapters with contract tests |
| Android companion not built | Medium | Kotlin code structure documented; needs Android SDK |

## What the owner should run next on their PC

1. Install Python 3.12+, clone repo, `pip install -e ".[dev]"`
2. Run `make check` — verify all gates pass
3. Run `make run-skeleton` — see the walking skeleton
4. Run `PYTHONPATH=src/python python -m jarvis.ui_shell` — see the Textual UI shell
5. Run Spike S1 (Windows notification listener)
6. Run Spike S2 (Audio loop, VAD, echo, latency)
7. Run Spike S3 (Taglish STT word-error rate)

## Unverified

All Windows/Android/third-party behaviors pending owner-run spikes S1–S6.
Android companion (Phase 7) requires Android SDK and Kotlin toolchain — not built in this sandbox.

## Remaining phases

| Phase | Status | Notes |
|---|---|---|
| Phase 7: Android companion | NOT STARTED | Requires Android SDK/Kotlin; documented in PLAN.md |
| Phase 8: Hardening | PARTIAL | Mutation tests added; security scans need trufflehog/safety installed |
