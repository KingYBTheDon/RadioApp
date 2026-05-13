// ===== State =====
let progressMs = 0;
let durationMs = 0;
let isPlaying = false;
let progressInterval = null;

// ===== DOM refs =====
const loginScreen    = document.getElementById("login-screen");
const playerScreen   = document.getElementById("player-screen");
const displayName    = document.getElementById("display-name");
const albumArt       = document.getElementById("album-art");
const albumPlaceholder = document.getElementById("album-art-placeholder");
const trackName      = document.getElementById("track-name");
const artistName     = document.getElementById("artist-name");
const albumName      = document.getElementById("album-name");
const progressBar    = document.getElementById("progress-bar");
const progressTime   = document.getElementById("progress-time");
const durationTime   = document.getElementById("duration-time");
const btnPlayPause   = document.getElementById("btn-play-pause");
const btnSkip        = document.getElementById("btn-skip");
const btnPrev        = document.getElementById("btn-prev");
const btnStartRadio  = document.getElementById("btn-start-radio");
const btnVibe        = document.getElementById("btn-vibe");
const vibeOverlay    = document.getElementById("vibe-overlay");
const vibeClose      = document.getElementById("vibe-close");
const vibeInput      = document.getElementById("vibe-input");
const vibeSubmit     = document.getElementById("vibe-submit");
const vibeResult     = document.getElementById("vibe-result");
const queueList      = document.getElementById("queue-list");
const statusMsg      = document.getElementById("status-msg");
const deviceToast    = document.getElementById("device-toast");
const contentBadge   = document.getElementById("content-badge");
const bubbleBadge    = document.getElementById("bubble-badge");

// ===== Helpers =====
function formatMs(ms) {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

function showToast(msg, duration = 3500) {
  deviceToast.textContent = msg;
  deviceToast.classList.remove("hidden");
  setTimeout(() => deviceToast.classList.add("hidden"), duration);
}

function setStatus(msg) {
  statusMsg.textContent = msg;
}

// ===== Progress bar animation =====
function startProgressTick() {
  clearInterval(progressInterval);
  if (!isPlaying) return;
  progressInterval = setInterval(() => {
    if (!isPlaying) return;
    progressMs = Math.min(progressMs + 1000, durationMs);
    updateProgressUI();
  }, 1000);
}

function updateProgressUI() {
  const pct = durationMs > 0 ? (progressMs / durationMs) * 100 : 0;
  progressBar.style.width = `${pct}%`;
  progressTime.textContent = formatMs(progressMs);
  durationTime.textContent = formatMs(durationMs);
}

// ===== Update now-playing UI =====
function applyTrack(data) {
  if (data.nothing_playing) {
    trackName.textContent = "Nothing playing";
    artistName.textContent = "Start Radio or open Spotify";
    albumName.textContent = "";
    albumArt.style.display = "none";
    albumPlaceholder.style.display = "flex";
    progressMs = 0; durationMs = 0;
    isPlaying = false;
    clearInterval(progressInterval);
    updateProgressUI();
    btnPlayPause.innerHTML = "&#9654;";
    return;
  }

  trackName.textContent  = data.name   || "—";
  artistName.textContent = data.artist || "—";
  albumName.textContent  = data.album  || "";

  if (data.image) {
    albumArt.src = data.image;
    albumArt.style.display = "block";
    albumPlaceholder.style.display = "none";
  } else {
    albumArt.style.display = "none";
    albumPlaceholder.style.display = "flex";
  }

  // Content type badge
  if (data.type === "episode") {
    const isNews = data.artist && (data.artist.includes("News") || data.artist.includes("NPR") || data.artist.includes("BBC") || data.artist.includes("Daily"));
    contentBadge.textContent = isNews ? "📰 News" : "🎙️ Podcast";
    contentBadge.className = "content-badge " + (isNews ? "news" : "podcast");
    contentBadge.classList.remove("hidden");
  } else {
    contentBadge.textContent = "🎵 Music";
    contentBadge.className = "content-badge";
    contentBadge.classList.remove("hidden");
  }

  progressMs = data.progress_ms || 0;
  durationMs = data.duration_ms || 0;
  isPlaying  = data.is_playing  || false;
  updateProgressUI();
  startProgressTick();

  btnPlayPause.innerHTML = isPlaying ? "&#9646;&#9646;" : "&#9654;";
}

// ===== Fetch now playing =====
async function pollNowPlaying() {
  try {
    const res = await fetch("/player/now-playing");
    if (res.status === 401) return; // not logged in, handled separately
    const data = await res.json();
    if (data.error === "no_device") return; // silently ignore when no device
    applyTrack(data);
  } catch (_) {}
}

// ===== Fetch queue =====
async function pollQueue() {
  try {
    const res = await fetch("/player/queue");
    if (!res.ok) return;
    const items = await res.json();
    queueList.innerHTML = "";
    if (!items.length) {
      queueList.innerHTML = '<li class="queue-empty">Queue is empty</li>';
      return;
    }
    items.forEach(item => {
      const li = document.createElement("li");
      li.className = "queue-item";
      const thumb = item.image
        ? `<img class="queue-thumb" src="${item.image}" alt="" />`
        : `<div class="queue-thumb-placeholder">♫</div>`;
      li.innerHTML = `
        ${thumb}
        <div class="queue-meta">
          <div class="queue-track">${item.name}</div>
          <div class="queue-artist">${item.artist}</div>
        </div>`;
      queueList.appendChild(li);
    });
  } catch (_) {}
}

// ===== Button handlers =====
btnPlayPause.addEventListener("click", async () => {
  try {
    const res = await fetch("/player/play-pause", { method: "POST" });
    const data = await res.json();
    if (data.error === "no_device" || data.message) {
      showToast(data.message || "Open Spotify on any device first.");
      return;
    }
    isPlaying = data.is_playing;
    btnPlayPause.innerHTML = isPlaying ? "&#9646;&#9646;" : "&#9654;";
    startProgressTick();
  } catch (_) {}
});

btnSkip.addEventListener("click", async () => {
  try {
    const res = await fetch("/player/skip", { method: "POST" });
    const data = await res.json();
    if (data.message) { showToast(data.message); return; }
    setTimeout(pollNowPlaying, 600);
    setTimeout(pollQueue, 800);
  } catch (_) {}
});

btnPrev.addEventListener("click", async () => {
  try {
    const res = await fetch("/player/previous", { method: "POST" });
    const data = await res.json();
    if (data.message) { showToast(data.message); return; }
    setTimeout(pollNowPlaying, 600);
  } catch (_) {}
});

btnStartRadio.addEventListener("click", async () => {
  setStatus("Starting radio...");
  btnStartRadio.disabled = true;
  try {
    const res = await fetch("/player/start-radio", { method: "POST" });
    const data = await res.json();
    if (data.error || data.message) {
      showToast(data.message || "Could not start radio.");
      setStatus("");
    } else {
      const bubble = data.bubble ? `${data.bubble.icon} ${data.bubble.name}` : "";
      bubbleBadge.textContent = bubble;
      bubbleBadge.classList.toggle("hidden", !bubble);

      let msg = `Radio started`;
      if (data.podcast) msg += ` · 🎙️ ${data.podcast.show}`;
      if (data.news)    msg += ` · 📰 ${data.news.show}`;
      setStatus(msg);
      setTimeout(() => setStatus(""), 6000);
      setTimeout(pollNowPlaying, 800);
      setTimeout(pollQueue, 1200);
    }
  } catch (_) {
    setStatus("");
  }
  btnStartRadio.disabled = false;
});

// ===== Vibe modal =====
btnVibe.addEventListener("click", () => {
  vibeOverlay.classList.remove("hidden");
  vibeInput.focus();
  vibeResult.classList.add("hidden");
  vibeResult.textContent = "";
});

vibeClose.addEventListener("click", () => vibeOverlay.classList.add("hidden"));
vibeOverlay.addEventListener("click", (e) => { if (e.target === vibeOverlay) vibeOverlay.classList.add("hidden"); });

vibeInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); vibeSubmit.click(); }
});

