import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

const state = {
  language: "zh-CN",
  theme: "light",
  role: "client",
  adapter: null,
  paired: [],
  available: [],
  audio: {
    sinks: [],
    sources: [],
    bluetoothAudio: [],
    defaultSink: "",
    defaultSource: "",
  },
  sendTarget: "",
  scanning: false,
  scanTimer: null,
  serverAdvertise: false,
  serverProfiles: [],
  incomingDevices: [],
  receivedFiles: [],
  transferHistory: [],
  tethering: { active: false, bridge: "", ip: "", clients: 0, clientList: [] },
  obexAgentReady: true,
  loaded: false,
  busy: false,
  polling: false,
};

const I18N = {
  "zh-CN": {
    appTitle: "蓝牙管理",
    loading: "正在加载...",
    refresh: "刷新",
    scan: "扫描设备",
    stopScan: "停止扫描",
    adapter: "适配器",
    bluetooth: "蓝牙",
    discoverable: "可发现",
    pairable: "可配对",
    adapterAddr: "适配器地址",
    adapterName: "适配器名称",
    pairedCount: "已配对",
    connectedCount: "已连接",
    pairedDevices: "已配对设备",
    availableDevices: "可用设备",
    audioSettings: "音频设置",
    fileTransfer: "文件传输",
    outputDevice: "输出设备",
    inputDevice: "输入设备",
    targetDevice: "目标设备",
    filePath: "文件路径",
    sendFile: "发送文件",
    browse: "浏览",
    connect: "连接",
    disconnect: "断开",
    pair: "配对",
    remove: "移除",
    trust: "添加信任",
    untrust: "取消信任",
    noAdapter: "未检测到蓝牙适配器",
    powered: "已开启",
    poweredOff: "已关闭",
    scanning: "扫描中",
    noPairedDevices: "暂无已配对设备",
    noAvailableDevices: "暂无可用设备",
    confirm: "确定",
    cancel: "取消",
    confirmPair: "确认配对",
    confirmPairMsg: "确定要配对此设备？\n{name} ({address})",
    confirmRemove: "确认移除",
    confirmRemoveMsg: "确定要移除此设备？\n{name} ({address})",
    confirmDisconnect: "确认断开",
    confirmDisconnectMsg: "确定要断开此设备？\n{name} ({address})",
    pairedSuccess: "配对成功",
    connectedSuccess: "连接成功",
    disconnectedSuccess: "已断开连接",
    processing: "处理中...",
    operationBusy: "正在处理，请稍候",
    removedSuccess: "已移除设备",
    trustedSuccess: "已设为信任",
    untrustedSuccess: "已取消信任",
    fileSent: "文件已发送",
    powerOn: "蓝牙已开启",
    powerOff: "蓝牙已关闭",
    discoverableOn: "已设为可发现",
    discoverableOff: "已取消可发现",
    pairableOn: "已设为可配对",
    pairableOff: "已取消可配对",
    sinkSet: "输出设备已切换",
    sourceSet: "输入设备已切换",
    selectDevice: "选择设备",
    typeAudio: "音频",
    typeKeyboard: "键盘",
    typeMouse: "鼠标",
    typeDisplay: "显示器",
    typePhone: "手机",
    typeTablet: "平板",
    typePrinter: "打印机",
    typeCamera: "相机",
    typeGamepad: "游戏手柄",
    typeComputer: "电脑",
    typeOther: "其他",
    sending: "发送中...",
    roleClient: "客户端",
    roleServer: "服务端",
    serverSettings: "服务端设置",
    serverAlias: "设备名称",
    serverProfiles: "服务 Profile",
    incomingDevices: "已连接设备",
    startAdvertise: "开始广播",
    stopAdvertise: "停止广播",
    advertiseOn: "已开始广播",
    advertiseOff: "已停止广播",
    aliasSet: "设备名称已设置",
    noProfiles: "暂无可用 Profile",
    noIncomingDevices: "暂无设备连接",
    serverActive: "服务端运行中",
    serverInactive: "服务端未启动",
    acceptPair: "接受配对",
    receivedFiles: "已接收文件",
    noReceivedFiles: "暂无已接收文件",
    savePath: "保存路径",
    transferHistory: "已发送文件",
    noTransferHistory: "暂无发送记录",
    sendDir: "发送",
    receiveDir: "接收",
    eta: "剩余",
    queued: "排队中",
    active: "传输中",
    complete: "完成",
    error: "失败",
    retrying: "重试中",
    transferComplete: "传输完成",
    transferFailed: "传输失败",
    successStatus: "成功",
    failedStatus: "失败",
    clearAll: "清空",
    cleared: "已清空",
    delete: "删除",
    tethering: "蓝牙共享网络",
    tetheringBridge: "网桥接口",
    tetheringGateway: "网关地址",
    tetheringClients: "已连接客户端",
    uploadSpeed: "上传",
    downloadSpeed: "下载",
    tetheringBridgeIP: "网桥地址",
    tetheringOn: "已开启网络共享",
    tetheringOff: "已关闭网络共享",
    noTetheringClients: "暂无客户端连接",
    clientMAC: "MAC 地址",
    clientIP: "IP 地址",
    clientIface: "接口",
    obexAgentWarning: "文件接收服务未就绪，无法接收文件",
    fixNow: "立即修复",
    obexAgentFixed: "文件接收服务已修复",
    obexAgentFixFailed: "修复失败，请重试",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
  },
  "en-US": {
    appTitle: "Bluetooth",
    loading: "Loading...",
    refresh: "Refresh",
    scan: "Scan Devices",
    stopScan: "Stop Scan",
    adapter: "Adapter",
    bluetooth: "Bluetooth",
    discoverable: "Discoverable",
    pairable: "Pairable",
    adapterAddr: "Adapter Address",
    adapterName: "Adapter Name",
    pairedCount: "Paired",
    connectedCount: "Connected",
    pairedDevices: "Paired Devices",
    availableDevices: "Available Devices",
    audioSettings: "Audio Settings",
    fileTransfer: "File Transfer",
    outputDevice: "Output Device",
    inputDevice: "Input Device",
    targetDevice: "Target Device",
    filePath: "File Path",
    sendFile: "Send File",
    browse: "Browse",
    connect: "Connect",
    disconnect: "Disconnect",
    pair: "Pair",
    remove: "Remove",
    trust: "Add Trust",
    untrust: "Untrust",
    noAdapter: "No Bluetooth adapter detected",
    powered: "Powered On",
    poweredOff: "Powered Off",
    scanning: "Scanning",
    noPairedDevices: "No paired devices",
    noAvailableDevices: "No available devices",
    confirm: "OK",
    cancel: "Cancel",
    confirmPair: "Confirm Pair",
    confirmPairMsg: "Pair this device?\n{name} ({address})",
    confirmRemove: "Confirm Remove",
    confirmRemoveMsg: "Remove this device?\n{name} ({address})",
    confirmDisconnect: "Confirm Disconnect",
    confirmDisconnectMsg: "Disconnect this device?\n{name} ({address})",
    pairedSuccess: "Paired successfully",
    connectedSuccess: "Connected successfully",
    disconnectedSuccess: "Disconnected",
    processing: "Processing...",
    operationBusy: "Please wait...",
    removedSuccess: "Device removed",
    trustedSuccess: "Device trusted",
    untrustedSuccess: "Device untrusted",
    fileSent: "File sent",
    powerOn: "Bluetooth powered on",
    powerOff: "Bluetooth powered off",
    discoverableOn: "Discoverable enabled",
    discoverableOff: "Discoverable disabled",
    pairableOn: "Pairable enabled",
    pairableOff: "Pairable disabled",
    sinkSet: "Output device changed",
    sourceSet: "Input device changed",
    selectDevice: "Select device",
    typeAudio: "Audio",
    typeKeyboard: "Keyboard",
    typeMouse: "Mouse",
    typeDisplay: "Display",
    typePhone: "Phone",
    typeTablet: "Tablet",
    typePrinter: "Printer",
    typeCamera: "Camera",
    typeGamepad: "Gamepad",
    typeComputer: "Computer",
    typeOther: "Other",
    sending: "Sending...",
    roleClient: "Client",
    roleServer: "Server",
    serverSettings: "Server Settings",
    serverAlias: "Device Name",
    serverProfiles: "Service Profiles",
    incomingDevices: "Connected Devices",
    startAdvertise: "Start Advertise",
    stopAdvertise: "Stop Advertise",
    advertiseOn: "Advertising started",
    advertiseOff: "Advertising stopped",
    aliasSet: "Device name set",
    noProfiles: "No profiles available",
    noIncomingDevices: "No devices connected",
    serverActive: "Server active",
    serverInactive: "Server inactive",
    acceptPair: "Accept Pairing",
    receivedFiles: "Received Files",
    noReceivedFiles: "No received files",
    savePath: "Save Path",
    transferHistory: "Sent Files",
    noTransferHistory: "No sent records",
    sendDir: "Send",
    receiveDir: "Receive",
    eta: "ETA",
    queued: "Queued",
    active: "Transferring",
    complete: "Complete",
    error: "Error",
    retrying: "Retrying",
    transferComplete: "Transfer complete",
    transferFailed: "Transfer failed",
    successStatus: "Success",
    failedStatus: "Failed",
    clearAll: "Clear",
    cleared: "Cleared",
    delete: "Delete",
    tethering: "Bluetooth Tethering",
    tetheringBridge: "Bridge Interface",
    tetheringGateway: "Gateway",
    tetheringClients: "Connected Clients",
    uploadSpeed: "Upload",
    downloadSpeed: "Download",
    tetheringBridgeIP: "Bridge IP",
    tetheringOn: "Tethering enabled",
    tetheringOff: "Tethering disabled",
    noTetheringClients: "No clients connected",
    clientMAC: "MAC Address",
    clientIP: "IP Address",
    clientIface: "Interface",
    obexAgentWarning: "File receiving service not ready, cannot receive files",
    fixNow: "Fix Now",
    obexAgentFixed: "File receiving service fixed",
    obexAgentFixFailed: "Fix failed, please retry",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
  },
};

