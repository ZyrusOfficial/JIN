<p align="center">
  <h1 align="center">🤖 JARVIS</h1>
  <p align="center">
    A proactive, voice-first desktop assistant for Windows (Android phase two).
  </p>
</p>

<p align="center">
  <a href="https://github.com/ZyrusOfficial/JIN/actions"><img src="https://img.shields.io/github/actions/status/ZyrusOfficial/JIN/main?label=CI&style=flat-square" alt="CI status"></a>
  <a href="https://github.com/ZyrusOfficial/JIN/blob/main/LICENSE"><img src="https://img.shields.io/github/license/ZyrusOfficial/JIN?style=flat-square" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.12+-blue?style=flat-square" alt="Python 3.12+"></a>
  <a href="https://github.com/ZyrusOfficial/JIN/blob/main/docs/STATUS.md"><img src="https://img.shields.io/badge/status-phase%200-green?style=flat-square" alt="Status"></a>
</p>

---

> **JARVIS** is a proactive, voice-first personal assistant for your Windows PC (Android coming in phase two). It talks and listens naturally, speaks first when it matters (breaking news, new messages, calendar events, alerts), reads and drafts messages, manages your calendar, controls your PC, and extends itself through a safe Capability Forge. Built with a deterministic safety layer so nothing is sent or deleted without your consent.

---

