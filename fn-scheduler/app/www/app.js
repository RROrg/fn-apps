import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };
window.__APP_SDK__ = sdk;
const API_ENDPOINT = "./api";

const state = {
  tasks: [],
  selectedIds: new Set(),
  sort: {
    key: "latest_status",
    direction: "asc",
  },
  editingTaskId: null,
  currentResultTaskId: null,
  resultLogCache: new Map(),
  accounts: [],
  accountLoading: false,
  posixSupported: true,
  defaultAccount: "",
  language: "zh-CN",
  theme: "light",
};

const I18N = {
  "zh-CN": {
    "app.title": "任务计划",
    "app.subtitle": "管理定时与条件触发的脚本任务",
    about: "关于",
    close: "关闭",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    "btn.refresh": "刷新",
    "btn.settings": "设置",
    "btn.create": "新建",
    "btn.edit": "编辑",
    "btn.delete": "删除",
    "btn.run": "立即运行",
    "btn.stop": "终止",
    "btn.toggle": "启用/停用",
    "btn.results": "查看结果",
    "btn.manage_templates": "模板管理",
    "table.enabled": "是否启动",
    "table.name": "任务名称",
    "table.next_run": "下次运行时间",
    "table.trigger": "触发类型",
    "table.latest_status": "最新状态",
    "table.account": "账号",
    "empty.no_tasks": "暂无任务，点击“新建”开始配置。",
    "empty.no_files": "目录为空",
    "modal.task.new": "新建任务",
    "field.name": "任务名称",
    "field.account": "用户账号",
    "field.trigger": "触发方式",
    "trigger.schedule": "定时",
    "trigger.event": "事件",
    "trigger.condition": "条件",
    "trigger.manual": "手动",
    "field.cron": "Cron 表达式",
    "field.cron_hint": "标准 5 字段 Cron，分钟 小时 日 月 周（周字段 0=周一）",
    "btn.cron_generator": "生成器",
    "field.event_type": "事件类型",
    "field.event_hint": "系统开/关机事件在服务启动或停止时各触发一次",
    "field.keep_success_log": "保留成功日志",
    "field.keep_failure_log": "保留失败日志",
    "event.script_note": "条件脚本（返回 0 触发）",
    "event.interval_label": "检测间隔（秒）",
    "btn.apply_cron": "填入 Cron",
    "cron.current_expression": "当前表达式：",
    "cron.hint":
      "顺序：分钟 小时 日 月 周；自定义字段可使用数字、*、/、,、-，为空时默认 *",
    "cron.placeholder": "例如：*/5 * * * *",
    "cron.generator_subtitle": "通过选择常见规则快速生成 Cron 表达式",
    "cron.field.minute": "分钟",
    "cron.field.hour": "小时",
    "cron.field.day": "日期（天）",
    "cron.field.month": "月份",
    "cron.field.weekday": "星期（0=周一）",
    "cron.opt.minute.every": "每分钟 *",
    "cron.opt.minute.zero": "整点 0",
    "cron.opt.minute.5": "每 5 分钟 */5",
    "cron.opt.minute.10": "每 10 分钟 */10",
    "cron.opt.minute.15": "每 15 分钟 */15",
    "cron.opt.hour.every": "每小时 *",
    "cron.opt.hour.2": "每 2 小时 */2",
    "cron.opt.hour.6": "每 6 小时 */6",
    "cron.opt.hour.12": "每 12 小时 */12",
    "cron.opt.hour.midnight": "每天 0 点",
    "cron.opt.hour.noon": "每天 12 点",
    "cron.opt.day.every": "每天 *",
    "cron.opt.day.1": "每月 1 日",
    "cron.opt.day.15": "每月 15 日",
    "cron.opt.day.1_5": "每月 1-5 日",
    "cron.opt.month.every": "每月 *",
    "cron.opt.month.quarter": "每季度 */3",
    "cron.opt.month.jan": "1 月",
    "cron.opt.month.jun": "6 月",
    "cron.opt.month.dec": "12 月",
    "cron.opt.weekday.every": "每周 *",
    "cron.opt.weekday.workdays": "工作日 0-4",
    "cron.opt.weekday.mon": "周一 0",
    "cron.opt.weekday.fri": "周五 4",
    "cron.opt.weekday.sat": "周六 5",
    "cron.opt.weekday.sun": "周日 6",
    "cron.opt.custom": "自定义",
    "cron.placeholder_list": "例如 0,15,30,45",
    "cron.placeholder_hour_list": "例如 0,6,12,18",
    "cron.placeholder_day_list": "例如 1-5 或 1,15",
    "cron.placeholder_month_list": "例如 3,6,9,12",
    "cron.placeholder_weekday_list": "例如 0,2,4",
    "template.preview_title": "模板预览",
    "template.col.key": "Key",
    "template.col.name": "名称",
    "template.col.preview": "预览（首行）",
    "template.key_hint": "Key（可选，留空自动生成）",
    "template.name_label": "名称",
    "template.script_label": "脚本内容",
    "validation.required_fields": "请完整填写必填字段",
    "validation.accounts_loading": "账号列表加载中，请稍后重试",
    "validation.no_accounts_posix":
      "未找到可用账号，请确认系统组 0 / 1000 / 1001 中存在账号",
    "validation.no_default_account": "未能检测到默认账号，请重新登录或刷新页面",
    "validation.account_not_in_group":
      "请选择属于系统组 0 / 1000 / 1001 的账号",
    "validation.cron_required": "Cron 表达式不能为空",
    "validation.script_required": "请填写条件脚本",
    "msg.task_updated": "任务已更新",
    "msg.task_created": "任务已创建",
    "error.load_templates": "加载模板失败：{status}",
    "file.invalid_format": "文件格式不正确",
    loading: "加载中...",
    loading_accounts: "正在获取可用账号...",
    no_accounts: "无可用账号",
    not_available: "暂不可用",
    "account.not_found_posix": "未找到属于系统组 0 / 1000 / 1001 的账号",
    "account.windows_not_detected":
      "Windows 环境未能检测到当前用户，请重新登录后再试",
    "label.current_logged_in_account": "当前登录账号",
    "label.trigger": "触发：",
    "placeholder.needs_reselect": "（需重新选择）",
    "error.task_account_not_allowed":
      "当前任务账号 {acc} 不在允许范围，请重新选择",
    "error.load_accounts": "加载账号失败：{err}",
    "cron.invalid": "表达式无效",
    "cron.preview": "执行时间预览：",
    "cron.search_exceeded":
      "已超出搜索范围（{months} 个月），可能在更远时间触发",
    "list.sep": "；",
    "error.load_tasks": "加载任务失败：{err}",
    "field.pre_tasks": "前置任务",
    "btn.clear_pre_tasks": "全取消",
    "field.pre_tasks_hint": "仅当所选任务最近一次成功后才执行",
    "field.template": "任务模板",
    "field.template_hint": "选择模板会自动填充任务内容",
    "template.edit_title": "新增模板",
    "template.placeholder": "无模板（自定义）",
    "field.script": "任务内容",
    "field.immediate": "立即启动",
    "btn.cancel": "取消",
    "btn.ok": "确定",
    "btn.save": "保存",
    "modal.results.title": "执行结果",
    "modal.settings.title": "运行设置",
    "modal.settings.subtitle": "调整结果保留与执行超时等全局参数",
    "settings.group.results.title": "结果与日志",
    "settings.group.results.subtitle":
      "控制执行记录保留数量，以及结果列表默认显示多少日志内容。",
    "settings.group.execution.title": "执行与超时",
    "settings.group.execution.subtitle":
      "控制任务脚本和条件脚本的最长执行时间，避免任务长时间卡住。",
    "btn.clear": "清空",
    "modal.templates.title": "模板管理",
    "modal.templates.subtitle": "增加、编辑、删除模板，或导入/导出为 JSON",
    "btn.add": "新增",
    "btn.preview": "预览",
    "btn.import": "导入 JSON",
    "btn.export": "导出 JSON",
    "btn.import_local": "从电脑导入",
    "btn.import_nas": "从 NAS 导入",
    "btn.export_local": "导出到电脑",
    "btn.export_nas": "导出到 NAS",
    "cron.generator_title": "Cron 生成器",
    "status.pretask_failed": "前置·失败",
    "status.success": "成功",
    "status.failed": "失败",
    "status.running": "运行中",
    "status.condition_failed": "条件·失败",
    "status.no_record": "无记录",
    "status.enabled": "已启动",
    "status.disabled": "已停用",
    "event.script": "条件脚本",
    "event.system_boot": "系统开机",
    "event.system_shutdown": "系统关机",
    "event.short.script": "脚本",
    "event.short.system_boot": "开机",
    "event.short.system_shutdown": "关机",
    "prompt.select_template": "请先选择模板",
    "prompt.select_file": "请选择文件",
    "confirm.delete_template": "确认删除所选模板？",
    "template.updated": "模板已更新",
    "template.created": "模板已创建",
    "template.deleted": "模板已删除",
    "error.task_name_exists": "任务名已存在，请修改后重试",
    "error.template_key_exists": "模板 Key 已存在，请修改后重试",
    "error.database_integrity": "数据库约束错误，请检查输入",
    "error.save_template": "保存模板失败：{err}",
    "error.delete_template": "删除失败：{err}",
    "file.import_result": "导入完成：新增 {inserted}，更新 {updated}",
    "file.import_failed": "导入失败：{err}",
    "file.save_result": "已保存到 {path}",
    "file.save_local_result": "已保存到本地",
    "file.save_failed": "导出失败：{err}",
    "file.nas_open_hint": "已在系统文件管理器中打开 NAS，请将文件放到目标位置后复制/移动",
    "file.open_failed": "打开文件管理器失败：{err}",
    "file.native_picker_unavailable": "当前环境不支持系统文件管理器",
    "msg.template_applied": "已应用模板：{name}（仅替换任务内容）",
    "prompt.select_template_to_edit": "请选择要编辑的模板",
    "error.template_not_found": "模板未找到",
    "prompt.select_template_to_preview": "请选择一个模板以预览",
    "prompt.select_single_task": "请选择单个任务",
    "prompt.select_task": "请先选择任务",
    "confirm.delete_selected_tasks": "确认删除选中的 {n} 个任务？",
    "msg.deleted_n": "已删除 {n} 个任务",
    "msg.missing_n": "{n} 个任务不存在",
    "msg.no_tasks_deleted": "未删除任何任务",
    "prompt.select_task_to_run": "请选择要运行的任务",
    "prompt.select_task_to_stop": "请选择要终止的任务",
    "msg.triggered_n": "已触发 {n} 个任务",
    "msg.stopped_n": "已终止 {n} 个任务",
    "msg.running_n": "{n} 个任务正在执行",
    "msg.not_running_n": "{n} 个任务未在运行",
    "msg.pretask_failed_n": "{n} 个任务前置·失败",
    "msg.condition_failed_n": "{n} 个任务条件·失败",
    "msg.no_tasks_triggered": "未触发任何任务",
    "msg.no_tasks_stopped": "未终止任何任务",
    "error.task_not_found": "任务不存在",
    "verb.enable": "启用",
    "verb.disable": "停用",
    "msg.action_completed": "已{verb} {n} 个任务",
    "msg.unchanged_count": "{n} 个任务状态本已满足",
    "msg.no_tasks_completed": "没有任务完成{verb}",
    "field.settings.result_retention": "结果保留条数",
    "field.settings.result_retention_hint":
      "每个任务最多保留多少条已完成结果，0 表示不限制。",
    "field.settings.task_timeout": "任务超时时间（秒）",
    "field.settings.task_timeout_hint":
      "脚本执行超过该时间会被终止，0 表示不限制。",
    "field.settings.condition_timeout": "条件脚本超时时间（秒）",
    "field.settings.condition_timeout_hint":
      "条件脚本执行超过该时间会被终止，最小 1 秒。",
    "field.settings.result_preview_limit": "结果预览长度",
    "field.settings.result_preview_limit_hint":
      "前端结果列表默认展示的日志摘要长度，最小 256 字符。",
    "msg.settings_saved": "设置已保存",
    "msg.settings_saved_pruned": "设置已保存，并清理了 {n} 条旧结果",
    "confirm.clear_results": "确认清空当前任务的全部执行记录？",
    "msg.results_cleared": "执行记录已清空",
    "results.no_records": "暂无执行记录",
    "results.expand_log": "展开完整日志",
    "results.collapse_log": "收起完整日志",
    "results.loading_log": "加载中...",
    "results.log_truncated": "日志较大，已显示前 {limit} 个字符，总长度 {n}。",
    "results.log_full": "当前已显示完整日志。",
  },
  "en-US": {
    "app.title": "Scheduler",
    "app.subtitle": "Manage scheduled and condition-triggered script tasks",
    about: "About",
    close: "Close",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    "btn.refresh": "Refresh",
    "btn.settings": "Settings",
    "btn.create": "Create",
    "btn.edit": "Edit",
    "btn.delete": "Delete",
    "btn.run": "Run now",
    "btn.stop": "Stop",
    "btn.toggle": "Enable/Disable",
    "btn.results": "Results",
    "btn.manage_templates": "Templates",
    "table.enabled": "Enabled",
    "table.name": "Name",
    "table.next_run": "Next Run",
    "table.trigger": "Trigger",
    "table.latest_status": "Latest",
    "table.account": "Account",
    "empty.no_tasks": "No tasks yet — click Create to get started.",
    "empty.no_files": "No files",
    "modal.task.new": "New Task",
    "field.name": "Name",
    "field.account": "Account",
    "field.trigger": "Trigger Type",
    "trigger.schedule": "Schedule",
    "trigger.event": "Event",
    "trigger.condition": "Condition",
    "trigger.manual": "Manual",
    "field.cron": "Cron expression",
    "field.cron_hint":
      "Standard 5-field cron: minute hour day month weekday (weekday 0=Mon)",
    "btn.cron_generator": "Generator",
    "field.event_type": "Event Type",
    "field.event_hint": "System boot/shutdown triggers on service start/stop",
    "field.keep_success_log": "Keep success logs",
    "field.keep_failure_log": "Keep failure logs",
    "event.script_note": "Condition script (exit code 0 triggers)",
    "event.interval_label": "Check interval (seconds)",
    "btn.apply_cron": "Apply Cron",
    "cron.current_expression": "Current expression:",
    "cron.hint":
      "Order: minute hour day month weekday; use numbers, *, /, , and -; default *",
    "cron.placeholder": "e.g.: */5 * * * *",
    "cron.generator_subtitle":
      "Quickly build cron expressions by selecting common rules",
    "cron.field.minute": "Minute",
    "cron.field.hour": "Hour",
    "cron.field.day": "Day (date)",
    "cron.field.month": "Month",
    "cron.field.weekday": "Weekday(0=Mon)",
    "cron.opt.minute.every": "Every minute *",
    "cron.opt.minute.zero": "On :00",
    "cron.opt.minute.5": "Every 5 minutes */5",
    "cron.opt.minute.10": "Every 10 minutes */10",
    "cron.opt.minute.15": "Every 15 minutes */15",
    "cron.opt.hour.every": "Every hour *",
    "cron.opt.hour.2": "Every 2 hours */2",
    "cron.opt.hour.6": "Every 6 hours */6",
    "cron.opt.hour.12": "Every 12 hours */12",
    "cron.opt.hour.midnight": "Daily 0:00",
    "cron.opt.hour.noon": "Daily 12:00",
    "cron.opt.day.every": "Every day *",
    "cron.opt.day.1": "Day 1",
    "cron.opt.day.15": "Day 15",
    "cron.opt.day.1_5": "Days 1-5",
    "cron.opt.month.every": "Every month *",
    "cron.opt.month.quarter": "Every quarter */3",
    "cron.opt.month.jan": "Jan",
    "cron.opt.month.jun": "Jun",
    "cron.opt.month.dec": "Dec",
    "cron.opt.weekday.every": "Every week *",
    "cron.opt.weekday.workdays": "Workdays 0-4",
    "cron.opt.weekday.mon": "Mon 0",
    "cron.opt.weekday.fri": "Fri 4",
    "cron.opt.weekday.sat": "Sat 5",
    "cron.opt.weekday.sun": "Sun 6",
    "cron.opt.custom": "Custom",
    "cron.placeholder_list": "e.g.: 0,15,30,45",
    "cron.placeholder_hour_list": "e.g.: 0,6,12,18",
    "cron.placeholder_day_list": "e.g.: 1-5 or 1,15",
    "cron.placeholder_month_list": "e.g.: 3,6,9,12",
    "cron.placeholder_weekday_list": "e.g.: 0,2,4",
    "template.preview_title": "Template Preview",
    "template.col.key": "Key",
    "template.col.name": "Name",
    "template.col.preview": "Preview (first line)",
    "template.key_hint": "Key (optional, auto-generated if empty)",
    "template.name_label": "Name",
    "template.script_label": "Script",
    "field.pre_tasks": "Pre-tasks",
    "btn.clear_pre_tasks": "Clear All",
    "field.pre_tasks_hint": "Only runs after selected tasks last succeeded",
    "field.template": "Template",
    "field.template_hint": "Choose a template to fill task content",
    "template.edit_title": "New Template",
    "template.placeholder": "No template (custom)",
    "field.script": "Script",
    "field.immediate": "Start immediately",
    "btn.cancel": "Cancel",
    "btn.ok": "OK",
    "btn.save": "Save",
    "modal.results.title": "Execution Results",
    "modal.settings.title": "Runtime Settings",
    "modal.settings.subtitle":
      "Adjust global limits such as retained results and execution timeouts",
    "settings.group.results.title": "Results and logs",
    "settings.group.results.subtitle":
      "Control how many execution records are kept and how much log content is shown by default.",
    "settings.group.execution.title": "Execution and timeouts",
    "settings.group.execution.subtitle":
      "Control how long task and condition scripts may run before being stopped.",
    "btn.clear": "Clear",
    "modal.templates.title": "Template Manager",
    "modal.templates.subtitle":
      "Add, edit, delete templates or import/export JSON",
    "btn.add": "Add",
    "btn.preview": "Preview",
    "btn.import": "Import JSON",
    "btn.export": "Export JSON",
    "btn.import_local": "Import from computer",
    "btn.import_nas": "Import from NAS",
    "btn.export_local": "Export to computer",
    "btn.export_nas": "Export to NAS",
    "cron.generator_title": "Cron Generator",
    "validation.required_fields": "Please fill required fields",
    "validation.accounts_loading":
      "Account list is loading, please try again later",
    "validation.no_accounts_posix":
      "No available accounts found; ensure system groups 0 / 1000 / 1001 contain accounts",
    "validation.no_default_account":
      "Default account not detected, please re-login or refresh the page",
    "validation.account_not_in_group":
      "Please select an account in system group 0 / 1000 / 1001",
    "validation.cron_required": "Cron expression is required",
    "validation.script_required": "Please provide a condition script",
    "msg.task_updated": "Task updated",
    "msg.task_created": "Task created",
    "error.load_templates": "Failed to load templates: {status}",
    "file.invalid_format": "Invalid file format",
    loading: "Loading...",
    loading_accounts: "Fetching available accounts...",
    no_accounts: "No accounts available",
    not_available: "Not available",
    "account.not_found_posix":
      "No accounts found in system groups 0 / 1000 / 1001",
    "account.windows_not_detected":
      "Windows environment could not detect the current user; please re-login",
    "label.current_logged_in_account": "Current logged-in account",
    "label.trigger": "Trigger:",
    "placeholder.needs_reselect": "(needs reselect)",
    "error.task_account_not_allowed":
      "Current task account {acc} is not allowed, please re-select",
    "error.load_accounts": "Failed to load accounts: {err}",
    "cron.invalid": "Invalid expression",
    "cron.preview": "Execution preview:",
    "cron.search_exceeded":
      "Search range exceeded ({months} months), next occurrences may be further in time",
    "list.sep": "; ",
    "error.load_tasks": "Failed to load tasks: {err}",
    "status.pretask_failed": "Pretask failed",
    "status.success": "Success",
    "status.failed": "Failed",
    "status.running": "Running",
    "status.condition_failed": "Condition failed",
    "status.no_record": "No record",
    "status.enabled": "Enabled",
    "status.disabled": "Disabled",
    "event.script": "Condition script",
    "event.system_boot": "System boot",
    "event.system_shutdown": "System shutdown",
    "event.short.script": "Script",
    "event.short.system_boot": "Boot",
    "event.short.system_shutdown": "Shutdown",
    "prompt.select_template": "Please select a template first",
    "prompt.select_file": "Please select a file",
    "confirm.delete_template": "Delete selected template?",
    "template.updated": "Template updated",
    "template.created": "Template created",
    "template.deleted": "Template deleted",
    "error.task_name_exists": "Task name already exists, please choose another",
    "error.template_key_exists":
      "Template key already exists, please choose another",
    "error.database_integrity":
      "Database integrity error, please check your input",
    "error.save_template": "Save template failed: {err}",
    "error.delete_template": "Delete failed: {err}",
    "file.import_result":
      "Import finished: inserted {inserted}, updated {updated}",
    "file.import_failed": "Import failed: {err}",
    "file.save_result": "Saved to {path}",
    "file.save_local_result": "Saved to local",
    "file.save_failed": "Save failed: {err}",
    "file.nas_open_hint": "Opened NAS in the system file manager. Move/copy the file to the target location.",
    "file.open_failed": "Failed to open file manager: {err}",
    "file.native_picker_unavailable": "System file manager is unavailable in this environment",
    "msg.template_applied": "Applied template: {name} (content only)",
    "prompt.select_template_to_edit": "Please select a template to edit",
    "error.template_not_found": "Template not found",
    "prompt.select_template_to_preview": "Please select a template to preview",
    "prompt.select_single_task": "Please select a single task",
    "prompt.select_task": "Please select a task",
    "confirm.delete_selected_tasks": "Delete selected {n} tasks?",
    "msg.deleted_n": "Deleted {n} tasks",
    "msg.missing_n": "{n} tasks not found",
    "msg.no_tasks_deleted": "No tasks deleted",
    "prompt.select_task_to_run": "Please select tasks to run",
    "prompt.select_task_to_stop": "Please select tasks to stop",
    "msg.triggered_n": "Triggered {n} tasks",
    "msg.stopped_n": "Stopped {n} tasks",
    "msg.running_n": "{n} tasks running",
    "msg.not_running_n": "{n} tasks are not running",
    "msg.pretask_failed_n": "{n} tasks pretask failed",
    "msg.condition_failed_n": "{n} tasks condition failed",
    "msg.no_tasks_triggered": "No tasks triggered",
    "msg.no_tasks_stopped": "No tasks stopped",
    "error.task_not_found": "Task not found",
    "verb.enable": "enable",
    "verb.disable": "disable",
    "msg.action_completed": "{verb} {n} tasks",
    "msg.unchanged_count": "{n} tasks already satisfied",
    "msg.no_tasks_completed": "No tasks completed ({verb})",
    "field.settings.result_retention": "Retained results",
    "field.settings.result_retention_hint":
      "Maximum finished results kept per task; 0 means unlimited.",
    "field.settings.task_timeout": "Task timeout (seconds)",
    "field.settings.task_timeout_hint":
      "A script running longer than this will be terminated; 0 means unlimited.",
    "field.settings.condition_timeout": "Condition script timeout (seconds)",
    "field.settings.condition_timeout_hint":
      "A condition script running longer than this will be terminated; minimum 1 second.",
    "field.settings.result_preview_limit": "Result preview length",
    "field.settings.result_preview_limit_hint":
      "Default log preview length shown in the result list; minimum 256 characters.",
    "msg.settings_saved": "Settings saved",
    "msg.settings_saved_pruned": "Settings saved and pruned {n} old results",
    "confirm.clear_results":
      "Clear all execution records for the current task?",
    "msg.results_cleared": "Execution records cleared",
    "results.no_records": "No execution records",
    "results.expand_log": "Expand full log",
    "results.collapse_log": "Collapse full log",
    "results.loading_log": "Loading...",
    "results.log_truncated":
      "Large log: showing the first {limit} characters out of {n}.",
    "results.log_full": "Showing the full log.",
  },
};

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

  const docTitle = document.querySelector("title[data-i18n]");
  if (docTitle) {
    docTitle.textContent = t(docTitle.getAttribute("data-i18n"));
    // 页面交互：宿主环境同步窗口标题（站内 / 标签页标题）
    if (sdk && typeof sdk.setTitle === "function") {
      sdk.setTitle(docTitle.textContent).catch(() => {});
    }
  }
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;
    const attr = el.getAttribute("data-i18n-attr");
    if (attr) {
      el.setAttribute(attr, t(key));
    } else {
      el.textContent = t(key);
    }
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
    el.setAttribute("aria-label", t(el.dataset.i18nTitle));
  });

  if (rerender && languageChanged) {
    window.dispatchEvent(new CustomEvent("scheduler:i18nchange"));
  }
  return languageChanged;
}

