import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

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
  countryLocked: false,
  regdom: "00",
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
    ssid: "SSID",
    ipCidr: "IP/CIDR",
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
    showPassword: "显示密码",
    hidePassword: "隐藏密码",
    countryLockedHint: "当前系统不允许修改国家码",
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
    ssid: "SSID",
    ipCidr: "IP/CIDR",
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
    showPassword: "Show password",
    hidePassword: "Hide password",
    countryLockedHint:
      "Changing the country code is not allowed on this system",
  },
};

// 错误码 → 前端多语言映射。后端只返回 { ok:false, code, params }，
// 前端通过 t("err_" + code, params) 产生本地化文案。
const ERRORS = {
  "zh-CN": {
    field_ssid: "SSID 不能为空",
    field_password: "密码长度至少 8 位",
    field_ipCidr: "IP/CIDR 格式无效（例如 192.168.12.1/24）",
    field_allowPorts: "放行端口格式不正确",
    field_country: "国家码需为空的或 2 位字母（如 CN/US）",
    field_band: "频段需为 2.4G(bg) 或 5G(a)",
    field_channel: "信道需为数字，且在该频段的合法范围内（bg:1-14，a:≥34）",
    field_channelWidth: "带宽需为 20/40/80/160，且 2.4G 仅支持 20/40",
    field_uplinkIface: "共享网卡名称无效",
    field_IP: "配置校验失败",
    err_config_invalid: "配置无效：{field}",
    err_save_failed: "保存配置失败（配置文件不可写）",
    err_country_unsupported: "系统不支持设置国家码 {country}",
    err_channel_disabled:
      "信道 {channel} 在当前国家码下不可用（regdom={regdom}）",
    err_channel_no_ir:
      "信道 {channel} 标记为 no IR（regdom={regdom}），无线热点可能无法正常工作。请改用 2.4G（bg）信道",
    err_no_wifi_iface: "未检测到 Wi-Fi 设备，请检查 'nmcli dev status'",
    err_iface_not_wifi: "设备 {iface} 不是 Wi-Fi 设备，请换用无线网卡",
    err_uplink_same_as_hotspot:
      "共享网卡不能与热点网卡相同（{iface}），请改选其它网卡或留空(自动)",
    err_ap_not_supported: "设备 {iface} 不支持 AP/热点模式，请换用其它无线网卡",
    err_nmcli_add_failed: "创建热点连接失败",
    err_nmcli_mod_failed: "配置热点连接失败",
    err_nmcli_up_failed: "热点连接启动失败（nmcli）",
    err_setup_timeout: "热点启动超时（等待 {wait} 秒）",
    err_dnsmasq_failed: "DNS/DHCP 服务(dnsmasq)启动失败",
    err_client_invalid_mac: "无效的 MAC 地址",
    err_client_no_wifi_iface: "未检测到 Wi-Fi 设备",
    err_client_iw_missing: "缺少 iw 工具",
    err_kick_failed: "下线客户端失败",
    err_missing_action: "缺少操作(action)",
    err_unsupported_action: "不支持的操作：{action}",
    err_unexpected: "发生意外错误（步骤 {step}）",
    warn_country_00: "国家码为 00，5GHz 频段可能未启用",
    warn_no_sta_ap_interrupt:
      "网卡不支持 STA+AP；热点将使用 {iface}（可能中断 Wi-Fi）",
    warn_no_sta_ap_disconnect: "网卡不支持 STA+AP；将断开连接 {con}（{iface}）",
    warn_channel_disabled: "信道 {channel} 当前不可用（regdom={regdom}）",
    warn_channel_no_ir:
      "信道 {channel} 标记为 no IR（regdom={regdom}），热点可能不被允许",
    warn_low_tx_power:
      "驱动 {driver} 上报的发射率过低（{txPower} dBm），热点可启动但覆盖/发现可能较差。建议先用 2.4G/20MHz",
  },
  "en-US": {
    field_ssid: "SSID is required",
    field_password: "Password must be at least 8 characters",
    field_ipCidr: "Invalid IP/CIDR (e.g. 192.168.12.1/24)",
    field_allowPorts: "Invalid allowed ports format",
    field_country: "Country code must be empty or a 2-letter code (e.g. CN/US)",
    field_band: "Band must be bg (2.4G) or a (5G)",
    field_channel:
      "Channel must be a number within the valid range (bg 1-14, a >= 34)",
    field_channelWidth:
      "Bandwidth must be 20/40/80/160; 2.4G only supports 20/40",
    field_uplinkIface: "Invalid uplink interface name",
    err_config_invalid: "Invalid config: {field}",
    err_save_failed: "Failed to save config (config file not writable)",
    err_country_unsupported:
      "System does not support setting country code {country}",
    err_channel_disabled:
      "Channel {channel} is not available under the current country code (regdom={regdom})",
    err_channel_no_ir:
      "Channel {channel} is marked 'no IR' (regdom={regdom}); the hotspot may not work. Use a 2.4G channel instead",
    err_no_wifi_iface: "No Wi-Fi device found. Check 'nmcli dev status'",
    err_iface_not_wifi: "Device {iface} is not a Wi-Fi device",
    err_uplink_same_as_hotspot:
      "Uplink cannot be the same as hotspot iface ({iface}). Choose another or leave empty (auto)",
    err_ap_not_supported:
      "Device {iface} does not support AP/hotspot mode. Use another Wi-Fi adapter",
    err_nmcli_add_failed: "Failed to create hotspot connection",
    err_nmcli_mod_failed: "Failed to configure hotspot connection",
    err_nmcli_up_failed: "Failed to bring up hotspot connection (nmcli)",
    err_setup_timeout: "Hotspot setup timed out after {wait}s",
    err_dnsmasq_failed: "DNS/DHCP service (dnsmasq) failed to start",
    err_client_invalid_mac: "Invalid MAC address",
    err_client_no_wifi_iface: "No Wi-Fi device found",
    err_client_iw_missing: "Missing iw tool",
    err_kick_failed: "Failed to kick client",
    err_missing_action: "Missing action",
    err_unsupported_action: "Unsupported action: {action}",
    err_unexpected: "Unexpected error (step {step})",
    warn_country_00: "Country code is 00; the 5GHz band may not be enabled",
    warn_no_sta_ap_interrupt:
      "Adapter does not support STA+AP; hotspot will use {iface} (may interrupt Wi-Fi)",
    warn_no_sta_ap_disconnect:
      "Adapter does not support STA+AP; will disconnect {con} on {iface}",
    warn_channel_disabled:
      "Channel {channel} is not available (regdom={regdom})",
    warn_channel_no_ir:
      "Channel {channel} is marked 'no IR' (regdom={regdom}); hotspot may not be allowed",
    warn_low_tx_power:
      "Driver {driver} is reporting very low TX power ({txPower} dBm). Hotspot can start but coverage may be poor. Try 2.4G/20MHz first",
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
  countryLocked: document.getElementById("countryLocked"),
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

function applyLanguage() {
  const language = String(platformConfig.language || "").replace("_", "-");
  const resolved = language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
  const changed = resolved !== state.language;
  state.language = resolved;
  document.documentElement.lang = resolved;
  return changed;
}

function t(key, params = {}) {
  const lang = state.language;
  const messages = I18N[lang] || I18N["zh-CN"];
  const errors = ERRORS[lang] || ERRORS["zh-CN"];
  const text =
    messages[key] ||
    I18N["zh-CN"][key] ||
    errors[key] ||
    ERRORS["zh-CN"][key] ||
    key;
  return String(text).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
}

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
}

function applyPreferences({ rerender = false } = {}) {
  const languageChanged = applyLanguage();
  applyTheme();
  const title = t("appTitle");
  document.title = title;
  if (sdk.setTitle) {
    sdk.setTitle(title).catch(() => {});
  }

  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
    node.setAttribute("aria-label", t(node.dataset.i18nTitle));
  });

  if (rerender && languageChanged) {
    render();
  }
  return languageChanged;
}

