const API = location.pathname.includes("/app/fn-WParted")
  ? "/app/fn-WParted/api"
  : "./api";

let currentDevice = "";
let devices = [];
let selectedPartition = null;
let selectedFreeSpace = null;
let partedInfo = null;
let _busy = false;

function showBusy() {
  document.getElementById("busyOverlay").classList.remove("hidden");
}

function hideBusy() {
  document.getElementById("busyOverlay").classList.add("hidden");
}

function preventDblClick(fn) {
  return async function (...args) {
    if (_busy) return;
    _busy = true;
    try {
      await fn.apply(this, args);
    } finally {
      _busy = false;
      hideBusy();
    }
  };
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

function normalizeTheme(value) {
  const theme = safeDecode(value).toLowerCase();
  if (theme.includes("dark") || theme === "night") return "dark";
  if (theme.includes("light") || theme === "day") return "light";
  if (theme === "10") return "light";
  if (theme === "20") return "dark";
  if (theme === "system" || theme === "auto" || theme === "os") {
    return prefersDarkTheme() ? "dark" : "light";
  }
  return "";
}

function themeMedia() {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;
}

function prefersDarkTheme() {
  return Boolean(themeMedia()?.matches);
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
  return prefersDarkTheme() ? "dark" : "light";
}

function applyTheme() {
  const theme = currentTheme();
  document.documentElement.dataset.theme = theme;
  document.body.dataset.theme = theme;
}

function watchThemeChange() {
  const media = themeMedia();
  if (media) {
    try {
      media.addEventListener("change", () => applyTheme());
    } catch (_error) {
      try {
        media.addListener(() => applyTheme());
      } catch (_error2) {}
    }
  }
  window.addEventListener("storage", (e) => {
    if (e.key === "fnos-theme-mode" || e.key === "os-theme-mode") {
      applyTheme();
    }
  });
}

const FS_COLORS = {
  ext2: "var(--part-ext2)",
  ext3: "var(--part-ext3)",
  ext4: "var(--part-ext4)",
  xfs: "var(--part-xfs)",
  zfs: "var(--part-zfs)",
  btrfs: "var(--part-btrfs)",
  f2fs: "var(--part-f2fs)",
  ntfs: "var(--part-ntfs)",
  fat16: "var(--part-fat16)",
  fat32: "var(--part-fat32)",
  vfat: "var(--part-fat32)",
  exfat: "var(--part-exfat)",
  swap: "var(--part-swap)",
  "linux-swap": "var(--part-linux-swap)",
  lvm2_member: "var(--part-lvm)",
  raid: "var(--part-raid)",
  crypto_LUKS: "var(--part-luks)",
  extended: "var(--part-extended)",
};

function fsColor(fs) {
  if (!fs) return "var(--part-unknown)";
  if (FS_COLORS[fs]) return FS_COLORS[fs];
  for (const key of Object.keys(FS_COLORS)) {
    if (fs.startsWith(key)) return FS_COLORS[key];
  }
  return "var(--part-unknown)";
}

const I18N = {
  "zh-CN": {
    refresh: "刷新",
    newPartition: "新建分区",
    deletePartition: "删除分区",
    resizeMove: "调整大小/移动",
    format: "格式化",
    check: "检查",
    mount: "挂载",
    umount: "卸载",
    wipeDisk: "擦除磁盘",
    newPartitionTable: "新建分区表",
    loading: "正在加载...",
    partitionList: "分区列表",
    partitionDetail: "分区详情",
    colPartition: "分区",
    colFilesystem: "文件系统",
    colMountPoint: "挂载点",
    colLabel: "标签",
    colSize: "大小",
    colUsed: "已用",
    colFlags: "标志",
    createPartition: "创建新分区",
    startMiB: "起始位置 (MiB)",
    endMiB: "结束位置 (MiB)",
    partitionType: "分区类型",
    primary: "主分区",
    logical: "逻辑分区",
    extended: "扩展分区",
    filesystem: "文件系统",
    label: "标签",
    cancel: "取消",
    create: "创建",
    formatPartition: "格式化分区",
    formatWarning: "警告：格式化将清除分区上的所有数据！此操作不可恢复！",
    partition: "分区",
    resizePartition: "调整分区大小",
    resize: "调整",
    mountPartition: "挂载分区",
    mountPoint: "挂载点",
    wipeDiskTitle: "擦除磁盘",
    wipeWarning: "警告：擦除磁盘将删除所有分区和数据！此操作不可恢复！",
    device: "设备",
    wipeMethod: "擦除方式",
    quickWipe: "快速擦除（仅清除签名）",
    zeroWipe: "零填充擦除（更彻底）",
    wipe: "擦除",
    newPartitionTableTitle: "新建分区表",
    newTableWarning:
      "警告：新建分区表将删除磁盘上所有现有分区！此操作不可恢复！",
    tableType: "分区表类型",
    confirm: "确定",
    confirmDelete: "确定要删除分区吗？此操作不可恢复！",
    confirmWipe: "确定要擦除整个磁盘吗？所有数据将丢失！",
    confirmNewTable: "确定要创建新的分区表吗？所有现有分区将丢失！",
    confirmFormat: "确定要格式化此分区吗？分区上的所有数据将丢失！",
    freeSpace: "未分配",
    model: "型号",
    size: "容量",
    sectorSize: "扇区大小",
    ptType: "分区表",
    rota: "类型",
    hdd: "机械硬盘",
    ssd: "固态硬盘",
    name: "名称",
    path: "路径",
    uuid: "UUID",
    partUUID: "分区UUID",
    number: "编号",
    startMiBLabel: "起始",
    endMiBLabel: "结束",
    sizeMiB: "大小",
    flags: "标志",
    fstype: "文件系统",
    noDevice: "未选择设备",
    noPartition: "未选择分区",
    operationSuccess: "操作成功",
    operationFailed: "操作失败",
    selectDeviceFirst: "请先选择一个磁盘",
    selectPartitionFirst: "请先选择一个分区",
    missingTools: "缺少必要工具",
    missingToolsDesc: "以下工具未安装，部分功能可能不可用：",
    installHint: "请在终端执行：apt-get install",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
  },
  en: {
    refresh: "Refresh",
    newPartition: "New Partition",
    deletePartition: "Delete Partition",
    resizeMove: "Resize/Move",
    format: "Format",
    check: "Check",
    mount: "Mount",
    umount: "Unmount",
    wipeDisk: "Wipe Disk",
    newPartitionTable: "New Partition Table",
    loading: "Loading...",
    partitionList: "Partition List",
    partitionDetail: "Partition Detail",
    colPartition: "Partition",
    colFilesystem: "Filesystem",
    colMountPoint: "Mount Point",
    colLabel: "Label",
    colSize: "Size",
    colUsed: "Used",
    colFlags: "Flags",
    createPartition: "Create New Partition",
    startMiB: "Start (MiB)",
    endMiB: "End (MiB)",
    partitionType: "Partition Type",
    primary: "Primary",
    logical: "Logical",
    extended: "Extended",
    filesystem: "Filesystem",
    label: "Label",
    cancel: "Cancel",
    create: "Create",
    formatPartition: "Format Partition",
    formatWarning:
      "Warning: Formatting will erase all data on the partition! This cannot be undone!",
    partition: "Partition",
    resizePartition: "Resize Partition",
    resize: "Resize",
    mountPartition: "Mount Partition",
    mountPoint: "Mount Point",
    wipeDiskTitle: "Wipe Disk",
    wipeWarning:
      "Warning: Wiping the disk will delete all partitions and data! This cannot be undone!",
    device: "Device",
    wipeMethod: "Wipe Method",
    quickWipe: "Quick wipe (signatures only)",
    zeroWipe: "Zero fill (more thorough)",
    wipe: "Wipe",
    newPartitionTableTitle: "New Partition Table",
    newTableWarning:
      "Warning: Creating a new partition table will delete all existing partitions! This cannot be undone!",
    tableType: "Partition Table Type",
    confirm: "Confirm",
    confirmDelete:
      "Are you sure you want to delete this partition? This cannot be undone!",
    confirmWipe:
      "Are you sure you want to wipe the entire disk? All data will be lost!",
    confirmNewTable:
      "Are you sure you want to create a new partition table? All existing partitions will be lost!",
    confirmFormat:
      "Are you sure you want to format this partition? All data will be lost!",
    freeSpace: "Free Space",
    model: "Model",
    size: "Size",
    sectorSize: "Sector Size",
    ptType: "Partition Table",
    rota: "Type",
    hdd: "HDD",
    ssd: "SSD",
    name: "Name",
    path: "Path",
    uuid: "UUID",
    partUUID: "Partition UUID",
    number: "Number",
    startMiBLabel: "Start",
    endMiBLabel: "End",
    sizeMiB: "Size",
    flags: "Flags",
    fstype: "Filesystem",
    noDevice: "No device selected",
    noPartition: "No partition selected",
    operationSuccess: "Operation successful",
    operationFailed: "Operation failed",
    selectDeviceFirst: "Please select a disk first",
    selectPartitionFirst: "Please select a partition first",
    missingTools: "Missing Tools",
    missingToolsDesc:
      "The following tools are not installed. Some features may be unavailable:",
    installHint: "Run in terminal: apt-get install",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
  },
};

function t(key) {
  const lang = navigator.language.startsWith("zh") ? "zh-CN" : "en";
  return (I18N[lang] && I18N[lang][key]) || I18N["en"][key] || key;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const text = t(key);
    if (text) el.textContent = text;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    const text = t(key);
    if (text) el.placeholder = text;
  });
}

