import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

const state = {
  selectedFile: null,
  currentStep: 1,
  downloadTaskId: "",
  installTaskId: "",
  appName: "",
  version: "",
  language: "zh-CN",
  theme: "light",
  polling: null,
  installInfo: null,
  wizardData: {},
  volumeID: 1,
  currentDir: "",
  dirHistory: [],
  isUpdate: false,
  installedInfo: null,
  canUpdate: false,
  canOverwrite: false,
  installAction: "install",
  installed: false,
  packageType: "file",
  _updateConfirmed: false,
};

const I18N = {
  "zh-CN": {
    appTitle: "📦 应用安装器",
    stepSelect: "选择文件",
    stepParse: "解析安装包",
    stepInstall: "安装中",
    stepDone: "完成",
    selectPackage: "选择安装包",
    refresh: "🔄 刷新",
    pathPlaceholder: "输入 NAS 目录路径，如 /vol1/docker",
    browse: "浏览",
    scanning: "正在扫描 NAS 中的 FPK 文件...",
    noFiles: "未找到 FPK 文件",
    noFilesDesc: "请确认 NAS 中存在 .fpk 安装包文件",
    nextStep: "下一步",
    parsePackage: "解析安装包",
    parsingPackage: "正在解析安装包...",
    parseProgress: "解析进度 {progress}%",
    prevStep: "上一步",
    install: "安装",
    installing: "安装中",
    installingApp: "正在安装应用...",
    installProgress: "安装进度 {progress}%",
    installSuccess: "安装成功",
    installFailed: "安装失败",
    continueInstall: "继续安装",
    fileSize: "大小",
    fileVersion: "版本",
    filePath: "路径",
    appName: "应用名称",
    appVersion: "版本",
    appMaintainer: "维护者",
    appDesc: "描述",
    appSource: "来源",
    appInstallType: "安装类型",
    appVolumeID: "安装卷",
    wizardConfig: "安装配置",
    wizardTips: "配置提示",
    errorTokenNotFound: "鉴权失败：未找到授权令牌，请从系统桌面打开此应用",
    errorNetwork: "网络请求失败",
    errorUnknown: "未知错误",
    loading: "加载中...",
    versionUnknown: "未知",
    sizeUnknown: "未知",
    parentDir: "上级目录",
    emptyDir: "此目录为空",
    selectFromDir: "从目录中选择",
    scanAll: "扫描全部",
    selectVolume: "选择安装卷",
    volumeFree: "可用",
    installReady: "准备就绪，点击安装按钮开始安装",
    openFileTitle: "安装应用",
    openFileDesc: "正在准备安装 {name}...",
    alreadyInstalling: "已在安装中：{name}",
    alreadyInstalled: "应用已安装，无需重复安装",
    updateApp: "更新",
    updateAvailable: "发现新版本，可更新",
    installedVersion: "已安装版本",
    newVersion: "新版本",
    updatingApp: "正在更新应用...",
    updateSuccess: "更新成功",
    updateFailed: "更新失败",
    overwriteApp: "覆盖",
    overwriteAvailable: "已安装相同或更高版本，可覆盖",
    overwritingApp: "正在覆盖安装...",
    overwriteSuccess: "覆盖成功",
    overwriteFailed: "覆盖失败",
    overwriteConfirmTitle: "覆盖安装",
    overwriteConfirmDesc:
      "当前已安装 {installedVersion}，安装包版本 {newVersion}，将覆盖安装，是否继续？",
    sameVersion: "当前已是最新版本",
    updateConfirmTitle: "发现新版本",
    updateConfirmDesc:
      "当前已安装 {installedVersion}，发现新版本 {newVersion}，是否更新？",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
  },
  "en-US": {
    appTitle: "📦 App Installer",
    stepSelect: "Select File",
    stepParse: "Parse Package",
    stepInstall: "Installing",
    stepDone: "Done",
    selectPackage: "Select Package",
    refresh: "🔄 Refresh",
    pathPlaceholder: "Enter NAS directory path, e.g. /vol1/docker",
    browse: "Browse",
    scanning: "Scanning NAS for FPK files...",
    noFiles: "No FPK files found",
    noFilesDesc: "Please confirm that .fpk package files exist on NAS",
    nextStep: "Next",
    parsePackage: "Parse Package",
    parsingPackage: "Parsing package...",
    parseProgress: "Parse progress {progress}%",
    prevStep: "Previous",
    install: "Install",
    installing: "Installing",
    installingApp: "Installing application...",
    installProgress: "Install progress {progress}%",
    installSuccess: "Installation Successful",
    installFailed: "Installation Failed",
    continueInstall: "Install Another",
    fileSize: "Size",
    fileVersion: "Version",
    filePath: "Path",
    appName: "App Name",
    appVersion: "Version",
    appMaintainer: "Maintainer",
    appDesc: "Description",
    appSource: "Source",
    appInstallType: "Install Type",
    appVolumeID: "Volume ID",
    wizardConfig: "Installation Config",
    wizardTips: "Configuration Tips",
    errorTokenNotFound:
      "Auth failed: authorization token not found, please open this app from system desktop",
    errorNetwork: "Network request failed",
    errorUnknown: "Unknown error",
    loading: "Loading...",
    versionUnknown: "Unknown",
    sizeUnknown: "Unknown",
    parentDir: "Parent Directory",
    emptyDir: "This directory is empty",
    selectFromDir: "Select from directory",
    scanAll: "Scan All",
    selectVolume: "Select Volume",
    volumeFree: "Free",
    installReady: "Ready to install, click the Install button to begin",
    openFileTitle: "Install App",
    openFileDesc: "Preparing to install {name}...",
    alreadyInstalling: "Already installing: {name}",
    alreadyInstalled: "App is already installed",
    updateApp: "Update",
    updateAvailable: "New version available, can update",
    installedVersion: "Installed Version",
    newVersion: "New Version",
    updatingApp: "Updating application...",
    updateSuccess: "Update Successful",
    updateFailed: "Update Failed",
    overwriteApp: "Overwrite",
    overwriteAvailable: "Same or higher version installed, can overwrite",
    overwritingApp: "Overwriting application...",
    overwriteSuccess: "Overwrite Successful",
    overwriteFailed: "Overwrite Failed",
    overwriteConfirmTitle: "Overwrite Install",
    overwriteConfirmDesc:
      "Currently installed {installedVersion}, package version {newVersion}. This will overwrite the install. Continue?",
    sameVersion: "Already on the latest version",
    updateConfirmTitle: "New Version Available",
    updateConfirmDesc:
      "Currently installed {installedVersion}, new version {newVersion} available. Update now?",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
  },
};

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_error) {
    return value || "";
  }
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
  document.title = t("appTitle").replace(/📦\s*/, "");

  if (rerender && languageChanged) {
    const dirBrowser = document.getElementById("dirBrowser");
    const isDirView = dirBrowser && !dirBrowser.classList.contains("hidden");
    if (state.currentStep === 1) {
      if (isDirView && state._dirEntries) {
        renderDirEntries(state._dirEntries, state.currentDir);
      } else if (state._files) {
        renderFileList(state._files);
      }
    } else if (state.installInfo) {
      loadInstallInfo();
    }
  }
  return languageChanged;
}

