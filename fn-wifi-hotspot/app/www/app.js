const API = "/app/fn-wifi-hotspot/api";

const state = {
  language: "zh-CN",
  theme: "light",
  config: null,
  status: null,
  channels: { bg: [], a: [] },
  running: false,
  loaded: false,
  busy: false,
  polling: false,
};

const I18N = {
  "zh-CN": {
    appTitle: "无线热点",
    loading: "正在加载...",
    refresh: "刷新",
    start: "开启热点",
    stop: "关闭热点",
    save: "保存",
    saving: "保存中...",
    status: "状态",
    config: "配置",
    clients: "客户端",
    hotspotDevice: "热点网卡",
    uplink: "共享网卡",
    address: "地址",
    internet: "互联网",
    password: "密码",
    allowPorts: "放行端口",
    country: "国家码",
    band: "频段",
    channel: "信道",
    width: "带宽",
    autoIface: "自动选择",
    autoUplink: "自动（系统默认路由）",
    unavailable: "不可用",
    running: "运行中",
    stopped: "已停止",
    online: "有网",
    offline: "无网",
    saved: "已保存",
    savedRestart: "已保存并重启热点",
    restarting: "重启中...",
    started: "热点已开启",
    stoppedDone: "热点已关闭",
    noClients: "暂无客户端",
    kick: "下线",
    kickTitle: "确认下线",
    kickConfirm: "确定要让客户端下线？\n{mac}",
    kicked: "已下线",
    confirm: "确定",
    cancel: "取消",
    warningTitle: "开启前确认",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
  },
  "en-US": {
    appTitle: "Wi-Fi Hotspot",
    loading: "Loading...",
    refresh: "Refresh",
    start: "Start Hotspot",
    stop: "Stop Hotspot",
    save: "Save",
    saving: "Saving...",
    status: "Status",
    config: "Config",
    clients: "Clients",
    hotspotDevice: "Hotspot Device",
    uplink: "Uplink",
    address: "Address",
    internet: "Internet",
    password: "Password",
    allowPorts: "Allowed Ports",
    country: "Country Code",
    band: "Band",
    channel: "Channel",
    width: "Bandwidth",
    autoIface: "Auto",
    autoUplink: "Auto (default route)",
    unavailable: "Unavailable",
    running: "Running",
    stopped: "Stopped",
    online: "Online",
    offline: "Offline",
    saved: "Saved",
    savedRestart: "Saved and restarted",
    restarting: "Restarting...",
    started: "Hotspot started",
    stoppedDone: "Hotspot stopped",
    noClients: "No clients",
    kick: "Kick",
    kickTitle: "Confirm kick",
    kickConfirm: "Kick this client?\n{mac}",
    kicked: "Kicked",
    confirm: "OK",
    cancel: "Cancel",
    warningTitle: "Before starting",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
  },
};

const countries = [
  "00",
  "CN",
  "US",
  "JP",
  "KR",
  "AU",
  "CA",
  "GB",
  "DE",
  "FR",
  "IT",
  "ES",
  "NL",
  "BE",
  "CH",
  "AT",
  "SE",
  "NO",
  "DK",
  "FI",
  "RU",
  "IN",
  "BR",
  "MX",
  "AR",
  "CL",
  "CO",
  "PE",
  "ZA",
  "TR",
  "SA",
  "AE",
  "IL",
  "TH",
  "MY",
  "SG",
  "PH",
  "ID",
  "VN",
  "HK",
  "TW",
  "MO",
];

const els = {
  summary: document.getElementById("statusSummary"),
  refresh: document.getElementById("refreshBtn"),
  toggle: document.getElementById("toggleBtn"),
  save: document.getElementById("saveBtn"),
  form: document.getElementById("configForm"),
  iface: document.getElementById("ifaceSelect"),
  uplink: document.getElementById("uplinkSelect"),
  country: document.getElementById("countrySelect"),
  channel: document.getElementById("channelSelect"),
  clients: document.getElementById("clients"),
  clientCount: document.getElementById("clientCount"),
  toast: document.getElementById("toast"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modalTitle"),
  modalBody: document.getElementById("modalBody"),
  modalOk: document.getElementById("modalOk"),
  modalCancel: document.getElementById("modalCancel"),
  statIface: document.getElementById("statIface"),
  statUplink: document.getElementById("statUplink"),
  statIp: document.getElementById("statIp"),
  statInternet: document.getElementById("statInternet"),
  aboutBtn: document.getElementById("btnAbout"),
  aboutModal: document.getElementById("aboutModal"),
};

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_error) {
    return value || "";
  }
}

