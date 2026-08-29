const API_ENDPOINT = location.pathname.includes("index.cgi")
  ? "../www/api.cgi"
  : "./api.cgi";
const POLL_INTERVAL = 15000;
const AUDIT_PAGE_SIZE = 20;

const JAIL_TEMPLATES = [
  {
    id: "sshd",
    icon: "🔐",
    name: { "zh-CN": "SSH", "en-US": "SSH" },
    desc: {
      "zh-CN": "SSH 暴力破解防护",
      "en-US": "SSH brute-force protection",
    },
    jailName: "sshd",
    content:
      "[sshd]\nenabled = true\nport = ssh\nfilter = sshd\nlogpath = /var/log/auth.log\nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
  {
    id: "apache",
    icon: "🌐",
    name: { "zh-CN": "Apache", "en-US": "Apache" },
    desc: { "zh-CN": "Apache HTTP 防护", "en-US": "Apache HTTP protection" },
    jailName: "apache-auth",
    content:
      "[apache-auth]\nenabled = true\nport = http,https\nfilter = apache-auth\nlogpath = /var/log/apache2/error.log\nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
  {
    id: "nginx",
    icon: "🛡️",
    name: { "zh-CN": "Nginx", "en-US": "Nginx" },
    desc: { "zh-CN": "Nginx HTTP 防护", "en-US": "Nginx HTTP protection" },
    jailName: "nginx-http-auth",
    content:
      "[nginx-http-auth]\nenabled = true\nport = http,https\nfilter = nginx-http-auth\nlogpath = /var/log/nginx/error.log\nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
  {
    id: "postfix",
    icon: "📧",
    name: { "zh-CN": "Postfix", "en-US": "Postfix" },
    desc: { "zh-CN": "邮件服务防护", "en-US": "Mail service protection" },
    jailName: "postfix",
    content:
      "[postfix]\nenabled = true\nport = smtp\nfilter = postfix\nlogpath = /var/log/mail.log\nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
  {
    id: "dovecot",
    icon: "📬",
    name: { "zh-CN": "Dovecot", "en-US": "Dovecot" },
    desc: { "zh-CN": "IMAP/POP3 防护", "en-US": "IMAP/POP3 protection" },
    jailName: "dovecot",
    content:
      "[dovecot]\nenabled = true\nport = pop3,pop3s,imap,imaps\nfilter = dovecot\nlogpath = /var/log/mail.log\nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
  {
    id: "recidive",
    icon: "🚫",
    name: { "zh-CN": "Recidive", "en-US": "Recidive" },
    desc: { "zh-CN": "重复违规长期封禁", "en-US": "Repeat offender long ban" },
    jailName: "recidive",
    content:
      "[recidive]\nenabled = true\nfilter = recidive\nlogpath = /var/log/fail2ban.log\naction = iptables-allports[name=recidive]\nbantime = 604800\nfindtime = 86400\nmaxretry = 5\n",
  },
  {
    id: "lighttpd",
    icon: "💡",
    name: { "zh-CN": "Lighttpd", "en-US": "Lighttpd" },
    desc: { "zh-CN": "Lighttpd 防护", "en-US": "Lighttpd protection" },
    jailName: "lighttpd-auth",
    content:
      "[lighttpd-auth]\nenabled = true\nport = http,https\nfilter = lighttpd-auth\nlogpath = /var/log/lighttpd/error.log\nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
  {
    id: "custom",
    icon: "✏️",
    name: { "zh-CN": "自定义", "en-US": "Custom" },
    desc: { "zh-CN": "从空白配置开始", "en-US": "Start from blank config" },
    jailName: "",
    content:
      "[jail-name]\nenabled = true\nport = \nfilter = \nlogpath = \nmaxretry = 5\nbantime = 600\nfindtime = 600\n",
  },
];

const I18N = {
  "zh-CN": {
    appTitle: "Fail2Ban 管理",
    subtitle: "入侵防御 · IP 封禁管理",
    about: "关于",
    jails: "Jail 列表",
    searchJail: "搜索 Jail",
    noJails: "暂无 Jail 数据",
    noJailsHint: "点击「新建」创建一个 Jail 规则",
    noBannedIPs: "暂无被封 IP",
    noAuditEntries: "暂无审计记录",
    noLogEntries: "暂无日志",
    btn: {
      new: "新建",
      delete: "删除",
      edit: "编辑",
      reload: "重载",
      refresh: "刷新",
      add: "添加",
      clear: "清空",
      export: "导出",
      import: "导入",
      confirm: "确认",
      cancel: "取消",
      close: "关闭",
      start: "启动",
      stop: "停止",
      toggle: "启用/禁用",
      save: "保存",
      validate: "验证",
      log: "日志",
      audit: "审计",
      custom: "自定义",
      repair: "修复",
    },
    modal: {
      editTitle: "编辑 Jail",
      newTitle: "新建 Jail",
      auditTitle: "审计日志",
      confirm: "确认",
      logTitle: "Fail2Ban 日志",
      unsavedTitle: "未保存的更改",
      unsavedBody: "当前配置已修改但未保存，确认关闭？",
    },
    col: {
      name: "名称",
      state: "状态",
      banned: "当前封禁",
      total: "累计封禁",
      list: "被封 IP",
    },
    state: {
      enabled: "已启用",
      disabled: "已禁用",
      active: "运行中",
      inactive: "未运行",
      running: "运行中",
      stopped: "已停止",
    },
    label: {
      jailName: "Jail 名称",
      jailContent: "配置内容",
      template: "选择模板",
    },
    placeholder: {
      jailName: "输入 Jail 名称",
      jailContent: "在此编辑 / 粘贴 jail 配置",
      banInput: "输入 IP 地址 或 CIDR",
      auditFilter: "筛选（jail / ip / action）",
      logFilter: "筛选日志内容",
    },
    msg: {
      selectFirst: "请先选择一个 Jail",
      deleteConfirm: "确认删除 Jail: {jail} ?",
      toggleConfirm: "确认{action} Jail: {jail} ?",
      toggleEnable: "启用",
      toggleDisable: "禁用",
      deleteSuccess: "删除成功",
      deleteFail: "删除失败",
      saveSuccess: "保存成功",
      saveSuccessWithLogs: "保存成功（已创建日志文件: {logs}）",
      saveFail: "保存失败: {err}",
      reloadSuccess: "重载成功",
      reloadFail: "重载失败: {err}",
      fetchStatusFail: "获取状态失败: {err}",
      nameExists: "名称已存在: {name}",
      formMissing: "配置信息无效，请重新编辑",
      clearSuccess: "清空完成",
      clearFail: "部分操作失败",
      importSuccess: "导入完成",
      importFail: "导入过程中出现错误",
      exportFail: "导出失败",
      multipleJailsDetected: "请保持有且仅有一个 jail 名称！",
      startSuccess: "启动成功",
      startFail: "启动失败: {err}",
      stopSuccess: "停止成功",
      stopFail: "停止失败: {err}",
      toggleSuccess: "操作成功",
      toggleFail: "操作失败: {err}",
      validateOk: "配置格式验证通过",
      validateFail: "配置验证失败: {err}",
      ipCopied: "IP 已复制到剪贴板",
      copyFail: "复制失败",
      logFetchFail: "获取日志失败: {err}",
      invalidIP: "IP 地址格式无效: {ip}",
      banSuccess: "封禁成功",
      banFail: "封禁失败: {err}",
      unbanSuccess: "解封成功",
      unbanFail: "解封失败: {err}",
      validateEmpty: "配置内容为空",
      validateNoSection: "缺少段头（如 [jail-name]）",
      validateBadLine: '第 {line} 行: 缺少 key=value 格式: "{text}"',
      validateLogpathMissing: "日志路径不存在: {path}，请确认后修改",
      repairOk: "配置修复成功，重复段已清理",
      repairOkWithLogs: "配置修复成功（已创建日志文件: {logs}）",
      repairNone: "配置文件无重复段",
      repairFail: "修复失败: {err}",
      warnDuplicateSections: "配置有重复段: {names}",
      warnMissingLog: "日志文件不存在: {path}",
    },
    stat: {
      jails: "Jail 总数",
      enabled: "已启用",
      disabled: "已禁用",
      banned: "当前封禁 IP",
      service: "服务状态",
    },
    audit: {
      time: "时间",
      action: "操作",
      jail: "Jail",
      ip: "IP",
      note: "备注",
      allActions: "全部操作",
      page: "{current} / {total}",
      summary: "共 {total} 条",
    },
    log: { autoRefresh: "自动刷新", allLevels: "全部级别" },
    default: { jailContent: "[DEFAULT]\n" },
    none: "-",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
  },
  "en-US": {
    appTitle: "Fail2Ban Manager",
    subtitle: "Intrusion Prevention · IP Ban Management",
    about: "About",
    jails: "Jails",
    searchJail: "Search Jail",
    noJails: "No jail data",
    noJailsHint: 'Click "New" to create a jail rule',
    noBannedIPs: "No banned IPs",
    noAuditEntries: "No audit entries",
    noLogEntries: "No log entries",
    btn: {
      new: "New",
      delete: "Delete",
      edit: "Edit",
      reload: "Reload",
      refresh: "Refresh",
      add: "Add",
      clear: "Clear",
      export: "Export",
      import: "Import",
      confirm: "Confirm",
      cancel: "Cancel",
      close: "Close",
      start: "Start",
      stop: "Stop",
      toggle: "Enable/Disable",
      save: "Save",
      validate: "Validate",
      log: "Log",
      audit: "Audit",
      custom: "Custom",
      repair: "Repair",
    },
    modal: {
      editTitle: "Edit Jail",
      newTitle: "New Jail",
      auditTitle: "Audit Log",
      confirm: "Confirm",
      logTitle: "Fail2Ban Log",
      unsavedTitle: "Unsaved Changes",
      unsavedBody:
        "Configuration has been modified but not saved. Close anyway?",
    },
    col: {
      name: "Name",
      state: "State",
      banned: "Banned",
      total: "Total Banned",
      list: "Banned IPs",
    },
    state: {
      enabled: "Enabled",
      disabled: "Disabled",
      active: "Active",
      inactive: "Inactive",
      running: "Running",
      stopped: "Stopped",
    },
    label: {
      jailName: "Jail Name",
      jailContent: "Configuration",
      template: "Select Template",
    },
    placeholder: {
      jailName: "Enter jail name",
      jailContent: "Edit / paste jail configuration here",
      banInput: "Enter IP address or CIDR",
      auditFilter: "Filter (jail / ip / action)",
      logFilter: "Filter log content",
    },
    msg: {
      selectFirst: "Please select a jail first",
      deleteConfirm: "Delete jail: {jail} ?",
      toggleConfirm: "{action} jail: {jail} ?",
      toggleEnable: "Enable",
      toggleDisable: "Disable",
      deleteSuccess: "Deleted",
      deleteFail: "Delete failed",
      saveSuccess: "Saved",
      saveSuccessWithLogs: "Saved (log files created: {logs})",
      saveFail: "Save failed: {err}",
      reloadSuccess: "Reload succeeded",
      reloadFail: "Reload failed: {err}",
      fetchStatusFail: "Failed to fetch status: {err}",
      nameExists: "Name already exists: {name}",
      formMissing: "Invalid configuration, please edit again",
      clearSuccess: "Cleared",
      clearFail: "Some operations failed",
      importSuccess: "Import completed",
      importFail: "Import encountered errors",
      exportFail: "Export failed",
      multipleJailsDetected: "Please keep only one jail name!",
      startSuccess: "Started",
      startFail: "Start failed: {err}",
      stopSuccess: "Stopped",
      stopFail: "Stop failed: {err}",
      toggleSuccess: "Operation succeeded",
      toggleFail: "Operation failed: {err}",
      validateOk: "Configuration format validated",
      validateFail: "Validation failed: {err}",
      ipCopied: "IP copied to clipboard",
      copyFail: "Copy failed",
      logFetchFail: "Failed to fetch log: {err}",
      invalidIP: "Invalid IP address format: {ip}",
      banSuccess: "Ban succeeded",
      banFail: "Ban failed: {err}",
      unbanSuccess: "Unban succeeded",
      unbanFail: "Unban failed: {err}",
      validateEmpty: "Configuration is empty",
      validateNoSection: "No section header found (e.g. [jail-name])",
      validateBadLine: 'Line {line}: Missing key=value pair: "{text}"',
      validateLogpathMissing: "Log path does not exist: {path}, please verify",
      repairOk: "Config repaired, duplicate sections cleaned",
      repairOkWithLogs: "Config repaired (log files created: {logs})",
      repairNone: "No duplicate sections found",
      repairFail: "Repair failed: {err}",
      warnDuplicateSections: "Duplicate sections: {names}",
      warnMissingLog: "Log file missing: {path}",
    },
    stat: {
      jails: "Total Jails",
      enabled: "Enabled",
      disabled: "Disabled",
      banned: "Banned IPs",
      service: "Service",
    },
    audit: {
      time: "Time",
      action: "Action",
      jail: "Jail",
      ip: "IP",
      note: "Note",
      allActions: "All Actions",
      page: "{current} / {total}",
      summary: "{total} entries",
    },
    log: { autoRefresh: "Auto Refresh", allLevels: "All Levels" },
    default: { jailContent: "[DEFAULT]\n" },
    none: "-",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
  },
};

const appState = {
  jails: [],
  active: false,
  language: "zh-CN",
  theme: "light",
  selectedJail: null,
  query: "",
  auditEntries: [],
  auditPage: 1,
  editDirty: false,
  configWarnings: [],
  _pollTimer: null,
  _logTimer: null,
};

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_e) {
    return value || "";
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
  } catch (_e) {
    return "";
  }
}

function applyLanguage() {
  const language = safeDecode(navigator.language || "zh-CN").replace("_", "-");
  return language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function applyTheme() {
  const themeMode = parentStoredValue("fnos-theme-mode");
  if (themeMode === "10") return "light";
  if (themeMode === "20") return "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function t(key, params) {
  const keys = key.split(".");
  let value = I18N[appState.language] || I18N["zh-CN"];
  for (const k of keys) {
    if (value && typeof value === "object") value = value[k];
    else {
      value = undefined;
      break;
    }
  }
  if (value === undefined) {
    value = I18N["zh-CN"];
    for (const k of keys) {
      if (value && typeof value === "object") value = value[k];
      else {
        value = key;
        break;
      }
    }
  }
  if (typeof value !== "string") return String(value ?? key);
  if (!params) return value;
  return value.replace(/\{(\w+)\}/g, (_match, name) => params[name] ?? "");
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

function isValidIP(ip) {
  if (!ip || typeof ip !== "string") return false;
  const v = ip.trim();
  if (!v) return false;
  const ipv4 = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
  const ipv6 = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(\/\d{1,3})?$/;
  if (ipv4.test(v)) {
    const parts = v.split("/")[0].split(".");
    return parts.every((p) => {
      const n = parseInt(p, 10);
      return n >= 0 && n <= 255;
    });
  }
  return ipv6.test(v);
}

function applyPreferences({ rerender = false } = {}) {
  const nextLanguage = applyLanguage();
  const nextTheme = applyTheme();
  const languageChanged = nextLanguage !== appState.language;

  appState.language = nextLanguage;
  appState.theme = nextTheme;
  document.documentElement.lang = nextLanguage === "en-US" ? "en-US" : "zh-CN";
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
    node.setAttribute("aria-label", t(node.dataset.i18nTitle));
  });
  document.title = t("appTitle");

  if (rerender && languageChanged) {
    renderApp();
  }
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3200);
}

function showLoading() {
  document.getElementById("loading-overlay")?.classList.remove("hidden");
}

function hideLoading() {
  document.getElementById("loading-overlay")?.classList.add("hidden");
}

async function api(body) {
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify(body),
  });
  return response.json();
}

function copyToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(() => showToast(t("msg.ipCopied")))
        .catch(() => showToast(t("msg.copyFail"), true));
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      showToast(t("msg.ipCopied"));
    }
  } catch (_e) {
    showToast(t("msg.copyFail"), true);
  }
}

