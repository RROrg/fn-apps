import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

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

const I18N = {
  "zh-CN": {
    appTitle: "执行器",
    execute: "执行",
    stop: "终止",
    argsLabel: "参数:",
    argsPlaceholder: "输入命令行参数（可选）",
    filePreview: "文件预览",
    waitingToExecute: "等待执行...",
    ready: "就绪",
    running: "执行中...",
    done: "完成",
    error: "错误",
    timeout: "超时",
    killed: "已终止",
    exitCode: "退出码",
    elapsedTime: "耗时: {time}s",
    noFilePath: "错误: 未提供文件路径",
    noFilePathStatus: "无文件路径",
    startFailed: "启动执行失败: {msg}",
    failed: "失败",
    userKilled: "[用户终止执行]",
    statusDone: "[完成] 退出码: {code}",
    statusError: "[错误] 退出码: {code}",
    statusTimeout: "[超时] 退出码: {code}",
    statusKilled: "[已终止] 退出码: {code}",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
  },
  "en-US": {
    appTitle: "Execute",
    execute: "Execute",
    stop: "Stop",
    argsLabel: "Args:",
    argsPlaceholder: "Enter command line arguments (optional)",
    filePreview: "File Preview",
    waitingToExecute: "Waiting to execute...",
    ready: "Ready",
    running: "Running...",
    done: "Done",
    error: "Error",
    timeout: "Timeout",
    killed: "Killed",
    exitCode: "Exit code",
    elapsedTime: "Time: {time}s",
    noFilePath: "Error: No file path provided",
    noFilePathStatus: "No file path",
    startFailed: "Failed to start: {msg}",
    failed: "Failed",
    userKilled: "[Killed by user]",
    statusDone: "[Done] Exit code: {code}",
    statusError: "[Error] Exit code: {code}",
    statusTimeout: "[Timeout] Exit code: {code}",
    statusKilled: "[Killed] Exit code: {code}",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
  },
};

function t(key, params) {
  const messages = I18N[currentLang] || I18N["zh-CN"];
  let text = messages[key] || I18N["zh-CN"][key] || key;
  if (params) {
    Object.keys(params).forEach((k) => {
      text = text.replace(new RegExp("\\{" + k + "\\}", "g"), params[k]);
    });
  }
  return text;
}

let currentLang = platformConfig.language;
let currentTheme = platformConfig.theme;

const sdkWebHost = () => sdk.isWeb === true && sdk.isStandaloneWeb === false;

async function initPreferences() {
  try {
    const config = await sdk.getPlatformConfig();
    if (config) {
      if (config.language) platformConfig.language = config.language;
      if (config.theme) platformConfig.theme = config.theme;
    }
  } catch (e) {}
  applyLanguage();
  applyTheme();
  applyI18n();
  if (sdkWebHost()) {
    await Promise.all([
      sdk.$on("os/theme", (theme) => {
        platformConfig.theme = theme;
        applyTheme();
      }),
      sdk.$on("os/language", (language) => {
        platformConfig.language = language;
        applyLanguage();
        applyI18n();
      }),
    ]);
  }
  if (typeof sdk.setTitle === "function") {
    sdk.setTitle(t("appTitle")).catch(() => {});
  }
}

function applyLanguage() {
  const language = String(platformConfig.language || "").replace("_", "-");
  const resolved = language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
  currentLang = resolved;
  platformConfig.language = resolved;
  document.documentElement.lang = resolved === "zh-CN" ? "zh-CN" : "en";
  return resolved;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-dynamic]").forEach((el) => {
    el.textContent = t(el.dataset.i18nDynamic);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.title = t("appTitle");
}

function applyTheme() {
  // fnOS 宿主可能返回 { theme: "dark" } 对象，先解包再规范化
  const value = platformConfig.theme;
  const v =
    value && typeof value === "object" && "theme" in value
      ? value.theme
      : value;
  const resolved = String(v || "").toLowerCase() === "dark" ? "dark" : "light";
  currentTheme = resolved;
  document.documentElement.dataset.theme = resolved;
  return resolved;
}

const outputArea = document.getElementById("outputArea");
const argsInput = document.getElementById("argsInput");
const btnExecute = document.getElementById("btnExecute");
const btnStop = document.getElementById("btnStop");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const headerPath = document.getElementById("headerPath");
const exitCodeDisplay = document.getElementById("exitCodeDisplay");
const exitCodeValue = document.getElementById("exitCodeValue");
const timeDisplay = document.getElementById("timeDisplay");
const previewSection = document.getElementById("previewSection");
const previewContent = document.getElementById("previewContent");
const previewArrow = document.getElementById("previewArrow");

const params = new URLSearchParams(window.location.search);
const openedPath = params.get("path");
let currentTaskId = null;
let pollTimer = null;

function clearOutput() {
  outputArea.innerHTML = "";
}

