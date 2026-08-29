import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

const state = {
  apps: [],
  services: [],
  env: [],
  runAs: {},
  selectedAppId: null,
  selectedServiceIndex: 0,
  selectedEnvIndex: 0,
  query: "",
  language: "zh-CN",
  theme: "light",
  saving: false,
  restartBaseline: {},
};

const I18N = {
  "zh-CN": {
    appTitle: "应用设置",
    apps: "应用",
    refresh: "刷新",
    searchApps: "搜索应用",
    about: "关于",
    save: "保存修改",
    saving: "保存中...",
    appConfig: "应用配置",
    installInfo: "安装信息",
    privilegeConfig: "权限配置",
    wizardParams: "Wizard 参数",
    uiConfig: "UI 配置",
    addEntry: "新增条目",
    deleteEntry: "删除条目",
    loading: "正在加载...",
    emptyApps: "暂无应用",
    editorTitle: "{name} 配置",
    entry: "条目 {index}",
    saveSuccess: "保存成功",
    refreshed: "已刷新",
    close: "关闭",
    selectWizardEntry: "选择 Wizard 参数条目",
    selectServiceEntry: "选择 UI 配置条目",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    field_id: "ID",
    field_app_name: "应用名称",
    field_name: "显示名称",
    field_version: "版本",
    field_version_id: "版本 ID",
    field_tags: "标签",
    field_maintainer: "开发者",
    field_distributor: "发布者",
    field_download_count: "下载次数",
    field_install_type: "安装类型",
    field_path: "安装路径",
    field_install_volume_id: "安装卷 ID",
    field_data_share_volume_id: "数据共享卷 ID",
    field_data_volume_id: "数据卷 ID",
    field_manual_install: "手动安装",
    field_is_stop: "是否停止",
    field_is_uninstall: "是否卸载",
    field_is_beta: "是否测试版",
    field_is_docker: "是否 Docker 应用",
    field_min_size: "最小容量",
    field_service_url: "服务地址",
    field_source: "来源",
    field_source_id: "来源 ID",
    field_status: "状态",
    field_is_non_manual_stop: "是否非手动停止",
    field_is_systemd_uint: "是否 Systemd 单元",
    field_disable_authorization_path: "禁用鉴权路径",
    field_features: "功能特性",
    field_micro_app: "微应用",
    field_native_app: "原生应用",
    field_file_types: "文件类型",
    field_is_power_off_stop: "是否关机停止",
    field_i18n_matadata: "国际化元数据",
    field_disabled_reason: "禁用原因",
    field_disabled_at: "禁用时间",
    field_service_name: "服务名称",
    field_title: "标题",
    field_desc: "描述",
    field_icon: "图标",
    field_type: "类型",
    field_url: "URL",
    field_default_url: "默认 URL",
    field_is_admin: "是否管理员",
    field_control: "控制配置",
    field_full_url: "完整 URL",
    field_no_display: "隐藏显示",
    field_gateway_socket: "网关 Socket",
    field_gateway_prefix: "网关 Prefix",
    field_k: "键名",
    field_v: "键值",
  },
  "en-US": {
    appTitle: "App Settings",
    apps: "Apps",
    refresh: "Refresh",
    searchApps: "Search apps",
    about: "About",
    save: "Save Changes",
    saving: "Saving...",
    appConfig: "App Config",
    installInfo: "Install Info",
    privilegeConfig: "Privilege",
    wizardParams: "Wizard Params",
    uiConfig: "UI Config",
    addEntry: "Add Entry",
    deleteEntry: "Delete Entry",
    loading: "Loading...",
    emptyApps: "No apps",
    editorTitle: "{name} Config",
    entry: "Entry {index}",
    saveSuccess: "Saved",
    refreshed: "Refreshed",
    close: "Close",
    selectWizardEntry: "Select Wizard Param Entry",
    selectServiceEntry: "Select UI Config Entry",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    field_id: "ID",
    field_app_name: "App Name",
    field_name: "Display Name",
    field_version: "Version",
    field_version_id: "Version ID",
    field_tags: "Tags",
    field_maintainer: "Maintainer",
    field_distributor: "Distributor",
    field_download_count: "Download Count",
    field_install_type: "Install Type",
    field_path: "Install Path",
    field_install_volume_id: "Install Volume ID",
    field_data_share_volume_id: "Data Share Volume ID",
    field_data_volume_id: "Data Volume ID",
    field_manual_install: "Manual Install",
    field_is_stop: "Is Stopped",
    field_is_uninstall: "Is Uninstalled",
    field_is_beta: "Is Beta",
    field_is_docker: "Is Docker App",
    field_min_size: "Min Size",
    field_service_url: "Service URL",
    field_source: "Source",
    field_source_id: "Source ID",
    field_status: "Status",
    field_is_non_manual_stop: "Is Non-manual Stop",
    field_is_systemd_uint: "Is Systemd Unit",
    field_disable_authorization_path: "Disable Auth Path",
    field_features: "Features",
    field_micro_app: "Micro App",
    field_native_app: "Native App",
    field_file_types: "File Types",
    field_is_power_off_stop: "Is Power-off Stop",
    field_i18n_matadata: "i18n Metadata",
    field_disabled_reason: "Disabled Reason",
    field_disabled_at: "Disabled At",
    field_service_name: "Service Name",
    field_title: "Title",
    field_desc: "Description",
    field_icon: "Icon",
    field_type: "Type",
    field_url: "URL",
    field_default_url: "Default URL",
    field_is_admin: "Is Admin",
    field_control: "Control Config",
    field_full_url: "Full URL",
    field_no_display: "Hidden",
    field_gateway_socket: "Gateway Socket",
    field_gateway_prefix: "Gateway Prefix",
    field_k: "Key",
    field_v: "Value",
  },
};

