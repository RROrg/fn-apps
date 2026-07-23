const API_ENDPOINT = location.pathname.includes("/app/fn-aptmng")
  ? "/app/fn-aptmng/api"
  : "./api";

const state = {
  activeTab: "installed",
  installed: [],
  upgradable: [],
  searchResults: [],
  sources: [],
  language: "zh-CN",
  theme: "light",
  loading: false,
  confirmCallback: null,
};

const I18N = {
  "zh-CN": {
    appTitle: "APT 管理",
    refresh: "刷新",
    installed: "已安装",
    upgradable: "可升级",
    search: "搜索",
    sources: "源列表",
    actions: "操作",
    about: "关于",
    install: "安装",
    upgrade: "升级",
    remove: "卸载",
    delete: "删除",
    purge: "彻底删除",
    upgradeAll: "全部升级",
    addSource: "添加源",
    updateCache: "更新缓存",
    updateCacheDesc: "刷新 apt 软件源缓存",
    autoremove: "自动清理",
    autoremoveDesc: "移除不再需要的依赖",
    cleanCache: "清理缓存",
    cleanCacheDesc: "清理下载的软件包缓存",
    save: "保存",
    close: "关闭",
    confirm: "确认",
    cancel: "取消",
    loading: "正在加载...",
    searchHint: "输入关键词搜索软件包",
    filterPackages: "过滤包名（支持正则）",
    searchPackages: "搜索包名（支持正则）",
    sourceFile: "文件名",
    sourceLine: "源地址",
    confirm: "确认操作",
    confirmInstall: "确认安装 {name}？",
    confirmUpgrade: "确认升级 {name}？",
    confirmUpgradeAll: "确认升级所有可升级的包？",
    confirmRemove: "确认卸载 {name}？",
    confirmPurge: "确认彻底删除 {name}（含配置文件）？",
    confirmAutoremove: "确认自动清理不再需要的依赖？",
    confirmClean: "确认清理软件包缓存？",
    confirmUpdate: "确认更新软件源缓存？",
    confirmRemoveSource: "确认删除此源？",
    noPackages: "暂无数据",
    noUpgradable: "所有包均为最新",
    noSources: "暂无源",
    add: "添加",
    confirmDeleteSourceFile: "确认删除整个源文件？",
    enterSourceLine: "请输入源地址（如 deb https://... stable main）",
    fixBroken: "修复依赖",
    fixBrokenDesc: "修复损坏的依赖关系",
    confirmFixBroken: "确认修复损坏的依赖关系？",
    sourceType: "类型",
    sourceUrl: "地址",
    sourceSuite: "发行版",
    sourceComponent: "组件",
    sourceEnabled: "状态",
    enabled: "启用",
    disabled: "禁用",
    package: "包名",
    version: "版本",
    arch: "架构",
    description: "描述",
    noDescription: "暂无描述",
    newVersion: "新版本",
    oldVersion: "旧版本",
    section: "分类",
    maintainer: "维护者",
    depends: "依赖",
    installedSize: "安装大小",
    installedVersion: "已安装版本",
    downloadSize: "下载大小",
    homepage: "主页",
    source: "软件源",
    status: "状态",
    file: "文件",
    output: "输出",
    operationSuccess: "操作成功",
    updating: "正在更新软件源...",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
  },
  "en-US": {
    appTitle: "APT Manager",
    refresh: "Refresh",
    installed: "Installed",
    upgradable: "Upgradable",
    search: "Search",
    sources: "Sources",
    actions: "Actions",
    about: "About",
    install: "Install",
    upgrade: "Upgrade",
    remove: "Remove",
    delete: "Delete",
    purge: "Purge",
    upgradeAll: "Upgrade All",
    addSource: "Add Source",
    updateCache: "Update Cache",
    updateCacheDesc: "Refresh apt source cache",
    autoremove: "Autoremove",
    autoremoveDesc: "Remove unused dependencies",
    cleanCache: "Clean Cache",
    cleanCacheDesc: "Clean downloaded package cache",
    save: "Save",
    close: "Close",
    confirm: "Confirm",
    cancel: "Cancel",
    loading: "Loading...",
    searchHint: "Enter keyword to search packages",
    filterPackages: "Filter packages (regex supported)",
    searchPackages: "Search packages (regex supported)",
    sourceFile: "File name",
    sourceLine: "Source line",
    confirmInstall: "Confirm install {name}?",
    confirmUpgrade: "Confirm upgrade {name}?",
    confirmUpgradeAll: "Confirm upgrade all upgradable packages?",
    confirmRemove: "Confirm remove {name}?",
    confirmPurge: "Confirm purge {name} (including config)?",
    confirmAutoremove: "Confirm autoremove unused dependencies?",
    confirmClean: "Confirm clean package cache?",
    confirmUpdate: "Confirm update source cache?",
    confirmRemoveSource: "Confirm remove this source?",
    noPackages: "No packages",
    noUpgradable: "All packages are up to date",
    noSources: "No sources",
    add: "Add",
    confirmDeleteSourceFile: "Confirm delete entire source file?",
    enterSourceLine: "Enter source line (e.g. deb https://... stable main)",
    fixBroken: "Fix Broken",
    fixBrokenDesc: "Fix broken dependencies",
    confirmFixBroken: "Confirm fix broken dependencies?",
    sourceType: "Type",
    sourceUrl: "URL",
    sourceSuite: "Suite",
    sourceComponent: "Component",
    sourceEnabled: "Status",
    enabled: "Enabled",
    disabled: "Disabled",
    package: "Package",
    version: "Version",
    arch: "Architecture",
    description: "Description",
    noDescription: "No description",
    newVersion: "New Version",
    oldVersion: "Old Version",
    section: "Section",
    maintainer: "Maintainer",
    depends: "Depends",
    installedSize: "Installed Size",
    installedVersion: "Installed Version",
    downloadSize: "Download Size",
    homepage: "Homepage",
    source: "APT Source",
    status: "Status",
    file: "File",
    output: "Output",
    operationSuccess: "Operation successful",
    updating: "Updating apt sources...",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
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
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
  document.title = t("appTitle");
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

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3000);
}