function validateJailConfig(content) {
  const errors = [];
  if (!content || !content.trim()) {
    errors.push(t("msg.validateEmpty"));
    return errors;
  }
  const sections = content.match(/^\[.+\]$/gm);
  if (!sections || sections.length === 0) {
    errors.push(t("msg.validateNoSection"));
  }
  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (
      !line ||
      line.startsWith("#") ||
      line.startsWith(";") ||
      line.startsWith("[")
    )
      continue;
    if (!line.includes("=") && !line.includes(":")) {
      errors.push(t("msg.validateBadLine", { line: i + 1, text: line }));
    }
  }
  return errors;
}

function statCard(label, value, tone) {
  return `<div class="stat-card${tone ? ` ${tone}` : ""}"><div class="stat-value">${escapeHtml(value)}</div><div class="stat-label">${escapeHtml(label)}</div></div>`;
}

function renderOverview() {
  const statsNode = document.getElementById("overviewStats");
  if (!statsNode) return;
  const jails = appState.jails || [];
  const enabled = jails.filter((j) => j.enabled).length;
  const disabled = jails.length - enabled;
  const totalBanned = jails.reduce(
    (sum, j) => sum + (parseInt(j.curBan, 10) || 0),
    0,
  );
  statsNode.innerHTML = [
    statCard(
      t("stat.service"),
      appState.active ? t("state.running") : t("state.stopped"),
      appState.active ? "ok" : "danger",
    ),
    statCard(t("stat.jails"), String(jails.length)),
    statCard(t("stat.enabled"), String(enabled), enabled ? "ok" : ""),
    statCard(t("stat.disabled"), String(disabled), disabled ? "warn" : ""),
    statCard(t("stat.banned"), String(totalBanned), totalBanned ? "info" : ""),
  ].join("");
}

