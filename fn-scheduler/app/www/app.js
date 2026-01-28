const state = {
  tasks: [],
  selectedIds: new Set(),
  editingTaskId: null,
  editingTaskName: '', // 添加这个字段
  currentResultTaskId: null,
  accounts: [],
  accountLoading: false,
  posixSupported: true,
  defaultAccount: "",
};

// 依赖 index.html 中暴露的 window.__i18n
function _t(key, vars) {
  try {
    const fn = window.__i18n && window.__i18n.translate;
    let msg = typeof fn === 'function' ? fn(key) : key;
    if (vars && typeof vars === 'object') {
      Object.keys(vars).forEach(k => {
        msg = msg.replace(new RegExp(`\\{${k}\\}`, 'g'), String(vars[k]));
      });
    }
    return msg;
  } catch (e) { return key; }
}

// Map common backend error messages to localized, user-friendly messages
function mapApiErrorMessage(raw) {
  if (!raw) return null;
  const s = String(raw).toLowerCase();
  if (s.includes('task name already exists')) return _t('error.task_name_exists');
  if (s.includes('template key already exists')) return _t('error.template_key_exists');
  if (s.includes('database integrity')) return _t('error.database_integrity');
  return null;
}

const AUTO_REFRESH_INTERVAL = 5000; // 5 seconds
let autoRefreshTimer = null;

const elements = {
  tableBody: document.querySelector("#taskTable tbody"),
  emptyState: document.getElementById("emptyState"),
  taskModal: document.getElementById("taskModal"),
  taskForm: document.getElementById("taskForm"),
  taskModalTitle: document.getElementById("taskModalTitle"),
  triggerTypeSelect: document.getElementById("triggerType"),
  scheduleSection: document.querySelector('[data-section="schedule"]'),
  eventSection: document.querySelector('[data-section="event"]'),
  eventTypeSelect: document.getElementById("eventType"),
  eventScriptSection: document.querySelector(
    '[data-event-subsection="script"]',
  ),
  accountSelect: document.getElementById("accountSelect"),
  accountStatus: document.getElementById("accountStatus"),
  accountReloadBtn: document.getElementById("btnReloadAccounts"),
  preTaskSelect: document.getElementById("preTaskSelect"),
  clearPreTasksBtn: document.getElementById("btnClearPreTasks"),
  resultModal: document.getElementById("resultModal"),
  resultSubtitle: document.getElementById("resultSubtitle"),
  resultList: document.getElementById("resultList"),
  toast: document.getElementById("toast"),
  cronModal: document.getElementById("cronModal"),
  cronForm: document.getElementById("cronForm"),
  cronPreview: document.getElementById("cronPreview"),
  cronNextTimes: document.getElementById("cronNextTimes"),
  scheduleInput: document.querySelector('input[name="schedule_expression"]'),
  currentTime: document.getElementById("currentTime"),
};

// 计算 API 基础路径：优先使用模块位置（支持通过 index.cgi 加载的情况），
// 其次回退到 window.location.pathname。若路径包含 index.cgi，则保留到该片段。
const API_BASE = (function () {
  try {
    let basePath = "/";
    if (typeof import.meta !== 'undefined' && import.meta.url) {
      try {
        basePath = new URL('.', import.meta.url).pathname;
      } catch (e) {
        basePath = window.location.pathname || '/';
      }
    } else {
      basePath = window.location.pathname || '/';
    }
    // 如果路径中包含 index.cgi，确保保留到 index.cgi/ 前缀
    const idx = basePath.indexOf('index.cgi');
    if (idx >= 0) {
      return basePath.slice(0, idx + 'index.cgi'.length) + '/';
    }
    if (!basePath.endsWith('/')) {
      const last = basePath.lastIndexOf('/');
      basePath = last >= 0 ? basePath.slice(0, last + 1) : '/';
    }
    return basePath;
  } catch (e) {
    return '/';
  }
})();

let taskTemplates = {};

async function loadTemplates() {
  try {
    // 从后端获取数据库中的模板
    const resp = await fetch('api/templates');
    if (!resp.ok) throw new Error(_t('error.load_templates', { status: resp.status }));
    const payload = await resp.json();
    // payload.data 为数组形式
    taskTemplates = {};
    if (payload && Array.isArray(payload.data)) {
      payload.data.forEach((t) => {
        if (t && t.key) {
          taskTemplates[t.key] = t;
        }
      });
    } else if (payload && typeof payload === 'object') {
      // 兼容 /api/templates/export 或直接返回 mapping
      if (!Array.isArray(payload)) {
        Object.keys(payload).forEach((k) => {
          const v = payload[k];
          taskTemplates[k] = { key: k, name: v.name, script_body: v.script_body };
        });
      }
    }
    renderTemplateOptions();
    console.info('任务模板已加载', Object.keys(taskTemplates));
  } catch (err) {
    console.warn('无法通过 API 加载模板', err);
    taskTemplates = {};
  }
}

function renderTemplateOptions() {
  const select = document.getElementById('templateSelect');
  if (!select) return;
  // 保留首项 "无模板（自定义）"
  const current = select.value || '';
  select.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = _t('template.placeholder');
  select.appendChild(placeholder);
  Object.keys(taskTemplates || {}).forEach((key) => {
    const tpl = taskTemplates[key];
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = tpl.name || key;
    select.appendChild(opt);
  });
  // 尝试恢复之前选择
  if (current) select.value = current;
}

// Template management UI state & helpers
const templatesState = {
  templates: [],
  selectedId: null,
  editingId: null,
};

async function refreshTemplatesList() {
  try {
    const resp = await api.listTemplates();
    if (resp && Array.isArray(resp.data)) {
      templatesState.templates = resp.data;
    } else {
      templatesState.templates = [];
    }
    renderTemplatesTable();
  } catch (err) {
    showToast(_t('file.import_failed', { err: err.message }), true);
  }
}

function renderTemplatesTable() {
  const tbody = document.querySelector('#templatesTable tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  templatesState.templates.forEach((t) => {
    const tr = document.createElement('tr');
    tr.dataset.id = t.id;
    tr.dataset.key = t.key || '';
    tr.innerHTML = `<td>${escapeHtml(t.key || '')}</td><td>${escapeHtml(t.name || '')}</td><td>${escapeHtml((t.script_body || '').split('\n')[0] || '')}</td>`;
    tr.tabIndex = 0;
    if (String(templatesState.selectedId) === String(t.id)) {
      tr.classList.add('selected');
      tr.setAttribute('aria-selected', 'true');
    } else {
      tr.setAttribute('aria-selected', 'false');
    }
    tbody.appendChild(tr);
  });
  // click selection
  const tbodyEl = document.querySelector('#templatesTable tbody');
  if (tbodyEl) {
    tbodyEl.onclick = (ev) => {
      const row = ev.target.closest('tr');
      if (!row) return;
      const id = Number(row.dataset.id);
      if (templatesState.selectedId === id) {
        templatesState.selectedId = null;
      } else {
        templatesState.selectedId = id;
      }
      renderTemplatesTable();
    };
    tbodyEl.ondblclick = (ev) => {
      const row = ev.target.closest('tr');
      if (!row) return;
      const id = Number(row.dataset.id);
      const tpl = templatesState.templates.find(t => Number(t.id) === Number(id));
      if (tpl) openTemplateEditModal(tpl);
    };
    tbodyEl.onkeydown = (ev) => {
      const row = ev.target.closest('tr');
      if (!row) return;
      const id = Number(row.dataset.id);
      // 空格或回车切换选择，回车为编辑
      if (ev.key === ' ' || ev.key === 'Spacebar') {
        ev.preventDefault();
        if (templatesState.selectedId === id) templatesState.selectedId = null;
        else templatesState.selectedId = id;
        renderTemplatesTable();
        return;
      }
      if (ev.key === 'Enter') {
        ev.preventDefault();
        const tpl = templatesState.templates.find(t => Number(t.id) === Number(id));
        if (tpl) openTemplateEditModal(tpl);
      }
    };
  }
  // 尝试将焦点移到被选中的行以便用户看到高亮
  if (templatesState.selectedId) {
    const selRow = document.querySelector(`#templatesTable tbody tr[data-id="${templatesState.selectedId}"]`);
    if (selRow) selRow.focus();
  }
}

