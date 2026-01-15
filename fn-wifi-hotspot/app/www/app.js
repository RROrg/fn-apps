const $ = (id) => document.getElementById(id);

const statusEl = $("status");
const clientsEl = $("clients");
const msgEl = $("msg");
const toggleBtn = $("toggleHotspot");
const toggleText = $("toggleText");
const form = $("cfg");
const ifaceEl = form.elements["iface"];
const uplinkEl = form.elements["uplinkIface"];
const passwordEl = form.elements["password"];
const countryCodeEl = form.elements["countryCode"];
const bandEl = form.elements["band"];
const channelEl = form.elements["channel"];
const channelWidthEl = form.elements["channelWidth"];
const pwToggleBtn = $("pwToggle");
const langSelectEl = $("langSelect");
const themeSelectEl = $("themeSelect");

let serverChannelMeta = { bg: {}, a: {} };

let lastRunning = false;
let lastInternetStatus = undefined;

const I18N = {
  zh: {
    "title.tip": "提示",
    "title.confirm": "确认",
    "title.progress": "处理中",
    "btn.ok": "确定",
    "btn.cancel": "取消",
    "btn.continue": "继续",
    "btn.save": "保存",
    "btn.kick": "下线",
    "toggle.on": "热点：开启",
    "toggle.off": "热点：关闭",
    "toggle.suffix.net": "（有网）",
    "toggle.suffix.nonnet": "（无网）",

    "err.invalidJson": "响应不是有效 JSON",

    "section.net": "网卡",
    "section.config": "配置",
    "section.wifi": "参数",
    "section.clients": "客户端",
    "label.uplink": "共享网卡",
    "label.iface": "热点网卡",
    "label.ssid": "SSID",
    "label.password": "密码（>=8位）",
    "label.ipCidr": "IP/CIDR",
    "label.allowPorts": "放行端口（供客户端访问主机服务）",
    "label.country": "国家码",
    "label.band": "频段",
    "label.channel": "信道",
    "label.width": "带宽",
    "opt.uplinkAuto": "自动（系统默认路由）",
    "opt.ifaceAuto": "自动选择",
    "opt.unavailable": "（不可用/未检测到）",

    "placeholder.ipCidr": "192.168.12.1/24",
    "placeholder.allowPorts": "80,443,5666,5667,67-68/udp",

    "pw.show": "显示密码",
    "pw.hide": "隐藏密码",

    "aria.langSelect": "语言",
    "aria.themeSelect": "主题",

    "lang.zh": "中文",
    "lang.en": "English",
    "theme.system": "跟随系统",
    "theme.light": "浅色",
    "theme.dark": "深色",

    "clients.empty": "暂无客户端",
    "clients.cols": ["主机名", "MAC", "IP", "信号", "在线", "流量", "操作"],
    "kick.confirm": "确定要让客户端下线？\n{mac}{ip}",
    "kick.title": "确认下线",
    "kick.progress": "正在让客户端下线…",
    "kick.done": "已下线",

    "hotspot.confirmTitle": "确认开启热点",
    "hotspot.confirmOk": "继续开启",
    "hotspot.confirmCancel": "取消",
    "hotspot.confirmMsg": "当前网卡不支持 STA+AP 并发，开启热点将断开当前 Wi‑Fi 连接{conPart}。是否继续？",

    "progress.enable": "正在开启热点…",
    "progress.disable": "正在关闭热点…",
    "progress.save": "正在保存配置…",
    "progress.restart": "正在重启热点…",

    "msg.canceled": "已取消",
    "msg.enabled": "已开启热点",
    "msg.disabled": "已关闭热点",
    "msg.saved": "已保存",
    "msg.savedRestart": "已保存并重启热点",
    "msg.no5g": "当前监管域下 5G 信道不可用，已切换到 2.4G",
    "msg.countryChangeFailed": "更改国家码失败：{err}",
    "countryNames": {
      "CN": "中国",
      "US": "美国",
      "JP": "日本",
      "KR": "韩国",
      "AU": "澳大利亚",
      "CA": "加拿大",
      "GB": "英国",
      "DE": "德国",
      "FR": "法国",
      "IT": "意大利",
      "ES": "西班牙",
      "NL": "荷兰",
      "BE": "比利时",
      "CH": "瑞士",
      "AT": "奥地利",
      "SE": "瑞典",
      "NO": "挪威",
      "DK": "丹麦",
      "FI": "芬兰",
      "RU": "俄罗斯",
      "IN": "印度",
      "BR": "巴西",
      "MX": "墨西哥",
      "AR": "阿根廷",
      "CL": "智利",
      "CO": "哥伦比亚",
      "PE": "秘鲁",
      "VE": "委内瑞拉",
      "ZA": "南非",
      "EG": "埃及",
      "NG": "尼日利亚",
      "KE": "肯尼亚",
      "MA": "摩洛哥",
      "TN": "突尼斯",
      "TR": "土耳其",
      "SA": "沙特阿拉伯",
      "AE": "阿联酋",
      "IL": "以色列",
      "TH": "泰国",
      "MY": "马来西亚",
      "SG": "新加坡",
      "PH": "菲律宾",
      "ID": "印尼",
      "VN": "越南",
      "HK": "中国香港",
      "TW": "中国台湾",
      "MO": "中国澳门"
    },
  },
  en: {
    "title.tip": "Info",
    "title.confirm": "Confirm",
    "title.progress": "Working",
    "btn.ok": "OK",
    "btn.cancel": "Cancel",
    "btn.continue": "Continue",
    "btn.save": "Save",
    "btn.kick": "Kick",
    "toggle.on": "Hotspot: On",
    "toggle.off": "Hotspot: Off",
    "toggle.suffix.net": " (online)",
    "toggle.suffix.nonnet": " (offline)",

    "err.invalidJson": "Response is not valid JSON",

    "section.net": "Network",
    "section.config": "Config",
    "section.wifi": "Wi-Fi",
    "section.clients": "Clients",
    "label.uplink": "Uplink",
    "label.iface": "Hotspot device",
    "label.ssid": "SSID",
    "label.password": "Password (>=8)",
    "label.ipCidr": "IP/CIDR",
    "label.allowPorts": "Allowed ports (client → host)",
    "label.country": "Country Code",
    "label.band": "Band",
    "label.channel": "Channel",
    "label.width": "Bandwidth",
    "opt.uplinkAuto": "Auto (default route)",
    "opt.ifaceAuto": "Auto",
    "opt.unavailable": " (unavailable)",

    "placeholder.ipCidr": "192.168.12.1/24",
    "placeholder.allowPorts": "80,443,5666,5667,67-68/udp",

    "pw.show": "Show password",
    "pw.hide": "Hide password",

    "aria.langSelect": "Language",
    "aria.themeSelect": "Theme",

    "lang.zh": "中文",
    "lang.en": "English",
    "theme.system": "System",
    "theme.light": "Light",
    "theme.dark": "Dark",

    "clients.empty": "No clients",
    "clients.cols": ["Hostname", "MAC", "IP", "Signal", "Online", "Traffic", "Action"],
    "kick.confirm": "Kick this client?\n{mac}{ip}",
    "kick.title": "Confirm kick",
    "kick.progress": "Kicking client…",
    "kick.done": "Kicked",

    "hotspot.confirmTitle": "Start hotspot",
    "hotspot.confirmOk": "Start",
    "hotspot.confirmCancel": "Cancel",
    "hotspot.confirmMsg": "This adapter does not support STA+AP concurrency. Starting hotspot will disconnect current Wi‑Fi{conPart}. Continue?",

    "progress.enable": "Starting hotspot…",
    "progress.disable": "Stopping hotspot…",
    "progress.save": "Saving…",
    "progress.restart": "Restarting…",

    "msg.canceled": "Canceled",
    "msg.enabled": "Hotspot started",
    "msg.disabled": "Hotspot stopped",
    "msg.saved": "Saved",
    "msg.savedRestart": "Saved and restarted",
    "msg.no5g": "5GHz channels unavailable; switched to 2.4GHz",
    "msg.countryChangeFailed": "Failed to change country code: {err}",
    "countryNames": {
      "CN": "China",
      "US": "United States",
      "JP": "Japan",
      "KR": "Korea",
      "AU": "Australia",
      "CA": "Canada",
      "GB": "United Kingdom",
      "DE": "Germany",
      "FR": "France",
      "IT": "Italy",
      "ES": "Spain",
      "NL": "Netherlands",
      "BE": "Belgium",
      "CH": "Switzerland",
      "AT": "Austria",
      "SE": "Sweden",
      "NO": "Norway",
      "DK": "Denmark",
      "FI": "Finland",
      "RU": "Russia",
      "IN": "India",
      "BR": "Brazil",
      "MX": "Mexico",
      "AR": "Argentina",
      "CL": "Chile",
      "CO": "Colombia",
      "PE": "Peru",
      "VE": "Venezuela",
      "ZA": "South Africa",
      "EG": "Egypt",
      "NG": "Nigeria",
      "KE": "Kenya",
      "MA": "Morocco",
      "TN": "Tunisia",
      "TR": "Turkey",
      "SA": "Saudi Arabia",
      "AE": "United Arab Emirates",
      "IL": "Israel",
      "TH": "Thailand",
      "MY": "Malaysia",
      "SG": "Singapore",
      "PH": "Philippines",
      "ID": "Indonesia",
      "VN": "Vietnam",
      "HK": "Hong Kong, China",
      "TW": "Taiwan, China",
      "MO": "Macau, China"
    },
  }
};