async function api(action, data = {}) {
  // token 由 fnOS 网关注入；前端同样不转发 token
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    credentials: "include",
    body: JSON.stringify({ action, ...data }),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) {
    // 新协议优先：code + params → t("err_"+code, params)
    if (result && result.code) {
      throw new Error(t("err_" + result.code, result.params || {}));
    }
    // 兼容旧字段
    throw new Error(result.message || `HTTP ${response.status}`);
  }
  return result;
}

// 前端校验：能挪到前端的校验都在这里完成，返回错误 key+params；合法返回 null。
function validateConfig() {
  const form = collectForm();
  if (!form.ssid)
    return { key: "config_invalid", params: { field: t("field_ssid") } };
  if (String(form.password).length < 8)
    return { key: "config_invalid", params: { field: t("field_password") } };
  if (form.ipCidr && !/^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/.test(form.ipCidr))
    return { key: "config_invalid", params: { field: t("field_ipCidr") } };
  if (form.allowPorts && !isValidPorts(form.allowPorts))
    return { key: "config_invalid", params: { field: t("field_allowPorts") } };
  if (
    form.countryCode &&
    form.countryCode !== "00" &&
    !/^[A-Za-z]{2}$/.test(form.countryCode)
  )
    return { key: "config_invalid", params: { field: t("field_country") } };
  if (!["bg", "a"].includes(form.band))
    return { key: "config_invalid", params: { field: t("field_band") } };
  if (!/^\d+$/.test(form.channel)) {
    return { key: "config_invalid", params: { field: t("field_channel") } };
  }
  const ch = Number(form.channel);
  if (form.band === "bg" && !(ch >= 1 && ch <= 14))
    return { key: "config_invalid", params: { field: t("field_channel") } };
  if (form.band === "a" && ch < 34)
    return { key: "config_invalid", params: { field: t("field_channel") } };
  if (!["20", "40", "80", "160"].includes(form.channelWidth))
    return {
      key: "config_invalid",
      params: { field: t("field_channelWidth") },
    };
  if (form.band === "bg" && !["20", "40"].includes(form.channelWidth))
    return {
      key: "config_invalid",
      params: { field: t("field_channelWidth") },
    };
  return null;
}