function showConfirm(message, callback) {
  state.confirmCallback = callback;
  document.getElementById("confirmMessage").textContent = message;
  document.getElementById("confirmModal").classList.remove("hidden");
}

function showOutput(title, content) {
  document.getElementById("outputTitle").textContent = title;
  document.getElementById("outputContent").textContent = content;
  document.getElementById("outputModal").classList.remove("hidden");
}

function closeModals() {
  document
    .querySelectorAll(".modal")
    .forEach((modal) => modal.classList.add("hidden"));
  state.confirmCallback = null;
}

function switchTab(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle(
      "hidden",
      panel.id !== `tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`,
    );
  });
  if (tabName === "installed" && state.installed.length === 0) {
    loadInstalled();
  } else if (tabName === "sources" && state.sources.length === 0) {
    loadSources();
  }
}

async function loadInstalled() {
  const list = document.getElementById("installedList");
  const empty = document.getElementById("installedEmpty");
  empty.textContent = t("loading");
  empty.classList.remove("hidden");
  list.innerHTML = "";
  try {
    const [installedResult, upgradableResult] = await Promise.all([
      api("list_installed"),
      api("list_upgradable"),
    ]);
    state.installed = installedResult.packages || [];
    state.upgradable = upgradableResult.packages || [];
    renderInstalled();
  } catch (error) {
    empty.textContent = error.message;
    empty.classList.remove("hidden");
  }
}

