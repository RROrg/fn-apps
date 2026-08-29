import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

const state = {
  apps: [],
  tasks: {},
  settings: { downloadDir: "", thirdPartySources: [] },
  query: "",
  view: "all",
  sourceFilter: "all",
  statusFilter: "all",
  downloadFilter: "all",
  page: 1,
  pageSize: 50,
  language: "zh-CN",
};

const I18N = {
  "zh-CN": {
    appTitle: "应用管理",
    search: "搜索",
    settings: "设置",
    about: "关于",
    shop: "商店",
    allShops: "全部商店",
    officialShop: "官方商店",
    thirdPartyShop: "三方商店",
    source: "来源",
    allSources: "全部来源",
    status: "状态",
    all: "全部",
    downloaded: "已下载",
    undownloaded: "未下载",
    downloading: "下载中",
    failed: "失败",
    installed: "已安装",
    upgradable: "可升级",
    downgradable: "可降级",
    notInstalled: "未安装",
    refresh: "刷新",
    openDir: "打开目录",
    openDirFailed: "无法打开文件管理器",
    icon: "图标",
    name: "名称",
    version: "版本",
    action: "操作",
    emptyApps: "暂无应用",
    loading: "正在加载...",
    loadFailed: "加载失败",
    totalItems: "共 {total} 项",
    pageSize: "每页条数:",
    jumpTo: "跳至",
    pageUnit: "页",
    savePath: "保存路径",
    sourceUrl: "源地址",
    addSource: "添加源",
    syncOnlineSource: "同步线上源",
    cancel: "取消",
    save: "保存",
    close: "关闭",
    sourceName: "名称",
    url: "URL",
    toggleSource: "开启/关闭",
    removeSource: "删除源",
    officialStore: "官方商店",
    thirdPartyStore: "三方商店",
    delete: "删除",
    download: "下载",
    deleting: "删除中",
    downloadingAction: "下载中",
    deleted: "已删除",
    downloadStarted: "已开始下载",
    refreshed: "已刷新",
    settingsSaved: "设置已保存",
    store: "商店",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    githubProxy: "GitHub 加速",
  },
  "en-US": {
    appTitle: "App Download",
    search: "Search",
    settings: "Settings",
    about: "About",
    shop: "Store",
    allShops: "All Stores",
    officialShop: "Official Store",
    thirdPartyShop: "Third-party Store",
    source: "Source",
    allSources: "All Sources",
    status: "Status",
    all: "All",
    downloaded: "Downloaded",
    undownloaded: "Not Downloaded",
    downloading: "Downloading",
    failed: "Failed",
    installed: "Installed",
    upgradable: "Upgradable",
    downgradable: "Downgradable",
    notInstalled: "Not Installed",
    refresh: "Refresh",
    openDir: "Open Folder",
    openDirFailed: "Unable to open file manager",
    icon: "Icon",
    name: "Name",
    version: "Version",
    action: "Action",
    emptyApps: "No apps",
    loading: "Loading...",
    loadFailed: "Load failed",
    totalItems: "{total} items",
    pageSize: "Per page:",
    jumpTo: "Go to",
    pageUnit: "page",
    savePath: "Save Path",
    sourceUrl: "Source URL",
    addSource: "Add Source",
    syncOnlineSource: "Sync Online Sources",
    cancel: "Cancel",
    save: "Save",
    close: "Close",
    sourceName: "Name",
    url: "URL",
    toggleSource: "Enable/Disable",
    removeSource: "Remove source",
    officialStore: "Official Store",
    thirdPartyStore: "Third-party Store",
    delete: "Delete",
    download: "Download",
    deleting: "Deleting",
    downloadingAction: "Downloading",
    deleted: "Deleted",
    downloadStarted: "Download started",
    refreshed: "Refreshed",
    settingsSaved: "Settings saved",
    store: "Store",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    githubProxy: "GitHub Proxy",
  },
};

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char],
  );
}

function taskKey(app) {
  return `${app.store}:${app.id}:${app.version}`;
}

function taskFor(app) {
  return state.tasks[taskKey(app)] || {};
}

function statusAppPayload() {
  return state.apps.map((app) => ({
    store: app.store,
    id: app.id,
    version: app.version,
  }));
}