const DEVICE_ICONS = {
  audio: "🎧",
  keyboard: "⌨️",
  mouse: "🖱️",
  display: "🖥️",
  phone: "📱",
  tablet: "📟",
  printer: "🖨️",
  camera: "📷",
  gamepad: "🎮",
  computer: "💻",
  other: "🔗",
};

const els = {
  summary: document.getElementById("statusSummary"),
  refresh: document.getElementById("refreshBtn"),
  scan: document.getElementById("scanBtn"),
  powerToggle: document.getElementById("powerToggle"),
  discoverableToggle: document.getElementById("discoverableToggle"),
  pairableToggle: document.getElementById("pairableToggle"),
  statAddr: document.getElementById("statAddr"),
  statName: document.getElementById("statName"),
  statPaired: document.getElementById("statPaired"),
  statConnected: document.getElementById("statConnected"),
  pairedDevices: document.getElementById("pairedDevices"),
  pairedCount: document.getElementById("pairedCount"),
  availableDevices: document.getElementById("availableDevices"),
  scanStatus: document.getElementById("scanStatus"),
  sinkSelect: document.getElementById("sinkSelect"),
  sourceSelect: document.getElementById("sourceSelect"),
  sendTargetSelect: document.getElementById("sendTargetSelect"),
  sendFilePath: document.getElementById("sendFilePath"),
  sendFileBtn: document.getElementById("sendFileBtn"),
  pickFileBtn: document.getElementById("pickFileBtn"),
  toast: document.getElementById("toast"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modalTitle"),
  modalBody: document.getElementById("modalBody"),
  modalOk: document.getElementById("modalOk"),
  modalCancel: document.getElementById("modalCancel"),
  roleClientBtn: document.getElementById("roleClientBtn"),
  roleServerBtn: document.getElementById("roleServerBtn"),
  clientMode: document.getElementById("clientMode"),
  serverMode: document.getElementById("serverMode"),
  serverPowerToggle: document.getElementById("serverPowerToggle"),
  serverDiscoverableToggle: document.getElementById("serverDiscoverableToggle"),
  serverPairableToggle: document.getElementById("serverPairableToggle"),
  serverAliasInput: document.getElementById("serverAliasInput"),
  serverAddr: document.getElementById("serverAddr"),
  serverAdvertiseBtn: document.getElementById("serverAdvertiseBtn"),
  obexAgentWarning: document.getElementById("obexAgentWarning"),
  fixObexAgentBtn: document.getElementById("fixObexAgentBtn"),
  serverProfilesList: document.getElementById("serverProfilesList"),
  incomingDevices: document.getElementById("incomingDevices"),
  incomingCount: document.getElementById("incomingCount"),
  receivedFilesList: document.getElementById("receivedFilesList"),
  clearReceivedBtn: document.getElementById("clearReceivedBtn"),
  transferProgress: document.getElementById("transferProgress"),
  transferHistoryList: document.getElementById("transferHistoryList"),
  clearHistoryBtn: document.getElementById("clearHistoryBtn"),
  tetheringToggle: document.getElementById("tetheringToggle"),
  tetherBridgeIP: document.getElementById("tetherBridgeIP"),
  tetherBridge: document.getElementById("tetherBridge"),
  tetherClients: document.getElementById("tetherClients"),
  tetheringClientsList: document.getElementById("tetheringClientsList"),
  aboutBtn: document.getElementById("aboutBtn"),
  aboutModal: document.getElementById("aboutModal"),
};

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_e) {
    return value || "";
  }
}

