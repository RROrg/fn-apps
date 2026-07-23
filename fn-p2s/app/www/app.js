function trimTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

function currentBasePath() {
  const script =
    document.currentScript || document.querySelector('script[src$="app.js"]');
  if (script?.src) {
    const url = new URL(script.src, location.href);
    return trimTrailingSlash(url.pathname.replace(/\/app\.js$/, ""));
  }
  return trimTrailingSlash(
    location.pathname.replace(/\/(?:index\.html)?$/, ""),
  );
}

const BASE_PATH = currentBasePath() || ".";
const API_ENDPOINT = `${BASE_PATH}/api`;

const state = {
  mappings: [],
  status: "all",
  scheme: "all",
  language: "zh-CN",
};

const I18N = {
  "zh-CN": {
    appTitle: "端口代理",
    addProxy: "添加代理",
    about: "关于",
    status: "状态",
    all: "全部",
    enabled: "已启用",
    disabled: "已禁用",
    inject: "注入脚本",
    injected: "已注入",
    notInjected: "未注入",
    openMode: "打开方式",
    openInWindow: "新窗口",
    openInIframe: "内嵌窗口",
    scheme: "协议",
    refresh: "刷新",
    newMapping: "新建映射",
    editMapping: "编辑映射",
    name: "名称",
    path: "路径",
    target: "目标",
    action: "操作",
    empty: "暂无映射",
    slug: "路径别名",
    host: "主机",
    port: "端口",
    description: "描述",
    test: "测试",
    cancel: "取消",
    save: "保存",
    close: "关闭",
    open: "打开",
    edit: "编辑",
    delete: "删除",
    deleteConfirm: "确定删除 {name} 吗？",
    saved: "已保存",
    deleted: "已删除",
    refreshed: "已刷新",
    reachable: "可连接",
    unreachable: "无法连接",
    loadFailed: "加载失败",
    saveFailed: "保存失败",
    totalItems: "共 {total} 项",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
  },
  "en-US": {
    appTitle: "Port Proxy",
    addProxy: "Add Proxy",
    about: "About",
    status: "Status",
    all: "All",
    enabled: "Enabled",
    disabled: "Disabled",
    inject: "Inject Script",
    injected: "Injected",
    notInjected: "No Inject",
    openMode: "Open Mode",
    openInWindow: "New Window",
    openInIframe: "Iframe",
    scheme: "Scheme",
    refresh: "Refresh",
    newMapping: "New Mapping",
    editMapping: "Edit Mapping",
    name: "Name",
    path: "Path",
    target: "Target",
    action: "Action",
    empty: "No mappings",
    slug: "Path Alias",
    host: "Host",
    port: "Port",
    description: "Description",
    test: "Test",
    cancel: "Cancel",
    save: "Save",
    close: "Close",
    open: "Open",
    edit: "Edit",
    delete: "Delete",
    deleteConfirm: "Delete {name}?",
    saved: "Saved",
    deleted: "Deleted",
    refreshed: "Refreshed",
    reachable: "Reachable",
    unreachable: "Unreachable",
    loadFailed: "Load failed",
    saveFailed: "Save failed",
    totalItems: "{total} items",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
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
  if (theme.includes("dark") || theme === "night" || theme === "20")
    return "dark";
  if (theme.includes("light") || theme === "day" || theme === "10")
    return "light";
  if (["system", "auto", "os"].includes(theme))
    return prefersDarkTheme() ? "dark" : "light";
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
      queryValue("fnos-theme-mode"),
    ]
      .map(normalizeTheme)
      .find(Boolean) || (prefersDarkTheme() ? "dark" : "light")
  );
}

function applyPreferences({ rerender = false } = {}) {
  const nextLanguage = currentLanguage();
  const languageChanged = nextLanguage !== state.language;
  state.language = nextLanguage;
  document.documentElement.lang = nextLanguage;
  document.documentElement.dataset.theme = currentTheme();
  document.title = t("appTitle");

  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n, { base: BASE_PATH });
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
    node.setAttribute("aria-label", t(node.dataset.i18nTitle));
  });
  if (rerender && languageChanged) renderRows();
}

function authToken() {
  return safeDecode(
    cookieValue("fnos-token") ||
      cookieValue("trim_token") ||
      cookieValue("token"),
  );
}