function formatSize(bytes) {
  if (!bytes || bytes <= 0) return t("sizeUnknown");
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i += 1;
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

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

async function api(action, data = {}) {
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

// ---------- app-center 安装流程封装（前端直连，网关注入鉴权） ----------

// 归一化 app-center 响应：取 data 或整体
function acData(result) {
  return result && typeof result === "object" && result.data != null
    ? result.data
    : result;
}

// 已安装应用列表：只从 /app/installed 获取。
// 列表项字段：name(appName) / version(已安装版本) / installedVolumeID(安装卷)。
let _installedAppsCache = null;
async function acInstalledApps(force) {
  if (!force && _installedAppsCache) return _installedAppsCache;
  let apps = [];
  try {
    const result = await appCenter(`app/installed?language=${state.language}`);
    const data = acData(result);
    if (Array.isArray(data)) {
      apps = data;
    } else if (data && typeof data === "object") {
      for (const key of ["list", "apps", "items"]) {
        if (Array.isArray(data[key])) {
          apps = data[key];
          break;
        }
      }
    }
  } catch (_e) {}
  _installedAppsCache = apps;
  return apps;
}
function clearInstalledAppsCache() {
  _installedAppsCache = null;
}

// 在 /app/installed 列表里按名字查找应用
function findInstalledApp(apps, appName) {
  const want = String(appName ?? "").trim();
  if (!want) return null;
  const keys = [
    "appName",
    "app_name",
    "name",
    "appKey",
    "app_key",
    "appId",
    "app_id",
    "id",
    "packageName",
    "package_name",
  ];
  for (const app of apps || []) {
    if (!app || typeof app !== "object") continue;
    for (const key of keys) {
      if (String(app[key] ?? "").trim() === want) return app;
    }
  }
  return null;
}

// 已安装/可更新检测：只读 /app/installed，按名字匹配即视为已安装。
// 返回 { installed, info }，info 为 { name, version, volumeID }。
async function detectInstalled(appName) {
  if (!appName) return { installed: false, info: null };
  let existing = null;
  try {
    existing = findInstalledApp(await acInstalledApps(), appName);
    // 首次未命中时强制刷新一次，排除 _installedAppsCache 陈旧缓存干扰
    if (!existing) {
      existing = findInstalledApp(await acInstalledApps(true), appName);
    }
  } catch (_e) {}
  if (!existing) return { installed: false, info: null };
  return {
    installed: true,
    info: {
      name: String(
        existing.appName ??
          existing.app_name ??
          existing.name ??
          existing.appKey ??
          existing.displayName ??
          appName,
      ),
      version: String(existing.version ?? existing.installedVersion ?? ""),
      volumeID: String(existing.installedVolumeID ?? ""),
    },
  };
}

// 版本比较：a > b 返回 1，a < b 返回 -1，相等返回 0。兼容数字段与点分/横杠版本。
function compareVersions(a, b) {
  const pa = String(a ?? "")
    .trim()
    .toLowerCase();
  const pb = String(b ?? "")
    .trim()
    .toLowerCase();
  if (pa === pb) return 0;
  const normalize = (s) =>
    (s || "").split(/[.\-_+]/).map((p) => (/^\d+$/.test(p) ? Number(p) : p));
  const na = normalize(pa);
  const nb = normalize(pb);
  const len = Math.max(na.length, nb.length);
  for (let i = 0; i < len; i += 1) {
    const x = na[i];
    const y = nb[i];
    if (x === undefined) return -1;
    if (y === undefined) return 1;
    if (typeof x === "number" && typeof y === "number") {
      if (x !== y) return x > y ? 1 : -1;
    } else if (String(x) !== String(y)) {
      return String(x) > String(y) ? 1 : -1;
    }
  }
  return 0;
}

// 解析本次安装动作：install(未安装) / update(已装低于新包) / overwrite(已装≥新包)。
// newVersion 为空或无法比较时，视为全新安装走 install。
function resolveInstallAction(instVer, newVer) {
  const iv = String(instVer ?? "").trim();
  const nv = String(newVer ?? "").trim();
  if (!iv) return "install";
  if (!nv) return "overwrite";
  const cmp = compareVersions(nv, iv);
  if (cmp > 0) return "update";
  return "overwrite";
}

async function acDownloadTask(payload) {
  return appCenter("download/task", { method: "POST", body: payload });
}
async function acDownloadStatus(taskId) {
  return appCenter(
    `download/status?downloadTaskId=${encodeURIComponent(taskId)}&language=${state.language}`,
  );
}
async function acInstallInfo(appName, version, packageType, isUpdate) {
  // 后端 install/info 解码进 InstallWizardRequest，要求必填 version 字段。
  // 更新场景除 updateVersion 外同时携带 version（新包版本），避免 10030(Version required)。
  const base = `appName=${encodeURIComponent(appName)}&packageType=${encodeURIComponent(packageType)}&language=${state.language}`;
  const url = isUpdate
    ? `install/info?version=${encodeURIComponent(version)}&updateVersion=${encodeURIComponent(version)}&${base}`
    : `install/info?version=${encodeURIComponent(version)}&${base}`;
  return appCenter(url);
}
async function acInstallTask(payload) {
  return appCenter("install/task", { method: "POST", body: payload });
}
async function acUpdateTask(payload) {
  return appCenter("update/task", { method: "POST", body: payload });
}
async function acInstallStatus(taskId) {
  return appCenter("install/status", {
    method: "POST",
    body: { taskId, language: state.language },
  });
}
async function acUpdateStatus(taskId) {
  return appCenter("update/status", {
    method: "POST",
    body: { taskId, language: state.language },
  });
}
async function acTaskStatus(taskId) {
  return appCenter("common/task-status", {
    method: "POST",
    body: { taskId, language: state.language },
  });
}

// 解析任务响应里的 taskId（兼容多种返回字段）
function extractTaskId(result) {
  const data = acData(result);
  const cands = [];
  if (data && typeof data === "object") {
    cands.push(data.installTaskId, data.taskId, data.id, data.downloadTaskId);
  }
  cands.push(
    result.installTaskId,
    result.taskId,
    result.id,
    result.downloadTaskId,
  );
  for (const c of cands) {
    if (c !== undefined && c !== null && String(c) !== "") return String(c);
  }
  return "";
}

// 归一化安装/下载状态
function normalizeTaskStatus(rawStatus) {
  if (typeof rawStatus === "number") {
    const s = Math.floor(rawStatus);
    if (s === 0) return { value: "pending", done: false };
    if (s === 1) return { value: "running", done: false };
    if (s === 2) return { value: "success", done: true };
    if (s === 3) return { value: "failed", done: true };
    if (s === 4) return { value: "cancelled", done: true };
    if (s === 5) return { value: "notfound", done: true };
    return { value: String(s), done: false };
  }
  const lower = String(rawStatus || "").toLowerCase();
  if (
    [
      "done",
      "success",
      "succeed",
      "finished",
      "completed",
      "installed",
      "downloaded",
    ].includes(lower)
  ) {
    return { value: "success", done: true };
  }
  if (["fail", "failed", "error"].includes(lower)) {
    return { value: "failed", done: true };
  }
  if (["cancel", "cancelled", "canceled"].includes(lower)) {
    return { value: "cancelled", done: true };
  }
  return { value: lower || "pending", done: false };
}

// 从 app-center 响应取 message/msg/outputText
function acMessage(result, data) {
  const msg =
    (data && (data.outputText || data.message || data.msg)) ||
    result.outputText ||
    result.message ||
    result.msg ||
    "";
  return String(msg || "");
}

// 判断 app-center 错误码是否命中（兼容 code 在顶层或 data）
function acCode(result) {
  if (result && typeof result === "object") {
    const c = result.code || (result.data && result.data.code) || 0;
    return Number(c) || 0;
  }
  return 0;
}

// 若 app-center 返回业务错误码（且无 data），则抛出错误
// 抛出的 Error 挂上 code 属性，供上层 catch 用 acCode 读取真实业务错误码。
function acThrowIfError(result) {
  const code = acCode(result);
  if (code && !(result && result.data)) {
    const err = new Error(acMessage(result) || `app-center code ${code}`);
    err.code = code;
    throw err;
  }
  return result;
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3000);
}

function showStep(step) {
  state.currentStep = step;
  for (let i = 1; i <= 4; i += 1) {
    const el = document.getElementById(`step${i}`);
    if (el) el.classList.toggle("hidden", i !== step);
  }
  updateStepIndicator(step);
}

function updateStepIndicator(currentStep) {
  for (let i = 1; i <= 4; i += 1) {
    const circle = document.getElementById(`stepCircle${i}`);
    const label = document.getElementById(`stepLabel${i}`);
    if (!circle || !label) continue;

    circle.classList.remove("active", "done", "error");
    label.classList.remove("active", "done");

    if (i < currentStep) {
      circle.classList.add("done");
      label.classList.add("done");
    } else if (i === currentStep) {
      circle.classList.add("active");
      label.classList.add("active");
    }
  }

  for (let i = 1; i <= 3; i += 1) {
    const connector = document.getElementById(`connector${i}`);
    if (connector) {
      connector.classList.toggle("done", i < currentStep);
    }
  }
}

function renderFileList(files) {
  const list = document.getElementById("fileList");
  if (!files || files.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="icon">📂</div>
        <p>${t("noFiles")}</p>
        <p class="no-files-desc">${t("noFilesDesc")}</p>
      </div>`;
    return;
  }

  list.innerHTML = files
    .map(
      (file) => `
    <div class="file-item${state.selectedFile?.path === file.path ? " selected" : ""}"
         data-path="${escapeHtml(file.path)}" data-action="select">
      <div class="file-icon">📦</div>
      <div class="file-info">
        <div class="file-name">${escapeHtml(file.name)}</div>
        <div class="file-meta">
          ${t("fileVersion")}: ${escapeHtml(file.version || t("versionUnknown"))} · ${t("fileSize")}: ${formatSize(file.size)}
        </div>
      </div>
      <div class="file-check">${state.selectedFile?.path === file.path ? "✓" : ""}</div>
    </div>`,
    )
    .join("");
}

function selectFile(el) {
  const path = el.dataset.path;
  const files = state._files || [];
  state.selectedFile = files.find((f) => f.path === path) || null;
  renderFileList(files);
  document.getElementById("btnNext1").disabled = !state.selectedFile;
}

async function loadFiles() {
  const list = document.getElementById("fileList");
  const dirBrowser = document.getElementById("dirBrowser");
  dirBrowser.classList.add("hidden");
  list.classList.remove("hidden");
  list.innerHTML = `
    <div class="empty-state">
      <div class="loading-spinner large"></div>
      <p>${t("scanning")}</p>
    </div>`;
  state.selectedFile = null;
  document.getElementById("btnNext1").disabled = true;

  try {
    const result = await api("list-files");
    state._files = result.files || [];
    renderFileList(state._files);
  } catch (error) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="icon">❌</div>
        <p>${escapeHtml(error.message)}</p>
      </div>`;
  }
}

async function browsePath() {
  const result = await sdk.pickUserFile({
    directory: false,
    multiple: false,
    accept: [".fpk"],
    title: t("selectPackage"),
    okText: t("nextStep"),
    sidebarGroup: ["myFiles", "otherShare", "favorites"],
  });
  const path = result?.data?.[0];
  if (!path) return;
  state.selectedFile = { path, name: path.split("/").pop() || path };
  document.getElementById("btnNext1").disabled = false;
  renderFileList([state.selectedFile]);
}

async function browseDir(dir) {
  const dirBrowser = document.getElementById("dirBrowser");
  const dirList = document.getElementById("dirList");
  const fileList = document.getElementById("fileList");

  dirBrowser.classList.remove("hidden");
  fileList.classList.add("hidden");
  state.currentDir = dir;

  dirList.innerHTML = `
    <div class="empty-state compact">
      <div class="loading-spinner large"></div>
      <p>${t("loading")}</p>
    </div>`;

  try {
    const result = await api("list-dir", { directory: dir });
    state._dirEntries = result.entries || [];
    renderBreadcrumb(dir);
    renderDirEntries(state._dirEntries, dir);
  } catch (error) {
    dirList.innerHTML = `
      <div class="empty-state compact">
        <div class="icon">❌</div>
        <p>${escapeHtml(error.message)}</p>
      </div>`;
  }
}

function renderBreadcrumb(dir) {
  const breadcrumb = document.getElementById("dirBreadcrumb");
  const parts = dir.split("/").filter(Boolean);
  let html = `<span class="breadcrumb-item" data-action="browse" data-path="/">/</span>`;
  let path = "";
  parts.forEach((part, i) => {
    path += "/" + part;
    const isLast = i === parts.length - 1;
    html += `<span class="breadcrumb-sep">/</span>`;
    if (isLast) {
      html += `<span class="breadcrumb-item active">${escapeHtml(part)}</span>`;
    } else {
      html += `<span class="breadcrumb-item" data-action="browse" data-path="${escapeHtml(path)}">${escapeHtml(part)}</span>`;
    }
  });
  breadcrumb.innerHTML = html;
}

function renderDirEntries(entries, currentDir) {
  const dirList = document.getElementById("dirList");
  const parentPath =
    currentDir === "/"
      ? ""
      : currentDir.split("/").slice(0, -1).join("/") || "/";

  let html = "";
  if (parentPath) {
    html += `
      <div class="dir-entry dir-parent" data-action="browse" data-path="${escapeHtml(parentPath)}">
        <span class="dir-icon">📁</span>
        <span class="dir-name">.. (${t("parentDir")})</span>
      </div>`;
  }

  if (entries.length === 0 && !parentPath) {
    html += `<div class="empty-state compact"><p>${t("emptyDir")}</p></div>`;
  }

  const dirs = entries.filter((e) => e.isDir);
  const files = entries.filter((e) => !e.isDir);

  dirs.forEach((entry) => {
    html += `
      <div class="dir-entry" data-action="browse" data-path="${escapeHtml(entry.path)}">
        <span class="dir-icon">📁</span>
        <span class="dir-name">${escapeHtml(entry.name)}</span>
      </div>`;
  });

  files.forEach((entry) => {
    const isSelected = state.selectedFile?.path === entry.path;
    html += `
      <div class="dir-entry fpk-entry${isSelected ? " selected" : ""}" data-action="select-fpk" data-path="${escapeHtml(entry.path)}">
        <span class="dir-icon">📦</span>
        <span class="dir-name">${escapeHtml(entry.name)}</span>
        ${entry.version ? `<span class="dir-meta">${escapeHtml(entry.version)} · ${formatSize(entry.size)}</span>` : ""}
        ${isSelected ? '<span class="dir-check">✓</span>' : ""}
      </div>`;
  });

  if (files.length > 0) {
    html += `
      <div class="dir-actions">
        <button class="btn btn-primary btn-sm" data-action="scan-current" data-i18n="selectFromDir">${t("selectFromDir")}</button>
      </div>`;
  }

  dirList.innerHTML = html;
}

function selectFpkFromBrowser(el, path) {
  document.querySelectorAll(".fpk-entry").forEach((e) => {
    e.classList.remove("selected");
    const check = e.querySelector(".dir-check");
    if (check) check.remove();
  });
  el.classList.add("selected");
  const checkSpan = document.createElement("span");
  checkSpan.className = "dir-check";
  checkSpan.textContent = "✓";
  el.appendChild(checkSpan);

  const entries = state._dirEntries || [];
  const fpkEntry = entries.find((e) => e.path === path);
  state.selectedFile = fpkEntry || { path, name: path.split("/").pop() };
  document.getElementById("btnNext1").disabled = false;
}

async function scanCurrentDir() {
  const dir = state.currentDir;
  const fileList = document.getElementById("fileList");
  const dirBrowser = document.getElementById("dirBrowser");
  dirBrowser.classList.add("hidden");
  fileList.classList.remove("hidden");

  fileList.innerHTML = `
    <div class="empty-state">
      <div class="loading-spinner large"></div>
      <p>${t("scanning")}</p>
    </div>`;

  try {
    const result = await api("list-files", { directory: dir });
    state._files = result.files || [];
    renderFileList(state._files);
  } catch (error) {
    fileList.innerHTML = `
      <div class="empty-state">
        <div class="icon">❌</div>
        <p>${escapeHtml(error.message)}</p>
      </div>`;
  }
}

async function goToStep2() {
  if (!state.selectedFile) return;
  showStep(2);

  const downloadStatusText = document.getElementById("downloadStatusText");
  const downloadProgressBar = document.getElementById("downloadProgressBar");
  const installInfoSection = document.getElementById("installInfoSection");
  const btnInstall = document.getElementById("btnInstall");

  downloadStatusText.textContent = t("parsingPackage");
  downloadProgressBar.style.width = "0%";
  downloadProgressBar.classList.remove("success", "error");
  installInfoSection.classList.add("hidden");
  btnInstall.disabled = true;

  try {
    const result = await acDownloadTask({
      packageSourceType: "file",
      path: state.selectedFile.path,
    });
    state.downloadTaskId = extractTaskId(result);
    const info = acData(result);
    state.appName = String(
      (info && (info.appName || info.app_name)) ||
        result.appName ||
        result.app_name ||
        "",
    ).trim();
    state.version = String(
      (info && (info.version || info.app_version)) ||
        result.version ||
        result.app_version ||
        "",
    ).trim();
    // 用下载登记时系统返回的真实 packageType，
    const pkgType = String(
      (info && (info.packageType || info.package_type)) ||
        result.packageType ||
        result.package_type ||
        "",
    ).trim();
    if (pkgType) state.packageType = pkgType;
    if (state.appName) {
      const downloadStatusText = document.getElementById("downloadStatusText");
      downloadStatusText.textContent = `${t("parsingPackage")} ${state.appName}`;
    }
    pollDownloadStatus();
  } catch (error) {
    downloadStatusText.textContent = error.message;
    downloadProgressBar.classList.add("error");
    downloadProgressBar.style.width = "100%";
    showToast(error.message, true);
  }
}

function pollDownloadStatus() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }

  let pollCount = 0;
  const maxPolls = 120;

  const checkStatus = async () => {
    try {
      const result = await acDownloadStatus(state.downloadTaskId);
      const data = acData(result);
      const info = data && typeof data === "object" ? data : result;
      const progress = Number(info && info.progress) || 0;
      const downloadProgressBar = document.getElementById(
        "downloadProgressBar",
      );
      const downloadStatusText = document.getElementById("downloadStatusText");

      if (info.appName || info.app_name) {
        state.appName = String(info.appName || info.app_name).trim();
      }
      if (info.version || info.app_version) {
        state.version = String(info.version || info.app_version).trim();
      }
      if (info.packageType || info.package_type) {
        state.packageType = String(
          info.packageType || info.package_type,
        ).trim();
      }
      if (info.installType || info.install_type) {
        state.installType = String(
          info.installType || info.install_type,
        ).trim();
      }

      downloadProgressBar.style.width = `${progress}%`;
      downloadStatusText.textContent = t("parseProgress", { progress });

      // 已安装/可更新检测：只读 app/installed，按名字匹配即视为已安装
      if (state.appName) {
        try {
          const det = await detectInstalled(state.appName);
          const existing = det.installed ? det.info : null;
          state.installed = !!existing;
          state.installedInfo = existing
            ? {
                name: String(existing.name || state.appName),
                version: String(existing.version || ""),
                volumeID: String(existing.volumeID || ""),
              }
            : null;
          const action = resolveInstallAction(
            state.installedInfo?.version,
            state.version,
          );
          state.installAction = action;
          state.canUpdate = action === "update";
          state.canOverwrite = action === "overwrite";
          state.isUpdate = action === "update";
        } catch (_e) {
          state.installed = false;
          state.installedInfo = null;
          state.canUpdate = false;
          state.canOverwrite = false;
          state.installAction = "install";
          state.isUpdate = false;
        }
      }

      const status = normalizeTaskStatus(
        info.status || info.downloadStatus || result.status,
      );

      if (status.done) {
        clearInterval(state.polling);
        state.polling = null;

        if (status.value === "success") {
          downloadProgressBar.classList.add("success");
          downloadProgressBar.style.width = "100%";
          downloadStatusText.textContent = t("parseProgress", {
            progress: 100,
          });

          if (state.installedInfo) {
            if (state.installedInfo.volumeID) {
              state.volumeID = Number(state.installedInfo.volumeID) || 1;
            }
            if (state.canUpdate) {
              downloadStatusText.textContent = `${t("updateAvailable")} (${state.installedInfo.version} → ${state.version})`;
            } else if (state.canOverwrite) {
              downloadStatusText.textContent = `${t("overwriteAvailable")} (${state.installedInfo.version} → ${state.version})`;
            }
          }
          // 更新/覆盖也走 loadInstallInfo 展示包信息，但安装向导会被跳过
          loadInstallInfo();
        } else {
          downloadProgressBar.classList.add("error");
          downloadStatusText.textContent = status.value;
          showToast(`${t("installFailed")}: ${status.value}`, true);
        }
        return;
      }

      pollCount++;
      if (pollCount >= maxPolls) {
        clearInterval(state.polling);
        state.polling = null;
        downloadStatusText.textContent = t("errorUnknown");
        downloadProgressBar.classList.add("error");
      }
    } catch (error) {
      pollCount++;
      if (pollCount >= 3) {
        clearInterval(state.polling);
        state.polling = null;
        document.getElementById("downloadStatusText").textContent =
          error.message;
        document.getElementById("downloadProgressBar").classList.add("error");
        showToast(error.message, true);
      }
    }
  };

  checkStatus();
  state.polling = setInterval(checkStatus, 1500);
}