function renderServiceStatus() {
  const statusEl = document.getElementById("serviceStatus");
  const btnEl = document.getElementById("btn-startstop");
  if (!statusEl || !btnEl) return;

  if (appState.active) {
    statusEl.className = "service-status running";
    statusEl.innerHTML = `<span class="service-status-dot"></span>${escapeHtml(t("state.running"))}`;
    btnEl.textContent = t("btn.stop");
    btnEl.className = "btn warn";
  } else {
    statusEl.className = "service-status stopped";
    statusEl.innerHTML = `<span class="service-status-dot"></span>${escapeHtml(t("state.stopped"))}`;
    btnEl.textContent = t("btn.start");
    btnEl.className = "btn secondary";
  }
}

function filteredJails() {
  const q = appState.query.trim().toLowerCase();
  if (!q) return appState.jails || [];
  return (appState.jails || []).filter((j) =>
    (j.name || "").toLowerCase().includes(q),
  );
}

function renderJailTable() {
  const jails = filteredJails();
  const emptyEl = document.getElementById("jailEmpty");
  const wrapEl = document.getElementById("jailTableWrap");
  const tbody = document.getElementById("jail-tbody");

  if (!jails.length) {
    emptyEl.classList.remove("hidden");
    wrapEl.classList.add("hidden");
    return;
  }
  emptyEl.classList.add("hidden");
  wrapEl.classList.remove("hidden");

  tbody.innerHTML = jails
    .map((j) => {
      const selected = appState.selectedJail === j.name ? " selected" : "";
      const stateBadge = j.enabled
        ? `<span class="badge"><span class="badge-dot"></span>${escapeHtml(t("state.enabled"))}</span>`
        : `<span class="badge subtle"><span class="badge-dot"></span>${escapeHtml(t("state.disabled"))}</span>`;
      const curBan = j.curBan != null ? j.curBan : "0";
      const tolBan = j.tolBan != null ? j.tolBan : "0";
      const curBanNum = parseInt(curBan, 10) || 0;
      const banDisplay =
        curBanNum > 0
          ? `<span class="badge danger">${escapeHtml(curBan)}</span>`
          : escapeHtml(curBan);
      return `<tr class="table-row${selected}" data-jail="${escapeHtml(j.name)}" tabindex="0" role="row">
      <td class="mono">${escapeHtml(j.name)}</td>
      <td>${stateBadge}</td>
      <td>${banDisplay}</td>
      <td>${escapeHtml(tolBan)}</td>
      <td><button class="btn secondary small" data-ban-jail="${escapeHtml(j.name)}">${escapeHtml(t("col.list"))}</button></td>
    </tr>`;
    })
    .join("");

  tbody.querySelectorAll("tr.table-row").forEach((tr) => {
    tr.addEventListener("click", (e) => {
      if (e.target.closest("[data-ban-jail]")) return;
      selectJail(tr.dataset.jail);
    });
    tr.addEventListener("dblclick", (e) => {
      if (e.target.closest("[data-ban-jail]")) return;
      selectJail(tr.dataset.jail);
      readSelectedJail().then((res) => {
        if (res && res.success)
          showEditModal(appState.selectedJail, res.content || "");
      });
    });
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.target.closest("[data-ban-jail]")) {
        selectJail(tr.dataset.jail);
      }
    });
  });

  tbody.querySelectorAll("[data-ban-jail]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const jailName = btn.dataset.banJail;
      const jail = appState.jails.find((j) => j.name === jailName);
      openBanModal(jailName, jail ? jail.banIPs : "");
    });
  });
}