function isValidPorts(value) {
  // 与后端 allow_ports_to_rules 一致：允许 "80"、"8000-9000"、可选 "/tcp|/udp" 后缀、逗号/空格分隔组合
  const parts = String(value).split(/[, ]+/).filter(Boolean);
  if (!parts.length) return true;
  return parts.every((part) => {
    let port = part;
    if (part.includes("/")) {
      const slash = part.lastIndexOf("/");
      const proto = part.slice(slash + 1).toLowerCase();
      if (proto !== "tcp" && proto !== "udp") return false;
      port = part.slice(0, slash);
    }
    const from = port.includes("-") ? port.split("-", 1)[0] : port;
    const to = port.includes("-") ? port.slice(port.indexOf("-") + 1) : port;
    if (!/^\d+$/.test(from) || !/^\d+$/.test(to)) return false;
    const nFrom = Number(from);
    const nTo = Number(to);
    if (nFrom < 1 || nFrom > 65535 || nTo < 1 || nTo > 65535) return false;
    if (nFrom > nTo) return false;
    return true;
  });
}

async function openFileManager(path) {
  // 打开目录：调用 fnOS 文件管理器
  await sdk.openFileManager(path);
}

function showToast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
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

function applyCountryLock() {
  // 国家码不可修改时：禁用下拉框并显示提示，收藏保存时固定为当前 regdom。
  const locked = state.countryLocked;
  els.country.disabled = locked;
  if (els.countryLocked) {
    els.countryLocked.classList.toggle("hidden", !locked);
  }
  if (locked && els.country.value !== state.regdom) {
    els.country.value = state.regdom || "00";
  }
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
  applyCountryLock();
}