const appFields = [
  { name: "id", label: "field_id", readonly: true },
  { name: "app_name", label: "field_app_name" },
  { name: "name", label: "field_name" },
  { name: "version", label: "field_version" },
  { name: "version_id", label: "field_version_id", readonly: true },
  { name: "tags", label: "field_tags" },
  { name: "maintainer", label: "field_maintainer" },
  { name: "distributor", label: "field_distributor" },
  { name: "download_count", label: "field_download_count" },
  { name: "install_type", label: "field_install_type", readonly: true },
  { name: "path", label: "field_path", readonly: true },
  {
    name: "install_volume_id",
    label: "field_install_volume_id",
    readonly: true,
  },
  {
    name: "data_share_volume_id",
    label: "field_data_share_volume_id",
    readonly: true,
  },
  { name: "data_volume_id", label: "field_data_volume_id", readonly: true },
  { name: "manual_install", label: "field_manual_install", type: "bool" },
  { name: "is_stop", label: "field_is_stop", type: "bool" },
  { name: "is_uninstall", label: "field_is_uninstall", type: "bool" },
  { name: "is_beta", label: "field_is_beta", type: "bool" },
  { name: "is_docker", label: "field_is_docker", type: "bool", readonly: true },
  { name: "min_size", label: "field_min_size" },
  { name: "service_url", label: "field_service_url" },
  {
    name: "source",
    label: "field_source",
    options: ["thirdparty", "official"],
  },
  { name: "source_id", label: "field_source_id", readonly: true },
  { name: "status", label: "field_status", readonly: true },
  {
    name: "is_non_manual_stop",
    label: "field_is_non_manual_stop",
    type: "bool",
  },
  { name: "is_systemd_uint", label: "field_is_systemd_uint", type: "bool" },
  {
    name: "disable_authorization_path",
    label: "field_disable_authorization_path",
    type: "bool",
  },
  { name: "features", label: "field_features", textarea: true },
  { name: "micro_app", label: "field_micro_app", type: "bool" },
  { name: "native_app", label: "field_native_app", type: "bool" },
  { name: "file_types", label: "field_file_types" },
  { name: "is_power_off_stop", label: "field_is_power_off_stop" },
  { name: "i18n_matadata", label: "field_i18n_matadata", textarea: true },
  { name: "disabled_reason", label: "field_disabled_reason", readonly: true },
  { name: "disabled_at", label: "field_disabled_at", readonly: true },
];

