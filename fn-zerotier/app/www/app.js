const nodeIdEl = document.getElementById("nodeId");
const versionEl = document.getElementById("version");
const onlineStateEl = document.getElementById("onlineState");
const peerSummaryEl = document.getElementById("peerSummary");
const serviceEnabledEl = document.getElementById("serviceEnabled");
const networkCountEl = document.getElementById("networkCount");
const networkListEl = document.getElementById("networkList");
const networksEmptyEl = document.getElementById("networksEmpty");
const joinedMoonCountEl = document.getElementById("joinedMoonCount");
const joinedMoonListEl = document.getElementById("joinedMoonList");
const joinedMoonsEmptyEl = document.getElementById("joinedMoonsEmpty");
const createdMoonCountEl = document.getElementById("createdMoonCount");
const createdMoonListEl = document.getElementById("createdMoonList");
const createdMoonsEmptyEl = document.getElementById("createdMoonsEmpty");
const moonForm = document.getElementById("moonForm");
const moonJoinWorldIdInput = document.getElementById("moonWorldId");
const moonSeedInput = document.getElementById("moonSeed");
const moonCreateSeedEl = document.getElementById("moonCreateSeed");
const moonRootIdentityEl = document.getElementById("moonRootIdentity");
const moonCreateSupportEl = document.getElementById("moonCreateSupport");
const moonCreateForm = document.getElementById("moonCreateForm");
const moonCreateWorldIdInput = document.getElementById(
  "moonCreateWorldIdInput",
);
const moonStableEndpointsInput = document.getElementById("moonStableEndpoints");
const moonCreateCancelBtn = document.getElementById("moonCreateCancelBtn");
const moonCreateBtn = document.getElementById("moonCreateBtn");
const peerListEl = document.getElementById("peerList");
const refreshBtn = document.getElementById("refreshBtn");
const joinForm = document.getElementById("joinForm");
const networkIdInput = document.getElementById("networkId");
const toastEl = document.getElementById("toast");

const state = {
  language: "zh-CN",
  theme: "light",
};