function applyFileStatus(files = {}) {
  state.apps.forEach((app) => {
    const file = files[taskKey(app)];
    if (!file) return;
    const task = taskFor(app);
    const taskDone =
      [
        "downloaded",
        "done",
        "success",
        "succeed",
        "finished",
        "completed",
      ].includes(normalizeStatus(task.status)) ||
      ["已下载", "下载完成"].includes(task.status);
    if (file.exists) {
      app.downloaded = true;
      app.path = file.path || app.path || "";
      app.status = "downloaded";
    } else if (!taskDone) {
      app.downloaded = false;
      app.path = "";
      if (
        [
          "downloaded",
          "done",
          "success",
          "succeed",
          "finished",
          "completed",
        ].includes(normalizeStatus(app.status)) ||
        ["已下载", "下载完成"].includes(app.status)
      ) {
        app.status = "";
      }
    }
  });
}

function rowsStateSignature() {
  return filteredApps()
    .map((app) => {
      const task = taskFor(app);
      const kind = statusKind(app);
      return [
        taskKey(app),
        kind,
        task.status || "",
        app.status || "",
        task.fileExists === false ? "0" : task.fileExists === true ? "1" : "",
        app.downloaded ? "1" : "0",
        task.path || app.path || "",
      ].join("|");
    })
    .join("\n");
}

function normalizeStatus(value = "") {
  return String(value || "").toLowerCase();
}

function isDownloaded(app) {
  const task = taskFor(app);
  if (task.deleted) return false;
  if (task.fileExists === false) return false;
  const status = normalizeStatus(task.status || app.status);
  const doneStatus =
    [
      "downloaded",
      "done",
      "success",
      "succeed",
      "finished",
      "completed",
    ].includes(status) ||
    ["已下载", "下载完成"].includes(task.status || app.status);
  return (
    Boolean(app.downloaded) ||
    (task.fileExists === true && Boolean(task.path || app.path) && doneStatus)
  );
}

function statusKind(app) {
  if (isDownloaded(app)) return "downloaded";
  const status = normalizeStatus(taskFor(app).status || app.status);
  if (status === "downloading") return "downloading";
  if (status === "failed") return "failed";
  return "undownloaded";
}

function installKind(app) {
  return app.installStatus || "not_installed";
}

function installStatusClass(app) {
  const kind = installKind(app);
  if (kind === "installed") return "installed";
  if (kind === "upgradable") return "upgradable";
  if (kind === "downgradable") return "downgradable";
  return "not-installed";
}

function installStatusText(app) {
  const kind = installKind(app);
  if (kind === "installed") return t("installed");
  if (kind === "upgradable") return t("upgradable");
  if (kind === "downgradable") return t("downgradable");
  return t("notInstalled");
}

function isBusyAction(app) {
  const task = taskFor(app);
  if (!task || !task.status || task.deleted) return false;
  if (isDownloaded(app)) return false;
  return normalizeStatus(task.status) !== "failed";
}

function actionButtonContent(app, busy = false) {
  const downloading = busy || isBusyAction(app);
  if (!downloading) {
    const kind = statusKind(app);
    const downloaded = kind === "downloaded";
    return downloaded ? t("delete") : t("download");
  }
  return t("downloadingAction");
}

function applyLanguage() {
  const language = String(platformConfig.language || "").replace("_", "-");
  const resolved = language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
  const changed = resolved !== state.language;
  state.language = resolved;
  document.documentElement.lang = resolved;
  return changed;
}

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
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
    renderSourceSelect();
    renderSourceList(state.settings.thirdPartySources || []);
    renderRows();
  }
  return languageChanged;
}

async function api(action, data = {}) {
  // token 由 fnOS 网关注入；后端不再依赖前端转发 token（app-center 调用已前移）
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    credentials: "include",
    body: JSON.stringify({ action, ...data }),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) {
    throw new Error(result.message || `HTTP ${response.status}`);
  }
  return result;
}