function addLine(text, cls) {
  const div = document.createElement("div");
  div.className = "line " + (cls || "stdout");
  div.textContent = text;
  outputArea.appendChild(div);
  outputArea.scrollTop = outputArea.scrollHeight;
}

function setStatus(status, textKey, textParams) {
  statusDot.className = "status-dot " + status;
  statusText.textContent = textParams ? t(textKey, textParams) : t(textKey);
}

function setExitCode(code) {
  exitCodeDisplay.classList.remove("is-hidden");
  exitCodeValue.textContent = code;
  exitCodeValue.className = "exit-code " + (code === 0 ? "success" : "fail");
}

function setRunning(running) {
  btnExecute.disabled = running;
  btnStop.disabled = !running;
  argsInput.disabled = running;
}

function togglePreview() {
  const content = previewContent;
  const arrow = previewArrow;
  if (content.classList.contains("is-hidden")) {
    content.classList.remove("is-hidden");
    arrow.classList.add("open");
  } else {
    content.classList.add("is-hidden");
    arrow.classList.remove("open");
  }
}

function loadFileInfo() {
  if (!openedPath) return;
  headerPath.textContent = openedPath;
  api("read_file", { path: openedPath })
    .then((data) => {
      if (data.preview) {
        previewSection.classList.remove("is-hidden");
        previewContent.textContent = data.preview;
      }
    })
    .catch(() => {});
}

function doExecute() {
  if (!openedPath) {
    addLine(t("noFilePath"), "error");
    return;
  }

  clearOutput();
  lastStdoutLen = 0;
  lastStderrLen = 0;
  addLine(
    "$ " + openedPath + (argsInput.value ? " " + argsInput.value : ""),
    "info",
  );
  addLine("", "");

  setStatus("running", "running");
  setRunning(true);
  exitCodeDisplay.classList.add("is-hidden");
  timeDisplay.classList.add("is-hidden");

  const startTime = Date.now();
  const timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    timeDisplay.classList.remove("is-hidden");
    timeDisplay.textContent = t("elapsedTime", { time: elapsed });
  }, 1000);

  api("execute", {
    path: openedPath,
    args: argsInput.value,
  })
    .then((data) => {
      currentTaskId = data.task_id;
      pollTimer = setInterval(
        () => pollTask(currentTaskId, timerInterval),
        500,
      );
    })
    .catch((err) => {
      addLine(t("startFailed", { msg: err.message }), "error");
      setStatus("error", "failed");
      setRunning(false);
      clearInterval(timerInterval);
    });
}

let lastStdoutLen = 0;
let lastStderrLen = 0;

function pollTask(taskId, timerInterval) {
  api("read_task", { task_id: taskId })
    .then((data) => {
      if (data.stdout && data.stdout.length > lastStdoutLen) {
        const newOut = data.stdout.substring(lastStdoutLen);
        lastStdoutLen = data.stdout.length;
        const lines = newOut.split("\n");
        if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
        lines.forEach((line) => addLine(line, "stdout"));
      }
      if (data.stderr && data.stderr.length > lastStderrLen) {
        const newErr = data.stderr.substring(lastStderrLen);
        lastStderrLen = data.stderr.length;
        const lines = newErr.split("\n");
        if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
        lines.forEach((line) => addLine(line, "stderr"));
      }

      if (
        data.status === "done" ||
        data.status === "error" ||
        data.status === "timeout" ||
        data.status === "killed"
      ) {
        clearInterval(pollTimer);
        clearInterval(timerInterval);
        pollTimer = null;
        currentTaskId = null;
        setRunning(false);

        const statusKeyMap = {
          done: "done",
          error: "error",
          timeout: "timeout",
          killed: "killed",
        };

        setStatus(data.status, statusKeyMap[data.status] || data.status);
        setExitCode(data.exit_code);

        addLine("", "");

        const summaryKeyMap = {
          done: "statusDone",
          error: "statusError",
          timeout: "statusTimeout",
          killed: "statusKilled",
        };
        const summaryKey = summaryKeyMap[data.status] || "statusError";
        addLine(
          t(summaryKey, { code: data.exit_code }),
          data.exit_code === 0 ? "info" : "error",
        );
      }
    })
    .catch(() => {});
}

function doStop() {
  if (!currentTaskId) return;
  api("stop_task", { task_id: currentTaskId })
    .then(() => {
      addLine("", "");
      addLine(t("userKilled"), "error");
    })
    .catch(() => {});
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

initPreferences();

if (!openedPath) {
  addLine(t("noFilePath"), "error");
  setStatus("error", "noFilePathStatus");
} else {
  loadFileInfo();
  argsInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doExecute();
  });
}

// expose for inline onclick handlers
window.togglePreview = togglePreview;
window.doExecute = doExecute;
window.doStop = doStop;
window.openAbout = openAbout;
window.closeAbout = closeAbout;