const I18N = {
  "zh-CN": {
    appTitle: "ZeroTier 组网控制台",
    refresh: "刷新",
    serviceStatus: "服务状态",
    version: "版本",
    systemService: "系统服务",
    onlineState: "在线状态",
    networkManagement: "网络管理",
    networkCount: "{count} 个网络",
    networkCountZero: "0 个网络",
    networkPlaceholder: "例如：8056c2e21c000001",
    join: "加入",
    emptyNetworks: "当前还没有加入任何网络。",
    moonManagement: "Moon 管理",
    createdCount: "创建 {count}",
    joinedCount: "加入 {count}",
    createdCountZero: "创建 0",
    joinedCountZero: "加入 0",
    status: "状态",
    actions: "操作",
    readyToCreate: "待创建",
    editing: "编辑中",
    unavailable: "不可用",
    create: "创建",
    update: "修改",
    cancel: "取消",
    joinMoon: "加入",
    moonWorldPlaceholder: "例如：ad7592d9dc",
    moonSeedPlaceholder: "例如：abcdef1234",
    emptyCreatedMoons: "当前还没有创建任何 Moon。",
    emptyJoinedMoons: "当前还没有加入任何 Moon。",
    peerInfo: "Peer 信息",
    loadingPeers: "等待加载 Peer 信息。",
    noPeers: "还没有可展示的 Peer 数据。",
    running: "运行中",
    stopped: "未运行",
    enabled: "已启用",
    disabled: "未启用",
    normal: "正常",
    accessDenied: "访问被拒绝",
    requestingConfiguration: "等待配置",
    unknown: "未知",
    unnamedNetwork: "未命名网络",
    noAddress: "尚未分配地址",
    name: "名称",
    type: "类型",
    device: "设备",
    address: "地址",
    settings: "设置",
    leave: "退出",
    removed: "移除",
    copy: "复制",
    download: "下载",
    start: "启动",
    stop: "停止",
    active: "已启动",
    inactive: "已停止",
    waitingPull: "等待拉取",
    effective: "已生效",
    refreshed: "状态已刷新",
    success: "操作成功",
    invalidJson: "返回结果不是合法 JSON",
    requestFailed: "请求失败",
    noCopyContent: "没有可复制的内容",
    copyFailed: "复制失败",
    networkIdInvalid: "Network ID 必须是 16 位十六进制字符串",
    joinedNetwork: "已发起加入网络 {id}",
    leftNetwork: "已离开网络 {id}",
    networkSaved: "网络 {id} 设置已保存",
    worldIdInvalid: "World ID 必须是 10 位十六进制，或补零后的 16 位字符串",
    seedInvalid: "Seed 必须是 10 位十六进制字符串",
    endpointRequired: "请至少填写一个 Stable Endpoint",
    joinedMoon: "已加入 moon {id}",
    createdMoon: "已创建 moon {id}",
    updatedMoon: "已修改 moon {id}",
    missingMoon: "未找到已创建 moon {id}",
    orbitCopied: "Orbit 命令已复制",
    noMoonFile: "当前没有可下载的 .moon 文件",
    startedMoon: "已启动 moon {id}",
    stoppedMoon: "已停止 moon {id}",
    removedMoon: "已移除 moon {id}",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
  },
  "en-US": {
    appTitle: "ZeroTier Console",
    refresh: "Refresh",
    serviceStatus: "Service Status",
    version: "Version",
    systemService: "System Service",
    onlineState: "Online State",
    networkManagement: "Networks",
    networkCount: "{count} networks",
    networkCountZero: "0 networks",
    networkPlaceholder: "Example: 8056c2e21c000001",
    join: "Join",
    emptyNetworks: "No networks joined yet.",
    moonManagement: "Moon Management",
    createdCount: "Created {count}",
    joinedCount: "Joined {count}",
    createdCountZero: "Created 0",
    joinedCountZero: "Joined 0",
    status: "Status",
    actions: "Actions",
    readyToCreate: "Ready",
    editing: "Editing",
    unavailable: "Unavailable",
    create: "Create",
    update: "Update",
    cancel: "Cancel",
    joinMoon: "Join",
    moonWorldPlaceholder: "Example: ad7592d9dc",
    moonSeedPlaceholder: "Example: abcdef1234",
    emptyCreatedMoons: "No created Moons yet.",
    emptyJoinedMoons: "No joined Moons yet.",
    peerInfo: "Peer Info",
    loadingPeers: "Loading peer info.",
    noPeers: "No peer data to display.",
    running: "Running",
    stopped: "Stopped",
    enabled: "Enabled",
    disabled: "Disabled",
    normal: "OK",
    accessDenied: "Access denied",
    requestingConfiguration: "Requesting config",
    unknown: "Unknown",
    unnamedNetwork: "Unnamed network",
    noAddress: "No address assigned",
    name: "Name",
    type: "Type",
    device: "Device",
    address: "Address",
    settings: "Settings",
    leave: "Leave",
    removed: "Remove",
    copy: "Copy",
    download: "Download",
    start: "Start",
    stop: "Stop",
    active: "Started",
    inactive: "Stopped",
    waitingPull: "Waiting",
    effective: "Effective",
    refreshed: "Refreshed",
    success: "Done",
    invalidJson: "Response is not valid JSON",
    requestFailed: "Request failed",
    noCopyContent: "Nothing to copy",
    copyFailed: "Copy failed",
    networkIdInvalid: "Network ID must be a 16-character hexadecimal string",
    joinedNetwork: "Joining network {id}",
    leftNetwork: "Left network {id}",
    networkSaved: "Network {id} settings saved",
    worldIdInvalid:
      "World ID must be 10 hex characters, or a zero-padded 16-character string",
    seedInvalid: "Seed must be a 10-character hexadecimal string",
    endpointRequired: "Enter at least one Stable Endpoint",
    joinedMoon: "Joined moon {id}",
    createdMoon: "Created moon {id}",
    updatedMoon: "Updated moon {id}",
    missingMoon: "Created moon {id} was not found",
    orbitCopied: "Orbit command copied",
    noMoonFile: "No .moon file is available",
    startedMoon: "Started moon {id}",
    stoppedMoon: "Stopped moon {id}",
    removedMoon: "Removed moon {id}",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
  },
};