// 直接调用 app-center（fnOS 网关注入鉴权，无需 token）。
// 后端不再转发 /app-center/ 请求，故 token 获取逻辑已彻底移除。
async function appCenter(path, options = {}) {
  const response = await fetch(`/app-center/v1/${path}`, {
    method: options.method || "GET",
    headers: options.body ? { "Content-Type": "application/json" } : {},
    cache: "no-store",
    credentials: "include",
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`app-center HTTP ${response.status}`);
  }
  return response.json();
}

async function defaultDownloadVolume() {
  // 默认下载卷由前端确定（参照 installer 的 loadVolumes），再传给后端
  try {
    const dv = await appCenter("common/remember-volume/config");
    const dvData = dv && dv.data ? dv.data : dv || {};
    const vid =
      dvData.downloadAndInstallVolumeID != null
        ? dvData.downloadAndInstallVolumeID
        : dvData.volumeID;
    return vid != null ? parseInt(vid) || 1 : 1;
  } catch (_error) {
    return 1;
  }
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3200);
}

async function openFileManager(path) {
  await sdk.openFileManager(path);
}

function fallbackIcon(app) {
  const name = app.name || app.id || "?";
  return `<div class="fallback-icon">${escapeHtml(name.slice(0, 1).toUpperCase())}</div>`;
}

function filteredApps() {
  const query = state.query.trim().toLowerCase();
  return state.apps.filter((app) => {
    const kind = statusKind(app);
    if (state.view === "official" && app.store !== "official") return false;
    if (state.view === "thirdparty" && app.store !== "thirdparty") return false;
    if (state.view === "downloaded" && kind !== "downloaded") return false;
    if (state.view === "undownloaded" && kind === "downloaded") return false;
    if (state.sourceFilter !== "all" && app.source !== state.sourceFilter)
      return false;
    if (state.statusFilter !== "all" && installKind(app) !== state.statusFilter)
      return false;
    if (state.downloadFilter === "downloaded" && kind !== "downloaded")
      return false;
    if (state.downloadFilter === "undownloaded" && kind === "downloaded")
      return false;
    if (!query) return true;
    return [app.name, app.id, app.version, app.source].some((value) =>
      String(value || "")
        .toLowerCase()
        .includes(query),
    );
  });
}

function pageItems(items) {
  const totalPages = Math.max(1, Math.ceil(items.length / state.pageSize));
  state.page = Math.min(Math.max(1, state.page), totalPages);
  const start = (state.page - 1) * state.pageSize;
  return {
    totalPages,
    rows: items.slice(start, start + state.pageSize),
  };
}

function pageButton(
  page,
  label = String(page),
  active = false,
  disabled = false,
) {
  return `<button class="page-btn ${active ? "active" : ""}" data-page="${page}" ${disabled ? "disabled" : ""} type="button">${escapeHtml(label)}</button>`;
}

function renderPager(total, totalPages) {
  const numbers = document.getElementById("pageNumbers");
  const prev = document.getElementById("prevPageBtn");
  const next = document.getElementById("nextPageBtn");
  const pages = [];
  const addPage = (page) =>
    pages.push(pageButton(page, String(page), page === state.page));

  if (totalPages <= 7) {
    for (let page = 1; page <= totalPages; page += 1) addPage(page);
  } else {
    addPage(1);
    if (state.page > 4) pages.push(pageButton(state.page - 3, "...", false));
    const start = Math.max(2, state.page - 1);
    const end = Math.min(totalPages - 1, state.page + 1);
    for (let page = start; page <= end; page += 1) addPage(page);
    if (state.page < totalPages - 3)
      pages.push(pageButton(state.page + 3, "...", false));
    addPage(totalPages);
  }

  numbers.innerHTML = pages.join("");
  prev.disabled = state.page <= 1;
  next.disabled = state.page >= totalPages;
  document.getElementById("jumpPageInput").max = String(totalPages);
  document.getElementById("summary").textContent = t("totalItems", { total });
}