function openTemplatesModal() {
  refreshTemplatesList();
  const modal = document.getElementById('templatesModal');
  if (modal) openModal(modal);
}

function openTemplateEditModal(editing = null) {
  templatesState.editingId = editing ? editing.id : null;
  const modal = document.getElementById('templateEditModal');
  const form = document.getElementById('templateForm');
  const title = document.getElementById('templateEditTitle');
  if (!form || !modal) return;
  form.reset();
  if (editing) {
    title.textContent = `${_t('btn.edit')}：${editing.name}`;
    form.key.value = editing.key || '';
    form.name.value = editing.name || '';
    form.script_body.value = editing.script_body || '';
  } else {
    title.textContent = _t('btn.add');
  }
  openModal(modal);
}

function openTemplatePreview(tpl) {
  const modal = document.getElementById('templatePreviewModal');
  const subtitle = document.getElementById('templatePreviewSubtitle');
  const content = document.getElementById('templatePreviewContent');
  if (!modal || !content) return;
  subtitle.textContent = tpl ? `${tpl.key || ''} · ${tpl.name || ''}` : '';
  content.textContent = tpl ? (tpl.script_body || '') : '';
  openModal(modal);
}

async function saveTemplateFromForm(ev) {
  ev.preventDefault();
  const form = document.getElementById('templateForm');
  if (!form) return;
  const data = {
    key: form.key.value.trim(),
    name: form.name.value.trim(),
    script_body: form.script_body.value.trim(),
  };
  try {
    if (templatesState.editingId) {
      await api.updateTemplate(templatesState.editingId, data);
      showToast(_t('template.updated'));
    } else {
      await api.createTemplate(data);
      showToast(_t('template.created'));
    }
    closeModal(document.getElementById('templateEditModal'));
    refreshTemplatesList();
    await loadTemplates();
  } catch (err) {
    showToast(_t('error.save_template', { err: err.message }), true);
  }
}

async function deleteSelectedTemplate() {
  const id = templatesState.selectedId;
  if (!id) { showToast(_t('prompt.select_template')); return; }
  if (!(await showConfirm(_t('confirm.delete_template')))) { return; }
  try {
    await api.deleteTemplate(id);
    templatesState.selectedId = null;
    refreshTemplatesList();
    await loadTemplates();
    showToast(_t('template.deleted'));
  } catch (err) {
    showToast(_t('error.delete_template', { err: err.message }), true);
  }
}

function bindTemplateImportFile() {
  const fileInput = document.getElementById('templateImportFile');
  if (!fileInput) return;
  fileInput.onchange = async () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    try {
      const text = await f.text();
      const obj = JSON.parse(text);
      if (typeof obj !== 'object') throw new Error(_t('file.invalid_format'));
      const resp = await api.importTemplates(obj);
      showToast(_t('file.import_result', { inserted: resp.imported.inserted, updated: resp.imported.updated }));
      refreshTemplatesList();
      await loadTemplates();
    } catch (err) {
      showToast(_t('file.import_failed', { err: err.message }), true);
    } finally {
      fileInput.value = '';
    }
  };
}

// 显示当前时间
function updateCurrentTime() {
  if (!elements.currentTime) { return; }
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const h = String(now.getHours()).padStart(2, "0");
  const min = String(now.getMinutes()).padStart(2, "0");
  const s = String(now.getSeconds()).padStart(2, "0");
  elements.currentTime.textContent = `${y}-${m}-${d} ${h}:${min}:${s}`;
}

setInterval(updateCurrentTime, 1000);
updateCurrentTime();

const buttons = {
  create: document.getElementById("btnCreate"),
  edit: document.getElementById("btnEdit"),
  delete: document.getElementById("btnDelete"),
  run: document.getElementById("btnRun"),
  toggle: document.getElementById("btnToggle"),
  results: document.getElementById("btnResults"),
  refresh: document.getElementById("btnRefresh"),
  clearResults: document.getElementById("btnClearResults"),
  cronGenerator: document.getElementById("btnCronGenerator"),
  applyCron: document.getElementById("btnApplyCron"),
};

const CRON_FIELDS = ["minute", "hour", "day", "month", "weekday"];
const cronSelects = {};
const cronCustomInputs = {};

CRON_FIELDS.forEach((field) => {
  cronSelects[field] = document.querySelector(`[data-cron-field="${field}"]`);
  cronCustomInputs[field] = document.querySelector(
    `[data-cron-custom="${field}"]`,
  );
});

const statusMap = {
  success: { label: 'status.success', className: "status-success" },
  failed: { label: 'status.failed', className: "status-failed" },
  running: { label: 'status.running', className: "status-running" },
};

const triggerMap = {
  schedule: 'trigger.schedule',
  event: 'trigger.event',
};

const eventTypeMap = {
  script: 'event.script',
  system_boot: 'event.system_boot',
  system_shutdown: 'event.system_shutdown',
};

// 响应式短标签（用于窄屏显示），存放为 i18n 键
const eventTypeShortMap = {
  script: 'event.short.script',
  system_boot: 'event.short.system_boot',
  system_shutdown: 'event.short.system_shutdown',
};

function isNarrow() {
  return window.innerWidth <= 480;
}

function getEventLabel(key) {
  if (isNarrow()) return _t(eventTypeShortMap[key] || eventTypeMap[key] || key);
  return _t(eventTypeMap[key] || key);
}

function escapeHtml(value = "") {
  const s = String(value == null ? '' : value);
  // single pass replace using map for better performance
  return s.replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case '&': return '&amp;';
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '"': return '&quot;';
      case "'": return '&#39;';
      default: return ch;
    }
  });
}

function applyModalI18n(modal) {
  if (!modal) return;
  // apply data-i18n and data-i18n-attr within modal
  modal.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (!key) return;
    const attr = el.getAttribute('data-i18n-attr');
    try {
      const v = _t(key);
      if (attr) el.setAttribute(attr, v);
      else el.textContent = v;
    } catch (e) {
      // noop
    }
  });
}

