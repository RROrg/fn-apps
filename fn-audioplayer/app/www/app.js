import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

let playlist = [];
let currentIndex = -1;
let currentLyrics = [];
let activeLyricIndex = -1;
let browserCurrentDir = "/var/apps/fn-audioplayer/tmp";
let browserSelectedPaths = new Set();
let outputMode = "client";
let serverDevices = [];
let selectedServerDevice = "";
let serverPollTimer = null;
let sortMode = "seq";
let shuffleOrder = [];
let lyricsAlign = "left";
let clientRecoverTimer = null;
let clientRecoverAttempts = 0;
let clientRecovering = false;
let lastClientRecoverAt = 0;

const I18N = {
  "zh-CN": {
    appTitle: "音频播放器",
    waitingToPlay: "等待播放",
    selectAudioToStart: "选择音频文件开始",
    playlist: "播放列表",
    lyrics: "歌词",
    noTracks: "暂无曲目，请添加音频文件",
    noLyrics: "暂无歌词",
    addLocal: "本地上传",
    addFromNas: "NAS浏览",
    browseFiles: "浏览文件",
    loading: "加载中...",
    cancel: "取消",
    addSelected: "添加选中",
    addedToList: "已添加到列表: {name}",
    nowPlaying: "正在播放: {name}",
    addedCount: "已添加 {count} 首音乐",
    pleaseAddAudio: "请先添加音频文件",
    parentDir: "上级目录",
    emptyDir: "此目录无音频文件或子目录",
    permissionDenied: "无权限访问此目录",
    loadFailed: "加载失败",
    outputDevice: "输出设备",
    clientMode: "客户端",
    serverMode: "服务器",
    soundCard: "声卡",
    noDevices: "未检测到音频设备",
    serverPlayError: "服务器播放失败",
    clientBrowser: "客户端（浏览器）",
    serverSoundCard: "服务器端（声卡）",
    sortSeq: "顺序播放",
    sortSingle: "单曲循环",
    sortLoop: "列表循环",
    sortShuffle: "随机播放",
    alignLeft: "靠左",
    alignCenter: "居中",
    alignRight: "靠右",
    playbackSetting: "播放设置",
    prev: "上一首",
    play: "播放",
    next: "下一首",
    volume: "音量",
    sortModeTitle: "播放顺序",
    lyricsAlignTitle: "歌词对齐",
    selectOutputDevice: "选择输出设备",
    selectAudioFile: "选择音频文件",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
  },
  "en-US": {
    appTitle: "Audio Player",
    waitingToPlay: "Waiting to play",
    selectAudioToStart: "Select audio file to start",
    playlist: "Playlist",
    lyrics: "Lyrics",
    noTracks: "No tracks, please add audio files",
    noLyrics: "No lyrics",
    addLocal: "Upload",
    addFromNas: "Browse NAS",
    browseFiles: "Browse Files",
    loading: "Loading...",
    cancel: "Cancel",
    addSelected: "Add Selected",
    addedToList: "Added: {name}",
    nowPlaying: "Now playing: {name}",
    addedCount: "Added {count} track(s)",
    pleaseAddAudio: "Please add audio files first",
    parentDir: "Parent directory",
    emptyDir: "No audio files or subdirectories",
    permissionDenied: "Permission denied",
    loadFailed: "Load failed",
    outputDevice: "Output Device",
    clientMode: "Client",
    serverMode: "Server",
    soundCard: "Sound Card",
    noDevices: "No audio devices detected",
    serverPlayError: "Server playback failed",
    clientBrowser: "Client (Browser)",
    serverSoundCard: "Server (Sound Card)",
    sortSeq: "Sequential",
    sortSingle: "Repeat One",
    sortLoop: "Repeat All",
    sortShuffle: "Shuffle",
    alignLeft: "Left",
    alignCenter: "Center",
    alignRight: "Right",
    playbackSetting: "Settings",
    prev: "Previous",
    play: "Play",
    next: "Next",
    volume: "Volume",
    sortModeTitle: "Playback Order",
    lyricsAlignTitle: "Lyrics Align",
    selectOutputDevice: "Select output device",
    selectAudioFile: "Select audio file",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
  },
};

const state = {
  language: "zh-CN",
  theme: "light",
};

function t(key, params) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  let text = messages[key] || I18N["zh-CN"][key] || key;
  if (params) {
    Object.keys(params).forEach((k) => {
      text = text.replace(new RegExp("\\{" + k + "\\}", "g"), params[k]);
    });
  }
  return text;
}

function applyLanguage() {
  const language = String(platformConfig.language || "").replace("_", "-");
  const resolved = language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
  state.language = resolved;
  document.documentElement.lang = resolved;
  return resolved;
}

function openAbout() {
  document.getElementById("aboutOverlay").classList.add("active");
}

function closeAbout() {
  document.getElementById("aboutOverlay").classList.remove("active");
}

document.addEventListener("click", function (e) {
  if (e.target.id === "aboutOverlay") {
    closeAbout();
  }
});