async function loadInstallInfo() {
  const installInfoSection = document.getElementById("installInfoSection");
  const installInfo = document.getElementById("installInfo");
  const btnInstall = document.getElementById("btnInstall");

  const maxRetries = 5;
  let lastError = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      // 已安装/可更新检测：只读 app/installed，按名字匹配即视为已安装
      let installed = false;
      let canUpdate = false;
      let canOverwrite = false;
      let installedInfo = {};
      try {
        const det = await detectInstalled(state.appName);
        if (det.installed) {
          installed = true;
          installedInfo = {
            name: String(det.info.name || state.appName),
            // 已安装版本：app/installed 的 version 字段
            version: String(det.info.version || ""),
            volumeID: String(det.info.volumeID || ""),
          };
          const action = resolveInstallAction(
            installedInfo.version,
            state.version,
          );
          canUpdate = action === "update";
          canOverwrite = action === "overwrite";
          state.isUpdate = action === "update";
        }
      } catch (_e) {}

      state.installed = installed;
      state.installedInfo = installed ? installedInfo : null;
      state.canUpdate = canUpdate;
      state.canOverwrite = canOverwrite;
      state.installAction = canUpdate
        ? "update"
        : canOverwrite
          ? "overwrite"
          : "install";

      // 本地 fpk 安装，packageType 用下载登记返回的真实值（root 应用非 file）。
      // 用 acThrowIfError 把 10100 等业务错误码抛成异常，走下方 retry 重试。
      const packageType = state.packageType || "file";
      const result = acThrowIfError(
        await acInstallInfo(
          state.appName,
          state.version,
          packageType,
          state.isUpdate,
        ),
      );
      state.installInfo = result;

      const info = result;
      const data = info.data || info;
      const wizardInfo = data.wizardInfo || data;
      const rows = [];

      const displayName =
        wizardInfo.name ||
        data.name ||
        data.display_name ||
        wizardInfo.appName ||
        data.appName ||
        data.app_name ||
        "";
      const appVersion = wizardInfo.version || data.version || "";
      const maintainer = wizardInfo.maintainer || data.maintainer || "";
      const desc =
        wizardInfo.desc ||
        data.desc ||
        wizardInfo.description ||
        data.description ||
        "";
      const installType =
        wizardInfo.installType || data.installType || data.install_type || "";
      const volumeID =
        wizardInfo.installedVolumeID ||
        data.volumeID ||
        data.volume_id ||
        data.installVolumeID ||
        "";

      state.installType = installType;

      if (displayName) {
        rows.push(infoRow(t("appName"), displayName));
      }
      if (appVersion) {
        rows.push(infoRow(t("appVersion"), appVersion));
      }

      if (maintainer) {
        rows.push(infoRow(t("appMaintainer"), maintainer));
      }
      if (desc) {
        rows.push(infoRowHtml(t("appDesc"), desc));
      }
      if (data.source) {
        rows.push(infoRow(t("appSource"), data.source));
      }
      if (installType) {
        rows.push(infoRow(t("appInstallType"), installType));
      }

      installInfo.innerHTML = rows.join("");

      const updateBanner = document.getElementById("updateBanner");
      if (updateBanner) {
        if (state.canUpdate) {
          updateBanner.className = "update-banner update-available";
          updateBanner.innerHTML = `
            <div class="update-confirm">
              <div class="update-confirm-title">${t("updateConfirmTitle")}</div>
              <div class="update-confirm-desc">${t("updateConfirmDesc", { installedVersion: escapeHtml(state.installedInfo?.version || ""), newVersion: escapeHtml(state.version || "") })}</div>
            </div>`;
          updateBanner.classList.remove("hidden");
        } else if (state.canOverwrite) {
          updateBanner.className = "update-banner overwrite-available";
          updateBanner.innerHTML = `
            <div class="update-confirm">
              <div class="update-confirm-title">${t("overwriteConfirmTitle")}</div>
              <div class="update-confirm-desc">${t("overwriteConfirmDesc", { installedVersion: escapeHtml(state.installedInfo?.version || ""), newVersion: escapeHtml(state.version || "") })}</div>
            </div>`;
          updateBanner.classList.remove("hidden");
        } else {
          updateBanner.classList.add("hidden");
        }
      }

      const wizardSection = document.getElementById("wizardSection");
      const wizardItems =
        wizardInfo.wizardContent ||
        wizardInfo.steps ||
        data.wizard ||
        data.wizardData ||
        [];

      // 更新/覆盖场景只展示包信息，跳过安装向导与安装卷选择
      const isReinstall = state.canUpdate || state.canOverwrite;
      if (isReinstall) {
        state._wizardInfo = null;
        if (wizardSection) wizardSection.classList.add("hidden");
      } else {
        const hasWizard =
          wizardInfo.hasWizard ||
          (Array.isArray(wizardItems) && wizardItems.length > 0);
        if (hasWizard && Array.isArray(wizardItems) && wizardItems.length > 0) {
          state._wizardInfo = wizardInfo;
          renderWizard(wizardItems, wizardSection);
          wizardSection.classList.remove("hidden");
        } else {
          state._wizardInfo = null;
          wizardSection.classList.add("hidden");
        }
      }

      const volumeSection = document.getElementById("volumeSection");
      if (isReinstall) {
        // 更新/覆盖沿用安装信息里的卷，不展示卷选择
        if (volumeSection) volumeSection.classList.add("hidden");
        state.volumeID = Number(volumeID) || 1;
      } else {
        await loadVolumes(volumeID || 0, installType);
      }

      installInfoSection.classList.remove("hidden");
      if (state.canUpdate) {
        state._updateConfirmed = true;
        btnInstall.disabled = false;
        btnInstall.textContent = t("updateApp");
        btnInstall.dataset.i18n = "updateApp";
      } else if (state.canOverwrite) {
        state._updateConfirmed = true;
        btnInstall.disabled = false;
        btnInstall.textContent = t("overwriteApp");
        btnInstall.dataset.i18n = "overwriteApp";
      } else {
        btnInstall.disabled = false;
        btnInstall.textContent = t("install");
        btnInstall.dataset.i18n = "install";
      }

      return;
    } catch (error) {
      lastError = error;
      const msg = error.message || "";
      if (msg.includes("10100") || msg.includes("not ready")) {
        if (attempt < maxRetries - 1) {
          await new Promise((r) => setTimeout(r, 2000));
          continue;
        }
      }
      break;
    }
  }

  installInfo.innerHTML = `<div class="info-row"><span class="info-value error">${escapeHtml(lastError ? lastError.message : t("errorUnknown"))}</span></div>`;
  installInfoSection.classList.remove("hidden");
  btnInstall.disabled = true;
}