const api = {
  async request(url, options = {}) {
    // Resolve relative urls like "api/tasks" against API_BASE
    const resolved = /^(https?:)?\/\//.test(url) || url.startsWith('/') ? url : (API_BASE + url.replace(/^\/+/, ''));
    // merge headers, but allow caller to override
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const response = await fetch(resolved, {
      ...options,
      headers,
    });
    const text = await response.text();
    let payload = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (err) {
        // keep raw text in payload for better diagnostics
        payload = { _raw: text };
      }
    }
    if (!response.ok) {
      const rawMessage = (payload && (payload.error || payload._raw)) || response.statusText || `HTTP ${response.status}`;
      const friendly = mapApiErrorMessage(rawMessage) || rawMessage;
      console.error("API error", { url: resolved, status: response.status, payload });
      throw new Error(friendly);
    }
    return payload || {};
  },
  listTasks() {
    return this.request("api/tasks");
  },
  listAccounts() {
    return this.request("api/accounts");
  },
  createTask(data) {
    return this.request("api/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  listTemplates() {
    return this.request('api/templates');
  },
  createTemplate(data) {
    return this.request('api/templates', { method: 'POST', body: JSON.stringify(data) });
  },
  updateTemplate(id, data) {
    return this.request(`api/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  },
  deleteTemplate(id) {
    return this.request(`api/templates/${id}`, { method: 'DELETE' });
  },
  importTemplates(mapping) {
    return this.request('api/templates/import', { method: 'POST', body: JSON.stringify(mapping) });
  },
  exportTemplates() {
    return this.request('api/templates/export').then((p) => p);
  },
  updateTask(id, data) {
    return this.request(`api/tasks/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
  deleteTask(id) {
    return this.request(`api/tasks/${id}`, { method: "DELETE" });
  },
  runTask(id) {
    return this.request(`api/tasks/${id}/run`, { method: "POST" });
  },
  fetchResults(id) {
    return this.request(`api/tasks/${id}/results?limit=50`);
  },
  deleteResult(id, resultId) {
    return this.request(`api/tasks/${id}/results/${resultId}`, {
      method: "DELETE",
    });
  },
  clearResults(id) {
    return this.request(`api/tasks/${id}/results`, { method: "DELETE" });
  },
  batchTasks(action, taskIds, extra = {}) {
    return this.request("api/tasks/batch", {
      method: "POST",
      body: JSON.stringify({ action, task_ids: taskIds, ...extra }),
    });
  },
};

function formatDate(value) {
  if (!value) { return "—"; }
  // 去除 T、去除时区（如 +00:00 或 Z）
  let s = value.replace("T", " ");
  // 去掉结尾的时区部分（+00:00、Z等）
  s = s.replace(/([\+\-]\d{2}:?\d{2}|Z)$/i, "");
  return s.trim();
}

function getSelectedTasks() {
  return state.tasks.filter((task) => state.selectedIds.has(task.id));
}

function renderTasks() {
  elements.tableBody.innerHTML = "";
  const { tasks } = state;
  if (!tasks.length) {
    elements.emptyState.classList.remove("hidden");
  } else {
    elements.emptyState.classList.add("hidden");
  }

  tasks.forEach((task) => {
    const tr = document.createElement("tr");
    tr.dataset.id = task.id;
    if (state.selectedIds.has(task.id)) {
      tr.classList.add("selected");
    }

    const latestResult = task.latest_result;
    const status = statusMap[latestResult?.status] || {
      label: "status.no_record",
      className: "status-unknown",
    };
    const statusLabel = _t(status.label);
    const safeName = escapeHtml(task.name);
    const safeAccount = escapeHtml(task.account);
    let triggerLabel = _t(triggerMap[task.trigger_type] || task.trigger_type);
    if (task.trigger_type === "event") {
      const subtype = getEventLabel(task.event_type) || _t('trigger.event');
      if (isNarrow()) {
        triggerLabel = subtype;
      } else {
        triggerLabel = `${triggerLabel} · ${subtype}`;
      }
    }

    tr.innerHTML = `
            <td><span class="badge ${task.is_active ? "badge-active" : "badge-paused"}">${task.is_active ? _t('status.enabled') : _t('status.disabled')}</span></td>
            <td>
                <div class="task-name">${safeName}</div>
            </td>
            <td>${escapeHtml(formatDate(task.next_run_at))}</td>
                <td><span class="trigger-label">${escapeHtml(triggerLabel)}</span></td>
            <td><span class="status-pill ${status.className}">${escapeHtml(statusLabel)}</span></td>
            <td>${safeAccount}</td>
        `;
    elements.tableBody.appendChild(tr);
  });
  updateToolbarState();
}

function updateToolbarState() {
  const selectedCount = state.selectedIds.size;
  buttons.edit.disabled = selectedCount !== 1;
  buttons.run.disabled = selectedCount === 0;
  buttons.delete.disabled = selectedCount === 0;
  buttons.toggle.disabled = selectedCount === 0;
  buttons.results.disabled = selectedCount !== 1;
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.remove("hidden");
  elements.toast.style.background = isError
    ? "var(--danger)"
    : "var(--primary)";
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    elements.toast.classList.add("hidden");
  }, 2600);
}

