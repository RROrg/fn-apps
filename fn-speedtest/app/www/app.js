import { TrimApp } from "./web-app.js";

const sdk = new TrimApp();
let platformConfig = { language: "zh-CN", theme: "light" };

const API_ENDPOINT = "./api";

const state = { language: "zh-CN", theme: "light" };

const I18N = {
  "zh-CN": {
    appTitle: "网络测速",
    about: "关于",
    start: "开始测速",
    retest: "重新测速",
    running: "测速中",
    ready: "准备就绪",
    done: "完成",
    error: "错误",
    failed: "失败",
    na: "N/A",
    latency: "延迟",
    jitter: "抖动",
    download: "下载",
    upload: "上传",
    downloading: "下载中",
    uploading: "上传中",
    pingMeasure: "测量延迟",
    wanTest: "外网测速",
    wanLatency: "外网延迟",
    wanDownload: "外网下载",
    wanUpload: "外网上传",
    scopeNote: "此设备 ↔ 服务器 ↔ 互联网",
    client: "客户端",
    server: "服务端",
    public: "互联网",
    pingLabel: "延迟 / PING",
    jitterLabel: "抖动 / JITTER",
    downloadLabel: "下载 / DOWNLOAD",
    uploadLabel: "上传 / UPLOAD",
    lanBadge: "本地",
    lanTitle: "客户端 ↔ 服务器",
    wanBadge: "外网",
    wanTitle: "服务器 ↔ 互联网",
    records: "测速记录",
    clear: "清空",
    emptyRecords: "暂无记录，点击表盘开始测速。",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    close: "关闭",
    recClient: "客户端",
    recLanPing: "本地延迟",
    recLanDown: "本地下载",
    recLanUp: "本地上传",
    recWanPing: "外网延迟",
    recWanDown: "外网下载",
    recWanUp: "外网上传",
    untransparent: "未透传",
    clientTitle: "浏览器局域网地址",
    clientTitleHint: "fnOS 网关未透传客户端地址",
  },
  "en-US": {
    appTitle: "Network Speed Test",
    about: "About",
    start: "Start Test",
    retest: "Test Again",
    running: "Testing",
    ready: "Ready",
    done: "Done",
    error: "Error",
    failed: "Failed",
    na: "N/A",
    latency: "Latency",
    jitter: "Jitter",
    download: "Download",
    upload: "Upload",
    downloading: "Downloading",
    uploading: "Uploading",
    pingMeasure: "Measuring Latency",
    wanTest: "WAN Test",
    wanLatency: "WAN Latency",
    wanDownload: "WAN Download",
    wanUpload: "WAN Upload",
    scopeNote: "This device ↔ Server ↔ Internet",
    client: "Client",
    server: "Server",
    public: "Internet",
    pingLabel: "LATENCY / PING",
    jitterLabel: "JITTER / JITTER",
    downloadLabel: "DOWNLOAD / DOWNLOAD",
    uploadLabel: "UPLOAD / UPLOAD",
    lanBadge: "LAN",
    lanTitle: "Client ↔ Server",
    wanBadge: "WAN",
    wanTitle: "Server ↔ Internet",
    records: "Test History",
    clear: "Clear",
    emptyRecords: "No records yet. Tap the gauge to start.",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    close: "Close",
    recClient: "Client",
    recLanPing: "LAN Ping",
    recLanDown: "LAN Down",
    recLanUp: "LAN Up",
    recWanPing: "WAN Ping",
    recWanDown: "WAN Down",
    recWanUp: "WAN Up",
    untransparent: "Not forwarded",
    clientTitle: "Browser LAN address",
    clientTitleHint: "fnOS gateway did not forward client address",
  },
};

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
  document.title = t("appTitle");
  if (sdk.setTitle) {
    sdk.setTitle(t("appTitle")).catch(() => {});
  }
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
  if (rerender && languageChanged) {
    renderRecords();
  }
  return languageChanged;
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3200);
}