function selectJail(name) {
  appState.selectedJail = name;
  renderJailTable();
  updateToolbar();
}

function updateToolbar() {
  const hasSelection = !!appState.selectedJail;
  const btnEdit = document.getElementById("btn-edit");
  const btnDelete = document.getElementById("btn-delete");
  const btnToggle = document.getElementById("btn-toggle");
  if (btnEdit) btnEdit.disabled = !hasSelection;
  if (btnDelete) btnDelete.disabled = !hasSelection;
  if (btnToggle) btnToggle.disabled = !hasSelection;
}

function renderApp() {
  renderOverview();
  renderServiceStatus();
  renderJailTable();
  updateToolbar();
}

async function fetchStatus() {
  try {
    const data = await api({ action: "status" });
    appState.jails = data.jails || [];
    appState.active = data.active || false;
    appState.configWarnings = data.config_warnings || [];
    if (!appState.jails.some((j) => j.name === appState.selectedJail)) {
      appState.selectedJail = null;
    }
    renderApp();
    renderConfigWarnings();
  } catch (e) {
    showToast(t("msg.fetchStatusFail", { err: (e && e.message) || "" }), true);
  }
}

function renderConfigWarnings() {
  const container = document.getElementById("config-warnings");
  if (!container) return;
  const warnings = appState.configWarnings || [];
  if (warnings.length === 0) {
    container.classList.add("hidden");
    container.innerHTML = "";
    return;
  }
  container.classList.remove("hidden");
  const items = warnings
    .map((w) => {
      if (w.startsWith("duplicate_sections:")) {
        const names = w.split(":", 2)[1];
        return `<span class="warning-item">⚠️ ${t("msg.warnDuplicateSections", { names })}</span>`;
      }
      if (w.startsWith("missing_log:")) {
        const path = w.split(":", 2)[1];
        return `<span class="warning-item">⚠️ ${t("msg.warnMissingLog", { path })}</span>`;
      }
      return "";
    })
    .filter(Boolean)
    .join("");
  container.innerHTML = `<div class="warning-banner">${items}<button class="btn secondary small" id="btn-repair-inline" data-i18n="btn.repair">修复</button></div>`;
  document
    .getElementById("btn-repair-inline")
    ?.addEventListener("click", repairConfig);
}

function startPolling() {
  stopPolling();
  appState._pollTimer = setInterval(fetchStatus, POLL_INTERVAL);
}

function stopPolling() {
  if (appState._pollTimer) {
    clearInterval(appState._pollTimer);
    appState._pollTimer = null;
  }
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
  const focusable = modal.querySelectorAll(
    'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])',
  );
  const items = Array.from(focusable).filter(
    (el) => !el.hasAttribute("disabled"),
  );
  if (items.length) items[0].focus();

  modal._keyHandler = (e) => {
    if (e.key === "Escape") closeModal(id);
    if (e.key === "Tab") {
      if (!items.length) return;
      const idx = items.indexOf(document.activeElement);
      if (e.shiftKey) {
        if (idx === 0) {
          e.preventDefault();
          items[items.length - 1].focus();
        }
      } else {
        if (idx === items.length - 1) {
          e.preventDefault();
          items[0].focus();
        }
      }
    }
  };
  document.addEventListener("keydown", modal._keyHandler);

  modal._backdropHandler = (e) => {
    if (e.target === modal) closeModal(id);
  };
  modal.addEventListener("click", modal._backdropHandler);
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add("hidden");
  document.body.style.overflow = "";
  if (modal._keyHandler) {
    document.removeEventListener("keydown", modal._keyHandler);
    delete modal._keyHandler;
  }
  if (modal._backdropHandler) {
    modal.removeEventListener("click", modal._backdropHandler);
    delete modal._backdropHandler;
  }
}

function showConfirm(message, onYes, onNo) {
  const body = document.getElementById("confirm-body");
  const btnOk = document.getElementById("confirm-ok");
  const btnCancel = document.getElementById("confirm-cancel");
  const btnClose = document.getElementById("confirm-close");
  body.textContent = message;

  const cleanup = () => {
    btnOk.onclick = null;
    btnCancel.onclick = null;
    btnClose.onclick = null;
    closeModal("modal-confirm");
  };

  btnOk.onclick = () => {
    cleanup();
    if (typeof onYes === "function") onYes();
  };
  btnCancel.onclick = () => {
    cleanup();
    if (typeof onNo === "function") onNo();
  };
  btnClose.onclick = () => {
    cleanup();
    if (typeof onNo === "function") onNo();
  };

  openModal("modal-confirm");
}

function renderTemplateGrid() {
  const grid = document.getElementById("template-grid");
  if (!grid) return;
  const lang = appState.language;
  grid.innerHTML = JAIL_TEMPLATES.map((tpl) => {
    const tplName = tpl.name[lang] || tpl.name["en-US"];
    const tplDesc = tpl.desc[lang] || tpl.desc["en-US"];
    return `<div class="template-card" data-template-id="${escapeHtml(tpl.id)}" tabindex="0" role="button" aria-label="${escapeHtml(tplName)}">
      <span class="template-card-icon">${tpl.icon}</span>
      <span class="template-card-name">${escapeHtml(tplName)}</span>
      <span class="template-card-desc">${escapeHtml(tplDesc)}</span>
    </div>`;
  }).join("");

  grid.querySelectorAll(".template-card").forEach((card) => {
    card.addEventListener("click", () =>
      selectTemplate(card.dataset.templateId),
    );
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectTemplate(card.dataset.templateId);
      }
    });
  });
}