vibeSubmit.addEventListener("click", async () => {
  const vibe = vibeInput.value.trim();
  if (!vibe) return;

  vibeSubmit.disabled = true;
  vibeSubmit.textContent = "Finding your vibe...";
  vibeResult.classList.add("hidden");

  try {
    const res = await fetch("/player/vibe-radio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vibe }),
    });
    const data = await res.json();

    if (data.error || !data.started) {
      vibeResult.textContent = "⚠️ " + (data.message || "Something went wrong.");
      vibeResult.style.color = "#f87171";
      vibeResult.classList.remove("hidden");
    } else {
      const plNames = (data.matched_playlists || []).join(", ");
      let msg = `✨ ${data.mood_label}\n\nPlaying from: ${plNames}`;
      if (data.podcast) msg += `\n🎙️ Podcast up soon: ${data.podcast.show}`;
      if (data.news)    msg += `\n📰 News up soon: ${data.news.show}`;
      vibeResult.style.color = "#c084fc";
      vibeResult.textContent = msg;
      vibeResult.classList.remove("hidden");

      bubbleBadge.textContent = `✨ ${data.mood_label}`;
      bubbleBadge.classList.remove("hidden");

      setTimeout(() => {
        vibeOverlay.classList.add("hidden");
        vibeInput.value = "";
        pollNowPlaying();
        pollQueue();
      }, 2800);
    }
  } catch (_) {
    vibeResult.textContent = "⚠️ Could not connect. Is Spotify open on a device?";
    vibeResult.style.color = "#f87171";
    vibeResult.classList.remove("hidden");
  }

  vibeSubmit.disabled = false;
  vibeSubmit.textContent = "Let's go →";
});

// ===== Auth check on load =====
async function init() {
  try {
    const res = await fetch("/auth/status");
    const data = await res.json();

    if (data.logged_in) {
      loginScreen.classList.add("hidden");
      playerScreen.classList.remove("hidden");
      displayName.textContent = data.display_name || "";

      // initial data load
      await pollNowPlaying();
      await pollQueue();

      // keep refreshing
      setInterval(pollNowPlaying, 5000);
      setInterval(pollQueue, 10000);
    } else {
      loginScreen.classList.remove("hidden");
      playerScreen.classList.add("hidden");
    }
  } catch (_) {
    loginScreen.classList.remove("hidden");
  }
}

init();