async function loadVolumes(defaultVolumeID, installType) {
  const volumeSection = document.getElementById("volumeSection");
  if (!volumeSection) return;

  const isRoot = (installType || "").toLowerCase() === "root";
  if (isRoot) {
    state.volumeID = 1;
    volumeSection.classList.add("hidden");
    return;
  }

  // 默认安装卷优先取安装信息中的 volumeID；未提供时回退到 1。
  // 注意：不调用 app-center 的 common/remember-volume/config（该端点在当前 fnOS 版本不存在，会 404）。
  let sysDefaultVolume = defaultVolumeID || 1;

  try {
    const result = await api("volumes");
    const volumes = result.volumes || [];
    if (!volumes.length) {
      state.volumeID = sysDefaultVolume || 1;
      volumeSection.classList.add("hidden");
      return;
    }
    const select = document.getElementById("volumeSelect");
    if (select) {
      select.innerHTML = volumes
        .map((vol) => {
          const free = vol.size - vol.used;
          const selected = vol.id == sysDefaultVolume ? " selected" : "";
          return `<option value="${vol.id}"${selected}>${escapeHtml(vol.name)} (${formatSize(free)} ${t("volumeFree")})</option>`;
        })
        .join("");
      state.volumeID = parseInt(select.value) || sysDefaultVolume || 1;
      select.disabled = volumes.length === 1;
    }
    volumeSection.classList.remove("hidden");
  } catch (_error) {
    state.volumeID = sysDefaultVolume || 1;
    if (volumeSection) volumeSection.classList.add("hidden");
  }
}

