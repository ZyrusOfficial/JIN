# Spike S6: mautrix-meta Messenger bridge trial (SPARE ACCOUNT ONLY)

## Purpose
Run mautrix-meta (Matrix-Messenger bridge) on your home hardware for about a week, using a **spare Messenger account**. Count checkpoints, logouts, forced password changes, and measure stability.

## ⚠️ CRITICAL: Use a SPARE account only

**Do NOT run this on your main Messenger account.** Meta may issue automated-activity warnings, force password changes, or restrict accounts that use bridges. Use a spare account you don't mind losing access to.

## What this tells us
- How often mautrix-meta needs re-login
- Whether checkpoints or forced password changes occur
- How stable the connection is over ~1 week
- Whether the bridge is viable as backend B for JARVIS

## Prerequisites
- A spare Facebook/Messenger account
- Home hardware that can run Docker (or a spare PC / Raspberry Pi / always-on device)
- Docker installed, or ability to run a Go binary
- About 1 week of observation time

## Steps

### Day 0: Setup
1. Choose a home device that stays on (PC, Raspberry Pi, old laptop).
2. Install Docker: https://docs.docker.com/desktop/install/windows-install/
3. Create a `docker-compose.yml` for mautrix-meta (see example below).
4. Register a **spare** Messenger account specifically for this trial.
5. Start the bridge and complete the login flow (owner does the login — never automatic).
6. Note the login date and time.

### Days 1-7: Daily check
Each day, check:
- Is the bridge still connected? (check Matrix client or bridge logs)
- Did you get a checkpoint warning?
- Did Facebook force a password change?
- Did messages stop flowing?
- Did you need to re-login?

Record each event in `s6_result.json`.

### Day 7: Summary
- Total checkpoints: ____
- Total forced password changes: ____
- Total re-logins required: ____
- Longest uninterrupted run: ____ days
- Messages sent/received successfully: ____
- Would you recommend this bridge? Yes/No

## Example docker-compose.yml

```yaml
version: "3"
services:
  mautrix-meta:
    image: dock.mau.dev/mautrix/meta:v0.2611.0
    restart: unless-stopped
    volumes:
      - ./mautrix-meta:/data
    environment:
      - MXT_BRIDGE_METASPACE_ENABLED=false
```

### Config (mautrix-meta config.yaml)
- Set `bridge.messenger.enabled: true`
- Set `bridge.messenger.username` and `password` (spare account)
- Login method: `device` (registers as new device) or `cookie` (browser fallback)

## Result file
`owner-spikes/S6_bridge_trial/s6_result.json` — paste this back after the trial.

## ⚠️ Safety rules (non-negotiable)
- SPARE ACCOUNT ONLY — never your main account
- No automatic re-login — if login fails, stop and ask
- No evasion tricks — no device ID spoofing, no fingerprint manipulation
- Low footprint: one session, home IP, few requests
- If the bridge breaks, Messenger falls back to notification-only mode