function applyTheme() {
  // fnOS 宿主可能返回 { theme: "dark" } 对象，先解包再规范化
  const value = platformConfig.theme;
  const v =
    value && typeof value === "object" && "theme" in value
      ? value.theme
      : value;
  const theme = String(v || "").toLowerCase() === "dark" ? "dark" : "light";
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  document.body.dataset.theme = theme;
  return theme;
}

function applyPreferences({ rerender = false } = {}) {
  applyLanguage();
  applyTheme();
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.title = t("appTitle");
  if (sdk.setTitle) {
    sdk.setTitle(t("appTitle")).catch(() => {});
  }
  if (rerender) {
    updatePlaylistUI();
    renderLyrics();
  }
}

const channel = new BroadcastChannel("fn-audioplayer");
let isPrimaryWindow = true;
let pendingFilePath = null;

channel.onmessage = function (e) {
  const msg = e.data;
  if (msg && msg.type === "ping") {
    channel.postMessage({ type: "pong" });
  }
  if (msg && msg.type === "open-file" && msg.path) {
    addFileFromPath(msg.path);
    channel.postMessage({ type: "pong" });
  }
  if (msg && msg.type === "pong") {
    isPrimaryWindow = false;
  }
};

function claimPrimary() {
  isPrimaryWindow = true;
}

const audioPlayer = document.getElementById("audioPlayer");
const playPauseBtn = document.getElementById("playPauseBtn");
const playIcon = document.getElementById("playIcon");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const trackTitle = document.getElementById("trackTitle");
const trackSubtitle = document.getElementById("trackSubtitle");
const currentTimeSpan = document.getElementById("currentTime");
const durationSpan = document.getElementById("duration");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");
const volumeSlider = document.getElementById("volumeSlider");
const volumeValue = document.getElementById("volumeValue");
const fileInput = document.getElementById("fileInput");
const playlistItems = document.getElementById("playlistItems");
const disc = document.getElementById("disc");
const discCover = document.getElementById("discCover");
const discLabel = document.getElementById("discLabel");
const toast = document.getElementById("toast");
const lyricsContainer = document.getElementById("lyricsContainer");
const tabPlaylist = document.getElementById("tabPlaylist");
const tabLyrics = document.getElementById("tabLyrics");
const panelPlaylist = document.getElementById("panelPlaylist");
const panelLyrics = document.getElementById("panelLyrics");

const PAUSE_ICON = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
const PLAY_ICON = '<path d="M8 5v14l11-7z"/>';
const FORMAT_LABELS = {
  mp3: "MP3",
  wav: "WAV",
  flac: "FLAC",
  ogg: "OGG",
  m4a: "M4A",
  aac: "AAC",
  wma: "WMA",
  ape: "APE",
};

async function setOutputMode(mode) {
  const prevMode = outputMode;
  outputMode = mode;
  document
    .getElementById("modeClientBtn")
    .classList.toggle("active", mode === "client");
  document
    .getElementById("modeServerBtn")
    .classList.toggle("active", mode === "server");
  document.getElementById("serverDeviceSelect").style.display =
    mode === "server" ? "block" : "none";

  if (mode === "server") {
    loadServerDevices();
  }

  if (prevMode !== mode && playlist.length > 0 && currentIndex >= 0) {
    const track = playlist[currentIndex];
    let position = 0;
    if (prevMode === "client") {
      position = audioPlayer.currentTime || 0;
      audioPlayer.pause();
    } else {
      try {
        const resp = await fetch(API_ENDPOINT + "/output/status");
        const status = await resp.json();
        if (
          status &&
          (status.state === "playing" || status.state === "paused")
        ) {
          position = status.position || 0;
        }
      } catch (e) {}
      fetch(API_ENDPOINT + "/output/stop", { method: "POST" }).catch(() => {});
      stopServerPoll();
    }
    if (track.isServerFile && position > 0) {
      if (mode === "server") {
        serverPlay(track.path, position);
      } else {
        setClientTrackSource(track, position, true);
      }
    }
  }

  if (mode === "client") {
    stopServerPoll();
  }

  try {
    localStorage.setItem("fn-audioplayer-output-mode", mode);
  } catch (e) {}
}

function loadServerDevices() {
  fetch(API_ENDPOINT + "/output/devices")
    .then((r) => r.json())
    .then((data) => {
      serverDevices = data.devices || [];
      const select = document.getElementById("serverDeviceSelect");
      if (serverDevices.length === 0) {
        select.innerHTML = '<option value="">' + t("noDevices") + "</option>";
        return;
      }
      select.innerHTML = serverDevices
        .map(
          (d) =>
            '<option value="' +
            escapeHtml(d.id) +
            '">' +
            escapeHtml(d.name || d.id) +
            "</option>",
        )
        .join("");
      if (
        selectedServerDevice &&
        serverDevices.some((d) => d.id === selectedServerDevice)
      ) {
        select.value = selectedServerDevice;
      } else if (serverDevices.length > 0) {
        selectedServerDevice = serverDevices[0].id;
        select.value = selectedServerDevice;
      }
    })
    .catch(() => {
      document.getElementById("serverDeviceSelect").innerHTML =
        '<option value="">' + t("noDevices") + "</option>";
    });
}

