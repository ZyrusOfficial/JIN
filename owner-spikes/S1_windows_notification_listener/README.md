# Spike S1: Windows notification listener

## Purpose
Verify that the Windows notification listener (`UserNotificationListener`) works from an **unpackaged** app on your PC, and capture what a Messenger notification looks like.

## What this tells us
- Whether notification listener access works without package identity (MSIX)
- Which apps post notifications (including Messenger via browser or Phone Link)
- What fields each notification contains (app ID, title, text, timestamp)

## Prerequisites
- Windows 10 or 11
- Python 3.12+ (or PowerShell 7+)
- Messenger installed or accessible via facebook.com/messages in a browser

## Steps

1. Open this folder in PowerShell or Command Prompt.
2. Run the spike script:
   ```powershell
   python s1_notification_listener.py
   ```
   or
   ```powershell
   pwsh s1_notification_listener.ps1
   ```
3. While the script is running, send yourself a Messenger message (from your phone or another device) so a toast appears on your PC.
4. Watch the console output — it prints each notification as it arrives.
5. Press Ctrl+C to stop.
6. The script writes `s1_result.json` with the full output.

## Expected output
The script prints:
- `access_granted`: whether notification listener access is available
- `unpackaged_app`: true (confirming this works without MSIX)
- `notifications`: array of captured notifications with app_id, title, text, timestamp
- `messenger_seen`: true if a Messenger notification was captured

## Result file
`owner-spikes/S1_windows_notification_listener/s1_result.json` — paste this back to the agent.

## Notes
- If `access_granted` is false, go to Windows Settings → System → Notifications and enable notification access.
- If no Messenger notification appears, try Phone Link mirroring or the browser version of facebook.com/messages.
- This is read-only — nothing is sent or modified.