// Map common backend error messages to localized, user-friendly messages
function mapApiErrorMessage(raw) {
  if (!raw) return null;
  const s = String(raw).toLowerCase();
  if (s.includes("task name already exists"))
    return t("error.task_name_exists");
  if (s.includes("template key already exists"))
    return t("error.template_key_exists");
  if (s.includes("database integrity")) return t("error.database_integrity");
  return null;
}

const AUTO_REFRESH_INTERVAL = 5000; // 5 seconds
const DEFAULT_SCHEDULE_EXPRESSION = "0 0 * * *";
let autoRefreshTimer = null;
let loadTasksPromise = null;

const elements = {
  tableHead: document.querySelector("#taskTable thead"),
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
  accountReloadBtn: document.getElementById("btnReloadAccounts"),
  preTaskSelect: document.getElementById("preTaskSelect"),
  preTaskChecklist: document.getElementById("preTaskChecklist"),
  clearPreTasksBtn: document.getElementById("btnClearPreTasks"),
  resultModal: document.getElementById("resultModal"),
  resultSubtitle: document.getElementById("resultSubtitle"),
  resultList: document.getElementById("resultList"),
  settingsModal: document.getElementById("settingsModal"),
  settingsForm: document.getElementById("settingsForm"),
  toast: document.getElementById("toast"),
  cronModal: document.getElementById("cronModal"),
  cronForm: document.getElementById("cronForm"),
  cronPreview: document.getElementById("cronPreview"),
  cronNextTimes: document.getElementById("cronNextTimes"),
  scheduleInput: document.querySelector('input[name="schedule_expression"]'),
};