function renderRows() {
  const rows = document.getElementById("appRows");
  const empty = document.getElementById("emptyState");
  const apps = filteredApps();
  const paged = pageItems(apps);

  empty.classList.toggle("hidden", apps.length > 0);
  renderPager(apps.length, paged.totalPages);

  rows.innerHTML = paged.rows
    .map((app) => {
      const kind = statusKind(app);
      const downloaded = kind === "downloaded";
      const busy = isBusyAction(app);
      const canDownload =
        app.store === "official"
          ? app.id && app.version && app.sourceID
          : app.downloadUrl;
      const icon = app.icon
        ? `<div class="icon-container">${fallbackIcon(app)}<img class="app-icon" src="${escapeHtml(app.icon)}" alt="" loading="lazy" onerror="this.classList.add('icon-err')"></div>`
        : fallbackIcon(app);
      const sourceLabel = escapeHtml(app.source || "-");
      return `
      <tr class="${app.orphaned ? "orphaned-row" : ""}">
        <td class="icon-cell">${icon}</td>
        <td>
          <div class="app-name">${escapeHtml(app.name || app.id)}</div>
          <div class="app-id">${escapeHtml(app.id || "")}</div>
        </td>
        <td>${escapeHtml(app.version || "-")}</td>
        <td>${app.store === "official" ? t("officialStore") : t("thirdPartyStore")}</td>
        <td>${sourceLabel}</td>
        <td><span class="status-pill ${installStatusClass(app)}">${escapeHtml(installStatusText(app))}</span></td>
        <td>
          <button class="download-btn ${downloaded ? "delete-btn" : ""} ${busy ? "is-progress" : ""}" data-action="${downloaded ? "delete" : "download"}" data-app-key="${escapeHtml(taskKey(app))}" ${!downloaded && !canDownload ? "disabled" : ""} ${busy ? "disabled" : ""} type="button">
            ${escapeHtml(actionButtonContent(app))}
          </button>
        </td>
      </tr>
    `;
    })
    .join("");
}

async function loadSettings() {
  const result = await api("settings");
  state.settings = result.settings || {
    downloadDir: "",
    thirdPartySources: [],
  };
  document.getElementById("downloadDirInput").value =
    state.settings.downloadDir || "";
  document.getElementById("githubProxyToggle").checked =
    state.settings.githubProxyEnabled !== false;
  document.getElementById("githubProxyUrlInput").value =
    state.settings.githubProxyUrl || "";
  renderSourceList(state.settings.thirdPartySources || []);
}

async function loadApps() {
  document.getElementById("summary").textContent = t("loading");
  try {
    const [appList, latest] = await Promise.all([
      appCenter("app/list?language=zh-CN"),
      appCenter("app/latest-release?language=zh-CN"),
    ]);
    const result = await api("process-apps", { appList, latest });
    state.apps = result.apps || [];
    state.tasks = result.tasks || {};
    applyFileStatus(result.files || {});
    const errors = result.errors || [];
    if (errors.length) {
      showToast(
        errors.map((item) => `${item.source}: ${item.message}`).join("；"),
        true,
      );
    }
  } catch (error) {
    state.apps = [];
    state.tasks = {};
    showToast(error.message, true);
  }
  renderRows();
}

async function refreshStatus() {
  try {
    const before = rowsStateSignature();
    const statusResults = {};
    const fetches = Object.entries(state.tasks || {}).map(
      async ([key, task]) => {
        if (task.store !== "official" || !task.taskId) return;
        try {
          const raw = await appCenter(
            `download/status?downloadTaskId=${encodeURIComponent(task.taskId)}&language=zh-CN`,
          );
          statusResults[key] = raw;
        } catch (_error) {
          // 单个任务查询失败不阻断整体轮询
        }
      },
    );
    await Promise.all(fetches);
    const result = await api("status", {
      apps: statusAppPayload(),
      statusResults,
    });
    state.tasks = result.tasks || {};
    applyFileStatus(result.files || {});
    if (rowsStateSignature() !== before) {
      renderRows();
    }
  } catch (_error) {
    // Keep polling quiet.
  }
}

function sourceRowTemplate(source = {}) {
  const name = escapeHtml(source.name || "");
  const url = escapeHtml(source.url || "");
  const enabled = source.enabled !== false ? "checked" : "";
  return `
    <div class="source-row">
      <label class="source-switch" title="${escapeHtml(t("toggleSource"))}">
        <input class="source-enabled" type="checkbox" ${enabled}>
        <span></span>
      </label>
      <input class="source-name" type="text" spellcheck="false" placeholder="${escapeHtml(t("sourceName"))}" value="${name}">
      <input class="source-url" type="text" spellcheck="false" placeholder="${escapeHtml(t("url"))}" value="${url}">
      <button class="icon-btn source-remove" type="button" aria-label="${escapeHtml(t("removeSource"))}" title="${escapeHtml(t("removeSource"))}">×</button>
    </div>
  `;
}

