# JARVIS Architecture

## Overview

JARVIS is a proactive, voice-first desktop assistant for Windows (phase 1), Android (phase 2). The design follows **hexagonal (ports-and-adapters)** architecture: domain logic has zero imports from platform, network, or UI code. Every input becomes a normalized event on a single event bus. The LLM proposes; deterministic code disposes.

## Process layout

| Process | Responsibility | Runs as |
|---|---|---|
| Core Agent (Python) | Brain: LLM router, tool calling, policy gate, memory, event bus, proactive engine | Normal user |
| UI Shell (Tauri/Electron) | Always-on-top popups, tray, settings, kill switch | Normal user |
| Windows Bridge (C#) | Notification listener, UI Automation, audio devices | Normal user (never admin) |
| Capability workers | Sandboxed skills/connectors/tools, started on demand | Restricted job object |
| Update Guardian | Staged updates, health checks, rollback | Windows scheduled task |

A crash anywhere must never kill the voice loop.

## Domain model (platform-agnostic)

### Event envelope (versioned)

```json
{
  "id": "evt_01",
  "source": "messenger|sms|calendar|news|system|user",
  "type": "message.received",
  "time": "2026-11-20T09:15:00+08:00",
  "payload": {},
  "importance_hint": 0.4,
  "sensitive": false,
  "dedupe_key": null,
  "thread_id": null,
  "envelope_version": "1"
}
```

### Ports (interfaces, implemented by adapters)

- `WakeWordSource` — detects "Hey Jarvis"
- `SpeechToText` — audio → text
- `TextToSpeech` — text → streaming audio
- `VoiceActivityDetector` — speech/silence segmentation
- `EchoCanceller` — remove Jarvis's own audio from mic input
- `MessageSource` (Messenger, SMS) — inbound/outbound messages
- `CalendarProvider` — calendar read/write
- `NewsSource` — RSS/Atom/CAP feeds
- `NotificationSource` — Windows notifications
- `DesktopControl` — launch apps, windows, files, system
- `Clock` — injectable virtual clock for tests
- `SecretsBroker` — injects credentials at call time
- `PolicyGate` — allow/ask/deny, deterministic code
- `AuditLog` — tamper-evident local log with "why"
- `MemoryStore` — SQLite + vectors, encrypted at rest

## Proactive engine (state machine)

Pipeline: **event → importance score → context check → delivery decision → speech queue.**

States: `Idle`, `Scoring`, `ContextCheck`, `Queued`, `Speaking`, `Preempted`, `Suppressed`, `Delivered`.

Interrupt levels:
- **L3 critical:** speak now, even over music
- **L2 normal:** next natural pause (no typing ~3s, end of media track)
- **L1 low:** queue for idle or briefing

Context signals (Windows): fullscreen/presentation, Focus Assist/DND, active call, foreground app, audio output device (headphones vs speakers), idle time, lock state.

Always-on rules: sensitive content not on speakers unless allowed; max 6 unsolicited utterances/hour; coalescing; quiet hours; global kill switch.

## Policy gate and trust tiers

| Tier | Examples | Approval |
|---|---|---|
| T0 | Pure computation, local non-sensitive reads | Auto after sandbox tests pass |
| T1 | Network read to declared hosts | Approve once at install |
| T2 | Writes, sends messages, calendar/file edits | Approve at install + confirm each action (unless standing rule) |
| T3 | Credentials, payments, system settings, security tools, self-edits | Never automatic; explicit + second confirmation |

Gate returns `allow / ask / deny` with reason; every decision audit-logged.

## Memory tiers

Working / episodic / semantic / profile. SQLite + embeddings, encrypted at rest (DPAPI/Credential Manager). "Forget this" removes fact and derived data. Raw message retention default 14 days, configurable.

## Self-extension (Capability Forge)

Skills / connectors (MCP) / tools / routines. Manifest-declared trust tier and permissions. Sandboxed authoring and install. Tier can never self-escalate. Secrets injected by broker at call time. Network allowlist enforced outside capability code.

## Update Guardian

State machine: `watch → verified → staged → tested → applied → healthy | rolled-back | skipped`. Staged, health-checked, auto-rollback. Never auto-login. No new permissions without approval. Max one auto-update per component per week (security fix or broken component fast path excepted).

## Deviations from the brief

1. **Windows bridge language:** Brief suggested C# (.NET 8). Kept — confirmed by research that `UserNotificationListener` works unpackaged from a Win32 app.
2. **UI shell:** Brief suggested Tauri. Kept as default but noted Electron/WinUI 3 as alternatives.
3. **Wake word:** Brief mentioned openWakeWord or Porcupine. Default is openWakeWord (Apache 2.0, no per-device fee) with Porcupine as optional higher-accuracy alternative.
4. **TTS:** Brief suggested Piper/Kokoro or cloud. Default is Piper (fast, CPU) with Kokoro as quality alternative; cloud neural TTS configurable.
5. **STT:** Brief suggested faster-whisper or cloud. Default is faster-whisper (Taglish via dominant-language code-switching); Google Cloud STT Chirp as cloud alternative for Filipino.
6. **Process layout:** Brief suggested one always-running Core Agent service. Kept, but added explicit Windows Bridge as separate process since notification listening requires the normal user session.

## Key interfaces (Python sketches)

See `src/python/jarvis/ports/` for the full port definitions and fakes.