const serviceFields = [
  { name: "id", label: "field_id", readonly: true },
  { name: "app_id", label: "field_app_name", readonly: true },
  { name: "service_name", label: "field_service_name" },
  { name: "title", label: "field_title" },
  { name: "desc", label: "field_desc" },
  { name: "icon", label: "field_icon" },
  { name: "type", label: "field_type", options: ["iframe", "url"] },
  { name: "url", label: "field_url" },
  { name: "default_url", label: "field_default_url" },
  { name: "is_admin", label: "field_is_admin", type: "bool" },
  { name: "control", label: "field_control", textarea: true },
  { name: "full_url", label: "field_full_url" },
  { name: "no_display", label: "field_no_display", type: "bool" },
  { name: "gateway_socket", label: "field_gateway_socket" },
  { name: "gateway_prefix", label: "field_gateway_prefix" },
  { name: "file_types", label: "field_file_types" },
  { name: "i18n_matadata", label: "field_i18n_matadata", textarea: true },
];

const serviceRestartFieldNames = serviceFields
  .map((field) => field.name)
  .filter((name) => name !== "id" && name !== "app_id");

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

function t(key, params = {}) {
  const messages = I18N[state.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
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
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.title = t("appTitle");
  if (!currentApp()) {
    document.getElementById("pageTitle").textContent = t("appConfig");
  }
  if (state.saving) {
    document.getElementById("saveBtn").textContent = t("saving");
  }

  if (rerender && languageChanged) {
    renderEditor();
  }
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

function boolValue(value) {
  return value === true || value === "t" || value === "true" || value === 1;
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
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 2600);
}

function setSaving(isSaving) {
  state.saving = isSaving;
  const saveBtn = document.getElementById("saveBtn");
  saveBtn.disabled = isSaving;
  saveBtn.textContent = isSaving ? t("saving") : t("save");
}

function openAbout() {
  document.getElementById("aboutModal").classList.remove("hidden");
}

function closeModals() {
  document
    .querySelectorAll(".modal")
    .forEach((modal) => modal.classList.add("hidden"));
}

function currentApp() {
  return state.apps.find((app) => app.id === state.selectedAppId) || null;
}

function currentServices() {
  return state.services.filter(
    (item) => item.app_id === state.selectedAppId && !item._delete,
  );
}

function currentEnv() {
  return state.env.filter(
    (item) => item.app_id === state.selectedAppId && !item._delete,
  );
}

function currentRunAs() {
  return state.runAs[String(state.selectedAppId)] === "package"
    ? "package"
    : "root";
}

function uniqueValue(base, existing) {
  const cleanBase = String(base || "item");
  if (!existing.has(cleanBase)) return cleanBase;
  let index = 2;
  while (existing.has(`${cleanBase}_${index}`)) index += 1;
  return `${cleanBase}_${index}`;
}

function restartSnapshot(appId) {
  const id = Number(appId);
  return JSON.stringify({
    runAs: state.runAs[String(id)] === "package" ? "package" : "root",
    services: state.services
      .filter((item) => item.app_id === id)
      .map((item) => {
        const snapshot = { id: item.id || "", delete: Boolean(item._delete) };
        serviceRestartFieldNames.forEach((name) => {
          snapshot[name] = item[name] ?? "";
        });
        return snapshot;
      }),
    env: state.env
      .filter((item) => item.app_id === id)
      .map((item) => ({
        id: item.id || "",
        delete: Boolean(item._delete),
        k: item.k ?? "",
        v: item.v ?? "",
      })),
  });
}

function rebuildRestartBaseline() {
  state.restartBaseline = {};
  state.apps.forEach((app) => {
    state.restartBaseline[String(app.id)] = restartSnapshot(app.id);
  });
}

function fallbackIcon(app) {
  return escapeHtml(
    (app.name || app.app_name || "?").slice(0, 1).toUpperCase(),
  );
}

function iconUrl(app) {
  const version = encodeURIComponent(app.updated_at || app.version || "");
  return `${API_ENDPOINT}?action=icon&id=${encodeURIComponent(app.id)}&v=${version}`;
}

function renderAppList() {
  const query = state.query.trim().toLowerCase();
  const list = document.getElementById("appList");
  const apps = state.apps.filter((app) => {
    if (!query) return true;
    return [app.name, app.app_name, app.version].some((value) =>
      String(value || "")
        .toLowerCase()
        .includes(query),
    );
  });
  list.innerHTML = apps
    .map(
      (app) => `
    <button class="app-item ${app.id === state.selectedAppId ? "active" : ""}" data-id="${app.id}" type="button">
      <span class="app-icon">
        <img src="${iconUrl(app)}" alt="" loading="lazy" onerror="this.classList.add('hidden')">
        <span>${fallbackIcon(app)}</span>
      </span>
      <span class="app-meta">
        <strong>${escapeHtml(app.name || app.app_name)}</strong>
        <small>${escapeHtml(app.app_name || "")}</small>
      </span>
    </button>
  `,
    )
    .join("");
}

function fieldInput(source, field) {
  if (field.hidden) return "";
  const value = source?.[field.name] ?? "";
  const attrs = field.readonly
    ? `value="${escapeHtml(value)}" readonly tabindex="-1"`
    : `data-field="${field.name}" value="${escapeHtml(value)}" spellcheck="false"`;
  let tag = `<input ${attrs}>`;
  if (field.type === "bool") {
    const selected = boolValue(value);
    tag = `
      <select ${field.readonly ? 'disabled tabindex="-1"' : `data-field="${field.name}"`} data-kind="bool">
        <option value="true" ${selected ? "selected" : ""}>true</option>
        <option value="false" ${!selected ? "selected" : ""}>false</option>
      </select>
    `;
  } else if (field.options) {
    const selectedValue = String(value || field.options[0] || "");
    tag = `
      <select ${field.readonly ? 'disabled tabindex="-1"' : `data-field="${field.name}"`}>
        ${field.options
          .map(
            (option) =>
              `<option value="${escapeHtml(option)}" ${option === selectedValue ? "selected" : ""}>${escapeHtml(option)}</option>`,
          )
          .join("")}
      </select>
    `;
  } else if (field.textarea) {
    tag = field.readonly
      ? `<textarea readonly tabindex="-1" spellcheck="false">${escapeHtml(value)}</textarea>`
      : `<textarea data-field="${field.name}" spellcheck="false">${escapeHtml(value)}</textarea>`;
  }
  return `<label class="field ${field.textarea ? "wide" : ""}"><span>${escapeHtml(t(field.label))} <small>(${escapeHtml(field.name)})</small></span>${tag}</label>`;
}

function renderAppFields(app) {
  document.getElementById("appFields").innerHTML = appFields
    .map((field) => fieldInput(app, field))
    .join("");
}

function optionLabel(item, index) {
  if (!item) return t("entry", { index: index + 1 });
  return item.service_name || item.k || t("entry", { index: index + 1 });
}

function renderSelect(selectId, items, selectedIndex) {
  const select = document.getElementById(selectId);
  select.innerHTML = items
    .map(
      (item, index) =>
        `<option value="${index}" ${index === selectedIndex ? "selected" : ""}>${escapeHtml(optionLabel(item, index))}</option>`,
    )
    .join("");
  select.disabled = items.length === 0;
}

function renderServiceFields() {
  const services = currentServices();
  state.selectedServiceIndex = Math.min(
    state.selectedServiceIndex,
    Math.max(services.length - 1, 0),
  );
  renderSelect("serviceSelect", services, state.selectedServiceIndex);
  const service = services[state.selectedServiceIndex] || {};
  document.getElementById("serviceFields").innerHTML = serviceFields
    .map((field) =>
      fieldInput(service, {
        ...field,
        hidden: field.name === "id" || field.name === "app_id",
      }),
    )
    .join("");
}

function renderEnvFields() {
  const env = currentEnv();
  state.selectedEnvIndex = Math.min(
    state.selectedEnvIndex,
    Math.max(env.length - 1, 0),
  );
  renderSelect("envSelect", env, state.selectedEnvIndex);
  const item = env[state.selectedEnvIndex] || {};
  document.getElementById("envFields").innerHTML =
    fieldInput(item, {
      name: "id",
      label: "field_id",
      readonly: true,
      hidden: true,
    }) +
    fieldInput(item, {
      name: "app_id",
      label: "field_app_name",
      readonly: true,
      hidden: true,
    }) +
    fieldInput(item, { name: "k", label: "field_k" }) +
    fieldInput(item, { name: "v", label: "field_v" });
}

function renderPrivilege() {
  document.getElementById("runAsSelect").value = currentRunAs();
}

function renderEditor() {
  const app = currentApp();
  const empty = document.getElementById("emptyState");
  const editor = document.getElementById("editor");
  if (!app) {
    empty.textContent = t("emptyApps");
    empty.classList.remove("hidden");
    editor.classList.add("hidden");
    document.getElementById("pageTitle").textContent = t("appConfig");
    return;
  }
  document.getElementById("pageTitle").textContent = t("editorTitle", {
    name: app.name || app.app_name,
  });
  empty.classList.add("hidden");
  editor.classList.remove("hidden");
  renderAppFields(app);
  renderPrivilege();
  renderEnvFields();
  renderServiceFields();
}

function collectFields(container, target) {
  container.querySelectorAll("[data-field]").forEach((input) => {
    target[input.dataset.field] =
      input.dataset.kind === "bool" ? input.value === "true" : input.value;
  });
}

function applyCurrentEdits() {
  const app = currentApp();
  if (!app) return;
  collectFields(document.getElementById("appFields"), app);
  state.runAs[String(app.id)] = document.getElementById("runAsSelect").value;

  const services = currentServices();
  const service = services[state.selectedServiceIndex];
  if (service) {
    collectFields(document.getElementById("serviceFields"), service);
  }

  const env = currentEnv();
  const item = env[state.selectedEnvIndex];
  if (item) collectFields(document.getElementById("envFields"), item);
}

function refreshAll(data) {
  state.apps = data.apps || [];
  state.services = data.services || [];
  state.env = data.env || [];
  state.runAs = data.runAs || {};
  rebuildRestartBaseline();
  if (!state.apps.some((app) => app.id === state.selectedAppId)) {
    state.selectedAppId = state.apps[0]?.id ?? null;
  }
  renderAppList();
  renderEditor();
}

async function loadData() {
  document.getElementById("emptyState").textContent = t("loading");
  const data = await api("list");
  refreshAll(data);
}

async function saveData() {
  if (state.saving) return;
  applyCurrentEdits();
  const app = currentApp();
  if (!app) return;
  setSaving(true);
  try {
    const restart =
      restartSnapshot(app.id) !== state.restartBaseline[String(app.id)];
    const payload = {
      app,
      restart,
    };
    if (restart) {
      payload.runAs = state.runAs[String(app.id)] || "root";
      payload.services = state.services.filter(
        (item) => item.app_id === app.id,
      );
      payload.env = state.env.filter((item) => item.app_id === app.id);
    }
    const data = await api("save", payload);
    refreshAll(data);
    showToast(t("saveSuccess"));
  } finally {
    setSaving(false);
  }
}

function addService() {
  applyCurrentEdits();
  const app = currentApp();
  if (!app) return;
  const existing = new Set(
    currentServices()
      .map((item) => item.service_name)
      .filter(Boolean),
  );
  const item = {
    app_id: app.id,
    service_name: uniqueValue(`${app.app_name}.Application`, existing),
    title: app.name || app.app_name,
    desc: "",
    icon: "ui/images/icon_{0}.png",
    type: "iframe",
    url: "",
    default_url: "",
    is_admin: true,
    control: "",
    full_url: "",
    no_display: false,
    gateway_socket: "",
    gateway_prefix: "",
    file_types: "[]",
    i18n_matadata: "",
  };
  state.services.push(item);
  state.selectedServiceIndex = currentServices().length - 1;
  renderServiceFields();
}

function deleteService() {
  applyCurrentEdits();
  const services = currentServices();
  const item = services[state.selectedServiceIndex];
  if (!item) return;
  if (item.id) item._delete = true;
  else state.services.splice(state.services.indexOf(item), 1);
  state.selectedServiceIndex = Math.max(0, state.selectedServiceIndex - 1);
  renderServiceFields();
}

function addEnv() {
  applyCurrentEdits();
  const app = currentApp();
  if (!app) return;
  const existing = new Set(
    currentEnv()
      .map((item) => item.k)
      .filter(Boolean),
  );
  state.env.push({
    app_id: app.id,
    k: uniqueValue("wizard_key", existing),
    v: "",
  });
  state.selectedEnvIndex = currentEnv().length - 1;
  renderEnvFields();
}

function deleteEnv() {
  applyCurrentEdits();
  const env = currentEnv();
  const item = env[state.selectedEnvIndex];
  if (!item) return;
  if (item.id) item._delete = true;
  else state.env.splice(state.env.indexOf(item), 1);
  state.selectedEnvIndex = Math.max(0, state.selectedEnvIndex - 1);
  renderEnvFields();
}

document.getElementById("appList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-id]");
  if (!button) return;
  applyCurrentEdits();
  state.selectedAppId = Number(button.dataset.id);
  state.selectedServiceIndex = 0;
  state.selectedEnvIndex = 0;
  renderAppList();
  renderEditor();
});