let currentLang = (localStorage.getItem("lang") || "").toString();
if (!currentLang) currentLang = (navigator.language || "").toLowerCase().startsWith("zh") ? "zh" : "en";
if (!I18N[currentLang]) currentLang = "zh";

function t(key, vars = {}) {
  const dict = I18N[currentLang] || I18N.zh;
  const v = (dict[key] != null) ? dict[key] : (I18N.zh[key] != null ? I18N.zh[key] : key);
  if (typeof v !== "string") return v;
  return v.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, k) => (vars[k] ?? "").toString());
}

let themeMode = (localStorage.getItem("theme") || "system").toString();
if (!themeMode) themeMode = "system";

function applyTheme() {
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const mode = themeMode === "system" ? (prefersDark ? "dark" : "light") : themeMode;
  const v = mode === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", v);
  document.body.setAttribute("data-theme", v);
  if (themeSelectEl) themeSelectEl.value = themeMode;
}

function applyI18nStatic() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;
    const val = t(key);
    if (typeof val === "string") el.textContent = val;
  });

  // Attributes
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (!key) return;
    const val = t(key);
    if (typeof val === "string") el.setAttribute("placeholder", val);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
    const key = el.getAttribute("data-i18n-aria-label");
    if (!key) return;
    const val = t(key);
    if (typeof val === "string") el.setAttribute("aria-label", val);
  });

  // Placeholders
  const ipCidrEl = form && form.elements ? form.elements["ipCidr"] : null;
  if (ipCidrEl) ipCidrEl.placeholder = t("placeholder.ipCidr");
  const allowPortsEl = form && form.elements ? form.elements["allowPorts"] : null;
  if (allowPortsEl) allowPortsEl.placeholder = t("placeholder.allowPorts");

  // Select labels
  if (langSelectEl) {
    const optZh = langSelectEl.querySelector('option[value="zh"]');
    const optEn = langSelectEl.querySelector('option[value="en"]');
    if (optZh) optZh.textContent = t("lang.zh");
    if (optEn) optEn.textContent = t("lang.en");
    langSelectEl.value = currentLang;
  }
  if (themeSelectEl) {
    const optSys = themeSelectEl.querySelector('option[value="system"]');
    const optLight = themeSelectEl.querySelector('option[value="light"]');
    const optDark = themeSelectEl.querySelector('option[value="dark"]');
    if (optSys) optSys.textContent = t("theme.system");
    if (optLight) optLight.textContent = t("theme.light");
    if (optDark) optDark.textContent = t("theme.dark");
  }

  // Localize country select options if present
  try {
    const countrySel = document.getElementById('countryCode');
    if (countrySel) {
      const dict = I18N[currentLang] || I18N.zh;
      const names = dict && dict.countryNames ? dict.countryNames : {};
      for (const opt of Array.from(countrySel.options)) {
        const code = (opt.value || '').toString();
        const name = names[code] || code;
        opt.textContent = `${code} (${name})`;
      }
    }
  } catch (e) {
    // noop
  }

  // Keep toggle label consistent.
  setRunningUI(lastRunning, lastInternetStatus);

  // Sync password toggle label for current language.
  setPasswordVisible(passwordVisible);
}