function renderInstalled() {
  const list = document.getElementById("installedList");
  const empty = document.getElementById("installedEmpty");
  const upgradeAllBtn = document.getElementById("upgradeAllBtn");
  const filter = (
    document.getElementById("installedSearch").value || ""
  ).trim();

  const upgradeMap = {};
  state.upgradable.forEach((pkg) => {
    upgradeMap[pkg.package] = pkg;
  });

  const totalUpgradable = state.upgradable.length;
  if (totalUpgradable > 0) {
    upgradeAllBtn.classList.remove("hidden");
    upgradeAllBtn.querySelector(".upgrade-count").textContent =
      ` (${totalUpgradable})`;
  } else {
    upgradeAllBtn.classList.add("hidden");
  }

  let regex;
  try {
    regex = filter ? new RegExp(filter, "i") : null;
  } catch {
    regex = null;
  }

  const packages = state.installed.filter(
    (pkg) => !regex || regex.test(pkg.package),
  );
  if (packages.length === 0) {
    list.innerHTML = "";
    empty.textContent = t("noPackages");
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  list.innerHTML = packages
    .map((pkg) => {
      const upgrade = upgradeMap[pkg.package];
      if (upgrade) {
        return `
        <div class="pkg-item upgradable-item" data-package="${escapeHtml(pkg.package)}" data-action="show">
          <div class="pkg-info">
            <strong class="pkg-name">${escapeHtml(pkg.package)}</strong>
            <span class="pkg-meta">
              <span class="pkg-ver-old">${escapeHtml(pkg.version)}</span>
              <span class="pkg-ver-arrow">→</span>
              <span class="pkg-ver-new">${escapeHtml(upgrade.new_version)}</span>
            </span>
            <span class="pkg-desc">${escapeHtml(pkg.description || "")}</span>
          </div>
          <button class="mini-btn" data-package="${escapeHtml(pkg.package)}" data-action="upgrade" type="button">${t("upgrade")}</button>
        </div>
      `;
      }
      return `
      <button class="pkg-item" data-package="${escapeHtml(pkg.package)}" data-action="show" type="button">
        <div class="pkg-info">
          <strong class="pkg-name">${escapeHtml(pkg.package)}</strong>
          <span class="pkg-meta">${escapeHtml(pkg.version)} · ${escapeHtml(pkg.arch)}</span>
          <span class="pkg-desc">${escapeHtml(pkg.description || "")}</span>
        </div>
        <span class="pkg-arrow">›</span>
      </button>
    `;
    })
    .join("");
}

async function loadUpgradable() {
  const list = document.getElementById("upgradableList");
  const empty = document.getElementById("upgradableEmpty");
  empty.textContent = t("loading");
  empty.classList.remove("hidden");
  list.innerHTML = "";
  try {
    const result = await api("list_upgradable");
    state.upgradable = result.packages || [];
    renderUpgradable();
  } catch (error) {
    empty.textContent = error.message;
    empty.classList.remove("hidden");
  }
}

function renderUpgradable() {
  const list = document.getElementById("upgradableList");
  const empty = document.getElementById("upgradableEmpty");
  if (state.upgradable.length === 0) {
    list.innerHTML = "";
    empty.textContent = t("noUpgradable");
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  list.innerHTML = state.upgradable
    .map(
      (pkg) => `
    <div class="upgrade-item" data-package="${escapeHtml(pkg.package)}" data-action="show">
      <div class="upgrade-info">
        <strong class="pkg-name">${escapeHtml(pkg.package)}</strong>
        <span class="pkg-meta">${escapeHtml(pkg.old_version)} → ${escapeHtml(pkg.new_version)}</span>
      </div>
      <button class="mini-btn" data-package="${escapeHtml(pkg.package)}" data-action="upgrade" type="button">${t("upgrade")}</button>
    </div>
  `,
    )
    .join("");
}

async function doSearch() {
  const keyword = (document.getElementById("searchInput").value || "").trim();
  if (!keyword) {
    showToast(t("searchHint"), true);
    return;
  }
  const list = document.getElementById("searchList");
  const empty = document.getElementById("searchEmpty");
  const btn = document.getElementById("searchBtn");
  empty.textContent = t("loading");
  empty.classList.remove("hidden");
  list.innerHTML = "";
  btn.disabled = true;
  state.loading = true;
  try {
    const result = await api("search", { keyword });
    state.searchResults = result.packages || [];
    renderSearch();
  } catch (error) {
    empty.textContent = error.message;
    empty.classList.remove("hidden");
  } finally {
    state.loading = false;
    btn.disabled = false;
  }
}

function renderSearch() {
  const list = document.getElementById("searchList");
  const empty = document.getElementById("searchEmpty");
  if (state.searchResults.length === 0) {
    list.innerHTML = "";
    empty.textContent = t("noPackages");
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  list.innerHTML = state.searchResults
    .map(
      (pkg) => `
    <button class="pkg-item" data-package="${escapeHtml(pkg.package)}" data-action="show" type="button">
      <div class="pkg-info">
        <strong class="pkg-name">${escapeHtml(pkg.package)}</strong>
        <span class="pkg-desc">${escapeHtml(pkg.description || "")}</span>
      </div>
      <span class="pkg-arrow">›</span>
    </button>
  `,
    )
    .join("");
}

async function loadSources() {
  const list = document.getElementById("sourcesList");
  const empty = document.getElementById("sourcesEmpty");
  empty.textContent = t("loading");
  empty.classList.remove("hidden");
  list.innerHTML = "";
  try {
    const result = await api("sources");
    state.sources = result.sources || [];
    renderSources();
  } catch (error) {
    empty.textContent = error.message;
    empty.classList.remove("hidden");
  }
}

function renderSources() {
  const list = document.getElementById("sourcesList");
  const empty = document.getElementById("sourcesEmpty");
  if (state.sources.length === 0) {
    list.innerHTML = "";
    empty.textContent = t("noSources");
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  const byFile = {};
  state.sources.forEach((src, index) => {
    const fname = src.file.split("/").pop() || src.file;
    if (!byFile[fname]) byFile[fname] = [];
    byFile[fname].push({ ...src, globalIndex: index });
  });

  const html = Object.entries(byFile)
    .map(
      ([fname, sources]) => `
    <div class="source-group">
      <div class="source-file-title">
        <span>${escapeHtml(fname)}</span>
        <span class="source-file-actions">
          <button class="mini-btn" data-file="${escapeHtml(fname)}" data-action="addSourceToFile" type="button">${t("add")}</button>
          <button class="mini-btn danger" data-file="${escapeHtml(fname)}" data-action="deleteSourceFile" type="button">${t("delete")}</button>
        </span>
      </div>
      <table class="source-table">
        <thead>
          <tr>
            <th class="col-enabled">${t("sourceEnabled")}</th>
            <th class="col-type">${t("sourceType")}</th>
            <th>${t("sourceUrl")}</th>
            <th class="col-suite">${t("sourceSuite")}</th>
            <th>${t("sourceComponent")}</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          ${sources
            .map(
              (src) => `
            <tr>
              <td class="col-enabled"><span class="badge badge-toggle ${src.enabled ? "badge-enabled" : "badge-disabled"}" data-file="${escapeHtml(src.file)}" data-line="${escapeHtml(src.line)}" data-action="toggleSource">${src.enabled ? t("enabled") : t("disabled")}</span></td>
              <td><span class="badge badge-type">${escapeHtml(src.type)}</span></td>
              <td>${escapeHtml(src.url)}</td>
              <td>${escapeHtml(src.suite)}</td>
              <td>${escapeHtml(src.components)}</td>
              <td class="col-actions"><button class="mini-btn danger" data-index="${src.globalIndex}" data-action="removeSource" type="button">${t("delete")}</button></td>
            </tr>
          `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `,
    )
    .join("");

  list.innerHTML = html;
}

async function showPackageDetail(packageName) {
  try {
    const result = await api("show", { package: packageName });
    const info = result.info || {};
    const isInstalled = Boolean(info.installed_version);

    document.getElementById("detailTitle").textContent = packageName;

    const formatSize = (value) => {
      if (!value) return value;
      const str = String(value).trim();
      if (/^\d+$/.test(str)) return str + " kB";
      return str;
    };

    info["installed-size"] = formatSize(info["installed-size"]);
    info["download-size"] = formatSize(info["download-size"]);

    const fields = [
      { key: "version", label: "version" },
      { key: "installed_version", label: "installedVersion" },
      { key: "section", label: "section" },
      { key: "installed-size", label: "installedSize" },
      { key: "download-size", label: "downloadSize" },
      { key: "maintainer", label: "maintainer" },
      { key: "homepage", label: "homepage", link: true },
      { key: "apt-sources", label: "source" },
      { key: "depends", label: "depends" },
      { key: "description", label: "description", multiline: true },
    ];

    document.getElementById("detailBody").innerHTML = fields
      .filter((f) => f.key === "description" || info[f.key])
      .map((f) => {
        let value = info[f.key] ? escapeHtml(info[f.key]) : t("noDescription");
        if (f.multiline) value = value.replace(/\n/g, "<br>");
        if (f.link && /^https?:\/\//i.test(info[f.key])) {
          value = `<a href="${escapeHtml(info[f.key])}" target="_blank" rel="noopener noreferrer">${value}</a>`;
        }
        return `
          <div class="detail-row">
            <span class="detail-label">${t(f.label)}</span>
            <span class="detail-value">${value}</span>
          </div>
        `;
      })
      .join("");

    const installBtn = document.getElementById("detailInstallBtn");
    const upgradeBtn = document.getElementById("detailUpgradeBtn");
    const removeBtn = document.getElementById("detailRemoveBtn");
    const purgeBtn = document.getElementById("detailPurgeBtn");

    installBtn.classList.toggle("hidden", isInstalled);
    upgradeBtn.classList.toggle("hidden", !isInstalled);
    removeBtn.classList.toggle("hidden", !isInstalled);
    purgeBtn.classList.toggle("hidden", !isInstalled);

    installBtn.dataset.package = packageName;
    upgradeBtn.dataset.package = packageName;
    removeBtn.dataset.package = packageName;
    purgeBtn.dataset.package = packageName;

    document.getElementById("detailModal").classList.remove("hidden");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function doInstall(packageName) {
  showConfirm(t("confirmInstall", { name: packageName }), async () => {
    try {
      await withProgress(async () => {
        const result = await api("install", { package: packageName });
        showToast(t("operationSuccess"));
        if (result.output) {
          showOutput(t("output"), result.output);
        }
      });
      loadInstalled();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doUpgrade(packageName) {
  showConfirm(t("confirmUpgrade", { name: packageName }), async () => {
    try {
      await withProgress(async () => {
        const result = await api("upgrade", { package: packageName });
        showToast(t("operationSuccess"));
        if (result.output) {
          showOutput(t("output"), result.output);
        }
      });
      loadInstalled();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doUpgradeAll() {
  showConfirm(t("confirmUpgradeAll"), async () => {
    try {
      await withProgress(async () => {
        const result = await api("upgrade", {});
        showToast(t("operationSuccess"));
        if (result.output) {
          showOutput(t("output"), result.output);
        }
      });
      loadInstalled();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doRemove(packageName) {
  showConfirm(t("confirmRemove", { name: packageName }), async () => {
    try {
      await withProgress(async () => {
        const result = await api("remove", { package: packageName });
        showToast(t("operationSuccess"));
        if (result.output) {
          showOutput(t("output"), result.output);
        }
      });
      loadInstalled();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doPurge(packageName) {
  showConfirm(t("confirmPurge", { name: packageName }), async () => {
    try {
      await withProgress(async () => {
        const result = await api("remove", {
          package: packageName,
          purge: true,
        });
        showToast(t("operationSuccess"));
        if (result.output) {
          showOutput(t("output"), result.output);
        }
      });
      loadInstalled();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

function withProgress(fn) {
  const bar = document.getElementById("progressBar");
  if (bar) bar.classList.remove("hidden");
  return fn().finally(() => {
    if (bar) bar.classList.add("hidden");
  });
}

function runAction(cardId, fn) {
  const card = document.getElementById(cardId);
  if (!card) return fn();
  const icon = card.querySelector(".action-icon");
  const origIcon = icon ? icon.textContent : "";
  const allCards = document.querySelectorAll(".action-card");

  card.classList.add("running");
  if (icon) icon.textContent = "⏳";
  allCards.forEach((c) => {
    c.disabled = true;
  });

  return fn().finally(() => {
    card.classList.remove("running");
    if (icon) icon.textContent = origIcon;
    allCards.forEach((c) => {
      c.disabled = false;
    });
  });
}

async function doUpdate() {
  showConfirm(t("confirmUpdate"), async () => {
    try {
      await withProgress(() =>
        runAction("actionUpdate", async () => {
          const result = await api("update");
          showToast(t("operationSuccess"));
          if (result.output) {
            showOutput(t("output"), result.output);
          }
        }),
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doAutoremove() {
  showConfirm(t("confirmAutoremove"), async () => {
    try {
      await withProgress(() =>
        runAction("actionAutoremove", async () => {
          const result = await api("autoremove");
          showToast(t("operationSuccess"));
          if (result.output) {
            showOutput(t("output"), result.output);
          }
        }),
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doClean() {
  showConfirm(t("confirmClean"), async () => {
    try {
      await withProgress(() =>
        runAction("actionClean", async () => {
          const result = await api("clean");
          showToast(t("operationSuccess"));
          if (result.output) {
            showOutput(t("output"), result.output);
          }
        }),
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doFixBroken() {
  showConfirm(t("confirmFixBroken"), async () => {
    try {
      await withProgress(() =>
        runAction("actionFixBroken", async () => {
          const result = await api("fix_broken");
          showToast(t("operationSuccess"));
          if (result.output) {
            showOutput(t("output"), result.output);
          }
        }),
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doAddSource() {
  const file = (document.getElementById("sourceFile").value || "").trim();
  const line = (document.getElementById("sourceLine").value || "").trim();
  if (!line) {
    showToast("source line is required", true);
    return;
  }
  try {
    await api("add_source", { file: file || "fn-aptmng.list", line });
    showToast(t("operationSuccess"));
    closeModals();
    loadSources();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function doRemoveSource(index) {
  const src = state.sources[index];
  if (!src) return;
  showConfirm(t("confirmRemoveSource"), async () => {
    try {
      const fileName = src.file.split("/").pop() || "fn-aptmng.list";
      const file = fileName.endsWith(".list")
        ? fileName.replace(/\.list$/, "")
        : fileName;
      await api("remove_source", { file, line: src.line });
      showToast(t("operationSuccess"));
      loadSources();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function doToggleSource(file, line) {
  try {
    await api("toggle_source", { file, line });
    loadSources();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function doAddSourceToFile(fname) {
  document.getElementById("sourceFile").value = fname;
  document.getElementById("sourceLine").value = "";
  document.getElementById("sourceModal").classList.remove("hidden");
}

async function doDeleteSourceFile(fname) {
  showConfirm(t("confirmDeleteSourceFile"), async () => {
    try {
      await api("delete_source_file", { file: fname });
      showToast(t("operationSuccess"));
      loadSources();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

function init() {
  try {
    applyPreferences();
  } catch (e) {
    console.error("applyPreferences failed:", e);
  }

  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("refreshBtn").addEventListener("click", async () => {
    try {
      await withProgress(async () => {
        await api("update");
      });
      showToast(t("operationSuccess"));
      state.installed = [];
      state.upgradable = [];
      state.sources = [];
      state.searchResults = [];
      switchTab(state.activeTab);
    } catch (error) {
      showToast(error.message, true);
    }
  });

  document
    .getElementById("installedSearch")
    .addEventListener("input", () => renderInstalled());

  document
    .getElementById("searchBtn")
    .addEventListener("click", () => doSearch());
  document.getElementById("searchInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
  });

  document
    .getElementById("upgradeAllBtn")
    .addEventListener("click", () =>
      doUpgradeAll().catch((e) => showToast(e.message, true)),
    );

  document.getElementById("addSourceBtn").addEventListener("click", () => {
    document.getElementById("sourceFile").value = "fn-aptmng.list";
    document.getElementById("sourceLine").value = "";
    document.getElementById("sourceModal").classList.remove("hidden");
  });

  document
    .getElementById("saveSourceBtn")
    .addEventListener("click", () => doAddSource());

  document
    .getElementById("actionUpdate")
    .addEventListener("click", () =>
      doUpdate().catch((e) => showToast(e.message, true)),
    );
  document
    .getElementById("actionFixBroken")
    .addEventListener("click", () =>
      doFixBroken().catch((e) => showToast(e.message, true)),
    );
  document
    .getElementById("actionAutoremove")
    .addEventListener("click", () =>
      doAutoremove().catch((e) => showToast(e.message, true)),
    );
  document
    .getElementById("actionClean")
    .addEventListener("click", () =>
      doClean().catch((e) => showToast(e.message, true)),
    );

  document.getElementById("aboutBtn").addEventListener("click", () => {
    document.getElementById("aboutModal").classList.remove("hidden");
  });

  document
    .getElementById("detailInstallBtn")
    .addEventListener("click", function () {
      closeModals();
      doInstall(this.dataset.package);
    });
  document
    .getElementById("detailUpgradeBtn")
    .addEventListener("click", function () {
      closeModals();
      doUpgrade(this.dataset.package);
    });
  document
    .getElementById("detailRemoveBtn")
    .addEventListener("click", function () {
      closeModals();
      doRemove(this.dataset.package);
    });
  document
    .getElementById("detailPurgeBtn")
    .addEventListener("click", function () {
      closeModals();
      doPurge(this.dataset.package);
    });

  document
    .getElementById("confirmOkBtn")
    .addEventListener("click", async () => {
      const cb = state.confirmCallback;
      closeModals();
      if (cb) {
        await cb();
      }
    });

  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;
    const packageName = target.dataset.package;

    if (action === "show") {
      showPackageDetail(packageName);
    } else if (action === "upgrade") {
      e.stopPropagation();
      doUpgrade(packageName);
    } else if (action === "removeSource") {
      e.stopPropagation();
      doRemoveSource(parseInt(target.dataset.index, 10));
    } else if (action === "toggleSource") {
      e.stopPropagation();
      doToggleSource(target.dataset.file, target.dataset.line);
    } else if (action === "addSourceToFile") {
      e.stopPropagation();
      doAddSourceToFile(target.dataset.file);
    } else if (action === "deleteSourceFile") {
      e.stopPropagation();
      doDeleteSourceFile(target.dataset.file);
    }
  });

  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModals());
  });

  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModals();
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModals();
  });

  loadInstalled();

  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => applyPreferences());
  setInterval(() => applyPreferences(), 5000);
}

document.addEventListener("DOMContentLoaded", init);