function infoRow(label, value) {
  return `
    <div class="info-row">
      <span class="info-label">${escapeHtml(label)}</span>
      <span class="info-value">${escapeHtml(String(value ?? ""))}</span>
    </div>`;
}

// 描述行：以 HTML 展示（来自安装包自身，受信内容），支持富文本/换行。
function infoRowHtml(label, value) {
  return `
    <div class="info-row">
      <span class="info-label">${escapeHtml(label)}</span>
      <span class="info-value desc-html">${String(value ?? "")}</span>
    </div>`;
}

function renderWizard(items, container) {
  let html = `<div class="wizard-title">${t("wizardConfig")}</div>`;

  const flatItems = [];
  for (const item of items) {
    if (item.items && Array.isArray(item.items)) {
      if (item.stepTitle) {
        html += `<div class="wizard-tips step-title">${escapeHtml(item.stepTitle)}</div>`;
      }
      flatItems.push(...item.items);
    } else {
      flatItems.push(item);
    }
  }

  flatItems.forEach((item, index) => {
    const key = item.field || item.key || item.name || `wizard_${index}`;
    const value = item.initValue ?? item.defaultValue ?? item.value ?? "";
    const required = Boolean(
      item.required || (item.rules || []).some((rule) => rule.required),
    );
    const pattern =
      (item.rules || []).find((rule) => rule.pattern)?.pattern ||
      item.pattern ||
      "";
    const minLength =
      (item.rules || []).find((rule) => rule.min)?.min || item.min || "";
    const message =
      (item.rules || []).find((rule) => rule.message)?.message ||
      item.message ||
      "";

    if (item.type === "tips" && !item.field && !item.key && !item.name) {
      html += `<div class="wizard-tips">${escapeHtml(item.helpText || item.tips || item.label || item.title || "")}</div>`;
    } else if (item.type === "radio" && item.options) {
      html += `
        <div class="wizard-item">
          ${item.helpText ? `<div class="wizard-tips">${escapeHtml(item.helpText)}</div>` : ""}
          <label>${escapeHtml(item.label || item.title || `${t("wizardConfig")} ${index + 1}`)}</label>
          <select data-wizard-key="${escapeHtml(key)}"
                  ${required ? "required" : ""}>
            ${item.options
              .map((opt) => {
                const optValue =
                  typeof opt === "string" ? opt : opt.value || opt.name || "";
                const optLabel =
                  typeof opt === "string"
                    ? opt
                    : opt.label || opt.name || opt.value || "";
                const selected = optValue === value ? " selected" : "";
                return `<option value="${escapeHtml(optValue)}"${selected}>${escapeHtml(optLabel)}</option>`;
              })
              .join("")}
          </select>
        </div>`;
    } else if (item.type === "select" && item.options) {
      html += `
        <div class="wizard-item">
          ${item.helpText ? `<div class="wizard-tips">${escapeHtml(item.helpText)}</div>` : ""}
          <label>${escapeHtml(item.label || item.title || `${t("wizardConfig")} ${index + 1}`)}</label>
          <select data-wizard-key="${escapeHtml(key)}"
                  ${required ? "required" : ""}>
            ${item.options
              .map((opt) => {
                const optValue =
                  typeof opt === "string" ? opt : opt.value || opt.name || "";
                const optLabel =
                  typeof opt === "string"
                    ? opt
                    : opt.label || opt.name || opt.value || "";
                const selected = optValue === value ? " selected" : "";
                return `<option value="${escapeHtml(optValue)}"${selected}>${escapeHtml(optLabel)}</option>`;
              })
              .join("")}
          </select>
        </div>`;
    } else if (item.type === "checkbox" || item.type === "switch") {
      const checked =
        value === true ||
        value === "true" ||
        value === "1" ||
        item.checked === true
          ? " checked"
          : "";
      html += `
        <label class="wizard-check">
          <input type="checkbox"
                 data-wizard-key="${escapeHtml(key)}"
                 data-wizard-type="checkbox"${checked} />
          <span>${escapeHtml(item.label || item.title || `${t("wizardConfig")} ${index + 1}`)}</span>
        </label>`;
    } else if (item.type === "textarea") {
      html += `
        <div class="wizard-item">
          ${item.helpText ? `<div class="wizard-tips">${escapeHtml(item.helpText)}</div>` : ""}
          <label>${escapeHtml(item.label || item.title || `${t("wizardConfig")} ${index + 1}`)}</label>
          <textarea data-wizard-key="${escapeHtml(key)}"
                    placeholder="${escapeHtml(item.placeholder || "")}"
                    ${pattern ? `pattern="${escapeHtml(pattern)}"` : ""}
                    ${message ? `title="${escapeHtml(message)}"` : ""}
                    ${required ? "required" : ""}>${escapeHtml(value)}</textarea>
        </div>`;
    } else {
      html += `
        <div class="wizard-item">
          ${item.helpText ? `<div class="wizard-tips">${escapeHtml(item.helpText)}</div>` : ""}
          <label>${escapeHtml(item.label || item.title || `${t("wizardConfig")} ${index + 1}`)}</label>
          <input type="${item.type === "password" ? "password" : item.type === "number" ? "number" : "text"}"
                 data-wizard-key="${escapeHtml(key)}"
                 value="${escapeHtml(value)}"
                 placeholder="${escapeHtml(item.placeholder || "")}"
                 ${pattern ? `pattern="${escapeHtml(pattern)}"` : ""}
                 ${minLength ? `minlength="${escapeHtml(minLength)}"` : ""}
                 ${message ? `title="${escapeHtml(message)}"` : ""}
                 ${required ? "required" : ""} />
        </div>`;
    }
  });
  container.innerHTML = html;
}

