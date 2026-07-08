// Ground Truth Daemon — background script
// Watches active tab, classifies behavior, logs time per category.
// Sends to Flask backend every 60 seconds.

const DEFAULT_API_BASE = "http://localhost:5000";
const TICK_SECONDS_DEFAULT = 5;
const FLUSH_INTERVAL = 60;

let apiBase = DEFAULT_API_BASE;
let tickSeconds = TICK_SECONDS_DEFAULT;
let apiToken = "";

// ---- classification rules ----
// returns {category, ok: bool, note: string, togglGoal: string|null, ambiguous: bool}
function classifyTab(url) {
  if (!url) return null;
  try { url = new URL(url); } catch { return null; }
  const h = url.hostname.replace(/^www\./, "");
  const p = url.pathname;
  const s = url.searchParams;

  // YouTube — the only platform with nuance (desktop only)
  if (h === "youtube.com" || h === "m.youtube.com") {
    // Shorts = always tax, no exceptions
    if (p.startsWith("/shorts/") || p.includes("/shorts"))
      return { category: "youtube", ok: false, note: "shorts", togglGoal: null };
    // Feed/homepage = always tax
    if (p.startsWith("/feed/") || p === "/")
      return { category: "youtube", ok: false, note: "feed", togglGoal: null };
    // Playlist page = ok
    if (p.startsWith("/playlist"))
      return { category: "youtube_playlist", ok: true, note: "playlist page", togglGoal: null };
    // Watch page with playlist = ok
    if (p.startsWith("/watch") && s.get("list"))
      return { category: "youtube_playlist", ok: true, note: "watch+playlist", togglGoal: null };
    // Watch page without playlist = ambiguous, default tax
    // (Toggl timer check happens in checkActiveTab, overrides this)
    if (p.startsWith("/watch"))
      return { category: "youtube", ok: false, note: "watch (no playlist)", togglGoal: null, ambiguous: true };
    return { category: "youtube", ok: false, note: "other", togglGoal: null };
  }

  // X / Twitter — ALL = tax (user confirmed)
  if (h === "x.com" || h === "twitter.com") {
    return { category: "social_media", ok: false, note: "X (all = tax)", togglGoal: null };
  }

  // Instagram — reels = BAD, DMs = meh, everything else = tax
  if (h === "instagram.com") {
    if (p.includes("/reels/") || p.includes("/reel/"))
      return { category: "social_media", ok: false, note: "reels", togglGoal: null };
    if (p.startsWith("/direct/"))
      return { category: "social_media", ok: true, note: "DMs", togglGoal: null };
    return { category: "social_media", ok: false, note: "feed", togglGoal: null };
  }

  // TikTok — all = tax
  if (h === "tiktok.com") return { category: "social_media", ok: false, note: "tiktok", togglGoal: null };

  // Reddit — all = tax
  if (h === "reddit.com") return { category: "social_media", ok: false, note: "reddit", togglGoal: null };

  // Porn sites — all = tax
  const PORN_DOMAINS = ["pornhub.com", "xvideos.com", "xnxx.com", "redtube.com",
    "onlyfans.com", "spankbang.com", "xhamster.com", "youporn.com",
    "chaturbate.com", "brazzers.com", "nhentai.net", "eporner.com"];
  if (PORN_DOMAINS.includes(h)) return { category: "porn", ok: false, note: "porn site", togglGoal: null };

  // Unknown — not tracked
  return null;
}

// ---- Togtl timer check ----
// Asks our Flask backend if a Toggl timer is running.
// If it is, returns the goal category (e.g. "learning", "research").
// This is the ground truth: if ur learning timer is running on YouTube,
// the time goes to learning, not doom scroll.
let cachedTimer = null;
let lastTimerCheck = 0;
const TIMER_CACHE_MS = 10000; // cache for 10s to avoid hammering the API