function selectTemplate(templateId) {
  const tpl = JAIL_TEMPLATES.find((t) => t.id === templateId);
  if (!tpl) return;

  const grid = document.getElementById("template-grid");
  if (grid) {
    grid
      .querySelectorAll(".template-card")
      .forEach((c) => c.classList.remove("selected"));
    const selected = grid.querySelector(`[data-template-id="${templateId}"]`);
    if (selected) selected.classList.add("selected");
  }

  const nameEl = document.getElementById("jail-name");
  const contentEl = document.getElementById("jail-content");
  if (nameEl && !nameEl.readOnly) {
    nameEl.value = tpl.jailName || "";
  }
  if (contentEl) {
    contentEl.value = tpl.content || "";
  }

  appState.editDirty = false;
  appState._editOriginal = contentEl ? contentEl.value : "";
}

function showEditModal(name, content) {
  const nameEl = document.getElementById("jail-name");
  const contentEl = document.getElementById("jail-content");
  const titleEl = document.getElementById("modal-title");
  const errorEl = document.getElementById("modal-error");
  const saveBtn = document.getElementById("modal-save");
  const templateSection = document.getElementById("template-section");

  const isNew = !name;
  titleEl.textContent = isNew ? t("modal.newTitle") : t("modal.editTitle");

  if (templateSection) {
    templateSection.classList.toggle("hidden", !isNew);
  }

  if (isNew) {
    renderTemplateGrid();
  }

  if (nameEl) {
    nameEl.value = name || "";
    nameEl.readOnly = !!(name && name.trim());
  }

  let displayContent = content || "";
  if (name && displayContent && !/^\[.+\]/m.test(displayContent)) {
    displayContent = `[${name}]\n` + displayContent;
  }
  if (contentEl) contentEl.value = displayContent;
  if (errorEl) {
    errorEl.textContent = "";
    errorEl.className = "form-error";
  }
  if (saveBtn) saveBtn.disabled = false;

  appState.editDirty = false;
  appState._editOriginal = contentEl ? contentEl.value : "";

  openModal("modal-edit");
}

function hideEditModal() {
  const contentEl = document.getElementById("jail-content");
  const current = contentEl ? contentEl.value : "";
  if (appState.editDirty && current !== appState._editOriginal) {
    showConfirm(t("modal.unsavedBody"), () => {
      appState.editDirty = false;
      closeModal("modal-edit");
    });
    return;
  }
  closeModal("modal-edit");
}

async function validateConfig() {
  const contentEl = document.getElementById("jail-content");
  const errorEl = document.getElementById("modal-error");
  if (!contentEl || !errorEl) return;

  const errors = validateJailConfig(contentEl.value);
  if (errors.length > 0) {
    errorEl.textContent = t("msg.validateFail", { err: errors.join("; ") });
    errorEl.className = "form-error";
    return;
  }

  const logpathMatch = contentEl.value.match(/^logpath\s*=\s*(.+)$/m);
  if (logpathMatch) {
    const logpath = logpathMatch[1].trim();
    try {
      const res = await api({ action: "check_logpath", paths: [logpath] });
      if (res && res.success && res.results && !res.results[logpath]) {
        errorEl.textContent = t("msg.validateLogpathMissing", {
          path: logpath,
        });
        errorEl.className = "form-error";
        return;
      }
    } catch (_) {}
  }

  errorEl.textContent = t("msg.validateOk");
  errorEl.className = "form-success";
}

async function saveJail() {
  const nameEl = document.getElementById("jail-name");
  const contentEl = document.getElementById("jail-content");
  if (!nameEl || !contentEl) {
    showToast(t("msg.formMissing"), true);
    return;
  }
  const name = (nameEl.value || "").trim();
  const rawContent = contentEl.value || "";
  if (!name) {
    showToast(t("msg.formMissing"), true);
    return;
  }
  const exists = appState.jails.some((j) => j.name === name);
  if (exists && name !== appState.selectedJail) {
    showToast(t("msg.nameExists", { name }), true);
    return;
  }
  const bodyContent = rawContent.replace(/^\[.+\]\s*\n?/m, "");
  try {
    const res = await api({
      action: "write",
      jail: name,
      content: bodyContent,
    });
    if (res && res.success) {
      appState.editDirty = false;
      closeModal("modal-edit");
      if (res.created_logs && res.created_logs.length > 0) {
        showToast(
          t("msg.saveSuccessWithLogs", { logs: res.created_logs.join(", ") }),
        );
      } else {
        showToast(t("msg.saveSuccess"));
      }
      fetchStatus();
    } else {
      showToast((res && res.message) || t("msg.saveFail", { err: "" }), true);
    }
  } catch (e) {
    showToast(t("msg.saveFail", { err: (e && e.message) || "" }), true);
  }
}

async function deleteJail() {
  if (!appState.selectedJail) {
    showToast(t("msg.selectFirst"), true);
    return;
  }
  showConfirm(
    t("msg.deleteConfirm", { jail: appState.selectedJail }),
    async () => {
      try {
        const res = await api({
          action: "delete",
          jail: appState.selectedJail,
        });
        if (res && res.success) {
          showToast(t("msg.deleteSuccess"));
          appState.selectedJail = null;
          fetchStatus();
        } else {
          showToast((res && res.message) || t("msg.deleteFail"), true);
        }
      } catch (e) {
        showToast(t("msg.deleteFail") + ": " + ((e && e.message) || ""), true);
      }
    },
  );
}

async function toggleJail() {
  if (!appState.selectedJail) {
    showToast(t("msg.selectFirst"), true);
    return;
  }
  const jail = appState.jails.find((j) => j.name === appState.selectedJail);
  if (!jail) return;
  const action = jail.enabled ? t("msg.toggleDisable") : t("msg.toggleEnable");
  showConfirm(
    t("msg.toggleConfirm", { action, jail: appState.selectedJail }),
    async () => {
      try {
        const res = await api({
          action: "toggle",
          jail: appState.selectedJail,
          enabled: !jail.enabled,
        });
        if (res && res.success) {
          showToast(t("msg.toggleSuccess"));
          fetchStatus();
        } else {
          showToast(
            t("msg.toggleFail", { err: (res && res.message) || "" }),
            true,
          );
        }
      } catch (e) {
        showToast(t("msg.toggleFail", { err: (e && e.message) || "" }), true);
      }
    },
  );
}

async function reloadFail2ban() {
  try {
    const res = await api({ action: "reload" });
    if (res && res.success) showToast(t("msg.reloadSuccess"));
    else
      showToast(t("msg.reloadFail", { err: (res && res.message) || "" }), true);
    fetchStatus();
  } catch (e) {
    showToast(t("msg.reloadFail", { err: (e && e.message) || "" }), true);
  }
}