let activeModalCleanup = null;

function getModalEls() {
  const modal = $("modal");
  const modalTitle = $("modalTitle");
  const modalContent = $("modalContent");
  const okBtn = $("modalOk");
  const cancelBtn = $("modalCancel");
  const actions = modal ? modal.querySelector(".actions") : null;
  return { modal, modalTitle, modalContent, okBtn, cancelBtn, actions };
}

function closeModal() {
  const { modal, actions, okBtn, cancelBtn } = getModalEls();
  if (!modal) return;
  if (activeModalCleanup) {
    const fn = activeModalCleanup;
    activeModalCleanup = null;
    try { fn(); } catch { /* ignore */ }
  }
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
  if (actions) actions.style.display = "";
  if (okBtn) okBtn.style.display = "";
  if (cancelBtn) cancelBtn.style.display = "";
}

function modalOpen({
  title = null,
  message = "",
  okText = null,
  cancelText = null,
  showCancel = false,
  allowBackdropClose = true,
  allowEsc = true,
  hideActions = false,
} = {}) {
  const { modal, modalTitle, modalContent, okBtn, cancelBtn, actions } = getModalEls();
  if (!modal || !modalTitle || !modalContent || !okBtn || !cancelBtn) {
    // Fallback if internal modal markup is missing.
    if (showCancel) return Promise.resolve(window.confirm(String(message || "")));
    // eslint-disable-next-line no-alert
    window.alert(String(message || ""));
    return Promise.resolve(true);
  }

  // Close any existing modal first.
  closeModal();

  modalTitle.textContent = String(title || t("title.tip"));
  modalContent.textContent = String(message || "");
  okBtn.textContent = String(okText || t("btn.ok"));
  cancelBtn.textContent = String(cancelText || t("btn.cancel"));
  cancelBtn.style.display = showCancel ? "" : "none";
  if (actions) actions.style.display = hideActions ? "none" : "";

  const prevActive = document.activeElement;
  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");

  if (!hideActions) okBtn.focus();

  return new Promise((resolve) => {
    let done = false;
    const finish = (val) => {
      if (done) return;
      done = true;
      closeModal();
      if (prevActive && typeof prevActive.focus === "function") prevActive.focus();
      resolve(val);
    };

    const onKeyDown = (ev) => {
      if (!ev) return;
      if (allowEsc && ev.key === "Escape") {
        ev.preventDefault();
        finish(false);
      }
      if (!hideActions && ev.key === "Enter") {
        if (document.activeElement === okBtn) {
          ev.preventDefault();
          finish(true);
        }
      }
    };

    const onClick = (ev) => {
      if (!allowBackdropClose) return;
      const t = ev && ev.target;
      if (t && t.getAttribute && t.getAttribute("data-modal-close") === "1") finish(false);
    };

    const onOk = () => finish(true);
    const onCancel = () => finish(false);

    const cleanup = () => {
      document.removeEventListener("keydown", onKeyDown);
      modal.removeEventListener("click", onClick);
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
    };
    activeModalCleanup = cleanup;

    document.addEventListener("keydown", onKeyDown);
    modal.addEventListener("click", onClick);
    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
  });
}