async function api(action, data = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = authToken();
  if (token) headers.Authorization = `trim ${token}`;
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
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 2800);
}

function proxyPath(mapping) {
  return `${BASE_PATH}/${mapping.slug}`;
}

function targetText(mapping) {
  return `${mapping.scheme}://${mapping.host}:${mapping.port}`;
}

function mappingSavePayload(mapping, overrides = {}) {
  return {
    existingSlug: mapping.slug,
    name: mapping.name || mapping.slug,
    slug: mapping.slug,
    scheme: mapping.scheme,
    host: mapping.host,
    port: mapping.port,
    enabled: mapping.enabled !== false,
    inject: mapping.inject === true,
    openMode: mapping.openMode || "window",
    description: mapping.description || "",
    ...overrides,
  };
}

function filteredMappings() {
  return state.mappings.filter((mapping) => {
    if (state.status === "enabled" && !mapping.enabled) return false;
    if (state.status === "disabled" && mapping.enabled) return false;
    if (state.scheme !== "all" && mapping.scheme !== state.scheme) return false;
    return true;
  });
}

function renderRows() {
  const rows = document.getElementById("mappingRows");
  const empty = document.getElementById("emptyState");
  const mappings = filteredMappings();
  empty.classList.toggle("hidden", mappings.length > 0);
  document.getElementById("summary").textContent = t("totalItems", {
    total: mappings.length,
  });

  rows.innerHTML = mappings
    .map(
      (mapping) => `
    <tr>
      <td>
        <button class="list-toggle ${mapping.enabled ? "enabled" : ""}" data-action="toggle-enabled" data-slug="${escapeHtml(mapping.slug)}" type="button" aria-pressed="${mapping.enabled ? "true" : "false"}">
          <span></span>
        </button>
      </td>
      <td>
        <div class="app-name">${escapeHtml(mapping.name || mapping.slug)}</div>
        <div class="app-id">${escapeHtml(mapping.description || mapping.slug)}</div>
      </td>
      <td><code>${escapeHtml(proxyPath(mapping))}</code></td>
      <td><code>${escapeHtml(targetText(mapping))}</code></td>
      <td><span class="status-pill ${mapping.inject ? "enabled" : "disabled"}">${mapping.inject ? t("injected") : t("notInjected")}</span></td>
      <td>
        <div class="row-actions">
          <button class="download-btn" data-action="open" data-slug="${escapeHtml(mapping.slug)}" ${mapping.enabled ? "" : "disabled"} type="button">${t("open")}</button>
          <button class="plain-btn row-btn" data-action="edit" data-slug="${escapeHtml(mapping.slug)}" type="button">${t("edit")}</button>
          <button class="download-btn delete-btn" data-action="delete" data-slug="${escapeHtml(mapping.slug)}" type="button">${t("delete")}</button>
        </div>
      </td>
    </tr>
  `,
    )
    .join("");
}

async function loadMappings(showMessage = false) {
  try {
    const result = await api("list");
    state.mappings = result.mappings || [];
    renderRows();
    if (showMessage) showToast(t("refreshed"));
  } catch (error) {
    showToast(`${t("loadFailed")}: ${error.message}`, true);
  }
}

function mappingFromForm() {
  const mapping = {
    existingSlug: document.getElementById("existingSlugInput").value.trim(),
    name: document.getElementById("nameInput").value.trim(),
    slug: document.getElementById("slugInput").value.trim(),
    scheme: document.getElementById("formSchemeSelect").value,
    host: document.getElementById("hostInput").value.trim() || "127.0.0.1",
    port: Number(document.getElementById("portInput").value),
    inject: document.getElementById("injectInput").checked,
    openMode: document.getElementById("openModeSelect").value,
    description: document.getElementById("descriptionInput").value.trim(),
  };
  const existing = state.mappings.find(
    (item) => item.slug === mapping.existingSlug,
  );
  mapping.enabled = existing ? existing.enabled !== false : true;
  return mapping;
}