async function repairConfig() {
  try {
    const res = await api({ action: "repair" });
    if (res && res.success) {
      if (res.duplicates && res.duplicates.length > 0) {
        if (res.created_logs && res.created_logs.length > 0) {
          showToast(
            t("msg.repairOkWithLogs", { logs: res.created_logs.join(", ") }),
          );
        } else {
          showToast(t("msg.repairOk"));
        }
      } else {
        showToast(t("msg.repairNone"));
      }
    } else {
      showToast(t("msg.repairFail", { err: (res && res.message) || "" }), true);
    }
    fetchStatus();
  } catch (e) {
    showToast(t("msg.repairFail", { err: (e && e.message) || "" }), true);
  }
}

async function startStopService() {
  const action = appState.active ? "stop" : "start";
  try {
    const res = await api({ action });
    if (res && res.success) {
      showToast(appState.active ? t("msg.stopSuccess") : t("msg.startSuccess"));
      fetchStatus();
    } else {
      showToast(
        appState.active
          ? t("msg.stopFail")
          : t("msg.startFail", { err: (res && res.message) || "" }),
        true,
      );
    }
  } catch (e) {
    showToast(
      appState.active
        ? t("msg.stopFail")
        : t("msg.startFail", { err: (e && e.message) || "" }),
      true,
    );
  }
}

async function readSelectedJail() {
  if (!appState.selectedJail) {
    showToast(t("msg.selectFirst"), true);
    return null;
  }
  try {
    const res = await api({ action: "read", jail: appState.selectedJail });
    return res;
  } catch (e) {
    showToast(t("msg.fetchStatusFail", { err: (e && e.message) || "" }), true);
    return null;
  }
}