async function api(action, body = null) {
  const url = `${API}?${action}`;
  const options = { method: body ? "POST" : "GET" };
  if (body) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const resp = await fetch(url, options);
  return resp.json();
}

function showToast(message, type = "") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast" + (type ? " " + type : "");
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3000);
}

function showConfirm(message) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirmModal");
    document.getElementById("confirmMessage").textContent = message;
    modal.classList.remove("hidden");
    const ok = document.getElementById("confirmOk");
    const cancel = document.getElementById("confirmCancel");
    function cleanup() {
      modal.classList.add("hidden");
      ok.removeEventListener("click", onOk);
      cancel.removeEventListener("click", onCancel);
    }
    function onOk() {
      cleanup();
      resolve(true);
    }
    function onCancel() {
      cleanup();
      resolve(false);
    }
    ok.addEventListener("click", onOk);
    cancel.addEventListener("click", onCancel);
  });
}

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

async function checkMissingTools() {
  try {
    const data = await api("check-tools");
    if (data.ok && data.missing && Object.keys(data.missing).length > 0) {
      const missingPackages = [...new Set(Object.values(data.missing))];
      const missingTools = Object.keys(data.missing);
      const banner = document.createElement("div");
      banner.className = "tools-warn";
      banner.innerHTML = `
        <div class="tools-warn-title">⚠ ${t("missingTools")}</div>
        <div class="tools-warn-desc">${t("missingToolsDesc")}</div>
        <div class="tools-warn-list">${missingTools.join(", ")}</div>
        <div class="tools-warn-hint">${t("installHint")} ${missingPackages.join(" ")}</div>
      `;
      const content = document.querySelector(".content");
      content.insertBefore(banner, content.firstChild);
    }
  } catch (err) {
    // ignore
  }
}

