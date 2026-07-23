const API_ENDPOINT = location.pathname.includes("/app/fn-installer")
  ? "/app/fn-installer/api"
  : "./api";

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

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
}

function themeMedia() {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;
}

function prefersDarkTheme() {
  return Boolean(themeMedia()?.matches);
}

function normalizeTheme(value) {
  const theme = safeDecode(value).toLowerCase();
  if (theme.includes("dark") || theme === "night") return "dark";
  if (theme.includes("light") || theme === "day") return "light";
  if (theme === "10") return "light";
  if (theme === "20") return "dark";
  if (theme === "system" || theme === "auto" || theme === "os") {
    return prefersDarkTheme() ? "dark" : "light";
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
  return prefersDarkTheme() ? "dark" : "light";
}

function applyTheme() {
  const theme = currentTheme();
  document.documentElement.dataset.theme = theme;
  document.body.dataset.theme = theme;
}

function applyPreferences() {
  const nextLanguage = currentLanguage();
  state.language = nextLanguage;
  state.theme = currentTheme();
  document.documentElement.lang = nextLanguage;
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

function authToken() {
  return safeDecode(
    cookieValue("fnos-token") ||
      cookieValue("trim_token") ||
      cookieValue("token"),
  );
}

async function api(action, data = {}) {
  const token = authToken();
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `trim ${token}`;
  }
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers,
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
         data-path="${escapeHtml(file.path)}" onclick="selectFile(this)">
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
    if (
      error.message.includes("authorization token not found") ||
      error.message.includes("token not found")
    ) {
      showToast(t("errorTokenNotFound"), true);
    }
  }
}

async function browsePath() {
  const customPath = document.getElementById("customPath").value.trim();
  const dir = customPath || "/vol1";
  await browseDir(dir);
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
    if (
      error.message.includes("authorization token not found") ||
      error.message.includes("token not found")
    ) {
      showToast(t("errorTokenNotFound"), true);
    }
  }
}