function showConfirm(message, { okText = _t('btn.ok'), cancelText = _t('btn.cancel') } = {}) {
  return new Promise((resolve) => {
    let modal = document.getElementById('__confirmModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = '__confirmModal';
      modal.className = 'modal hidden';
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <div><h2></h2></div>
            <div class="modal-header-actions"><button class="ghost" data-close>&times;</button></div>
          </div>
          <div class="modal-body" style="padding:1rem;"></div>
          <div class="modal-actions" style="display:flex;justify-content:flex-end;gap:0.5rem;padding:1rem;">
            <button class="ghost" id="__confirmCancel"></button>
            <button class="primary" id="__confirmOk"></button>
          </div>
        </div>`;
      document.body.appendChild(modal);
      // wire close on overlay
      modal.addEventListener('click', (ev) => { if (ev.target === modal) { closeModal(modal); resolve(false); } });
      modal.querySelectorAll('[data-close]').forEach((btn) => btn.addEventListener('click', () => { closeModal(modal); resolve(false); }));
    }
    const hdr = modal.querySelector('h2');
    const body = modal.querySelector('.modal-body');
    const okBtn = modal.querySelector('#__confirmOk');
    const cancelBtn = modal.querySelector('#__confirmCancel');
    if (hdr) hdr.textContent = '';
    if (body) body.textContent = message || '';
    if (okBtn) {
      okBtn.textContent = okText;
      okBtn.onclick = () => { closeModal(modal); resolve(true); };
    }
    if (cancelBtn) {
      cancelBtn.textContent = cancelText;
      cancelBtn.onclick = () => { closeModal(modal); resolve(false); };
    }
    applyModalI18n(modal);
    openModal(modal);
  });
}

function openModal(modal) {
  modal.classList.remove("hidden");
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.add("hidden");
  // restore i18n-driven texts for any modal (will reset server file picker as well)
  try {
    applyModalI18n(modal);
    // restore placeholder attributes if present
    modal.querySelectorAll('[data-i18n-attr]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const attr = el.getAttribute('data-i18n-attr');
      if (key && attr) el.setAttribute(attr, _t(key));
    });
    // ensure use-local button visible by default
    const btnUseLocalEl = modal.querySelector('#btnUseLocalFile');
    if (btnUseLocalEl) btnUseLocalEl.classList.remove('hidden');
  } catch (e) {
    // ignore i18n restore errors
  }
}

function toggleSections() {
  const type = elements.triggerTypeSelect.value;
  const isSchedule = type !== "event";
  elements.scheduleSection.classList.toggle("hidden", !isSchedule);
  elements.eventSection.classList.toggle("hidden", isSchedule);
  toggleEventInputs();
}

function toggleEventInputs() {
  const isEvent = elements.triggerTypeSelect.value === "event";
  elements.eventTypeSelect.disabled = !isEvent;
  if (!isEvent) {
    elements.eventScriptSection.classList.add("hidden");
    elements.taskForm.condition_script.disabled = true;
    elements.taskForm.condition_interval.disabled = true;
    return;
  }
  const isScriptMode = elements.eventTypeSelect.value === "script";
  elements.eventScriptSection.classList.toggle("hidden", !isScriptMode);
  elements.taskForm.condition_script.disabled = !isScriptMode;
  elements.taskForm.condition_interval.disabled = !isScriptMode;
}

function renderAccountOptions(selectedAccount = "") {
  const select = elements.accountSelect;
  const statusEl = elements.accountStatus;
  const reloadBtn = elements.accountReloadBtn;
  if (!select) { return; }

  select.innerHTML = "";
  const isReadOnly = !state.posixSupported;
  if (reloadBtn) {
    reloadBtn.disabled = state.accountLoading;
    reloadBtn.classList.toggle("hidden", isReadOnly);
  }

  if (state.accountLoading) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = _t('loading');
    option.disabled = true;
    option.selected = true;
    select.appendChild(option);
    select.disabled = true;
    if (statusEl) {
      statusEl.textContent = _t('loading_accounts');
    }
    return;
  }

  if (!state.accounts.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = state.posixSupported ? _t('no_accounts') : _t('not_available');
    option.disabled = true;
    option.selected = true;
    select.appendChild(option);
    select.disabled = true;
    if (statusEl) {
      statusEl.textContent = state.posixSupported
        ? _t('account.not_found_posix')
        : _t('account.windows_not_detected');
    }
    return;
  }

  if (isReadOnly) {
    const defaultAccount = state.accounts[0] || state.defaultAccount || "";
    const option = document.createElement("option");
    option.value = defaultAccount;
    option.textContent = defaultAccount || _t('label.current_logged_in_account');
    option.selected = true;
    select.appendChild(option);
    select.disabled = true;
    if (statusEl) {
      statusEl.textContent = defaultAccount ? "" : "";
    }
    return;
  }

  select.disabled = false;
  let hasSelected = false;
  const legacyAccount =
    selectedAccount && !state.accounts.includes(selectedAccount)
      ? selectedAccount
      : "";
  if (legacyAccount) {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = `${legacyAccount} ${_t('placeholder.needs_reselect')}`;
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);
  }

  state.accounts.forEach((account) => {
    const option = document.createElement("option");
    option.value = account;
    option.textContent = account;
    if (!hasSelected && account === selectedAccount) {
      option.selected = true;
      hasSelected = true;
    }
    select.appendChild(option);
  });


  // 更新事件类型下拉选项的显示文本（响应式）
  function updateEventOptionLabels() {
    const el = elements.eventTypeSelect;
    if (!el) return;
    const useShort = isNarrow();
    // 保留选项顺序及 value，仅调整显示文本
    for (const opt of el.options) {
      const v = opt.value;
      if (v === 'script' || v === 'system_boot' || v === 'system_shutdown') {
        opt.textContent = useShort ? _t(eventTypeShortMap[v] || eventTypeMap[v]) : _t(eventTypeMap[v] || eventTypeShortMap[v]);
      }
    }
  }

  // 在窗口尺寸变化时更新 event 下拉与任务列表显示
  window.addEventListener('resize', () => {
    updateEventOptionLabels();
    // 重新渲染任务以更新在表格中显示的事件简称/全称
    renderTasks();
  });

  // 初始化时也更新一下
  document.addEventListener('DOMContentLoaded', () => {
    updateEventOptionLabels();
  });
  if (!hasSelected && !legacyAccount && select.options.length) {
    select.options[0].selected = true;
  }

  if (statusEl) {
    statusEl.textContent = legacyAccount
      ? _t('error.task_account_not_allowed', { acc: legacyAccount })
      : "";
  }
}

async function loadAccounts({ showError = true, preferredAccount = "" } = {}) {
  const select = elements.accountSelect;
  if (!select) {
    return;
  }
  const previousValue = preferredAccount || select.value || "";
  state.accountLoading = true;
  renderAccountOptions(previousValue);
  try {
    const response = await api.listAccounts();
    state.accounts = response.data || [];
    if (response.meta) {
      if (
        Object.prototype.hasOwnProperty.call(response.meta, "posix_supported")
      ) {
        state.posixSupported = Boolean(response.meta.posix_supported);
      }
      if (
        Object.prototype.hasOwnProperty.call(response.meta, "default_account")
      ) {
        state.defaultAccount = response.meta.default_account || "";
      }
    }
    if (
      !state.posixSupported &&
      !state.accounts.length &&
      state.defaultAccount
    ) {
      state.accounts = [state.defaultAccount];
    }
  } catch (error) {
    if (showError) {
      showToast(_t('error.load_accounts', { err: error.message }), true);
    }
  } finally {
    state.accountLoading = false;
    renderAccountOptions(preferredAccount || previousValue);
  }
}

function populatePreTaskOptions(currentId = null, selected = []) {
  elements.preTaskSelect.innerHTML = "";
  state.tasks
    .filter((task) => task.id !== currentId)
    .forEach((task) => {
      const option = document.createElement("option");
      option.value = task.id;
      option.textContent = `${task.name} (#${task.id})`;
      if (selected.includes(task.id)) {
        option.selected = true;
      }
      elements.preTaskSelect.appendChild(option);
    });
}

function openTaskModal(task = null) {
  state.editingTaskId = task?.id ?? null;
  elements.taskForm.reset();

  // 重置模板选择
  const templateSelect = document.getElementById('templateSelect');
  if (templateSelect) {
    templateSelect.value = '';
  }

  // 记录原始任务名称（用于判断是否已修改）
  if (task) {
    state.editingTaskName = task.name;
    elements.taskForm.name.value = task.name;
  } else {
    state.editingTaskName = '';
  }

  const preferredAccount = task?.account || "";
  renderAccountOptions(preferredAccount);
  if (!state.accountLoading && !state.accounts.length) {
    loadAccounts({ showError: false, preferredAccount });
  }
  populatePreTaskOptions(state.editingTaskId, task?.pre_task_ids || []);
  if (task) {
    elements.taskModalTitle.textContent = `${_t('btn.edit')}：${task.name}`;
    elements.taskForm.name.value = task.name;
    elements.triggerTypeSelect.value = task.trigger_type;
    elements.eventTypeSelect.value = task.event_type || "system_shutdown";
    elements.taskForm.is_active.checked = Boolean(task.is_active);
    if (elements.scheduleInput) {
      elements.scheduleInput.value = task.schedule_expression || "";
    }
    elements.taskForm.condition_script.value = task.condition_script || "";
    elements.taskForm.condition_interval.value = task.condition_interval || 60;
    elements.taskForm.script_body.value = task.script_body || "";
  } else {
    elements.taskModalTitle.textContent = _t('modal.task.new');
    elements.eventTypeSelect.value = "system_shutdown";
    elements.taskForm.condition_interval.value = 60;
    if (elements.scheduleInput) {
      elements.scheduleInput.value = "";
    }
  }
  toggleSections();
  openModal(elements.taskModal);
}

function collectFormData() {
  const data = {
    name: elements.taskForm.name.value.trim(),
    account: (elements.accountSelect?.value || "").trim(),
    trigger_type: elements.triggerTypeSelect.value,
    is_active: elements.taskForm.is_active.checked,
    pre_task_ids: Array.from(elements.preTaskSelect.selectedOptions).map(
      (opt) => Number(opt.value),
    ),
    script_body: elements.taskForm.script_body.value.trim(),
  };
  if (data.trigger_type === "schedule") {
    const scheduleField = elements.scheduleInput;
    data.schedule_expression = scheduleField ? scheduleField.value.trim() : "";
  } else {
    data.event_type = elements.eventTypeSelect.value;
    if (data.event_type === "script") {
      data.condition_script = elements.taskForm.condition_script.value.trim();
      data.condition_interval =
        Number(elements.taskForm.condition_interval.value) || 60;
    }
  }
  return data;
}

function sanitizeCronValue(value = "") {
  return value.replace(/[^0-9*\/,\-]/g, "").replace(/,{2,}/g, ",");
}

function getCronFieldValue(field) {
  const select = cronSelects[field];
  if (!select) {
    return "*";
  }
  if (select.value === "custom") {
    const input = cronCustomInputs[field];
    const sanitized = sanitizeCronValue(input?.value || "");
    return sanitized || "*";
  }
  return select.value || "*";
}

function updateCronPreview() {
  const expression = CRON_FIELDS.map((field) => getCronFieldValue(field)).join(
    " ",
  );
  if (elements.cronPreview) {
    elements.cronPreview.textContent = expression;
  }
  // 计算2次执行时间并显示有效性
  if (elements.cronNextTimes) {
    const result = getNextCronTimes(expression, 2);
    if (!result.valid) {
      elements.cronNextTimes.textContent = _t('cron.invalid');
      elements.cronNextTimes.classList.add("cron-invalid");
      if (elements.cronPreview) {
        elements.cronPreview.classList.add("cron-invalid");
      }
      if (buttons.applyCron) {
        buttons.applyCron.disabled = true;
      }
    } else {
      if (buttons.applyCron) {
        buttons.applyCron.disabled = false;
      }
      elements.cronNextTimes.classList.remove("cron-invalid");
      if (elements.cronPreview) {
        elements.cronPreview.classList.remove("cron-invalid");
      }
      if (result.times.length) {
        elements.cronNextTimes.innerHTML =
          _t('cron.preview') +
          result.times.map((t) => `<div>${t}</div>`).join("");
      } else {
        elements.cronNextTimes.textContent = "";
      }
      if (result.exceeded) {
        const hint = document.createElement("div");
        hint.className = "muted";
        hint.style.marginTop = "6px";
        hint.textContent = _t('cron.search_exceeded', { months: result.maxMonths });
        elements.cronNextTimes.appendChild(hint);
      }
    }
  }
  return expression;
}

// 计算N次 Cron 时间（本地时间）
function getNextCronTimes(expr, count = 2) {
  try {
    const now = new Date();
    let base = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      now.getHours(),
      now.getMinutes(),
      0,
      0,
    );
    const parts = expr.trim().split(/\s+/);
    if (parts.length !== 5) { return { times: [], valid: false }; }
    // 解析每个字段
    function parseField(str, min, max) {
      if (str === "*") { return Array.from({ length: max - min + 1 }, (_, i) => i + min); }
      let out = new Set();
      str.split(",").forEach((token) => {
        if (token.includes("/")) {
          let [range, step] = token.split("/");
          step = parseInt(step);
          if (!step || step < 1) { return; }
          let vals =
            range === "*"
              ? Array.from({ length: max - min + 1 }, (_, i) => i + min)
              : parseRange(range, min, max);
          vals.forEach((v, i) => {
            if ((v - min) % step === 0) { out.add(v); }
          });
        } else {
          parseRange(token, min, max).forEach((v) => out.add(v));
        }
      });
      return Array.from(out)
        .filter((v) => v >= min && v <= max)
        .sort((a, b) => a - b);
    }
    function parseRange(token, min, max) {
      if (token === "*") { return Array.from({ length: max - min + 1 }, (_, i) => i + min); }
      if (token.includes("-")) {
        let [a, b] = token.split("-").map(Number);
        if (isNaN(a) || isNaN(b) || a > b) { return []; }
        return Array.from({ length: b - a + 1 }, (_, i) => a + i);
      }
      let n = Number(token);
      return isNaN(n) ? [] : [n];
    }
    const rawParts = parts;
    const minutes = parseField(rawParts[0], 0, 59);
    const hours = parseField(rawParts[1], 0, 23);
    const days = parseField(rawParts[2], 1, 31);
    const months = parseField(rawParts[3], 1, 12);
    const weekdays = parseField(rawParts[4], 0, 6);
    const dayFieldIsStar = rawParts[2] === "*";
    const weekdayFieldIsStar = rawParts[4] === "*";
    // 如果任一字段使用了非 '*' 的自定义值但解析为空，则视为无效表达式
    if (
      (rawParts[0] !== "*" && !minutes.length) ||
      (rawParts[1] !== "*" && !hours.length) ||
      (rawParts[2] !== "*" && !days.length) ||
      (rawParts[3] !== "*" && !months.length) ||
      (rawParts[4] !== "*" && !weekdays.length)
    ) {
      return { times: [], valid: false };
    }
    // 使用按月/天枚举的方式来生成候选时间，避免逐分钟扫描导致无法找到远期匹配（例如只在半年后触发的任务）
    let results = [];
    const maxMonths = 36; // 向前搜索的最大月份数（可覆盖多年场景）
    const seen = new Set();
    function pushIfNew(dt) {
      const s = dt.getTime();
      if (s <= base.getTime() || seen.has(s)) return;
      seen.add(s);
      results.push(formatCronDate(dt));
    }

    for (let offset = 0; offset < maxMonths && results.length < count; offset++) {
      const y = base.getFullYear() + Math.floor((base.getMonth() + offset) / 12);
      const mIndex = (base.getMonth() + offset) % 12; // 0-based month index
      const monthNum = mIndex + 1;
      if (!months.includes(monthNum)) continue;
      const daysInThisMonth = new Date(y, mIndex + 1, 0).getDate();
      // 遍历该月的每一天，检查是否符合日或周条件
      for (let day = 1; day <= daysInThisMonth && results.length < count; day++) {
        const dtWeekJs = new Date(y, mIndex, day).getDay(); // 0=周日
        const cronWeekday = (dtWeekJs + 6) % 7; // 转为 0=周一..6=周日
        const dayMatch = days.includes(day);
        const weekMatch = weekdays.includes(cronWeekday);
        // Cron rule: if either DOM or DOW is '*', the other field is used to determine match.
        // If both are not '*', match when either matches.
        let dateMatches = false;
        if (dayFieldIsStar && weekdayFieldIsStar) {
          dateMatches = true;
        } else if (dayFieldIsStar) {
          dateMatches = weekMatch;
        } else if (weekdayFieldIsStar) {
          dateMatches = dayMatch;
        } else {
          dateMatches = dayMatch || weekMatch;
        }
        if (!dateMatches) continue;
        // 对于匹配的日期，生成时分组合
        for (let hi = 0; hi < hours.length && results.length < count; hi++) {
          const hour = hours[hi];
          for (let mi = 0; mi < minutes.length && results.length < count; mi++) {
            const minute = minutes[mi];
            const cand = new Date(y, mIndex, day, hour, minute, 0, 0);
            pushIfNew(cand);
          }
        }
      }
    }
    // 结果按时间排序并返回前 count 项
    results.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    return { times: results.slice(0, count), valid: true };
  } catch (e) {
    return { times: [], valid: false };
  }
}

function formatCronDate(dt) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  const h = String(dt.getHours()).padStart(2, "0");
  const min = String(dt.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${d} ${h}:${min}`;
}

function prefillCronGenerator(expression = "") {
  const normalized = expression.trim();
  const tokens = normalized ? normalized.split(/\s+/) : [];
  CRON_FIELDS.forEach((field, index) => {
    const select = cronSelects[field];
    const input = cronCustomInputs[field];
    if (!select) {
      return;
    }
    const rawPart = tokens[index] || "*";
    const normalizedPart =
      rawPart === "*" ? "*" : sanitizeCronValue(rawPart) || "*";
    const hasOption = Array.from(select.options).some(
      (option) => option.value === normalizedPart,
    );
    if (hasOption) {
      select.value = normalizedPart;
      if (input) {
        input.classList.add("hidden");
        input.value = "";
      }
    } else {
      select.value = "custom";
      if (input) {
        input.classList.remove("hidden");
        input.value = normalizedPart;
      }
    }
  });
  updateCronPreview();
}

async function handleFormSubmit(event) {
  event.preventDefault();
  try {
    const payload = collectFormData();
    if (!payload.name || !payload.account || !payload.script_body) {
      throw new Error(_t('validation.required_fields'));
    }
    if (state.accountLoading) {
      throw new Error(_t('validation.accounts_loading'));
    }
    if (!state.accounts.length) {
      if (state.posixSupported) {
        throw new Error(_t('validation.no_accounts_posix'));
      }
      throw new Error(_t('validation.no_default_account'));
    }
    if (!state.posixSupported) {
      payload.account =
        state.accounts[0] || state.defaultAccount || payload.account;
    } else if (!state.accounts.includes(payload.account)) {
      throw new Error(_t('validation.account_not_in_group'));
    }
    if (payload.trigger_type === "schedule" && !payload.schedule_expression) {
      throw new Error(_t('validation.cron_required'));
    }
    if (payload.trigger_type === "event") {
      if (!payload.event_type) {
        payload.event_type = "script";
      }
      if (payload.event_type === "script" && !payload.condition_script) {
        throw new Error(_t('validation.script_required'));
      }
    }
    if (state.editingTaskId) {
      await api.updateTask(state.editingTaskId, payload);
      showToast(_t('msg.task_updated'));
    } else {
      await api.createTask(payload);
      showToast(_t('msg.task_created'));
    }
    closeModal(elements.taskModal);
    state.selectedIds.clear();
    await loadTasks();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadTasks({ silent = false } = {}) {
  try {
    const { data } = await api.listTasks();
    state.tasks = data || [];
    state.tasks.sort((a, b) => a.id - b.id);
    state.selectedIds.forEach((id) => {
      if (!state.tasks.some((task) => task.id === id)) {
        state.selectedIds.delete(id);
      }
    });
    renderTasks();
  } catch (error) {
    if (!silent) {
      showToast(_t('error.load_tasks', { err: error.message }), true);
    } else {
      console.error("自动刷新任务失败", error);
    }
  }
}

function startAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
  }
  autoRefreshTimer = setInterval(() => {
    if (!document.hidden) {
      loadTasks({ silent: true });
    }
  }, AUTO_REFRESH_INTERVAL);
}

async function deleteSelectedTasks() {
  const selected = Array.from(state.selectedIds);
  if (!selected.length) {
    showToast(_t('prompt.select_task'));
    return;
  }
  if (!(await showConfirm(_t('confirm.delete_selected_tasks', { n: selected.length })))) {
    return;
  }
  try {
    const response = await api.batchTasks("delete", selected);
    const result = response.result || {};
    const { deleted = [], missing = [] } = result;
    const deletedCount = deleted.length;
    const missingCount = missing.length;
    state.selectedIds.clear();
    await loadTasks();
    let parts = [];
    if (deletedCount) parts.push(_t('msg.deleted_n', { n: deletedCount }));
    if (missingCount) parts.push(_t('msg.missing_n', { n: missingCount }));
    showToast(parts.join(_t('list.sep')) || _t('msg.no_tasks_deleted'));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function runSelectedTasks() {
  const selected = Array.from(state.selectedIds);
  if (!selected.length) {
    showToast(_t('prompt.select_task_to_run'));
    return;
  }
  try {
    const response = await api.batchTasks("run", selected);
    const result = response.result || {};
    const { queued = [], running = [], blocked = [], missing = [] } = result;
    const queuedCount = queued.length;
    const runningCount = running.length;
    const blockedCount = blocked.length;
    const missingCount = missing.length;
    const parts = [];
    if (queuedCount) parts.push(_t('msg.triggered_n', { n: queuedCount }));
    if (runningCount) parts.push(_t('msg.running_n', { n: runningCount }));
    if (blockedCount) parts.push(_t('msg.blocked_n', { n: blockedCount }));
    if (missingCount) parts.push(_t('msg.missing_n', { n: missingCount }));
    showToast(parts.join(_t('list.sep')) || _t('msg.no_tasks_triggered'));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function toggleSelectedTask() {
  const selected = Array.from(state.selectedIds);
  if (!selected.length) {
    showToast(_t('prompt.select_task'));
    return;
  }
  try {
    const selectedTasks = state.tasks.filter((task) =>
      selected.includes(task.id),
    );
    if (!selectedTasks.length) {
      throw new Error(_t('error.task_not_found'));
    }
    const shouldEnable = selectedTasks.some((task) => !task.is_active);
    const action = shouldEnable ? "enable" : "disable";
    const response = await api.batchTasks(action, selected);
    const result = response.result || {};
    const { updated = [], unchanged = [], missing = [] } = result;
    const updatedCount = updated.length;
    const unchangedCount = unchanged.length;
    const missingCount = missing.length;
    await loadTasks();
    const verb = shouldEnable ? _t('verb.enable') : _t('verb.disable');
    const parts = [];
    if (updatedCount) parts.push(_t('msg.action_completed', { verb, n: updatedCount }));
    if (unchangedCount) parts.push(_t('msg.unchanged_count', { n: unchangedCount }));
    if (missingCount) parts.push(_t('msg.missing_n', { n: missingCount }));
    showToast(parts.join(_t('list.sep')) || _t('msg.no_tasks_completed', { verb }));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function openResultModal() {
  const selected = Array.from(state.selectedIds);
  if (selected.length !== 1) {
    showToast(_t('prompt.select_single_task'));
    return;
  }
  const taskId = selected[0];
  const task = state.tasks.find((item) => item.id === taskId);
  if (!task) {
    showToast(_t('error.task_not_found'), true);
    return;
  }
  state.currentResultTaskId = taskId;
  elements.resultSubtitle.textContent = `${task.name} (#${task.id})`;
  openModal(elements.resultModal);
  await refreshResults();
}

async function refreshResults() {
  if (!state.currentResultTaskId) { return; }
  try {
    const { data } = await api.fetchResults(state.currentResultTaskId);
    renderResults(data || []);
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderResults(results) {
  elements.resultList.innerHTML = "";
  if (!results.length) {
    elements.resultList.innerHTML = `<p class="empty">${_t('results.no_records')}</p>`;
    return;
  }
  results.forEach((result) => {
    const status = statusMap[result.status] || {
      label: result.status,
      className: "status-unknown",
    };
    const card = document.createElement("article");
    card.className = "result-card";
    // translate status label and trigger reason (try trigger.<reason> then fallback)
    const statusText = _t(status.label);
    let reasonKey = `trigger.${result.trigger_reason}`;
    let reasonText = _t(reasonKey);
    if (reasonText === reasonKey) {
      reasonText = result.trigger_reason || "";
    }
    card.innerHTML = `
            <header>
                <div>
                    <div class="status-pill ${status.className}">${escapeHtml(statusText)}</div>
                    <span class="muted">${_t('label.trigger')}${escapeHtml(reasonText)}</span>
                </div>
                  <div class="muted">${escapeHtml(formatDate(result.started_at))} - ${escapeHtml(formatDate(result.finished_at))}</div>
                  <button class="ghost" data-delete="${result.id}">${_t('btn.delete')}</button>
            </header>
            <pre>${escapeHtml(result.log || "")}</pre>
        `;
    card.querySelector("[data-delete]").addEventListener("click", async () => {
      try {
        await api.deleteResult(state.currentResultTaskId, result.id);
        await refreshResults();
      } catch (error) {
        showToast(error.message, true);
      }
    });
    elements.resultList.appendChild(card);
  });
}

async function clearResultHistory() {
  if (!state.currentResultTaskId) { return; }
  if (!(await showConfirm(_t('confirm.clear_results')))) {
    return;
  }
  try {
    await api.clearResults(state.currentResultTaskId);
    await refreshResults();
    showToast(_t('msg.results_cleared'));
  } catch (error) {
    showToast(error.message, true);
  }
}

function closeModalOnOverlay(event) {
  if (event.target.matches("[data-close]")) {
    const modal = event.target.closest(".modal");
    closeModal(modal);
  }
  if (event.target.classList.contains("modal")) {
    closeModal(event.target);
  }
}

function attachEventListeners() {
  elements.tableBody.addEventListener("click", (event) => {
    const row = event.target.closest("tr");
    if (!row) { return; }
    const id = Number(row.dataset.id);
    if (event.metaKey || event.ctrlKey) {
      if (state.selectedIds.has(id)) {
        state.selectedIds.delete(id);
      } else {
        state.selectedIds.add(id);
      }
    } else {
      state.selectedIds.clear();
      state.selectedIds.add(id);
    }
    renderTasks();
  });

  buttons.create.addEventListener("click", () => openTaskModal());
  buttons.edit.addEventListener("click", () => {
    const selected = getSelectedTasks();
    if (selected.length !== 1) {
      showToast(_t('prompt.select_single_task'));
      return;
    }
    openTaskModal(selected[0]);
  });
  buttons.delete.addEventListener("click", deleteSelectedTasks);
  buttons.run.addEventListener("click", runSelectedTasks);
  buttons.toggle.addEventListener("click", toggleSelectedTask);
  buttons.results.addEventListener("click", openResultModal);
  buttons.refresh.addEventListener("click", loadTasks);
  buttons.clearResults.addEventListener("click", clearResultHistory);
  elements.clearPreTasksBtn.addEventListener("click", () => {
    Array.from(elements.preTaskSelect.options).forEach((option) => {
      option.selected = false;
    });
  });
  if (elements.accountReloadBtn) {
    elements.accountReloadBtn.addEventListener("click", () =>
      loadAccounts({ showError: true }),
    );
  }

  elements.taskForm.addEventListener("submit", handleFormSubmit);
  document
    .querySelectorAll("[data-close]")
    .forEach((btn) => btn.addEventListener("click", closeModalOnOverlay));
  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal(modal);
      }
    });
  });

  elements.triggerTypeSelect.addEventListener("change", toggleSections);
  elements.eventTypeSelect.addEventListener("change", toggleEventInputs);

  CRON_FIELDS.forEach((field) => {
    const select = cronSelects[field];
    const input = cronCustomInputs[field];
    if (select) {
      select.addEventListener("change", () => {
        const useCustom = select.value === "custom";
        if (input) {
          input.classList.toggle("hidden", !useCustom);
          if (useCustom && !input.value.trim()) {
            input.value = "*";
          }
          if (!useCustom) {
            input.value = "";
          }
        }
        updateCronPreview();
      });
    }
    if (input) {
      input.addEventListener("input", () => {
        const sanitized = sanitizeCronValue(input.value);
        if (sanitized !== input.value) {
          input.value = sanitized;
        }
        updateCronPreview();
      });
    }
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }
    if (target.closest("#btnCronGenerator") && elements.cronModal) {
      event.preventDefault();
      const current = elements.scheduleInput?.value || "";
      prefillCronGenerator(current);
      openModal(elements.cronModal);
      return;
    }
    if (target.closest("#btnApplyCron") && elements.cronModal) {
      event.preventDefault();
      const expression = updateCronPreview();
      if (elements.scheduleInput) {
        elements.scheduleInput.value = expression;
      }
      closeModal(elements.cronModal);
    }
  });

  // 添加模板选择事件监听器
  const templateSelect = document.getElementById('templateSelect');
  if (templateSelect) {
    templateSelect.addEventListener('change', function () {
      const templateKey = this.value;
      if (templateKey && taskTemplates[templateKey]) {
        const template = taskTemplates[templateKey];
        // 仅替换任务内容，不修改名称、触发方式或其它字段
        elements.taskForm.script_body.value = template.script_body;
        showToast(_t('msg.template_applied', { name: template.name }));
      } else {
        // 选择“无模板（自定义）”时不做其它自动清理，仅保留当前用户输入
      }
    });
  }
}
// 模板管理按钮与操作
const manageBtn = document.getElementById('btnManageTemplates');
if (manageBtn) manageBtn.addEventListener('click', openTemplatesModal);
const addTplBtn = document.getElementById('btnAddTemplate');
if (addTplBtn) addTplBtn.addEventListener('click', () => openTemplateEditModal(null));
const editTplBtn = document.getElementById('btnEditTemplate');
if (editTplBtn) editTplBtn.addEventListener('click', () => {
  const id = templatesState.selectedId;
  if (!id) { showToast(_t('prompt.select_template_to_edit')); return; }
  const tpl = templatesState.templates.find(t => Number(t.id) === Number(id));
  if (!tpl) { showToast(_t('error.template_not_found')); return; }
  openTemplateEditModal(tpl);
});
const delTplBtn = document.getElementById('btnDeleteTemplate');
if (delTplBtn) delTplBtn.addEventListener('click', deleteSelectedTemplate);
const expTplBtn = document.getElementById('btnExportTemplates');
if (expTplBtn) expTplBtn.addEventListener('click', async () => {
  const mapping = await api.exportTemplates();
  const content = JSON.stringify(mapping, null, 2);
  // directly open server file picker in save mode (no confirmation)
  openServerFilePicker('/', { mode: 'save', content });
});
const impTplBtn = document.getElementById('btnImportTemplates');
if (impTplBtn) impTplBtn.addEventListener('click', () => {
  openServerFilePicker('/');
});
const previewBtn = document.getElementById('btnPreviewTemplate');
if (previewBtn) previewBtn.addEventListener('click', () => {
  const id = templatesState.selectedId;
  if (!id) { showToast(_t('prompt.select_template_to_preview')); return; }
  const tpl = templatesState.templates.find(t => Number(t.id) === Number(id));
  if (!tpl) { showToast(_t('error.template_not_found')); return; }
  openTemplatePreview(tpl);
});
const tplForm = document.getElementById('templateForm');
if (tplForm) tplForm.addEventListener('submit', saveTemplateFromForm);
bindTemplateImportFile();
// 服务器文件选择：浏览并读取服务器端文件（依赖后端 api/fs 列表与读取接口）
function openServerFilePicker(defaultPath = '/', options = {}) {
  const mode = options.mode || 'open'; // 'open' or 'save'
  const saveContent = options.content || null;
  const modal = document.getElementById('serverFilePickerModal');
  const pathInput = document.getElementById('serverPathInput');
  const listEl = document.getElementById('serverFileList');
  if (!modal || !pathInput || !listEl) {
    // fallback to local file input
    document.getElementById('templateImportFile')?.click();
    return;
  }

  // ensure i18n baseline
  applyModalI18n(modal);

  // prepare UI for mode
  const headerTitleEl = modal.querySelector('h2');
  const subtitleEl = modal.querySelector('.subtitle');
  const btnSelectEl = modal.querySelector('#btnSelectServerFile');
  const btnUseLocalEl = modal.querySelector('#btnUseLocalFile');

  if (mode === 'save') {
    if (headerTitleEl) headerTitleEl.textContent = _t('file.export_to_server_title');
    if (subtitleEl) subtitleEl.textContent = _t('file.export_to_server_subtitle');
    if (btnSelectEl) btnSelectEl.textContent = _t('filepicker.export_selected');
    if (btnUseLocalEl) btnUseLocalEl.textContent = _t('filepicker.export_to_local');
  }

  // normalize path helper
  const normalizePath = (p) => {
    let s = String(p || '/').replace(/\\/g, '/').trim();
    if (!s) s = '/';
    if (s.length > 1) s = s.replace(/\/\/+$/g, '');
    return s;
  };

  pathInput.value = normalizePath(defaultPath);
  listEl.innerHTML = '<div class="muted">' + _t('loading') + '</div>';

  const btnRefresh = modal.querySelector('#btnServerRefresh');
  if (btnRefresh) btnRefresh.onclick = () => fetchServerFiles(normalizePath(pathInput.value));

  if (btnUseLocalEl) {
    btnUseLocalEl.onclick = () => {
      if (mode === 'save') {
        try {
          const filename = 'templates-export.json';
          const blob = new Blob([saveContent || ''], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);
          showToast(_t('file.save_local_result'));
          closeModal(modal);
        } catch (e) {
          showToast(_t('file.save_failed', { err: e && e.message }), true);
        }
      } else {
        document.getElementById('templateImportFile')?.click();
      }
    };
  }

  if (btnSelectEl) {
    btnSelectEl.onclick = async () => {
      const sel = listEl.querySelector('.selected');
      let fp = sel?.dataset?.path || '';
      if (!fp && mode === 'save') {
        fp = normalizePath(pathInput.value);
      }
      if (!fp) { showToast(_t('prompt.select_file')); return; }
      try {
        showToast(_t('loading'));
        if (mode === 'save') {
          const isDir = sel ? sel.dataset.isdir === 'true' : true;
          let targetPath = fp;
          if (isDir) {
            const defaultName = 'templates-export.json';
            targetPath = (fp === '/') ? ('/' + defaultName) : (fp.replace(/\/\/+$/g, '') + '/' + defaultName);
          }
          const resp = await api.request('api/fs/write/' + encodeURIComponent(targetPath), { method: 'POST', body: JSON.stringify({ content: saveContent }), headers: { 'Content-Type': 'application/json', 'X-FS-Path': targetPath } });
          showToast(_t('file.save_result', { path: resp.path || targetPath }));
          closeModal(modal);
          return;
        }
        // read and import
        const payload = await api.request('api/fs/read/' + encodeURIComponent(fp), { headers: { 'X-FS-Path': fp } });
        let obj = null;
        if (payload && Object.prototype.hasOwnProperty.call(payload, '_raw')) {
          try { obj = JSON.parse(payload._raw); } catch (e) { throw new Error(_t('file.invalid_format')); }
        } else if (payload && typeof payload === 'object') {
          obj = payload;
        } else {
          throw new Error(_t('file.invalid_format'));
        }
        const result = await api.importTemplates(obj);
        showToast(_t('file.import_result', { inserted: result?.imported?.inserted || 0, updated: result?.imported?.updated || 0 }));
        closeModal(modal);
        refreshTemplatesList();
        await loadTemplates();
      } catch (err) {
        showToast(_t('file.import_failed', { err: err.message }), true);
      }
    };
  }

  // file list click handling (delegated)
  listEl.onclick = (ev) => {
    const row = ev.target.closest('.srv-file');
    if (!row) return;
    const isDir = row.dataset.isdir === 'true';
    const path = row.dataset.path;
    if (isDir) {
      pathInput.value = normalizePath(path);
      fetchServerFiles(pathInput.value);
      return;
    }
    listEl.querySelectorAll('.srv-file').forEach(r => r.classList.remove('selected'));
    row.classList.add('selected');
  };

  // double click behavior
  listEl.ondblclick = (ev) => {
    const row = ev.target.closest('.srv-file');
    if (!row) return;
    const isDir = row.dataset.isdir === 'true';
    if (isDir) {
      const newPath = normalizePath(row.dataset.path);
      pathInput.value = newPath;
      fetchServerFiles(newPath);
    } else {
      modal.querySelector('#btnSelectServerFile')?.click();
    }
  };

  openModal(modal);
  fetchServerFiles(pathInput.value);
}