function collectWizardData() {
  const data = {};
  document.querySelectorAll("[data-wizard-key]").forEach((el) => {
    data[el.dataset.wizardKey] =
      el.dataset.wizardType === "checkbox" ? el.checked : el.value;
  });
  return data;
}

function goToStep1() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }
  state.appName = "";
  state.version = "";
  state.installType = "";
  state.downloadTaskId = "";
  state.installTaskId = "";
  state.installInfo = null;
  state.wizardData = null;
  state._wizardInfo = null;
  state.isUpdate = false;
  state.installedInfo = null;
  state.canUpdate = false;
  state.canOverwrite = false;
  state.installAction = "install";
  state._updateConfirmed = false;
  const updateBanner = document.getElementById("updateBanner");
  if (updateBanner) updateBanner.classList.add("hidden");
  showStep(1);
  loadFiles();
}

async function goToStep3() {
  if ((state.isUpdate || state.canOverwrite) && !state._updateConfirmed) {
    return;
  }

  if (!state.isUpdate && !state.canOverwrite) {
    const invalidWizardField = document.querySelector(
      "[data-wizard-key]:invalid",
    );
    if (invalidWizardField) {
      invalidWizardField.reportValidity();
      return;
    }
  }

  if (!state.isUpdate && !state.canOverwrite) {
    state.wizardData = collectWizardData();
    const volumeSelect = document.getElementById("volumeSelect");
    if (volumeSelect) {
      state.volumeID = parseInt(volumeSelect.value) || 1;
    }
  }
  showStep(3);

  const installStatusText = document.getElementById("installStatusText");
  const installProgressBar = document.getElementById("installProgressBar");

  installStatusText.textContent = state.isUpdate
    ? t("updatingApp")
    : state.canOverwrite
      ? t("overwritingApp")
      : t("installingApp");
  installProgressBar.style.width = "0%";
  installProgressBar.classList.remove("success", "error");

  try {
    const language = state.language;
    // 系统空间(root)应用安装到系统分区，installVolumeID 必须为 0（对齐 fnOS 官方前端）。
    const isRoot = (state.installType || "").toLowerCase() === "root";
    const installVolume = isRoot ? 0 : state.volumeID;
    const commonSysParams = {
      installVolumeID: installVolume,
      dataVolumeID: state.volumeID,
    };

    const makeCustom = () => {
      if (state.wizardData && Object.keys(state.wizardData).length > 0) {
        return Object.entries(state.wizardData).map(([key, value]) => ({
          key,
          value: String(value ?? ""),
        }));
      }
      return undefined;
    };

    // 本地 fpk 安装，packageType 用下载登记返回的真实值（非固定 file）
    const installPayload = {
      appName: state.appName,
      version: state.version,
      packageType: state.packageType || "file",
      volumeID: state.volumeID,
      installVolumeID: installVolume,
      dataVolumeID: state.volumeID,
      language,
      immediateStart: true,
      systemParameters: {
        ...commonSysParams,
        INSTALL_VOLUME_ID: String(installVolume),
      },
    };
    const custom = makeCustom();
    if (custom) {
      installPayload.wizardData = state.wizardData;
      installPayload.customParameters = custom;
    }

    const updatePayload = {
      appName: state.appName,
      packageType: state.packageType || "file",
      version: state.version,
      updateVersion: state.version,
      language,
      immediateStart: true,
      systemParameters: commonSysParams,
    };
    if (custom) updatePayload.customParameters = custom;

    // 统一提交安装/更新任务，双向容错：
    // 1) isUpdate=true：优先 update/task，任何业务错误回退 install/task(upgrade)。
    // 2) isUpdate=false（app/installed 未匹配到等）：先 install/task；
    //    若报"已安装"(10236) 说明应用已存在，只要有待安装版本就回退 update/task 尝试更新，
    //    避免把"安装新版本"误判为"无需重复安装"。
    const doInstall = async (upgrade) =>
      acThrowIfError(await acInstallTask({ ...installPayload, upgrade }));
    const doUpdate = async () =>
      acThrowIfError(await acUpdateTask(updatePayload));

    let result = null;
    try {
      if (state.isUpdate) {
        try {
          result = await doUpdate();
        } catch (_updateErr) {
          result = await doInstall(true);
        }
      } else {
        try {
          result = await doInstall(false);
        } catch (installErr) {
          const code = acCode(installErr);
          if (
            code === 10236 ||
            /already installed|已安装/.test(installErr.message || "")
          ) {
            result = await doUpdate();
          } else {
            throw installErr;
          }
        }
      }
    } catch (error) {
      const code = acCode(error);
      const msg = error.message || "";
      // 只有 update/task 与 install/task(upgrade) 都报"已安装"，才确为同版本无需重复安装。
      if (code === 10236 || /already installed|已安装/.test(msg)) {
        installProgressBar.classList.add("success");
        installProgressBar.style.width = "100%";
        installStatusText.textContent = t("alreadyInstalled");
        showStep(4);
        document.getElementById("resultSuccess").classList.remove("hidden");
        document.getElementById("resultError").classList.add("hidden");
        document.getElementById("resultSuccessDesc").textContent =
          t("alreadyInstalled");
        return;
      }
      installStatusText.textContent = msg;
      installProgressBar.classList.add("error");
      installProgressBar.style.width = "100%";
      showToast(msg, true);
      return;
    }

    state.installTaskId = extractTaskId(result);
    pollInstallStatus();
  } catch (outerError) {
    installStatusText.textContent = outerError.message || String(outerError);
    installProgressBar.classList.add("error");
    installProgressBar.style.width = "100%";
    showToast(outerError.message || String(outerError), true);
  }
}