function renderSourceList(sources = []) {
  const list = document.getElementById("sourceList");
  if (!list) return;
  const rows =
    Array.isArray(sources) && sources.length
      ? sources
      : [{ name: "", url: "", enabled: true }];
  list.innerHTML = rows.map((source) => sourceRowTemplate(source)).join("");
}

function collectSources() {
  const list = document.getElementById("sourceList");
  if (!list) return [];
  return Array.from(list.querySelectorAll(".source-row"))
    .map((row) => ({
      name: row.querySelector(".source-name")?.value.trim() || "",
      url: row.querySelector(".source-url")?.value.trim() || "",
      enabled: row.querySelector(".source-enabled")?.checked ?? true,
    }))
    .filter((source) => source.name || source.url);
}

function setPage(page) {
  state.page = Number(page) || 1;
  renderRows();
}

function resetPaging() {
  state.page = 1;
}

function sourceOptionsForView() {
  const scope =
    state.view === "official" || state.view === "thirdparty" ? state.view : "";
  const sources = new Set();
  state.apps.forEach((app) => {
    if (scope && app.store !== scope) return;
    if (app.source) sources.add(app.source);
  });
  return Array.from(sources).sort((left, right) =>
    left.localeCompare(right, "zh-Hans-CN"),
  );
}

function renderSourceSelect() {
  const sourceSelect = document.getElementById("storeSelect");
  if (!sourceSelect) return;
  const options = sourceOptionsForView();
  const current = state.sourceFilter;
  const fragments = [
    `<option value="all">${escapeHtml(t("allSources"))}</option>`,
  ];
  options.forEach((source) => {
    fragments.push(
      `<option value="${escapeHtml(source)}">${escapeHtml(source)}</option>`,
    );
  });
  sourceSelect.innerHTML = fragments.join("");
  if (current !== "all" && !options.includes(current)) {
    state.sourceFilter = "all";
  }
  sourceSelect.value = state.sourceFilter;
}

function syncSourceControls() {
  const shopSelect = document.getElementById("shopSelect");
  if (shopSelect) shopSelect.value = state.view;
  renderSourceSelect();
}

function openSettings() {
  document.getElementById("settingsModal").classList.remove("hidden");
}

function openAbout() {
  document.getElementById("aboutModal").classList.remove("hidden");
}

function closeModals() {
  document
    .querySelectorAll(".modal")
    .forEach((modal) => modal.classList.add("hidden"));
}