let taskTemplates = {};

function buildTemplateLookup(templates) {
  const lookup = {};
  if (!Array.isArray(templates)) {
    return lookup;
  }

  templates.forEach((template) => {
    if (template && template.key) {
      lookup[template.key] = template;
    }
  });

  return lookup;
}

async function loadTemplates() {
  try {
    const payload = await api("list-templates");
    taskTemplates = buildTemplateLookup(payload?.data);
    renderTemplateOptions();
  } catch (err) {
    taskTemplates = {};
    renderTemplateOptions();
  }
}

function renderTemplateOptions() {
  const select = document.getElementById("templateSelect");
  if (!select) return;
  // 保留首项 "无模板（自定义）"
  const current = select.value || "";
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = t("template.placeholder");
  select.appendChild(placeholder);
  Object.keys(taskTemplates || {}).forEach((key) => {
    const tpl = taskTemplates[key];
    const opt = document.createElement("option");
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

function updateTemplateActionState() {
  const hasSelection = Boolean(templatesState.selectedId);
  const editButton = document.getElementById("btnEditTemplate");
  const deleteButton = document.getElementById("btnDeleteTemplate");
  const previewButton = document.getElementById("btnPreviewTemplate");
  if (editButton) editButton.disabled = !hasSelection;
  if (deleteButton) deleteButton.disabled = !hasSelection;
  if (previewButton) previewButton.disabled = !hasSelection;
}

async function refreshTemplatesList() {
  try {
    const resp = await api("list-templates");
    if (resp && Array.isArray(resp.data)) {
      templatesState.templates = resp.data;
    } else {
      templatesState.templates = [];
    }
    renderTemplatesTable();
  } catch (err) {
    showToast(t("file.import_failed", { err: err.message }), true);
  }
}

function renderTemplatesTable() {
  const tbody = document.querySelector("#templatesTable tbody");
  if (!tbody) {
    updateTemplateActionState();
    return;
  }
  tbody.innerHTML = "";
  templatesState.templates.forEach((t) => {
    const tr = document.createElement("tr");
    tr.dataset.id = t.id;
    tr.dataset.key = t.key || "";
    tr.innerHTML = `<td>${escapeHtml(t.key || "")}</td><td>${escapeHtml(t.name || "")}</td><td>${escapeHtml((t.script_body || "").split("\n")[0] || "")}</td>`;
    tr.tabIndex = 0;
    if (String(templatesState.selectedId) === String(t.id)) {
      tr.classList.add("selected");
      tr.setAttribute("aria-selected", "true");
    } else {
      tr.setAttribute("aria-selected", "false");
    }
    tbody.appendChild(tr);
  });
  // click selection
  const tbodyEl = document.querySelector("#templatesTable tbody");
  if (tbodyEl) {
    tbodyEl.onclick = (ev) => {
      const row = ev.target.closest("tr");
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
      const row = ev.target.closest("tr");
      if (!row) return;
      const id = Number(row.dataset.id);
      const tpl = templatesState.templates.find(
        (t) => Number(t.id) === Number(id),
      );
      if (tpl) openTemplateEditModal(tpl);
    };
    tbodyEl.onkeydown = (ev) => {
      const row = ev.target.closest("tr");
      if (!row) return;
      const id = Number(row.dataset.id);
      // 空格或回车切换选择，回车为编辑
      if (ev.key === " " || ev.key === "Spacebar") {
        ev.preventDefault();
        if (templatesState.selectedId === id) templatesState.selectedId = null;
        else templatesState.selectedId = id;
        renderTemplatesTable();
        return;
      }
      if (ev.key === "Enter") {
        ev.preventDefault();
        const tpl = templatesState.templates.find(
          (t) => Number(t.id) === Number(id),
        );
        if (tpl) openTemplateEditModal(tpl);
      }
    };
  }
  // 尝试将焦点移到被选中的行以便用户看到高亮
  if (templatesState.selectedId) {
    const selRow = document.querySelector(
      `#templatesTable tbody tr[data-id="${templatesState.selectedId}"]`,
    );
    if (selRow) selRow.focus();
  }
  updateTemplateActionState();
}

function openTemplatesModal() {
  refreshTemplatesList();
  const modal = document.getElementById("templatesModal");
  if (modal) openModal(modal);
}

function openTemplateEditModal(editing = null) {
  templatesState.editingId = editing ? editing.id : null;
  const modal = document.getElementById("templateEditModal");
  const form = document.getElementById("templateForm");
  const title = document.getElementById("templateEditTitle");
  if (!form || !modal) return;
  form.reset();
  if (editing) {
    title.textContent = `${t("btn.edit")}：${editing.name}`;
    form.key.value = editing.key || "";
    form.name.value = editing.name || "";
    form.script_body.value = editing.script_body || "";
  } else {
    title.textContent = t("btn.add");
  }
  openModal(modal);
}

function openTemplatePreview(tpl) {
  const modal = document.getElementById("templatePreviewModal");
  const subtitle = document.getElementById("templatePreviewSubtitle");
  const content = document.getElementById("templatePreviewContent");
  if (!modal || !content) return;
  subtitle.textContent = tpl ? `${tpl.key || ""} · ${tpl.name || ""}` : "";
  content.textContent = tpl ? tpl.script_body || "" : "";
  openModal(modal);
}

async function saveTemplateFromForm(ev) {
  ev.preventDefault();
  const form = document.getElementById("templateForm");
  if (!form) return;
  const data = {
    key: form.key.value.trim(),
    name: form.name.value.trim(),
    script_body: form.script_body.value.trim(),
  };
  try {
    if (templatesState.editingId) {
      await api("update-template", { id: templatesState.editingId, ...data });
      showToast(t("template.updated"));
    } else {
      await api("create-template", data);
      showToast(t("template.created"));
    }
    closeModal(document.getElementById("templateEditModal"));
    refreshTemplatesList();
    await loadTemplates();
  } catch (err) {
    showToast(t("error.save_template", { err: err.message }), true);
  }
}

async function deleteSelectedTemplate() {
  const id = templatesState.selectedId;
  if (!id) {
    showToast(t("prompt.select_template"));
    return;
  }
  if (!(await showConfirm(t("confirm.delete_template")))) {
    return;
  }
  try {
    await api("delete-template", { id });
    templatesState.selectedId = null;
    refreshTemplatesList();
    await loadTemplates();
    showToast(t("template.deleted"));
  } catch (err) {
    showToast(t("error.delete_template", { err: err.message }), true);
  }
}

// 归一化 SDK 文件选择返回值：可能是 string / [obj] / { path } / { paths }。
function _normalizePicked(picked) {
  if (!picked) return null;
  if (Array.isArray(picked)) {
    const first = picked[0];
    if (!first) return null;
    return typeof first === "object" ? first.path || first.value || "" : first;
  }
  if (typeof picked === "object") {
    const p = picked.path || picked.value || picked.filePath;
    if (p) return p;
    const arr = picked.paths || picked.values || picked.files;
    if (Array.isArray(arr) && arr.length) {
      const first = arr[0];
      return typeof first === "object" ? first.path || "" : first;
    }
    return "";
  }
  return typeof picked === "string" ? picked : "";
}

// 同时支持 host 型（pickUserFile/pickSharedFile/pickFile）与独立网页（openAppAuth 授权）。
// 通过 SDK pickFile（即系统文件管理器）选取路径；用户取消或环境不支持时返回 null。
async function pickSystemPath(options) {
  const sdk = window.__APP_SDK__;
  if (!sdk) return null;

  const opts = options || {};

  // 独立网页：无宿主桥接，走 openAppAuth 路由授权（适配 pickFile 类方法）。
  if (sdk.isStandaloneWeb) {
    if (typeof sdk.openAppAuth === "function") {
      try {
        await sdk.openAppAuth(
          "pickFile",
          {
            appName: "fn-scheduler",
            directory: Boolean(opts.directory),
            accept: opts.accept,
            redirectUri: "/app/fn-scheduler/callback.html",
          },
          { target: "_blank", features: "width=750,height=630" },
        );
      } catch (_err) {
        // 授权页被浏览器拦截或环境不支持，交由调用方兜底
      }
    }
    return null;
  }

  // 宿主环境：优先 hosted pickFile，退化到 openFileManager。
  if (typeof sdk.pickFile === "function") {
    try {
      const picked = await sdk.pickFile(opts);
      return _normalizePicked(picked);
    } catch (_err) {
      // 用户取消或平台不支持，返回 null
    }
  }
  return null;
}

// 打开系统文件管理器到指定目录。
async function openSystemFileManager(path) {
  const sdk = window.__APP_SDK__;
  if (sdk && typeof sdk.openFileManager === "function") {
    try {
      await sdk.openFileManager(path || "/");
    } catch (_err) {
      showToast(t("file.open_failed"), true);
    }
  } else {
    showToast(t("file.native_picker_unavailable"), true);
  }
}

function bindTemplateImportFile() {
  const fileInput = document.getElementById("templateImportFile");
  if (!fileInput) return;
  fileInput.onchange = async () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    try {
      const text = await f.text();
      const obj = JSON.parse(text);
      if (typeof obj !== "object") throw new Error(t("file.invalid_format"));
      const resp = await api("import-templates", { mapping: obj });
      showToast(
        t("file.import_result", {
          inserted: resp.imported.inserted,
          updated: resp.imported.updated,
        }),
      );
      refreshTemplatesList();
      await loadTemplates();
    } catch (err) {
      showToast(t("file.import_failed", { err: err.message }), true);
    } finally {
      fileInput.value = "";
    }
  };
}

function bindTaskTemplateSelection() {
  const templateSelect = document.getElementById("templateSelect");
  if (!templateSelect) {
    return;
  }

  templateSelect.addEventListener("change", function () {
    const templateKey = this.value;
    if (templateKey && taskTemplates[templateKey]) {
      const template = taskTemplates[templateKey];
      elements.taskForm.script_body.value = template.script_body;
      showToast(t("msg.template_applied", { name: template.name }));
    }
  });
}

function bindTemplateManagementEventListeners() {
  const manageButton = document.getElementById("btnManageTemplates");
  if (manageButton) {
    manageButton.addEventListener("click", openTemplatesModal);
  }

  const addTemplateButton = document.getElementById("btnAddTemplate");
  if (addTemplateButton) {
    addTemplateButton.addEventListener("click", () =>
      openTemplateEditModal(null),
    );
  }

  const editTemplateButton = document.getElementById("btnEditTemplate");
  if (editTemplateButton) {
    editTemplateButton.addEventListener("click", () => {
      const id = templatesState.selectedId;
      if (!id) {
        showToast(t("prompt.select_template_to_edit"));
        return;
      }
      const template = templatesState.templates.find(
        (item) => Number(item.id) === Number(id),
      );
      if (!template) {
        showToast(t("error.template_not_found"));
        return;
      }
      openTemplateEditModal(template);
    });
  }

  const deleteTemplateButton = document.getElementById("btnDeleteTemplate");
  if (deleteTemplateButton) {
    deleteTemplateButton.addEventListener("click", deleteSelectedTemplate);
  }

  // 导出到 NAS：直接调用系统文件管理器/系统选择器选取目标目录并写入
  const exportNasButton = document.getElementById("btnExportNasTemplate");
  if (exportNasButton) {
    exportNasButton.addEventListener("click", async () => {
      try {
        const mapping = await api("export-templates");
        const content = JSON.stringify(mapping, null, 2);
        const targetDir = await pickSystemPath({ directory: true });
        if (!targetDir) {
          // 用户取消或环境不支持选择器时，退化为打开系统文件管理器
          await openSystemFileManager("/");
          showToast(t("file.nas_open_hint"), true);
          return;
        }
        const filename = "templates-export.json";
        const path =
          targetDir.replace(/\/+$/, "") + "/" + filename;
        await api("fs-write", { path, content });
        showToast(t("file.save_result", { path }));
      } catch (err) {
        showToast(t("file.save_failed", { err: err.message }), true);
      }
    });
  }

  // 从 NAS 导入：直接调用系统文件管理器/系统选择器选取文件并导入
  const importNasButton = document.getElementById("btnImportNasTemplate");
  if (importNasButton) {
    importNasButton.addEventListener("click", async () => {
      try {
        const path = await pickSystemPath({});
        if (!path) {
          // 用户取消选择
          return;
        }
        showToast(t("loading"));
        const resp = await api("fs-read", { path });
        const mapping =
          resp && resp._raw ? JSON.parse(resp._raw) : resp;
        if (typeof mapping !== "object" || Array.isArray(mapping) || !mapping) {
          throw new Error(t("file.invalid_format"));
        }
        const imp = await api("import-templates", { mapping });
        showToast(
          t("file.import_result", {
            inserted: imp.imported ? imp.imported.inserted : 0,
            updated: imp.imported ? imp.imported.updated : 0,
          }),
        );
        refreshTemplatesList();
        await loadTemplates();
      } catch (err) {
        showToast(t("file.import_failed", { err: err.message }), true);
      }
    });
  }

  // 导出到电脑：直接下载 JSON 到本地浏览器
  const exportLocalButton = document.getElementById("btnExportLocalTemplate");
  if (exportLocalButton) {
    exportLocalButton.addEventListener("click", async () => {
      try {
        showToast(t("loading"));
        const mapping = await api("export-templates");
        const content = JSON.stringify(mapping, null, 2);
        const filename = "templates-export.json";
        const blob = new Blob([content], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        showToast(t("file.save_local_result"));
      } catch (err) {
        showToast(t("file.save_failed", { err: err.message }), true);
      }
    });
  }

  // 从电脑导入：触发隐藏的本地文件选择
  const importLocalButton = document.getElementById("btnImportLocalTemplate");
  if (importLocalButton) {
    importLocalButton.addEventListener("click", () => {
      document.getElementById("templateImportFile")?.click();
    });
  }

  const previewTemplateButton = document.getElementById("btnPreviewTemplate");
  if (previewTemplateButton) {
    previewTemplateButton.addEventListener("click", () => {
      const id = templatesState.selectedId;
      if (!id) {
        showToast(t("prompt.select_template_to_preview"));
        return;
      }
      const template = templatesState.templates.find(
        (item) => Number(item.id) === Number(id),
      );
      if (!template) {
        showToast(t("error.template_not_found"));
        return;
      }
      openTemplatePreview(template);
    });
  }

  const templateForm = document.getElementById("templateForm");
  if (templateForm) {
    templateForm.addEventListener("submit", saveTemplateFromForm);
  }

  bindTemplateImportFile();
}

const buttons = {
  create: document.getElementById("btnCreate"),
  edit: document.getElementById("btnEdit"),
  delete: document.getElementById("btnDelete"),
  run: document.getElementById("btnRun"),
  stop: document.getElementById("btnStop"),
  toggle: document.getElementById("btnToggle"),
  results: document.getElementById("btnResults"),
  about: document.getElementById("btnAbout"),
  settings: document.getElementById("btnSettings"),
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
  running: { label: "status.running", className: "status-running" },
  success: { label: "status.success", className: "status-success" },
  failed: { label: "status.failed", className: "status-failed" },
  condition_failed: {
    label: "status.condition_failed",
    className: "status-condition-failed",
  },
  pretask_failed: {
    label: "status.pretask_failed",
    className: "status-pretask-failed",
  },
};

const taskStatusPriority = {
  running: 0,
  success: 1,
  failed: 2,
  condition_failed: 3,
  pretask_failed: 4,
};

const SORT_DIRECTIONS = {
  asc: "ascending",
  desc: "descending",
};

function getTaskSortPriority(task) {
  const status = task?.latest_result?.status || "";
  if (Object.prototype.hasOwnProperty.call(taskStatusPriority, status)) {
    return taskStatusPriority[status];
  }
  return 5;
}

function getTaskTriggerLabel(task) {
  let triggerLabel = t(
    triggerMap[task.trigger_type] || task.trigger_type || "",
  );
  if (task.trigger_type === "event") {
    const subtype = getEventLabel(task.event_type) || t("trigger.event");
    triggerLabel = `${triggerLabel} · ${subtype}`;
  }
  return triggerLabel;
}

function getTaskSortValue(task, key) {
  switch (key) {
    case "enabled":
      return task.is_active ? 0 : 1;
    case "name":
      return String(task.name || "");
    case "next_run": {
      const value = task.next_run_at
        ? Date.parse(task.next_run_at)
        : Number.NaN;
      return Number.isFinite(value) ? value : null;
    }
    case "trigger":
      return getTaskTriggerLabel(task);
    case "latest_status":
      return getTaskSortPriority(task);
    case "account":
      return String(task.account || "");
    default:
      return null;
  }
}

function compareTaskSortValues(left, right, direction) {
  const leftMissing = left == null;
  const rightMissing = right == null;
  if (leftMissing || rightMissing) {
    if (leftMissing && rightMissing) {
      return 0;
    }
    return leftMissing ? 1 : -1;
  }
  if (typeof left === "string" || typeof right === "string") {
    const result = String(left).localeCompare(String(right), "zh-CN", {
      numeric: true,
      sensitivity: "base",
    });
    return direction === "desc" ? -result : result;
  }
  if (left === right) {
    return 0;
  }
  if (direction === "desc") {
    return left > right ? -1 : 1;
  }
  return left > right ? 1 : -1;
}

function sortTasks() {
  const { key, direction } = state.sort;
  state.tasks.sort((leftTask, rightTask) => {
    const valueDiff = compareTaskSortValues(
      getTaskSortValue(leftTask, key),
      getTaskSortValue(rightTask, key),
      direction,
    );
    if (valueDiff !== 0) {
      return valueDiff;
    }
    return leftTask.id - rightTask.id;
  });
}

function updateSortHeaders() {
  if (!elements.tableHead) {
    return;
  }
  elements.tableHead.querySelectorAll("th[data-sort-key]").forEach((header) => {
    const key = header.dataset.sortKey;
    if (key === state.sort.key) {
      header.setAttribute(
        "aria-sort",
        SORT_DIRECTIONS[state.sort.direction] || "none",
      );
      return;
    }
    header.setAttribute("aria-sort", "none");
  });
}

function toggleTaskSort(sortKey) {
  if (!sortKey) {
    return;
  }
  if (state.sort.key === sortKey) {
    state.sort.direction = state.sort.direction === "asc" ? "desc" : "asc";
  } else {
    state.sort.key = sortKey;
    state.sort.direction = "asc";
  }
  sortTasks();
  updateSortHeaders();
  renderTasks();
}

const triggerMap = {
  schedule: "trigger.schedule",
  event: "trigger.event",
};

const eventTypeMap = {
  script: "event.script",
  system_boot: "event.system_boot",
  system_shutdown: "event.system_shutdown",
};

// 响应式短标签（用于窄屏显示），存放为 i18n 键
const eventTypeShortMap = {
  script: "event.short.script",
  system_boot: "event.short.system_boot",
  system_shutdown: "event.short.system_shutdown",
};

function isNarrow() {
  return window.innerWidth <= 480;
}

function getEventLabel(key) {
  if (isNarrow()) return t(eventTypeShortMap[key] || eventTypeMap[key] || key);
  return t(eventTypeMap[key] || key);
}

function updateEventTypeOptionLabels() {
  const select = elements.eventTypeSelect;
  if (!select) {
    return;
  }
  const useShortLabel = isNarrow();
  for (const option of select.options) {
    const value = option.value;
    if (
      value === "script" ||
      value === "system_boot" ||
      value === "system_shutdown"
    ) {
      option.textContent = useShortLabel
        ? t(eventTypeShortMap[value] || eventTypeMap[value] || value)
        : t(eventTypeMap[value] || eventTypeShortMap[value] || value);
    }
  }
}

function handleViewportChange() {
  updateEventTypeOptionLabels();
  renderTasks();
}

function escapeHtml(value = "") {
  const s = String(value == null ? "" : value);
  // single pass replace using map for better performance
  return s.replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return ch;
    }
  });
}