function onServerDeviceChange() {
  selectedServerDevice = document.getElementById("serverDeviceSelect").value;
  try {
    localStorage.setItem("fn-audioplayer-server-device", selectedServerDevice);
  } catch (e) {}
  if (outputMode === "server" && playlist.length > 0 && currentIndex >= 0) {
    const track = playlist[currentIndex];
    if (track.isServerFile) {
      let position = 0;
      fetch(API_ENDPOINT + "/output/status")
        .then((r) => r.json())
        .then((status) => {
          position = status.position || 0;
          serverPlay(track.path, position);
        })
        .catch(() => {
          serverPlay(track.path, 0);
        });
    }
  }
}

function serverPlay(filePath, position) {
  fetch(API_ENDPOINT + "/output/play", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file: filePath,
      sink: selectedServerDevice,
      position: position || 0,
    }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        showToast(t("serverPlayError") + ": " + data.error, "error");
      } else {
        startServerPoll();
      }
    })
    .catch(() => {
      showToast(t("serverPlayError"), "error");
    });
}

function startServerPoll() {
  stopServerPoll();
  serverPollTimer = setInterval(pollServerStatus, 1000);
}

function stopServerPoll() {
  if (serverPollTimer) {
    clearInterval(serverPollTimer);
    serverPollTimer = null;
  }
}

function pollServerStatus() {
  fetch(API_ENDPOINT + "/output/status")
    .then((r) => r.json())
    .then((status) => {
      if (status.state === "playing") {
        const pos = status.position || 0;
        const dur = status.duration || 0;
        if (dur > 0) {
          progressFill.style.width = (pos / dur) * 100 + "%";
        }
        currentTimeSpan.textContent = formatTime(pos);
        if (dur > 0) {
          durationSpan.textContent = formatTime(dur);
        }
        playIcon.innerHTML = PAUSE_ICON;
        disc.classList.add("spinning");
        updateLyrics(pos);
      } else if (status.state === "paused") {
        playIcon.innerHTML = PLAY_ICON;
        disc.classList.remove("spinning");
      } else if (status.state === "ended") {
        stopServerPoll();
        if (playlist.length > 0) {
          nextTrack();
        }
      } else {
        playIcon.innerHTML = PLAY_ICON;
        disc.classList.remove("spinning");
        stopServerPoll();
      }
    })
    .catch(() => {});
}

function loadOutputMode() {
  try {
    const saved = localStorage.getItem("fn-audioplayer-output-mode");
    if (saved === "server") {
      outputMode = "server";
    }
    const savedDevice = localStorage.getItem("fn-audioplayer-server-device");
    if (savedDevice) selectedServerDevice = savedDevice;
  } catch (e) {}
}

playPauseBtn.addEventListener("click", togglePlayPause);
prevBtn.addEventListener("click", previousTrack);
nextBtn.addEventListener("click", nextTrack);
audioPlayer.addEventListener("timeupdate", updateProgress);
audioPlayer.addEventListener("loadedmetadata", updateDuration);
audioPlayer.addEventListener("ended", () => {
  resetClientRecovery();
  nextTrack();
});
audioPlayer.addEventListener("play", () => {
  playIcon.innerHTML = PAUSE_ICON;
  disc.classList.add("spinning");
});
audioPlayer.addEventListener("pause", () => {
  if (!clientRecovering) {
    playIcon.innerHTML = PLAY_ICON;
    disc.classList.remove("spinning");
  }
});
audioPlayer.addEventListener("waiting", () =>
  scheduleClientRecovery(3500, false),
);
audioPlayer.addEventListener("stalled", () =>
  scheduleClientRecovery(1200, false),
);
audioPlayer.addEventListener("error", () => scheduleClientRecovery(200, true));
progressBar.addEventListener("click", seek);
volumeSlider.addEventListener("input", updateVolume);
fileInput.addEventListener("change", handleFileSelect);

tabPlaylist.addEventListener("click", () => switchTab("playlist"));
tabLyrics.addEventListener("click", () => switchTab("lyrics"));

function switchTab(tab) {
  tabPlaylist.classList.toggle("active", tab === "playlist");
  tabLyrics.classList.toggle("active", tab === "lyrics");
  panelPlaylist.classList.toggle("active", tab === "playlist");
  panelLyrics.classList.toggle("active", tab === "lyrics");
}

function togglePlayPause() {
  if (playlist.length === 0) {
    showToast(t("pleaseAddAudio"), "error");
    return;
  }
  if (outputMode === "server") {
    if (currentIndex < 0 || !playlist[currentIndex].isServerFile) {
      showToast(t("pleaseAddAudio"), "error");
      return;
    }
    fetch(API_ENDPOINT + "/output/status")
      .then((r) => r.json())
      .then((status) => {
        if (status.state === "playing") {
          fetch(API_ENDPOINT + "/output/pause", { method: "POST" }).catch(
            () => {},
          );
          playIcon.innerHTML = PLAY_ICON;
          disc.classList.remove("spinning");
        } else if (status.state === "paused") {
          fetch(API_ENDPOINT + "/output/resume", { method: "POST" }).catch(
            () => {},
          );
          playIcon.innerHTML = PAUSE_ICON;
          disc.classList.add("spinning");
          startServerPoll();
        } else {
          const track = playlist[currentIndex];
          serverPlay(track.path, 0);
        }
      })
      .catch(() => {});
  } else {
    audioPlayer.paused ? audioPlayer.play() : audioPlayer.pause();
  }
}