function bindEvents() {
  document.getElementById("shopSelect").addEventListener("change", (event) => {
    state.view = event.target.value;
    state.sourceFilter = "all";
    syncSourceControls();
    resetPaging();
    renderRows();
  });

  document.getElementById("storeSelect").addEventListener("change", (event) => {
    state.sourceFilter = event.target.value;
    syncSourceControls();
    resetPaging();
    renderRows();
  });

  document
    .getElementById("statusSelect")
    .addEventListener("change", (event) => {
      state.statusFilter = event.target.value;
      resetPaging();
      renderRows();
    });

  document
    .getElementById("downloadFilterSelect")
    .addEventListener("change", (event) => {
      state.downloadFilter = event.target.value;
      resetPaging();
      renderRows();
    });

  document.getElementById("searchInput").addEventListener("input", (event) => {
    state.query = event.target.value;
    resetPaging();
    renderRows();
  });

  document
    .getElementById("pageSizeSelect")
    .addEventListener("change", (event) => {
      state.pageSize = Number(event.target.value) || 50;
      resetPaging();
      renderRows();
    });

  document.getElementById("pageNumbers").addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (button) setPage(button.dataset.page);
  });

  document
    .getElementById("prevPageBtn")
    .addEventListener("click", () => setPage(state.page - 1));
  document
    .getElementById("nextPageBtn")
    .addEventListener("click", () => setPage(state.page + 1));
  document
    .getElementById("jumpPageInput")
    .addEventListener("change", (event) => setPage(event.target.value));

  document
    .getElementById("settingsBtn")
    .addEventListener("click", openSettings);

  document.getElementById("aboutBtn").addEventListener("click", openAbout);

  document.getElementById("refreshBtn").addEventListener("click", async () => {
    try {
      await loadApps();
      showToast(t("refreshed"));
    } catch (error) {
      showToast(error.message, true);
    }
  });

  document.getElementById("openDirBtn").addEventListener("click", async () => {
    const dir =
      state.settings.downloadDir ||
      "/var/apps/fn-appdownload/shares/fn-appdownload/downloads";
    try {
      await openFileManager(dir);
    } catch (error) {
      showToast(error.message || t("openDirFailed"), true);
    }
  });

  document
    .querySelectorAll("[data-close]")
    .forEach((node) => node.addEventListener("click", closeModals));

  document.getElementById("addSourceBtn").addEventListener("click", () => {
    const list = document.getElementById("sourceList");
    list.insertAdjacentHTML(
      "beforeend",
      sourceRowTemplate({ name: "", url: "", enabled: true }),
    );
  });

  document
    .getElementById("syncSourceBtn")
    .addEventListener("click", async () => {
      const btn = document.getElementById("syncSourceBtn");
      btn.disabled = true;
      const originalText = btn.textContent;
      btn.textContent = t("loading");

      async function tryFetch(url) {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) {
          const err = new Error(`HTTP ${response.status}`);
          err.status = response.status;
          throw err;
        }
        return response.json();
      }

      async function fetchSources() {
        const rawUrl =
          "https://raw.githubusercontent.com/RROrg/fn-apps/refs/heads/main/fn-appdownload/thirdPartySources.json";
        const proxyEnabled =
          document.getElementById("githubProxyToggle").checked;
        const proxyUrl = document
          .getElementById("githubProxyUrlInput")
          .value.trim()
          .replace(/\/+$/, "");

        // 如果代理已启用，优先走代理
        if (proxyEnabled && proxyUrl) {
          try {
            return await tryFetch(`${proxyUrl}/${rawUrl}`);
          } catch (err) {
            if (err.status !== 429) throw err;
            // 429 时降级到直连
          }
        }

        // 直连
        return await tryFetch(rawUrl);
      }

      try {
        const remoteSources = await fetchSources();
        if (!Array.isArray(remoteSources)) throw new Error(t("loadFailed"));

        const existingSources = collectSources();
        let added = 0;
        let updated = 0;

        remoteSources.forEach((remote) => {
          const idx = existingSources.findIndex((s) => s.url === remote.url);
          if (idx === -1) {
            existingSources.push({
              name: remote.name || "",
              url: remote.url || "",
              enabled: remote.enabled !== false,
            });
            added++;
          } else if (existingSources[idx].name !== remote.name) {
            existingSources[idx].name = remote.name || "";
            updated++;
          }
        });

        renderSourceList(existingSources);
        const summary = added
          ? `添加 ${added} 个，更新 ${updated} 个`
          : `已是最新`;
        showToast(t("syncOnlineSource") + "：" + summary);
      } catch (error) {
        const msg =
          error.status === 429
            ? "请求过于频繁，请稍后重试或启用 GitHub 加速代理"
            : error.message;
        showToast(msg, true);
      } finally {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });

  document.getElementById("sourceList").addEventListener("click", (event) => {
    const button = event.target.closest(".source-remove");
    if (!button) return;
    const row = button.closest(".source-row");
    if (row) row.remove();
    const list = document.getElementById("sourceList");
    if (list && !list.querySelector(".source-row")) {
      list.insertAdjacentHTML(
        "beforeend",
        sourceRowTemplate({ name: "", url: "", enabled: true }),
      );
    }
  });

  document
    .getElementById("settingsForm")
    .addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const result = await api("save-settings", {
          downloadDir: document.getElementById("downloadDirInput").value.trim(),
          thirdPartySources: collectSources(),
          githubProxyEnabled:
            document.getElementById("githubProxyToggle").checked,
          githubProxyUrl: document
            .getElementById("githubProxyUrlInput")
            .value.trim(),
        });
        state.settings = result.settings || state.settings;
        renderSourceList(state.settings.thirdPartySources || []);
        closeModals();
        showToast(t("settingsSaved"));
        await loadApps();
        syncSourceControls();
      } catch (error) {
        showToast(error.message, true);
      }
    });

  document
    .getElementById("appRows")
    .addEventListener("click", async (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const app = state.apps.find(
        (item) => taskKey(item) === button.dataset.appKey,
      );
      if (!app) return;
      const action = button.dataset.action;
      button.disabled = true;
      button.classList.add("is-progress");
      button.textContent =
        action === "delete" ? t("deleting") : t("downloadingAction");
      try {
        let result;
        if (action === "download" && app.store === "official") {
          // 官方应用：前端直接向 app-center 创建下载任务，后端只注册任务状态
          // 默认下载卷由前端确定，再传给后端
          const downloadVolume =
            Number(app.volumeID) || (await defaultDownloadVolume()) || 1;
          const taskResult = await appCenter("download/task", {
            method: "POST",
            body: {
              packageSourceType: app.packageSourceType || "cloud",
              appName: app.id,
              sourceID: app.sourceID,
              version: app.version,
              volumeID: downloadVolume,
            },
          });
          result = await api("download", {
            app: { ...app, volumeID: downloadVolume },
            taskResult,
          });
        } else {
          result = await api(action, { app });
        }
        if (action === "delete") {
          delete state.tasks[taskKey(app)];
          app.downloaded = false;
          app.path = "";
          app.status = "";
          showToast(t("deleted"));
        } else {
          state.tasks[taskKey(app)] = result.task || {};
          showToast(t("downloadStarted"));
        }
        renderRows();
      } catch (error) {
        showToast(error.message, true);
        button.classList.remove("is-progress");
        button.disabled = false;
        button.textContent = action === "delete" ? t("delete") : t("download");
        renderRows();
      }
    });
}

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

  bindEvents();
  try {
    await loadSettings();
    await loadApps();
    syncSourceControls();
    setInterval(refreshStatus, 4000);
  } catch (error) {
    showToast(error.message, true);
    document.getElementById("summary").textContent = t("loadFailed");
  }
});