async function getActiveTogglGoal() {
  const now = Date.now();
  if (now - lastTimerCheck < TIMER_CACHE_MS) return cachedTimer;

  lastTimerCheck = now;
  try {
    const resp = await fetch(`${apiBase}/api/current?token=${encodeURIComponent(apiToken)}`);
    if (!resp.ok) { cachedTimer = null; return null; }
    const data = await resp.json();
    if (data.running && data.categories && data.categories.length > 0) {
      cachedTimer = data.categories[0]; // primary goal
      return cachedTimer;
    }
    cachedTimer = null;
    return null;
  } catch (e) {
    console.error("[GT Daemon] timer check error:", e);
    cachedTimer = null;
    return null;
  }
}

// ---- state ----
let currentSession = null;  // {category, ok, note, startTime}
let sessionLog = [];        // [{date, category, seconds, source}]

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// ---- session tracking ----
async function checkActiveTab() {
  try {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) { endSession(); return; }

    const result = classifyTab(tab.url);
    if (!result) { endSession(); return; }

    // ---- THE KILLER FEATURE: Toggl timer override ----
    // Before logging as tax, check if a Toggl timer is running.
    // If learning timer is running while on YouTube → it's learning, not doom scroll.
    // The Toggl timer is the ground truth of what you're actually doing.
    const togglGoal = await getActiveTogglGoal();
    if (togglGoal && !result.ok) {
      const overridden = { ...result, category: togglGoal, ok: true, note: `${result.note} → ${togglGoal} (timer)` };
      if (currentSession && currentSession.category === overridden.category) return;
      endSession();
      currentSession = { ...overridden, startTime: Date.now() };
      return;
    }

    // session continues if same category
    if (currentSession && currentSession.category === result.category) return;

    // new session
    endSession();
    currentSession = { ...result, startTime: Date.now() };
  } catch (e) {
    console.error("[GT Daemon] tab check error:", e);
  }
}

function endSession() {
  if (!currentSession) return;
  const elapsed = Math.round((Date.now() - currentSession.startTime) / 1000);
  if (elapsed >= 1) {
    sessionLog.push({
      date: todayStr(),
      category: currentSession.category,
      seconds: elapsed,
      source: "extension",
    });
    console.log(`[GT Daemon] ${currentSession.category}: ${elapsed}s (${currentSession.note})`);
  }
  currentSession = null;
}

// ---- flush to backend ----
async function flushToBackend() {
  if (sessionLog.length === 0) {
    endSession();
    if (sessionLog.length === 0) return;
  }
  const merged = {};
  for (const entry of sessionLog) {
    const key = `${entry.date}|${entry.category}`;
    merged[key] = (merged[key] || 0) + entry.seconds;
  }
  const payload = Object.entries(merged).map(([key, seconds]) => {
    const [date, category] = key.split("|");
    return { date, category, seconds, source: "extension" };
  });
  try {
    const resp = await fetch(`${apiBase}/api/screen-time?token=${encodeURIComponent(apiToken)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: payload }),
    });
    if (resp.ok) {
      console.log(`[GT Daemon] flushed ${payload.length} entries to backend`);
      sessionLog = [];
    } else {
      console.error(`[GT Daemon] flush failed: HTTP ${resp.status}`);
    }
  } catch (e) {
    console.error("[GT Daemon] flush error:", e);
  }
}

// ---- alarms ----
browser.alarms.create("tick", { periodInMinutes: tickSeconds / 60 });
browser.alarms.create("flush", { periodInMinutes: FLUSH_INTERVAL / 60 });

// ---- load settings ----
browser.storage.local.get(["apiBase", "pollInterval", "apiToken"]).then(r => {
  if (r.apiBase) apiBase = r.apiBase;
  if (r.pollInterval) tickSeconds = r.pollInterval;
  if (r.apiToken) apiToken = r.apiToken;
});

// ---- message handler (popup asks for today's log) ----
browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "getLog") {
    const log = sessionLog.filter(e => e.date === msg.date);
    sendResponse({ log });
  }
});

browser.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "tick") checkActiveTab();
  if (alarm.name === "flush") flushToBackend();
});

browser.runtime.onSuspend.addListener(() => {
  endSession();
  flushToBackend();
});

console.log("[Ground Truth Daemon] loaded. Watching your tabs...");