function formatSize(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
  let val = bytes;
  for (const unit of units) {
    if (Math.abs(val) < 1024) return `${val.toFixed(1)} ${unit}`;
    val /= 1024;
  }
  return `${val.toFixed(1)} EiB`;
}

async function loadDevices() {
  document.getElementById("loadingState").classList.remove("hidden");
  document.getElementById("errorState").classList.add("hidden");
  document.getElementById("diskView").classList.add("hidden");
  document.getElementById("tableSection").classList.add("hidden");
  document.getElementById("detailSection").classList.add("hidden");

  try {
    const data = await api("disks");
    if (!data.ok) throw new Error(data.message || "Failed to load devices");
    devices = data.devices || [];
    renderDeviceSelect();
    if (devices.length > 0) {
      if (!currentDevice || !devices.find((d) => d.path === currentDevice)) {
        currentDevice = devices[0].path;
      }
      document.getElementById("deviceSelect").value = currentDevice;
      await loadDeviceDetail();
    }
    document.getElementById("loadingState").classList.add("hidden");
  } catch (err) {
    document.getElementById("loadingState").classList.add("hidden");
    document.getElementById("errorState").textContent = err.message;
    document.getElementById("errorState").classList.remove("hidden");
  }
}

function renderDeviceSelect() {
  const select = document.getElementById("deviceSelect");
  select.innerHTML = "";
  devices.forEach((d) => {
    const opt = document.createElement("option");
    opt.value = d.path;
    const rota =
      d.rota === 1 ? ` (${t("hdd")})` : d.rota === 0 ? ` (${t("ssd")})` : "";
    opt.textContent =
      `${d.path} - ${formatSize(d.size)}${rota} ${d.model || ""}`.trim();
    select.appendChild(opt);
  });
}

