const state = {
    tasks: [],
    selectedIds: new Set(),
    editingTaskId: null,
    currentResultTaskId: null,
    accounts: [],
    accountLoading: false,
    posixSupported: true,
    defaultAccount: '',
};

const AUTO_REFRESH_INTERVAL = 5000; // 5 seconds
let autoRefreshTimer = null;

const elements = {
    tableBody: document.querySelector('#taskTable tbody'),
    emptyState: document.getElementById('emptyState'),
    taskModal: document.getElementById('taskModal'),
    taskForm: document.getElementById('taskForm'),
    taskModalTitle: document.getElementById('taskModalTitle'),
    triggerTypeSelect: document.getElementById('triggerType'),
    scheduleSection: document.querySelector('[data-section="schedule"]'),
    eventSection: document.querySelector('[data-section="event"]'),
    eventTypeSelect: document.getElementById('eventType'),
    eventScriptSection: document.querySelector('[data-event-subsection="script"]'),
    accountSelect: document.getElementById('accountSelect'),
    accountStatus: document.getElementById('accountStatus'),
    accountReloadBtn: document.getElementById('btnReloadAccounts'),
    preTaskSelect: document.getElementById('preTaskSelect'),
    clearPreTasksBtn: document.getElementById('btnClearPreTasks'),
    resultModal: document.getElementById('resultModal'),
    resultSubtitle: document.getElementById('resultSubtitle'),
    resultList: document.getElementById('resultList'),
    toast: document.getElementById('toast'),
    cronModal: document.getElementById('cronModal'),
    cronForm: document.getElementById('cronForm'),
    cronPreview: document.getElementById('cronPreview'),
    scheduleInput: document.querySelector('input[name="schedule_expression"]'),
};

const buttons = {
    create: document.getElementById('btnCreate'),
    edit: document.getElementById('btnEdit'),
    delete: document.getElementById('btnDelete'),
    run: document.getElementById('btnRun'),
    toggle: document.getElementById('btnToggle'),
    results: document.getElementById('btnResults'),
    refresh: document.getElementById('btnRefresh'),
    clearResults: document.getElementById('btnClearResults'),
    cronGenerator: document.getElementById('btnCronGenerator'),
    applyCron: document.getElementById('btnApplyCron'),
};

const CRON_FIELDS = ['minute', 'hour', 'day', 'month', 'weekday'];
const cronSelects = {};
const cronCustomInputs = {};

CRON_FIELDS.forEach((field) => {
    cronSelects[field] = document.querySelector(`[data-cron-field="${field}"]`);
    cronCustomInputs[field] = document.querySelector(`[data-cron-custom="${field}"]`);
});

const statusMap = {
    success: { label: '成功', className: 'status-success' },
    failed: { label: '失败', className: 'status-failed' },
    running: { label: '运行中', className: 'status-running' },
};

const triggerMap = {
    schedule: '定时',
    event: '事件',
};

const eventTypeMap = {
    script: '条件脚本',
    system_boot: '系统开机',
    system_shutdown: '系统关机',
};