function internalConfirm(message, {
  title = null,
  okText = null,
  cancelText = null,
} = {}) {
  return modalOpen({
    title: title || t("title.confirm"),
    message,
    okText: okText || t("btn.continue"),
    cancelText: cancelText || t("btn.cancel"),
    showCancel: true,
    allowBackdropClose: true,
    allowEsc: true,
    hideActions: false,
  }).then(Boolean);
}

function internalAlert(message, { title = null, okText = null } = {}) {
  return modalOpen({
    title: title || t("title.tip"),
    message,
    okText: okText || t("btn.ok"),
    showCancel: false,
    allowBackdropClose: true,
    allowEsc: true,
    hideActions: false,
  });
}

function internalProgress(message, { title = null } = {}) {
  modalOpen({
    title: title || t("title.progress"),
    message,
    hideActions: true,
    allowBackdropClose: false,
    allowEsc: false,
  }).catch(() => { /* ignore */ });
  return () => closeModal();
}

function setRunningUI(running, internetStatus) {
  lastRunning = !!running;
  lastInternetStatus = internetStatus;
  if (!toggleBtn) return;
  toggleBtn.setAttribute("aria-pressed", lastRunning ? "true" : "false");
  let suffix = "";
  if (lastRunning) {
    if (internetStatus === true) suffix = t("toggle.suffix.net");
    else if (internetStatus === false) suffix = t("toggle.suffix.nonnet");
  }
  const label = `${lastRunning ? t("toggle.on") : t("toggle.off")}${suffix}`;
  if (toggleText) toggleText.textContent = label;
  else toggleBtn.textContent = label;
}

let formDirty = false;
const markDirty = () => { formDirty = true; };

let passwordVisible = false;

function defaultChannelForBand(band) {
  return (band === "a") ? "36" : "6";
}

function channelOptionsForBand(band) {
  const meta = serverChannelMeta && serverChannelMeta[band];
  if (meta && Object.keys(meta).length > 0) {
    // Prefer numeric sort for channel numbers
    return Object.keys(meta).sort((a, b) => Number(a) - Number(b));
  }
  return [];
}

function updateBandAvailability() {
  if (!bandEl) return;
  const opt5g = bandEl.querySelector('option[value="a"]');
  // Consider 5G available only if there's at least one non-disabled channel
  let has5g = true;
  const metaA = serverChannelMeta && serverChannelMeta.a ? serverChannelMeta.a : {};
  if (Object.keys(metaA).length > 0) {
    has5g = Object.keys(metaA).some(ch => {
      const st = (metaA && metaA[ch] && metaA[ch].state) ? metaA[ch].state : null;
      return st !== 'disabled';
    });
  }
  if (opt5g) opt5g.disabled = !has5g;
  if (!has5g && bandEl.value === "a") {
    bandEl.value = "bg";
    syncChannelSelect({ band: "bg", forceDefaultIfInvalid: true });
    setMsg(t("msg.no5g"));
    markDirty();
  }
}

// Fetch channel options from server for a specific country and apply them.
async function fetchAndApplyChannelOptions(countryCode, { forceDefaultIfInvalid = false } = {}) {
  if (!countryCode) countryCode = "CN";
  try {
    // Request server config with country override so backend can return proper channelOptions
    const url = cgiUrl("config_get.cgi") + `&countryCode=${encodeURIComponent(countryCode)}`;
    const cfg = await getJSON(url);
    if (cfg && cfg.channelOptions && typeof cfg.channelOptions === "object") {
      serverChannelMeta = { bg: {}, a: {} };
      for (const band of ["bg", "a"]) {
        const arr = Array.isArray(cfg.channelOptions[band]) ? cfg.channelOptions[band] : null;
        if (!Array.isArray(arr)) continue;
        for (const entry of arr) {
          const parts = String(entry).split(":");
          const ch = parts[0] || "";
          const freq = parts[1] || null;
          const state = parts[2] || (parts.length > 1 ? 'supported' : null);
          if (ch) serverChannelMeta[band][String(ch)] = { freq, state };
        }
      }
      updateBandAvailability();
      syncChannelSelect({ forceDefaultIfInvalid });
      markDirty();
    }
  } catch (e) {
    const msg = t("msg.countryChangeFailed", { err: e.message || String(e) });
    try { internalAlert(msg).catch(() => { /* ignore */ }); } catch (_) { setMsg(msg); }
  }
}