function cookieValue(name) {
  const prefix = `${name}=`;
  return (
    document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix))
      ?.slice(prefix.length) || ""
  );
}

function storedValue(name) {
  try {
    return localStorage.getItem(name) || sessionStorage.getItem(name) || "";
  } catch (_error) {
    return "";
  }
}

function parentStoredValue(name) {
  try {
    if (!window.parent || window.parent === window) return "";
    return (
      window.parent.localStorage.getItem(name) ||
      window.parent.sessionStorage.getItem(name) ||
      ""
    );
  } catch (_error) {
    return "";
  }
}

function queryValue(name) {
  return new URLSearchParams(location.search).get(name) || "";
}

function documentThemeValue(doc) {
  if (!doc) return "";
  const root = doc.documentElement;
  const body = doc.body;
  return (
    [
      body?.getAttribute("theme-mode"),
      body?.dataset?.theme,
      root?.dataset?.theme,
      root?.classList?.contains("dark") ? "dark" : "",
      root?.classList?.contains("light") ? "light" : "",
    ].find(Boolean) || ""
  );
}

function parentDocumentThemeValue() {
  try {
    if (!window.parent || window.parent === window) return "";
    return documentThemeValue(window.parent.document);
  } catch (_error) {
    return "";
  }
}

function normalizeLanguage(value) {
  const language = safeDecode(value).replace("_", "-");
  return language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function normalizeTheme(value) {
  const theme = safeDecode(value).toLowerCase();
  if (theme.includes("dark") || theme === "night") return "dark";
  if (theme.includes("light") || theme === "day") return "light";
  if (theme === "10") return "light";
  if (theme === "20") return "dark";
  if (["system", "auto", "os"].includes(theme))
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  return "";
}

function currentTheme() {
  return (
    [
      queryValue("theme"),
      cookieValue("fnos-theme-mode"),
      cookieValue("os-theme-mode"),
      storedValue("fnos-theme-mode"),
      storedValue("os-theme-mode"),
      parentStoredValue("fnos-theme-mode"),
      parentStoredValue("os-theme-mode"),
      documentThemeValue(document),
      parentDocumentThemeValue(),
    ]
      .map(normalizeTheme)
      .find(Boolean) ||
    (window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light")
  );
}

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
}

function applyPreferences({ rerender = false } = {}) {
  const nextLanguage = normalizeLanguage(
    cookieValue("language") ||
      queryValue("language") ||
      navigator.language ||
      "zh-CN",
  );
  const changed = nextLanguage !== state.language;
  state.language = nextLanguage;
  state.theme = currentTheme();
  document.documentElement.lang = nextLanguage;
  document.documentElement.dataset.theme = state.theme;
  document.body.dataset.theme = state.theme;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.title = t("appTitle");
  if (state.status) {
    render();
  } else {
    els.summary.textContent = t("loading");
    els.toggle.textContent = t("start");
  }
  if (rerender && changed) render();
}

function showToast(message, error = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", error);
  els.toast.classList.remove("hidden");
  clearTimeout(els.toast._timer);
  els.toast._timer = setTimeout(() => els.toast.classList.add("hidden"), 2600);
}

function setBusy(busy) {
  state.busy = Boolean(busy);
  els.refresh.disabled = state.busy;
  els.save.disabled = state.busy || !state.loaded;
  els.toggle.disabled = state.busy || !state.loaded;
}

function apiUrl(action) {
  const [path, rawQuery = ""] = String(action).split("?", 2);
  const params = new URLSearchParams(rawQuery);
  params.set("lang", state.language === "zh-CN" ? "zh-CN" : "en-US");
  return `${API}/${encodeURIComponent(path)}?${params.toString()}`;
}

async function api(action, { method = "GET", data = null } = {}) {
  const options = { method, cache: "no-store" };
  if (data) {
    options.method = method === "GET" ? "POST" : method;
    options.headers = { "Content-Type": "application/x-www-form-urlencoded" };
    options.body = new URLSearchParams(data);
  }
  const response = await fetch(apiUrl(action), options);
  const result = await response.json();
  if (!response.ok || result.ok === false) {
    throw new Error(
      result.error || result.message || `HTTP ${response.status}`,
    );
  }
  return result;
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
}

function setOptions(select, values, selected, firstLabel = "") {
  const options = [];
  if (firstLabel)
    options.push(`<option value="">${escapeHtml(firstLabel)}</option>`);
  values.forEach((value) => {
    const label = Array.isArray(value) ? value[1] : value;
    const optionValue = Array.isArray(value) ? value[0] : value;
    options.push(
      `<option value="${escapeHtml(optionValue)}">${escapeHtml(label)}</option>`,
    );
  });
  select.innerHTML = options.join("");
  select.value = selected || "";
}

function channelOptions() {
  const band = els.form.elements.band.value || "bg";
  const raw = state.channels[band] || [];
  const parsed = raw.map((item) => {
    const [channel, freq, support] = String(item).split(":");
    return [
      channel,
      `${channel} (${freq} MHz${support === "disabled" ? `, ${t("unavailable")}` : ""})`,
    ];
  });
  if (!parsed.length) {
    return band === "a"
      ? [
          ["36", "36"],
          ["40", "40"],
          ["44", "44"],
          ["48", "48"],
          ["149", "149"],
        ]
      : [
          ["1", "1"],
          ["6", "6"],
          ["11", "11"],
        ];
  }
  return parsed;
}

function fillForm() {
  const cfg = state.config || {};
  els.form.ssid.value = cfg.ssid || "";
  els.form.password.value = cfg.password || "";
  els.form.ipCidr.value = cfg.ipCidr || "";
  els.form.allowPorts.value = cfg.allowPorts || "";
  els.form.band.value = cfg.band || "bg";
  els.form.channelWidth.value = cfg.channelWidth || "20";
  setOptions(els.country, countries, cfg.countryCode || "00");
  setOptions(els.channel, channelOptions(), cfg.channel || "");
}

function collectForm() {
  return {
    iface: els.form.iface.value,
    uplinkIface: els.form.uplinkIface.value,
    ssid: els.form.ssid.value,
    password: els.form.password.value,
    ipCidr: els.form.ipCidr.value,
    allowPorts: els.form.allowPorts.value,
    countryCode: els.form.countryCode.value,
    band: els.form.band.value,
    channel: els.form.channel.value,
    channelWidth: els.form.channelWidth.value,
  };
}

function formatBytes(value) {
  const n = Number(value || 0);
  if (!n) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function renderClients(clients) {
  els.clientCount.textContent = String(clients.length);
  if (!clients.length) {
    els.clients.innerHTML = `<div class="empty">${t("noClients")}</div>`;
    return;
  }
  els.clients.innerHTML = clients
    .map(
      (client) => `
    <div class="client-row">
      <strong>${escapeHtml(client.hostname || "-")}</strong>
      <span>${escapeHtml(client.mac || "-")}</span>
      <span>${escapeHtml(client.ip || "-")}</span>
      <span>${client.signalDbm == null ? "-" : `${client.signalDbm} dBm`}</span>
      <span class="client-muted">${formatBytes(client.rxBytes)} / ${formatBytes(client.txBytes)}</span>
      <button class="danger-btn" type="button" data-kick="${escapeHtml(client.mac || "")}">${t("kick")}</button>
    </div>
  `,
    )
    .join("");
}

function render() {
  const status = state.status || {};
  state.running = Boolean(status.running);
  els.summary.textContent = state.running
    ? `${t("running")} · ${status.hotspotIface || "-"}`
    : t("stopped");
  els.toggle.textContent = state.running ? t("stop") : t("start");
  els.statIface.textContent = status.hotspotIface || status.iface || "-";
  els.statUplink.textContent =
    status.effectiveUplinkIface || status.uplinkIface || "-";
  els.statIp.textContent = status.ip || "-";
  els.statInternet.textContent = status.internetStatus
    ? t("online")
    : t("offline");
  els.statInternet.className = status.internetStatus ? "ok" : "bad";
}

async function loadAll() {
  setBusy(true);
  try {
    const [config, ifaces, uplinks, status, clients] = await Promise.all([
      api("config_get"),
      api("ifaces"),
      api("uplinks"),
      api("status"),
      api("clients"),
    ]);
    state.config = config.config || {};
    state.channels = config.channelOptions || { bg: [], a: [] };
    setOptions(
      els.iface,
      ifaces.ifaces || [],
      state.config.iface || "",
      t("autoIface"),
    );
    setOptions(
      els.uplink,
      uplinks.uplinks || [],
      state.config.uplinkIface || "",
      t("autoUplink"),
    );
    fillForm();
    state.status = status.status || {};
    state.loaded = true;
    render();
    renderClients(clients.clients || []);
  } finally {
    setBusy(false);
  }
}

async function refreshLiveData({ silent = true } = {}) {
  if (!state.loaded || state.busy || state.polling) return;
  state.polling = true;
  try {
    const [status, clients] = await Promise.all([
      api("status"),
      api("clients"),
    ]);
    state.status = status.status || {};
    render();
    renderClients(clients.clients || []);
  } catch (error) {
    if (!silent) showToast(error.message, true);
  } finally {
    state.polling = false;
  }
}

function confirmDialog(title, body) {
  return new Promise((resolve) => {
    els.modalTitle.textContent = title;
    els.modalBody.textContent = body;
    els.modal.classList.remove("hidden");
    const done = (value) => {
      els.modal.classList.add("hidden");
      els.modalOk.onclick = null;
      els.modalCancel.onclick = null;
      resolve(value);
    };
    els.modalOk.onclick = () => done(true);
    els.modalCancel.onclick = () => done(false);
  });
}

async function saveConfig() {
  if (!state.loaded) return;
  const shouldRestart = state.running;
  setBusy(true);
  els.save.textContent = t("saving");
  try {
    await api("config_set", { method: "POST", data: collectForm() });
    if (shouldRestart) {
      els.save.textContent = t("restarting");
      await api("stop");
      await api("start");
      showToast(t("savedRestart"));
    } else {
      showToast(t("saved"));
    }
    await loadAll();
  } finally {
    setBusy(false);
    els.save.textContent = t("save");
  }
}

async function toggleHotspot() {
  if (!state.loaded) return;
  setBusy(true);
  try {
    if (state.running) {
      await api("stop");
      showToast(t("stoppedDone"));
    } else {
      await api("config_set", { method: "POST", data: collectForm() });
      const pre = await api("stpre");
      if (pre.abort) throw new Error(pre.error || "start aborted");
      if (Array.isArray(pre.warnings) && pre.warnings.length) {
        const ok = await confirmDialog(
          t("warningTitle"),
          pre.warnings.join("\n"),
        );
        if (!ok) return;
      }
      await api("start");
      showToast(t("started"));
    }
    await loadAll();
  } finally {
    setBusy(false);
  }
}

els.refresh.addEventListener("click", () =>
  loadAll().catch((error) => showToast(error.message, true)),
);
els.save.addEventListener("click", () =>
  saveConfig().catch((error) => showToast(error.message, true)),
);
els.toggle.addEventListener("click", () =>
  toggleHotspot().catch((error) => showToast(error.message, true)),
);
els.aboutBtn.addEventListener("click", () =>
  els.aboutModal.classList.remove("hidden"),
);
document.addEventListener("click", (event) => {
  if (event.target.closest("[data-close]")) {
    const modal = event.target.closest(".modal");
    if (modal) modal.classList.add("hidden");
    return;
  }
  if (event.target === els.aboutModal) {
    els.aboutModal.classList.add("hidden");
    return;
  }
});
els.form.elements.band.addEventListener("change", () =>
  setOptions(els.channel, channelOptions(), ""),
);
els.clients.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-kick]");
  if (!button) return;
  const mac = button.dataset.kick;
  const ok = await confirmDialog(t("kickTitle"), t("kickConfirm", { mac }));
  if (!ok) return;
  await api(`kick?mac=${encodeURIComponent(mac)}`);
  showToast(t("kicked"));
  await loadAll();
});

applyPreferences();
window
  .matchMedia?.("(prefers-color-scheme: dark)")
  .addEventListener?.("change", () => applyPreferences());
window.addEventListener("storage", () => applyPreferences({ rerender: true }));
setInterval(() => refreshLiveData(), 5000);
setBusy(true);
loadAll().catch((error) => {
  state.loaded = false;
  setBusy(false);
  showToast(error.message, true);
});
