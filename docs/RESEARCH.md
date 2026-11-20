# JARVIS Research Notes

Findings from section 14 research and build-time verification. Sources are linked with access dates. Everything here is current as of 2026-11-20.

## 1. Windows notification listener (RQ1)

**Finding:** `UserNotificationListener` works from an **unpackaged** Win32/tray app — no package identity (MSIX/sparse package) required for *reading* notifications. A spike on a similar project (stm32-desk-dashboard #33, Oct 2026) confirmed: polled every 500 ms, app names/texts/removals come through, no admin needed, `NotificationChanged` fails with `0x80070490`. Apps with notifications turned off are excluded by Windows.

**Sending notifications:** `AppNotificationManager` (Windows App SDK) works unpackaged for local app notifications; package identity is **not** required for local notifications. Package identity IS required for push/WNS background delivery and COM activation.

**Source:** [Microsoft Q&A — AppNotificationManager unpackaged host](https://learn.microsoft.com/en-us/answers/questions/6006815/is-windows-app-sdk-appnotificationmanager-supporte) (accessed 2026-11-20); [Windows notifications overview](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/) (accessed 2026-11-20); [stm32-desk-dashboard issue #33](https://github.com/egungor/stm32-desk-dashboard/issues/33) (accessed 2026-11-20).

**Decision:** Ship the Windows bridge as an **unpackaged** Win32/C# app using `UserNotificationListener` for reading and `AppNotificationManager` for sending. Revisit MSIX packaging only if push/WNS background delivery is needed. Marked **unverified on owner's hardware** — see spike S1.

## 2. Android Messenger notification extras (RQ2)

**Finding:** Android `Notification.MessagingStyle.Message` exposes `sender`, `text`, `timestamp`, `dataUri`, `dataMimeType`, and `extras`. The notification carries `EXTRA_MESSAGES` (array of message bundles) and `EXTRA_HISTORIC_MESSAGES` (array of historic message bundles). Compliant apps also attach reply/mark-as-read actions.

**Gap:** No public source confirms exactly which fields Facebook Messenger populates. Must be verified on-device via spike S4.

**Source:** [Android Developers — Notification.MessagingStyle.Message](https://developer.android.com/reference/android/app/Notification.MessagingStyle.Message) (accessed 2026-11-20); [NotificationCompat EXTRA_MESSAGES / EXTRA_HISTORIC_MESSAGES](https://developer.android.com/reference/androidx/core/app/NotificationCompat) (accessed 2026-11-20).

**Decision:** Design the Android notification listener to log whatever Messenger provides, flag `partial` when truncated, and fill gaps via backend B/C/D. Marked **unverified** — see spike S4.

## 3. Phone Link Messenger mirroring (RQ3)

**Finding:** Phone Link (Link to Windows on Android) mirrors **all Android app notifications** to Windows, including Messenger, with bidirectional action sync (dismiss/reply on PC syncs to phone). Full support for Android; limited for iPhone. Notification mirroring works even when the phone screen is locked. OEM battery optimization can interfere.

**Caveat:** Fidelity depends on the Link to Windows version and OEM. Not verified specifically for Messenger content completeness.

**Source:** [Windows 11 Phone Link Feature Explained](https://onewebcare.com/windows/windows-11-phone-link-feature/) (accessed 2026-11-20); [Phone Link & Link to Windows 2025](https://windowsforum.com/news/phone-link-and-link-to-windows-2025-seamless-android-to-pc-productivity-387368/) (accessed 2026-11-20).

**Decision:** Treat Phone Link mirroring as backend E (partial, notification-only). Marked **unverified** — see spike S5.

## 4. mautrix-meta Messenger bridge (RQ4)

**Finding:** mautrix-meta v26.11 released 2026-11-16. Supports Messenger + Instagram DM puppeting, E2EE with secure-history PIN recovery, media, replies, reactions, edits, read receipts, typing indicators. AGPL-3.0 licensed. Login flow was broken and fixed several times between Sep–Nov 2026; connection handling improved in October 2026. Default login registers a new device like the official mobile app; browser cookies as fallback. Runs as a Docker container or standalone Go binary.

**Risk:** Automated-activity warnings, forced password changes, new device identity per re-login, checkpoint risk from datacenter IPs. Meta's automated-access ToS still apply. No reliable data on permanent restriction frequency.

**Source:** [mau.fi blog — November 2026 releases](https://mau.fi/blog/2026-11-mautrix-release/) (accessed 2026-11-20); [mautrix-meta release 0.16.0 / v0.2611.0](https://github.com/tamcore/charts/releases/tag/mautrix-meta-0.16.0) (accessed 2026-11-20); [musebridge issue #193](https://github.com/misospace/musebridge/issues/193) (accessed 2026-11-20).

**Decision:** Backend B, opt-in, feature-flagged, self-hosted on owner's home hardware, trial on a **spare account first**. Never run on the owner's main account. Marked **unverified** — see spike S6.

## 5. Wake word, STT, TTS (RQ5)

**Wake word:**
- openWakeWord: Apache 2.0 code, pre-trained models CC BY-NC-SA 4.0 (non-commercial), custom wake words trainable, ~97% accuracy, <3.5% CPU on Pi 5.
- Picovoice Porcupine: proprietary, free tier for ≤3 users, commercial from $6,000, best accuracy (97.3%, 1 FA/10h), sunset of free tier announced May 2026.

**STT:**
- faster-whisper (large-v3): 7.44% WER English, CTranslate2, CPU-friendly.
- Google Cloud STT Chirp (V2): supports Tagalog/Filipino, explicit code-switching config.
- OpenAI Whisper Large-v3: handles code-switching (Taglish) automatically when dominant language set.

**TTS:**
- Kokoro 82M: 4.5 MOS, 17% CER, CPU, ~3.7s first-token latency, 341 MB model.
- Piper: 3.3 MOS, 28% CER, ~1.7s first-token latency, 61 MB model, 8–9× faster than Kokoro.

**Source:** [Picovoice Porcupine](https://picovoice.ai/products/voice/wake-word/) (accessed 2026-11-20); [Jinn wake word system](https://get.jinn.today/blog/jinn-wake-word-system) (accessed 2026-11-20); [Local voice models 2026](https://local-ai-zone.github.io/blog/local-voice-models-2026.html) (accessed 2026-11-20); [Best transcription for Asian languages](https://convertaudiototext.com/blog/best-transcription-for-asian-languages) (accessed 2026-11-20); [Kokoro vs Piper benchmark](https://dev.to/obole/kokoro-82m-computed-slower-than-it-spoke-piper-tts-was-87-to-93-times-faster-3lgh) (accessed 2026-11-20); [On-device TTS benchmark](https://picovoice.ai/blog/on-device-tts/) (accessed 2026-11-20).

**Decision:** Default stack: openWakeWord (custom "Hey Jarvis"), Silero VAD, faster-whisper (STT, Taglish via dominant-language code-switching), Piper TTS (local, fast, CPU), Kokoro as higher-quality alternative. Cloud fallback (OpenAI/Google) configurable. All marked **unverified for Taglish accuracy** — see spike S3.

## 6. Echo cancellation (RQ6)

**Finding:** WebRTC AEC is the standard approach; half-duplex fallback when AEC is unavailable. No specific Windows AEC library research completed yet.

**Decision:** Use WebRTC AEC via the WebRTC noise suppression/AEC bindings, with half-duplex (mic muted while speaking) as fallback. Marked **unverified** — see spike S2.

## 7. MCP spec and registries (RQ7)

**Finding:** Current MCP spec revision is 2026-07-28 (stateless, no initialize handshake/session, `server/discover` required, `server/discover` returns versions/capabilities/identity). Transports: stdio (local), Streamable HTTP (remote). Auth: OAuth 2.1 profile (RFC 9728) or none. Official MCP Registry at registry.modelcontextprotocol.io (preview, ~36K servers as of Sep 2026). Independent aggregators: mcp.so (~20K), smithery.ai, glama.ai (~20K).

**Source:** [What Is MCP? The Model Context Protocol](https://www.bdemerson.com/article/model-context-protocol) (accessed 2026-11-20); [MCP Registry & Server Discovery Guide](https://chatforest.com/guides/mcp-registry-server-discovery/) (accessed 2026-11-20); [MCP Registries in 2026](https://roxyapi.com/blogs/mcp-registries-where-to-list-your-server-2026) (accessed 2026-11-20).

**Decision:** Capability Forge connectors use MCP stdio for local servers, Streamable HTTP for remote. Discovery via official MCP Registry API (v0.1) plus private allowlist. Marked **unverified** until a connector is actually installed.

## 8. Windows context signals (RQ8)

**Finding:** No deep research completed on specific APIs for fullscreen, presentation, call-active, and headphone detection. The brief notes the shell's user-notification-state API is the usual one for fullscreen and presentation.

**Decision:** Research at Phase 2 (proactive engine). Use Windows App SDK notification state + UI Automation for foreground app, audio endpoint APIs for headphone/speakers, call-state via telephony APIs where available. Marked **unverified**.

## 9. Philippine alert feeds (RQ9)

**Finding:** PAGASA publishes a **CAP alert feed** at `publicalert.pagasa.dost.gov.ph/feeds` (Common Alerting Protocol, machine-readable XML). PHIVOLCS publishes earthquake/volcano/tsunami bulletins but **no structured RSS/feed** — requires scraping or third-party aggregation (e.g. Apify `ph-hazards`). No official PAGASA/PHIVOLCS API confirmed.

**Source:** [Hazards Bulletin — LIGTAS DRRMS](https://ligtas.cair.ph/bulletin/) (accessed 2026-11-20); [PHIVOLCS Earthquakes & PAGASA Weather API](https://apify.com/a-g-d/ph-hazards) (accessed 2026-11-20).

**Decision:** News/alert source adapter reads PAGASA CAP feed (official, machine-readable) and scrapes PHIVOLCS bulletin page as fallback. Breaking-news corroboration rule: L3 only from official source or 2+ independent outlets. Marked **unverified** until the CAP feed is polled.

## 10. Google Play SMS/Assistant policy (RQ10)

**Finding:** Google Play restricts SMS and Call Log permissions to apps registered as default SMS, Phone, or Assistant handler. "Notification enhancement" and text-to-voice for SMS are disallowed uses for non-default handlers. Play policy does not apply to personal sideloaded builds (inference, unverified).

**Source:** [Google Play Console Help — SMS and Call Log permissions](https://support.google.com/googleplay/android-developer/) (accessed 2026-11-20).

**Decision:** Android companion targets Assistant role first, default SMS app as alternative, sideload personal build as fallback. Marked **unverified** — see spike S4/S6.

## 11. Windows sandbox for generated code (RQ11)

**Finding:** No research completed. Options: Windows Sandbox, containers, restricted job-object subprocess.

**Decision:** Use restricted job-object subprocess for capability workers (no network by default), with Windows Sandbox as a stronger option if available. Marked **unverified**.

## 12. Additional findings

- Meta shut down the Messenger desktop app Dec 15, 2025 and closed messenger.com in April 2026. Web access is now `facebook.com/messages`. (Wikipedia + Gulf News coverage; dates vary slightly.)
- mautrix-meta login: each re-login may look like a new device; checkpoint risk from datacenter IPs; run on home IP, one session, low footprint.
- MCP server/discover RPC method added in spec 2026-07-28 for in-session discovery.