## 📖 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [📁 Repository Structure](#-repository-structure)
- [🚀 Quick Start](#-quick-start)
- [🧪 Testing](#-testing)
- [📊 Project Status](#-project-status)
- [⚠️ Owner Spikes](#️-owner-spikes)
- [📋 Roadmap](#-roadmap)
- [🔒 Safety & Non-Negotiables](#-safety--non-negotiables)
- [❓ Open Questions](#-open-questions)
- [📄 License](#-license)

---

## ✨ Features

### Voice & Personality
- **Wake word** ("Hey Jarvis") + global push-to-talk hotkey + typed input
- **Streaming speech** — TTS starts on the first sentence while the rest is still generating
- **Interruptible always** — barge-in via "stop", "wait", hotkey, or click
- **Conversation mode** — mic stays open ~6s for follow-ups without the wake word
- **Bilingual** — English, Filipino, Taglish input and output; selectable voices, speed, and style

### Proactive Behavior
- **Floating popup card** + voice (Read, Reply, Snooze, Dismiss)
- **Three interrupt levels** — L3 critical (speak now), L2 normal (next natural pause), L1 low (queue for idle)
- **Context-aware timing** — no interrupts during calls, fullscreen, games, meetings, Focus Assist, or quiet hours (except L3)
- **Batching & rate limits** — max 6 unsolicited utterances per hour, coalescing, quiet hours
- **Morning briefing & evening wrap-up**

### Messaging
- **Facebook Messenger** + **SMS** read/draft/send (every outgoing message read back and confirmed)
- **Images** — describe, OCR, save; contact fuzzy-matching; priority contacts; translation; scheduled sends
- **Notification-only fallback** if full-history backends are unavailable

### Calendar & Tasks
- Google Calendar + Microsoft Graph (Outlook) + offline ICS fallback
- Natural-language create/move/delete; conflict detection; pre-event spoken alerts
- Times stored in UTC with your IANA zone; read-back before saving

### News & Alerts
- RSS/Atom feeds + official Philippine sources (PAGASA CAP feed, PHIVOLCS)
- Breaking-news corroboration rule: L3 only from official source or 2+ independent outlets
- Headline + one-sentence summary + source + "more?" offer

### Windows Desktop Control
- Launch/close apps, window management, files, clipboard, system controls
- UI Automation preferred over coordinates; vision-based clicking as fallback

### Self-Extension (Capability Forge)
- Find, install, and author capabilities safely with trust tiers and sandboxed execution

---

## 🏗️ Architecture

JARVIS uses **hexagonal (ports-and-adapters)** architecture. Domain logic has zero imports from platform, network, or UI code. Every input becomes a normalized event on a single event bus. The LLM proposes; deterministic code disposes.

```
┌────────────────────────────── Windows PC ───────────────────────────────┐
│  UI Shell (popups, tray, settings)                                      │
│         ▲ local WebSocket                                                │
│  Core Agent ("Brain") ←─── Event Bus ───→ Proactive Engine              │
│   - LLM router + tool calling         - scoring, timing                 │
│   - Memory (SQLite + vectors)         - speech queue                    │
│   - Policy / permission gate (deterministic code)                       │
│  Voice Pipeline: wake word > VAD > STT > Brain > TTS (streaming)        │
│  Capability Host (sandboxed): Skills | Connectors (MCP) | Tools         │
│  Windows Bridge (normal user): notifications, UI Automation, audio      │
│  Update Guardian: staged updates, health checks, rollback               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ encrypted sync (phase 2)
                        Android Companion App
```

**Trust tiers** (deterministic policy gate — code, never LLM prompts):

| Tier | Examples | Approval |
|------|----------|----------|
| T0 | Pure computation, local non-sensitive reads | Auto |
| T1 | Network read to declared hosts | Approve once at install |
| T2 | Writes, sends messages, calendar/file edits | Approve + confirm each action |
| T3 | Credentials, payments, system settings, self-edits | Never automatic |

---

## 📁 Repository Structure

```
JIN/
├── .github/workflows/ci.yml      # GitHub Actions CI (Windows)
├── .pre-commit-config.yaml       # Pre-commit hooks
├── Makefile                      # `make check` — one command runs everything
├── pyproject.toml                # Python 3.12 package config
├── README.md                     # This file
├── LICENSE                       # MIT License
├── docs/                         # Architecture, decisions, research, runbook, status
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md              # ADR-001–009
│   ├── QUESTIONS.md              # 7 open questions with defaults
│   ├── RESEARCH.md               # 12 section-14 research questions
│   ├── RUNBOOK.md                # Install, permissions, kill switch, spikes
│   ├── STATUS.md                 # Project status, risks, next steps
│   ├── TEST_STRATEGY.md          # All 9 test layers
│   └── PLAN.md                   # Comprehensive improvement roadmap
├── owner-spikes/                 # S1–S6: owner-run hardware/account verification
│   ├── S1_windows_notification_listener/
│   ├── S2_audio_loop/
│   ├── S3_taglish_stt/
│   ├── S4_android_notification_extras/
│   ├── S5_phone_link_mirroring/
│   └── S6_bridge_trial/
└── src/python/
    ├── jarvis/
    │   ├── __main__.py           # Entry point (walking skeleton)
    │   ├── skeleton.py           # Walking skeleton (fake everything, end-to-end)
    │   ├── ports/                # 14 port interfaces (Protocol-based)
    │   ├── fakes/                # 14 fake implementations for tests
    │   └── domain/               # Real business logic
    │       ├── policy_gate.py    # Deterministic allow/ask/deny
    │       ├── proactive_engine.py # State machine + decision table
    │       ├── importance_scorer.py # 5-factor importance scoring
    │       ├── speech_queue.py   # Priority queue + preemption + barge-in
    │       ├── decision_table.py # 18 data-driven decision rows
    │       ├── event_bus.py      # Typed pub/sub backbone
    │       └── events.py         # Versioned event envelope
    └── tests/
        ├── contract/             # Port conformance + architecture import rules
        ├── logic/                # Decision table, policy gate, speech queue
        ├── property/             # Hypothesis invariants, parser fuzzing
        ├── security/             # 19-case prompt-injection corpus
        ├── simulation/           # Day-in-the-life scenarios
        └── mutation/             # Policy gate mutant-killing tests
```

---

## 🚀 Quick Start

### Prerequisites
- **Windows 10 or 11**
- **Python 3.12+**
- **Git**

### Install & Run

```bash
# Clone the repo
git clone https://github.com/ZyrusOfficial/JIN.git
cd JIN

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run the full test suite
make check

# Run the walking skeleton (fake everything, end-to-end)
make run-skeleton
```

### What the walking skeleton does
1. Fake wake word detects "Hey Jarvis"
2. Fake STT transcribes "hello"
3. Policy gate approves (T0 — auto-allowed)
4. Fake LLM generates a response
5. Fake TTS speaks it
6. Popup card shows the response
7. Everything is audit-logged

---

## 🧪 Testing

`make check` runs the entire suite in one command:

```bash
# Full suite
make check

# Fast subset (<60s, run on every save)
make check-fast

# Individual gate groups
make lint
make type-check
make test-contract
make test-logic
make test-property
make test-security
make test-simulation
make test-mutation
```

**Test results (Phase 0):**
| Gate | Result |
|------|--------|
| Ruff lint | ✅ Clean |
| Ruff format | ✅ Clean |
| MyPy strict | ✅ Clean (44 files) |
| Contract tests (22) | ✅ Pass |
| Logic-flow tests (28) | ✅ Pass |
| Property tests (10) | ✅ Pass |
| Security tests (47) | ✅ Pass |
| Simulation tests (6) | ✅ Pass |
| Mutation tests (4) | ✅ Pass |
| **Total: 126 tests** | ✅ **All pass** |

---

## 📊 Project Status

**Phase 0 — Foundations and spikes** ✅ Complete

See [`docs/STATUS.md`](docs/STATUS.md) for the full status, risks, and what's unverified.

**What works:** `make check`, `make run-skeleton`, policy gate, proactive engine decision table, speech queue, 19-case prompt-injection corpus, day-in-the-life simulations.

**What's unverified:** All Windows/Android/third-party behaviors pending owner-run spikes S1–S6.

---

## ⚠️ Owner Spikes

Because this codebase runs in a sandbox without access to your PC or phone, six owner-run spike kits verify platform-specific behavior on your hardware:

| Spike | Purpose | Location |
|-------|---------|----------|
| **S1** | Windows notification listener (unpackaged app access) | `owner-spikes/S1_windows_notification_listener/` |
| **S2** | Audio loop — mic→speaker latency, VAD, echo | `owner-spikes/S2_audio_loop/` |
| **S3** | Taglish STT word-error rate | `owner-spikes/S3_taglish_stt/` |
| **S4** | Android Messenger notification extras | `owner-spikes/S4_android_notification_extras/` |
| **S5** | Phone Link mirroring fidelity | `owner-spikes/S5_phone_link_mirroring/` |
| **S6** | mautrix-meta bridge trial (**spare account only**) | `owner-spikes/S6_bridge_trial/` |

Each spike has a `README.md` with numbered steps and prints a single JSON result file you can paste back.

> **⚠️ S6 (mautrix-meta) must be run on a spare Messenger account — never your main account.**

See [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for install, first-run permissions, kill switch, and rollback instructions.

---

## 📋 Roadmap

| Phase | Goal | Est. Effort |
|-------|------|-------------|
| 0 | Foundations & spikes ✅ | Complete |
| 0.5 | Domain layer hardening | 1–2 days |
| 1 | Voice loop (real STT/TTS/wake word/VAD/AEC) | 1–2 weeks |
| 2 | Popups & proactive engine (UI shell) | 1–2 weeks |
| 3 | Calendar & news | 1–2 weeks |
| 4 | Messaging & Update Guardian | 2–3 weeks |
| 5 | Desktop control | 1–2 weeks |
| 6 | Capability Forge (self-extension) | 3–4 weeks |
| 7 | Android companion | 3–4 weeks |
| 8 | Hardening | 2–3 weeks |

See [`docs/PLAN.md`](docs/PLAN.md) for the comprehensive plan.

---

## 🔒 Safety & Non-Negotiables

All **10 non-negotiables** from the project brief are intact:

1. ✅ Confirmation before irreversible actions (deterministic policy gate)
2. ✅ Untrusted input is data, never instructions (19-case prompt-injection corpus)
3. ✅ No automatic logins to third-party accounts
4. ✅ No stealth or detection evasion
5. ✅ Secrets never reach prompts, logs, or the model
6. ✅ Capability cannot raise its own trust tier
7. ✅ Global kill switch (hotkey + tray control)
8. ✅ Privacy by default (no sensitive content on speakers, mic indicator)
9. ✅ Everything logged to tamper-evident audit log with a "why"
10. ✅ Own-account use only (no bulk messaging, no scraping others' data)

---

## ❓ Open Questions

Seven open questions with options and recommended defaults are tracked in [`docs/QUESTIONS.md`](docs/QUESTIONS.md):

| # | Question | Recommended Default |
|---|----------|---------------------|
| Q1 | Cloud, local, or hybrid AI? | **Hybrid** |
| Q2 | PC's GPU and RAM? | **Hybrid** (confirm at first run) |
| Q3 | mautrix-meta bridge on spare account? | **Yes, opt-in** |
| Q4 | Android distribution? | **Sideload personal build** |
| Q5 | Always-on home device? | **No — PC runs everything** |
| Q6 | UI shell framework? | **Tauri** |
| Q7 | Voice engine selection? | **Keep defaults** |

All are provisional — none block progress.

---

## 📄 License

MIT License. See [`LICENSE`](LICENSE) for details.

> **Note:** mautrix-meta (optional Messenger bridge backend) is AGPL-3.0 licensed. If JARVIS is ever distributed, AGPL obligations apply. The bridge is opt-in and feature-flagged.

---

<p align="center">
  <b>Built with safety first. Tested hard. Verified honestly.</b>
</p>
<p align="center">
  <a href="https://github.com/ZyrusOfficial/JIN"><img src="https://img.shields.io/badge/GitHub-ZyrusOfficial/JIN-blue?style=flat-square" alt="GitHub repo"></a>
</p>