function syncChannelSelect({ band, prefer, forceDefaultIfInvalid = false } = {}) {
  if (!channelEl) return;
  const b = (band ?? (bandEl && bandEl.value) ?? "bg").toString();
  const desired = (prefer ?? channelEl.value ?? "").toString().trim();
  const opts = channelOptionsForBand(b);

  channelEl.innerHTML = "";
  for (const v of opts) {
    const opt = document.createElement("option");
    opt.value = v;
    // If server provided metadata, show frequency and disable if marked.
    const meta = (serverChannelMeta[b] && serverChannelMeta[b][v]) ? serverChannelMeta[b][v] : null;
    opt.textContent = meta && meta.freq ? `${v} (${meta.freq} MHz)` : v;
    if (meta && meta.state === 'disabled') opt.disabled = true;
    if (meta && meta.state && meta.state !== 'supported') opt.title = meta.state;
    channelEl.appendChild(opt);
  }

  const has = desired && opts.includes(desired);
  if (has) channelEl.value = desired;
  else if (forceDefaultIfInvalid || !desired) channelEl.value = defaultChannelForBand(b);
  else channelEl.value = opts[0] || "";
}

function isChannelValidForBand(channel, band) {
  const n = Number.parseInt((channel || "").toString(), 10);
  if (!Number.isFinite(n)) return false;
  if (band === "bg") return n >= 1 && n <= 14;
  if (band === "a") return n >= 34;
  return true;
}

function setPasswordVisible(visible) {
  passwordVisible = !!visible;
  if (!passwordEl || !pwToggleBtn) return;
  passwordEl.type = passwordVisible ? "text" : "password";
  pwToggleBtn.setAttribute("aria-pressed", passwordVisible ? "true" : "false");
  pwToggleBtn.setAttribute("aria-label", passwordVisible ? t("pw.hide") : t("pw.show"));
  const eye = pwToggleBtn.querySelector(".icon-eye");
  const eyeOff = pwToggleBtn.querySelector(".icon-eye-off");
  if (eye) eye.style.display = passwordVisible ? "none" : "block";
  if (eyeOff) eyeOff.style.display = passwordVisible ? "block" : "none";
}

if (pwToggleBtn) {
  pwToggleBtn.addEventListener("click", () => setPasswordVisible(!passwordVisible));
  setPasswordVisible(false);
}

// When band changes, auto-fill a sensible default channel if empty or obviously invalid.
if (bandEl && channelEl) {
  bandEl.addEventListener("change", () => {
    const band = (bandEl.value || "bg").toString();
    const current = (channelEl.value || "").toString().trim();
    syncChannelSelect({ band, prefer: current, forceDefaultIfInvalid: true });
    markDirty();
  });
}

// When country code changes, fetch updated regulatory channel options and refresh selects.
if (countryCodeEl) {
  countryCodeEl.addEventListener("change", () => {
    const cc = (countryCodeEl.value || "CN").toString();
    // Fetch channel options for the chosen country and update UI accordingly.
    fetchAndApplyChannelOptions(cc, { forceDefaultIfInvalid: true }).catch((e) => {
      setMsg(e.message);
    });
  });
}

// Any manual edits should not be overwritten by refresh() unless forced.
form.addEventListener("input", markDirty);
form.addEventListener("change", markDirty);

let msgTimer = null;
function setMsg(t) {
  // Use internal modal for all prompts.
  if (msgTimer) {
    clearTimeout(msgTimer);
    msgTimer = null;
  }
  const text = (t || "").toString().trim();
  if (!text) return;
  // Keep legacy toast updated but hidden (in case someone relies on it).
  if (msgEl) msgEl.textContent = text;
  internalAlert(text).catch(() => { /* ignore */ });
}

function formatDuration(sec) {
  const n = Number(sec);
  if (!Number.isFinite(n) || n < 0) return "";
  if (n < 60) return `${n}s`;
  const m = Math.floor(n / 60);
  const s = n % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return `${h}h ${mm}m`;
}

function formatBytes(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n < 0) return "";
  if (n < 1024) return `${n} B`;
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  const gb = mb / 1024;
  return `${gb.toFixed(2)} GB`;
}