const NETWORK_STATUS_META = {
  OK: { className: "pill-ok", key: "normal" },
  ACCESS_DENIED: { className: "pill-warn", key: "accessDenied" },
  REQUESTING_CONFIGURATION: {
    className: "pill-warn",
    key: "requestingConfiguration",
  },
};

function moonTableHeaderHtml() {
  return `
    <div class="moon-created-header">
      <span>World ID</span>
      <span>Seed</span>
      <span>Root Identity</span>
      <span>Stable Endpoints</span>
      <span>${t("status")}</span>
      <span>${t("actions")}</span>
    </div>
  `;
}

let busy = false;
let toastTimer = null;
let latestStatusData = null;
let editingCreatedMoonId = "";

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

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_error) {
    return value || "";
  }
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

function currentLanguage() {
  return normalizeLanguage(
    cookieValue("language") ||
      queryValue("language") ||
      navigator.language ||
      "zh-CN",
  );
}

function normalizeTheme(value) {
  const theme = safeDecode(value).toLowerCase();
  if (theme.includes("dark") || theme === "night") return "dark";
  if (theme.includes("light") || theme === "day") return "light";
  if (theme === "10") return "light";
  if (theme === "20") return "dark";
  if (theme === "system" || theme === "auto" || theme === "os") {
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return "";
}

function currentTheme() {
  const fromSystem = [
    queryValue("theme"),
    cookieValue("fnos-theme-mode"),
    cookieValue("os-theme-mode"),
    storedValue("fnos-theme-mode"),
    storedValue("os-theme-mode"),
    parentStoredValue("fnos-theme-mode"),
    parentStoredValue("os-theme-mode"),
    documentThemeValue(document),
    parentDocumentThemeValue(),
    queryValue("fnos-theme-mode"),
  ]
    .map(normalizeTheme)
    .find(Boolean);
  if (fromSystem) return fromSystem;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
}

function applyPreferences({ rerender = false } = {}) {
  const nextLanguage = currentLanguage();
  const nextTheme = currentTheme();
  const languageChanged = nextLanguage !== state.language;
  state.language = nextLanguage;
  state.theme = nextTheme;
  document.documentElement.lang = nextLanguage;
  document.documentElement.dataset.theme = nextTheme;
  document.body.dataset.theme = nextTheme;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.title = "ZeroTier";
  if (!latestStatusData) {
    networkCountEl.textContent = t("networkCountZero");
    createdMoonCountEl.textContent = t("createdCountZero");
    joinedMoonCountEl.textContent = t("joinedCountZero");
    moonCreateSupportEl.textContent = t("readyToCreate");
  }
  if (!editingCreatedMoonId) {
    moonCreateBtn.textContent = t("create");
  }
  if (rerender && languageChanged && latestStatusData) {
    renderAll(latestStatusData);
  }
}

function showToast(text, tone = "info") {
  if (!toastEl) return;
  toastEl.textContent = String(text || "");
  toastEl.dataset.tone = tone;
  toastEl.classList.add("show");
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toastEl.classList.remove("show");
  }, 3200);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(text || t("invalidJson"));
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || text || t("requestFailed"));
  }
  return data;
}

function setBusy(nextBusy) {
  busy = !!nextBusy;
  refreshBtn.disabled = busy;
  for (const button of document.querySelectorAll("button")) {
    if (button === refreshBtn) continue;
    button.disabled = busy;
  }
}

async function copyText(text, successMessage) {
  if (!text) {
    showToast(t("noCopyContent"), "error");
    return;
  }

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const input = document.createElement("textarea");
      input.value = text;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
    }
    showToast(successMessage, "success");
  } catch (error) {
    showToast(t("copyFailed"), "error");
  }
}

function toBool(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  return (
    normalized === "1" ||
    normalized === "true" ||
    normalized === "yes" ||
    normalized === "on"
  );
}

function renderService(data) {
  const service = data.service || {};
  const info = data.info || {};
  const peerSummary = data.peerSummary || {};

  const serviceActive = toBool(service.active);
  const serviceEnabled = toBool(service.enabled);

  nodeIdEl.textContent = info.address || "-";
  versionEl.textContent = info.version || "-";
  onlineStateEl.textContent = serviceActive ? t("running") : t("stopped");
  peerSummaryEl.textContent = `${peerSummary.online || 0} / ${peerSummary.total || 0}`;
  serviceEnabledEl.textContent = serviceEnabled ? t("enabled") : t("disabled");
}

