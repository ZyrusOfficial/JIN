# JARVIS Project Status

**Phase:** 0 — Foundations and spikes (COMPLETE), entering Phase 0.5 — Domain layer  
**Branch:** `arena/00127883-jin`  
**Date:** 2026-11-20  
**Last updated:** 2026-11-20

## What is done

### Repository skeleton
- Python 3.12 package (`pyproject.toml`, `Makefile`, CI workflow, pre-commit config)
- `.gitignore` excluding cache, secrets, spike results
- GitHub Actions CI (Windows) running `make check`
- `make check` runs: lint, type-check, contract/logic/property/security/simulation tests
- `make check-fast` runs fast subset (<60s)
- No `|| true` masking — failures properly fail the build

### Domain layer (14 ports + real implementations)
- **Port interfaces** (`jarvis/ports/`): 14 Protocol-based ports (Clock, PolicyGate, SecretsBroker, AuditLog, MemoryStore, WakeWordSource, SpeechToText, TextToSpeech, VoiceActivityDetector, EchoCanceller, MessageSource, CalendarProvider, NewsSource, NotificationSource, DesktopControl)
- **Real policy gate** (`jarvis/domain/policy_gate.py`): T0-T3 trust tiers, standing rules, approvals, expiry, deterministic allow/ask/deny
- **Proactive engine** (`jarvis/domain/proactive_engine.py`): State machine (Idle→Scoring→ContextCheck→Queued→Speaking→Preempted→Suppressed→Delivered), importance scoring, context signals, rate limiting (6/hr), preemption
- **Importance scorer** (`jarvis/domain/importance_scorer.py`): Configurable weights (source rule, content classification, recency, learned behavior, hint), deterministic content classification
- **Speech queue** (`jarvis/domain/speech_queue.py`): Priority queue (L3>L2>L1), FIFO within level, chunk checkpoints, preemption, barge-in/kill switch
- **Decision table** (`jarvis/domain/decision_table.py`): 18 data-driven rows covering all importance × context × rate-limit combinations
- **Event bus** (`jarvis/domain/event_bus.py`): Pub/sub backbone with typed subscriptions
- **Event envelope** (`jarvis/domain/events.py`): Versioned envelope matching the brief spec

### Fakes (14 implementations)
Every port has a fake implementation for tests and the walking skeleton.

### Tests (122 passing)
| Category | Count | Status |
|---|---|---|
| Contract (ports + fakes + import rules) | 22 | ✅ Pass |
| Logic-flow (decision table, policy gate, speech queue, rate limits) | 28 | ✅ Pass |
| Property (Hypothesis invariants, parser fuzzing) | 7 | ✅ Pass |
| Security (19 prompt-injection cases, secret leak checks) | 47 | ✅ Pass |
| Simulation (day-in-the-life scenarios) | 6 | ✅ Pass |
| Architecture (import rules) | included in contract | ✅ Pass |
| **Total** | **122** | ✅ All pass |

### Static checks
- Ruff lint: clean
- Ruff format: clean
- MyPy strict: clean (44 files)

### Walking skeleton
- Fake wake word → STT → LLM → TTS + popup → audit log
- End-to-end cycle verified under `make run-skeleton`

### Docs (7 files)
- ARCHITECTURE.md, DECISIONS.md (ADR-001–009), QUESTIONS.md (7 questions), RESEARCH.md (12 section-14 questions), RUNBOOK.md, STATUS.md, TEST_STRATEGY.md

### Owner-spike kits (6 kits)
S1–S6 each with README, script, and JSON result template

## What works

- `make check` — all 122 tests pass, lint clean, types clean
- `make check-fast` — fast subset passes
- `make run-skeleton` — end-to-end fake pipeline works
- Policy gate: T0 auto-allow, T1/T2 ask, T3 deny, standing rules, expiry
- Proactive engine: all 18 decision table rows produce correct decisions
- Speech queue: priority ordering, preemption, barge-in, checkpoints
- Security: 19 prompt-injection patterns never trigger T2/T3, no secret leakage
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

## Open questions with defaults

See docs/QUESTIONS.md. All 7 are provisional; none block progress.

## What the owner should run next on their PC

1. Install Python 3.12+, clone repo, `pip install -e ".[dev]"`
2. Run `make check` — verify all gates pass
3. Run `make run-skeleton` — see the walking skeleton
4. Run Spike S1 (Windows notification listener)
5. Run Spike S2 (Audio loop, VAD, echo, latency)
6. Run Spike S3 (Taglish STT word-error rate)

## Unverified

All Windows/Android/third-party behaviors pending owner-run spikes S1–S6.

---

## Next: Major Improvement Plan

See `docs/PLAN.md` for the comprehensive roadmap.