function pollInstallStatus() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }

  let pollCount = 0;
  const maxPolls = 180;

  const checkStatus = async () => {
    try {
      const queryStatus = async (useUpdate) => {
        if (useUpdate) return acUpdateStatus(state.installTaskId);
        return acTaskStatus(state.installTaskId);
      };

      let result = await queryStatus(state.isUpdate);
      let data = acData(result);
      let st = normalizeTaskStatus(
        data.status || data.installStatus || result.status,
      );

      // 接口返回 notfound（状态 5）：尝试另一接口
      if (st.value === "notfound") {
        const alt = await queryStatus(!state.isUpdate);
        const altData = acData(alt);
        const altSt = normalizeTaskStatus(
          altData.status || altData.installStatus || alt.status,
        );
        if (altSt.value !== "notfound") {
          result = alt;
          data = altData;
          st = altSt;
        }
      }

      const progress = Number(data && data.progress) || 0;
      const installProgressBar = document.getElementById("installProgressBar");
      const installStatusText = document.getElementById("installStatusText");

      installProgressBar.style.width = `${progress}%`;
      installStatusText.textContent = t("installProgress", { progress });

      if (st.done) {
        clearInterval(state.polling);
        state.polling = null;

        if (st.value === "success") {
          clearInstalledAppsCache();
          installProgressBar.classList.add("success");
          installProgressBar.style.width = "100%";
          installStatusText.textContent = state.canOverwrite
            ? t("overwriteSuccess")
            : state.isUpdate
              ? t("updateSuccess")
              : t("installSuccess");
          showStep(4);
          document.getElementById("resultSuccess").classList.remove("hidden");
          document.getElementById("resultError").classList.add("hidden");
          document.getElementById("resultSuccessDesc").textContent =
            state.appName;
        } else {
          installProgressBar.classList.add("error");
          installProgressBar.style.width = "100%";
          const message = acMessage(result) || st.value;
          installStatusText.textContent = state.canOverwrite
            ? t("overwriteFailed")
            : state.isUpdate
              ? t("updateFailed")
              : t("installFailed");
          showStep(4);
          document.getElementById("resultSuccess").classList.add("hidden");
          document.getElementById("resultError").classList.remove("hidden");
          document.getElementById("resultErrorDesc").textContent = message;
        }
        return;
      }

      pollCount++;
      if (pollCount >= maxPolls) {
        clearInterval(state.polling);
        state.polling = null;
        installStatusText.textContent = t("errorUnknown");
        installProgressBar.classList.add("error");
      }
    } catch (error) {
      pollCount++;
      if (pollCount >= 3) {
        clearInterval(state.polling);
        state.polling = null;
        const installProgressBar =
          document.getElementById("installProgressBar");
        const installStatusText = document.getElementById("installStatusText");
        installStatusText.textContent = error.message;
        installProgressBar.classList.add("error");
        installProgressBar.style.width = "100%";
        showStep(4);
        document.getElementById("resultSuccess").classList.add("hidden");
        document.getElementById("resultError").classList.remove("hidden");
        document.getElementById("resultErrorDesc").textContent = error.message;
      }
    }
  };

  checkStatus();
  state.polling = setInterval(checkStatus, 2000);
}

