# JARVIS Architecture Decision Records

## ADR-001: Stack — Python 3.12 core, C# Windows bridge, Kotlin Android

**Context:** The brief suggested Python for the core agent and C# for the Windows bridge. Alternatives considered: .NET 8 end-to-end, Tauri for UI.

**Decision:** Core agent in Python 3.12 (asyncio, pydantic v2, FastAPI + WebSocket). Windows bridge in C# (.NET 8) for `UserNotificationListener` and UI Automation. UI shell TBD (Tauri default, Electron/WinUI 3 alternatives).

**Consequences:** Python gives fast iteration and rich AI/ML libraries. C# gives first-class Windows API access. Two languages increase context-switching but match each platform's strengths.

**Date:** 2026-11-20

## ADR-002: Wake word — openWakeWord default, Porcupine optional

**Context:** Brief mentioned openWakeWord or Porcupine. Custom "Hey Jarvis" wake word needed.

**Decision:** Default to openWakeWord (Apache 2.0 code, custom wake words trainable, no per-device fee). Porcupine available as a higher-accuracy licensed alternative.

**Consequences:** Zero licensing cost for the default path. Models are CC BY-NC-SA (non-commercial) — fine for personal use. Accuracy slightly below Porcupine but acceptable for a personal assistant.

**Date:** 2026-11-20

## ADR-003: STT — faster-whisper default, Google Cloud STT Chirp cloud alternative

**Context:** Taglish accuracy is the weakest point of many engines. Need local + cloud options.

**Decision:** Default to faster-whisper (large-v3) with dominant-language setting for Taglish code-switching. Google Cloud STT Chirp as cloud alternative for Filipino.

**Consequences:** Local STT keeps audio private. Taglish accuracy unverified — see spike S3.

**Date:** 2026-11-20

## ADR-004: TTS — Piper default, Kokoro quality alternative, cloud neural configurable

**Context:** Need streaming, interruptible TTS with Filipino naturalness.

**Decision:** Default to Piper (fast, CPU, ~1.7s first-token). Kokoro as higher-quality alternative (4.5 MOS but slower). Cloud neural TTS (OpenAI/Google/ElevenLabs) configurable.

**Consequences:** Piper works on modest hardware. Filipino voice quality unverified — needs testing.

**Date:** 2026-11-20

## ADR-005: Windows bridge unpackaged (no MSIX)

**Context:** Research confirmed `UserNotificationListener` works from unpackaged Win32 apps for reading notifications. Package identity only needed for push/WNS background delivery.

**Decision:** Ship Windows bridge as unpackaged C# Win32 app. Revisit MSIX only if push notifications needed.

**Consequences:** Simpler distribution (ZIP or Inno Setup installer). No Store or package identity complexity. Marked unverified on owner's hardware — see spike S1.

**Date:** 2026-11-20

## ADR-006: Messenger backend priority — Android notification capture first

**Context:** No sanctioned personal Messenger API. mautrix-meta is high-completeness but medium-high detection risk.

**Decision:** Backend A (Android notification capture) is primary. Backend B (mautrix-meta) is opt-in, feature-flagged, spare-account trial first. Backend C (facebook.com/messages passive reader) is read-only fallback.

**Consequences:** Lowest risk path first. Full message history requires backend B or C, both unverified.

**Date:** 2026-11-20

## ADR-007: Hybrid AI — local voice front end, cloud reasoning, local fallback

**Context:** Owner's GPU/RAM unknown. Cloud vs local is an open decision.

**Decision:** Default hybrid: local wake word/VAD/STT/TTS, cloud LLM for reasoning, local Ollama fallback. Abstract model layer so it's a configuration choice.

**Consequences:** Works on modest hardware with cloud LLM. Falls back to local if cloud unavailable. Owner decides final cloud/local mix.

**Date:** 2026-11-20

## ADR-008: Alert sources — PAGASA CAP feed primary, PHIVOLCS scrape fallback

**Context:** Need Philippine weather/earthquake alerts as first-class defaults.

**Decision:** PAGASA CAP alert feed (`publicalert.pagasa.dost.gov.ph/feeds`) as primary official source. PHIVOLCS bulletin page scraping as fallback (no structured feed confirmed).

**Consequences:** CAP is machine-readable and official. PHIVOLCS scraping is fragile — monitor for changes.

**Date:** 2026-11-20

## ADR-009: MCP for connectors — spec 2026-07-28, stdio + Streamable HTTP

**Context:** Capability Forge needs a connector protocol. MCP is the emerging standard.

**Decision:** Connectors speak MCP (2026-07-28 stateless spec). Local servers on stdio, remote on Streamable HTTP. Discovery via official MCP Registry + private allowlist.

**Consequences:** Access to ~36K+ public MCP servers. Security scanning still needed per capability.

**Date:** 2026-11-20

## Deviations summary vs. brief

- No deviation weakens any non-negotiable (section 3.3).
- Stack choices match the brief's suggestions with documented alternatives.
- Windows bridge is unpackaged (deviates from possible MSIX expectation) — justified by research.
