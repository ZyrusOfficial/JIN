/* ==========================================================================
   JARVIS — Application Logic
   Glassmorphism 2.0 voice-first desktop assistant UI
   State machine: idle | listening | thinking | speaking | alert | kill-active
   ========================================================================== */

(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Audio Context (Web Audio API) — micro-feedback beeps / buzzers     */
  /* ------------------------------------------------------------------ */
  let audioCtx = null;

  function ensureAudio() {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) audioCtx = new AC();
    }
    return audioCtx;
  }

  function beep(freq, type = "sine", duration = 80, volume = 0.1) {
    const ctx = ensureAudio();
    if (!ctx) return;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    gain.gain.setValueAtTime(volume, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + duration / 1000);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t);
    osc.stop(t + duration / 1000 + 0.05);
  }

  function chime() {
    beep(880, "sine", 120, 0.12);
    setTimeout(() => beep(1320, "sine", 160, 0.12), 100);
  }

  function buzz() {
    beep(220, "sawtooth", 160, 0.15);
  }

  /* ------------------------------------------------------------------ */
  /* State                                                              */
  /* ------------------------------------------------------------------ */
  const UI_STATES = {
    IDLE: "idle",
    LISTENING: "listening",
    THINKING: "thinking",
    SPEAKING: "speaking",
    ALERT: "alert",
    KILL_ACTIVE: "kill-active",
  };

  const state = {
    ui: UI_STATES.IDLE,
    micOn: false,
    killActive: false,
    alertOpen: false,
    volume: 0.8,
    audioAvailable: false,
  };

  /* ------------------------------------------------------------------ */
  /* Elements                                                           */
  /* ------------------------------------------------------------------ */
  const els = {
    body: document.body,
    statusPill: document.getElementById("status-pill"),
    micBtn: document.getElementById("mic-btn"),
    micIcon: document.querySelector(".mic-icon"),
    micLabel: document.querySelector(".mic-label"),
    micPulse: document.querySelector(".mic-pulse"),
    killSwitch: document.getElementById("kill-switch"),
    killSwitchBig: document.getElementById("kill-switch-big"),
    killStatusIndicator: document.getElementById("kill-status-indicator"),
    micStatusDisplay: document.getElementById("mic-status-display"),
    micDot: document.querySelector(".mic-dot"),
    micText: document.querySelector(".mic-text"),
    micLevelMeter: document.getElementById("mic-level-meter"),
    conversationLog: document.getElementById("conversation-log"),
    typingIndicator: document.getElementById("typing-indicator"),
    bentoGrid: document.getElementById("bento-grid"),
    bentoPlaceholder: document.querySelector(".bento-placeholder"),
    popupOverlay: document.getElementById("popup-overlay"),
    popupCard: document.getElementById("popup-card"),
    popupLevel: document.getElementById("popup-level"),
    popupTitle: document.getElementById("popup-title"),
    popupBody: document.getElementById("popup-body"),
    popupSource: document.getElementById("popup-source"),
    popupClose: document.getElementById("popup-close"),
    popupBtnRead: document.getElementById("popup-btn-read"),
    popupBtnSnooze: document.getElementById("popup-btn-snooze"),
    popupBtnDismiss: document.getElementById("popup-btn-dismiss"),
    toastContainer: document.getElementById("toast-container"),
    textInput: document.getElementById("text-input"),
    inputSend: document.getElementById("input-send"),
    auditEntries: document.getElementById("audit-entries"),
  };

  /* ------------------------------------------------------------------ */
  /* Helpers                                                            */
  /* ------------------------------------------------------------------ */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function nowISO() {
    return new Date().toISOString();
  }

  function formatTime() {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
  }

  function setUiState(next) {
    if (state.ui === next) return;
    const prev = state.ui;
    state.ui = next;
    els.body.setAttribute("data-ui-state", next);

    // Announce state change to screen readers
    const announcements = {
      [UI_STATES.IDLE]: "JARVIS is on standby.",
      [UI_STATES.LISTENING]: "Listening.",
      [UI_STATES.THINKING]: "JARVIS is thinking.",
      [UI_STATES.SPEAKING]: "JARVIS is speaking.",
      [UI_STATES.ALERT]: "Proactive alert displayed.",
      [UI_STATES.KILL_ACTIVE]: "Kill switch active. All systems halted.",
    };
    if (announcements[next]) {
      announce(announcements[next]);
    }

    // Audio cues
    switch (next) {
      case UI_STATES.LISTENING:
        beep(1100, "sine", 60, 0.08);
        break;
      case UI_STATES.SPEAKING:
        beep(1320, "sine", 80, 0.08);
        break;
      case UI_STATES.ALERT:
        chime();
        break;
      case UI_STATES.KILL_ACTIVE:
        buzz();
        break;
    }

    // Mic button sync
    updateMicUI();
    updateKillUI();
  }

  function announce(text) {
    if (!text) return;
    const live = document.createElement("div");
    live.setAttribute("aria-live", "polite");
    live.setAttribute("aria-atomic", "true");
    live.style.position = "absolute";
    live.style.left = "-10000px";
    live.style.width = "1px";
    live.style.height = "1px";
    live.style.overflow = "hidden";
    live.textContent = text;
    document.body.appendChild(live);
    setTimeout(() => live.remove(), 1000);
  }

  function updateMicUI() {
    const on = state.micOn && !state.killActive;
    els.micBtn.setAttribute("data-state", on ? "on" : "off");
    els.micBtn.setAttribute("aria-pressed", String(on));
    els.micBtn.setAttribute("aria-label", on ? "Microphone on — click to mute" : "Microphone off — click to unmute");

    const dot = els.micDot;
    const micText = els.micText;
    if (on) {
      dot.className = "mic-dot mic-dot--on";
      if (micText) micText.textContent = "On";
      els.micLabel.textContent = "Mic: On";
    } else {
      dot.className = "mic-dot mic-dot--off";
      if (micText) micText.textContent = "Off";
      els.micLabel.textContent = "Mic: Off";
    }
  }

  function updateKillUI() {
    const active = state.killActive;
    els.killSwitch.setAttribute("data-state", active ? "active" : "inactive");
    els.killSwitch.setAttribute("aria-pressed", String(active));
    els.killSwitch.querySelector(".ks-state").textContent = active ? "ACTIVE" : "Inactive";

    els.killSwitchBig.setAttribute("data-state", active ? "active" : "inactive");
    els.killSwitchBig.querySelector(".ks-big-text").textContent = active ? "KILL SWITCH" : "KILL SWITCH";
    els.killSwitchBig.querySelector(".ks-big-sub").textContent = active ? "ACTIVE — ALL SYSTEMS HALTED" : "INACTIVE";

    const indicator = els.killStatusIndicator;
    indicator.setAttribute("data-active", String(active));
    const dot = indicator.querySelector(".dot");
    dot.className = active ? "dot dot--danger" : "dot dot--safe";
    indicator.querySelector(".text").textContent = active
      ? "ALL SYSTEMS HALTED"
      : "All systems operational";
  }

  function toggleMic() {
    if (state.killActive) {
      toast("Mic disabled while kill switch is active.", "warning");
      return;
    }
    state.micOn = !state.micOn;
    updateMicUI();
    const msg = state.micOn ? "Microphone enabled." : "Microphone muted.";
    toast(msg, state.micOn ? "success" : "info");
    audit("mic.toggle", state.micOn ? "Microphone enabled by user." : "Microphone muted by user.");
  }

  function toggleKill() {
    state.killActive = !state.killActive;
    if (state.killActive) {
      setUiState(UI_STATES.KILL_ACTIVE);
      toast("Kill switch ACTIVE — all speech, listening, and proactive behavior halted.", "error");
    } else {
      setUiState(UI_STATES.IDLE);
      toast("Kill switch inactive — systems operational.", "success");
    }
    audit("kill.toggle", state.killActive ? "Kill switch activated by user — all systems halted." : "Kill switch deactivated by user.");
  }

  /* ------------------------------------------------------------------ */
  /* Conversation                                                       */
  /* ------------------------------------------------------------------ */
  let msgCounter = 0;

  function addMessage(role, text, opts = {}) {
    msgCounter++;
    const isSystem = role === "system";
    const div = document.createElement("div");
    div.className = `msg${isSystem ? " msg--system" : ""}`;
    div.setAttribute("role", "log");
    div.setAttribute("aria-label", `${role} message`);

    const avatarLetter = isSystem ? "J" : role.charAt(0).toUpperCase();
    const avatarClass = isSystem ? "msg-avatar msg-avatar--system" : "msg-avatar";

    const time = opts.time || formatTime();
    div.innerHTML = `
      <div class="${avatarClass}" aria-hidden="true">${escapeHtml(avatarLetter)}</div>
      <div class="msg-content">
        <div class="msg-text">${escapeHtml(text)}</div>
        <div class="msg-time">${time}</div>
      </div>
    `;

    els.conversationLog.appendChild(div);
    scrollToBottom();

    // Audit significant messages
    if (opts.audit) {
      audit(`message.${role}`, escapeHtml(text));
    }

    return div;
  }

  function scrollToBottom() {
    els.conversationLog.scrollTop = els.conversationLog.scrollHeight;
  }

  function setTyping(show) {
    els.typingIndicator.style.display = show ? "flex" : "none";
    if (show) scrollToBottom();
  }

  function clearConversation() {
    els.conversationLog.innerHTML = "";
    msgCounter = 0;
    addMessage("system", "Conversation cleared.", { audit: true });
  }

  /* ------------------------------------------------------------------ */
  /* Bento Grid Alerts                                                  */
  /* ------------------------------------------------------------------ */
  const alerts = new Map();

  function addAlert({ id, level = "L2", title, body, source = "system", ts, actions = [] }) {
    if (alerts.has(id)) return;
    const item = document.createElement("div");
    item.className = `bento-item level--${level}`;
    item.setAttribute("data-alert-id", id);
    item.setAttribute("role", "alert");
    item.setAttribute("aria-label", `Alert level ${level}: ${title}`);

    const badgeText = { L1: "LOW", L2: "MEDIUM", L3: "CRITICAL" }[level] || level;
    const time = ts || formatTime();

    item.innerHTML = `
      <span class="bento-level-badge">${badgeText}</span>
      <div class="bento-title">${escapeHtml(title)}</div>
      <div class="bento-body">${escapeHtml(body)}</div>
      <div class="bento-footer">
        <span class="bento-source"><span class="source-dot"></span><span>${escapeHtml(source)}</span></span>
        <span>${time}</span>
      </div>
    `;

    // Click to expand / read aloud
    item.addEventListener("click", (e) => {
      if (e.target.closest(".bento-actions")) return;
      showPopup({ id, level, title, body, source, time });
    });

    if (els.bentoPlaceholder) els.bentoPlaceholder.style.display = "none";
    els.bentoGrid.prepend(item);
    alerts.set(id, { element: item, level, title, body, source, time });

    toast(`New alert: ${title}`, "info", 4000);
    audit(`alert.received`, `Level ${level} alert "${title}" from ${source}.`);
    setUiState(UI_STATES.ALERT);

    return item;
  }

  function dismissAlert(id) {
    const entry = alerts.get(id);
    if (!entry) return;
    entry.element.style.opacity = "0";
    entry.element.style.transform = "translateY(-10px)";
    setTimeout(() => {
      entry.element.remove();
      alerts.delete(id);
      if (alerts.size === 0 && els.bentoPlaceholder) {
        els.bentoPlaceholder.style.display = "flex";
      }
      if (alerts.size === 0) setUiState(UI_STATES.IDLE);
    }, 300);
    audit("alert.dismissed", `Alert "${id}" dismissed by user.`);
  }

  function dismissAllAlerts() {
    $$(".bento-item").forEach((el) => {
      const id = el.getAttribute("data-alert-id");
      el.style.opacity = "0";
      el.style.transform = "translateY(-10px)";
      if (id) audit("alert.dismissed", `Alert "${id}" dismissed (dismiss all).`);
    });
    setTimeout(() => {
      $$(".bento-item").forEach((el) => el.remove());
      alerts.clear();
      if (els.bentoPlaceholder) els.bentoPlaceholder.style.display = "flex";
      setUiState(UI_STATES.IDLE);
    }, 300);
  }

  /* ------------------------------------------------------------------ */
  /* Popup Overlay                                                      */
  /* ------------------------------------------------------------------ */
  let currentPopupId = null;

  function showPopup({ id, level, title, body, source, time }) {
    currentPopupId = id;
    els.popupLevel.textContent = `L${level} ${{ L1: "Low", L2: "Medium", L3: "Critical" }[level] || ""}`;
    els.popupLevel.className = `popup-level popup-level--${level}`;
    els.popupTitle.textContent = title;
    els.popupBody.textContent = body;
    els.popupSource.textContent = `Source: ${source} · ${time}`;

    els.popupOverlay.style.display = "flex";
    els.popupOverlay.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    setUiState(UI_STATES.ALERT);
    audit("alert.opened", `Popup opened for alert "${id}".`);
  }

  function hidePopup() {
    els.popupOverlay.style.display = "none";
    els.popupOverlay.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    currentPopupId = null;
    if (alerts.size === 0) setUiState(UI_STATES.IDLE);
  }

  els.popupClose.addEventListener("click", () => {
    if (currentPopupId) dismissAlert(currentPopupId);
    hidePopup();
  });

  els.popupOverlay.addEventListener("click", (e) => {
    if (e.target === els.popupOverlay) {
      if (currentPopupId) dismissAlert(currentPopupId);
      hidePopup();
    }
  });

  els.popupBtnRead.addEventListener("click", () => {
    if (!currentPopupId) return;
    const entry = alerts.get(currentPopupId);
    if (!entry) return;
    speakText(`${entry.title}. ${entry.body}`);
    audit("alert.read_aloud", `Alert "${currentPopupId}" read aloud by user.`);
    hidePopup();
  });

  els.popupBtnSnooze.addEventListener("click", () => {
    if (!currentPopupId) return;
    dismissAlert(currentPopupId);
    hidePopup();
    toast("Alert snoozed for 30 minutes.", "info", 3000);
    audit("alert.snoozed", `Alert "${currentPopupId}" snoozed for 30 minutes.`);
  });

  els.popupBtnDismiss.addEventListener("click", () => {
    if (!currentPopupId) return;
    dismissAlert(currentPopupId);
    hidePopup();
    audit("alert.dismissed", `Alert "${currentPopupId}" dismissed from popup.`);
  });

  /* ------------------------------------------------------------------ */
  /* Toasts                                                             */
  /* ------------------------------------------------------------------ */
  let toastIdCounter = 0;

  function toast(message, type = "info", duration = 3500) {
    const id = `toast-${++toastIdCounter}`;
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.setAttribute("role", "alert");
    el.setAttribute("aria-label", `Notification: ${message}`);

    const icons = {
      info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>',
      success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
      warning: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
      error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
    };

    el.innerHTML = `
      <div class="toast-icon">${icons[type] || icons.info}</div>
      <div class="toast-body">
        <div class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
      </div>
      <button class="toast-btn" aria-label="Dismiss notification">✕</button>
    `;

    const btn = el.querySelector(".toast-btn");
    btn.addEventListener("click", () => removeToast(el));

    els.toastContainer.appendChild(el);
    // Force reflow for animation
    el.offsetHeight;
    el.style.animation = `toast-slide-in var(--dur-base) var(--ease-out)`;

    setTimeout(() => removeToast(el), duration);
    return id;
  }

  function removeToast(el) {
    el.style.opacity = "0";
    el.style.transform = "translateX(100%)";
    setTimeout(() => el.remove(), 300);
  }

  /* ------------------------------------------------------------------ */
  /* Audit Trail (sidebar)                                              */
  /* ------------------------------------------------------------------ */
  let auditCounter = 0;

  function audit(action, reason) {
    auditCounter++;
    const entry = document.createElement("div");
    entry.className = "audit-entry";
    entry.innerHTML = `
      <span class="audit-time">${formatTime()}</span>
      <span class="audit-action">${escapeHtml(action)}</span>
      <span class="audit-reason">${escapeHtml(reason)}</span>
    `;
    if (els.auditEntries) {
      els.auditEntries.prepend(entry);
      // Keep only last 8 entries
      const children = els.auditEntries.children;
      if (children.length > 8) children[children.length - 1].remove();
    }
    console.log(`[AUDIT ${new Date().toISOString()}] ${action}: ${reason}`);
  }

  /* ------------------------------------------------------------------ */
  /* Mic level simulation (visual feedback only)                        */
  /* ------------------------------------------------------------------ */
  let meterFrame = null;

  function startMeter() {
    if (meterFrame) return;
    const bars = $$(".meter-bar");
    function tick() {
      if (!state.micOn) {
        bars.forEach((b) => (b.style.height = "10%"));
        meterFrame = null;
        return;
      }
      bars.forEach((b) => {
        b.style.height = `${Math.floor(20 + Math.random() * 80)}%`;
      });
      meterFrame = requestAnimationFrame(tick);
    }
    tick();
  }

  function stopMeter() {
    if (meterFrame) {
      cancelAnimationFrame(meterFrame);
      meterFrame = null;
    }
    const bars = $$(".meter-bar");
    bars.forEach((b) => (b.style.height = "10%"));
  }

  /* ------------------------------------------------------------------ */
  /* Speak (TTS simulation)                                             */
  /* ------------------------------------------------------------------ */
  let utteranceTimeout = null;

  function speakText(text, opts = {}) {
    if (state.killActive) {
      toast("Speech blocked — kill switch is active.", "warning");
      return;
    }
    setUiState(UI_STATES.SPEAKING);
    setTyping(false);
    addMessage("jarvis", text, { audit: opts.audit });

    // Simulate speaking duration based on length
    const ms = Math.min(3000, Math.max(1200, text.length * 35));
    if (utteranceTimeout) clearTimeout(utteranceTimeout);
    utteranceTimeout = setTimeout(() => {
      setUiState(UI_STATES.IDLE);
    }, ms);

    audit("tts.speak", `Spoke ${Math.round(text.length / 5)} words.`);
  }

  /* ------------------------------------------------------------------ */
  /* Input (text fallback)                                              */
  /* ------------------------------------------------------------------ */
  function handleUserInput(text) {
    if (!text || !text.trim()) return;
    if (state.killActive) {
      toast("Input blocked — kill switch is active.", "warning");
      return;
    }
    text = text.trim();
    addMessage("user", text, { audit: true });
    setTyping(true);
    setUiState(UI_STATES.THINKING);

    // Simulate assistant response after a short "thinking" delay
    setTimeout(() => {
      setTyping(false);
      const reply = generateReply(text);
      speakText(reply);
    }, 1200);
  }

  function generateReply(input) {
    const lower = input.toLowerCase();
    if (lower.includes("hello") || lower.includes("hey jarvis") || lower.includes("hi")) {
      return "Hello. I'm JARVIS, your voice-first assistant. Systems are online and ready.";
    }
    if (lower.includes("time")) {
      return `The current time is ${formatTime()}.`;
    }
    if (lower.includes("status") || lower.includes("system")) {
      return "All systems nominal. STT, TTS, wake word, and policy gate are operational.";
    }
    if (lower.includes("help")) {
      return "You can speak to me, type in the input bar, or dismiss proactive alerts from the bento grid. The kill switch halts all activity immediately.";
    }
    return `I heard: "${input}". How can I help?`;
  }

  els.inputSend.addEventListener("click", () => {
    handleUserInput(els.textInput.value);
    els.textInput.value = "";
  });

  els.textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      handleUserInput(els.textInput.value);
      els.textInput.value = "";
    }
  });

  /* ------------------------------------------------------------------ */
  /* Event Wiring                                                       */
  /* ------------------------------------------------------------------ */
  els.micBtn.addEventListener("click", toggleMic);
  els.killSwitch.addEventListener("click", toggleKill);
  els.killSwitchBig.addEventListener("click", toggleKill);

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl/Cmd + K = kill switch toggle
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      toggleKill();
    }
    // Escape = dismiss popup / close overlays
    if (e.key === "Escape") {
      if (state.alertOpen || els.popupOverlay.style.display === "flex") {
        if (currentPopupId) dismissAlert(currentPopupId);
        hidePopup();
      }
    }
    // M = toggle mic (when not in an input)
    if (e.key.toLowerCase() === "m" && !els.textInput.matches(":focus, :focus-within")) {
      e.preventDefault();
      toggleMic();
    }
  });

  // Click outside conversation to focus input (accessibility nicety)
  els.textInput.addEventListener("focus", () => {
    els.textInput.parentElement.classList.add("focused");
  });
  els.textInput.addEventListener("blur", () => {
    els.textInput.parentElement.classList.remove("focused");
  });

  /* ------------------------------------------------------------------ */
  /* Initialization                                                     */
  /* ------------------------------------------------------------------ */
  function init() {
    // Detect reduced motion preference
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      els.body.setAttribute("data-prefers-reduced-motion", "true");
    }

    // Start mic level meter (simulated)
    startMeter();

    // Audio context resume on first user gesture (browser requirement)
    const resumeAudio = () => {
      const ctx = ensureAudio();
      if (ctx && ctx.state === "suspended") ctx.resume();
      state.audioAvailable = !!ctx;
    };
    document.addEventListener("click", resumeAudio, { once: true });
    document.addEventListener("keydown", resumeAudio, { once: true });

    // Seed with a couple of sample alerts to demonstrate the bento grid
    // (These are demo data — in production these come from the proactive engine)
    setTimeout(() => {
      addAlert({
        id: "alert-1",
        level: "L2",
        title: "Calendar reminder",
        body: "Team sync in 10 minutes — Conference Room B.",
        source: "calendar",
      });
    }, 2500);

    setTimeout(() => {
      addAlert({
        id: "alert-2",
        level: "L3",
        title: "Security update available",
        body: "Critical OS update detected. Install now?",
        source: "update-guardian",
      });
    }, 5000);

    audit("system.init", "JARVIS UI initialized — glassmorphism shell ready.");
    toast("JARVIS ready. Say 'Hey Jarvis' or click the mic.", "success", 4000);
  }

  // Boot when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  /* ------------------------------------------------------------------ */
  /* Public API (exposed for integration with the Python backend)       */
  /* ------------------------------------------------------------------ */
  window.JARVIS_UI = {
    setUiState,
    addMessage,
    addAlert,
    dismissAlert,
    dismissAllAlerts,
    showPopup,
    hidePopup,
    toast,
    speakText,
    setTyping,
    toggleMic,
    toggleKill,
    getState: () => ({ ...state }),
    audit,
  };
})();