function fillForm(mapping = null) {
  document.getElementById("editTitle").textContent = t(
    mapping ? "editMapping" : "newMapping",
  );
  document.getElementById("existingSlugInput").value = mapping?.slug || "";
  document.getElementById("nameInput").value = mapping?.name || "";
  document.getElementById("slugInput").value = mapping?.slug || "";
  document.getElementById("formSchemeSelect").value = mapping?.scheme || "http";
  document.getElementById("hostInput").value = mapping?.host || "127.0.0.1";
  document.getElementById("portInput").value = mapping?.port || "";
  document.getElementById("openModeSelect").value =
    mapping?.openMode || "window";
  document.getElementById("injectInput").checked = mapping?.inject === true;
  document.getElementById("descriptionInput").value =
    mapping?.description || "";
  document.getElementById("testResult").textContent = "";
}

function openEditor(mapping = null) {
  fillForm(mapping);
  document.getElementById("editModal").classList.remove("hidden");
  setTimeout(
    () => document.getElementById(mapping ? "nameInput" : "slugInput").focus(),
    0,
  );
}

function openProxy(mapping) {
  const path = proxyPath(mapping);
  if ((mapping.openMode || "window") === "iframe") {
    document.getElementById("iframeTitle").textContent =
      mapping.name || mapping.slug;
    const frame = document.getElementById("proxyFrame");
    frame.src = "about:blank";
    requestAnimationFrame(() => {
      frame.src = path;
    });
    document.getElementById("iframeModal").classList.remove("hidden");
    return;
  }
  window.open(path, "_blank");
}

function closeModals() {
  document.getElementById("proxyFrame").src = "about:blank";
  document
    .querySelectorAll(".modal")
    .forEach((modal) => modal.classList.add("hidden"));
}

function bindEvents() {
  document
    .getElementById("statusSelect")
    .addEventListener("change", (event) => {
      state.status = event.target.value;
      renderRows();
    });
  document
    .getElementById("schemeSelect")
    .addEventListener("change", (event) => {
      state.scheme = event.target.value;
      renderRows();
    });
  document
    .getElementById("refreshBtn")
    .addEventListener("click", () => loadMappings(true));
  document
    .getElementById("newBtn")
    .addEventListener("click", () => openEditor());
  document
    .getElementById("aboutBtn")
    .addEventListener("click", () =>
      document.getElementById("aboutModal").classList.remove("hidden"),
    );
  document
    .querySelectorAll("[data-close]")
    .forEach((node) => node.addEventListener("click", closeModals));

  document
    .getElementById("mappingRows")
    .addEventListener("click", async (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const mapping = state.mappings.find(
        (item) => item.slug === button.dataset.slug,
      );
      if (!mapping) return;
      if (button.dataset.action === "open") {
        openProxy(mapping);
        return;
      }
      if (button.dataset.action === "toggle-enabled") {
        try {
          const result = await api("save", {
            mapping: mappingSavePayload(mapping, {
              enabled: mapping.enabled === false,
            }),
          });
          state.mappings = result.mappings || [];
          renderRows();
          showToast(t("saved"));
        } catch (error) {
          showToast(error.message, true);
        }
        return;
      }
      if (button.dataset.action === "edit") {
        openEditor(mapping);
        return;
      }
      if (!confirm(t("deleteConfirm", { name: mapping.name || mapping.slug })))
        return;
      try {
        const result = await api("delete", { slug: mapping.slug });
        state.mappings = result.mappings || [];
        renderRows();
        showToast(t("deleted"));
      } catch (error) {
        showToast(error.message, true);
      }
    });

  document.getElementById("testBtn").addEventListener("click", async () => {
    const resultNode = document.getElementById("testResult");
    resultNode.textContent = "...";
    try {
      const result = await api("test", {
        mapping: mappingFromForm(),
        existingSlug: document.getElementById("existingSlugInput").value.trim(),
      });
      resultNode.textContent = result.reachable
        ? t("reachable")
        : t("unreachable");
      resultNode.classList.toggle("bad", !result.reachable);
    } catch (error) {
      resultNode.textContent = error.message;
      resultNode.classList.add("bad");
    }
  });

  document
    .getElementById("mappingForm")
    .addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const result = await api("save", { mapping: mappingFromForm() });
        state.mappings = result.mappings || [];
        closeModals();
        renderRows();
        showToast(t("saved"));
      } catch (error) {
        showToast(`${t("saveFailed")}: ${error.message}`, true);
      }
    });
}

window.addEventListener("load", async () => {
  applyPreferences();
  bindEvents();
  await loadMappings();
});

themeMedia()?.addEventListener?.("change", () => applyPreferences());
window.addEventListener("storage", () => applyPreferences({ rerender: true }));