function collectForm() {
  // 国家码锁定时不得改动/保存，固定为系统真实 regdom
  const countryCode = state.countryLocked
    ? state.regdom || "00"
    : els.form.countryCode.value;
  return {
    iface: els.form.iface.value,
    uplinkIface: els.form.uplinkIface.value,
    ssid: els.form.ssid.value,
    password: els.form.password.value,
    ipCidr: els.form.ipCidr.value,
    allowPorts: els.form.allowPorts.value,
    countryCode,
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
    state.countryLocked = Boolean(config.countryLocked);
    state.regdom = config.regdom || "00";
    applyCountryLock();
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
  const invalid = validateConfig();
  if (invalid) {
    showToast(t(invalid.key, invalid.params), true);
    return;
  }
  const shouldRestart = state.running;
  setBusy(true);
  els.save.textContent = t("saving");
  try {
    await api("config_set", collectForm());
    if (shouldRestart) {
      els.save.textContent = t("restarting");
      await api("stop");
      await api("start");
      showToast(t("savedRestart"));
    } else {
      showToast(t("saved"));
    }
    await loadAll();
  } catch (error) {
    // 保存/重启失败：表单所有参数恢复到当前已保存（运行）的配置。
    // state.config 只在 loadAll() 成功后才更新，故此处仍为改动前的值。
    fillForm();
    throw error;
  } finally {
    setBusy(false);
    els.save.textContent = t("save");
  }
}

async function toggleHotspot() {
  if (!state.loaded) return;
  const invalid = validateConfig();
  if (invalid) {
    showToast(t(invalid.key, invalid.params), true);
    return;
  }
  setBusy(true);
  try {
    if (state.running) {
      await api("stop");
      showToast(t("stoppedDone"));
    } else {
      await api("config_set", collectForm());
      const pre = await api("stpre");
      if (pre.abort) {
        // 预检失败：优先按 code 映射，兼容旧 error 字段
        if (pre.code) {
          throw new Error(t("err_" + pre.code, pre.params || {}));
        }
        throw new Error(pre.error || "start aborted");
      }
      if (Array.isArray(pre.warnings) && pre.warnings.length) {
        const lines = renderWarnings(pre.warnings);
        const ok = await confirmDialog(t("warningTitle"), lines.join("\n"));
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

// 语义化警告：后端返回 [{code, params}]（或兼容旧版 {text}），本地化渲染。
function renderWarnings(warnings) {
  return warnings.map((warning) => {
    if (warning && warning.code) {
      return t("warn_" + warning.code, warning.params || {});
    }
    // 兼容旧格式（纯文本或 {text}）
    if (warning && warning.text) return String(warning.text);
    return String(warning ?? "");
  });
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
// 密码显示/隐藏切换
document.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-pw-toggle]");
  if (!toggle) return;
  const wrap = toggle.closest(".pw-wrap");
  if (!wrap) return;
  const input = wrap.querySelector("input");
  if (!input) return;
  const shown = input.type === "text";
  input.type = shown ? "password" : "text";
  toggle.setAttribute("aria-pressed", String(!shown));
  toggle.setAttribute(
    "aria-label",
    shown ? t("showPassword") : t("hidePassword"),
  );
  input.focus({ preventScroll: true });
});
els.clients.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-kick]");
  if (!button) return;
  const mac = button.dataset.kick;
  const ok = await confirmDialog(t("kickTitle"), t("kickConfirm", { mac }));
  if (!ok) return;
  await api("kick", { mac });
  showToast(t("kicked"));
  await loadAll();
});

window.addEventListener("load", async () => {
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

  setInterval(() => refreshLiveData(), 5000);
  setBusy(true);
  loadAll().catch((error) => {
    state.loaded = false;
    setBusy(false);
    showToast(error.message, true);
  });
});