function previousTrack() {
  if (playlist.length === 0) return;
  if (outputMode === "server") {
    fetch(API_ENDPOINT + "/output/stop", { method: "POST" }).catch(() => {});
    stopServerPoll();
  }
  let idx = getPrevIndex();
  currentIndex = idx;
  loadTrack(currentIndex);
}

function nextTrack() {
  if (playlist.length === 0) return;
  if (outputMode === "server") {
    fetch(API_ENDPOINT + "/output/stop", { method: "POST" }).catch(() => {});
    stopServerPoll();
  }
  let idx = getNextIndex();
  if (idx < 0) return;
  currentIndex = idx;
  loadTrack(currentIndex);
}

function getNextIndex() {
  if (playlist.length === 0) return -1;
  if (sortMode === "single") {
    return currentIndex;
  } else if (sortMode === "shuffle") {
    let pos = shuffleOrder.indexOf(currentIndex);
    if (pos < 0 || pos >= shuffleOrder.length - 1) {
      regenerateShuffle();
      return shuffleOrder[0];
    }
    return shuffleOrder[pos + 1];
  } else if (sortMode === "loop") {
    return (currentIndex + 1) % playlist.length;
  }
  return currentIndex + 1 < playlist.length ? currentIndex + 1 : -1;
}

function getPrevIndex() {
  if (playlist.length === 0) return -1;
  if (sortMode === "single") {
    return currentIndex;
  } else if (sortMode === "shuffle") {
    let pos = shuffleOrder.indexOf(currentIndex);
    if (pos < 0) {
      regenerateShuffle();
      return shuffleOrder[shuffleOrder.length - 1];
    }
    if (pos === 0) {
      regenerateShuffle();
      return shuffleOrder[shuffleOrder.length - 1];
    }
    return shuffleOrder[pos - 1];
  } else if (sortMode === "loop") {
    return (currentIndex - 1 + playlist.length) % playlist.length;
  }
  return currentIndex - 1 >= 0 ? currentIndex - 1 : 0;
}

function regenerateShuffle() {
  shuffleOrder = playlist.map((_, i) => i);
  for (let i = shuffleOrder.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffleOrder[i], shuffleOrder[j]] = [shuffleOrder[j], shuffleOrder[i]];
  }
  if (shuffleOrder.length > 1 && currentIndex >= 0) {
    const pos = shuffleOrder.indexOf(currentIndex);
    if (pos === 0) {
      const swapWith =
        1 + Math.floor(Math.random() * (shuffleOrder.length - 1));
      [shuffleOrder[0], shuffleOrder[swapWith]] = [
        shuffleOrder[swapWith],
        shuffleOrder[0],
      ];
    }
  }
}

function setSortMode(mode) {
  sortMode = mode;
  updateSortModeUI();
  if (mode === "shuffle") {
    regenerateShuffle();
  }
  try {
    localStorage.setItem("fn-audioplayer-sort-mode", mode);
  } catch (e) {}
}

function cycleSortMode() {
  const modes = ["seq", "single", "loop", "shuffle"];
  let idx = modes.indexOf(sortMode);
  idx = (idx + 1) % modes.length;
  sortMode = modes[idx];
  if (sortMode === "shuffle") {
    regenerateShuffle();
  }
  updateSortModeUI();
  try {
    localStorage.setItem("fn-audioplayer-sort-mode", sortMode);
  } catch (e) {}
}

function loadSortMode() {
  try {
    const saved = localStorage.getItem("fn-audioplayer-sort-mode");
    if (saved && ["seq", "single", "loop", "shuffle"].includes(saved)) {
      sortMode = saved;
      if (sortMode === "shuffle") {
        regenerateShuffle();
      }
      updateSortModeUI();
    }
  } catch (e) {}
}

function updateSortModeUI() {
  const icons = {
    seq: '<path d="M3 15h6v-2H3v2zm0 4h6v-2H3v2zm0-8h6V9H3v2zm0-6v2h6V5H3zm10 0v14l7-7z"/>',
    single:
      '<path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/>',
    loop: '<path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/>',
    shuffle:
      '<path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/>',
  };
  const labels = {
    seq: "sortSeq",
    single: "sortSingle",
    loop: "sortLoop",
    shuffle: "sortShuffle",
  };
  document.getElementById("sortModeIcon").innerHTML = icons[sortMode];
  document.getElementById("sortModeText").textContent = t(labels[sortMode]);
}

function cycleLyricsAlign() {
  const modes = ["left", "center", "right"];
  let idx = modes.indexOf(lyricsAlign);
  idx = (idx + 1) % modes.length;
  lyricsAlign = modes[idx];
  updateLyricsAlignUI();
}

