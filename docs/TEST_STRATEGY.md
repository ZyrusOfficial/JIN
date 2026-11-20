# JARVIS Test Strategy

`make check` runs everything: syntax/static, architecture gates, logic-flow tests, property tests, security corpus, simulations, mutation tests. One command, pass/fail summary.

## Test layers

### A. Syntax and static quality
- **Ruff** for formatting and linting (Python). Zero warnings on core.
- **Mypy strict** on core Python.
- **Pre-commit hooks** on every commit.
- JSON Schema / pydantic validation for events, capability manifests, settings.
- **Secret scanning** (truffleHog or similar) in CI — fail if secrets, tokens, or real personal data found.
- **Dependency vulnerability scanning** in CI.

### B. Architecture tests (enforced automatically)
- **Import-linter:** domain code may not import adapters, UI, network, or OS libs; adapters may not import each other; capabilities may import only the SDK.
- **Dependency allowlist:** fail if a new dependency is added without approval.
- **Manifest conformance:** every capability declares permissions; every adapter passes its contract suite.
- **Contract test suites** per port: `WakeWordSource`, `SpeechToText`, `TextToSpeech`, `VoiceActivityDetector`, `EchoCanceller`, `MessageSource`, `CalendarProvider`, `NewsSource`, `NotificationSource`, `DesktopControl`, `Clock`, `SecretsBroker`, `PolicyGate`. Each suite runs against the fake; real implementations run when available (owner-run).
- **Dead-code and circular-dependency detection.**
- **"No business logic in adapters" check:** size and complexity thresholds on adapter modules.

### C. Logic-flow tests
- **Proactive engine decision table:** every combination of importance × interrupt level × context (call, fullscreen, DND, headphones/speakers, quiet hours) × rate-limit state → expected outcome. Table stored as data (JSON/YAML), tests enumerate every row.
- **Speech queue and barge-in:** preemption, resume, stop commands, chunk checkpoints, simultaneous L3 arrival, queue ordering — using a **virtual clock**.
- **Confirmation flows:** every T2/T3 action requires approval; standing rules scoped and expiring.
- **Update Guardian state machine:** every transition plus injected failures (bad checksum, failed health check, login-required state, crash mid-swap, power loss during swap) → automatic rollback, no auto-login.
- **Forge pipeline:** spec→install, permission diff, tier enforcement, rollback, self-escalation attempt must fail.
- **Messenger gap handling:** replay recorded notification streams (truncated, replaced, grouped, dismissed) → correct `partial` flags and thread reconstruction.
- **Calendar:** time zones, DST, recurring events, conflict detection, read-back-before-save.
- **News:** dedupe, clustering, breaking-news corroboration rule (L3 only official source or 2+ independent outlets).

### D. Property-based and fuzz tests (Hypothesis)
- **Policy gate:** no sequence of tool calls reaches T2/T3 behavior without required approval.
- **Scheduler/queue invariants:** no starvation, no lost L3 events, no duplicate speech.
- **Parsers:** notification payloads, feeds, manifests never crash on malformed input.

### E. Scenario and replay simulation
- Deterministic simulation harness with virtual clock and recorded event streams ("a day in the life"): morning briefing, group-chat burst during a call, typhoon alert at 2 AM, meeting, flaky bridge. Golden tests assert exactly what Jarvis says and when.

### F. Security tests
- **Prompt-injection corpus:** hostile text inside messages, headlines, web pages, skill READMEs, filenames, tool output. Pass: zero unapproved actions, zero secret leakage.
- Secrets never in prompts or logs (scan outputs).
- Sandbox escape attempts against capability workers; network-allowlist enforcement.
- Privacy mode: sensitive content never spoken on speakers unless allowed.

### G. Voice and performance
- Fixed audio fixtures (English, Filipino, Taglish) with WER thresholds — CI only if fixtures/models available; otherwise owner-run.
- Latency-budget assertions using fakes with configurable delays (STT <500ms, first LLM token <800ms, first TTS audio <300ms; end-to-end <2s).
- CPU/memory/battery budgets for always-on parts; soak test (long event stream) for leaks.

### H. Mutation testing and coverage
- **Mutation testing** on policy gate, proactive engine, updater state machine.
- **Coverage gates:** 100% branch coverage on policy gate and updater state machine; ~90% elsewhere in core. Killing mutants is the goal, not coverage percentage.

### I. Platform integration tests (owner-run)
- Windows and Android adapter contract suites packaged as spike kits (owner-spikes/S1–S6). Owner runs on real hardware, pastes JSON results.

## Test-writing rules
- Write the failing test first for logic flows and the safety layer.
- Deterministic: virtual clock, seeded randomness, no live network in default suite.
- Every bug fix gets a regression test.
- Fixtures in repo with provenance notes, **no real personal data**.

## `make check` fast subset
Target: under 60 seconds on every save. Full suite runs in CI and before each milestone.