async function fetchServerFiles(path) {
  const listEl = document.getElementById('serverFileList');
  if (!listEl) return;
  const normalizePath = (p) => {
    let s = String(p || '/').replace(/\\/g, '/').trim();
    if (!s) s = '/';
    if (s.length > 1) s = s.replace(/\/\/+$/g, '');
    return s;
  };
  const p = normalizePath(path);
  listEl.innerHTML = '<div class="muted">' + _t('loading') + '</div>';
  try {
    const payload = await api.request('api/fs/list/' + encodeURIComponent(p), { headers: { 'X-FS-Path': p } });
    const files = payload && Array.isArray(payload.files) ? payload.files : [];
    renderServerFileList(files, p);
  } catch (err) {
    listEl.innerHTML = '<div class="muted">' + escapeHtml(err && err.message ? err.message : String(err)) + '</div>';
  }
}

function renderServerFileList(files, parentPath) {
  const listEl = document.getElementById('serverFileList');
  if (!listEl) return;
  listEl.innerHTML = '';
  if (!files || !files.length) {
    listEl.innerHTML = '<div class="muted">' + _t('empty.no_files') + '</div>';
    return;
  }
  try {
    const normalize = (p) => String(p || '/').replace(/\\/g, '/').replace(/\/\/+$/g, '') || '/';
    const base = normalize(parentPath);
    const frag = document.createDocumentFragment();
    if (base !== '/') {
      const up = document.createElement('div');
      up.className = 'srv-file srv-dir';
      up.dataset.path = (function () {
        const p = base.replace(/\/\/+$/g, '');
        const idx = p.lastIndexOf('/');
        if (idx <= 0) return '/';
        return p.slice(0, idx) || '/';
      })();
      up.dataset.isdir = 'true';
      up.innerHTML = `<span class="srv-icon">⬆️</span><span class="srv-name">..</span>`;
      frag.appendChild(up);
    }
    files.forEach((f) => {
      const row = document.createElement('div');
      row.className = 'srv-file' + (f.isdir ? ' srv-dir' : ' srv-file-item');
      const path = f.path || (base === '/' ? '/' + (f.name || '') : base + '/' + (f.name || ''));
      row.dataset.path = path;
      row.dataset.isdir = f.isdir ? 'true' : 'false';
      const icon = f.isdir ? '📁' : '📄';
      row.innerHTML = `<span class="srv-icon">${icon}</span><span class="srv-name">${escapeHtml(f.name || '')}</span>`;
      frag.appendChild(row);
    });
    listEl.appendChild(frag);
  } catch (e) {
    listEl.innerHTML = '<div class="muted">' + escapeHtml(e && e.message ? e.message : String(e)) + '</div>';
  }
}
// update buttons state periodically
setInterval(() => {
  const editBtn = document.getElementById('btnEditTemplate');
  const delBtn = document.getElementById('btnDeleteTemplate');
  const previewBtn2 = document.getElementById('btnPreviewTemplate');
  const sel = templatesState.selectedId;
  if (editBtn) editBtn.disabled = !sel;
  if (delBtn) delBtn.disabled = !sel;
  if (previewBtn2) previewBtn2.disabled = !sel;
}, 300);

(async function init() {
  await loadTemplates();
  attachEventListeners();
  toggleSections();
  await loadAccounts({ showError: false });
  await loadTasks();
  startAutoRefresh();
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      loadTasks({ silent: true });
    }
  });
})();