function updateLyricsAlignUI() {
  const icons = {
    left: '<path d="M3 3h18v2H3zm0 4h12v2H3zm0 4h18v2H3zm0 4h12v2H3z"/>',
    center: '<path d="M3 3h18v2H3zm3 4h12v2H6zm-3 4h18v2H3zm3 4h12v2H6z"/>',
    right: '<path d="M3 3h18v2H3zm6 4h12v2H9zm-6 4h18v2H3zm6 4h12v2H9z"/>',
  };
  const labels = {
    left: "alignLeft",
    center: "alignCenter",
    right: "alignRight",
  };
  document.getElementById("lyricsAlignIcon").innerHTML = icons[lyricsAlign];
  document.getElementById("lyricsAlignText").textContent = t(
    labels[lyricsAlign],
  );
  const container = document.getElementById("lyricsContainer");
  if (container) {
    container.style.textAlign = lyricsAlign;
  }
}

function loadTrack(index) {
  if (playlist.length === 0) return;
  resetClientRecovery();
  currentIndex = index;
  const track = playlist[index];
  trackTitle.textContent = track.title || track.name;
  trackSubtitle.textContent = track.artist
    ? track.artist + (track.album ? " - " + track.album : "")
    : FORMAT_LABELS[track.name.split(".").pop().toLowerCase()] || "";
  updatePlaylistUI();
  fetchLyrics(track);
  fetchCover(track);
  if (track.isServerFile && !track.title) {
    fetchMetadata(track, index, true);
  }
  if (outputMode === "server" && track.isServerFile) {
    fetch(API_ENDPOINT + "/output/stop", { method: "POST" }).catch(() => {});
    serverPlay(track.path, 0);
  } else {
    setClientTrackSource(track, 0, true);
  }
}

function getClientTrackSrc(track, cacheBust) {
  if (!track.isServerFile) return track.path;
  let url =
    API_ENDPOINT + "/audio/stream?file=" + encodeURIComponent(track.path);
  if (cacheBust) url += "&r=" + Date.now();
  return url;
}

function setClientTrackSource(track, position, autoplay, cacheBust) {
  audioPlayer.src = getClientTrackSrc(track, cacheBust);
  if (position > 0) {
    const seekToPosition = function () {
      try {
        audioPlayer.currentTime = Math.max(0, position - 0.25);
      } catch (e) {}
      if (autoplay) audioPlayer.play().catch(() => {});
    };
    audioPlayer.addEventListener("loadedmetadata", seekToPosition, {
      once: true,
    });
    audioPlayer.load();
  } else if (autoplay) {
    audioPlayer.play().catch(() => {});
  }
}

function resetClientRecovery() {
  if (clientRecoverTimer) {
    clearTimeout(clientRecoverTimer);
    clientRecoverTimer = null;
  }
  clientRecoverAttempts = 0;
  clientRecovering = false;
  lastClientRecoverAt = 0;
}

function scheduleClientRecovery(delay, force) {
  if (
    outputMode === "server" ||
    currentIndex < 0 ||
    currentIndex >= playlist.length
  )
    return;
  const track = playlist[currentIndex];
  if (
    !track ||
    !track.isServerFile ||
    (!force && audioPlayer.paused) ||
    audioPlayer.ended
  )
    return;
  const position = audioPlayer.currentTime || 0;
  const duration = audioPlayer.duration || 0;
  if (duration > 0 && position >= duration - 1) return;
  if (clientRecoverAttempts >= 3) return;
  if (clientRecoverTimer) clearTimeout(clientRecoverTimer);
  clientRecoverTimer = setTimeout(function () {
    clientRecoverTimer = null;
    if ((force || !audioPlayer.paused) && !audioPlayer.ended) {
      recoverClientPlayback(position);
    }
  }, delay);
}

function recoverClientPlayback(position) {
  if (
    outputMode === "server" ||
    currentIndex < 0 ||
    currentIndex >= playlist.length
  )
    return;
  const track = playlist[currentIndex];
  if (!track || !track.isServerFile) return;
  // 若无有效续播位置（错误后 currentTime 已归零）且已自动恢复过，则不再自动从头重播，
  // 交由用户手动控制，避免“播放几秒又从 0 开始”的无限恢复循环。
  if (position < 0.5 && clientRecoverAttempts >= 1) return;
  clientRecoverAttempts += 1;
  clientRecovering = true;
  lastClientRecoverAt = Date.now();
  const volume = audioPlayer.volume;
  audioPlayer.pause();
  audioPlayer.volume = volume;
  setClientTrackSource(track, position, true, true);
  setTimeout(function () {
    clientRecovering = false;
  }, 1500);
}

function fetchCover(track) {
  discCover.style.display = "none";
  discLabel.style.display = "flex";
  if (!track.isServerFile) return;
  const url =
    API_ENDPOINT + "/audio/cover?file=" + encodeURIComponent(track.path);
  const img = new Image();
  img.onload = function () {
    discCover.src = url;
    discCover.style.display = "block";
    discLabel.style.display = "none";
  };
  img.onerror = function () {};
  img.src = url;
}