/* ===== 黑客帝国矩阵雨 ===== */
(function initMatrixRain() {
  const canvas = document.getElementById("matrixRain");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // 矩阵字符集：复杂繁体汉字（笔画繁密，更有黑客帝国密雨感）
  const CHARS = "菩提本无树，明镜亦非台。本来无一物，何处惹尘埃！";

  let columns = 0;
  let drops = [];
  let chars = [];
  let fontSize = 12;
  // 下落速度（每帧移动的字符高度数，<1 即慢速下落）
  let speed = 0.1;

  function isDark() {
    return document.documentElement.getAttribute("data-theme") !== "light";
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    fontSize = 18;
    columns = Math.floor(rect.width / fontSize);
    drops = Array.from({ length: columns }, () =>
      Math.floor((Math.random() * rect.height) / fontSize),
    );
    // 每列一个固定字符：雨滴存活期间不变，只有新雨滴开始时才换新字符
    chars = Array.from(
      { length: columns },
      () => CHARS[Math.floor(Math.random() * CHARS.length)],
    );
  }

  function draw() {
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    ctx.fillStyle = isDark() ? "rgba(13,17,23,0.12)" : "rgba(255,255,255,0.12)";
    ctx.fillRect(0, 0, rect.width, rect.height);
    ctx.font = fontSize + "px 'Courier New', monospace";

    for (let i = 0; i < columns; i++) {
      // 雨滴字符在存活期间保持固定不变，只随位置下移
      const char = chars[i];
      const y = drops[i] * fontSize;
      ctx.fillStyle = isDark() ? "#0f0" : "#006b00";
      ctx.fillText(char, i * fontSize, y);
      // 雨滴落到底部后开始新雨滴：重置位置并换一个新字符
      if (y > rect.height && Math.random() > 0.975) {
        drops[i] = -Math.random() * 6;
        chars[i] = CHARS[Math.floor(Math.random() * CHARS.length)];
      }
      drops[i] += speed;
    }
    requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener("resize", resize);
  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  requestAnimationFrame(draw);
})();
