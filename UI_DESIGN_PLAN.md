# JARVIS UI Design Plan

## Design Philosophy
"Beautiful, functional, and alive" — an AI assistant UI that feels premium, responsive, and trustworthy.

## Core Design Tokens

### Color Palette (Dark Mode Baseline)
- Surface elevation system (5 levels):
  - `--surface-0`: #0a0a0b (deep background)
  - `--surface-1`: #111113 (elevated surface)
  - `--surface-2`: #18181b (card surface)
  - `--surface-3`: #1f1f22 (hover surface)
  - `--surface-4`: #27272a (active surface)
- Accent (JARVIS holographic cyan):
  - `--accent-primary`: #00f3ff (bright cyan)
  - `--accent-glow`: rgba(0, 243, 255, 0.4)
  - `--accent-dim`: rgba(0, 243, 255, 0.1)
- Semantic colors:
  - `--success`: #00ff88
  - `--warning`: #ffb800
  - `--danger`: #ff3366
  - `--muted`: #8a8a92
- Text:
  - `--text-primary`: #ffffff
  - `--text-secondary`: #a1a1aa
  - `--text-muted`: #71717a

### Typography
- Primary: Inter (variable font, optical sizing)
- Display: Orbitron (for JARVIS branding, headings)
- Mono: JetBrains Mono (for status, technical data)

### Motion Design
- All animations respect `prefers-reduced-motion`
- Micro-interactions under 400ms
- Spring physics for card lifts
- Ease-out for fades, ease-in-out for slides
- Breathing animations for active states

### Glassmorphism 2.0 Rules
- Glass applied selectively to cards/modals/popups only
- `backdrop-filter: blur(12px)` max
- `border: 1px solid rgba(255,255,255,0.08)`
- Min 4.5:1 contrast on all text
- Never full-screen glass background

## UI States

1. **Idle** — Mic indicator off, status "Standby", no alerts
2. **Listening** — Mic pulsing, status "Listening...", waveform visualization
3. **Thinking** — Status "Processing...", thinking animation (orb pulses)
4. **Speaking** — TTS waveform, status "Speaking...", subtitle display
5. **Alert** — Popup card slide-in (L1/L2/L3), sound-ready
6. **Kill Switch Active** — Red overlay, all controls disabled, "SYSTEM LOCKED"

## Layout Sections
- Top bar: Brand + kill switch + mic indicator + system status
- Main area: Conversation + proactive alerts grid (bento layout)
- Right panel: System health, capabilities, quick actions
- Bottom: Input bar (text fallback) + settings

## Animations Required
- Kill switch toggle (scale + color shift)
- Mic pulse (breathing opacity)
- Alert slide-in + scale-up
- Orb thinking (rotate + scale pulse)
- TTS waveform (bar height animation)
- Button hover (lift + glow)
- Toast notifications (slide in + fade out)
- Page transitions (fade + slide)

## Files to Build
- `ui/jarvis/index.html` — Main application
- `ui/jarvis/styles.css` — All styling (tokens, components, animations)
- `ui/jarvis/app.js` — State management, interactions, simulation
- `ui/server.py` — Simple HTTP server for preview

## Non-Negotiables Preserved
- Kill switch prominent and functional (stops all motion/audio simulation)
- Mic indicator visible when "listening"
- Audit-style status logging (visible "why" for state changes)
- No deceptive animations (motion communicates real state)
- Accessible contrast ratios
- Respect prefers-reduced-motion