function networkStatusClass(status) {
  return NETWORK_STATUS_META[status]?.className || "pill-muted";
}

function networkStatusText(status) {
  const meta = NETWORK_STATUS_META[status];
  return meta ? t(meta.key) : status || t("unknown");
}

function checkedAttr(value) {
  return toBool(value) ? "checked" : "";
}

function isValidMoonWorldId(value) {
  return /^(?:[0-9a-fA-F]{10}|0{6}[0-9a-fA-F]{10})$/.test(
    String(value || "").trim(),
  );
}

function extractSeedFromIdentity(identity) {
  const normalized = String(identity || "")
    .trim()
    .toLowerCase();
  if (/^[0-9a-f]{10}$/.test(normalized)) {
    return normalized;
  }
  const match = normalized.match(/^([0-9a-f]{10}):/);
  return match ? match[1] : "";
}

function resetMoonJoinForm() {
  moonJoinWorldIdInput.value = "";
  moonSeedInput.value = "";
}

function resetMoonCreateForm() {
  editingCreatedMoonId = "";
  moonCreateBtn.textContent = t("create");
  moonCreateCancelBtn.hidden = true;
  moonCreateWorldIdInput.value = "";
  moonStableEndpointsInput.value = "";
}

function moonEndpoints(moon) {
  const roots = Array.isArray(moon?.roots) ? moon.roots : [];
  return roots
    .flatMap((root) =>
      Array.isArray(root?.stableEndpoints) ? root.stableEndpoints : [],
    )
    .filter(Boolean);
}

function getCreatedMoonById(worldId) {
  const moons = Array.isArray(latestStatusData?.createdMoons)
    ? latestStatusData.createdMoons
    : [];
  return moons.find((moon) => moon.id === worldId) || null;
}

function getMoonRowData(moon) {
  const roots = Array.isArray(moon?.roots) ? moon.roots : [];
  const identity = roots.length ? roots[0].identity || "" : "";
  const seed = roots.length ? extractSeedFromIdentity(identity) : "";
  const endpoints = moonEndpoints(moon);
  return {
    identity: identity || "-",
    seed: seed || "-",
    endpointsText: endpoints.length ? endpoints.join(", ") : "-",
  };
}

function formatPeerPathEntry(entry) {
  if (!entry) return "-";
  if (typeof entry === "string") return entry;
  if (typeof entry !== "object") return String(entry);

  const parts = [];
  if (entry.address) parts.push(entry.address);
  if (entry.ip) parts.push(entry.ip);
  if (entry.port) parts.push(String(entry.port));
  if (entry.preferred === true) parts.push("preferred");
  if (entry.trustedPathId) parts.push(`tpid:${entry.trustedPathId}`);
  if (entry.lastSend) parts.push(`tx:${entry.lastSend}`);
  if (entry.lastReceive) parts.push(`rx:${entry.lastReceive}`);

  return parts.length ? parts.join(" ") : JSON.stringify(entry);
}

function formatPeerPath(peer) {
  if (Array.isArray(peer.paths) && peer.paths.length) {
    return peer.paths.map(formatPeerPathEntry).join(" | ");
  }
  if (peer.path) {
    return formatPeerPathEntry(peer.path);
  }
  return "-";
}

