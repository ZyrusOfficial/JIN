# Spike S4: Android Messenger notification extras

## Purpose
Log what Facebook Messenger puts in its Android notification extras (EXTRA_MESSAGES, EXTRA_HISTORIC_MESSAGES, sender, text, timestamp, etc.).

## What this tells us
- How complete Messenger's notification payload is
- Whether we can reconstruct message threads from notifications alone
- Whether messages are truncated (partial flag needed)
- Whether historic messages extra is populated

## Prerequisites
- Android phone with Messenger installed
- A second Messenger account (to send test messages to yourself)
- Android Studio / adb, or a notification-logging app from Play Store

## Steps

1. Install a notification-logging app on your Android phone (or use adb shell dumpsys notification).
2. Send yourself several Messenger messages:
   - A short text message
   - A long message (tests truncation / partial flag)
   - A message with an image
   - A group chat message
   - An edited message
   - An unsent message
3. Capture the notification extras for each.
4. Record what EXTRA_MESSAGES and EXTRA_HISTORIC_MESSAGES contain.
5. Fill in `s4_result.json` with your findings.

## Result file
`owner-spikes/S4_android_notification_extras/s4_result.json` — paste this back.

## Notes
- Do not include real message content from other people. Use your own test account.
- This is read-only — nothing is sent or modified.
- Mark each field as "present", "absent", or "truncated".