function applyLanguage() {
  const language = safeDecode(platformConfig.language).replace("_", "-");
  const resolved = language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
  const changed = resolved !== state.language;
  state.language = resolved;
  document.documentElement.lang = resolved;
  return changed;
}

function applyTheme() {
  // fnOS 宿主可能返回 { theme: "dark" } 对象，先解包再规范化
  const value = platformConfig.theme;
  const v =
    value && typeof value === "object" && "theme" in value
      ? value.theme
      : value;
  const theme = safeDecode(v).toLowerCase() === "dark" ? "dark" : "light";
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  document.body.dataset.theme = theme;
  return theme;
}

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
}

function applyPreferences({ rerender = false } = {}) {
  const changed = applyLanguage();
  applyTheme();
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
  const title = t("appTitle");
  document.title = title;
  if (sdk.setTitle) {
    sdk.setTitle(title).catch(() => {});
  }
  if (state.loaded) render();
  else els.summary.textContent = t("loading");
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
  els.scan.disabled = state.busy || !state.loaded;
  els.sendFileBtn.disabled = state.busy;
}

async function api(action, data = {}) {
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    credentials: "include",
    body: JSON.stringify({ action, ...data }),
  });
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

function deviceIcon(type) {
  return DEVICE_ICONS[type] || DEVICE_ICONS.other;
}

function typeName(type) {
  const key = `type${type.charAt(0).toUpperCase()}${type.slice(1)}`;
  return t(key) || type;
}

function rssiToLevel(rssi) {
  if (rssi == null) return 0;
  if (rssi >= -50) return 4;
  if (rssi >= -65) return 3;
  if (rssi >= -75) return 2;
  if (rssi >= -85) return 1;
  return 0;
}

function signalBars(rssi) {
  const level = rssiToLevel(rssi);
  let bars = "";
  for (let i = 1; i <= 4; i++) {
    bars += `<div class="signal-bar${i <= level ? " active" : ""}"></div>`;
  }
  return `<div class="device-signal" title="${rssi != null ? rssi + " dBm" : ""}">${bars}</div>`;
}

function renderDeviceRow(dev, isPaired) {
  const icon = deviceIcon(dev.deviceType);
  const name = escapeHtml(dev.alias || dev.name || "Unknown");
  const addr = escapeHtml(dev.address);
  const statusBadge = dev.connected
    ? '<span class="ok">●</span>'
    : '<span class="bad">○</span>';

  let actions = "";
  if (isPaired) {
    if (dev.connected) {
      actions += `<button class="ghost-btn" type="button" data-action="disconnect" data-addr="${addr}">${t("disconnect")}</button>`;
    } else {
      actions += `<button class="primary-btn" type="button" data-action="connect" data-addr="${addr}">${t("connect")}</button>`;
    }
    if (dev.trusted) {
      actions += `<button class="ghost-btn" type="button" data-action="untrust" data-addr="${addr}">${t("untrust")}</button>`;
    } else {
      actions += `<button class="ghost-btn" type="button" data-action="trust" data-addr="${addr}">${t("trust")}</button>`;
    }
    actions += `<button class="danger-btn" type="button" data-action="remove" data-addr="${addr}">${t("remove")}</button>`;
  } else {
    actions += `<button class="primary-btn" type="button" data-action="pair" data-addr="${addr}">${t("pair")}</button>`;
  }

  return `<div class="device-row" data-address="${addr}">
    <div class="device-icon">${icon}</div>
    <div class="device-info">
      <div class="device-name">${statusBadge} ${name}</div>
      <div class="device-addr">${addr}</div>
    </div>
    ${signalBars(dev.rssi)}
    <div class="device-type-badge">${escapeHtml(typeName(dev.deviceType))}</div>
    <div class="device-actions">${actions}</div>
  </div>`;
}

function renderDevices() {
  els.pairedCount.textContent = String(state.paired.length);
  if (!state.paired.length) {
    els.pairedDevices.innerHTML = `<div class="empty">${t("noPairedDevices")}</div>`;
  } else {
    els.pairedDevices.innerHTML = state.paired
      .map((dev) => renderDeviceRow(dev, true))
      .join("");
  }

  if (!state.available.length) {
    els.availableDevices.innerHTML = `<div class="empty">${t("noAvailableDevices")}</div>`;
  } else {
    els.availableDevices.innerHTML = state.available
      .map((dev) => renderDeviceRow(dev, false))
      .join("");
  }

  const sendTargets = state.paired.map((dev) => [
    dev.address,
    `${dev.alias || dev.name || "Unknown"} (${dev.address})`,
  ]);
  const savedTarget = els.sendTargetSelect.value || state.sendTarget;
  setOptions(els.sendTargetSelect, sendTargets, savedTarget, t("selectDevice"));
}

function renderAdapter() {
  const adapter = state.adapter;
  if (!adapter) {
    els.summary.textContent = t("noAdapter");
    els.powerToggle.classList.remove("active");
    els.discoverableToggle.classList.remove("active");
    els.pairableToggle.classList.remove("active");
    els.statAddr.textContent = "-";
    els.statName.textContent = "-";
    return;
  }
  els.summary.textContent = adapter.powered
    ? `${t("powered")} · ${adapter.name || adapter.address}`
    : t("poweredOff");
  els.powerToggle.classList.toggle("active", adapter.powered);
  els.powerToggle.setAttribute("aria-checked", String(adapter.powered));
  els.discoverableToggle.classList.toggle("active", adapter.discoverable);
  els.discoverableToggle.setAttribute(
    "aria-checked",
    String(adapter.discoverable),
  );
  els.pairableToggle.classList.toggle("active", adapter.pairable);
  els.pairableToggle.setAttribute("aria-checked", String(adapter.pairable));
  els.statAddr.textContent = adapter.address || "-";
  els.statName.textContent = adapter.alias || adapter.name || "-";
  els.statPaired.textContent = String(state.paired.length);
  els.statConnected.textContent = String(
    state.paired.filter((d) => d.connected).length,
  );
}