async function kickClient(mac) {
  const m = (mac || "").toString().trim().toLowerCase();
  const url = cgiUrl(`kick.cgi?mac=${encodeURIComponent(m)}`);
  return getJSON(url);
}

function renderClients(list) {
  if (!clientsEl) return;
  clientsEl.innerHTML = "";

  const clients = Array.isArray(list) ? list : [];
  if (clients.length === 0) {
    const empty = document.createElement("div");
    empty.className = "clients-empty";
    empty.textContent = t("clients.empty");
    clientsEl.appendChild(empty);
    return;
  }

  const table = document.createElement("table");
  table.className = "clients";

  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  const cols = t("clients.cols");
  const colList = Array.isArray(cols) ? cols : ["主机名", "MAC", "IP", "信号", "在线", "流量", "操作"];
  for (const name of colList) {
    const th = document.createElement("th");
    th.textContent = name;
    hr.appendChild(th);
  }
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const c of clients) {
    const tr = document.createElement("tr");

    const mac = (c && c.mac) ? String(c.mac).trim().toLowerCase() : "";
    const hostname = (c && c.hostname) ? String(c.hostname) : "";
    const ip = (c && c.ip) ? String(c.ip) : "";
    const sig = (c && (c.signalDbm ?? c.signal))
      ? `${String(c.signalDbm ?? c.signal)} dBm`
      : "";
    const dur = (c && c.connectedSeconds != null)
      ? formatDuration(c.connectedSeconds)
      : "";

    const rx = (c && c.rxBytes != null) ? formatBytes(c.rxBytes) : "";
    const tx = (c && c.txBytes != null) ? formatBytes(c.txBytes) : "";
    const traffic = (rx || tx) ? `↓${rx || "0 B"} ↑${tx || "0 B"}` : "";

    for (const txt of [hostname, mac, ip, sig, dur, traffic]) {
      const td = document.createElement("td");
      td.textContent = txt;
      tr.appendChild(td);
    }

    const tdAct = document.createElement("td");
    tdAct.className = "clients-actions";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = t("btn.kick");
    btn.disabled = !/^[0-9a-f]{2}(:[0-9a-f]{2}){5}$/.test(mac);
    btn.onclick = async () => {
      if (!mac) return;
      const ok = await internalConfirm(t("kick.confirm", { mac, ip: ip ? `\n${ip}` : "" }), {
        title: t("kick.title"),
        okText: t("btn.kick"),
        cancelText: t("btn.cancel"),
      });
      if (!ok) return;
      btn.disabled = true;
      const closeProg = internalProgress(t("kick.progress"));
      try {
        await kickClient(mac);
        closeProg();
        setMsg(t("kick.done"));
        await refresh({ withConfig: false });
      } catch (e) {
        closeProg();
        setMsg(e.message);
      } finally {
        btn.disabled = false;
      }
    };
    tdAct.appendChild(btn);
    tr.appendChild(tdAct);

    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  clientsEl.appendChild(table);
}

// Determine CGI path prefix based on current URL.
// - When hosted via /.../index.cgi/index.html, static files come from /.../index.cgi/...
//   and executable CGIs are exposed under ../www/cgi-bin/.
// - When hosted directly from /.../www/index.html, use ./cgi-bin/.
const CGI_PREFIX = location.pathname.includes("index.cgi") ? "../www/cgi-bin/" : "cgi-bin/";
const cgiUrl = (p) => {
  const u = new URL(CGI_PREFIX + p, location.href);
  // Pass UI language to backend so CGI can localize messages.
  u.searchParams.set("lang", currentLang);
  return u.toString();
};

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  const text = await r.text();
  let j = null;
  try {
    j = text ? JSON.parse(text) : {};
  } catch (e) {
    j = null;
  }

  // If server responded non-2xx, prefer JSON.error -> raw text -> statusText
  if (!r.ok) {
    const msg = (j && j.error) || text || r.statusText;
    throw new Error(msg);
  }

  // 2xx but not JSON: present raw text as error so UI shows useful info
  if (!j) {
    const msg = text || t("err.invalidJson");
    throw new Error(msg);
  }

  if (j.ok === false) throw new Error(j.error || r.statusText);
  return j;
}

async function postForm(url, dataObj) {
  const body = new URLSearchParams(dataObj).toString();
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.ok === false) throw new Error(j.error || r.statusText);
  return j;
}

function readForm() {
  const fd = new FormData(form);
  return {
    iface: (fd.get("iface") || "").toString().trim(),
    uplinkIface: (fd.get("uplinkIface") || "").toString().trim(),
    ipCidr: (fd.get("ipCidr") || "").toString().trim(),
    allowPorts: (fd.get("allowPorts") || "").toString().trim(),
    ssid: (fd.get("ssid") || "").toString().trim(),
    password: (fd.get("password") || "").toString(),
    countryCode: (fd.get("countryCode") || "CN").toString(),
    band: (fd.get("band") || "bg").toString(),
    channel: (fd.get("channel") || "6").toString(),
    channelWidth: (fd.get("channelWidth") || "20").toString()
  };
}