function renderNetworks(data) {
  const networks = Array.isArray(data.networks) ? data.networks : [];
  networkCountEl.textContent = t("networkCount", { count: networks.length });
  networksEmptyEl.style.display = networks.length ? "none" : "block";

  if (!networks.length) {
    networkListEl.innerHTML = "";
    return;
  }

  networkListEl.innerHTML = networks
    .map((network) => {
      const name = network.name || t("unnamedNetwork");
      const nwid = network.nwid || "-";
      const addresses =
        Array.isArray(network.assignedAddresses) &&
        network.assignedAddresses.length
          ? network.assignedAddresses.join(", ")
          : t("noAddress");
      return `
        <article class="network-table-row">
          <div class="network-table-col network-table-col-name">
            <strong>${name}</strong>
          </div>
          <div class="network-table-col network-table-col-id">
            <strong>${nwid}</strong>
          </div>
          <div class="network-table-col network-table-col-type">
            <strong>${network.type || "-"}</strong>
          </div>
          <div class="network-table-col network-table-col-device">
            <strong>${network.portDeviceName || network.dev || "-"}</strong>
          </div>
          <div class="network-table-col network-table-col-addresses">
            <strong>${addresses}</strong>
          </div>
          <div class="network-table-col network-table-col-status">
            <span class="pill ${networkStatusClass(network.status)}">${networkStatusText(network.status)}</span>
          </div>
          <div class="network-table-col network-table-col-settings">
            <div class="network-flags" data-network="${nwid}">
              <label><input type="checkbox" data-setting="allowManaged" ${checkedAttr(network.allowManaged)}> Managed</label>
              <label><input type="checkbox" data-setting="allowDNS" ${checkedAttr(network.allowDNS)}> DNS</label>
              <label><input type="checkbox" data-setting="allowDefault" ${checkedAttr(network.allowDefault)}> Default Route</label>
              <label><input type="checkbox" data-setting="allowGlobal" ${checkedAttr(network.allowGlobal)}> Global IP</label>
            </div>
          </div>
          <div class="network-table-col network-table-col-actions">
            <div class="network-actions">
              <button class="btn btn-danger" type="button" data-action="leave-network" data-network="${nwid}">${t("leave")}</button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  networkListEl.innerHTML = `
    <div class="network-table-header">
      <span>${t("name")}</span>
      <span>Network ID</span>
      <span>${t("type")}</span>
      <span>${t("device")}</span>
      <span>${t("address")}</span>
      <span>${t("status")}</span>
      <span>${t("settings")}</span>
      <span>${t("actions")}</span>
    </div>
    ${networkListEl.innerHTML}
  `;
}

function renderMoonTable(container, rowsHtml) {
  container.innerHTML = `${moonTableHeaderHtml()}${rowsHtml}`;
}

function renderMoonSection(
  moons,
  countEl,
  emptyEl,
  listEl,
  countLabel,
  rowRenderer,
) {
  countEl.textContent = t(countLabel, { count: moons.length });
  emptyEl.style.display = moons.length ? "none" : "block";

  if (!moons.length) {
    listEl.innerHTML = "";
    return;
  }

  renderMoonTable(listEl, moons.map(rowRenderer).join(""));
}

function renderJoinedMoonRow(moon) {
  const active = moon.active !== undefined ? toBool(moon.active) : true;
  const waiting = toBool(moon.waiting);
  const { identity, seed, endpointsText } = getMoonRowData(moon);
  const stateClass = !active ? "pill-muted" : waiting ? "pill-warn" : "pill-ok";
  const stateText = !active
    ? t("inactive")
    : waiting
      ? t("waitingPull")
      : t("effective");
  return `
    <article class="moon-created-row">
      <div class="moon-created-col moon-created-col-id">
          <strong>${moon.id || "-"}</strong>
      </div>
      <div class="moon-created-col moon-created-col-seed">
          <strong>${seed}</strong>
      </div>
      <div class="moon-created-col moon-created-col-identity">
        <strong>${identity}</strong>
      </div>
      <div class="moon-created-col moon-created-col-endpoints">
        <strong>${endpointsText}</strong>
      </div>
      <div class="moon-created-col moon-created-col-state">
        <span class="pill ${stateClass}">${stateText}</span>
      </div>
      <div class="moon-created-col moon-created-col-actions">
        <button class="btn btn-danger" type="button" data-action="leave-joined-moon" data-world-id="${moon.id || ""}">${t("removed")}</button>
      </div>
    </article>
  `;
}

function renderCreatedMoonRow(moon) {
  const active = toBool(moon.active);
  const { identity, seed, endpointsText } = getMoonRowData(moon);
  const orbitCommand =
    moon.orbitCommand ||
    (moon.id && seed !== "-" ? `zerotier-cli orbit ${moon.id} ${seed}` : "");
  const moonFileBase64 = moon.moonFileBase64 || "";
  const moonFileName = moon.moonFileName || `${String(moon.id || "moon")}.moon`;
  return `
    <article class="moon-created-row">
      <div class="moon-created-col moon-created-col-id">
          <strong>${moon.id || "-"}</strong>
      </div>
      <div class="moon-created-col moon-created-col-seed">
          <strong>${seed}</strong>
      </div>
      <div class="moon-created-col moon-created-col-identity">
        <strong>${identity}</strong>
      </div>
      <div class="moon-created-col moon-created-col-endpoints">
        <strong>${endpointsText}</strong>
      </div>
      <div class="moon-created-col moon-created-col-state">
          <span class="pill ${active ? "pill-ok" : "pill-muted"}">${active ? t("active") : t("inactive")}</span>
      </div>
      <div class="moon-created-col moon-created-col-actions">
        <button class="btn btn-secondary" type="button" data-action="copy-created-moon-orbit" data-orbit-command="${escapeHtml(orbitCommand)}" ${orbitCommand ? "" : "disabled"}>${t("copy")}</button>
        <button class="btn btn-secondary" type="button" data-action="download-created-moon" data-moon-file-base64="${escapeHtml(moonFileBase64)}" data-moon-file-name="${escapeHtml(moonFileName)}" ${moonFileBase64 ? "" : "disabled"}>${t("download")}</button>
        <button class="btn btn-secondary" type="button" data-action="edit-created-moon" data-world-id="${moon.id || ""}">${t("update")}</button>
        <button class="btn ${active ? "btn-secondary" : "btn-primary"}" type="button" data-action="${active ? "stop-created-moon" : "start-created-moon"}" data-world-id="${moon.id || ""}">${active ? t("stop") : t("start")}</button>
        <button class="btn btn-danger" type="button" data-action="remove-created-moon" data-world-id="${moon.id || ""}">${t("removed")}</button>
      </div>
    </article>
  `;
}

function renderJoinedMoons(data) {
  const moons = Array.isArray(data.joinedMoons) ? data.joinedMoons : [];
  renderMoonSection(
    moons,
    joinedMoonCountEl,
    joinedMoonsEmptyEl,
    joinedMoonListEl,
    "joinedCount",
    renderJoinedMoonRow,
  );
}

function renderCreatedMoons(data) {
  const moons = Array.isArray(data.createdMoons) ? data.createdMoons : [];
  renderMoonSection(
    moons,
    createdMoonCountEl,
    createdMoonsEmptyEl,
    createdMoonListEl,
    "createdCount",
    renderCreatedMoonRow,
  );
}

function renderMoonCreator(data) {
  const info = data.moonCreate || {};
  const supported = toBool(info.supported);
  const error = info.error || "";

  moonCreateSeedEl.textContent = info.seed || "-";
  moonRootIdentityEl.textContent = info.rootIdentity || error || "-";
  moonCreateSupportEl.textContent = supported
    ? editingCreatedMoonId
      ? t("editing")
      : t("readyToCreate")
    : t("unavailable");
  moonCreateSupportEl.className = supported
    ? `pill ${editingCreatedMoonId ? "pill-warn" : "pill-muted"}`
    : "pill pill-muted";
  moonCreateBtn.textContent = editingCreatedMoonId ? t("update") : t("create");
  moonCreateBtn.disabled = !supported;
  moonCreateWorldIdInput.disabled = !supported;
  moonStableEndpointsInput.disabled = !supported;

  if (!moonSeedInput.value && info.seed) {
    moonSeedInput.value = info.seed;
  }
  if (!moonJoinWorldIdInput.value && info.worldId) {
    moonJoinWorldIdInput.value = info.worldId;
  }
  if (!editingCreatedMoonId && !moonCreateWorldIdInput.value && info.worldId) {
    moonCreateWorldIdInput.value = info.worldId;
  }
}

function renderPeers(data) {
  const peers = Array.isArray(data.peers) ? data.peers : [];
  if (!peers.length) {
    peerListEl.innerHTML = `<div class="empty-state">${t("noPeers")}</div>`;
    return;
  }

  peerListEl.innerHTML = peers
    .map((peer) => {
      const online = typeof peer.latency === "number" && peer.latency >= 0;
      const latency = online ? `${peer.latency} ms` : "-";
      const path = formatPeerPath(peer);
      return `
        <div class="peer-item">
          <span class="peer-cell">
            <span class="peer-key">ztaddr</span>
            <span class="peer-field peer-addr">${peer.address || "-"}</span>
          </span>
          <span class="peer-cell">
            <span class="peer-key">ver</span>
            <span class="peer-field">${peer.version || "-"}</span>
          </span>
          <span class="peer-cell">
            <span class="peer-key">role</span>
            <span class="peer-field">${peer.role || "-"}</span>
          </span>
          <span class="peer-cell">
            <span class="peer-key">lat</span>
            <span class="peer-field">
              <span class="pill ${online ? "pill-ok" : "pill-muted"}">${latency}</span>
            </span>
          </span>
          <span class="peer-cell">
            <span class="peer-key">link</span>
            <span class="peer-field">${peer.link || "-"}</span>
          </span>
          <span class="peer-cell">
            <span class="peer-key">lastTX</span>
            <span class="peer-field">${peer.lastTX || "-"}</span>
          </span>
          <span class="peer-cell">
            <span class="peer-key">lastRX</span>
            <span class="peer-field">${peer.lastRX || "-"}</span>
          </span>
          <span class="peer-cell peer-cell-path">
            <span class="peer-key">path</span>
            <span class="peer-field peer-path">${path}</span>
          </span>
        </div>
      `;
    })
    .join("");
}

function renderAll(data) {
  latestStatusData = data;
  renderService(data);
  renderMoonCreator(data);
  renderJoinedMoons(data);
  renderCreatedMoons(data);
  renderNetworks(data);
  renderPeers(data);
}

async function refreshStatus(showMessage = false) {
  try {
    const data = await requestJson("../www/api.cgi?action=status");
    renderAll(data);
    if (showMessage) showToast(t("refreshed"), "success");
  } catch (error) {
    showToast(error.message || String(error), "error");
  }
}

async function postAction(action, payload, successMessage) {
  setBusy(true);
  try {
    const data = await requestJson(
      `../www/api.cgi?action=${encodeURIComponent(action)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload || {}),
      },
    );
    renderAll(data);
    showToast(successMessage || data.message || t("success"), "success");
    return data;
  } catch (error) {
    showToast(error.message || String(error), "error");
    return null;
  } finally {
    setBusy(false);
  }
}