function openAbout() {
  els.aboutModal.classList.remove("hidden");
}

function closeModals() {
  document.querySelectorAll(".modal").forEach((m) => m.classList.add("hidden"));
}

const GAUGE_CIRC = 2 * Math.PI * 140; // r = 140
const LAN_DURATION = 12;

// 量程档位（Mbps）。优先用网卡链路速率，向上取整到最近的档位。
const SCALE_STEPS = [1000, 2500, 5000, 10000, 25000, 40000, 100000];
function scaleFor(value) {
  if (!value || value <= 0) return SCALE_STEPS[0];
  for (let i = 0; i < SCALE_STEPS.length; i++) {
    if (value <= SCALE_STEPS[i]) return SCALE_STEPS[i];
  }
  return SCALE_STEPS[SCALE_STEPS.length - 1];
}
let GAUGE_SCALE = SCALE_STEPS[0];

function setGauge(value, unit, stage) {
  const v = Math.max(0, Number(value) || 0);
  const ratio = Math.min(1, v / GAUGE_SCALE);
  els.gaugeProgress.style.strokeDashoffset = String(GAUGE_CIRC * (1 - ratio));
  els.gaugeValue.textContent = v >= 100 ? Math.round(v) : v.toFixed(1);
  if (unit) els.gaugeUnit.textContent = unit;
  if (stage) els.gaugeStage.textContent = stage;
}

const els = {
  go: document.getElementById("goBtn"),
  goLabel: document.querySelector("#goBtn .go-label"),
  gaugeValue: document.getElementById("gaugeValue"),
  gaugeUnit: document.getElementById("gaugeUnit"),
  gaugeStage: document.getElementById("gaugeStage"),
  gaugeProgress: document.getElementById("gaugeProgress"),
  mPing: document.getElementById("mPing"),
  mJitter: document.getElementById("mJitter"),
  mDown: document.getElementById("mDown"),
  mUp: document.getElementById("mUp"),
  lanHost: document.getElementById("lanHost"),
  lanPing: document.getElementById("lanPing"),
  lanJitter: document.getElementById("lanJitter"),
  lanDown: document.getElementById("lanDown"),
  lanUp: document.getElementById("lanUp"),
  lanBar: document.getElementById("lanBar"),
  wanHost: document.getElementById("wanHost"),
  wanPing: document.getElementById("wanPing"),
  wanJitter: document.getElementById("wanJitter"),
  wanDown: document.getElementById("wanDown"),
  wanUp: document.getElementById("wanUp"),
  wanBar: document.getElementById("wanBar"),
  recList: document.getElementById("recList"),
  clearRec: document.getElementById("clearRec"),
  ipClient: document.getElementById("ipClient"),
  ipServer: document.getElementById("ipServer"),
  ipPublic: document.getElementById("ipPublic"),
  aboutBtn: document.getElementById("aboutBtn"),
  aboutModal: document.getElementById("aboutModal"),
};

let running = false;

// ---- records ----------------------------------------------------------
const REC_KEY = "fn_speedtest_records";
const REC_MAX = 30;