function fetchLyrics(track) {
  currentLyrics = [];
  activeLyricIndex = -1;
  renderLyrics();
  if (!track.isServerFile) return;
  const url = API_ENDPOINT + "/lyrics?file=" + encodeURIComponent(track.path);
  fetch(url)
    .then((r) => r.json())
    .then((data) => {
      if (data.found && data.lyrics) {
        currentLyrics = parseLRC(data.lyrics);
        if (currentLyrics.length > 0) {
          switchTab("lyrics");
        }
        renderLyrics();
      }
    })
    .catch(() => {});
}

function parseLRC(lrcText) {
  const lines = lrcText.split("\n");
  const result = [];
  const timeRegex = /\[(\d{1,3}):(\d{2})(?:[.:])(\d{2,3})\]/g;
  for (const line of lines) {
    const times = [];
    let match;
    while ((match = timeRegex.exec(line)) !== null) {
      const min = parseInt(match[1], 10);
      const sec = parseInt(match[2], 10);
      let ms = parseInt(match[3], 10);
      if (match[3].length === 2) ms *= 10;
      times.push(min * 60 + sec + ms / 1000);
    }
    const text = line.replace(/\[\d{1,3}:\d{2}[.:]\d{2,3}\]/g, "").trim();
    if (!text) continue;
    for (const t of times) {
      result.push({ time: t, text: text });
    }
  }
  result.sort((a, b) => a.time - b.time);
  return result;
}

function renderLyrics() {
  if (currentLyrics.length === 0) {
    lyricsContainer.innerHTML =
      '<div class="lyrics-empty"><svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>' +
      t("noLyrics") +
      "</div>";
    return;
  }
  lyricsContainer.innerHTML = currentLyrics
    .map(
      (l, i) =>
        `<div class="lyric-line" data-index="${i}" onclick="seekToLyric(${i})">${l.text}</div>`,
    )
    .join("");
}

function seekToLyric(index) {
  if (index < 0 || index >= currentLyrics.length) return;
  if (outputMode === "server") {
    fetch(API_ENDPOINT + "/output/seek", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position: currentLyrics[index].time }),
    }).catch(() => {});
  } else {
    audioPlayer.currentTime = currentLyrics[index].time;
    if (audioPlayer.paused) audioPlayer.play().catch(() => {});
  }
}

function updateLyrics(serverPosition) {
  if (currentLyrics.length === 0) return;
  const t =
    outputMode === "server" && serverPosition !== undefined
      ? serverPosition
      : audioPlayer.currentTime;
  let newIndex = -1;
  for (let i = currentLyrics.length - 1; i >= 0; i--) {
    if (t >= currentLyrics[i].time) {
      newIndex = i;
      break;
    }
  }
  if (newIndex === activeLyricIndex) return;
  activeLyricIndex = newIndex;
  const lines = lyricsContainer.querySelectorAll(".lyric-line");
  lines.forEach((el, i) => el.classList.toggle("active", i === newIndex));
  if (newIndex >= 0 && lines[newIndex]) {
    const lineEl = lines[newIndex];
    const container = lyricsContainer;
    const lineTop = lineEl.offsetTop - container.offsetTop;
    const lineCenter =
      lineTop - container.clientHeight / 2 + lineEl.clientHeight / 2;
    container.scrollTo({ top: lineCenter, behavior: "smooth" });
  }
}

function updateProgress() {
  if (outputMode === "server") return;
  if (audioPlayer.duration) {
    const percent = (audioPlayer.currentTime / audioPlayer.duration) * 100;
    progressFill.style.width = percent + "%";
    currentTimeSpan.textContent = formatTime(audioPlayer.currentTime);
  }
  updateLyrics();
}

function updateDuration() {
  durationSpan.textContent = formatTime(audioPlayer.duration);
}

function seek(e) {
  const rect = progressBar.getBoundingClientRect();
  const percent = Math.max(
    0,
    Math.min(1, (e.clientX - rect.left) / rect.width),
  );
  if (outputMode === "server") {
    fetch(API_ENDPOINT + "/output/status")
      .then((r) => r.json())
      .then((status) => {
        const dur = status.duration || 0;
        if (dur > 0) {
          fetch(API_ENDPOINT + "/output/seek", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ position: percent * dur }),
          }).catch(() => {});
        }
      })
      .catch(() => {});
  } else {
    audioPlayer.currentTime = percent * audioPlayer.duration;
  }
}

function updateVolume() {
  const vol = volumeSlider.value;
  if (outputMode === "server") {
    audioPlayer.volume = vol / 100;
    fetch(API_ENDPOINT + "/output/volume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        volume: parseInt(vol, 10),
        sink: selectedServerDevice,
      }),
    }).catch(() => {});
  } else {
    audioPlayer.volume = vol / 100;
  }
  volumeValue.textContent = vol + "%";
  try {
    localStorage.setItem("fn-audioplayer-volume", vol);
  } catch (e) {}
}

