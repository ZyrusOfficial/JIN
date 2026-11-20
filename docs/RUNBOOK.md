# JARVIS Runbook

## Install (developer / owner PC)

### Prerequisites
- Windows 10 or 11
- Python 3.12+
- .NET 8 SDK (for the Windows bridge)
- Node.js 18+ (for the UI shell, later)
- A C compiler (for some Python wheel builds)

### Clone and set up
```bash
git clone <repo-url> JIN
cd JIN
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### Run `make check`
```bash
make check
```
This runs lint, type-check, architecture rules, contract tests, logic-flow tests, property tests, security corpus, simulations, and mutation tests. Fast subset targets <60s.

### Run the walking skeleton
```bash
make run-skeleton
```
Starts the core agent with fake microphone input, fake LLM, TTS stub, and one popup — end to end.

## First-run permissions (Windows)

1. **Notifications:** Windows Settings → System → Notifications → enable notifications for JARVIS bridge. Grant notification listener access when prompted.
2. **Microphone:** Windows Settings → Privacy & security → Microphone → enable microphone access and let desktop apps access the mic.
3. **Tray icon:** JARVIS runs in the system tray. Click the icon for settings, kill switch, and status.
4. **Kill switch:** Global hotkey (default: `Ctrl+Alt+K`) instantly stops speech, listening, proactive behavior, and updates. Also available from the tray menu.

## Running spike kits

Each spike is in `owner-spikes/S<N>_<name>/`. Each has a `README.md` with numbered steps and prints a single JSON result file.

| Spike | Purpose | What to run |
|---|---|---|
| S1 | Windows notification listener access | See `owner-spikes/S1_windows_notification_listener/README.md` |
| S2 | Audio loop, VAD, echo, latency | See `owner-spikes/S2_audio_loop/README.md` |
| S3 | Taglish STT word-error rate | See `owner-spikes/S3_taglish_stt/README.md` |
| S4 | Android Messenger notification extras | See `owner-spikes/S4_android_notification_extras/README.md` |
| S5 | Phone Link mirroring fidelity | See `owner-spikes/S5_phone_link_mirroring/README.md` |
| S6 | mautrix-meta bridge trial (spare account) | See `owner-spikes/S6_bridge_trial/README.md` |

**Important:** S6 must be run on a **spare Messenger account**, never the owner's main account.

## Kill switch

- Hotkey: `Ctrl+Alt+K` (configurable in settings)
- Tray: right-click JARVIS icon → "Kill switch"
- Effect: stops speech, listening, proactive behavior, and updates immediately. Restart JARVIS to re-enable.

## Freeze / roll back a component

- Freeze: Settings → Update Guardian → "Freeze this component" on the component you want to pause.
- Roll back: Settings → Update Guardian → version list → "Roll back" on the previous version.
- Rollback restores the previous version and database backup; the bad version is added to the skip list.

## Audit log

- Location: `%APPDATA%\JARVIS\audit.log` (Windows) or `~/.jarvis/audit.log`
- Every policy decision, message sent, and capability install is logged with a "why."
- The log is tamper-evident (hash chain).

## Secrets

- Secrets are held by the secrets broker (Windows Credential Manager / DPAPI).
- Secrets never appear in prompts, logs, or model input.
- Secret-scanning runs in CI and locally via pre-commit.

## Unverified items

Everything that touches real Windows, Android, or third-party accounts is unverified until an owner-run spike confirms it. See docs/STATUS.md for the full list.

## Support

File an issue in this repo with:
- The output of `make check`
- The JSON result from any spike you ran
- Your Windows version and PC specs (GPU/RAM)
