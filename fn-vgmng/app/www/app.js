const API_ENDPOINT = location.pathname.includes("index.cgi")
  ? "../www/api.cgi"
  : "./api.cgi";
const SUPPORTED_FILESYSTEMS = new Set([
  "btrfs",
  "ext4",
  "ext3",
  "ext2",
  "xfs",
  "ntfs",
  "ntfs3",
  "exfat",
  "vfat",
]);
const RECOGNIZED_UNMOUNTABLE_FILESYSTEMS = new Set(["swap"]);

const I18N = {
  "zh-CN": {
    appTitle: "存储池管理",
    subtitle: "磁盘 / 卷管理",
    scanAndAssemble: "扫描并组装",
    disks: "磁盘",
    volumes: "卷",
    noDiskInfo: "暂未读取到磁盘分区信息。",
    noVolumeInfo: "暂未发现可挂载或已挂载的卷。",
    diskStat: "磁盘",
    partitionStat: "分区",
    mountableVolStat: "可挂载卷",
    mountedVolStat: "已挂载卷",
    mounted: "已挂载",
    mountable: "可挂载",
    lvmPV: "LVM 物理卷",
    raidMember: "RAID 成员",
    hasImportedVol: "已有导入卷",
    foundMountableVol: "发现可挂载卷",
    disk: "磁盘",
    noPartition: "无分区",
    diskOnly: "仅检测到整盘",
    canFormVol: "可形成卷",
    unmountable: "不可挂载",
    recognized: "已识别",
    readOnly: "只读",
    readWrite: "读写",
    mountRO: "只读",
    mountRW: "读写",
    unmount: "卸载",
    thAutoMount: "自动挂载",
    thDevice: "设备",
    thLabel: "标签",
    thPartId: "分区 ID",
    thCapacity: "容量",
    thFilesystem: "文件系统",
    thStatus: "状态",
    thMountPoint: "挂载位置",
    thVolDevice: "卷设备",
    thRelatedPart: "关联分区",
    thAction: "操作",
    partition: "分区",
    diskMeta: "{n} 块磁盘，{m} 个分区",
    volumeMeta: "{n} 个卷",
    mountedMode: "已挂载({mode})",
    activateDone: "扫描并组装完成",
    mountRWDone: "卷已按读写方式挂载",
    mountRODone: "卷已按只读方式挂载",
    unmountDone: "卷已卸载",
    autoMountOff: "已关闭自动挂载",
    autoMountOn: "已开启自动挂载",
    actionDone: "操作完成",
    statusRefreshed: "状态已刷新",
    fetchFailed: "获取状态失败（HTTP {status}）",
    requestFailed: "请求失败（HTTP {status}）",
    actionFailed: "操作失败",
    about: "关于",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
  },
  "en-US": {
    appTitle: "Volume Manager",
    subtitle: "Disk / Volume Management",
    scanAndAssemble: "Scan & Assemble",
    disks: "Disks",
    volumes: "Volumes",
    noDiskInfo: "No disk partition information available.",
    noVolumeInfo: "No mountable or mounted volumes found.",
    diskStat: "Disks",
    partitionStat: "Partitions",
    mountableVolStat: "Mountable",
    mountedVolStat: "Mounted",
    mounted: "Mounted",
    mountable: "Mountable",
    lvmPV: "LVM PV",
    raidMember: "RAID Member",
    hasImportedVol: "Has imported vol",
    foundMountableVol: "Mountable vol found",
    disk: "Disk",
    noPartition: "No partition",
    diskOnly: "Whole disk only",
    canFormVol: "Can form vol",
    unmountable: "Unmountable",
    recognized: "Recognized",
    readOnly: "Read-only",
    readWrite: "Read-write",
    mountRO: "Read-only",
    mountRW: "Read-write",
    unmount: "Unmount",
    thAutoMount: "Auto Mount",
    thDevice: "Device",
    thLabel: "Label",
    thPartId: "Part ID",
    thCapacity: "Capacity",
    thFilesystem: "Filesystem",
    thStatus: "Status",
    thMountPoint: "Mount Point",
    thVolDevice: "Vol Device",
    thRelatedPart: "Related Partitions",
    thAction: "Action",
    partition: "Partition",
    diskMeta: "{n} disks, {m} partitions",
    volumeMeta: "{n} volumes",
    mountedMode: "Mounted ({mode})",
    activateDone: "Scan & assemble completed",
    mountRWDone: "Volume mounted read-write",
    mountRODone: "Volume mounted read-only",
    unmountDone: "Volume unmounted",
    autoMountOff: "Auto-mount disabled",
    autoMountOn: "Auto-mount enabled",
    actionDone: "Done",
    statusRefreshed: "Status refreshed",
    fetchFailed: "Failed to fetch status (HTTP {status})",
    requestFailed: "Request failed (HTTP {status})",
    actionFailed: "Action failed",
    about: "About",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
  },
};

const appState = {
  statusData: null,
  language: "zh-CN",
  theme: "light",
};

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_error) {
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
  } catch (_error) {
    return "";
  }
}