function loadVolume() {
  try {
    const saved = localStorage.getItem("fn-audioplayer-volume");
    if (saved !== null) {
      const vol = Math.max(0, Math.min(100, parseInt(saved, 10)));
      if (!isNaN(vol)) {
        volumeSlider.value = vol;
      }
    }
  } catch (e) {}
}

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  const wasEmpty = playlist.length === 0;
  files.forEach((file) => {
    playlist.push({
      name: file.name,
      path: URL.createObjectURL(file),
      isServerFile: false,
    });
  });
  if (sortMode === "shuffle") regenerateShuffle();
  updatePlaylistUI();
  if (wasEmpty) loadTrack(0);
  fileInput.value = "";
  showToast(t("addedCount", { count: files.length }), "success");
}

function addFileFromPath(filePath) {
  const fileName = filePath.split("/").pop();
  const isPlaying = !audioPlayer.paused || outputMode === "server";
  const track = { name: fileName, path: filePath, isServerFile: true };
  playlist.push(track);
  if (sortMode === "shuffle") regenerateShuffle();
  updatePlaylistUI();
  if (isPlaying && outputMode !== "server") {
    showToast(t("addedToList", { name: fileName }), "success");
    fetchMetadata(track, playlist.length - 1);
  } else {
    currentIndex = playlist.length - 1;
    loadTrack(currentIndex);
    showToast(t("nowPlaying", { name: fileName }), "success");
  }
}

function fetchMetadata(track, index, shouldPlay) {
  if (!track.isServerFile) return;
  fetch(API_ENDPOINT + "/audio/metadata?file=" + encodeURIComponent(track.path))
    .then((r) => r.json())
    .then((data) => {
      if (data.title) track.title = data.title;
      if (data.artist) track.artist = data.artist;
      if (data.album) track.album = data.album;
      updatePlaylistUI();
      if (shouldPlay && index === currentIndex) {
        trackTitle.textContent = track.title || track.name;
        trackSubtitle.textContent = track.artist
          ? track.artist + (track.album ? " - " + track.album : "")
          : FORMAT_LABELS[track.name.split(".").pop().toLowerCase()] || "";
      }
    })
    .catch(() => {});
}

function updatePlaylistUI() {
  if (playlist.length === 0) {
    playlistItems.innerHTML =
      '<div class="playlist-empty">' + t("noTracks") + "</div>";
    return;
  }
  playlistItems.innerHTML = playlist
    .map((item, index) => {
      const ext = item.name.split(".").pop().toLowerCase();
      const active = index === currentIndex;
      const coverUrl = item.isServerFile
        ? API_ENDPOINT + "/audio/cover?file=" + encodeURIComponent(item.path)
        : "";
      const iconHtml = coverUrl
        ? `<img src="${coverUrl}" onerror="this.classList.add('is-hidden');this.nextElementSibling.classList.remove('is-hidden')"><svg viewBox="0 0 24 24" class="is-hidden"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55C7.79 13 6 14.79 6 17s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>`
        : '<svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55C7.79 13 6 14.79 6 17s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>';
      return `
      <div class="playlist-item ${active ? "active" : ""}" onclick="loadTrack(${index})">
        <span class="pl-index">${active ? '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>' : index + 1}</span>
        <div class="pl-icon">${iconHtml}</div>
        <div class="pl-info">
          <div class="pl-name">${item.title || item.name}</div>
          <div class="pl-ext">${item.artist || FORMAT_LABELS[ext] || ext.toUpperCase()}</div>
        </div>
      </div>`;
    })
    .join("");
}