function loadRecords() {
  try {
    const raw = localStorage.getItem(REC_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}
function saveRecords(list) {
  try {
    localStorage.setItem(REC_KEY, JSON.stringify(list));
  } catch (e) {}
}
function addRecord(rec) {
  const list = loadRecords();
  list.unshift(rec);
  if (list.length > REC_MAX) list = list.slice(0, REC_MAX);
  saveRecords(list);
  renderRecords();
}
function fmtRec(v, unit) {
  if (v == null) return t("na");
  if (unit === "ms") return v.toFixed(1) + " ms";
  return (v >= 100 ? Math.round(v) : v.toFixed(1)) + " Mbps";
}
function recRowHTML(r) {
  return (
    '<div class="rec-row">' +
    '<div class="rec-time">' +
    r.time +
    "</div>" +
    '<div class="rec-cell"><span>' +
    t("recClient") +
    "</span><b>" +
    (r.clientIp || "—") +
    "</b></div>" +
    '<div class="rec-cell"><span>' +
    t("recLanPing") +
    "</span><b>" +
    fmtRec(r.lanPing, "ms") +
    "</b></div>" +
    '<div class="rec-cell"><span>' +
    t("recLanDown") +
    "</span><b>" +
    fmtRec(r.lanDown, "mb") +
    "</b></div>" +
    '<div class="rec-cell"><span>' +
    t("recLanUp") +
    "</span><b>" +
    fmtRec(r.lanUp, "mb") +
    "</b></div>" +
    '<div class="rec-cell"><span>' +
    t("recWanPing") +
    "</span><b>" +
    fmtRec(r.wanPing, "ms") +
    "</b></div>" +
    '<div class="rec-cell"><span>' +
    t("recWanDown") +
    "</span><b>" +
    fmtRec(r.wanDown, "mb") +
    "</b></div>" +
    '<div class="rec-cell"><span>' +
    t("recWanUp") +
    "</span><b>" +
    fmtRec(r.wanUp, "mb") +
    "</b></div>" +
    "</div>"
  );
}
function renderRecords(live) {
  const list = loadRecords();
  let html = "";
  // live 为「进行中」的记录：显示在历史记录顶部，测速过程实时刷新。
  if (live) html += recRowHTML(live);
  html += list.map(recRowHTML).join("");
  if (!html) {
    els.recList.innerHTML =
      '<div class="records-empty">' + t("emptyRecords") + "</div>";
    return;
  }
  els.recList.innerHTML = html;
}

function setGaugeColor(color) {
  els.gaugeProgress.style.stroke = color;
  els.gaugeProgress.style.filter = "drop-shadow(0 0 10px " + color + "99)";
}

function fmtMs(v) {
  return v == null ? "—" : v.toFixed(1) + " ms";
}
function fmtMbps(v) {
  if (v == null) return "—";
  return (v >= 100 ? Math.round(v) : v.toFixed(1)) + " Mbps";
}
function fmtBar(v) {
  if (v == null) return "0%";
  return Math.min(100, (v / GAUGE_SCALE) * 100) + "%";
}
function jitterOf(samples) {
  if (samples.length < 2) return 0;
  let d = 0;
  for (let i = 1; i < samples.length; i++)
    d += Math.abs(samples[i] - samples[i - 1]);
  return d / (samples.length - 1);
}

// ---- LAN: ping --------------------------------------------------------
function lanPing() {
  const N = 20,
    samples = [];
  setGaugeColor("#00b3ff");
  setGauge(0, "Mbps", t("pingMeasure"));
  return (async () => {
    for (let i = 0; i < N; i++) {
      const t0 = performance.now();
      try {
        // 后端 /echo 是顶层路由（无 /api 前缀），不要拼到 ./api 下。
        await fetch("./echo", { cache: "no-store" });
        const r = performance.now() - t0;
        if (r < 5000) samples.push(r);
      } catch (e) {
        /* ignore */
      }
    }
    const avg = samples.reduce((a, b) => a + b, 0) / (samples.length || 1);
    const jit = jitterOf(samples);
    els.mPing.innerHTML = samples.length
      ? avg.toFixed(1) + " <small>ms</small>"
      : "— <small>ms</small>";
    els.mJitter.innerHTML = samples.length
      ? jit.toFixed(1) + " <small>ms</small>"
      : "— <small>ms</small>";
    els.lanPing.textContent = fmtMs(samples.length ? avg : null);
    els.lanJitter.textContent = fmtMs(samples.length ? jit : null);
    return {
      avg: samples.length ? avg : null,
      jitter: samples.length ? jit : null,
    };
  })();
}

// ---- LAN: download (多路并发聚合) ----------------
// 关键发现：fnOS 网关(nginx→trim_http_cgi)对「单条下行连接」限速约 763 Mbps
// （上传单连接却能到 2.3G，说明是代理下行每连接转发慢，而非总带宽不足）。
// 因此单流永远打不满 2.5G 网卡，必须用多路并发把带宽聚合起来。后端 /api/dl
// 用 os.sendfile（释放 GIL），N 路并发各跑满各自的 ~763 Mbps，合计即可跑满
// 2.5G（N×763 > 2500 → 取网卡上限）。
// 每流 30MB：避免响应缓冲占用过高。维持 N 路并发：启动 N 条流，任一条 onload
// 立即补一条，使窗口内始终 N 路在跑。全程累加进 totLoaded；grace 后记录基准
// (tBase, baseLoaded)，最终均值 = (totLoaded - baseLoaded) * 8 / (tEnd - tBase)。
let DL_STREAMS = 8;
let DL_BLOB_MB = 30;
const DL_GRACE = 1.5;
const DL_STAGGER = 120;

function lanDownload() {
  setGaugeColor("#00b3ff");
  setGauge(0, "Mbps", t("downloading"));
  return new Promise((resolve) => {
    let totLoaded = 0; // 全程累加（不随 grace 清零）
    let measuring = false;
    let done = false;
    let stopped = false;
    const streams = [];
    let lastPush = 0;
    let tBase = 0,
      baseLoaded = 0;

    function finish() {
      if (done) return;
      done = true;
      streams.forEach((x) => {
        try {
          x.abort();
        } catch (e) {}
      });
      const tEnd = performance.now();
      const secs = Math.max((tEnd - tBase) / 1000, 0.001);
      const bytes = Math.max(totLoaded - baseLoaded, 0);
      const mbps = (bytes * 8) / (secs * 1e6);
      setGauge(mbps, "Mbps", t("download"));
      els.mDown.innerHTML =
        (mbps >= 100 ? Math.round(mbps) : mbps.toFixed(1)) +
        " <small>Mbps</small>";
      els.lanDown.textContent = fmtMbps(mbps);
      els.lanBar.style.width = fmtBar(mbps);
      resolve(mbps);
    }

    function startStream(i) {
      if (stopped) return;
      const xhr = new XMLHttpRequest();
      streams[i] = xhr;
      xhr.open(
        "GET",
        API_ENDPOINT + "/dl?mb=" + DL_BLOB_MB + "&_=" + Date.now() + "_" + i,
        true,
      );
      xhr.responseType = "arraybuffer";
      let prev = 0;
      xhr.onprogress = (e) => {
        if (stopped) return;
        const loaded = e.loaded > 0 ? e.loaded : 0;
        const diff = loaded - prev;
        prev = loaded;
        if (diff > 0) totLoaded += diff;
        const now = performance.now();
        if (measuring && now - lastPush >= 200) {
          const secs = (now - tBase) / 1000;
          const bytes = Math.max(totLoaded - baseLoaded, 0);
          const inst = (bytes * 8) / (secs * 1e6);
          setGauge(inst, "Mbps", t("download"));
          els.mDown.innerHTML =
            (inst >= 100 ? Math.round(inst) : inst.toFixed(1)) +
            " <small>Mbps</small>";
          lastPush = now;
        }
      };
      xhr.onload = () => {
        // Some browsers coalesce the last progress event.  Account for that
        // final completed response before replacing the worker, otherwise the
        // result systematically under-counts fast connections.
        const finalLoaded =
          Number(xhr.getResponseHeader("Content-Length")) || DL_BLOB_MB * 1e6;
        const missing = Math.max(0, finalLoaded - prev);
        if (missing > 0 && measuring) totLoaded += missing;
        if (!stopped) startStream(i); // 接力下一段，填满整个窗口
      };
      xhr.onerror = () => {
        if (!stopped) {
          stopped = true;
          finish();
        }
      };
      xhr.send();
    }

    for (let i = 0; i < DL_STREAMS; i++) {
      setTimeout(() => startStream(i), DL_STAGGER * i);
    }
    setTimeout(() => {
      if (stopped) return;
      measuring = true;
      tBase = performance.now();
      baseLoaded = totLoaded; // 仅记录基准，不清零
      lastPush = tBase;
    }, DL_GRACE * 1000);
    // Keep warm-up outside the sampling interval.  Previously this timer was
    // counted from request start while the denominator started after warm-up,
    // which made the advertised 8 s window shorter and inconsistent.
    setTimeout(
      () => {
        stopped = true;
        finish();
      },
      (DL_GRACE + LAN_DURATION) * 1000,
    );
  });
}

// ---- LAN: upload ------------------------------------------------------
// 多路并发上传聚合（与下载对称）。后端 /api/ul 接收 body 并丢弃，返回 JSON。
// 每路用 XHR POST，progress 事件聚合 loaded 累加进 totUploaded。
let UL_STREAMS = 3;
let UL_CHUNK_MB = 8;
const UL_GRACE = 1.5;
const UL_STAGGER = 120;

function lanUpload() {
  setGaugeColor("#00b3ff");
  setGauge(0, "Mbps", t("uploading"));
  return new Promise((resolve) => {
    let totUploaded = 0;
    let measuring = false;
    let done = false;
    let stopped = false;
    const streams = [];
    let lastPush = 0;
    let tBase = 0,
      baseUploaded = 0;

    function finish() {
      if (done) return;
      done = true;
      streams.forEach((x) => {
        try {
          x.abort();
        } catch (e) {}
      });
      const tEnd = performance.now();
      const secs = Math.max((tEnd - tBase) / 1000, 0.001);
      const bytes = Math.max(totUploaded - baseUploaded, 0);
      const mbps = (bytes * 8) / (secs * 1e6);
      setGauge(mbps, "Mbps", t("upload"));
      els.mUp.innerHTML =
        (mbps >= 100 ? Math.round(mbps) : mbps.toFixed(1)) +
        " <small>Mbps</small>";
      els.lanUp.textContent = fmtMbps(mbps);
      els.lanBar.style.width = fmtBar(mbps);
      resolve(mbps);
    }

    function startStream(i) {
      if (stopped) return;
      const xhr = new XMLHttpRequest();
      streams[i] = xhr;
      xhr.open("POST", API_ENDPOINT + "/ul?_=" + Date.now() + "_" + i, true);
      const blob = new Blob([new ArrayBuffer(UL_CHUNK_MB * 1e6)]);
      let prev = 0;
      xhr.upload.onprogress = (e) => {
        if (stopped) return;
        const loaded = e.loaded > 0 ? e.loaded : 0;
        const diff = loaded - prev;
        prev = loaded;
        if (diff > 0) totUploaded += diff;
        const now = performance.now();
        if (measuring && now - lastPush >= 200) {
          const secs = (now - tBase) / 1000;
          const bytes = Math.max(totUploaded - baseUploaded, 0);
          const inst = (bytes * 8) / (secs * 1e6);
          setGauge(inst, "Mbps", t("upload"));
          els.mUp.innerHTML =
            (inst >= 100 ? Math.round(inst) : inst.toFixed(1)) +
            " <small>Mbps</small>";
          lastPush = now;
        }
      };
      xhr.onload = () => {
        if (!stopped) startStream(i);
      };
      xhr.onerror = () => {
        if (!stopped) {
          stopped = true;
          finish();
        }
      };
      xhr.send(blob);
    }

    for (let i = 0; i < UL_STREAMS; i++) {
      setTimeout(() => startStream(i), UL_STAGGER * i);
    }
    setTimeout(() => {
      if (stopped) return;
      measuring = true;
      tBase = performance.now();
      baseUploaded = totUploaded;
      lastPush = tBase;
    }, UL_GRACE * 1000);
    setTimeout(
      () => {
        stopped = true;
        finish();
      },
      (UL_GRACE + LAN_DURATION) * 1000,
    );
  });
}

// ---- WAN: SSE 流式结果 ----------------------------------------------
// 后端 /api/internet 以 text/event-stream 推送事件（event: + data: 双行）。
// 事件类型：phase(阶段切换)、latency(延迟对象)、download/upload(吞吐数值)、
// done(最终结果)。前端逐帧解析并实时更新表盘与卡片。
function wan(onUpdate) {
  setGaugeColor("#00d9a3");
  setGauge(0, "Mbps", t("wanTest"));
  return new Promise((resolve) => {
    let es;
    let result = {};
    let lastDown = null;
    let lastUp = null;
    const finish = () => {
      try {
        es.close();
      } catch (e) {}
      resolve({
        ping: result.ping ?? null,
        jitter: result.jitter ?? null,
        down: result.down ?? null,
        up: result.up ?? null,
      });
    };
    // 原生 EventSource：浏览器原生流式解析 SSE，实时更新表盘，
    // 不受 XHR POST 流式响应的缓冲/分段读取问题影响。
    es = new EventSource(API_ENDPOINT + "/internet");
    // 后端在推完 done 后关闭连接，EventSource 会触发 onerror；close 防自动重连。
    es.onerror = () => {
      try {
        es.close();
      } catch (e) {}
    };
    es.addEventListener("phase", (e) => {
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch (_) {
        return;
      }
      if (ev.stage === "latency") setGauge(0, "ms", t("wanLatency"));
      else if (ev.stage === "download") setGauge(0, "Mbps", t("wanDownload"));
      else if (ev.stage === "upload") setGauge(0, "Mbps", t("wanUpload"));
    });
    es.addEventListener("latency", (e) => {
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch (_) {
        return;
      }
      const ping = ev.avg ?? null;
      const jitter = ev.jitter ?? null;
      els.wanPing.textContent = fmtMs(ping);
      els.wanJitter.textContent = fmtMs(jitter);
      els.mPing.innerHTML =
        ping != null
          ? ping.toFixed(1) + " <small>ms</small>"
          : "— <small>ms</small>";
      els.mJitter.innerHTML =
        jitter != null
          ? jitter.toFixed(1) + " <small>ms</small>"
          : "— <small>ms</small>";
      if (onUpdate) onUpdate({ ping, jitter });
    });
    es.addEventListener("download", (e) => {
      const mbps = Number(e.data) || 0;
      lastDown = mbps;
      setGauge(mbps, "Mbps", t("wanDownload"));
      els.wanDown.textContent = fmtMbps(mbps);
      els.wanBar.style.width = fmtBar(mbps);
      els.mDown.innerHTML =
        (mbps >= 100 ? Math.round(mbps) : mbps.toFixed(1)) +
        " <small>Mbps</small>";
      if (onUpdate) onUpdate({ down: mbps });
    });
    es.addEventListener("upload", (e) => {
      const mbps = Number(e.data) || 0;
      lastUp = mbps;
      setGauge(mbps, "Mbps", t("wanUpload"));
      els.wanUp.textContent = fmtMbps(mbps);
      els.wanBar.style.width = fmtBar(mbps);
      els.mUp.innerHTML =
        (mbps >= 100 ? Math.round(mbps) : mbps.toFixed(1)) +
        " <small>Mbps</small>";
      if (onUpdate) onUpdate({ up: mbps });
    });
    es.addEventListener("done", (e) => {
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch (_) {
        return;
      }
      const lat = ev.latency || {};
      result = {
        ping: lat.avg != null ? lat.avg : (ev.ping ?? null),
        jitter: lat.jitter != null ? lat.jitter : null,
        down: ev.download != null ? ev.download : lastDown,
        up: ev.upload != null ? ev.upload : lastUp,
      };
      finish();
    });
  });
}

// ---- 主流程 ----------------------------------------------------------
async function runAll() {
  if (running) return;
  running = true;
  els.go.disabled = true;
  // 进入 running 态：表盘中央从「开始测速」切换为实时读数（gauge-readout）。
  els.go.classList.add("running");
  els.goLabel.textContent = t("running");
  els.recList.innerHTML = "";

  setGaugeColor("#00b3ff");
  setGauge(0, "Mbps", t("ready"));

  const info = await loadInfo();

  // 本次测速的「进行中」记录：每完成一阶段即写入并实时渲染到列表顶部。
  const rec = {
    time: new Date().toLocaleString(state.language),
    clientIp: info.clientIp || "—",
    lanPing: null,
    lanDown: null,
    lanUp: null,
    wanPing: null,
    wanDown: null,
    wanUp: null,
  };

  const lan = {};
  try {
    lan.ping = await lanPing();
  } catch (e) {
    lan.ping = { avg: null, jitter: null };
  }
  rec.lanPing = lan.ping ? lan.ping.avg : null;
  rec.lanDown = null;
  renderRecords(rec);

  try {
    lan.down = await lanDownload();
  } catch (e) {
    lan.down = null;
  }
  rec.lanDown = lan.down;
  renderRecords(rec);

  try {
    lan.up = await lanUpload();
  } catch (e) {
    lan.up = null;
  }
  rec.lanUp = lan.up;
  renderRecords(rec);

  // WAN 阶段通过 onUpdate 回调实时刷新记录（延迟/下载/上传随 SSE 事件更新）。
  const wanRes = await wan((u) => {
    if (u.ping != null) {
      rec.wanPing = u.ping;
      renderRecords(rec);
    }
    if (u.down != null) {
      rec.wanDown = u.down;
      renderRecords(rec);
    }
    if (u.up != null) {
      rec.wanUp = u.up;
      renderRecords(rec);
    }
  });
  // 最终结果兜底
  rec.wanPing = wanRes.ping;
  rec.wanDown = wanRes.down;
  rec.wanUp = wanRes.up;
  renderRecords(rec);

  // 正式保存到历史记录
  addRecord(rec);

  setGaugeColor("#00d9a3");
  // 测速完成后表盘中央回到「开始测速」按钮。
  els.goLabel.textContent = t("start");
  els.go.classList.remove("running");
  els.go.disabled = false;
  running = false;
}

// ---- info 加载 -------------------------------------------------------
async function loadInfo() {
  try {
    const res = await fetch(API_ENDPOINT + "/info", { cache: "no-store" });
    const d = await res.json();
    els.lanHost.textContent = d.server || t("na");
    els.wanHost.textContent = d.server || t("na");
    els.ipServer.textContent = d.serverIp || t("na");
    els.ipPublic.textContent = d.publicIp || t("na");
    // 后端对不可用的客户端地址（loopback/空/unix socket 占位）返回 null。
    if (d.clientIp) {
      els.ipClient.textContent = d.clientIp;
      els.ipClient.title = t("clientTitle");
    } else {
      els.ipClient.textContent = t("untransparent");
      els.ipClient.title = t("clientTitleHint");
    }
    if (d.lanSpeedMbps) GAUGE_SCALE = scaleFor(d.lanSpeedMbps);
    return d;
  } catch (e) {
    els.lanHost.textContent = t("na");
    els.wanHost.textContent = t("na");
    els.ipServer.textContent = t("na");
    els.ipPublic.textContent = t("na");
    els.ipClient.textContent = t("na");
    return {};
  }
}

function bindEvents() {
  els.go.addEventListener("click", () => runAll());
  els.clearRec.addEventListener("click", () => {
    saveRecords([]);
    renderRecords();
  });
  els.aboutBtn.addEventListener("click", openAbout);
  document
    .querySelectorAll("[data-close]")
    .forEach((btn) => btn.addEventListener("click", closeModals));
  els.aboutModal.addEventListener("click", (e) => {
    if (e.target === els.aboutModal) closeModals();
  });
}

// ---- 初始化 ----------------------------------------------------------
window.addEventListener("load", async () => {
  try {
    platformConfig = await sdk.getPlatformConfig();
  } catch (e) {
    /* 保持默认 */
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
  bindEvents();
  renderRecords();
  setGaugeColor("#00b3ff");
  setGauge(0, "Mbps", t("ready"));
  loadInfo();
});