function applyLanguage() {
  const language = safeDecode(navigator.language || "zh-CN").replace("_", "-");
  return language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function applyTheme() {
  const thememode = parentStoredValue("fnos-theme-mode");
  if (thememode === "10") return "light";
  if (thememode === "20") return "dark";

  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function t(key, params = {}) {
  const messages = I18N[appState.language] || I18N["zh-CN"];
  return String(messages[key] || I18N["zh-CN"][key] || key).replace(
    /\{(\w+)\}/g,
    (_match, name) => params[name] ?? "",
  );
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
  document.title = t("appTitle");

  if (rerender && languageChanged) {
    renderApp();
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

function displayText(value, fallback = "-") {
  return value && value !== "" ? value : fallback;
}

function filesystemName(device) {
  return String(device?.fstype || "").toLowerCase();
}

function showToast(message, isError = false) {
  const toastNode = document.getElementById("toast");
  if (!toastNode) {
    return;
  }

  toastNode.textContent = message;
  toastNode.classList.toggle("error", isError);
  toastNode.classList.remove("hidden");
  clearTimeout(toastNode._timer);
  toastNode._timer = setTimeout(() => toastNode.classList.add("hidden"), 3200);
}

function flattenDevices(devices, flattened = [], parentPath = null) {
  for (const device of devices || []) {
    flattened.push({
      ...device,
      parent: parentPath,
      children: undefined,
    });

    if (device.children && device.children.length) {
      flattenDevices(
        device.children,
        flattened,
        device.name || device.path || null,
      );
    }
  }

  return flattened;
}

function isImportableDevice(device) {
  if (!device?.path || !SUPPORTED_FILESYSTEMS.has(filesystemName(device))) {
    return false;
  }
  if (device.mountpoint === "/" || device.mountpoint === "/boot/efi") {
    return false;
  }
  return true;
}

function normalizePath(path = "") {
  const normalized = String(path || "");
  if (normalized === "/") {
    return "/";
  }
  return normalized.replace(/\/+$/, "");
}

function normalizeMountSource(source = "") {
  return String(source || "").replace(/\[[^\]]*\]$/, "");
}

function pathBase(path = "") {
  const normalized = String(path || "").replace(/\/+$/, "");
  if (!normalized) {
    return "";
  }
  const segments = normalized.split("/").filter(Boolean);
  return segments.length ? segments[segments.length - 1] : normalized;
}

function cleanLabel(label = "") {
  const normalized = String(label || "").trim();
  if (!normalized || /\\x[0-9a-f]{2}/i.test(normalized)) {
    return "";
  }
  return normalized;
}

function mountModeFromOptions(options = "") {
  return String(options || "").includes("rw") ? "rw" : "ro";
}

function mountModeText(mode = "") {
  return mode === "rw" ? t("readWrite") : t("readOnly");
}

function autoMountCheckboxId(path = "") {
  return `auto-mount-${String(path || "").replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function getManagedRoots(statusData = {}) {
  return [
    normalizePath(statusData?.mountRoot || ""),
    normalizePath(statusData?.mountAliasRoot || ""),
  ].filter(Boolean);
}

function isManagedMount(target = "", managedRoots = []) {
  const normalizedTarget = normalizePath(target);
  if (!normalizedTarget || !managedRoots.length) {
    return false;
  }
  return managedRoots.some(
    (rootPath) =>
      normalizedTarget === rootPath ||
      normalizedTarget.startsWith(`${rootPath}/`),
  );
}

function displayMountTarget(target = "", statusData = {}) {
  const normalizedTarget = normalizePath(target);
  const mountRoot = normalizePath(statusData?.mountRoot || "");
  const aliasRoot = normalizePath(statusData?.mountAliasRoot || "");

  if (!normalizedTarget || !mountRoot || !aliasRoot) {
    return normalizedTarget;
  }
  if (normalizedTarget === mountRoot) {
    return aliasRoot;
  }
  if (normalizedTarget.startsWith(`${mountRoot}/`)) {
    return `${aliasRoot}${normalizedTarget.slice(mountRoot.length)}`;
  }
  return normalizedTarget;
}

function deviceTitle(path = "", label = "", fallback = "") {
  return cleanLabel(label) || pathBase(path) || fallback || "-";
}

function devicePathCell(path = "", fallback = "") {
  const title = pathBase(path) || fallback || "-";
  const normalizedPath = displayText(path, "");

  if (!normalizedPath || title === normalizedPath) {
    return `<span class="mono">${escapeHtml(normalizedPath || title)}</span>`;
  }

  return `
    <div class="identity-title">${escapeHtml(title)}</div>
    <div class="identity-path mono">${escapeHtml(normalizedPath)}</div>
  `;
}

function upsertMountEntry(mountStore, mountEntry, managedRoots) {
  const mountTarget = normalizePath(mountEntry?.target || "");
  if (!isManagedMount(mountTarget, managedRoots)) {
    return;
  }

  const mountSource = normalizeMountSource(
    mountEntry?.source || mountEntry?.path || "",
  );
  const mountKey = `${mountTarget}::${mountSource}`;
  const previousEntry = mountStore.get(mountKey) || {};

  mountStore.set(mountKey, {
    target: mountTarget,
    source: mountSource || previousEntry.source || "",
    fstype: mountEntry?.fstype || previousEntry.fstype || "",
    options: mountEntry?.options || previousEntry.options || "",
  });
}

function collectMountedEntries(statusData) {
  const managedMounts = new Map();
  const lsblkDevices = flattenDevices(statusData?.lsblk?.blockdevices || []);
  const inventoryDisks = statusData?.inventory?.disks || [];
  const managedRoots = getManagedRoots(statusData);

  (statusData?.findmnt?.filesystems || []).forEach((filesystem) => {
    upsertMountEntry(managedMounts, filesystem, managedRoots);
  });

  lsblkDevices.forEach((device) => {
    if (device?.mountpoint) {
      upsertMountEntry(
        managedMounts,
        {
          target: device.mountpoint,
          source: device.path,
          fstype: device.fstype,
        },
        managedRoots,
      );
    }
  });

  inventoryDisks.forEach((disk) => {
    (disk.partitions || []).forEach((partition) => {
      if (partition?.mountpoint) {
        upsertMountEntry(
          managedMounts,
          {
            target: partition.mountpoint,
            source: partition.path,
            fstype: partition.fstype,
          },
          managedRoots,
        );
      }
    });
  });

  return Array.from(managedMounts.values()).sort((left, right) =>
    left.target.localeCompare(right.target),
  );
}

function collectMountedSources(mountEntries) {
  return new Set(
    mountEntries
      .map((entry) => normalizeMountSource(entry.source))
      .filter(Boolean),
  );
}

function isImportableInventoryEntry(entry) {
  if (!entry?.path || !SUPPORTED_FILESYSTEMS.has(filesystemName(entry))) {
    return false;
  }
  if (entry.mountpoint === "/" || entry.mountpoint === "/boot/efi") {
    return false;
  }
  return true;
}

function buildCandidateDevices(statusData, mountedEntries) {
  const mountedSources = collectMountedSources(mountedEntries);
  const candidateByPath = new Map();
  const flatDevices = flattenDevices(statusData?.lsblk?.blockdevices || []);

  flatDevices.forEach((device) => {
    const devicePath = normalizeMountSource(device?.path);
    if (
      !devicePath ||
      !isImportableDevice(device) ||
      device.mountpoint ||
      mountedSources.has(devicePath)
    ) {
      return;
    }

    candidateByPath.set(devicePath, {
      path: device.path,
      label: device.label || device.name || "",
      size: device.size || "",
      fstype: device.fstype || "",
      type: device.type || "",
    });
  });

  (statusData?.inventory?.disks || []).forEach((disk) => {
    const diskPath = normalizeMountSource(disk?.path);
    if (
      diskPath &&
      isImportableInventoryEntry(disk) &&
      !disk.mountpoint &&
      !mountedSources.has(diskPath) &&
      !candidateByPath.has(diskPath)
    ) {
      candidateByPath.set(diskPath, {
        path: disk.path,
        label: disk.label || "",
        size: disk.size || "",
        fstype: disk.fstype || "",
        type: "disk",
      });
    }

    (disk.partitions || []).forEach((partition) => {
      const partitionPath = normalizeMountSource(partition?.path);
      if (
        !partitionPath ||
        !isImportableInventoryEntry(partition) ||
        partition.mountpoint ||
        mountedSources.has(partitionPath) ||
        candidateByPath.has(partitionPath)
      ) {
        return;
      }

      candidateByPath.set(partitionPath, {
        path: partition.path,
        label: partition.label || "",
        size: partition.size || "",
        fstype: partition.fstype || "",
        type: "part",
      });
    });
  });

  return Array.from(candidateByPath.values()).sort((left, right) =>
    left.path.localeCompare(right.path),
  );
}

function collectAllMountTargets(statusData) {
  const mountTargetBySource = new Map();

  (statusData?.findmnt?.filesystems || []).forEach((filesystem) => {
    const source = normalizeMountSource(
      filesystem?.source || filesystem?.path || "",
    );
    const target = filesystem?.target || "";
    if (source && target && !mountTargetBySource.has(source)) {
      mountTargetBySource.set(source, target);
    }
  });

  flattenDevices(statusData?.lsblk?.blockdevices || []).forEach((device) => {
    const source = normalizeMountSource(device?.path);
    const target = device?.mountpoint || "";
    if (source && target && !mountTargetBySource.has(source)) {
      mountTargetBySource.set(source, target);
    }
  });

  (statusData?.inventory?.disks || []).forEach((disk) => {
    (disk.partitions || []).forEach((partition) => {
      const source = normalizeMountSource(partition?.path);
      const target = partition?.mountpoint || "";
      if (source && target && !mountTargetBySource.has(source)) {
        mountTargetBySource.set(source, target);
      }
    });
  });

  return mountTargetBySource;
}

function countPartitions(disks) {
  return disks.reduce(
    (count, disk) => count + (disk.partitions || []).length,
    0,
  );
}

function statCard(label, value, tone = "") {
  return `
    <div class="stat-card${tone ? ` ${tone}` : ""}">
      <div class="stat-value">${escapeHtml(value)}</div>
      <div class="stat-label">${escapeHtml(label)}</div>
    </div>
  `;
}

function renderOverview(
  _statusData,
  candidateDevices,
  mountedEntries,
  inventoryDisks,
) {
  const statsNode = document.getElementById("overviewStats");
  if (!statsNode) {
    return;
  }

  statsNode.innerHTML = [
    statCard(t("diskStat"), String(inventoryDisks.length)),
    statCard(t("partitionStat"), String(countPartitions(inventoryDisks))),
    statCard(
      t("mountableVolStat"),
      String(candidateDevices.length),
      candidateDevices.length ? "ok" : "",
    ),
    statCard(
      t("mountedVolStat"),
      String(mountedEntries.length),
      mountedEntries.length ? "info" : "",
    ),
  ].join("");
}

function inventoryStatus(partition, mountedTarget = "") {
  const fstype = filesystemName(partition);
  if (partition.mountpoint || mountedTarget) {
    return t("mounted");
  }
  if (SUPPORTED_FILESYSTEMS.has(fstype)) {
    return t("mountable");
  }
  if (fstype === "lvm2_member") {
    return t("lvmPV");
  }
  if (
    fstype === "linux_raid_member" ||
    /raid/i.test(partition.partType || "")
  ) {
    return t("raidMember");
  }
  return "-";
}

function summarizeDiskStatus(disk, candidateByPath, mountedBySource) {
  const partitions = disk.partitions || [];
  if (
    partitions.find((partition) =>
      mountedBySource.has(normalizeMountSource(partition.path)),
    )
  ) {
    return t("hasImportedVol");
  }
  if (partitions.some((partition) => candidateByPath.has(partition.path))) {
    return t("foundMountableVol");
  }
  return t("disk");
}

function getReportRows(statusData, key) {
  return statusData?.[key]?.report?.[0]?.[key.slice(0, -1)] || [];
}

function buildPartitionMaps(disks) {
  const partitionToDisk = new Map();
  const partitionMeta = new Map();

  disks.forEach((disk) => {
    (disk.partitions || []).forEach((partition) => {
      const normalizedPath = normalizeMountSource(partition.path);
      if (!normalizedPath) {
        return;
      }
      partitionToDisk.set(normalizedPath, disk.path);
      partitionMeta.set(normalizedPath, partition);
    });
  });

  return { partitionToDisk, partitionMeta };
}

function buildLsblkMaps(statusData) {
  const deviceByPath = new Map();
  const parentByPath = new Map();

  flattenDevices(statusData?.lsblk?.blockdevices || []).forEach((device) => {
    const normalizedPath = normalizeMountSource(device?.path);
    if (!normalizedPath) {
      return;
    }

    deviceByPath.set(normalizedPath, device);

    const pkname = device?.pkname
      ? String(device.pkname).startsWith("/dev/")
        ? String(device.pkname)
        : `/dev/${device.pkname}`
      : "";
    const parentPath = normalizeMountSource(device?.parent || pkname);
    if (parentPath) {
      parentByPath.set(normalizedPath, parentPath);
    }
  });

  return { deviceByPath, parentByPath };
}

function buildAutoMountMap(statusData) {
  const autoMountByDevice = new Map();

  (statusData?.autoMounts || []).forEach((entry) => {
    const devicePath = normalizeMountSource(entry?.device);
    if (devicePath) {
      autoMountByDevice.set(devicePath, entry);
    }
  });

  return autoMountByDevice;
}

function resolvePhysicalPartition(
  devicePath,
  resolutionContext,
  visited = new Set(),
) {
  const normalizedPath = normalizeMountSource(devicePath);
  if (!normalizedPath || visited.has(normalizedPath)) {
    return [];
  }

  visited.add(normalizedPath);

  if (resolutionContext.partitionToDisk.has(normalizedPath)) {
    return [normalizedPath];
  }

  const resolvedPartitions = new Set();
  const parentPath = resolutionContext.parentByPath.get(normalizedPath);

  if (parentPath) {
    resolvePhysicalPartition(parentPath, resolutionContext, visited).forEach(
      (path) => resolvedPartitions.add(path),
    );
  }

  return Array.from(resolvedPartitions);
}

function resolveVolumePartitions(devicePath, resolutionContext) {
  const normalizedPath = normalizeMountSource(devicePath);
  if (!normalizedPath) {
    return [];
  }

  const directPartitions = resolvePhysicalPartition(
    normalizedPath,
    resolutionContext,
  );
  if (directPartitions.length) {
    return directPartitions;
  }

  const logicalVolume = resolutionContext.lvByPath.get(normalizedPath);
  if (!logicalVolume) {
    return [];
  }

  const resolvedPartitions = new Set();
  const physicalVolumes =
    resolutionContext.vgToPvs.get(logicalVolume.vg_name) || [];

  physicalVolumes.forEach((pvName) => {
    resolvePhysicalPartition(pvName, resolutionContext).forEach((path) =>
      resolvedPartitions.add(path),
    );
  });

  return Array.from(resolvedPartitions);
}

function buildVolumeEntries(
  statusData,
  disks,
  candidateDevices,
  mountedEntries,
) {
  const { partitionToDisk, partitionMeta } = buildPartitionMaps(disks);
  const { deviceByPath, parentByPath } = buildLsblkMaps(statusData);
  const physicalVolumes = getReportRows(statusData, "pvs");
  const logicalVolumes = getReportRows(statusData, "lvs");
  const vgToPvs = new Map();
  const lvByPath = new Map();

  physicalVolumes.forEach((physicalVolume) => {
    const vgName = physicalVolume?.vg_name;
    const pvPath = normalizeMountSource(physicalVolume?.pv_name);
    if (!vgName || !pvPath) {
      return;
    }
    const existing = vgToPvs.get(vgName) || [];
    existing.push(pvPath);
    vgToPvs.set(vgName, existing);
  });

  logicalVolumes.forEach((logicalVolume) => {
    const lvPath = normalizeMountSource(logicalVolume?.lv_path);
    if (lvPath) {
      lvByPath.set(lvPath, logicalVolume);
    }
  });

  const resolutionContext = {
    partitionToDisk,
    partitionMeta,
    vgToPvs,
    lvByPath,
    deviceByPath,
    parentByPath,
  };

  const volumeEntryByKey = new Map();

  mountedEntries.forEach((mountEntry) => {
    const volumeKey =
      normalizeMountSource(mountEntry.source) ||
      normalizePath(mountEntry.target);
    if (!volumeKey) {
      return;
    }

    const lsblkDevice = deviceByPath.get(
      normalizeMountSource(mountEntry.source),
    );
    const volumeEntry = volumeEntryByKey.get(volumeKey) || {
      path: normalizeMountSource(mountEntry.source) || "",
      label: "",
      size: "",
      fstype: mountEntry.fstype || "",
      mountTarget: "",
      mountOptions: "",
      mountMode: "",
      mounted: false,
      candidate: false,
    };

    volumeEntry.path =
      volumeEntry.path || normalizeMountSource(mountEntry.source) || "";
    volumeEntry.label =
      volumeEntry.label || lsblkDevice?.label || lsblkDevice?.name || "";
    volumeEntry.size = volumeEntry.size || lsblkDevice?.size || "";
    volumeEntry.fstype = volumeEntry.fstype || mountEntry.fstype || "";
    volumeEntry.mountTarget =
      mountEntry.target || lsblkDevice?.mountpoint || volumeEntry.mountTarget;
    volumeEntry.mountOptions = mountEntry.options || volumeEntry.mountOptions;
    volumeEntry.mountMode = mountModeFromOptions(
      mountEntry.options || volumeEntry.mountOptions,
    );
    volumeEntry.mounted = true;
    volumeEntryByKey.set(volumeKey, volumeEntry);
  });

  candidateDevices.forEach((candidateDevice) => {
    const volumeKey = normalizeMountSource(candidateDevice.path);
    if (!volumeKey) {
      return;
    }

    const lsblkDevice = deviceByPath.get(volumeKey);
    const volumeEntry = volumeEntryByKey.get(volumeKey) || {
      path: candidateDevice.path || "",
      label: "",
      size: "",
      fstype: "",
      mountTarget: "",
      mountOptions: "",
      mountMode: "",
      mounted: false,
      candidate: false,
    };

    volumeEntry.path = volumeEntry.path || candidateDevice.path || "";
    volumeEntry.label =
      volumeEntry.label ||
      candidateDevice.label ||
      lsblkDevice?.label ||
      lsblkDevice?.name ||
      "";
    volumeEntry.size =
      volumeEntry.size || candidateDevice.size || lsblkDevice?.size || "";
    volumeEntry.fstype = volumeEntry.fstype || candidateDevice.fstype || "";
    volumeEntry.candidate = true;
    volumeEntryByKey.set(volumeKey, volumeEntry);
  });

  deviceByPath.forEach((device, devicePath) => {
    const normalizedPath = normalizeMountSource(devicePath);
    const deviceFstype = filesystemName(device);
    if (
      !normalizedPath ||
      volumeEntryByKey.has(normalizedPath) ||
      !RECOGNIZED_UNMOUNTABLE_FILESYSTEMS.has(deviceFstype)
    ) {
      return;
    }

    volumeEntryByKey.set(normalizedPath, {
      path: device.path || normalizedPath,
      label: device.label || device.name || "",
      size: device.size || "",
      fstype: device.fstype || "",
      mountTarget: "",
      mountOptions: "",
      mountMode: "",
      mounted: false,
      candidate: false,
    });
  });

  return Array.from(volumeEntryByKey.values())
    .map((volumeEntry) => {
      const normalizedPath = normalizeMountSource(volumeEntry.path);
      const lsblkDevice = deviceByPath.get(normalizedPath);
      const logicalVolume = lvByPath.get(normalizedPath);
      const relatedPartitions = resolveVolumePartitions(
        volumeEntry.path,
        resolutionContext,
      );
      const relatedDisks = Array.from(
        new Set(
          relatedPartitions
            .map((partitionPath) =>
              resolutionContext.partitionToDisk.get(partitionPath),
            )
            .filter(Boolean),
        ),
      );

      return {
        ...volumeEntry,
        label:
          volumeEntry.label ||
          lsblkDevice?.label ||
          logicalVolume?.lv_name ||
          lsblkDevice?.name ||
          "",
        size:
          volumeEntry.size || lsblkDevice?.size || logicalVolume?.lv_size || "",
        fstype: volumeEntry.fstype || lsblkDevice?.fstype || "",
        mountTarget: volumeEntry.mountTarget || lsblkDevice?.mountpoint || "",
        mountOptions: volumeEntry.mountOptions || "",
        mountMode:
          volumeEntry.mountMode ||
          mountModeFromOptions(volumeEntry.mountOptions),
        mountmode: relatedPartitions.some(
          (partitionPath) =>
            resolutionContext.partitionMeta.get(partitionPath)?.mountmode ===
            "ro",
        )
          ? "ro"
          : "rw",
        partitions: relatedPartitions,
        disks: relatedDisks,
        relation: relatedPartitions
          .map((partitionPath) => {
            const partition =
              resolutionContext.partitionMeta.get(partitionPath);
            const partLabel = deviceTitle(
              partitionPath,
              partition?.label,
              partition?.partType || t("partition"),
            );
            return `${partLabel} @ ${partitionPath}`;
          })
          .join(" @ "),
      };
    })
    .sort((left, right) => left.path.localeCompare(right.path));
}

function collectPartitionMountTargets(volumes) {
  const mountTargetByPartition = new Map();

  (volumes || []).forEach((volume) => {
    const mountTarget = normalizePath(volume?.mountTarget || "");
    if (!mountTarget) {
      return;
    }

    (volume.partitions || []).forEach((partitionPath) => {
      const normalizedPartition = normalizeMountSource(partitionPath);
      if (
        normalizedPartition &&
        !mountTargetByPartition.has(normalizedPartition)
      ) {
        mountTargetByPartition.set(normalizedPartition, mountTarget);
      }
    });
  });

  return mountTargetByPartition;
}

function renderInventory(
  disks,
  candidateDevices,
  mountedEntries,
  statusData,
  volumes,
) {
  const tableContainer = document.getElementById("inventoryTableWrap");
  const emptyState = document.getElementById("inventoryEmpty");
  const metaNode = document.getElementById("inventoryMeta");

  if (!tableContainer || !emptyState || !metaNode) {
    return;
  }

  const candidateByPath = new Map(
    candidateDevices.map((candidateDevice) => [
      candidateDevice.path,
      candidateDevice,
    ]),
  );
  const mountedBySource = new Map(
    mountedEntries.map((mountEntry) => [
      normalizeMountSource(mountEntry.source),
      mountEntry,
    ]),
  );
  const allMountTargets = collectAllMountTargets(statusData);
  const partitionMountTargets = collectPartitionMountTargets(volumes);
  const { deviceByPath } = buildLsblkMaps(statusData);

  if (!disks.length) {
    tableContainer.classList.add("hidden");
    emptyState.classList.remove("hidden");
    tableContainer.innerHTML = "";
    metaNode.textContent = "";
    return;
  }

  metaNode.textContent = t("diskMeta", {
    n: disks.length,
    m: countPartitions(disks),
  });

  const diskRows = disks
    .map((disk) => {
      const partitions = disk.partitions || [];
      const rows = [];

      rows.push(`
      <tr class="table-row disk-row">
        <td class="device-cell">${devicePathCell(disk.path, t("disk"))}</td>
        <td>${escapeHtml(cleanLabel(disk.label) || "-")}</td>
        <td>-</td>
        <td>${escapeHtml(displayText(disk.size))}</td>
        <td>${escapeHtml(displayText(disk.fstype, "-"))}</td>
        <td>${escapeHtml(summarizeDiskStatus(disk, candidateByPath, mountedBySource))}</td>
        <td>-</td>
      </tr>
    `);

      if (!partitions.length) {
        rows.push(`
        <tr class="table-row partition-row muted-row">
          <td class="device-cell subdevice">${t("noPartition")}</td>
          <td>-</td>
          <td>-</td>
          <td>-</td>
          <td>-</td>
          <td>${t("diskOnly")}</td>
          <td>-</td>
        </tr>
      `);
        return rows.join("");
      }

      partitions.forEach((partition) => {
        const normalizedPartitionPath = normalizeMountSource(partition.path);
        const mountedEntry = mountedBySource.get(normalizedPartitionPath);
        const candidateEntry = candidateByPath.get(partition.path);
        const lsblkPartition = deviceByPath.get(normalizedPartitionPath);
        const mountedTarget =
          mountedEntry?.target ||
          partitionMountTargets.get(normalizedPartitionPath) ||
          allMountTargets.get(normalizedPartitionPath) ||
          partition.mountpoint ||
          lsblkPartition?.mountpoint ||
          "";
        const statusLabel = mountedTarget
          ? t("mounted")
          : candidateEntry
            ? t("canFormVol")
            : inventoryStatus(partition, mountedTarget);

        rows.push(`
        <tr class="table-row partition-row">
          <td class="device-cell subdevice">${devicePathCell(partition.path, partition.partType || t("partition"))}</td>
          <td>${escapeHtml(cleanLabel(partition.label) || "-")}</td>
          <td>${escapeHtml(displayText(partition.partId, "-"))}</td>
          <td>${escapeHtml(displayText(partition.size))}</td>
          <td>${escapeHtml(displayText(partition.fstype))}</td>
          <td>${escapeHtml(statusLabel)}</td>
          <td class="mount-cell">${escapeHtml(mountedTarget ? displayMountTarget(mountedTarget, statusData) : "-")}</td>
        </tr>
      `);
      });

      return rows.join("");
    })
    .join("");

  tableContainer.innerHTML = `
    <table class="inventory-table">
      <thead>
        <tr>
          <th>${t("thDevice")}</th>
          <th>${t("thLabel")}</th>
          <th>${t("thPartId")}</th>
          <th>${t("thCapacity")}</th>
          <th>${t("thFilesystem")}</th>
          <th>${t("thStatus")}</th>
          <th>${t("thMountPoint")}</th>
        </tr>
      </thead>
      <tbody>
        ${diskRows}
      </tbody>
    </table>
  `;

  emptyState.classList.add("hidden");
  tableContainer.classList.remove("hidden");
}

function renderVolumes(volumes, statusData) {
  const tableContainer = document.getElementById("volumeTableWrap");
  const emptyState = document.getElementById("volumeEmpty");
  const metaNode = document.getElementById("volumeMeta");

  if (!tableContainer || !emptyState || !metaNode) {
    return;
  }

  const autoMountByDevice = buildAutoMountMap(statusData);

  metaNode.textContent = volumes.length
    ? t("volumeMeta", { n: volumes.length })
    : "";

  if (!volumes.length) {
    tableContainer.classList.add("hidden");
    tableContainer.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }

  tableContainer.innerHTML = `
    <table class="inventory-table volume-table">
      <thead>
        <tr>
          <th>${t("thAutoMount")}</th>
          <th>${t("thVolDevice")}</th>
          <th>${t("thLabel")}</th>
          <th>${t("thRelatedPart")}</th>
          <th>${t("thCapacity")}</th>
          <th>${t("thFilesystem")}</th>
          <th>${t("thStatus")}</th>
          <th>${t("thMountPoint")}</th>
          <th>${t("thAction")}</th>
        </tr>
      </thead>
      <tbody>
        ${volumes
          .map((volume) => {
            const autoMountEntry = autoMountByDevice.get(
              normalizeMountSource(volume.path),
            );
            const supportedMountMode = volume.mountmode || "rw";
            const statusLabel = volume.mounted
              ? t("mountedMode", { mode: mountModeText(volume.mountMode) })
              : volume.candidate
                ? t("mountable")
                : RECOGNIZED_UNMOUNTABLE_FILESYSTEMS.has(filesystemName(volume))
                  ? `${t("unmountable")}(${displayText(volume.fstype)})`
                  : t("recognized");
            const mountTarget =
              volume.mounted && volume.mountTarget
                ? displayMountTarget(volume.mountTarget, statusData)
                : "-";
            const checkboxId = autoMountCheckboxId(volume.path);
            const actions = volume.mounted
              ? `<button class="btn danger small" data-unmount="${escapeHtml(volume.mountTarget)}">${t("unmount")}</button>`
              : volume.candidate
                ? supportedMountMode === "ro"
                  ? `<button class="btn secondary small" data-mount="${escapeHtml(volume.path)}" data-mode="ro">${t("mountRO")}</button>`
                  : `<button class="btn secondary small" data-mount="${escapeHtml(volume.path)}" data-mode="ro">${t("mountRO")}</button>
                   <button class="btn warn small" data-mount="${escapeHtml(volume.path)}" data-mode="rw">${t("mountRW")}</button>`
                : "-";
            const autoCheckbox =
              volume.mounted || volume.candidate
                ? `
                <label class="auto-mount-checkbox" for="${escapeHtml(checkboxId)}">
                  <input
                    id="${escapeHtml(checkboxId)}"
                    type="checkbox"
                    data-auto-checkbox="1"
                    ${volume.mounted ? 'data-mounted-auto-toggle="1"' : ""}
                    data-device="${escapeHtml(volume.path)}"
                    data-target="${escapeHtml(volume.mountTarget || "")}"
                    data-mode="${escapeHtml(supportedMountMode === "ro" ? "ro" : autoMountEntry?.mode || volume.mountMode || "ro")}"
                    ${autoMountEntry ? "checked" : ""}
                  >
                </label>
              `
                : '<span class="auto-mount-placeholder">-</span>';

            return `
            <tr class="table-row ${volume.mounted ? "mounted-row" : volume.candidate ? "candidate-row" : ""}" data-volume-path="${escapeHtml(volume.path)}" data-mountmode="${escapeHtml(supportedMountMode)}">
              <td class="auto-mount-cell">${autoCheckbox}</td>
              <td class="device-cell">${devicePathCell(volume.path, "卷设备")}</td>
              <td>${escapeHtml(cleanLabel(volume.label) || displayText(volume.label))}</td>
              <td>${escapeHtml(volume.relation || "-")}</td>
              <td>${escapeHtml(displayText(volume.size))}</td>
              <td>${escapeHtml(displayText(volume.fstype))}</td>
              <td>${escapeHtml(statusLabel)}</td>
              <td class="mount-cell">${escapeHtml(mountTarget)}</td>
              <td class="table-actions">${actions}</td>
            </tr>
          `;
          })
          .join("")}
      </tbody>
    </table>
  `;

  emptyState.classList.add("hidden");
  tableContainer.classList.remove("hidden");
}

async function loadStatus() {
  const response = await fetch(API_ENDPOINT, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(t("fetchFailed", { status: response.status }));
  }

  const statusData = await response.json();
  appState.statusData = statusData || {};
  renderApp();
  return appState.statusData;
}

async function invokeAction(action, params = {}) {
  const requestBody = new URLSearchParams({ action, ...params });
  const response = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    },
    body: requestBody.toString(),
  });

  if (!response.ok) {
    throw new Error(t("requestFailed", { status: response.status }));
  }

  const result = await response.json();
  if (!result?.ok) {
    throw new Error(result?.message || t("actionFailed"));
  }

  if (result.status) {
    appState.statusData = result.status;
    renderApp();
  }

  return result;
}

function successToastMessage(action, params = {}) {
  switch (action) {
    case "activate":
      return t("activateDone");
    case "mount":
      return params.mode === "rw" ? t("mountRWDone") : t("mountRODone");
    case "unmount":
      return t("unmountDone");
    case "auto-mount":
      return params.auto === "0" ? t("autoMountOff") : t("autoMountOn");
    default:
      return t("actionDone");
  }
}

async function applyVolumeAction(action, params = {}, successMessage = "") {
  try {
    await invokeAction(action, params);
    showToast(successMessage || successToastMessage(action, params), false);
  } catch (error) {
    showToast(error.message || "操作失败", true);
    throw error;
  }
}

async function refreshStatus({ activate = false, silent = false } = {}) {
  if (activate) {
    await invokeAction("activate");
    if (!silent) {
      showToast(successToastMessage("activate"), false);
    }
    return appState.statusData;
  }

  const statusData = await loadStatus();
  if (!silent) {
    showToast(t("statusRefreshed"), false);
  }
  return statusData;
}

function renderApp() {
  const statusData = appState.statusData || {};
  const mountedEntries = collectMountedEntries(statusData);
  const candidateDevices = buildCandidateDevices(statusData, mountedEntries);
  const inventoryDisks = statusData.inventory?.disks || [];
  const volumeEntries = buildVolumeEntries(
    statusData,
    inventoryDisks,
    candidateDevices,
    mountedEntries,
  );

  renderOverview(statusData, candidateDevices, mountedEntries, inventoryDisks);
  renderInventory(
    inventoryDisks,
    candidateDevices,
    mountedEntries,
    statusData,
    volumeEntries,
  );
  renderVolumes(volumeEntries, statusData);
}

function bindUiActions() {
  document
    .getElementById("assembleBtn")
    ?.addEventListener("click", async () => {
      try {
        await refreshStatus({ activate: true });
      } catch (error) {
        showToast(error.message, true);
      }
    });

  document.getElementById("btnAbout")?.addEventListener("click", () => {
    document.getElementById("aboutModal")?.classList.remove("hidden");
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-close]")) {
      const modal = event.target.closest(".modal");
      if (modal) modal.classList.add("hidden");
      return;
    }
    if (event.target.id === "aboutModal") {
      document.getElementById("aboutModal")?.classList.add("hidden");
      return;
    }
  });

  document
    .getElementById("volumeTableWrap")
    ?.addEventListener("click", async (event) => {
      const mountButton = event.target.closest("[data-mount]");
      const unmountButton = event.target.closest("[data-unmount]");

      if (mountButton) {
        const volumeRow = mountButton.closest("[data-volume-path]");
        const autoCheckbox = volumeRow?.querySelector(
          '[data-auto-checkbox="1"]',
        );
        const requestDevice = mountButton.getAttribute("data-mount") || "";
        const supportedMountMode =
          volumeRow?.getAttribute("data-mountmode") || "rw";
        const requestMode =
          supportedMountMode === "ro"
            ? "ro"
            : mountButton.getAttribute("data-mode") || "ro";
        const requestAuto = autoCheckbox?.checked ? "1" : "0";

        if (!requestDevice) {
          return;
        }

        mountButton.disabled = true;
        try {
          await applyVolumeAction("mount", {
            device: requestDevice,
            mode: requestMode,
            auto: requestAuto,
          });
        } finally {
          mountButton.disabled = false;
        }
        return;
      }

      if (unmountButton) {
        const requestTarget = unmountButton.getAttribute("data-unmount") || "";
        if (!requestTarget) {
          return;
        }

        unmountButton.disabled = true;
        try {
          await applyVolumeAction("unmount", { target: requestTarget });
        } finally {
          unmountButton.disabled = false;
        }
      }
    });

  document
    .getElementById("volumeTableWrap")
    ?.addEventListener("change", async (event) => {
      const autoCheckbox = event.target.closest('[data-auto-checkbox="1"]');
      if (!autoCheckbox) {
        return;
      }

      const requestDevice = autoCheckbox.getAttribute("data-device") || "";
      const requestTarget = autoCheckbox.getAttribute("data-target") || "";
      const requestMode = autoCheckbox.getAttribute("data-mode") || "ro";
      const requestAuto = autoCheckbox.checked ? "1" : "0";

      if (!requestDevice) {
        return;
      }

      autoCheckbox.disabled = true;
      try {
        await applyVolumeAction("auto-mount", {
          device: requestDevice,
          target: requestTarget,
          mode: requestMode,
          auto: requestAuto,
        });
      } catch (_error) {
        autoCheckbox.checked = !autoCheckbox.checked;
      } finally {
        autoCheckbox.disabled = false;
      }
    });
}

window.addEventListener("load", async () => {
  applyPreferences();
  bindUiActions();

  try {
    await refreshStatus({ activate: true, silent: true });
  } catch (error) {
    try {
      await loadStatus();
    } catch (fetchError) {
      showToast(fetchError.message, true);
    }
  }
});

window
  .matchMedia?.("(prefers-color-scheme: dark)")
  .addEventListener("change", () => {
    applyPreferences({ rerender: true });
  });

window.addEventListener("storage", () => {
  applyPreferences({ rerender: true });
});