function renderAudio() {
  const audio = state.audio;
  if (!audio.audioAvailable) {
    els.sinkSelect.innerHTML = "";
    els.sinkSelect.disabled = true;
    els.sourceSelect.innerHTML = "";
    els.sourceSelect.disabled = true;
    const noAudio =
      state.language === "zh-CN"
        ? "音频服务未运行"
        : "Audio service not running";
    els.sinkSelect.innerHTML = `<option value="">${noAudio}</option>`;
    els.sourceSelect.innerHTML = `<option value="">${noAudio}</option>`;
    return;
  }
  els.sinkSelect.disabled = false;
  els.sourceSelect.disabled = false;
  const sinks = (audio.sinks || []).map((s) => [
    s.name,
    s.displayName || s.name,
  ]);
  const sources = (audio.sources || []).map((s) => [
    s.name,
    s.displayName || s.name,
  ]);
  setOptions(els.sinkSelect, sinks, audio.defaultSink || "");
  setOptions(els.sourceSelect, sources, audio.defaultSource || "");
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function toFileManagerPath(path) {
  try {
    const parts = path.split("/");
    const sharesIdx = parts.indexOf("shares");
    if (sharesIdx >= 0 && parts.length > sharesIdx + 1) {
      return "/vol1/@appshare/" + parts.slice(sharesIdx + 1).join("/");
    }
  } catch (_e) {}
  return path;
}

function formatSpeed(bytesPerSec) {
  if (bytesPerSec < 1024) return bytesPerSec + " B/s";
  if (bytesPerSec < 1048576) return (bytesPerSec / 1024).toFixed(1) + " KB/s";
  return (bytesPerSec / 1048576).toFixed(1) + " MB/s";
}

function fileIcon(name) {
  const ext = (name || "").split(".").pop().toLowerCase();
  const map = {
    pdf: "📄",
    doc: "📝",
    docx: "📝",
    xls: "📊",
    xlsx: "📊",
    ppt: "📑",
    pptx: "📑",
    jpg: "🖼️",
    jpeg: "🖼️",
    png: "🖼️",
    gif: "🖼️",
    bmp: "🖼️",
    svg: "🖼️",
    mp3: "🎵",
    wav: "🎵",
    flac: "🎵",
    aac: "🎵",
    ogg: "🎵",
    mp4: "🎬",
    avi: "🎬",
    mkv: "🎬",
    mov: "🎬",
    zip: "📦",
    rar: "📦",
    "7z": "📦",
    tar: "📦",
    gz: "📦",
    txt: "📃",
    json: "📃",
    csv: "📃",
    xml: "📃",
  };
  return map[ext] || "📎";
}

function renderReceivedFiles() {
  const files = state.receivedFiles || [];
  if (!files.length) {
    els.receivedFilesList.innerHTML = `<div class="empty">${t("noReceivedFiles")}</div>`;
    return;
  }
  const savePath =
    files[0] && files[0].path ? files[0].path.replace(/\/[^/]+$/, "") : "";
  const displayPath = savePath ? toFileManagerPath(savePath) : "";
  let html = displayPath
    ? `<div class="save-path-hint">${t("savePath")}：<code>${escapeHtml(displayPath)}</code></div>`
    : "";
  html += files
    .map((f) => {
      const d = new Date(f.time * 1000);
      const ts = d.toLocaleString();
      return `<div class="received-row">
      <span class="received-icon">${fileIcon(f.name)}</span>
      <div class="received-info">
        <div class="received-name">${escapeHtml(f.name)}</div>
        <div class="received-meta">${formatSize(f.size)} · ${ts}</div>
      </div>
      <button class="danger-btn" type="button" data-action="delete-received" data-name="${escapeHtml(f.name)}">${t("delete")}</button>
    </div>`;
    })
    .join("");
  els.receivedFilesList.innerHTML = html;
}

function renderTransferHistory() {
  const allHistory = state.transferHistory || [];
  const history = allHistory.filter((h) => h.direction === "send");
  if (!history.length) {
    if (els.transferHistoryList) {
      els.transferHistoryList.innerHTML = `<div class="empty">${t("noTransferHistory")}</div>`;
    }
    return;
  }
  if (!els.transferHistoryList) return;
  els.transferHistoryList.innerHTML = history
    .map((h) => {
      const d = new Date(h.time * 1000);
      const ts = d.toLocaleString();
      const statusCls =
        h.status === "success" ? "transfer-ok" : "transfer-fail";
      const statusLabel =
        h.status === "success" ? t("successStatus") : t("failedStatus");
      return `<div class="transfer-row ${statusCls}">
      <span class="transfer-dir">↑</span>
      <div class="transfer-info">
        <div class="transfer-name">${escapeHtml(h.filename)}</div>
        <div class="transfer-meta">${escapeHtml(h.address)} · ${formatSize(h.size)} · ${ts}</div>
      </div>
      <span class="transfer-status ${statusCls}">${statusLabel}</span>
    </div>`;
    })
    .join("");
}

let _progressTimer = null;
let _receiveWatchTimer = null;
let _progressSnapshots = [];
let _progressSeenActive = false;

function startReceiveWatch() {
  stopReceiveWatch();
  _receiveWatchTimer = setInterval(async () => {
    try {
      const res = await api("transfer_progress");
      if (res.active && res.direction === "receive") {
        startProgressPolling();
        stopReceiveWatch();
      }
    } catch {
      stopReceiveWatch();
    }
  }, 2000);
}

function stopReceiveWatch() {
  if (_receiveWatchTimer) {
    clearInterval(_receiveWatchTimer);
    _receiveWatchTimer = null;
  }
}

function calcSpeed(transferred, size) {
  if (_progressSnapshots.length < 2) return 0;
  const latest = _progressSnapshots[_progressSnapshots.length - 1];
  const earliest = _progressSnapshots[0];
  const dt = (latest.ts - earliest.ts) / 1000;
  if (dt <= 0) return 0;
  return (latest.transferred - earliest.transferred) / dt;
}

function calcETA(speed, transferred, size) {
  if (speed <= 0 || size <= 0 || transferred >= size) return null;
  const remaining = size - transferred;
  const seconds = remaining / speed;
  if (seconds < 60) return `${Math.ceil(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.ceil(seconds % 60);
  return `${mins}m ${secs}s`;
}

function startProgressPolling() {
  stopProgressPolling();
  _progressSnapshots = [];
  _progressSeenActive = false;
  _progressTimer = setInterval(async () => {
    try {
      const res = await api("transfer_progress");
      if (res.active) {
        _progressSeenActive = true;
      }
      if (els.transferProgress) {
        if (res.active || (_progressSeenActive && res.status === "complete")) {
          const pct =
            res.size > 0 ? Math.round((res.transferred / res.size) * 100) : 0;
          const dir = res.direction === "receive" ? "↓" : "↑";
          const dirLabel =
            res.direction === "receive" ? t("receiveDir") : t("sendDir");
          const statusLabel =
            res.status === "queued"
              ? t("queued")
              : res.status === "active"
                ? t("active")
                : res.status === "complete"
                  ? t("complete") || "✓"
                  : res.status === "error"
                    ? t("error") || "✗"
                    : res.status === "retrying"
                      ? t("retrying")
                      : res.status === "sending"
                        ? t("active")
                        : "";

          _progressSnapshots.push({
            ts: Date.now(),
            transferred: res.transferred,
          });
          if (_progressSnapshots.length > 20) _progressSnapshots.shift();
          const speed = calcSpeed(res.transferred, res.size);
          const eta = calcETA(speed, res.transferred, res.size);
          const speedStr = speed > 0 ? `${formatSize(speed)}/s` : "";
          const etaStr = eta ? ` · ${t("eta")} ${eta}` : "";

          const isComplete = pct >= 100 || res.status === "complete";
          const barCls = isComplete
            ? "progress-bar-fill complete"
            : res.status === "error"
              ? "progress-bar-fill error"
              : "progress-bar-fill active";

          els.transferProgress.innerHTML = `
            <div class="progress-header">
              <span class="progress-dir">${dir}</span>
              <span class="progress-filename">${escapeHtml(res.filename)}</span>
              <span class="progress-pct">${pct}%</span>
            </div>
            <div class="progress-bar-wrap">
              <div class="${barCls}" style="width:${isComplete ? 100 : pct}%"></div>
            </div>
            <div class="progress-detail">
              <span>${dirLabel} · ${formatSize(res.transferred)} / ${formatSize(res.size)}</span>
              ${speedStr ? `<span class="progress-speed">${speedStr}</span>` : ""}
              ${etaStr ? `<span>${etaStr}</span>` : ""}
              ${statusLabel ? `<span class="progress-status-label">${statusLabel}</span>` : ""}
            </div>`;
          els.transferProgress.classList.remove("hidden");
        } else if (_progressSeenActive) {
          els.transferProgress.classList.add("hidden");
        }
      }
      if (!res.active && _progressSeenActive) {
        stopProgressPolling();
        loadTransferHistory();
        loadReceivedFiles();
      }
    } catch {
      stopProgressPolling();
    }
  }, 500);
}

function stopProgressPolling() {
  if (_progressTimer) {
    clearInterval(_progressTimer);
    _progressTimer = null;
  }
  _progressSnapshots = [];
  _progressSeenActive = false;
}

function render() {
  renderAdapter();
  renderDevices();
  renderAudio();
  renderReceivedFiles();
  renderTransferHistory();
  renderRoleSwitch();
  if (state.role === "client") {
    els.scan.textContent = state.scanning ? t("stopScan") : t("scan");
    if (state.scanning) {
      els.scanStatus.innerHTML = `<span class="scanning-indicator"><span class="scanning-dot"></span><span class="scanning-dot"></span><span class="scanning-dot"></span> ${t("scanning")}</span>`;
    } else {
      els.scanStatus.innerHTML = "";
    }
  } else {
    renderServerMode();
  }
}

function renderRoleSwitch() {
  els.roleClientBtn.classList.toggle("active", state.role === "client");
  els.roleServerBtn.classList.toggle("active", state.role === "server");
  els.clientMode.classList.toggle("hidden", state.role !== "client");
  els.serverMode.classList.toggle("hidden", state.role !== "server");
}

function renderServerMode() {
  const adapter = state.adapter;
  if (!adapter) {
    els.serverPowerToggle.classList.remove("active");
    els.serverDiscoverableToggle.classList.remove("active");
    els.serverPairableToggle.classList.remove("active");
    els.serverAddr.textContent = "-";
    return;
  }
  els.serverPowerToggle.classList.toggle("active", adapter.powered);
  els.serverPowerToggle.setAttribute("aria-checked", String(adapter.powered));
  els.serverDiscoverableToggle.classList.toggle("active", adapter.discoverable);
  els.serverDiscoverableToggle.setAttribute(
    "aria-checked",
    String(adapter.discoverable),
  );
  els.serverPairableToggle.classList.toggle("active", adapter.pairable);
  els.serverPairableToggle.setAttribute(
    "aria-checked",
    String(adapter.pairable),
  );
  els.serverAddr.textContent = adapter.address || "-";
  if (!els.serverAliasInput.value && adapter.alias) {
    els.serverAliasInput.value = adapter.alias;
  }
  els.serverAdvertiseBtn.textContent = state.serverAdvertise
    ? t("stopAdvertise")
    : t("startAdvertise");
  els.serverAdvertiseBtn.classList.toggle("danger-btn", state.serverAdvertise);
  els.serverAdvertiseBtn.classList.toggle(
    "primary-btn",
    !state.serverAdvertise,
  );

  if (els.obexAgentWarning) {
    els.obexAgentWarning.classList.toggle("hidden", state.obexAgentReady);
  }

  if (!state.serverProfiles.length) {
    els.serverProfilesList.innerHTML = `<div class="empty">${t("noProfiles")}</div>`;
  } else {
    els.serverProfilesList.innerHTML = state.serverProfiles
      .map(
        (p) =>
          `<div class="profile-row"><span class="profile-name">${escapeHtml(p.name)}</span><span class="profile-uuid">${escapeHtml(p.uuid)}</span></div>`,
      )
      .join("");
  }

  els.incomingCount.textContent = String(state.incomingDevices.length);
  if (!state.incomingDevices.length) {
    els.incomingDevices.innerHTML = `<div class="empty">${t("noIncomingDevices")}</div>`;
  } else {
    els.incomingDevices.innerHTML = state.incomingDevices
      .map((dev) => {
        const icon = deviceIcon(dev.deviceType);
        const name = escapeHtml(dev.alias || dev.name || "Unknown");
        const addr = escapeHtml(dev.address);
        return `<div class="device-row">
        <div class="device-icon">${icon}</div>
        <div class="device-info">
          <div class="device-name"><span class="ok">●</span> ${name}</div>
          <div class="device-addr">${addr}</div>
        </div>
        ${signalBars(dev.rssi)}
        <div class="device-type-badge">${escapeHtml(typeName(dev.deviceType))}</div>
        <div class="device-actions">
          <button class="ghost-btn" type="button" data-action="disconnect" data-addr="${addr}">${t("disconnect")}</button>
        </div>
      </div>`;
      })
      .join("");
  }
  renderTethering();
}

function renderTethering() {
  const th = state.tethering;
  els.tetheringToggle.classList.toggle("active", th.active);
  els.tetheringToggle.setAttribute("aria-checked", String(th.active));
  els.tetherBridgeIP.disabled = th.active;
  els.tetherBridge.textContent = th.active ? th.bridge : "-";
  els.tetherClients.textContent = String(th.clients);
  if (th.active && th.ip) {
    els.tetherBridgeIP.value = th.ip;
  }
  const clientList = th.clientList || [];
  if (!clientList.length) {
    els.tetheringClientsList.innerHTML = `<div class="empty">${th.active ? t("noTetheringClients") : "-"}</div>`;
  } else {
    els.tetheringClientsList.innerHTML =
      `
      <div class="client-row client-header">
        <span>${t("clientMAC")}</span>
        <span>${t("clientIP")}</span>
        <span>${t("uploadSpeed")} / ${t("downloadSpeed")}</span>
      </div>
    ` +
      clientList
        .map(
          (c) => `
      <div class="client-row">
        <span>${escapeHtml(c.mac || "-")}</span>
        <span>${escapeHtml(c.ip || "-")}</span>
        <span class="speed-cell"><span class="speed-up">↑${formatSpeed(c.txSpeed || 0)}</span><span class="speed-down">↓${formatSpeed(c.rxSpeed || 0)}</span></span>
      </div>
    `,
        )
        .join("");
  }
}

async function loadAll() {
  setBusy(true);
  try {
    const roleRes = await api("role_get");
    state.role = roleRes.role || "client";
    state.serverAdvertise = roleRes.serverActive || false;

    const statusRes = await api("status").catch(() => null);
    if (statusRes) {
      state.obexAgentReady = statusRes.obexAgentReady !== false;
    }

    const requests = [
      api("adapter_info"),
      api("devices"),
      api("audio_status"),
      api("received_files"),
      api("transfer_history"),
    ];
    if (state.role === "server") {
      requests.push(api("server_profiles"));
      requests.push(api("incoming_devices"));
      requests.push(api("tethering_status"));
    }
    const results = await Promise.all(requests);

    const [adapterRes, devicesRes, audioRes, receivedRes, historyRes] = results;
    state.adapter = adapterRes.adapter || null;
    state.paired = devicesRes.paired || [];
    state.available = devicesRes.available || [];
    state.audio = {
      audioAvailable: audioRes.audioAvailable !== false,
      sinks: audioRes.sinks || [],
      sources: audioRes.sources || [],
      bluetoothAudio: audioRes.bluetoothAudio || [],
      defaultSink: audioRes.defaultSink || "",
      defaultSource: audioRes.defaultSource || "",
    };
    state.receivedFiles = receivedRes.files || [];
    state.transferHistory = historyRes.history || [];

    if (state.role === "server" && results.length >= 8) {
      const profilesRes = results[5];
      const incomingRes = results[6];
      const tetherRes = results[7];
      state.serverProfiles = profilesRes.profiles || [];
      state.incomingDevices = incomingRes.devices || [];
      state.tethering = {
        active: tetherRes.active || false,
        bridge: tetherRes.bridge || "",
        ip: tetherRes.ip || "",
        clients: tetherRes.clients || 0,
        clientList: tetherRes.clientList || [],
      };
    }

    // 打开时不自动发起扫描；仅同步适配器已有状态（discovering 由用户手动触发）。
    if (state.adapter && state.adapter.discovering && !state.scanning) {
      state.scanning = true;
      startScanTimer();
    } else if (state.adapter && !state.adapter.discovering) {
      state.scanning = false;
      clearScanTimer();
      api("scan_stop").catch(() => {});
    }
    state.loaded = true;
    startReceiveWatch();
    render();
  } finally {
    setBusy(false);
  }
}

async function refreshLiveData({ silent = true } = {}) {
  if (!state.loaded || state.busy || state.polling) return;
  state.polling = true;
  try {
    const requests = [api("adapter_info"), api("devices"), api("audio_status")];
    if (state.role === "server") {
      requests.push(api("incoming_devices"));
      requests.push(api("tethering_status"));
    }
    const results = await Promise.all(requests);
    state.adapter = results[0].adapter || null;
    state.paired = results[1].paired || [];
    state.available = results[1].available || [];
    const audioRes = results[2];
    state.audio = {
      audioAvailable: audioRes.audioAvailable !== false,
      sinks: audioRes.sinks || [],
      sources: audioRes.sources || [],
      bluetoothAudio: audioRes.bluetoothAudio || [],
      defaultSink: audioRes.defaultSink || "",
      defaultSource: audioRes.defaultSource || "",
    };
    if (state.role === "server" && results.length >= 5) {
      state.incomingDevices = results[3].devices || [];
      const tetherRes = results[4];
      state.tethering = {
        active: tetherRes.active || false,
        bridge: tetherRes.bridge || "",
        ip: tetherRes.ip || "",
        clients: tetherRes.clients || 0,
        clientList: tetherRes.clientList || [],
      };
    }
    if (state.adapter && !state.adapter.discovering && state.scanning) {
      state.scanning = false;
      clearScanTimer();
    }
    render();
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

async function togglePower() {
  if (state.busy) return;
  if (!state.adapter) return;
  setBusy(true);
  try {
    const action = state.adapter.powered ? "off" : "on";
    await api("adapter_power", { state: action });
    showToast(state.adapter.powered ? t("powerOff") : t("powerOn"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function toggleDiscoverable() {
  if (state.busy) return;
  if (!state.adapter) return;
  setBusy(true);
  try {
    const action = state.adapter.discoverable ? "off" : "on";
    await api("adapter_discoverable", { state: action });
    showToast(
      state.adapter.discoverable ? t("discoverableOff") : t("discoverableOn"),
    );
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function togglePairable() {
  if (state.busy) return;
  if (!state.adapter) return;
  setBusy(true);
  try {
    const action = state.adapter.pairable ? "off" : "on";
    await api("adapter_pairable", { state: action });
    showToast(state.adapter.pairable ? t("pairableOff") : t("pairableOn"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

const SCAN_TIMEOUT = 30000;

function clearScanTimer() {
  if (state.scanTimer) {
    clearTimeout(state.scanTimer);
    state.scanTimer = null;
  }
}

function startScanTimer() {
  clearScanTimer();
  state.scanTimer = setTimeout(async () => {
    if (state.scanning) {
      try {
        await api("scan_stop");
      } catch (_e) {
        /* ignore */
      }
      state.scanning = false;
      render();
    }
  }, SCAN_TIMEOUT);
}

async function toggleScan() {
  if (state.busy) return;
  setBusy(true);
  try {
    if (state.scanning) {
      await api("scan_stop");
      state.scanning = false;
      clearScanTimer();
    } else {
      await api("scan_start");
      state.scanning = true;
      startScanTimer();
    }
    render();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function pairDevice(addr) {
  if (state.busy) return;
  const dev = state.available.find((d) => d.address === addr);
  const name = dev ? dev.alias || dev.name || addr : addr;
  const ok = await confirmDialog(
    t("confirmPair"),
    t("confirmPairMsg", { name, address: addr }),
  );
  if (!ok) return;
  setBusy(true);
  try {
    await api("pair", { address: addr });
    showToast(t("pairedSuccess"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function connectDevice(addr) {
  if (state.busy) return;
  setBusy(true);
  try {
    await api("connect", { address: addr });
    showToast(t("connectedSuccess"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
    await loadAll();
  } finally {
    setBusy(false);
  }
}

async function disconnectDevice(addr) {
  if (state.busy) return;
  const dev = state.paired.find((d) => d.address === addr);
  const name = dev ? dev.alias || dev.name || addr : addr;
  const ok = await confirmDialog(
    t("confirmDisconnect"),
    t("confirmDisconnectMsg", { name, address: addr }),
  );
  if (!ok) return;
  setBusy(true);
  try {
    await api("disconnect", { address: addr });
    showToast(t("disconnectedSuccess"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function removeDevice(addr) {
  if (state.busy) return;
  const dev = state.paired.find((d) => d.address === addr);
  const name = dev ? dev.alias || dev.name || addr : addr;
  const ok = await confirmDialog(
    t("confirmRemove"),
    t("confirmRemoveMsg", { name, address: addr }),
  );
  if (!ok) return;
  setBusy(true);
  try {
    await api("remove", { address: addr });
    showToast(t("removedSuccess"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function trustDevice(addr) {
  if (state.busy) return;
  setBusy(true);
  try {
    await api("trust", { address: addr });
    showToast(t("trustedSuccess"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function untrustDevice(addr) {
  if (state.busy) return;
  setBusy(true);
  try {
    await api("untrust", { address: addr });
    showToast(t("untrustedSuccess"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function pickFileForSend() {
  if (!sdk.pickFile) {
    showToast("File picker not available", true);
    return;
  }
  try {
    const picked = await sdk.pickFile({});
    let path = "";
    if (picked) {
      if (Array.isArray(picked)) {
        path =
          picked[0] && typeof picked[0] === "object"
            ? picked[0].path
            : picked[0];
      } else if (typeof picked === "object") {
        path = picked.path;
      } else if (typeof picked === "string") {
        path = picked;
      }
    }
    if (path) {
      els.sendFilePath.value = path;
    }
  } catch (_error) {
    // 用户取消或环境不支持时忽略
  }
}

async function sendFile() {
  if (state.busy) return;
  const addr = els.sendTargetSelect.value;
  const filepath = els.sendFilePath.value.trim();
  if (!addr) {
    showToast("Select a target device", true);
    return;
  }
  if (!filepath) {
    showToast("Enter file path", true);
    return;
  }
  setBusy(true);
  els.sendFileBtn.textContent = t("sending");
  const fname = filepath.split("/").pop() || filepath;
  if (els.transferProgress) {
    els.transferProgress.innerHTML = `
      <div class="progress-header">
        <span class="progress-dir">↑</span>
        <span class="progress-filename">${escapeHtml(fname)}</span>
        <span class="progress-pct">0%</span>
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill active" style="width:0%"></div>
      </div>
      <div class="progress-detail">
        <span>${t("sendDir")} · ${t("active")}</span>
      </div>`;
    els.transferProgress.classList.remove("hidden");
  }
  startProgressPolling();
  let sendOk = false;
  try {
    await api("send_file", { address: addr, filepath });
    sendOk = true;
    showToast(t("fileSent"));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    stopProgressPolling();
    if (els.transferProgress) {
      const barFill = els.transferProgress.querySelector(".progress-bar-fill");
      if (barFill) {
        barFill.classList.remove("active");
        barFill.classList.add(sendOk ? "complete" : "error");
      }
      const pctEl = els.transferProgress.querySelector(".progress-pct");
      if (pctEl && sendOk) pctEl.textContent = "100%";
      if (sendOk) {
        setTimeout(() => {
          if (els.transferProgress)
            els.transferProgress.classList.add("hidden");
        }, 2000);
      } else {
        setTimeout(() => {
          if (els.transferProgress)
            els.transferProgress.classList.add("hidden");
        }, 3000);
      }
    }
    setBusy(false);
    els.sendFileBtn.textContent = t("sendFile");
    const histRes = await api("transfer_history").catch(() => null);
    if (histRes && histRes.history) {
      state.transferHistory = histRes.history;
      renderTransferHistory();
    }
  }
}

async function clearReceived() {
  if (state.busy) return;
  try {
    await api("clear_received");
    state.receivedFiles = [];
    renderReceivedFiles();
    showToast(t("cleared"));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function clearTransferHistory() {
  if (state.busy) return;
  try {
    await api("clear_transfer_history");
    state.transferHistory = [];
    renderTransferHistory();
    showToast(t("cleared"));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function deleteReceived(name) {
  if (state.busy) return;
  try {
    await api("delete_received", { name });
    state.receivedFiles = state.receivedFiles.filter((f) => f.name !== name);
    renderReceivedFiles();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadAudio() {
  try {
    const audioRes = await api("audio_status");
    state.audio = {
      audioAvailable: audioRes.audioAvailable !== false,
      sinks: audioRes.sinks || [],
      sources: audioRes.sources || [],
      bluetoothAudio: audioRes.bluetoothAudio || [],
      defaultSink: audioRes.defaultSink || "",
      defaultSource: audioRes.defaultSource || "",
    };
    renderAudio();
  } catch (_e) {}
}

async function setSink() {
  if (state.busy) return;
  const sink = els.sinkSelect.value;
  if (!sink) return;
  try {
    await api("audio_sink_set", { sink });
    showToast(t("sinkSet"));
    await loadAudio();
  } catch (error) {
    showToast(error.message, true);
    await loadAudio();
  }
}

async function setSource() {
  if (state.busy) return;
  const source = els.sourceSelect.value;
  if (!source) return;
  try {
    await api("audio_source_set", { source });
    showToast(t("sourceSet"));
    await loadAudio();
  } catch (error) {
    showToast(error.message, true);
    await loadAudio();
  }
}

els.refresh.addEventListener("click", () =>
  loadAll().catch((error) => showToast(error.message, true)),
);
els.scan.addEventListener("click", () =>
  toggleScan().catch((error) => showToast(error.message, true)),
);
els.powerToggle.addEventListener("click", () => togglePower());
els.discoverableToggle.addEventListener("click", () => toggleDiscoverable());
els.pairableToggle.addEventListener("click", () => togglePairable());
els.sendFileBtn.addEventListener("click", () => sendFile());
els.pickFileBtn.addEventListener("click", () => pickFileForSend());
els.sinkSelect.addEventListener("change", () => setSink());
els.sourceSelect.addEventListener("change", () => setSource());
els.sendTargetSelect.addEventListener("change", () => {
  state.sendTarget = els.sendTargetSelect.value;
});
els.clearReceivedBtn.addEventListener("click", () => clearReceived());
els.clearHistoryBtn.addEventListener("click", () => clearTransferHistory());

els.roleClientBtn.addEventListener("click", () => switchRole("client"));
els.roleServerBtn.addEventListener("click", () => switchRole("server"));
els.serverPowerToggle.addEventListener("click", () => togglePower());
els.serverDiscoverableToggle.addEventListener("click", () =>
  toggleDiscoverable(),
);
els.serverPairableToggle.addEventListener("click", () => togglePairable());
els.serverAdvertiseBtn.addEventListener("click", () => toggleAdvertise());
els.fixObexAgentBtn.addEventListener("click", () => fixObexAgent());
els.serverAliasInput.addEventListener("change", () => setServerAlias());
els.tetheringToggle.addEventListener("click", () => toggleTethering());
els.aboutBtn.addEventListener("click", () =>
  els.aboutModal.classList.remove("hidden"),
);

async function switchRole(role) {
  if (state.busy) return;
  if (state.role === role) return;
  setBusy(true);
  try {
    await api("role_set", { role });
    state.role = role;
    if (role === "server") {
      const [profilesRes, incomingRes] = await Promise.all([
        api("server_profiles"),
        api("incoming_devices"),
      ]);
      state.serverProfiles = profilesRes.profiles || [];
      state.incomingDevices = incomingRes.devices || [];
    }
    render();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function toggleAdvertise() {
  if (state.busy) return;
  setBusy(true);
  try {
    const action = state.serverAdvertise ? "off" : "on";
    await api("server_advertise", { state: action });
    state.serverAdvertise = !state.serverAdvertise;
    showToast(state.serverAdvertise ? t("advertiseOn") : t("advertiseOff"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function setServerAlias() {
  if (state.busy) return;
  const alias = els.serverAliasInput.value.trim();
  if (!alias) return;
  try {
    await api("server_alias", { alias });
    showToast(t("aliasSet"));
    await loadAll();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function fixObexAgent() {
  if (state.busy) return;
  setBusy(true);
  try {
    const res = await api("server_accept");
    state.obexAgentReady = res.obexAgentReady !== false;
    if (state.obexAgentReady) {
      showToast(t("obexAgentFixed"));
    } else {
      showToast(t("obexAgentFixFailed"), true);
    }
    render();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function loadTransferHistory() {
  try {
    const res = await api("transfer_history");
    state.transferHistory = res.history || [];
    renderTransferHistory();
  } catch (_e) {}
}

async function loadReceivedFiles() {
  try {
    const res = await api("received_files");
    state.receivedFiles = res.files || [];
    renderReceivedFiles();
  } catch (_e) {}
}

async function toggleTethering() {
  if (state.busy) return;
  setBusy(true);
  try {
    if (state.tethering.active) {
      await api("tethering_stop");
      showToast(t("tetheringOff"));
    } else {
      const bridgeIP = els.tetherBridgeIP.value.trim() || "192.168.7.1";
      await api("tethering_start", { bridge_ip: bridgeIP });
      showToast(t("tetheringOn"));
    }
    const res = await api("tethering_status");
    state.tethering = {
      active: res.active || false,
      bridge: res.bridge || "",
      ip: res.ip || "",
      clients: res.clients || 0,
      clientList: res.clientList || [],
    };
    renderTethering();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

document.addEventListener("click", async (event) => {
  if (event.target.closest("[data-close]")) {
    event.target.closest(".modal").classList.add("hidden");
    return;
  }
  if (
    event.target.classList.contains("modal") &&
    !event.target.closest(".modal-content")
  ) {
    event.target.classList.add("hidden");
    return;
  }
  const btn = event.target.closest("[data-action]");
  if (!btn) return;
  const action = btn.dataset.action;
  const addr = btn.dataset.addr;
  const name = btn.dataset.name;
  if (action === "delete-received" && name) {
    await deleteReceived(name);
    return;
  }
  if (!action || !addr) return;
  // 设备操作：处理中即时反馈 + 禁止重复触发（防连点）
  const busyActions = [
    "pair",
    "connect",
    "disconnect",
    "remove",
    "trust",
    "untrust",
  ];
  if (busyActions.includes(action)) {
    if (state.busy) {
      showToast(t("operationBusy"));
      return;
    }
    const origLabel = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = t("processing");
    try {
      switch (action) {
        case "pair":
          await pairDevice(addr);
          break;
        case "connect":
          await connectDevice(addr);
          break;
        case "disconnect":
          await disconnectDevice(addr);
          break;
        case "remove":
          await removeDevice(addr);
          break;
        case "trust":
          await trustDevice(addr);
          break;
        case "untrust":
          await untrustDevice(addr);
          break;
      }
    } finally {
      btn.disabled = false;
      btn.innerHTML = origLabel;
    }
    return;
  }
  switch (action) {
    case "delete-received":
      break;
    default:
      break;
  }
});

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
setInterval(() => refreshLiveData(), 5000);
setBusy(true);
loadAll().catch((error) => {
  state.loaded = false;
  setBusy(false);
  showToast(error.message, true);
});