document.getElementById("serviceSelect").addEventListener("change", (event) => {
  applyCurrentEdits();
  state.selectedServiceIndex = Number(event.target.value || 0);
  renderServiceFields();
});

document.getElementById("envSelect").addEventListener("change", (event) => {
  applyCurrentEdits();
  state.selectedEnvIndex = Number(event.target.value || 0);
  renderEnvFields();
});

document.getElementById("searchInput").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderAppList();
});
document.getElementById("runAsSelect").addEventListener("change", (event) => {
  const app = currentApp();
  if (!app) return;
  state.runAs[String(app.id)] =
    event.target.value === "package" ? "package" : "root";
});

document.getElementById("refreshBtn").addEventListener("click", () => {
  loadData()
    .then(() => showToast(t("refreshed")))
    .catch((error) => showToast(error.message, true));
});
document.getElementById("saveBtn").addEventListener("click", () => {
  saveData().catch((error) => showToast(error.message, true));
});
document.getElementById("addServiceBtn").addEventListener("click", addService);
document
  .getElementById("deleteServiceBtn")
  .addEventListener("click", deleteService);
document.getElementById("addEnvBtn").addEventListener("click", addEnv);
document.getElementById("deleteEnvBtn").addEventListener("click", deleteEnv);
document.getElementById("aboutBtn").addEventListener("click", openAbout);
document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", closeModals);
});
document.querySelectorAll(".modal").forEach((modal) => {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModals();
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModals();
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

  try {
    await loadData();
  } catch (error) {
    document.getElementById("emptyState").textContent = error.message;
    showToast(error.message, true);
  }
});