function resetWizard() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }
  state.selectedFile = null;
  state.downloadTaskId = "";
  state.installTaskId = "";
  state.appName = "";
  state.version = "";
  state.volumeID = 1;
  state.installInfo = null;
  state.wizardData = {};
  state._wizardInfo = null;
  state.isUpdate = false;
  state.installedInfo = null;
  state.canUpdate = false;
  state.canOverwrite = false;
  state.installAction = "install";
  state._updateConfirmed = false;
  state._files = [];
  state._dirEntries = [];
  state.currentDir = "";
  const updateBanner = document.getElementById("updateBanner");
  if (updateBanner) updateBanner.classList.add("hidden");
  document.getElementById("btnNext1").disabled = true;
  document.getElementById("dirBrowser").classList.add("hidden");
  document.getElementById("fileList").classList.remove("hidden");
  showStep(1);
  loadFiles();
}

const channel = new BroadcastChannel("fn-installer");
let isPrimaryWindow = true;
let pendingFilePath = null;

channel.onmessage = function (e) {
  const msg = e.data;
  if (msg && msg.type === "ping") {
    channel.postMessage({ type: "pong" });
  }
  if (msg && msg.type === "open-file" && msg.path) {
    openFileFromPath(msg.path);
    channel.postMessage({ type: "pong" });
  }
  if (msg && msg.type === "pong") {
    isPrimaryWindow = false;
  }
};

function claimPrimary() {
  isPrimaryWindow = true;
}

async function openFileFromPath(filePath) {
  if (!filePath || !filePath.toLowerCase().endsWith(".fpk")) {
    showToast(t("noFiles"), true);
    return;
  }

  state.selectedFile = {
    name: filePath.split("/").pop(),
    path: filePath,
    appId: "",
    version: "",
    size: 0,
  };

  try {
    const result = await api("parse-fpk", { filePath });
    if (result.manifest) {
      state.selectedFile.appId = result.manifest.appname || "";
      state.selectedFile.version = result.manifest.version || "";
      state.selectedFile.name = result.manifest.appname
        ? `${result.manifest.appname}-${result.manifest.version || "unknown"}.fpk`
        : state.selectedFile.name;
    }
  } catch (_error) {}

  document.getElementById("btnNext1").disabled = false;
  goToStep2();
}

function openAbout() {
  document.getElementById("aboutModal").classList.remove("hidden");
}

function closeAbout() {
  document.getElementById("aboutModal").classList.add("hidden");
}

document.addEventListener("click", function (e) {
  if (e.target.id === "aboutModal") {
    closeAbout();
  }
});

document.addEventListener("DOMContentLoaded", async () => {
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

  claimPrimary();

  const customPath = document.getElementById("customPath");
  if (customPath) {
    customPath.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        browsePath();
      }
    });
  }

  const urlParams = new URLSearchParams(window.location.search);
  const pathParam = urlParams.get("path");
  if (pathParam) {
    const decodedPath = safeDecode(pathParam);
    channel.postMessage({ type: "open-file", path: decodedPath });
    pendingFilePath = decodedPath;
    setTimeout(function () {
      if (isPrimaryWindow && pendingFilePath) {
        openFileFromPath(pendingFilePath);
        pendingFilePath = null;
      } else if (!isPrimaryWindow) {
        document.body.innerHTML =
          '<div class="fullscreen-message">' +
          t("installing") +
          ": " +
          escapeHtml(decodedPath.split("/").pop()) +
          "</div>";
        setTimeout(function () {
          try {
            window.close();
          } catch (e) {}
        }, 1500);
      }
    }, 500);
  } else {
    loadFiles();
  }
});

// 事件绑定（ES Module 作用域内函数不暴露到 window，故用 addEventListener 代替内联 onclick）
document.getElementById("btnAbout").addEventListener("click", openAbout);
document.getElementById("btnScanAll").addEventListener("click", loadFiles);
document.getElementById("btnBrowse").addEventListener("click", browsePath);
document.getElementById("btnNext1").addEventListener("click", goToStep2);
document.getElementById("btnBack2").addEventListener("click", goToStep1);
document.getElementById("btnInstall").addEventListener("click", goToStep3);
document.getElementById("btnReset").addEventListener("click", resetWizard);
document.getElementById("btnCloseAbout").addEventListener("click", closeAbout);
document.getElementById("volumeSelect").addEventListener("change", (e) => {
  state.volumeID = parseInt(e.target.value, 10) || 1;
});

// 事件委托：动态生成的列表项/面包屑等通过 data-action 分发（ES Module 作用域内函数不暴露到 window，不能使用内联 onclick）
document.addEventListener("click", (event) => {
  const actionEl = event.target.closest("[data-action]");
  if (!actionEl) return;
  const action = actionEl.dataset.action;
  const path = actionEl.dataset.path;
  if (action === "select") {
    selectFile(actionEl);
  } else if (action === "browse") {
    browseDir(path);
  } else if (action === "select-fpk") {
    selectFpkFromBrowser(actionEl, path);
  } else if (action === "scan-current") {
    scanCurrentDir();
  }
});