refreshBtn.addEventListener("click", () => refreshStatus(true));

document.getElementById("btnAbout").addEventListener("click", () => {
  document.getElementById("aboutModal").classList.remove("hidden");
});

joinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const network = (networkIdInput.value || "").trim();
  if (!/^[0-9a-fA-F]{16}$/.test(network)) {
    showToast(t("networkIdInvalid"), "error");
    networkIdInput.focus();
    return;
  }
  await postAction("join", { network }, t("joinedNetwork", { id: network }));
  networkIdInput.value = "";
});

moonForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const worldId = (moonJoinWorldIdInput.value || "").trim();
  const seed = (moonSeedInput.value || "").trim();
  if (!isValidMoonWorldId(worldId)) {
    showToast(t("worldIdInvalid"), "error");
    moonJoinWorldIdInput.focus();
    return;
  }
  if (!/^[0-9a-fA-F]{10}$/.test(seed)) {
    showToast(t("seedInvalid"), "error");
    moonSeedInput.focus();
    return;
  }
  const data = await postAction(
    "moon_join",
    { worldId, seed },
    t("joinedMoon", { id: worldId }),
  );
  if (data) {
    resetMoonJoinForm();
  }
});

moonCreateCancelBtn.addEventListener("click", () => {
  resetMoonCreateForm();
});

moonCreateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const worldId = (moonCreateWorldIdInput.value || "").trim();
  const stableEndpoints = (moonStableEndpointsInput.value || "").trim();
  if (!isValidMoonWorldId(worldId)) {
    showToast(t("worldIdInvalid"), "error");
    moonCreateWorldIdInput.focus();
    return;
  }
  if (!stableEndpoints) {
    showToast(t("endpointRequired"), "error");
    moonStableEndpointsInput.focus();
    return;
  }

  const action = editingCreatedMoonId ? "moon_update" : "moon_create";
  const payload = editingCreatedMoonId
    ? { oldWorldId: editingCreatedMoonId, worldId, stableEndpoints }
    : { worldId, stableEndpoints };
  const successMessage = editingCreatedMoonId
    ? t("updatedMoon", { id: worldId })
    : t("createdMoon", { id: worldId });
  const data = await postAction(action, payload, successMessage);
  if (data) {
    resetMoonCreateForm();
  }
});

document.addEventListener("click", async (event) => {
  if (event.target.closest("[data-close]")) {
    const modal = event.target.closest(".modal");
    if (modal) modal.classList.add("hidden");
    return;
  }
  if (event.target.id === "aboutModal") {
    document.getElementById("aboutModal").classList.add("hidden");
    return;
  }

  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const action = button.getAttribute("data-action");
  const network = button.getAttribute("data-network") || "";
  const worldId = button.getAttribute("data-world-id") || "";
  const orbitCommand = button.getAttribute("data-orbit-command") || "";
  const moonFileBase64 = button.getAttribute("data-moon-file-base64") || "";
  const moonFileName = button.getAttribute("data-moon-file-name") || "";
  if (action === "leave-network") {
    await postAction("leave", { network }, t("leftNetwork", { id: network }));
    return;
  }

  if (action === "edit-created-moon") {
    const moon = getCreatedMoonById(worldId);
    if (!moon) {
      showToast(t("missingMoon", { id: worldId }), "error");
      return;
    }
    editingCreatedMoonId = worldId;
    moonCreateBtn.textContent = t("update");
    moonCreateCancelBtn.hidden = false;
    moonCreateWorldIdInput.value = moon.id || "";
    moonStableEndpointsInput.value = moonEndpoints(moon).join("\n");
    moonCreateSupportEl.textContent = t("editing");
    moonCreateSupportEl.className = "pill pill-warn";
    moonCreateWorldIdInput.focus();
    return;
  }

  if (action === "copy-created-moon-orbit") {
    await copyText(orbitCommand, t("orbitCopied"));
    return;
  }

  if (action === "download-created-moon") {
    if (!moonFileBase64) {
      showToast(t("noMoonFile"), "error");
      return;
    }
    const link = document.createElement("a");
    link.href = `data:application/octet-stream;base64,${moonFileBase64}`;
    link.download = moonFileName || "moon.moon";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    return;
  }

  if (action === "start-created-moon") {
    await postAction(
      "moon_start",
      { worldId },
      t("startedMoon", { id: worldId }),
    );
    return;
  }

  if (action === "stop-created-moon") {
    await postAction(
      "moon_stop",
      { worldId },
      t("stoppedMoon", { id: worldId }),
    );
    if (editingCreatedMoonId && editingCreatedMoonId === worldId) {
      resetMoonCreateForm();
    }
    return;
  }

  if (action === "remove-created-moon") {
    await postAction(
      "moon_remove",
      { worldId },
      t("removedMoon", { id: worldId }),
    );
    if (editingCreatedMoonId && editingCreatedMoonId === worldId) {
      resetMoonCreateForm();
    }
    return;
  }

  if (action === "leave-joined-moon") {
    await postAction(
      "moon_leave",
      { worldId },
      t("removedMoon", { id: worldId }),
    );
    return;
  }
});

document.addEventListener("change", async (event) => {
  const checkbox = event.target.closest("input[data-setting]");
  if (!checkbox) return;
  const panel = checkbox.closest(".network-table-row");
  if (!panel) return;
  const network =
    panel.querySelector(".network-flags")?.getAttribute("data-network") || "";
  const setting = checkbox.getAttribute("data-setting") || "";
  if (!network) return;
  if (!setting) return;
  await postAction(
    "network_set",
    { network, settings: { [setting]: checkbox.checked } },
    t("networkSaved", { id: network }),
  );
});

applyPreferences();
window
  .matchMedia?.("(prefers-color-scheme: dark)")
  .addEventListener?.("change", () => applyPreferences());
window.addEventListener("storage", () => applyPreferences({ rerender: true }));
refreshStatus();