function applyModalI18n(modal) {
  if (!modal) return;
  // apply data-i18n and data-i18n-attr within modal
  modal.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;
    const attr = el.getAttribute("data-i18n-attr");
    try {
      const v = t(key);
      if (attr) el.setAttribute(attr, v);
      else el.textContent = v;
    } catch (e) {
      // noop
    }
  });
}

async function api(action, data = {}) {
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    credentials: "include",
    body: JSON.stringify({ action, ...data }),
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
    const rawMessage =
      (payload && (payload.error || payload._raw)) ||
      response.statusText ||
      `HTTP ${response.status}`;
    const friendly = mapApiErrorMessage(rawMessage) || rawMessage;
    console.error("API error", { action, status: response.status, payload });
    throw new Error(friendly);
  }
  return payload || {};
}

function formatDate(value) {
  if (!value) {
    return "—";
  }
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
    const statusLabel = t(status.label);
    const safeName = escapeHtml(task.name);
    const safeAccount = escapeHtml(task.account);
    let triggerLabel = getTaskTriggerLabel(task);
    if (task.trigger_type === "event") {
      if (isNarrow()) {
        triggerLabel = getEventLabel(task.event_type) || t("trigger.event");
      }
    }

    tr.innerHTML = `
            <td><span class="badge ${task.is_active ? "badge-active" : "badge-paused"}">${task.is_active ? t("status.enabled") : t("status.disabled")}</span></td>
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
  buttons.stop.disabled = selectedCount === 0;
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

function showConfirm(
  message,
  { okText = t("btn.ok"), cancelText = t("btn.cancel") } = {},
) {
  return new Promise((resolve) => {
    let modal = document.getElementById("__confirmModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "__confirmModal";
      modal.className = "modal hidden";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <div><h2></h2></div>
            <div class="modal-header-actions"><button class="icon-btn" data-close type="button" aria-label="${t("close")}">&times;</button></div>
          </div>
          <div class="modal-body confirm-modal-body"></div>
          <div class="modal-actions confirm-modal-actions">
            <button class="ghost" id="__confirmCancel"></button>
            <button class="primary" id="__confirmOk"></button>
          </div>
        </div>`;
      document.body.appendChild(modal);
      // wire close on overlay
      modal.addEventListener("click", (ev) => {
        if (ev.target === modal) {
          closeModal(modal);
          resolve(false);
        }
      });
      modal.querySelectorAll("[data-close]").forEach((btn) =>
        btn.addEventListener("click", () => {
          closeModal(modal);
          resolve(false);
        }),
      );
    }
    const hdr = modal.querySelector("h2");
    const body = modal.querySelector(".modal-body");
    const okBtn = modal.querySelector("#__confirmOk");
    const cancelBtn = modal.querySelector("#__confirmCancel");
    if (hdr) hdr.textContent = "";
    if (body) body.textContent = message || "";
    if (okBtn) {
      okBtn.textContent = okText;
      okBtn.onclick = () => {
        closeModal(modal);
        resolve(true);
      };
    }
    if (cancelBtn) {
      cancelBtn.textContent = cancelText;
      cancelBtn.onclick = () => {
        closeModal(modal);
        resolve(false);
      };
    }
    applyModalI18n(modal);
    openModal(modal);
  });
}