function fillForm(cfg) {
  if (!cfg || typeof cfg !== "object") return;
  for (const [k, v] of Object.entries(cfg)) {
    const el = form.elements[k];
    if (el) el.value = v ?? "";
  }
}

function setIfaceOptions(ifaces, selected) {
  if (!ifaceEl || !ifaceEl.options) return;

  const list = Array.isArray(ifaces) ? ifaces.map(String) : [];
  const uniq = Array.from(new Set(list.filter(Boolean)));

  const keep = (selected ?? "").toString();
  const needsUnknown = keep && !uniq.includes(keep);

  ifaceEl.innerHTML = '';
  const autoOpt = document.createElement('option');
  autoOpt.value = '';
  autoOpt.textContent = t('opt.ifaceAuto');
  ifaceEl.appendChild(autoOpt);

  for (const d of uniq) {
    const opt = document.createElement('option');
    opt.value = d;
    opt.textContent = d;
    ifaceEl.appendChild(opt);
  }

  if (needsUnknown) {
    const opt = document.createElement('option');
    opt.value = keep;
    opt.textContent = `${keep}${t('opt.unavailable')}`;
    ifaceEl.appendChild(opt);
  }

  ifaceEl.value = keep;
}

function setUplinkOptions(uplinks, selected) {
  if (!uplinkEl || !uplinkEl.options) return;

  const list = Array.isArray(uplinks) ? uplinks.map(String) : [];
  const uniq = Array.from(new Set(list.filter(Boolean)));

  const keep = (selected ?? "").toString();
  const needsUnknown = keep && !uniq.includes(keep);

  uplinkEl.innerHTML = '';
  const autoOpt = document.createElement('option');
  autoOpt.value = '';
  autoOpt.textContent = t('opt.uplinkAuto');
  uplinkEl.appendChild(autoOpt);

  for (const d of uniq) {
    const opt = document.createElement('option');
    opt.value = d;
    opt.textContent = d;
    uplinkEl.appendChild(opt);
  }

  if (needsUnknown) {
    const opt = document.createElement('option');
    opt.value = keep;
    opt.textContent = `${keep}${t('opt.unavailable')}`;
    uplinkEl.appendChild(opt);
  }

  uplinkEl.value = keep;
}

async function refresh({ force = false, withConfig = true } = {}) {
  const baseline = readForm();

  if (withConfig) {
    const [cfg, st, cl, ifs, ups] = await Promise.all([
      getJSON(cgiUrl("config_get.cgi")),
      getJSON(cgiUrl("status.cgi")),
      getJSON(cgiUrl("clients.cgi")),
      getJSON(cgiUrl("ifaces.cgi")),
      getJSON(cgiUrl("uplinks.cgi")),
    ]);

    const cfgObj = cfg && cfg.config;
    if (cfg && cfg.channelOptions && typeof cfg.channelOptions === "object") {
      // Build meta mapping for quick lookup from server-provided entries which may be
      // either "CH:FRQ:STATE" or plain "CH".
      serverChannelMeta = { bg: {}, a: {} };
      for (const band of ["bg", "a"]) {
        const arr = Array.isArray(cfg.channelOptions[band]) ? cfg.channelOptions[band] : null;
        if (!Array.isArray(arr)) continue;
        for (const entry of arr) {
          const parts = String(entry).split(":");
          const ch = parts[0] || "";
          const freq = parts[1] || null;
          const state = parts[2] || (parts.length > 1 ? 'supported' : null);
          if (ch) serverChannelMeta[band][String(ch)] = { freq, state };
        }
      }
      updateBandAvailability();
    }
    const current = (!force && formDirty) ? baseline : null;
    setIfaceOptions(ifs && ifs.ifaces, current ? current.iface : (cfgObj && cfgObj.iface));
    setUplinkOptions(ups && ups.uplinks, current ? current.uplinkIface : (cfgObj && cfgObj.uplinkIface));

    if (cfgObj && (force || !formDirty)) {
      fillForm(cfgObj);
      // After fill, rebuild channel list based on current band.
      syncChannelSelect({ forceDefaultIfInvalid: true });
      formDirty = false;
    }

    setRunningUI(
      st && st.status && st.status.running === true,
      st && st.status ? st.status.internetStatus : undefined
    );
    if (statusEl) statusEl.textContent = JSON.stringify(st.status, null, 2);
    renderClients(cl.clients);
    return;
  }

  const [st, cl, ifs, ups] = await Promise.all([
    getJSON(cgiUrl("status.cgi")),
    getJSON(cgiUrl("clients.cgi")),
    getJSON(cgiUrl("ifaces.cgi")),
    getJSON(cgiUrl("uplinks.cgi")),
  ]);

  // No config fetch: keep current form values while refreshing option lists.
  setIfaceOptions(ifs && ifs.ifaces, baseline.iface);
  setUplinkOptions(ups && ups.uplinks, baseline.uplinkIface);
  setRunningUI(
    st && st.status && st.status.running === true,
    st && st.status ? st.status.internetStatus : undefined
  );
  if (statusEl) statusEl.textContent = JSON.stringify(st.status, null, 2);
  renderClients(cl.clients);
}