function renderBreadcrumb(dir) {
  const breadcrumb = document.getElementById("dirBreadcrumb");
  const parts = dir.split("/").filter(Boolean);
  let html = `<span class="breadcrumb-item" onclick="browseDir('/')">/</span>`;
  let path = "";
  parts.forEach((part, i) => {
    path += "/" + part;
    const isLast = i === parts.length - 1;
    html += `<span class="breadcrumb-sep">/</span>`;
    if (isLast) {
      html += `<span class="breadcrumb-item active">${escapeHtml(part)}</span>`;
    } else {
      html += `<span class="breadcrumb-item" onclick="browseDir('${escapeHtml(path)}')">${escapeHtml(part)}</span>`;
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
      <div class="dir-entry dir-parent" onclick="browseDir('${escapeHtml(parentPath)}')">
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
      <div class="dir-entry" onclick="browseDir('${escapeHtml(entry.path)}')">
        <span class="dir-icon">📁</span>
        <span class="dir-name">${escapeHtml(entry.name)}</span>
      </div>`;
  });

  files.forEach((entry) => {
    const isSelected = state.selectedFile?.path === entry.path;
    html += `
      <div class="dir-entry fpk-entry${isSelected ? " selected" : ""}" onclick="selectFpkFromBrowser(this, '${escapeHtml(entry.path)}')">
        <span class="dir-icon">📦</span>
        <span class="dir-name">${escapeHtml(entry.name)}</span>
        ${entry.version ? `<span class="dir-meta">${escapeHtml(entry.version)} · ${formatSize(entry.size)}</span>` : ""}
        ${isSelected ? '<span class="dir-check">✓</span>' : ""}
      </div>`;
  });

  if (files.length > 0) {
    html += `
      <div class="dir-actions">
        <button class="btn btn-primary btn-sm" onclick="scanCurrentDir()" data-i18n="selectFromDir">${t("selectFromDir")}</button>
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
    const result = await api("parse-task", {
      filePath: state.selectedFile.path,
    });
    state.downloadTaskId = result.taskId;
    state.appName = result.appName || "";
    state.version = result.version || "";
    if (state.appName) {
      const downloadStatusText = document.getElementById("downloadStatusText");
      downloadStatusText.textContent = `${t("parsingPackage")} ${state.appName}`;
    }
    pollDownloadStatus();
  } catch (error) {
    downloadStatusText.textContent = error.message;
    downloadProgressBar.classList.add("error");
    downloadProgressBar.style.width = "100%";
    if (
      error.message.includes("authorization token not found") ||
      error.message.includes("token not found")
    ) {
      showToast(t("errorTokenNotFound"), true);
    } else {
      showToast(error.message, true);
    }
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
      const result = await api("parse-status", {
        taskId: state.downloadTaskId,
      });
      const progress = result.progress || 0;
      const downloadProgressBar = document.getElementById(
        "downloadProgressBar",
      );
      const downloadStatusText = document.getElementById("downloadStatusText");

      if (result.appName) {
        state.appName = result.appName;
      }
      if (result.version) {
        state.version = result.version;
      }

      downloadProgressBar.style.width = `${progress}%`;
      downloadStatusText.textContent = t("parseProgress", { progress });

      if (result.installed) {
        state.installedInfo = result.installedInfo || {};
        if (result.canUpdate) {
          state.canUpdate = true;
          state.isUpdate = true;
        } else {
          clearInterval(state.polling);
          state.polling = null;
          downloadProgressBar.classList.add("success");
          downloadProgressBar.style.width = "100%";
          const info = result.installedInfo || {};
          downloadStatusText.textContent = `${info.name || state.appName} ${t("sameVersion")}`;
          showToast(t("sameVersion"), false);
          document.getElementById("btnInstall").disabled = true;
          return;
        }
      }

      if (result.isDone) {
        clearInterval(state.polling);
        state.polling = null;

        if (result.status === "success") {
          downloadProgressBar.classList.add("success");
          downloadProgressBar.style.width = "100%";
          downloadStatusText.textContent = t("parseProgress", {
            progress: 100,
          });

          if (state.isUpdate && state.installedInfo) {
            if (state.installedInfo.volumeID) {
              state.volumeID = state.installedInfo.volumeID;
            }
            downloadStatusText.textContent = `${t("updateAvailable")} (${state.installedInfo.version} → ${state.version})`;
            showUpdateConfirm();
          } else {
            loadInstallInfo();
          }
        } else {
          downloadProgressBar.classList.add("error");
          downloadStatusText.textContent = result.status;
          showToast(`${t("installFailed")}: ${result.status}`, true);
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
      const result = await api("install-info", {
        appName: state.appName,
        version: state.version,
        downloadTaskId: state.downloadTaskId,
      });
      state.installInfo = result.info;

      if (result.installed) {
        state.installedInfo = result.installedInfo || {};
        if (result.canUpdate) {
          state.canUpdate = true;
          state.isUpdate = true;
        }
      }

      const info = result.info;
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

      if (state.isUpdate && state.installedInfo) {
        rows.push(
          infoRow(t("installedVersion"), state.installedInfo.version || ""),
        );
        rows.push(infoRow(t("newVersion"), appVersion));
      }

      if (maintainer) {
        rows.push(infoRow(t("appMaintainer"), maintainer));
      }
      if (desc) {
        rows.push(infoRow(t("appDesc"), desc));
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
        if (state.isUpdate) {
          updateBanner.className = "update-banner update-available";
          updateBanner.innerHTML = `
            <div class="update-confirm">
              <div class="update-confirm-title">${t("updateConfirmTitle")}</div>
              <div class="update-confirm-desc">${t("updateConfirmDesc", { installedVersion: escapeHtml(state.installedInfo?.version || ""), newVersion: escapeHtml(state.version || "") })}</div>
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

      await loadVolumes(volumeID || 0, installType);

      installInfoSection.classList.remove("hidden");
      if (state.isUpdate) {
        state._updateConfirmed = true;
        btnInstall.disabled = false;
        btnInstall.textContent = t("updateApp");
        btnInstall.dataset.i18n = "updateApp";
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
  if (
    lastError &&
    (lastError.message.includes("authorization token not found") ||
      lastError.message.includes("token not found"))
  ) {
    showToast(t("errorTokenNotFound"), true);
  }
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

  let sysDefaultVolume = defaultVolumeID;
  if (!sysDefaultVolume) {
    try {
      const dv = await api("default-volume");
      sysDefaultVolume = dv.volumeID || 1;
    } catch (_e) {
      sysDefaultVolume = 1;
    }
  }

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
  state._updateConfirmed = false;
  const updateBanner = document.getElementById("updateBanner");
  if (updateBanner) updateBanner.classList.add("hidden");
  showStep(1);
  loadFiles();
}

function showUpdateConfirm() {
  const installInfoSection = document.getElementById("installInfoSection");
  const btnInstall = document.getElementById("btnInstall");
  const updateBanner = document.getElementById("updateBanner");

  installInfoSection.classList.remove("hidden");

  if (updateBanner) {
    updateBanner.className = "update-banner update-available";
    updateBanner.innerHTML = `
      <div class="update-confirm">
        <div class="update-confirm-title">${t("updateConfirmTitle")}</div>
        <div class="update-confirm-desc">${t("updateConfirmDesc", { installedVersion: escapeHtml(state.installedInfo?.version || ""), newVersion: escapeHtml(state.version || "") })}</div>
      </div>`;
    updateBanner.classList.remove("hidden");
  }

  state._updateConfirmed = true;
  btnInstall.disabled = false;
  btnInstall.textContent = t("updateApp");
  btnInstall.dataset.i18n = "updateApp";
}

async function goToStep3() {
  if (state.isUpdate && !state._updateConfirmed) {
    return;
  }

  if (!state.isUpdate) {
    const invalidWizardField = document.querySelector(
      "[data-wizard-key]:invalid",
    );
    if (invalidWizardField) {
      invalidWizardField.reportValidity();
      return;
    }
  }

  if (!state.isUpdate) {
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
    : t("installingApp");
  installProgressBar.style.width = "0%";
  installProgressBar.classList.remove("success", "error");

  try {
    const installPayload = {
      appName: state.appName,
      version: state.version,
      volumeID: state.volumeID,
      installVolumeID: state.volumeID,
      dataVolumeID: state.volumeID,
      isUpdate: state.isUpdate,
      systemParameters: {
        installVolumeID: state.volumeID,
        dataVolumeID: state.volumeID,
        INSTALL_VOLUME_ID: String(state.volumeID),
      },
    };
    if (state.wizardData && Object.keys(state.wizardData).length > 0) {
      installPayload.wizardData = state.wizardData;
      installPayload.customParameters = Object.entries(state.wizardData).map(
        ([key, value]) => ({
          key,
          value: String(value ?? ""),
        }),
      );
    }
    const result = await api("install-task", installPayload);
    state.installTaskId = result.taskId;
    pollInstallStatus();
  } catch (error) {
    const msg = error.message || "";
    if (
      msg.includes("10236") ||
      msg.includes("already installed") ||
      msg.includes("已安装")
    ) {
      if (!state.isUpdate) {
        installProgressBar.classList.add("success");
        installProgressBar.style.width = "100%";
        installStatusText.textContent = t("alreadyInstalled");
        showStep(4);
        document.getElementById("resultSuccess").classList.remove("hidden");
        document.getElementById("resultError").classList.add("hidden");
        document.getElementById("resultSuccessDesc").textContent =
          t("alreadyInstalled");
      } else {
        installProgressBar.classList.add("error");
        installProgressBar.style.width = "100%";
        installStatusText.textContent = msg;
        showToast(msg, true);
        showStep(4);
        document.getElementById("resultSuccess").classList.add("hidden");
        document.getElementById("resultError").classList.remove("hidden");
        document.getElementById("resultErrorDesc").textContent = msg;
      }
    } else {
      installStatusText.textContent = msg;
      installProgressBar.classList.add("error");
      installProgressBar.style.width = "100%";
      if (
        msg.includes("authorization token not found") ||
        msg.includes("token not found")
      ) {
        showToast(t("errorTokenNotFound"), true);
      } else {
        showToast(msg, true);
      }
    }
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
      const result = await api("install-status", {
        appName: state.appName,
        taskId: state.installTaskId,
        isUpdate: state.isUpdate,
      });
      const progress = result.progress || 0;
      const installProgressBar = document.getElementById("installProgressBar");
      const installStatusText = document.getElementById("installStatusText");

      installProgressBar.style.width = `${progress}%`;
      installStatusText.textContent = t("installProgress", { progress });

      if (result.isDone) {
        clearInterval(state.polling);
        state.polling = null;

        if (result.status === "success") {
          installProgressBar.classList.add("success");
          installProgressBar.style.width = "100%";
          installStatusText.textContent = state.isUpdate
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
          const message = result.message || result.status;
          installStatusText.textContent = state.isUpdate
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

document.addEventListener("DOMContentLoaded", () => {
  applyPreferences();
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

themeMedia()?.addEventListener?.("change", () => applyPreferences());
window.addEventListener("storage", () => applyPreferences());