function escapeHtml(value = '') {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const api = {
    async request(url, options = {}) {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        const text = await response.text();
        let payload = {};
        if (text) {
            try {
                payload = JSON.parse(text);
            } catch (err) {
                console.error('JSON parse error', err);
            }
        }
        if (!response.ok) {
            const error = payload?.error || response.statusText;
            throw new Error(error);
        }
        return payload;
    },
    listTasks() {
        return this.request('/api/tasks');
    },
    listAccounts() {
        return this.request('/api/accounts');
    },
    createTask(data) {
        return this.request('/api/tasks', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
    updateTask(id, data) {
        return this.request(`/api/tasks/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },
    deleteTask(id) {
        return this.request(`/api/tasks/${id}`, { method: 'DELETE' });
    },
    runTask(id) {
        return this.request(`/api/tasks/${id}/run`, { method: 'POST' });
    },
    fetchResults(id) {
        return this.request(`/api/tasks/${id}/results?limit=50`);
    },
    deleteResult(id, resultId) {
        return this.request(`/api/tasks/${id}/results/${resultId}`, { method: 'DELETE' });
    },
    clearResults(id) {
        return this.request(`/api/tasks/${id}/results`, { method: 'DELETE' });
    },
    batchTasks(action, taskIds, extra = {}) {
        return this.request('/api/tasks/batch', {
            method: 'POST',
            body: JSON.stringify({ action, task_ids: taskIds, ...extra }),
        });
    },
};

function formatDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function getSelectedTasks() {
    return state.tasks.filter((task) => state.selectedIds.has(task.id));
}

function renderTasks() {
    elements.tableBody.innerHTML = '';
    const { tasks } = state;
    if (!tasks.length) {
        elements.emptyState.classList.remove('hidden');
    } else {
        elements.emptyState.classList.add('hidden');
    }
    tasks.forEach((task) => {
        const tr = document.createElement('tr');
        tr.dataset.id = task.id;
        if (state.selectedIds.has(task.id)) {
            tr.classList.add('selected');
        }
        const latestResult = task.latest_result;
        const status = statusMap[latestResult?.status] || { label: '无记录', className: 'status-unknown' };
        const safeName = escapeHtml(task.name);
        const safeAccount = escapeHtml(task.account);
            let triggerLabel = triggerMap[task.trigger_type] || task.trigger_type;
            if (task.trigger_type === 'event') {
                const subtype = eventTypeMap[task.event_type] || '事件';
                triggerLabel = `${triggerLabel} · ${subtype}`;
            }
        tr.innerHTML = `
            <td><span class="badge ${task.is_active ? 'badge-active' : 'badge-paused'}">${task.is_active ? '已启动' : '已停用'}</span></td>
            <td>
                <div class="task-name">${safeName}</div>
            </td>
            <td>${escapeHtml(formatDate(task.next_run_at))}</td>
                <td><span class="trigger-label">${escapeHtml(triggerLabel)}</span></td>
            <td><span class="status-pill ${status.className}">${status.label}</span></td>
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
    elements.toast.classList.remove('hidden');
    elements.toast.style.background = isError ? 'var(--danger)' : 'var(--primary)';
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 2600);
}

function openModal(modal) {
    modal.classList.remove('hidden');
}

function closeModal(modal) {
    modal.classList.add('hidden');
}

function toggleSections() {
    const type = elements.triggerTypeSelect.value;
    const isSchedule = type !== 'event';
    elements.scheduleSection.classList.toggle('hidden', !isSchedule);
    elements.eventSection.classList.toggle('hidden', isSchedule);
    toggleEventInputs();
}

function toggleEventInputs() {
    const isEvent = elements.triggerTypeSelect.value === 'event';
    elements.eventTypeSelect.disabled = !isEvent;
    if (!isEvent) {
        elements.eventScriptSection.classList.add('hidden');
        elements.taskForm.condition_script.disabled = true;
        elements.taskForm.condition_interval.disabled = true;
        return;
    }
    const isScriptMode = elements.eventTypeSelect.value === 'script';
    elements.eventScriptSection.classList.toggle('hidden', !isScriptMode);
    elements.taskForm.condition_script.disabled = !isScriptMode;
    elements.taskForm.condition_interval.disabled = !isScriptMode;
}

function renderAccountOptions(selectedAccount = '') {
    const select = elements.accountSelect;
    const statusEl = elements.accountStatus;
    const reloadBtn = elements.accountReloadBtn;
    if (!select) return;

    select.innerHTML = '';
    const isReadOnly = !state.posixSupported;
    if (reloadBtn) {
        reloadBtn.disabled = state.accountLoading;
        reloadBtn.classList.toggle('hidden', isReadOnly);
    }

    if (state.accountLoading) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '加载中...';
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        if (statusEl) {
            statusEl.textContent = '正在获取可用账号...';
        }
        return;
    }

    if (!state.accounts.length) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = state.posixSupported ? '无可用账号' : '暂不可用';
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        if (statusEl) {
            statusEl.textContent = state.posixSupported
                ? '未找到属于系统组 0 / 1000 / 1001 的账号'
                : 'Windows 环境未能检测到当前用户，请重新登录后再试';
        }
        return;
    }

    if (isReadOnly) {
        const defaultAccount = state.accounts[0] || state.defaultAccount || '';
        const option = document.createElement('option');
        option.value = defaultAccount;
        option.textContent = defaultAccount || '当前登录账号';
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        if (statusEl) {
            statusEl.textContent = defaultAccount
                ? ''
                : '';
        }
        return;
    }

    select.disabled = false;
    let hasSelected = false;
    const legacyAccount = selectedAccount && !state.accounts.includes(selectedAccount) ? selectedAccount : '';
    if (legacyAccount) {
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = `${legacyAccount}（需重新选择）`;
        placeholder.disabled = true;
        placeholder.selected = true;
        select.appendChild(placeholder);
    }

    state.accounts.forEach((account) => {
        const option = document.createElement('option');
        option.value = account;
        option.textContent = account;
        if (!hasSelected && account === selectedAccount) {
            option.selected = true;
            hasSelected = true;
        }
        select.appendChild(option);
    });

    if (!hasSelected && !legacyAccount && select.options.length) {
        select.options[0].selected = true;
    }

    if (statusEl) {
        statusEl.textContent = legacyAccount
            ? `当前任务账号 ${legacyAccount} 不在允许范围，请重新选择`
            : '';
    }
}

async function loadAccounts({ showError = true, preferredAccount = '' } = {}) {
    const select = elements.accountSelect;
    if (!select) {
        return;
    }
    const previousValue = preferredAccount || select.value || '';
    state.accountLoading = true;
    renderAccountOptions(previousValue);
    try {
        const response = await api.listAccounts();
        state.accounts = response.data || [];
        if (response.meta) {
            if (Object.prototype.hasOwnProperty.call(response.meta, 'posix_supported')) {
                state.posixSupported = Boolean(response.meta.posix_supported);
            }
            if (Object.prototype.hasOwnProperty.call(response.meta, 'default_account')) {
                state.defaultAccount = response.meta.default_account || '';
            }
        }
        if (!state.posixSupported && !state.accounts.length && state.defaultAccount) {
            state.accounts = [state.defaultAccount];
        }
    } catch (error) {
        if (showError) {
            showToast(`加载账号失败：${error.message}`, true);
        }
    } finally {
        state.accountLoading = false;
        renderAccountOptions(preferredAccount || previousValue);
    }
}

function populatePreTaskOptions(currentId = null, selected = []) {
    elements.preTaskSelect.innerHTML = '';
    state.tasks
        .filter((task) => task.id !== currentId)
        .forEach((task) => {
            const option = document.createElement('option');
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
    const preferredAccount = task?.account || '';
    renderAccountOptions(preferredAccount);
    if (!state.accountLoading && !state.accounts.length) {
        loadAccounts({ showError: false, preferredAccount });
    }
    populatePreTaskOptions(state.editingTaskId, task?.pre_task_ids || []);
    if (task) {
        elements.taskModalTitle.textContent = `编辑任务：${task.name}`;
        elements.taskForm.name.value = task.name;
        elements.triggerTypeSelect.value = task.trigger_type;
        elements.eventTypeSelect.value = task.event_type || 'script';
        elements.taskForm.is_active.checked = Boolean(task.is_active);
        if (elements.scheduleInput) {
            elements.scheduleInput.value = task.schedule_expression || '';
        }
        elements.taskForm.condition_script.value = task.condition_script || '';
        elements.taskForm.condition_interval.value = task.condition_interval || 60;
        elements.taskForm.script_body.value = task.script_body || '';
    } else {
        elements.taskModalTitle.textContent = '新建任务';
        elements.eventTypeSelect.value = 'script';
        elements.taskForm.condition_interval.value = 60;
        if (elements.scheduleInput) {
            elements.scheduleInput.value = '';
        }
    }
    toggleSections();
    openModal(elements.taskModal);
}

function collectFormData() {
    const data = {
        name: elements.taskForm.name.value.trim(),
        account: (elements.accountSelect?.value || '').trim(),
        trigger_type: elements.triggerTypeSelect.value,
        is_active: elements.taskForm.is_active.checked,
        pre_task_ids: Array.from(elements.preTaskSelect.selectedOptions).map((opt) => Number(opt.value)),
        script_body: elements.taskForm.script_body.value.trim(),
    };
    if (data.trigger_type === 'schedule') {
        const scheduleField = elements.scheduleInput;
        data.schedule_expression = scheduleField ? scheduleField.value.trim() : '';
    } else {
        data.event_type = elements.eventTypeSelect.value;
        if (data.event_type === 'script') {
            data.condition_script = elements.taskForm.condition_script.value.trim();
            data.condition_interval = Number(elements.taskForm.condition_interval.value) || 60;
        }
    }
    return data;
}

function sanitizeCronValue(value = '') {
    return value.replace(/[^0-9*\/,\-]/g, '').replace(/,{2,}/g, ',');
}

function getCronFieldValue(field) {
    const select = cronSelects[field];
    if (!select) {
        return '*';
    }
    if (select.value === 'custom') {
        const input = cronCustomInputs[field];
        const sanitized = sanitizeCronValue(input?.value || '');
        return sanitized || '*';
    }
    return select.value || '*';
}

function updateCronPreview() {
    const expression = CRON_FIELDS.map((field) => getCronFieldValue(field)).join(' ');
    if (elements.cronPreview) {
        elements.cronPreview.textContent = expression;
    }
    return expression;
}

function prefillCronGenerator(expression = '') {
    const normalized = expression.trim();
    const tokens = normalized ? normalized.split(/\s+/) : [];
    CRON_FIELDS.forEach((field, index) => {
        const select = cronSelects[field];
        const input = cronCustomInputs[field];
        if (!select) {
            return;
        }
        const rawPart = tokens[index] || '*';
        const normalizedPart = rawPart === '*' ? '*' : sanitizeCronValue(rawPart) || '*';
        const hasOption = Array.from(select.options).some((option) => option.value === normalizedPart);
        if (hasOption) {
            select.value = normalizedPart;
            if (input) {
                input.classList.add('hidden');
                input.value = '';
            }
        } else {
            select.value = 'custom';
            if (input) {
                input.classList.remove('hidden');
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
            throw new Error('请完整填写必填字段');
        }
        if (state.accountLoading) {
            throw new Error('账号列表加载中，请稍后重试');
        }
        if (!state.accounts.length) {
            if (state.posixSupported) {
                throw new Error('未找到可用账号，请确认系统组 0 / 1000 / 1001 中存在账号');
            }
            throw new Error('未能检测到默认账号，请重新登录或刷新页面');
        }
        if (!state.posixSupported) {
            payload.account = state.accounts[0] || state.defaultAccount || payload.account;
        } else if (!state.accounts.includes(payload.account)) {
            throw new Error('请选择属于系统组 0 / 1000 / 1001 的账号');
        }
        if (payload.trigger_type === 'schedule' && !payload.schedule_expression) {
            throw new Error('Cron 表达式不能为空');
        }
        if (payload.trigger_type === 'event') {
            if (!payload.event_type) {
                payload.event_type = 'script';
            }
            if (payload.event_type === 'script' && !payload.condition_script) {
                throw new Error('请填写条件脚本');
            }
        }
        if (state.editingTaskId) {
            await api.updateTask(state.editingTaskId, payload);
            showToast('任务已更新');
        } else {
            await api.createTask(payload);
            showToast('任务已创建');
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
            showToast(`加载任务失败：${error.message}`, true);
        } else {
            console.error('自动刷新任务失败', error);
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
        showToast('请先选择任务');
        return;
    }
    if (!window.confirm(`确认删除选中的 ${selected.length} 个任务？`)) {
        return;
    }
    try {
        const response = await api.batchTasks('delete', selected);
        const result = response.result || {};
        const { deleted = [], missing = [] } = result;
        const deletedCount = deleted.length;
        const missingCount = missing.length;
        state.selectedIds.clear();
        await loadTasks();
        let message = deletedCount ? `已删除 ${deletedCount} 个任务` : '';
        if (missingCount) {
            message += `${message ? '；' : ''}${missingCount} 个任务不存在`;
        }
        showToast(message || '未删除任何任务');
    } catch (error) {
        showToast(error.message, true);
    }
}

async function runSelectedTasks() {
    const selected = Array.from(state.selectedIds);
    if (!selected.length) {
        showToast('请选择要运行的任务');
        return;
    }
    try {
        const response = await api.batchTasks('run', selected);
        const result = response.result || {};
        const {
            queued = [],
            running = [],
            blocked = [],
            missing = [],
        } = result;
        const queuedCount = queued.length;
        const runningCount = running.length;
        const blockedCount = blocked.length;
        const missingCount = missing.length;
        const parts = [];
        if (queuedCount) parts.push(`已触发 ${queuedCount} 个任务`);
        if (runningCount) parts.push(`${runningCount} 个任务正在执行`);
        if (blockedCount) parts.push(`${blockedCount} 个任务等待前置完成`);
        if (missingCount) parts.push(`${missingCount} 个任务不存在`);
        showToast(parts.join('；') || '未触发任何任务');
    } catch (error) {
        showToast(error.message, true);
    }
}

async function toggleSelectedTask() {
    const selected = Array.from(state.selectedIds);
    if (!selected.length) {
        showToast('请选择任务');
        return;
    }
    try {
        const selectedTasks = state.tasks.filter((task) => selected.includes(task.id));
        if (!selectedTasks.length) {
            throw new Error('任务不存在');
        }
        const shouldEnable = selectedTasks.some((task) => !task.is_active);
        const action = shouldEnable ? 'enable' : 'disable';
        const response = await api.batchTasks(action, selected);
        const result = response.result || {};
        const { updated = [], unchanged = [], missing = [] } = result;
        const updatedCount = updated.length;
        const unchangedCount = unchanged.length;
        const missingCount = missing.length;
        await loadTasks();
        const verb = shouldEnable ? '启用' : '停用';
        const parts = [];
        if (updatedCount) parts.push(`已${verb} ${updatedCount} 个任务`);
        if (unchangedCount) parts.push(`${unchangedCount} 个任务状态本已满足`);
        if (missingCount) parts.push(`${missingCount} 个任务不存在`);
        showToast(parts.join('；') || `没有任务完成${verb}`);
    } catch (error) {
        showToast(error.message, true);
    }
}

async function openResultModal() {
    const selected = Array.from(state.selectedIds);
    if (selected.length !== 1) {
        showToast('请选择单个任务');
        return;
    }
    const taskId = selected[0];
    const task = state.tasks.find((item) => item.id === taskId);
    if (!task) {
        showToast('任务不存在', true);
        return;
    }
    state.currentResultTaskId = taskId;
    elements.resultSubtitle.textContent = `${task.name} (#${task.id})`;
    openModal(elements.resultModal);
    await refreshResults();
}

async function refreshResults() {
    if (!state.currentResultTaskId) return;
    try {
        const { data } = await api.fetchResults(state.currentResultTaskId);
        renderResults(data || []);
    } catch (error) {
        showToast(error.message, true);
    }
}

function renderResults(results) {
    elements.resultList.innerHTML = '';
    if (!results.length) {
        elements.resultList.innerHTML = '<p class="empty">暂无执行记录</p>';
        return;
    }
    results.forEach((result) => {
        const status = statusMap[result.status] || { label: result.status, className: 'status-unknown' };
        const card = document.createElement('article');
        card.className = 'result-card';
        card.innerHTML = `
            <header>
                <div>
                    <div class="status-pill ${status.className}">${status.label}</div>
                    <span class="muted">触发：${escapeHtml(result.trigger_reason)}</span>
                </div>
                <div class="muted">${escapeHtml(formatDate(result.started_at))} - ${escapeHtml(formatDate(result.finished_at))}</div>
                <button class="ghost" data-delete="${result.id}">删除</button>
            </header>
            <pre>${escapeHtml(result.log || '')}</pre>
        `;
        card.querySelector('[data-delete]').addEventListener('click', async () => {
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
    if (!state.currentResultTaskId) return;
    if (!window.confirm('确认清空该任务的全部历史记录？')) {
        return;
    }
    try {
        await api.clearResults(state.currentResultTaskId);
        await refreshResults();
        showToast('执行记录已清空');
    } catch (error) {
        showToast(error.message, true);
    }
}

function closeModalOnOverlay(event) {
    if (event.target.matches('[data-close]')) {
        const modal = event.target.closest('.modal');
        closeModal(modal);
    }
    if (event.target.classList.contains('modal')) {
        closeModal(event.target);
    }
}

function attachEventListeners() {
    elements.tableBody.addEventListener('click', (event) => {
        const row = event.target.closest('tr');
        if (!row) return;
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

    buttons.create.addEventListener('click', () => openTaskModal());
    buttons.edit.addEventListener('click', () => {
        const selected = getSelectedTasks();
        if (selected.length !== 1) {
            showToast('请选择单个任务');
            return;
        }
        openTaskModal(selected[0]);
    });
    buttons.delete.addEventListener('click', deleteSelectedTasks);
    buttons.run.addEventListener('click', runSelectedTasks);
    buttons.toggle.addEventListener('click', toggleSelectedTask);
    buttons.results.addEventListener('click', openResultModal);
    buttons.refresh.addEventListener('click', loadTasks);
    buttons.clearResults.addEventListener('click', clearResultHistory);
    elements.clearPreTasksBtn.addEventListener('click', () => {
        Array.from(elements.preTaskSelect.options).forEach((option) => {
            option.selected = false;
        });
    });
    if (elements.accountReloadBtn) {
        elements.accountReloadBtn.addEventListener('click', () => loadAccounts({ showError: true }));
    }

    elements.taskForm.addEventListener('submit', handleFormSubmit);
    document.querySelectorAll('[data-close]').forEach((btn) => btn.addEventListener('click', closeModalOnOverlay));
    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeModal(modal);
            }
        });
    });

    elements.triggerTypeSelect.addEventListener('change', toggleSections);
    elements.eventTypeSelect.addEventListener('change', toggleEventInputs);

    CRON_FIELDS.forEach((field) => {
        const select = cronSelects[field];
        const input = cronCustomInputs[field];
        if (select) {
            select.addEventListener('change', () => {
                const useCustom = select.value === 'custom';
                if (input) {
                    input.classList.toggle('hidden', !useCustom);
                    if (useCustom && !input.value.trim()) {
                        input.value = '*';
                    }
                    if (!useCustom) {
                        input.value = '';
                    }
                }
                updateCronPreview();
            });
        }
        if (input) {
            input.addEventListener('input', () => {
                const sanitized = sanitizeCronValue(input.value);
                if (sanitized !== input.value) {
                    input.value = sanitized;
                }
                updateCronPreview();
            });
        }
    });

    document.addEventListener('click', (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest('#btnCronGenerator') && elements.cronModal) {
            event.preventDefault();
            const current = elements.scheduleInput?.value || '';
            prefillCronGenerator(current);
            openModal(elements.cronModal);
            return;
        }
        if (target.closest('#btnApplyCron') && elements.cronModal) {
            event.preventDefault();
            const expression = updateCronPreview();
            if (elements.scheduleInput) {
                elements.scheduleInput.value = expression;
            }
            closeModal(elements.cronModal);
        }
    });
}

(async function init() {
    attachEventListeners();
    toggleSections();
    await loadAccounts({ showError: false });
    await loadTasks();
    startAutoRefresh();
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            loadTasks({ silent: true });
        }
    });
})();
