# Spike S5: Phone Link Messenger mirroring

## Purpose
Verify whether Microsoft Phone Link mirrors Messenger notifications to Windows, and with what fidelity.

## What this tells us
- Whether Phone Link shows Messenger notifications on the PC
- Whether notification content (sender, text) is visible
- Whether reply actions work from the PC
- Whether this can serve as backend E (notification-only Messenger)

## Prerequisites
- Windows 11 with Phone Link app
- Android phone with Link to Windows app
- Both devices paired and linked

## Steps

1. Open Phone Link on Windows and Link to Windows on your Android phone.
2. Ensure notifications are enabled for both apps.
3. Send yourself a Messenger message from another device.
4. Check if the notification appears in Windows Action Center / Phone Link.
5. Record:
   - Does the notification appear?
   - What fields are visible (sender, text, timestamp)?
   - Can you reply from Windows?
   - Does dismissing on PC dismiss on phone?
6. Fill in `s5_result.json`.

## Result file
`owner-spikes/S5_phone_link_mirroring/s5_result.json` — paste this back.

## Notes
- Phone Link for Android supports notification mirroring; iPhone is more limited.
- Results vary by OEM and Android version.
- This is read-only.