function parseBanIPs(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.slice();
  return raw
    .toString()
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function openBanModal(jailName, banIPsRaw) {
  const listEl = document.getElementById("ban-list");
  const input = document.getElementById("ban-input");
  const addBtn = document.getElementById("ban-add");
  const titleEl = document.getElementById("modal-ban-title");
  const emptyEl = document.getElementById("ban-empty");

  titleEl.textContent = `${jailName} - ${t("col.list")}`;
  listEl.innerHTML = "";
  const items = parseBanIPs(banIPsRaw);

  if (emptyEl) emptyEl.classList.toggle("hidden", items.length > 0);

  function renderBanItem(ip) {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.className = "ip-text";
    span.textContent = ip;
    span.title = t("msg.ipCopied");
    span.addEventListener("click", () => copyToClipboard(ip));
    const del = document.createElement("button");
    del.className = "btn danger small";
    del.textContent = t("btn.delete");
    del.addEventListener("click", () => {
      api({ action: "unban", jail: jailName, ip })
        .then((res) => {
          if (res && res.success) {
            showToast(t("msg.unbanSuccess"));
            fetchStatus();
            li.remove();
            const remaining = listEl.querySelectorAll("li").length;
            if (emptyEl) emptyEl.classList.toggle("hidden", remaining > 0);
          } else {
            showToast(
              t("msg.unbanFail", { err: (res && res.message) || "" }),
              true,
            );
          }
        })
        .catch((e) => {
          showToast(t("msg.unbanFail", { err: (e && e.message) || "" }), true);
        });
    });
    li.appendChild(span);
    li.appendChild(del);
    listEl.appendChild(li);
  }

  items.forEach(renderBanItem);

  input.value = "";
  if (addBtn._handler) {
    addBtn.removeEventListener("click", addBtn._handler);
  }
  addBtn._handler = () => {
    const val = (input.value || "").trim();
    if (!val) return;
    if (!isValidIP(val)) {
      showToast(t("msg.invalidIP", { ip: val }), true);
      return;
    }
    api({ action: "ban", jail: jailName, ip: val })
      .then((res) => {
        if (res && res.success) {
          showToast(t("msg.banSuccess"));
          fetchStatus();
          input.value = "";
          renderBanItem(val);
          if (emptyEl) emptyEl.classList.toggle("hidden", true);
        } else {
          showToast(
            t("msg.banFail", { err: (res && res.message) || "" }),
            true,
          );
        }
      })
      .catch((e) => {
        showToast(t("msg.banFail", { err: (e && e.message) || "" }), true);
      });
  };
  addBtn.addEventListener("click", addBtn._handler);

  input.onkeydown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addBtn._handler();
    }
  };

  const closeBtn = document.getElementById("modal-ban-close");
  if (closeBtn) closeBtn.onclick = () => closeModal("modal-ban");

  const exportBtn = document.getElementById("ban-export");
  if (exportBtn)
    exportBtn.onclick = () => {
      try {
        const ips = Array.from(listEl.querySelectorAll(".ip-text")).map(
          (el) => el.textContent,
        );
        const blob = new Blob([JSON.stringify(ips, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${jailName}_banned_ips.json`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        showToast(t("msg.exportFail"), true);
      }
    };

  const importBtn = document.getElementById("ban-import");
  const importFile = document.getElementById("ban-import-file");
  if (importBtn && importFile) {
    importBtn.onclick = () => importFile.click();
    importFile.onchange = () => {
      const file = importFile.files && importFile.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          let ips = [];
          const text = reader.result || "";
          if (file.name.endsWith(".json")) {
            const parsed = JSON.parse(text);
            ips = Array.isArray(parsed) ? parsed : [];
          } else {
            ips = text
              .split(/[\r\n,;]+/)
              .map((s) => s.trim())
              .filter(Boolean);
          }
          if (!ips.length) return;
          api({ action: "bulkban", jail: jailName, ips })
            .then((res) => {
              if (res && res.success) {
                showToast(t("msg.importSuccess"));
                fetchStatus();
                closeModal("modal-ban");
              } else {
                showToast(t("msg.importFail"), true);
              }
            })
            .catch(() => showToast(t("msg.importFail"), true));
        } catch (e) {
          showToast(t("msg.importFail"), true);
        }
      };
      reader.readAsText(file);
      importFile.value = "";
    };
  }

  const clearBtn = document.getElementById("ban-clear");
  if (clearBtn) {
    clearBtn.onclick = () => {
      showConfirm(t("btn.clear") + " ?", () => {
        api({ action: "clear", jail: jailName })
          .then((res) => {
            if (res && res.success) {
              showToast(res.message || t("msg.clearSuccess"));
              fetchStatus();
              listEl.innerHTML = "";
              if (emptyEl) emptyEl.classList.toggle("hidden", false);
            } else {
              showToast(
                res && res.message ? res.message : t("msg.clearFail"),
                true,
              );
            }
          })
          .catch((e) =>
            showToast(
              t("msg.clearFail") + ": " + ((e && e.message) || ""),
              true,
            ),
          );
      });
    };
  }

  openModal("modal-ban");
}

function formatAuditTime(ts) {
  if (!ts) return "-";
  try {
    const d = new Date(ts.endsWith("Z") ? ts : ts + "Z");
    if (isNaN(d.getTime())) return ts;
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch (_e) {
    return ts;
  }
}

function auditActionBadge(action) {
  const a = (action || "").toLowerCase();
  const cls = [
    "ban",
    "unban",
    "write",
    "delete",
    "reload",
    "start",
    "stop",
    "toggle",
    "clear_unban",
  ].includes(a)
    ? a
    : "other";
  return `<span class="audit-action-badge ${cls}">${escapeHtml(action || "-")}</span>`;
}

function openAuditModal() {
  let filterText = "";
  let filterAction = "";
  appState.auditPage = 1;

  async function fetchAndRender() {
    try {
      const res = await api({
        action: "audit",
        filter: filterText,
        limit: 500,
      });
      if (res && res.success) {
        let entries = res.entries || [];
        appState.auditEntries = entries;
        if (filterAction) {
          entries = entries.filter((e) =>
            (e.action || "").toLowerCase().includes(filterAction.toLowerCase()),
          );
        }
        renderAuditTable(entries);
      }
    } catch (e) {
      showToast(
        t("msg.fetchStatusFail", { err: (e && e.message) || "" }),
        true,
      );
    }
  }

  function renderAuditTable(entries) {
    const tbody = document.getElementById("audit-tbody");
    const emptyEl = document.getElementById("audit-empty");
    const pagerEl = document.getElementById("audit-pager");
    const summaryEl = document.getElementById("audit-summary");
    const pageInfoEl = document.getElementById("audit-page-info");
    const prevBtn = document.getElementById("audit-prev");
    const nextBtn = document.getElementById("audit-next");
    if (!tbody) return;

    const total = entries.length;
    const totalPages = Math.max(1, Math.ceil(total / AUDIT_PAGE_SIZE));

    if (appState.auditPage > totalPages) appState.auditPage = totalPages;
    if (appState.auditPage < 1) appState.auditPage = 1;

    const startIdx = (appState.auditPage - 1) * AUDIT_PAGE_SIZE;
    const pageEntries = entries.slice(startIdx, startIdx + AUDIT_PAGE_SIZE);

    if (!total) {
      tbody.innerHTML = "";
      if (emptyEl) emptyEl.classList.remove("hidden");
      if (pagerEl) pagerEl.classList.add("hidden");
      return;
    }
    if (emptyEl) emptyEl.classList.add("hidden");

    tbody.innerHTML = pageEntries
      .reverse()
      .map(
        (e) => `<tr>
      <td class="audit-time">${escapeHtml(formatAuditTime(e.ts))}</td>
      <td>${auditActionBadge(e.action)}</td>
      <td class="mono">${escapeHtml(e.jail || "-")}</td>
      <td class="audit-ip">${escapeHtml(e.ip || "-")}</td>
      <td class="audit-note" title="${escapeHtml(e.note || "")}">${escapeHtml(e.note || "-")}</td>
    </tr>`,
      )
      .join("");

    if (pagerEl) {
      pagerEl.classList.toggle("hidden", totalPages <= 1);
    }
    if (summaryEl) {
      summaryEl.textContent = t("audit.summary", { total });
    }
    if (pageInfoEl) {
      pageInfoEl.textContent = t("audit.page", {
        current: appState.auditPage,
        total: totalPages,
      });
    }
    if (prevBtn) prevBtn.disabled = appState.auditPage <= 1;
    if (nextBtn) nextBtn.disabled = appState.auditPage >= totalPages;
  }

  const filterInput = document.getElementById("audit-filter");
  const actionFilter = document.getElementById("audit-action-filter");
  const refreshBtn = document.getElementById("audit-refresh");

  if (filterInput) {
    filterInput.value = "";
    let debounceTimer;
    filterInput.oninput = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        filterText = filterInput.value;
        appState.auditPage = 1;
        fetchAndRender();
      }, 300);
    };
  }
  if (actionFilter) {
    actionFilter.value = "";
    actionFilter.onchange = () => {
      filterAction = actionFilter.value;
      appState.auditPage = 1;
      fetchAndRender();
    };
  }
  if (refreshBtn) refreshBtn.onclick = fetchAndRender;

  const prevBtn = document.getElementById("audit-prev");
  const nextBtn = document.getElementById("audit-next");
  if (prevBtn)
    prevBtn.onclick = () => {
      appState.auditPage--;
      fetchAndRender();
    };
  if (nextBtn)
    nextBtn.onclick = () => {
      appState.auditPage++;
      fetchAndRender();
    };

  const exportBtn = document.getElementById("audit-export");
  if (exportBtn)
    exportBtn.onclick = () => {
      try {
        const blob = new Blob(
          [JSON.stringify(appState.auditEntries, null, 2)],
          { type: "application/json" },
        );
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "fail2ban_audit.json";
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        showToast(t("msg.exportFail"), true);
      }
    };

  const clearBtn = document.getElementById("audit-clear");
  if (clearBtn) {
    clearBtn.onclick = () => {
      showConfirm(t("btn.clear") + " ?", () => {
        api({ action: "audit_clear" })
          .then((res) => {
            if (res && res.success) {
              showToast(res.message || t("msg.clearSuccess"));
              appState.auditEntries = [];
              renderAuditTable([]);
            } else
              showToast(
                res && res.message ? res.message : t("msg.clearFail"),
                true,
              );
          })
          .catch((e) =>
            showToast(
              t("msg.clearFail") + ": " + ((e && e.message) || ""),
              true,
            ),
          );
      });
    };
  }

  const closeBtn = document.getElementById("modal-audit-close");
  if (closeBtn) closeBtn.onclick = () => closeModal("modal-audit");

  openModal("modal-audit");
  fetchAndRender();
}

function openLogModal() {
  let logFilter = "";
  let logLevel = "";
  let logLines = 100;
  let autoRefresh = false;

  const filterInput = document.getElementById("log-filter");
  const levelSelect = document.getElementById("log-level");
  const linesSelect = document.getElementById("log-lines");
  const refreshBtn = document.getElementById("log-refresh");
  const autoRefreshCb = document.getElementById("log-autorefresh");
  const contentEl = document.getElementById("log-content");
  const emptyEl = document.getElementById("log-empty");
  const closeBtn = document.getElementById("modal-log-close");
  const exportBtn = document.getElementById("log-export");

  if (filterInput) {
    filterInput.value = "";
  }
  if (levelSelect) {
    levelSelect.value = "";
  }
  if (linesSelect) {
    linesSelect.value = "100";
  }
  if (autoRefreshCb) {
    autoRefreshCb.checked = false;
  }

  function colorizeLine(line) {
    const upper = line.toUpperCase();
    if (
      upper.includes("ERROR") ||
      upper.includes("CRITICAL") ||
      upper.includes("FATAL")
    )
      return "log-error";
    if (upper.includes("WARNING") || upper.includes("WARN")) return "log-warn";
    if (upper.includes("INFO")) return "log-info";
    if (upper.includes("DEBUG")) return "log-debug";
    return "";
  }

  async function fetchLog() {
    try {
      const res = await api({ action: "log", lines: logLines });
      if (res && res.success && res.lines) {
        let lines = res.lines;
        if (logLevel) {
          lines = lines.filter((l) =>
            l.toUpperCase().includes(logLevel.toUpperCase()),
          );
        }
        if (logFilter) {
          const q = logFilter.toLowerCase();
          lines = lines.filter((l) => l.toLowerCase().includes(q));
        }
        if (!lines.length) {
          contentEl.innerHTML = "";
          if (emptyEl) emptyEl.classList.remove("hidden");
        } else {
          if (emptyEl) emptyEl.classList.add("hidden");
          contentEl.innerHTML = lines
            .map((l) => {
              const cls = colorizeLine(l);
              return `<span class="log-line${cls ? ` ${cls}` : ""}">${escapeHtml(l)}</span>`;
            })
            .join("");
          const container = document.getElementById("log-container");
          if (container) container.scrollTop = container.scrollHeight;
        }
      } else {
        contentEl.innerHTML = "";
        if (emptyEl) emptyEl.classList.remove("hidden");
      }
    } catch (e) {
      showToast(t("msg.logFetchFail", { err: (e && e.message) || "" }), true);
    }
  }

  function startLogPolling() {
    stopLogPolling();
    if (autoRefresh) {
      appState._logTimer = setInterval(fetchLog, 3000);
    }
  }

  function stopLogPolling() {
    if (appState._logTimer) {
      clearInterval(appState._logTimer);
      appState._logTimer = null;
    }
  }

  if (filterInput) {
    let debounce;
    filterInput.oninput = () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        logFilter = filterInput.value;
        fetchLog();
      }, 300);
    };
  }

  if (levelSelect) {
    levelSelect.onchange = () => {
      logLevel = levelSelect.value;
      fetchLog();
    };
  }

  if (linesSelect) {
    linesSelect.onchange = () => {
      logLines = parseInt(linesSelect.value, 10) || 100;
      fetchLog();
    };
  }

  if (refreshBtn) refreshBtn.onclick = fetchLog;

  if (autoRefreshCb) {
    autoRefreshCb.onchange = () => {
      autoRefresh = autoRefreshCb.checked;
      startLogPolling();
    };
  }

  if (closeBtn) {
    closeBtn.onclick = () => {
      stopLogPolling();
      closeModal("modal-log");
    };
  }

  if (exportBtn) {
    exportBtn.onclick = () => {
      try {
        const text = contentEl.textContent || "";
        const blob = new Blob([text], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "fail2ban.log";
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        showToast(t("msg.exportFail"), true);
      }
    };
  }

  openModal("modal-log");
  fetchLog();
}

function closeAboutModal() {
  closeModal("modal-about");
}

document.addEventListener("DOMContentLoaded", () => {
  applyPreferences();
  fetchStatus();
  startPolling();

  document
    .getElementById("btn-refresh")
    ?.addEventListener("click", fetchStatus);
  document
    .getElementById("btn-new")
    ?.addEventListener("click", () => showEditModal("", ""));
  document.getElementById("btn-edit")?.addEventListener("click", async () => {
    const res = await readSelectedJail();
    if (res && res.success) {
      showEditModal(appState.selectedJail, res.content || "");
    }
  });
  document.getElementById("btn-toggle")?.addEventListener("click", toggleJail);
  document.getElementById("btn-delete")?.addEventListener("click", deleteJail);
  document
    .getElementById("btn-reload")
    ?.addEventListener("click", reloadFail2ban);
  document
    .getElementById("btn-repair")
    ?.addEventListener("click", repairConfig);
  document
    .getElementById("btn-startstop")
    ?.addEventListener("click", startStopService);
  document
    .getElementById("btn-audit")
    ?.addEventListener("click", openAuditModal);
  document.getElementById("btn-log")?.addEventListener("click", openLogModal);
  document
    .getElementById("btn-about")
    ?.addEventListener("click", () => openModal("modal-about"));
  document
    .getElementById("btn-validate")
    ?.addEventListener("click", validateConfig);

  document
    .getElementById("btn-skip-template")
    ?.addEventListener("click", () => {
      const templateSection = document.getElementById("template-section");
      if (templateSection) templateSection.classList.add("hidden");
    });

  document.getElementById("modal-save")?.addEventListener("click", saveJail);
  document
    .getElementById("modal-cancel")
    ?.addEventListener("click", hideEditModal);
  document
    .getElementById("modal-cancel2")
    ?.addEventListener("click", hideEditModal);

  document.getElementById("jail-name")?.addEventListener("input", (e) => {
    appState.editDirty = true;
    const name = (e.target.value || "").trim();
    const contentEl = document.getElementById("jail-content");
    if (contentEl && name) {
      contentEl.value = contentEl.value.replace(/^\[.+\]/m, `[${name}]`);
    }
  });

  document.getElementById("jail-content")?.addEventListener("input", () => {
    appState.editDirty = true;
  });

  document.getElementById("searchInput")?.addEventListener("input", (e) => {
    appState.query = e.target.value || "";
    renderJailTable();
  });

  document.querySelectorAll("#modal-about [data-close]").forEach((btn) => {
    btn.addEventListener("click", closeAboutModal);
  });

  window
    .matchMedia?.("(prefers-color-scheme: dark)")
    .addEventListener("change", () => {
      applyPreferences({ rerender: true });
    });

  window.addEventListener("storage", () => {
    applyPreferences({ rerender: true });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "F5" || (e.ctrlKey && e.key === "r")) {
      e.preventDefault();
      fetchStatus();
    }
    if (e.ctrlKey && e.key === "n") {
      e.preventDefault();
      showEditModal("", "");
    }
    if (
      e.key === "Delete" &&
      appState.selectedJail &&
      !document.querySelector(".modal:not(.hidden)")
    ) {
      e.preventDefault();
      deleteJail();
    }
    if (e.key === "Escape" && !document.querySelector(".modal:not(.hidden)")) {
      appState.selectedJail = null;
      renderJailTable();
      updateToolbar();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      fetchStatus();
      startPolling();
    } else {
      stopPolling();
    }
  });
});