async function loadDeviceDetail() {
  if (!currentDevice) return;

  try {
    const data = await api("disk-detail", { device: currentDevice });
    if (!data.ok) throw new Error(data.message || "Failed to load detail");

    const device = devices.find((d) => d.path === currentDevice);
    partedInfo = data.parted;

    renderDiskInfo(device);
    renderPartitionCanvas(device, data.parted);
    renderPartitionTable(device, data.parted);
    document.getElementById("diskView").classList.remove("hidden");
    document.getElementById("tableSection").classList.remove("hidden");
    updateToolbarState();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderDiskInfo(device) {
  if (!device) return;
  const info = document.getElementById("diskInfo");
  const rotaLabel =
    device.rota === 1 ? t("hdd") : device.rota === 0 ? t("ssd") : "";
  info.innerHTML = `
    <div class="info-item"><span class="info-label">${t("device")}:</span><span class="info-value">${device.path}</span></div>
    <div class="info-item"><span class="info-label">${t("model")}:</span><span class="info-value">${device.model || "-"}</span></div>
    <div class="info-item"><span class="info-label">${t("size")}:</span><span class="info-value">${formatSize(device.size)}</span></div>
    <div class="info-item"><span class="info-label">${t("sectorSize")}:</span><span class="info-value">${device.sectorSize || 512} B</span></div>
    <div class="info-item"><span class="info-label">${t("ptType")}:</span><span class="info-value">${device.pttype || "-".toUpperCase()}</span></div>
    ${rotaLabel ? `<div class="info-item"><span class="info-label">${t("rota")}:</span><span class="info-value">${rotaLabel}</span></div>` : ""}
  `;
}

function renderPartitionCanvas(device, parted) {
  const canvas = document.getElementById("partitionCanvas");
  canvas.innerHTML = "";
  const legend = document.getElementById("partitionLegend");
  legend.innerHTML = "";

  if (!parted) return;

  const partitions = parted.partitions || [];
  const freeSpaces = parted.freeSpaces || [];
  const allItems = [];

  partitions.forEach((p) => {
    allItems.push({
      type: "partition",
      startMiB: parseFloat(p.startMiB) || 0,
      endMiB: parseFloat(p.endMiB) || 0,
      sizeMiB: parseFloat(p.sizeMiB) || 0,
      fstype: p.fstype,
      name: p.name,
      number: p.number,
      flags: p.flags,
    });
  });

  freeSpaces.forEach((f, idx) => {
    allItems.push({
      type: "free",
      startMiB: parseFloat(f.startMiB) || 0,
      endMiB: parseFloat(f.endMiB) || 0,
      sizeMiB: parseFloat(f.sizeMiB) || 0,
      _freeIdx: idx,
    });
  });

  allItems.sort((a, b) => a.startMiB - b.startMiB);

  const totalMiB = device.size / (1024 * 1024);
  if (totalMiB <= 0) return;

  const seenFs = new Set();

  allItems.forEach((item) => {
    const leftPct = (item.startMiB / totalMiB) * 100;
    const widthPct = (item.sizeMiB / totalMiB) * 100;

    const bar = document.createElement("div");
    bar.className =
      "partition-bar" + (item.type === "free" ? " free-space" : "");
    bar.style.left = leftPct + "%";
    bar.style.width = Math.max(widthPct, 0.3) + "%";

    if (item.type === "partition") {
      bar.style.background = fsColor(item.fstype || item.flags);
      bar.dataset.partNumber = item.number;
      bar.dataset.fstype = item.fstype;
      bar.dataset.startMiB = item.startMiB;
      bar.dataset.endMiB = item.endMiB;
      bar.dataset.sizeMiB = item.sizeMiB;

      const label = item.fstype || item.flags || item.number;
      bar.textContent = widthPct > 3 ? label : "";

      if (selectedPartition && selectedPartition.number === item.number) {
        bar.classList.add("selected");
      }

      bar.addEventListener("click", () => selectPartition(item));

      const legendKey = item.fstype || item.flags;
      if (legendKey && !seenFs.has(legendKey)) {
        seenFs.add(legendKey);
        const li = document.createElement("div");
        li.className = "legend-item";
        li.innerHTML = `<span class="legend-dot" style="background:${fsColor(legendKey)}"></span>${legendKey}`;
        legend.appendChild(li);
      }
    } else {
      bar.textContent = widthPct > 4 ? t("freeSpace") : "";
      bar.dataset.freeIdx = String(item._freeIdx);
      bar.addEventListener("click", () => {
        selectedPartition = null;
        selectedFreeSpace = item;
        document
          .querySelectorAll(".partition-bar.selected")
          .forEach((b) => b.classList.remove("selected"));
        document
          .querySelectorAll(".data-table tbody tr.selected")
          .forEach((r) => r.classList.remove("selected"));
        bar.classList.add("selected");
        document
          .querySelectorAll(
            `.data-table tbody tr.free-row[data-free-idx="${item._freeIdx}"]`,
          )
          .forEach((r) => {
            r.classList.add("selected");
            r.scrollIntoView({ block: "nearest", behavior: "smooth" });
          });
        updateToolbarState();
        document.getElementById("createStart").value = item.startMiB;
        document.getElementById("createEnd").value = item.endMiB;
        showFreeSpaceDetail(item);
      });
    }

    canvas.appendChild(bar);
  });

  const freeLegend = document.createElement("div");
  freeLegend.className = "legend-item";
  freeLegend.innerHTML = `<span class="legend-dot free"></span>${t("freeSpace")}`;
  legend.appendChild(freeLegend);
}

function renderPartitionTable(device, parted) {
  const tbody = document.getElementById("partitionBody");
  tbody.innerHTML = "";

  if (!parted) return;

  const partitions = parted.partitions || [];
  const freeSpaces = parted.freeSpaces || [];

  const allRows = [];
  partitions.forEach((p) => {
    allRows.push({
      type: "partition",
      data: p,
      startMiB: parseFloat(p.startMiB) || 0,
    });
  });
  freeSpaces.forEach((f, idx) => {
    allRows.push({
      type: "free",
      data: f,
      idx,
      startMiB: parseFloat(f.startMiB) || 0,
    });
  });
  allRows.sort((a, b) => a.startMiB - b.startMiB);

  allRows.forEach((row) => {
    if (row.type === "partition") {
      const p = row.data;
      const tr = document.createElement("tr");
      tr.dataset.partNumber = p.number;

      const partName = p.number ? buildPartName(device.path, p.number) : "-";
      const fsBadge =
        p.fstype || p.flags
          ? `<span class="fs-badge" style="background:${fsColor(p.fstype || p.flags)}">${p.fstype || p.flags}</span>`
          : "-";

      const lsblkPart = findLsblkPartition(device, p.number);
      const mountPoint = lsblkPart ? lsblkPart.mountpoint : "";
      const mountBadge = mountPoint
        ? `<span class="mount-badge">${mountPoint}</span>`
        : "";
      const label = lsblkPart ? lsblkPart.label || "" : "";

      let usedCell = "-";
      if (lsblkPart && lsblkPart.mountpoint) {
        usedCell = "-";
      }

      tr.innerHTML = `
        <td>${partName}</td>
        <td>${fsBadge}</td>
        <td>${mountBadge || "-"}</td>
        <td>${label || "-"}</td>
        <td>${p.sizeMiB} MiB</td>
        <td>${usedCell}</td>
        <td>${p.flags || "-"}</td>
      `;

      tr.addEventListener("click", () => selectPartition(p));
      if (selectedPartition && selectedPartition.number === p.number) {
        tr.classList.add("selected");
      }

      tbody.appendChild(tr);
    } else {
      const f = row.data;
      const idx = row.idx;
      const tr = document.createElement("tr");
      tr.className = "free-row";
      tr.dataset.freeIdx = idx;

      tr.innerHTML = `
        <td>${t("freeSpace")}</td>
        <td>-</td>
        <td>-</td>
        <td>-</td>
        <td>${f.sizeMiB} MiB</td>
        <td>-</td>
        <td>-</td>
      `;

      tr.addEventListener("click", () => {
        selectedPartition = null;
        selectedFreeSpace = {
          type: "free",
          startMiB: parseFloat(f.startMiB) || 0,
          endMiB: parseFloat(f.endMiB) || 0,
          sizeMiB: parseFloat(f.sizeMiB) || 0,
        };
        document
          .querySelectorAll(".partition-bar.selected")
          .forEach((b) => b.classList.remove("selected"));
        document
          .querySelectorAll(".data-table tbody tr.selected")
          .forEach((r) => r.classList.remove("selected"));
        tr.classList.add("selected");
        document
          .querySelectorAll(`.partition-bar[data-free-idx="${idx}"]`)
          .forEach((b) => {
            b.classList.add("selected");
            b.scrollIntoView({ block: "nearest", behavior: "smooth" });
          });
        updateToolbarState();
        document.getElementById("createStart").value = f.startMiB;
        document.getElementById("createEnd").value = f.endMiB;
        showFreeSpaceDetail(selectedFreeSpace);
      });

      tbody.appendChild(tr);
    }
  });
}

function buildPartName(devicePath, partNumber) {
  if (/nvme\d+n\d+$/.test(devicePath) || /mmcblk\d+$/.test(devicePath)) {
    return `${devicePath}p${partNumber}`;
  }
  return `${devicePath}${partNumber}`;
}

function findLsblkPartition(device, partNumber) {
  if (!device || !device.partitions) return null;
  for (const part of device.partitions) {
    const name = part.name || "";
    const match = name.match(/(\d+)$/);
    if (match && parseInt(match[1]) === partNumber) return part;
    if (part.partn && parseInt(part.partn) === partNumber) return part;
  }
  return null;
}

function selectPartition(partInfo) {
  selectedPartition = partInfo;
  selectedFreeSpace = null;
  document
    .querySelectorAll(".partition-bar.selected")
    .forEach((b) => b.classList.remove("selected"));
  document
    .querySelectorAll(".data-table tbody tr.selected")
    .forEach((r) => r.classList.remove("selected"));

  document
    .querySelectorAll(`.partition-bar[data-part-number="${partInfo.number}"]`)
    .forEach((b) => b.classList.add("selected"));
  document
    .querySelectorAll(
      `.data-table tbody tr[data-part-number="${partInfo.number}"]`,
    )
    .forEach((r) => {
      r.classList.add("selected");
      r.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });

  updateToolbarState();
  showPartitionDetail(partInfo);
}

function showPartitionDetail(partInfo) {
  const section = document.getElementById("detailSection");
  const grid = document.getElementById("detailGrid");
  const device = devices.find((d) => d.path === currentDevice);
  const lsblkPart = device ? findLsblkPartition(device, partInfo.number) : null;

  const partPath = partInfo.number
    ? buildPartName(currentDevice, partInfo.number)
    : "-";

  grid.innerHTML = `
    <div class="detail-item"><span class="detail-label">${t("path")}</span><span class="detail-value">${partPath}</span></div>
    <div class="detail-item"><span class="detail-label">${t("number")}</span><span class="detail-value">${partInfo.number || "-"}</span></div>
    <div class="detail-item"><span class="detail-label">${t("fstype")}</span><span class="detail-value">${partInfo.fstype || "-"}</span></div>
    <div class="detail-item"><span class="detail-label">${t("startMiBLabel")}</span><span class="detail-value">${partInfo.startMiB} MiB</span></div>
    <div class="detail-item"><span class="detail-label">${t("endMiBLabel")}</span><span class="detail-value">${partInfo.endMiB} MiB</span></div>
    <div class="detail-item"><span class="detail-label">${t("sizeMiB")}</span><span class="detail-value">${partInfo.sizeMiB} MiB</span></div>
    <div class="detail-item"><span class="detail-label">${t("flags")}</span><span class="detail-value">${partInfo.flags || "-"}</span></div>
    <div class="detail-item"><span class="detail-label">${t("label")}</span><span class="detail-value">${lsblkPart ? lsblkPart.label || "-" : "-"}</span></div>
    <div class="detail-item"><span class="detail-label">${t("uuid")}</span><span class="detail-value">${lsblkPart ? lsblkPart.uuid || "-" : "-"}</span></div>
    <div class="detail-item"><span class="detail-label">${t("partUUID")}</span><span class="detail-value">${lsblkPart ? lsblkPart.partuuid || "-" : "-"}</span></div>
    <div class="detail-item"><span class="detail-label">${t("colMountPoint")}</span><span class="detail-value">${lsblkPart ? lsblkPart.mountpoint || "-" : "-"}</span></div>
  `;

  section.classList.remove("hidden");
}

function showFreeSpaceDetail(item) {
  const section = document.getElementById("detailSection");
  const grid = document.getElementById("detailGrid");

  grid.innerHTML = `
    <div class="detail-item"><span class="detail-label">${t("fstype")}</span><span class="detail-value">${t("freeSpace")}</span></div>
    <div class="detail-item"><span class="detail-label">${t("startMiBLabel")}</span><span class="detail-value">${item.startMiB} MiB</span></div>
    <div class="detail-item"><span class="detail-label">${t("endMiBLabel")}</span><span class="detail-value">${item.endMiB} MiB</span></div>
    <div class="detail-item"><span class="detail-label">${t("sizeMiB")}</span><span class="detail-value">${item.sizeMiB} MiB</span></div>
  `;

  section.classList.remove("hidden");
}

function updateToolbarState() {
  const hasDevice = !!currentDevice;
  const hasPart = !!selectedPartition;
  const hasFree = !!selectedFreeSpace;
  const isMounted =
    hasPart &&
    (() => {
      const device = devices.find((d) => d.path === currentDevice);
      if (!device) return false;
      const lsblk = findLsblkPartition(device, selectedPartition.number);
      return lsblk && lsblk.mountpoint;
    })();

  document.getElementById("newPartBtn").disabled = !hasFree;
  document.getElementById("deletePartBtn").disabled = !hasPart;
  document.getElementById("resizePartBtn").disabled = !hasPart;
  document.getElementById("formatBtn").disabled = !hasPart;
  document.getElementById("checkBtn").disabled = !hasPart;
  document.getElementById("mountBtn").disabled = !hasPart || isMounted;
  document.getElementById("umountBtn").disabled = !hasPart || !isMounted;
  document.getElementById("wipeBtn").disabled = !hasDevice;
  document.getElementById("newTableBtn").disabled = !hasDevice;
}

async function createPartition() {
  const startMiB = document.getElementById("createStart").value;
  const endMiB = document.getElementById("createEnd").value;
  const partType = document.getElementById("createPartType").value;
  const fstype = document.getElementById("createFstype").value;
  const label = document.getElementById("createLabel").value;

  if (!startMiB || !endMiB) {
    showToast(t("startMiB") + " / " + t("endMiB") + " required", "warn");
    return;
  }

  showBusy();
  try {
    const data = await api("partition-create", {
      device: currentDevice,
      startMiB: parseFloat(startMiB),
      endMiB: parseFloat(endMiB),
      partType: partType,
      fstype: fstype,
      label: label,
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      closeModal("createModal");
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deletePartition() {
  if (!selectedPartition) return;
  const confirmed = await showConfirm(t("confirmDelete"));
  if (!confirmed) return;

  showBusy();
  try {
    const data = await api("partition-delete", {
      device: currentDevice,
      partNumber: selectedPartition.number,
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      selectedPartition = null;
      selectedFreeSpace = null;
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function resizePartition() {
  if (!selectedPartition) return;
  const endMiB = document.getElementById("resizeEnd").value;
  if (!endMiB) {
    showToast(t("endMiB") + " required", "warn");
    return;
  }

  showBusy();
  try {
    const data = await api("partition-resize", {
      device: currentDevice,
      partNumber: selectedPartition.number,
      endMiB: parseFloat(endMiB),
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      closeModal("resizeModal");
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function formatPartition() {
  if (!selectedPartition) return;
  const confirmed = await showConfirm(t("confirmFormat"));
  if (!confirmed) return;

  const fstype = document.getElementById("formatFstype").value;
  const label = document.getElementById("formatLabel").value;
  const partPath = buildPartName(currentDevice, selectedPartition.number);

  showBusy();
  try {
    const data = await api("partition-format", {
      partition: partPath,
      fstype: fstype,
      label: label,
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      closeModal("formatModal");
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function checkPartition() {
  if (!selectedPartition) return;
  const partPath = buildPartName(currentDevice, selectedPartition.number);

  showBusy();
  try {
    const data = await api("partition-check", {
      partition: partPath,
      fstype: selectedPartition.fstype || "",
    });
    if (data.ok) {
      const output = data.output || data.errors || "Check completed";
      showToast(output.substring(0, 100), data.rc === 0 ? "success" : "warn");
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function mountPartition() {
  const mountPoint = document.getElementById("mountPoint").value;
  const partPath = buildPartName(currentDevice, selectedPartition.number);

  if (!mountPoint) {
    showToast(t("mountPoint") + " required", "warn");
    return;
  }

  showBusy();
  try {
    const data = await api("partition-mount", {
      partition: partPath,
      mountPoint: mountPoint,
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      closeModal("mountModal");
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function umountPartition() {
  if (!selectedPartition) return;
  const device = devices.find((d) => d.path === currentDevice);
  const lsblk = device
    ? findLsblkPartition(device, selectedPartition.number)
    : null;
  const target =
    lsblk && lsblk.mountpoint
      ? lsblk.mountpoint
      : buildPartName(currentDevice, selectedPartition.number);

  showBusy();
  try {
    const data = await api("partition-umount", { target });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function wipeDisk() {
  const confirmed = await showConfirm(t("confirmWipe"));
  if (!confirmed) return;

  const method = document.getElementById("wipeMethod").value;

  showBusy();
  try {
    const data = await api("disk-wipe", {
      device: currentDevice,
      method: method,
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      closeModal("wipeModal");
      selectedPartition = null;
      selectedFreeSpace = null;
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function newPartitionTable() {
  const confirmed = await showConfirm(t("confirmNewTable"));
  if (!confirmed) return;

  const labelType = document.getElementById("newTableType").value;

  showBusy();
  try {
    const data = await api("disk-label", {
      device: currentDevice,
      labelType: labelType,
    });
    if (data.ok) {
      showToast(t("operationSuccess"), "success");
      closeModal("newTableModal");
      selectedPartition = null;
      selectedFreeSpace = null;
      await loadDeviceDetail();
    } else {
      showToast(data.message || t("operationFailed"), "error");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

function initEventListeners() {
  document.getElementById("deviceSelect").addEventListener("change", (e) => {
    currentDevice = e.target.value;
    selectedPartition = null;
    loadDeviceDetail();
  });

  document.getElementById("refreshBtn").addEventListener(
    "click",
    preventDblClick(async () => {
      selectedPartition = null;
      showBusy();
      await loadDevices();
    }),
  );

  document.getElementById("aboutBtn").addEventListener("click", () => {
    openModal("aboutModal");
  });

  document.getElementById("newPartBtn").addEventListener("click", () => {
    if (!currentDevice) return;
    if (selectedFreeSpace) {
      document.getElementById("createStart").value = selectedFreeSpace.startMiB;
      document.getElementById("createEnd").value = selectedFreeSpace.endMiB;
    } else if (
      partedInfo &&
      partedInfo.freeSpaces &&
      partedInfo.freeSpaces.length > 0
    ) {
      const firstFree = partedInfo.freeSpaces[0];
      document.getElementById("createStart").value = firstFree.startMiB;
      document.getElementById("createEnd").value = firstFree.endMiB;
    }
    openModal("createModal");
  });

  document
    .getElementById("deletePartBtn")
    .addEventListener("click", preventDblClick(deletePartition));

  document.getElementById("resizePartBtn").addEventListener("click", () => {
    if (!selectedPartition) return;
    document.getElementById("resizePartition").value = buildPartName(
      currentDevice,
      selectedPartition.number,
    );
    document.getElementById("resizeEnd").value = selectedPartition.endMiB;
    document.getElementById("resizeInfo").textContent =
      `${t("startMiBLabel")}: ${selectedPartition.startMiB} MiB → ${t("endMiBLabel")}: ${selectedPartition.endMiB} MiB`;
    openModal("resizeModal");
  });

  document.getElementById("formatBtn").addEventListener("click", () => {
    if (!selectedPartition) return;
    document.getElementById("formatPartition").value = buildPartName(
      currentDevice,
      selectedPartition.number,
    );
    document.getElementById("formatFstype").value = "ext4";
    document.getElementById("formatLabel").value = "";
    openModal("formatModal");
  });

  document
    .getElementById("checkBtn")
    .addEventListener("click", preventDblClick(checkPartition));

  document.getElementById("mountBtn").addEventListener("click", () => {
    if (!selectedPartition) return;
    document.getElementById("mountPartition").value = buildPartName(
      currentDevice,
      selectedPartition.number,
    );
    document.getElementById("mountPoint").value = "";
    openModal("mountModal");
  });

  document
    .getElementById("umountBtn")
    .addEventListener("click", preventDblClick(umountPartition));

  document.getElementById("wipeBtn").addEventListener("click", () => {
    if (!currentDevice) return;
    document.getElementById("wipeDevice").value = currentDevice;
    openModal("wipeModal");
  });

  document.getElementById("newTableBtn").addEventListener("click", () => {
    if (!currentDevice) return;
    document.getElementById("newTableDevice").value = currentDevice;
    openModal("newTableModal");
  });

  document
    .getElementById("createConfirmBtn")
    .addEventListener("click", preventDblClick(createPartition));
  document
    .getElementById("formatConfirmBtn")
    .addEventListener("click", preventDblClick(formatPartition));
  document
    .getElementById("resizeConfirmBtn")
    .addEventListener("click", preventDblClick(resizePartition));
  document
    .getElementById("mountConfirmBtn")
    .addEventListener("click", preventDblClick(mountPartition));
  document
    .getElementById("wipeConfirmBtn")
    .addEventListener("click", preventDblClick(wipeDisk));
  document
    .getElementById("newTableConfirmBtn")
    .addEventListener("click", preventDblClick(newPartitionTable));

  document.getElementById("closeDetailBtn").addEventListener("click", () => {
    document.getElementById("detailSection").classList.add("hidden");
  });

  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal");
      if (modal) modal.classList.add("hidden");
    });
  });

  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  applyTheme();
  watchThemeChange();
  applyI18n();
  initEventListeners();
  checkMissingTools();
  loadDevices();
});
