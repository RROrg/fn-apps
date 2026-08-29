import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

const state = {
  mappings: [],
  status: "all",
  scheme: "all",
  language: "zh-CN",
  theme: "light",
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

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
}

function applyLanguage() {
  const language = String(platformConfig.language || "").replace("_", "-");
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
  const theme = String(v || "").toLowerCase() === "dark" ? "dark" : "light";
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  document.body.dataset.theme = theme;
}

function applyPreferences({ rerender = false } = {}) {
  const languageChanged = applyLanguage();
  applyTheme();
  document.title = t("appTitle");
  if (sdk.setTitle) {
    sdk.setTitle(t("appTitle")).catch(() => {});
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

  if (rerender && languageChanged) renderRows();
}

async function api(action, data = {}) {
  // token 由 fnOS 网关注入鉴权；后端不校验 token，不在此转发
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
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 2800);
}

function proxyPath(mapping) {
  return `./${mapping.slug}`;
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
  await loadMappings();
});