function openModal(modal) {
  if (!modal) return;
  const active = document.activeElement;
  if (active instanceof HTMLElement && !modal.contains(active)) {
    modal.__returnFocusEl = active;
  } else if (!(modal.__returnFocusEl instanceof HTMLElement)) {
    modal.__returnFocusEl = null;
  }
  modal.inert = false;
  modal.setAttribute("aria-hidden", "false");
  modal.classList.remove("hidden");
  queueMicrotask(() => {
    const focusTarget = modal.querySelector(
      "[autofocus], button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
    );
    if (focusTarget instanceof HTMLElement) {
      focusTarget.focus();
    }
  });
}

function closeModal(modal) {
  if (!modal) return;
  const active = document.activeElement;
  if (active instanceof HTMLElement && modal.contains(active)) {
    active.blur();
  }
  modal.inert = true;
  modal.setAttribute("aria-hidden", "true");
  modal.classList.add("hidden");
  const returnFocusEl = modal.__returnFocusEl;
  queueMicrotask(() => {
    if (
      returnFocusEl instanceof HTMLElement &&
      returnFocusEl.isConnected &&
      !returnFocusEl.hasAttribute("disabled")
    ) {
      returnFocusEl.focus();
      return;
    }
    if (document.body instanceof HTMLElement) {
      document.body.focus?.();
    }
  });
  // restore i18n-driven texts for any modal (will reset server file picker as well)
  try {
    applyModalI18n(modal);
    // restore placeholder attributes if present
    modal.querySelectorAll("[data-i18n-attr]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const attr = el.getAttribute("data-i18n-attr");
      if (key && attr) el.setAttribute(attr, t(key));
    });
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
  const reloadBtn = elements.accountReloadBtn;
  if (!select) {
    return;
  }

  select.innerHTML = "";
  const isReadOnly = !state.posixSupported;
  if (reloadBtn) {
    reloadBtn.disabled = state.accountLoading;
    reloadBtn.classList.toggle("hidden", isReadOnly);
  }

  if (state.accountLoading) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = t("loading");
    option.disabled = true;
    option.selected = true;
    select.appendChild(option);
    select.disabled = true;
    return;
  }

  if (!state.accounts.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = state.posixSupported
      ? t("no_accounts")
      : t("not_available");
    option.disabled = true;
    option.selected = true;
    select.appendChild(option);
    select.disabled = true;
    return;
  }

  if (isReadOnly) {
    const defaultAccount = state.accounts[0] || state.defaultAccount || "";
    const option = document.createElement("option");
    option.value = defaultAccount;
    option.textContent =
      defaultAccount || t("label.current_logged_in_account");
    option.selected = true;
    select.appendChild(option);
    select.disabled = true;
    return;
  }

  select.disabled = false;
  let hasSelected = false;
  const unavailableSelectedAccount =
    selectedAccount && !state.accounts.includes(selectedAccount)
      ? selectedAccount
      : "";
  if (unavailableSelectedAccount) {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = `${unavailableSelectedAccount} ${t("placeholder.needs_reselect")}`;
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

  if (!hasSelected && !unavailableSelectedAccount && select.options.length) {
    select.options[0].selected = true;
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
    const response = await api("list-accounts");
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
      showToast(t("error.load_accounts", { err: error.message }), true);
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
  renderPreTaskChecklist();
}

function renderPreTaskChecklist() {
  if (!elements.preTaskChecklist || !elements.preTaskSelect) {
    return;
  }

  const options = Array.from(elements.preTaskSelect.options);
  if (!options.length) {
    elements.preTaskChecklist.innerHTML = `<div class="pretask-empty">${escapeHtml(t("empty.no_tasks"))}</div>`;
    return;
  }

  const html = options
    .map((opt) => {
      const id = String(opt.value);
      const checked = opt.selected ? " checked" : "";
      return `<label class="pretask-item"><input type="checkbox" data-pretask-id="${escapeHtml(id)}"${checked}><span>${escapeHtml(opt.textContent || "")}</span></label>`;
    })
    .join("");
  elements.preTaskChecklist.innerHTML = html;
}

function openTaskModal(task = null) {
  state.editingTaskId = task?.id ?? null;
  elements.taskForm.reset();

  // 重置模板选择
  const templateSelect = document.getElementById("templateSelect");
  if (templateSelect) {
    templateSelect.value = "";
  }

  const preferredAccount = task?.account || "";
  renderAccountOptions(preferredAccount);
  if (!state.accountLoading && !state.accounts.length) {
    loadAccounts({ showError: false, preferredAccount });
  }
  populatePreTaskOptions(state.editingTaskId, task?.pre_task_ids || []);
  if (task) {
    elements.taskModalTitle.textContent = `${t("btn.edit")}：${task.name}`;
    elements.taskForm.name.value = task.name;
    elements.triggerTypeSelect.value = task.trigger_type;
    elements.eventTypeSelect.value = task.event_type || "system_shutdown";
    elements.taskForm.is_active.checked = Boolean(task.is_active);
    elements.taskForm.keep_success_log.checked =
      task.keep_success_log !== false;
    elements.taskForm.keep_failure_log.checked =
      task.keep_failure_log !== false;
    if (elements.scheduleInput) {
      elements.scheduleInput.value = task.schedule_expression || "";
    }
    elements.taskForm.condition_script.value = task.condition_script || "";
    elements.taskForm.condition_interval.value = task.condition_interval || 60;
    elements.taskForm.script_body.value = task.script_body || "";
  } else {
    elements.taskModalTitle.textContent = t("modal.task.new");
    elements.eventTypeSelect.value = "system_shutdown";
    elements.taskForm.condition_interval.value = 60;
    elements.taskForm.keep_success_log.checked = true;
    elements.taskForm.keep_failure_log.checked = true;
    if (elements.scheduleInput) {
      elements.scheduleInput.value = DEFAULT_SCHEDULE_EXPRESSION;
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
    keep_success_log: elements.taskForm.keep_success_log.checked,
    keep_failure_log: elements.taskForm.keep_failure_log.checked,
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
      elements.cronNextTimes.textContent = t("cron.invalid");
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
          t("cron.preview") +
          result.times.map((t) => `<div>${t}</div>`).join("");
      } else {
        elements.cronNextTimes.textContent = "";
      }
      if (result.exceeded) {
        const hint = document.createElement("div");
        hint.className = "muted";
        hint.style.marginTop = "6px";
        hint.textContent = t("cron.search_exceeded", {
          months: result.maxMonths,
        });
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
    if (parts.length !== 5) {
      return { times: [], valid: false };
    }
    // 解析每个字段
    function parseField(str, min, max) {
      if (str === "*") {
        return Array.from({ length: max - min + 1 }, (_, i) => i + min);
      }
      let out = new Set();
      str.split(",").forEach((token) => {
        if (token.includes("/")) {
          let [range, step] = token.split("/");
          step = parseInt(step);
          if (!step || step < 1) {
            return;
          }
          let vals =
            range === "*"
              ? Array.from({ length: max - min + 1 }, (_, i) => i + min)
              : parseRange(range, min, max);
          vals.forEach((v, i) => {
            if ((v - min) % step === 0) {
              out.add(v);
            }
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
      if (token === "*") {
        return Array.from({ length: max - min + 1 }, (_, i) => i + min);
      }
      if (token.includes("-")) {
        let [a, b] = token.split("-").map(Number);
        if (isNaN(a) || isNaN(b) || a > b) {
          return [];
        }
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

    for (
      let offset = 0;
      offset < maxMonths && results.length < count;
      offset++
    ) {
      const y =
        base.getFullYear() + Math.floor((base.getMonth() + offset) / 12);
      const mIndex = (base.getMonth() + offset) % 12; // 0-based month index
      const monthNum = mIndex + 1;
      if (!months.includes(monthNum)) continue;
      const daysInThisMonth = new Date(y, mIndex + 1, 0).getDate();
      // 遍历该月的每一天，检查是否符合日或周条件
      for (
        let day = 1;
        day <= daysInThisMonth && results.length < count;
        day++
      ) {
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
          for (
            let mi = 0;
            mi < minutes.length && results.length < count;
            mi++
          ) {
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
      throw new Error(t("validation.required_fields"));
    }
    if (state.accountLoading) {
      throw new Error(t("validation.accounts_loading"));
    }
    if (!state.accounts.length) {
      if (state.posixSupported) {
        throw new Error(t("validation.no_accounts_posix"));
      }
      throw new Error(t("validation.no_default_account"));
    }
    if (!state.posixSupported) {
      payload.account =
        state.accounts[0] || state.defaultAccount || payload.account;
    } else if (!state.accounts.includes(payload.account)) {
      throw new Error(t("validation.account_not_in_group"));
    }
    if (payload.trigger_type === "schedule" && !payload.schedule_expression) {
      throw new Error(t("validation.cron_required"));
    }
    if (payload.trigger_type === "event") {
      if (!payload.event_type) {
        payload.event_type = "script";
      }
      if (payload.event_type === "script" && !payload.condition_script) {
        throw new Error(t("validation.script_required"));
      }
    }
    if (state.editingTaskId) {
      await api("update-task", { id: state.editingTaskId, ...payload });
      showToast(t("msg.task_updated"));
    } else {
      await api("create-task", payload);
      showToast(t("msg.task_created"));
    }
    closeModal(elements.taskModal);
    state.selectedIds.clear();
    await loadTasks();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadTasks({ silent = false } = {}) {
  if (loadTasksPromise) {
    return loadTasksPromise;
  }
  loadTasksPromise = (async () => {
    try {
      const { data } = await api("list-tasks");
      state.tasks = data || [];
      sortTasks();
      state.selectedIds.forEach((id) => {
        if (!state.tasks.some((task) => task.id === id)) {
          state.selectedIds.delete(id);
        }
      });
      renderTasks();
    } catch (error) {
      if (!silent) {
        showToast(t("error.load_tasks", { err: error.message }), true);
      } else {
        console.error("自动刷新任务失败", error);
      }
    } finally {
      loadTasksPromise = null;
    }
  })();
  return loadTasksPromise;
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
    showToast(t("prompt.select_task"));
    return;
  }
  if (
    !(await showConfirm(
      t("confirm.delete_selected_tasks", { n: selected.length }),
    ))
  ) {
    return;
  }
  try {
    const response = await api("batch-tasks", { batch_action: "delete", task_ids: selected });
    const result = response.result || {};
    const { deleted = [], missing = [] } = result;
    const deletedCount = deleted.length;
    const missingCount = missing.length;
    state.selectedIds.clear();
    await loadTasks();
    let parts = [];
    if (deletedCount) parts.push(t("msg.deleted_n", { n: deletedCount }));
    if (missingCount) parts.push(t("msg.missing_n", { n: missingCount }));
    showToast(parts.join(t("list.sep")) || t("msg.no_tasks_deleted"));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function runSelectedTasks() {
  const selected = Array.from(state.selectedIds);
  if (!selected.length) {
    showToast(t("prompt.select_task_to_run"));
    return;
  }
  try {
    const response = await api("batch-tasks", { batch_action: "run", task_ids: selected });
    const result = response.result || {};
    const {
      queued = [],
      running = [],
      pretask_failed = [],
      condition_failed = [],
      missing = [],
    } = result;
    const queuedCount = queued.length;
    const runningCount = running.length;
    const pretaskFailedCount = pretask_failed.length;
    const conditionFailedCount = condition_failed.length;
    const missingCount = missing.length;
    const parts = [];
    if (queuedCount) parts.push(t("msg.triggered_n", { n: queuedCount }));
    if (runningCount) parts.push(t("msg.running_n", { n: runningCount }));
    if (pretaskFailedCount)
      parts.push(t("msg.pretask_failed_n", { n: pretaskFailedCount }));
    if (conditionFailedCount)
      parts.push(t("msg.condition_failed_n", { n: conditionFailedCount }));
    if (missingCount) parts.push(t("msg.missing_n", { n: missingCount }));
    showToast(parts.join(t("list.sep")) || t("msg.no_tasks_triggered"));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function stopSelectedTasks() {
  const selected = Array.from(state.selectedIds);
  if (!selected.length) {
    showToast(t("prompt.select_task_to_stop"));
    return;
  }
  try {
    const response = await api("batch-tasks", { batch_action: "stop", task_ids: selected });
    const result = response.result || {};
    const { stopped = [], not_running = [], missing = [] } = result;
    const stoppedCount = stopped.length;
    const notRunningCount = not_running.length;
    const missingCount = missing.length;
    const parts = [];
    if (stoppedCount) parts.push(t("msg.stopped_n", { n: stoppedCount }));
    if (notRunningCount)
      parts.push(t("msg.not_running_n", { n: notRunningCount }));
    if (missingCount) parts.push(t("msg.missing_n", { n: missingCount }));
    showToast(parts.join(t("list.sep")) || t("msg.no_tasks_stopped"));
    await loadTasks({ silent: true });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function toggleSelectedTask() {
  const selected = Array.from(state.selectedIds);
  if (!selected.length) {
    showToast(t("prompt.select_task"));
    return;
  }
  try {
    const selectedTasks = state.tasks.filter((task) =>
      selected.includes(task.id),
    );
    if (!selectedTasks.length) {
      throw new Error(t("error.task_not_found"));
    }
    const shouldEnable = selectedTasks.some((task) => !task.is_active);
    const action = shouldEnable ? "enable" : "disable";
    const response = await api("batch-tasks", { batch_action: action, task_ids: selected });
    const result = response.result || {};
    const { updated = [], unchanged = [], missing = [] } = result;
    const updatedCount = updated.length;
    const unchangedCount = unchanged.length;
    const missingCount = missing.length;
    await loadTasks();
    const verb = shouldEnable ? t("verb.enable") : t("verb.disable");
    const parts = [];
    if (updatedCount)
      parts.push(t("msg.action_completed", { verb, n: updatedCount }));
    if (unchangedCount)
      parts.push(t("msg.unchanged_count", { n: unchangedCount }));
    if (missingCount) parts.push(t("msg.missing_n", { n: missingCount }));
    showToast(
      parts.join(t("list.sep")) || t("msg.no_tasks_completed", { verb }),
    );
  } catch (error) {
    showToast(error.message, true);
  }
}

async function openResultModal() {
  const selected = Array.from(state.selectedIds);
  if (selected.length !== 1) {
    showToast(t("prompt.select_single_task"));
    return;
  }
  const taskId = selected[0];
  const task = state.tasks.find((item) => item.id === taskId);
  if (!task) {
    showToast(t("error.task_not_found"), true);
    return;
  }
  state.currentResultTaskId = taskId;
  state.resultLogCache.clear();
  elements.resultSubtitle.textContent = `${task.name} (#${task.id})`;
  openModal(elements.resultModal);
  await refreshResults();
}

async function openSettingsModal() {
  if (!elements.settingsModal || !elements.settingsForm) {
    return;
  }
  openModal(elements.settingsModal);
  try {
    const payload = await api("get-settings");
    const settings = payload?.data || {};
    Object.entries(settings).forEach(([key, value]) => {
      const field = elements.settingsForm.elements.namedItem(key);
      if (field instanceof HTMLInputElement) {
        field.value = String(value ?? "");
      }
    });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  if (!elements.settingsForm) {
    return;
  }
  const formData = new FormData(elements.settingsForm);
  const payload = {
    result_retention_per_task: Number(
      formData.get("result_retention_per_task"),
    ),
    task_timeout: Number(formData.get("task_timeout")),
    condition_timeout: Number(formData.get("condition_timeout")),
    result_log_preview_limit: Number(formData.get("result_log_preview_limit")),
  };
  try {
    const response = await api("update-settings", payload);
    const pruned = Number(response?.pruned || 0);
    closeModal(elements.settingsModal);
    if (pruned > 0) {
      showToast(t("msg.settings_saved_pruned", { n: pruned }));
    } else {
      showToast(t("msg.settings_saved"));
    }
  } catch (error) {
    showToast(error.message, true);
  }
}

async function refreshResults() {
  if (!state.currentResultTaskId) {
    return;
  }
  try {
    const { data } = await api("list-results", { id: state.currentResultTaskId, limit: 50, offset: 0, summary: 1 });
    renderResults(data || []);
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderResults(results) {
  elements.resultList.innerHTML = "";
  if (!results.length) {
    elements.resultList.innerHTML = `<p class="empty">${t("results.no_records")}</p>`;
    return;
  }
  const fragment = document.createDocumentFragment();
  results.forEach((result) => {
    const status = statusMap[result.status] || {
      label: result.status,
      className: "status-unknown",
    };
    const card = document.createElement("article");
    card.className = "result-card";
    const statusText = t(status.label);
    let reasonKey = `trigger.${result.trigger_reason}`;
    let reasonText = t(reasonKey);
    if (reasonText === reasonKey) {
      reasonText = result.trigger_reason || "";
    }
    const header = document.createElement("header");
    const metaGroup = document.createElement("div");
    const statusEl = document.createElement("div");
    statusEl.className = `status-pill ${status.className}`;
    statusEl.textContent = statusText;
    const reasonEl = document.createElement("span");
    reasonEl.className = "muted";
    reasonEl.textContent = `${t("label.trigger")}${reasonText}`;
    metaGroup.appendChild(statusEl);
    metaGroup.appendChild(reasonEl);

    const actionsGroup = document.createElement("div");
    actionsGroup.className = "result-card-actions";
    const timeEl = document.createElement("div");
    timeEl.className = "muted";
    timeEl.textContent = `${formatDate(result.started_at)} - ${formatDate(result.finished_at)}`;
    const deleteBtn = document.createElement("button");
    deleteBtn.className = "ghost";
    deleteBtn.type = "button";
    deleteBtn.textContent = t("btn.delete");
    deleteBtn.addEventListener("click", async () => {
      try {
        await api("delete-results", { id: state.currentResultTaskId, result_id: result.id });
        state.resultLogCache.delete(result.id);
        await refreshResults();
      } catch (error) {
        showToast(error.message, true);
      }
    });
    actionsGroup.appendChild(timeEl);
    actionsGroup.appendChild(deleteBtn);
    header.appendChild(metaGroup);
    header.appendChild(actionsGroup);
    card.appendChild(header);

    const previewText =
      typeof result.log_preview === "string"
        ? result.log_preview
        : result.log || "";
    const cachedFullLog = state.resultLogCache.get(result.id);
    const isExpanded = typeof cachedFullLog === "string";
    const logText = isExpanded ? cachedFullLog : previewText;
    const hasLogText = typeof logText === "string" && logText.trim().length > 0;

    if (hasLogText && (result.log_truncated || isExpanded)) {
      const logMeta = document.createElement("div");
      logMeta.className = "result-log-meta";

      const hint = document.createElement("span");
      hint.className = "muted";
      if (result.log_truncated) {
        const previewLimit =
          typeof result.log_preview === "string"
            ? result.log_preview.length
            : 0;
        hint.textContent = t("results.log_truncated", {
          n: result.log_size || 0,
          limit: previewLimit,
        });
      } else {
        hint.textContent = t("results.log_full");
      }
      logMeta.appendChild(hint);

      const toggleBtn = document.createElement("button");
      toggleBtn.className = "ghost small";
      toggleBtn.type = "button";
      toggleBtn.textContent = isExpanded
        ? t("results.collapse_log")
        : t("results.expand_log");
      toggleBtn.addEventListener("click", async () => {
        if (state.resultLogCache.has(result.id)) {
          state.resultLogCache.delete(result.id);
          renderResults(results);
          return;
        }
        toggleBtn.disabled = true;
        toggleBtn.textContent = t("results.loading_log");
        try {
          const payload = await api("get-result", {
            id: state.currentResultTaskId,
            result_id: result.id,
          });
          const fullLog = payload?.data?.log || "";
          state.resultLogCache.set(result.id, fullLog);
          renderResults(results);
        } catch (error) {
          showToast(error.message, true);
          toggleBtn.disabled = false;
          toggleBtn.textContent = t("results.expand_log");
        }
      });
      logMeta.appendChild(toggleBtn);
      card.appendChild(logMeta);
    }

    if (hasLogText) {
      const logEl = document.createElement("pre");
      logEl.className = "result-log";
      logEl.textContent = logText;
      card.appendChild(logEl);
    }

    fragment.appendChild(card);
  });
  elements.resultList.appendChild(fragment);
}

async function clearResultHistory() {
  if (!state.currentResultTaskId) {
    return;
  }
  if (!(await showConfirm(t("confirm.clear_results")))) {
    return;
  }
  try {
    await api("clear-results", { id: state.currentResultTaskId });
    state.resultLogCache.clear();
    await refreshResults();
    showToast(t("msg.results_cleared"));
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

function bindTaskTableEventListeners() {
  if (elements.tableHead) {
    elements.tableHead.addEventListener("click", (event) => {
      const header = event.target.closest("th[data-sort-key]");
      if (!header) {
        return;
      }
      toggleTaskSort(header.dataset.sortKey || "");
    });
    elements.tableHead.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      const header = event.target.closest("th[data-sort-key]");
      if (!header) {
        return;
      }
      event.preventDefault();
      toggleTaskSort(header.dataset.sortKey || "");
    });
  }

  elements.tableBody.addEventListener("click", (event) => {
    const row = event.target.closest("tr");
    if (!row) {
      return;
    }
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
}

function bindTaskActionEventListeners() {
  buttons.create.addEventListener("click", () => openTaskModal());
  buttons.edit.addEventListener("click", () => {
    const selected = getSelectedTasks();
    if (selected.length !== 1) {
      showToast(t("prompt.select_single_task"));
      return;
    }
    openTaskModal(selected[0]);
  });
  buttons.delete.addEventListener("click", deleteSelectedTasks);
  buttons.run.addEventListener("click", runSelectedTasks);
  buttons.stop.addEventListener("click", stopSelectedTasks);
  buttons.toggle.addEventListener("click", toggleSelectedTask);
  buttons.results.addEventListener("click", openResultModal);
  buttons.settings?.addEventListener("click", openSettingsModal);
  buttons.clearResults.addEventListener("click", clearResultHistory);

  elements.clearPreTasksBtn.addEventListener("click", () => {
    Array.from(elements.preTaskSelect.options).forEach((option) => {
      option.selected = false;
    });
    renderPreTaskChecklist();
  });
  if (elements.preTaskChecklist) {
    elements.preTaskChecklist.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || target.type !== "checkbox") {
        return;
      }
      const id = target.getAttribute("data-pretask-id");
      if (!id) {
        return;
      }
      const option = Array.from(elements.preTaskSelect.options).find(
        (opt) => String(opt.value) === id,
      );
      if (option) {
        option.selected = target.checked;
      }
    });
  }
  if (elements.accountReloadBtn) {
    elements.accountReloadBtn.addEventListener("click", () =>
      loadAccounts({ showError: true }),
    );
  }
}

function bindFormAndModalEventListeners() {
  elements.taskForm.addEventListener("submit", handleFormSubmit);
  elements.settingsForm?.addEventListener("submit", saveSettings);
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
}

function bindCronGeneratorEventListeners() {
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
}

function attachEventListeners() {
  window.addEventListener("resize", handleViewportChange);
  bindTaskTableEventListeners();
  bindTaskActionEventListeners();
  bindFormAndModalEventListeners();
  bindCronGeneratorEventListeners();

  bindTaskTemplateSelection();
  bindTemplateManagementEventListeners();
  buttons.about?.addEventListener("click", () => {
    openModal(document.getElementById("aboutModal"));
  });
}
(async function init() {
  try {
    platformConfig = await sdk.getPlatformConfig();
  } catch (e) {
    // fall back to defaults
  }
  applyPreferences();
  if (sdk.isWeb === true && sdk.isStandaloneWeb === false) {
    sdk.$on("os/theme", (theme) => {
      platformConfig = { ...platformConfig, theme };
      applyPreferences();
    });
    sdk.$on("os/language", (language) => {
      platformConfig = { ...platformConfig, language };
      applyPreferences({ rerender: true });
    });
  }

  document.querySelectorAll(".modal").forEach((modal) => {
    if (modal.classList.contains("hidden")) {
      modal.inert = true;
      modal.setAttribute("aria-hidden", "true");
    }
  });
  await loadTemplates();
  attachEventListeners();
  updateSortHeaders();
  toggleSections();
  updateEventTypeOptionLabels();
  updateTemplateActionState();
  await loadAccounts({ showError: false });
  await loadTasks();
  startAutoRefresh();
  window.addEventListener("scheduler:i18nchange", () => {
    renderTemplateOptions();
    renderTemplatesTable();
    renderTasks();
    updateSortHeaders();
    updateEventTypeOptionLabels();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      loadTasks({ silent: true });
    }
  });
})();