let toastTimer;
function showToast(message, type) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast ${type} show`;
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
}

function openBrowser() {
  browserCurrentDir = "/var/apps/fn-audioplayer/tmp";
  browserSelectedPaths = new Set();
  document.getElementById("browserOverlay").classList.add("active");
  browseDir("/var/apps/fn-audioplayer/tmp");
}

function closeBrowser() {
  document.getElementById("browserOverlay").classList.remove("active");
}

function browseDir(dirPath) {
  browserCurrentDir = dirPath;
  browserSelectedPaths = new Set();
  document.getElementById("browserPathText").textContent = dirPath;
  document.getElementById("browserConfirm").disabled = true;
  const body = document.getElementById("browserBody");
  body.innerHTML = '<div class="browse-loading">' + t("loading") + "</div>";

  fetch(API_ENDPOINT + "/browse?dir=" + encodeURIComponent(dirPath))
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        body.innerHTML =
          '<div class="browse-empty">' +
          (data.error === "Permission denied"
            ? t("permissionDenied")
            : data.error) +
          "</div>";
        return;
      }
      let html = "";
      if (data.parentDir !== null) {
        html += `<div class="browse-item" onclick="browseDir('${escapeAttr(data.parentDir)}')">
          <div class="browse-icon folder"><svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg></div>
          <div class="browse-name">.. (${t("parentDir")})</div>
        </div>`;
      }
      if (data.entries && data.entries.length > 0) {
        data.entries.forEach((entry) => {
          if (entry.isDir) {
            html += `<div class="browse-item" onclick="browseDir('${escapeAttr(entry.path)}')">
              <div class="browse-icon folder"><svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg></div>
              <div class="browse-name">${escapeHtml(entry.name)}</div>
            </div>`;
          } else if (entry.isAudio) {
            html += `<div class="browse-item" id="browse-${cssEscape(entry.path)}" onclick="toggleBrowseSelect('${escapeAttr(entry.path)}')">
              <div class="browse-icon audio"><svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55C7.79 13 6 14.79 6 17s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg></div>
              <div class="browse-name">${escapeHtml(entry.name)}</div>
              <div class="browse-check"></div>
            </div>`;
          }
        });
      }
      if (
        !html ||
        (!data.parentDir && data.entries && data.entries.length === 0)
      ) {
        html = '<div class="browse-empty">' + t("emptyDir") + "</div>";
      }
      body.innerHTML = html;
    })
    .catch(() => {
      body.innerHTML =
        '<div class="browse-empty">' + t("loadFailed") + "</div>";
    });
}

function toggleBrowseSelect(path) {
  if (browserSelectedPaths.has(path)) {
    browserSelectedPaths.delete(path);
  } else {
    browserSelectedPaths.add(path);
  }
  const el = document.getElementById("browse-" + cssEscape(path));
  if (el) el.classList.toggle("selected", browserSelectedPaths.has(path));
  document.getElementById("browserConfirm").disabled =
    browserSelectedPaths.size === 0;
}

function confirmBrowser() {
  if (browserSelectedPaths.size === 0) return;
  const wasEmpty = playlist.length === 0;
  const isPlaying = !audioPlayer.paused && playlist.length > 0;
  browserSelectedPaths.forEach((path) => {
    const fileName = path.split("/").pop();
    const track = { name: fileName, path: path, isServerFile: true };
    playlist.push(track);
    fetchMetadata(track, playlist.length - 1);
  });
  if (sortMode === "shuffle") regenerateShuffle();
  updatePlaylistUI();
  if (!isPlaying) {
    currentIndex = playlist.length - browserSelectedPaths.size;
    loadTrack(currentIndex);
  }
  showToast(t("addedCount", { count: browserSelectedPaths.size }), "success");
  closeBrowser();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

function cssEscape(str) {
  return String(str).replace(/[^a-zA-Z0-9]/g, function (c) {
    return "\\" + c.charCodeAt(0).toString(16).padStart(6, "0") + " ";
  });
}

loadVolume();
updateVolume();
loadOutputMode();
loadSortMode();
if (outputMode === "server") {
  setOutputMode("server");
}
claimPrimary();

// 初始化：通过 TrimApp SDK 获取平台语言/主题，并订阅实时变化
(async function initPlatform() {
  platformConfig = await sdk.getPlatformConfig();
  applyPreferences();
  if (sdk.isWeb === true && sdk.isStandaloneWeb === false) {
    await sdk.$on("os/theme", (theme) => {
      platformConfig = { ...platformConfig, theme };
      applyPreferences();
    });
    await sdk.$on("os/language", (language) => {
      platformConfig = { ...platformConfig, language };
      applyPreferences({ rerender: true });
    });
  }
})();

window.addEventListener("beforeunload", function () {
  if (outputMode === "server") {
    fetch(API_ENDPOINT + "/output/stop", {
      method: "POST",
      keepalive: true,
    }).catch(() => {});
  } else {
    audioPlayer.pause();
    audioPlayer.src = "";
  }
});

(function initFromURL() {
  const urlParams = new URLSearchParams(window.location.search);
  const pathParam = urlParams.get("path");
  if (pathParam) {
    const decodedPath = decodeURIComponent(pathParam);
    channel.postMessage({ type: "open-file", path: decodedPath });
    pendingFilePath = decodedPath;
    setTimeout(function () {
      if (isPrimaryWindow && pendingFilePath) {
        addFileFromPath(pendingFilePath);
        pendingFilePath = null;
      } else if (!isPrimaryWindow) {
        document.body.innerHTML =
          '<div class="fullscreen-msg">' +
          t("addedToList", { name: decodedPath.split("/").pop() }) +
          "</div>";
        setTimeout(function () {
          try {
            window.close();
          } catch (e) {}
        }, 1500);
      }
    }, 500);
  }
})();

// HTML 内联 onclick 处理器在全局作用域解析函数名。
// module 脚本顶层函数不挂到 window，需显式导出供内联 onclick 使用。
window.openAbout = openAbout;
window.closeAbout = closeAbout;
window.cycleSortMode = cycleSortMode;
window.cycleLyricsAlign = cycleLyricsAlign;
window.setOutputMode = setOutputMode;
window.onServerDeviceChange = onServerDeviceChange;
window.openBrowser = openBrowser;
window.closeBrowser = closeBrowser;
window.confirmBrowser = confirmBrowser;
window.browseDir = browseDir;
window.toggleBrowseSelect = toggleBrowseSelect;
window.loadTrack = loadTrack;
window.seekToLyric = seekToLyric;
window.addFileFromPath = addFileFromPath;