$("save").onclick = async (ev) => {
  if (ev && typeof ev.preventDefault === "function") ev.preventDefault();
  const saveBtn = $("save");
  try {
    if (saveBtn) saveBtn.disabled = true;
    if (lastRunning) {
      const closeRestart = internalProgress(t("progress.restart"));
      await getJSON(cgiUrl("stop.cgi"));
      await postForm(cgiUrl("config_set.cgi"), readForm());
      await getJSON(cgiUrl("start.cgi"));
      closeRestart();
      setMsg(t("msg.savedRestart"));
      await refresh({ withConfig: false });
    } else {
      const closeProg = internalProgress(t("progress.save"));
      await postForm(cgiUrl("config_set.cgi"), readForm());
      closeProg();
      setMsg(t("msg.saved"));
      await refresh({ force: true });
    }
  } catch (e) {
    setMsg(e.message);
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
};
if (toggleBtn) {
  toggleBtn.onclick = async () => {
    try {
      toggleBtn.disabled = true;
      if (lastRunning) {
        const closeProg = internalProgress(t("progress.disable"));
        await getJSON(cgiUrl("stop.cgi"));
        closeProg();
        setMsg(t("msg.disabled"));
      } else {
        // If STA+AP concurrent mode is not supported, starting hotspot will disconnect current Wi-Fi.
        const stPre = await getJSON(cgiUrl("status.cgi"));
        const willDisc = !!(stPre && stPre.status && stPre.status.willDisconnectSta === true);
        const apConc = !!(stPre && stPre.status && stPre.status.staApConcurrent === true);
        if (!apConc && willDisc) {
          const parentCon = (stPre && stPre.status && stPre.status.parentActiveConnection) ? String(stPre.status.parentActiveConnection) : "";
          const conPart = parentCon ? (currentLang === "zh" ? `（${parentCon}）` : ` (${parentCon})`) : "";
          const ok = await internalConfirm(t("hotspot.confirmMsg", { conPart }), {
            title: t("hotspot.confirmTitle"),
            okText: t("hotspot.confirmOk"),
            cancelText: t("hotspot.confirmCancel"),
          });
          if (!ok) {
            setMsg(t("msg.canceled"));
            return;
          }
        }
        const closeProg = internalProgress(t("progress.enable"));
        await getJSON(cgiUrl("start.cgi"));
        closeProg();
        setMsg(t("msg.enabled"));
      }
      await refresh({ withConfig: false });
    } catch (e) {
      setMsg(e.message);
    } finally {
      toggleBtn.disabled = false;
    }
  };
}

// Theme + language init
if (langSelectEl) {
  langSelectEl.value = currentLang;
  langSelectEl.onchange = () => {
    const v = (langSelectEl.value || "zh").toString();
    currentLang = I18N[v] ? v : "zh";
    localStorage.setItem("lang", currentLang);
    applyI18nStatic();
    refresh({ withConfig: false }).catch(e => setMsg(e.message));
  };
}
if (themeSelectEl) {
  themeSelectEl.value = themeMode;
  themeSelectEl.onchange = () => {
    const v = (themeSelectEl.value || "system").toString();
    themeMode = (v === "light" || v === "dark" || v === "system") ? v : "system";
    localStorage.setItem("theme", themeMode);
    applyTheme();
  };
}
applyTheme();
applyI18nStatic();
if (window.matchMedia) {
  const mql = window.matchMedia("(prefers-color-scheme: dark)");
  const onChange = () => { if (themeMode === "system") applyTheme(); };
  if (typeof mql.addEventListener === "function") mql.addEventListener("change", onChange);
  else if (typeof mql.addListener === "function") mql.addListener(onChange);
}

refresh({ force: true }).catch(e => setMsg(e.message));

// Init channel options on first load.
syncChannelSelect({ forceDefaultIfInvalid: true });

// Auto refresh clients (and running state) every 5 seconds.
let autoRefreshInFlight = false;
async function refreshClientsOnly() {
  if (autoRefreshInFlight) return;
  autoRefreshInFlight = true;
  try {
    const [st, cl] = await Promise.all([
      getJSON(cgiUrl("status.cgi")),
      getJSON(cgiUrl("clients.cgi")),
    ]);
    setRunningUI(
      st && st.status && st.status.running === true,
      st && st.status ? st.status.internetStatus : undefined
    );
    renderClients(cl && cl.clients);
  } finally {
    autoRefreshInFlight = false;
  }
}

setInterval(() => {
  refreshClientsOnly().catch(() => { /* keep UI quiet */ });
}, 5000);
