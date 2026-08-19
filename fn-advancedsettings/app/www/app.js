const API_ENDPOINT = location.pathname.includes("/app/fn-advancedsettings")
  ? "/app/fn-advancedsettings/api"
  : "./api";

const sections = [
  ["boot", "bootSettings"],
  ["power", "powerSettings"],
  ["display", "displaySettings"],
  ["ssh", "sshSettings"],
  ["cpu", "cpuSettings"],
  ["dns", "dnsSettings"],
  ["network", "networkSettings"],
  ["proxy", "proxySettings"],
  ["identity", "identitySettings"],
  ["device", "deviceSettings"],
  ["port", "portSettings"],
  ["process", "processSettings"],
  ["service", "serviceSettings"],
  ["diag", "diagSettings"],
];

const icons = {
  boot: '<svg viewBox="0 0 24 24"><path d="M5 17h14M7 17l1.2-8h7.6L17 17"/><path d="M9 9V6h6v3M10 13h4"/></svg>',
  power:
    '<svg viewBox="0 0 24 24"><path d="M12 3v8"/><path d="M8 5.5a8 8 0 1 0 8 0"/></svg>',
  ssh: '<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="14" rx="2"/><path d="M8 10l2 2-2 2M12 14h4"/></svg>',
  cpu: '<svg viewBox="0 0 24 24"><rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M4 9h3M4 15h3M17 9h3M17 15h3M9 4v3M15 4v3M9 17v3M15 17v3"/></svg>',
  display:
    '<svg viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
  dns: '<svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/><circle cx="7" cy="7" r="1"/><circle cx="7" cy="12" r="1"/><circle cx="7" cy="17" r="1"/></svg>',
  network:
    '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="5" rx="1"/><rect x="4" y="16" width="6" height="5" rx="1"/><rect x="14" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M7 16v-4h10v4"/></svg>',
  proxy:
    '<svg viewBox="0 0 24 24"><path d="M5 12a7 7 0 0 1 12.7-4"/><path d="M19 12a7 7 0 0 1-12.7 4"/><path d="M17 4v4h-4M7 20v-4h4"/></svg>',
  identity:
    '<svg viewBox="0 0 24 24"><path d="M12 3l7 3v5c0 4.5-2.8 8-7 10-4.2-2-7-5.5-7-10V6l7-3z"/><path d="M9 12l2 2 4-5"/></svg>',
  device:
    '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6M9 13h4M9 17h2"/></svg>',
  port: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>',
  process:
    '<svg viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/><path d="M7 8h2M7 12h4"/></svg>',
  service:
    '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  diag: '<svg viewBox="0 0 24 24"><path d="M3 21l4-4M7 17l3-3M10 14l3-6M13 8l4-2M17 6l4-1"/><circle cx="7" cy="17" r="1.5"/><circle cx="17" cy="6" r="1.5"/></svg>',
};

const powerFields = [
  "HandlePowerKey",
  "HandlePowerKeyLongPress",
  "HandleRebootKey",
  "HandleRebootKeyLongPress",
  "HandleSuspendKey",
  "HandleSuspendKeyLongPress",
  "HandleHibernateKey",
  "HandleHibernateKeyLongPress",
  "HandleLidSwitch",
  "HandleLidSwitchExternalPower",
  "HandleLidSwitchDocked",
];

const sshFields = [
  "PermitRootLogin",
  "PasswordAuthentication",
  "PubkeyAuthentication",
  "PermitEmptyPasswords",
  "PermitTTY",
  "X11Forwarding",
  "AllowTcpForwarding",
  "AllowAgentForwarding",
  "GatewayPorts",
];
const sshOptions = {
  PermitRootLogin: ["yes", "no", "prohibit-password"],
  PasswordAuthentication: ["yes", "no"],
  PubkeyAuthentication: ["yes", "no"],
  PermitEmptyPasswords: ["yes", "no"],
  PermitTTY: ["yes", "no"],
  X11Forwarding: ["yes", "no"],
  AllowTcpForwarding: ["yes", "no"],
  AllowAgentForwarding: ["yes", "no"],
  GatewayPorts: ["yes", "no", "clientspecified"],
};
const bootFields = [
  "GRUB_TIMEOUT",
  "GRUB_CMDLINE_LINUX_DEFAULT",
  "GRUB_DEFAULT",
  "GRUB_DISABLE_OS_PROBER",
  "GRUB_CMDLINE_LINUX",
];

const kernelParams = [
  ["quiet", "quietDesc"],
  ["splash", "splashDesc"],
  ["nomodeset", "nomodesetDesc"],
  ["console=ttyS0,115200n8", "consoleTtySDesc"],
  ["net.ifnames=0", "netIfnames0Desc"],
  ["panic=5", "panic5Desc"],
  ["nowatchdog", "nowatchdogDesc"],
  ["pcie_aspm=off", "pcieAspmOffDesc"],
  ["modprobe.blacklist=module", "blacklistDesc"],
  ["iommu=pt", "iommuPtDesc"],
  ["intel_iommu=on", "intelIommuDesc"],
  ["amd_iommu=on", "amdIommuDesc"],
  ["intremap=off", "intremapOffDesc"],
  ["amd_iommu_intr=legacy", "amdIommuIntrLegacyDesc"],
  ["nox2apic", "nox2apicDesc"],
  ["intel_pstate=disable", "intelPstateDisableDesc"],
  ["amd_pstate=disable", "amdPstateDisableDesc"],
  ["split_lock_detect=off", "splitLockDetectOffDesc"],
  ["hugepages=number", "hugepagesDesc"],
  ["transparent_hugepage=never", "thpNeverDesc"],
  ["mitigations=off", "mitigationsOffDesc"],
  ["nosmp", "nosmpDesc"],
  ["maxcpus=number", "maxcpusDesc"],
  ["nohz_full=cpurange", "nohzFullDesc"],
  ["irqaffinity=cpurange", "irqaffinityDesc"],
  ["processor.max_cstate=1", "maxCstate1Desc"],
  ["idle=poll", "idlePollDesc"],
  ["nmi_watchdog=0", "nmiWatchdog0Desc"],
  ["audit=0", "audit0Desc"],
  ["sysrq_always_enabled", "sysrqDesc"],
];
const proxyFields = [
  "http_proxy",
  "https_proxy",
  "ftp_proxy",
  "socks_proxy",
  "no_proxy",
];
const proxyTargetList = ["apt", "docker", "pip", "npm", "git"];

const I18N = {
  "zh-CN": {
    appTitle: "高级设置",
    refresh: "刷新",
    save: "保存",
    saving: "保存中...",
    loading: "正在加载...",
    saved: "已保存",
    about: "关于",
    close: "关闭",
    cancel: "取消",
    confirm: "确定",
    aboutDeclaration:
      "本项目由社区维护，免费开源，仅用于学习与交流，请遵守所在地法律法规与平台服务条款。",
    communitySupport: "社区支持",
    sponsorSupport: "赞助支持",
    join: "点击加入",
    bootSettings: "启动设置",
    powerSettings: "电源设置",
    sshSettings: "SSH 设置",
    cpuSettings: "CPU 设置",
    cpuExtra: "其他项",
    cpuList: "CPU 列表",
    cpuName: "名称",
    cpuDriver: "驱动",
    currentFreq: "当前频率",
    epp: "能效偏好 (EPP)",
    boost: "CPU 加速 (Boost)",
    no_turbo: "禁用 Turbo Boost",
    amd_pstate_prefcore: "AMD 首选核心",
    displaySettings: "屏幕设置",
    displayConnector: "接口",
    displayStatus: "状态",
    displayConnected: "已连接",
    displayDisconnected: "未连接",
    displayMonitor: "显示器",
    displayManufacturer: "制造商",
    displayResolution: "分辨率",
    displayCurrentResolution: "当前分辨率",
    displayNativeResolution: "原生分辨率",
    displayRefreshRate: "刷新率",
    displaySize: "尺寸",
    displayModes: "支持模式",
    displayDpms: "电源管理",
    displayEnabled: "已启用",
    displayDisabled: "已禁用",
    displayForcedOff: "已关闭",
    displayPowerOn: "开启",
    displayPowerOff: "关闭",
    displayPowerOffConfirm:
      "确定要关闭此屏幕吗？关闭后可能需要物理操作或重新连接来恢复。",
    displayPowerOnConfirm: "确定要开启此屏幕吗？",
    dnsSettings: "DNS 设置",
    networkSettings: "网络设置",
    proxySettings: "代理设置",
    identitySettings: "设备标识",
    deviceSettings: "设备信息",
    portSettings: "端口信息",
    applyGrub: "更新 grub 配置",
    restartLogind: "重启 logind 服务",
    restartSsh: "重启 SSH 服务",
    restartIdentity: "重启系统信息服务",
    rootPasswordBlock: "root 密码",
    rootPassword: "root 新密码",
    rootPasswordConfirm: "确认 root 密码",
    passwordMismatch: "两次输入的 root 密码不一致",
    minFreq: "最小频率",
    maxFreq: "最大频率",
    governor: "CPU 策略",
    current: "当前",
    available: "可用",
    enabled: "启用",
    disguise: "伪装",
    disabled: "禁用",
    deviceId: "设备 ID",
    original: "原始",
    mac: "MAC 地址",
    wol: "Wake-on-LAN",
    wolStatus: "WOL 状态",
    mode: "模式",
    notAvailable: "不可用",
    speed: "速率",
    duplex: "双工",
    autoneg: "自动协商",
    mtu: "MTU",
    keep: "保持不变",
    GRUB_TIMEOUT: "启动菜单等待时间",
    GRUB_CMDLINE_LINUX_DEFAULT: "默认内核参数",
    GRUB_CMDLINE_LINUX: "额外内核参数",
    GRUB_DEFAULT: "默认启动项",
    GRUB_DISABLE_OS_PROBER: "检测其他系统",
    commonKernelParams: "常用内核参数",
    paramName: "参数",
    paramDesc: "说明",
    quietDesc: "抑制内核启动时的文本输出，仅显示关键错误",
    splashDesc: "显示启动画面的图形进度条（需配合 plymouth）",
    nomodesetDesc: "禁止内核在启动早期加载图形驱动，使用 VESA 模式",
    consoleTtySDesc:
      "将内核控制台输出重定向到串口（ttyS0），波特率 115200，常用于无头服务器和 IPMI",
    netIfnames0Desc: "禁用可预测网络接口命名，恢复 eth0/eth1 传统命名方式",
    panic5Desc: "内核恐慌后 5 秒自动重启，提高系统可用性",
    nowatchdogDesc: "禁用看门狗定时器，减少中断开销",
    pcieAspmOffDesc: "禁用 PCIe 链路电源管理（ASPM），可解决某些设备兼容性问题",
    blacklistDesc: "将指定模块加入黑名单，阻止内核自动加载（如 pcspkr 蜂鸣器）",
    iommuPtDesc: "启用 IOMMU 直通模式，提升设备直通性能（需配合 VT-d/AMD-Vi）",
    intelIommuDesc: "启用 Intel IOMMU（VT-d）支持，用于 PCIe 设备直通",
    amdIommuDesc: "启用 AMD IOMMU（AMD-Vi）支持，用于 PCIe 设备直通",
    intremapOffDesc: "禁用中断重映射，解决某些硬件上中断分配异常问题",
    amdIommuIntrLegacyDesc: "AMD IOMMU 使用传统中断模式，兼容旧硬件直通",
    nox2apicDesc: "禁用 x2APIC，回退到 xAPIC 模式，解决某些平台中断问题",
    intelPstateDisableDesc:
      "禁用 Intel P-State 驱动，改用 acpi-cpufreq 频率管理",
    amdPstateDisableDesc: "禁用 AMD P-State 驱动，改用 acpi-cpufreq 频率管理",
    splitLockDetectOffDesc:
      "禁用拆分锁检测，避免跨缓存行原子操作触发 #AC 异常降频",
    hugepagesDesc: "预分配指定数量的 2MB 大页内存，用于数据库或虚拟化优化",
    thpNeverDesc: "禁用透明大页，避免内存分配延迟（适用于数据库等场景）",
    mitigationsOffDesc:
      "关闭 CPU 安全缓解措施（如 Spectre/Meltdown），提升性能但降低安全性",
    nosmpDesc: "禁用多核处理器，仅使用单核运行（调试用）",
    maxcpusDesc: "限制系统最多使用的 CPU 核心数（如 maxcpus=4）",
    nohzFullDesc: "启用无滴答内核模式，减少时钟中断（如 nohz_full=1-3）",
    irqaffinityDesc: "将硬件中断绑定到指定 CPU 核心（如 irqaffinity=0）",
    maxCstate1Desc: "限制 CPU 最低进入 C1 空闲状态，减少唤醒延迟",
    idlePollDesc: "使用轮询空闲循环代替 CPU 睡眠，最低延迟但功耗最高",
    nmiWatchdog0Desc: "禁用 NMI 看门狗定时器，减少中断开销",
    audit0Desc: "禁用审计子系统，减少系统调用开销",
    sysrqDesc: "始终启用 Magic SysRq 键，用于紧急系统恢复",
    HandlePowerKey: "按下电源键",
    HandlePowerKeyLongPress: "长按电源键",
    HandleRebootKey: "按下重启键",
    HandleRebootKeyLongPress: "长按重启键",
    HandleSuspendKey: "按下睡眠键",
    HandleSuspendKeyLongPress: "长按睡眠键",
    HandleHibernateKey: "按下休眠键",
    HandleHibernateKeyLongPress: "长按休眠键",
    HandleLidSwitch: "合上盖子",
    HandleLidSwitchExternalPower: "接通电源时合盖",
    HandleLidSwitchDocked: "外接显示器/扩展坞时合盖",
    PermitRootLogin: "允许 root 登录",
    PasswordAuthentication: "允许密码登录",
    PubkeyAuthentication: "允许密钥登录",
    PermitEmptyPasswords: "允许空密码",
    PermitTTY: "允许 TTY 分配",
    X11Forwarding: "允许 X11 转发",
    AllowTcpForwarding: "允许 TCP 转发",
    AllowAgentForwarding: "允许 Agent 转发",
    GatewayPorts: "允许远程网关端口",
    http_proxy: "HTTP 代理",
    https_proxy: "HTTPS 代理",
    ftp_proxy: "FTP 代理",
    socks_proxy: "SOCKS 代理",
    no_proxy: "不走代理的地址",
    proxyTargets: "代理应用",
    aptTarget: "APT 包管理器",
    dockerTarget: "Docker 守护进程",
    pipTarget: "Python pip",
    npmTarget: "Node.js npm",
    gitTarget: "Git",
    min_freq: "最小频率",
    max_freq: "最大频率",
    device_id: "设备 ID",
    poweroff: "关机",
    reboot: "重启",
    suspend: "睡眠",
    hibernate: "休眠",
    ignore: "忽略",
    lock: "锁定",
    yes: "是",
    no: "否",
    "prohibit-password": "禁止密码",
    "without-password": "仅密钥",
    clientspecified: "客户端指定",
    full: "全双工",
    half: "半双工",
    on: "开启",
    off: "关闭",
    d: "d 禁用",
    g: "g 魔术包",
    p: "p PHY活动",
    u: "u 单播包",
    b: "b 广播包",
    m: "m 组播包",
    pciDevices: "PCI 设备",
    usbDevices: "USB 设备",
    tcpPorts: "TCP 端口",
    udpPorts: "UDP 端口",
    slot: "插槽",
    class: "类型",
    description: "描述",
    bus: "总线",
    device: "设备",
    id: "ID",
    deviceId: "设备 ID",
    driver: "驱动",
    proto: "协议",
    localAddress: "本地地址",
    port: "端口",
    processName: "进程名",
    processPid: "PID",
    modules: "内核模块",
    state: "状态",
    listen: "监听",
    unconn: "未连接",
    noData: "暂无数据",
    bridgeSettings: "桥接设置",
    bridgeName: "桥接名称",
    bridgeType: "桥接类型",
    bridgeTypeLinux: "Linux 桥接",
    bridgeTypeOvs: "OVS 桥接",
    ipType: "IP 方式",
    ipAddress: "IP 地址",
    ipPrefixlen: "前缀长度",
    ipGateway: "网关",
    ipDns: "DNS",
    ipMtu: "MTU",
    ipDhcp: "DHCP",
    ipStatic: "静态",
    ipNone: "未配置",
    ipEdit: "编辑",
    ipv4Address: "IPv4 地址",
    ipv4Prefixlen: "IPv4 前缀",
    ipv4Gateway: "IPv4 网关",
    ipv4Dns: "IPv4 DNS",
    ipv6Address: "IPv6 地址",
    ipv6Prefixlen: "IPv6 前缀",
    ipv6Gateway: "IPv6 网关",
    ipv6Dns: "IPv6 DNS",
    ip4Type: "IPv4 方式",
    ip6Type: "IPv6 方式",
    stp: "STP",
    forwardDelay: "转发延迟",
    helloTime: "Hello 时间",
    maxAge: "最大老化",
    members: "从属接口",
    actions: "操作",
    createBridge: "创建桥接",
    deleteBridge: "删除",
    addMember: "添加接口",
    removeMember: "移除",
    toggleStp: "切换 STP",
    enabled: "启用",
    disabled: "禁用",
    forwarding: "转发",
    learning: "学习",
    listening: "监听",
    blocking: "阻塞",
    selectInterface: "选择接口",
    confirmDeleteBridge: "确定要删除桥接",
    confirmRemoveMember: "确定要从桥接中移除接口",
    searchPort: "搜索端口/地址/进程",
    noMatch: "无匹配结果",
    processSettings: "进程管理",
    searchProcess: "搜索进程...",
    processUser: "用户",
    processCpu: "CPU%",
    processMem: "内存%",
    processStat: "状态",
    processTime: "运行时间",
    processCmd: "命令",
    killProcess: "结束进程",
    processTerm: "结束进程 (-TERM)",
    processKill: "强制杀死 (-KILL)",
    processStop: "停止进程 (-STOP)",
    processCont: "恢复进程 (-CONT)",
    processConfirmTERM: "确定要向进程 {pid} 发送 SIGTERM 信号？",
    processConfirmKILL: "确定要向进程 {pid} 发送 SIGKILL 信号？",
    processConfirmSTOP: "确定要向进程 {pid} 发送 SIGSTOP 信号？",
    processConfirmCONT: "确定要向进程 {pid} 发送 SIGCONT 信号？",
    processSignalSent: "信号已发送",
    serviceSettings: "服务管理",
    searchService: "搜索服务...",
    serviceName: "服务",
    serviceDescription: "描述",
    serviceActive: "状态",
    serviceSub: "子状态",
    serviceEnabled: "开机自启",
    serviceStart: "启动服务",
    serviceStop: "停止服务",
    serviceRestart: "重启服务",
    serviceReload: "重载服务",
    serviceEnable: "启用开机自启",
    serviceDisable: "禁用开机自启",
    serviceConfirmStart: "确定要启动服务 {name}？",
    serviceConfirmStop: "确定要停止服务 {name}？",
    serviceConfirmRestart: "确定要重启服务 {name}？",
    serviceConfirmReload: "确定要重载服务 {name}？",
    serviceConfirmEnable: "确定要启用服务 {name} 的开机自启？",
    serviceConfirmDisable: "确定要禁用服务 {name} 的开机自启？",
    serviceActionDone: "操作已执行",
    serviceStateRunning: "运行中",
    serviceStateStopped: "已停止",
    serviceStateFailed: "失败",
    serviceStateStarting: "启动中",
    serviceStateStopping: "停止中",
    serviceStateReloading: "重载中",
    serviceEnabledYes: "已启用",
    serviceEnabledNo: "已禁用",
    serviceEnabledStatic: "静态",
    serviceEnabledMasked: "屏蔽",
    serviceEnabledUnknown: "未知",
    serviceStatus: "查看状态",
    serviceCat: "查看配置",
    serviceEdit: "编辑配置",
    serviceStatusTitle: "服务状态 - {name}",
    serviceCatTitle: "服务配置 - {name}",
    serviceEditTitle: "编辑配置 - {name}",
    serviceEditHint: "保存后将写入 {path} 并执行 daemon-reload",
    serviceEditSaved: "配置已保存并已重载 systemd",
    serviceEditClearConfirm: "内容为空，将删除该服务的 override 配置，继续？",
    serviceEditorLabel: "服务配置编辑框",
    bootAnalyze: "启动分析",
    bootAnalyzeTitle: "启动时间线分析",
    analyzeTime: "总时间",
    analyzeBlame: "耗时排行",
    analyzeCritical: "关键链",
    analyzeBlameSummary: "共 {count} 个服务，累计 {total}s",
    analyzeColUnit: "服务",
    analyzeColTime: "耗时",
    analyzeColShare: "占比",
    zoomReset: "重置",
    killed: "进程已终止",
    tcpSettings: "拥塞控制",
    congestionControl: "拥塞控制算法",
    fastopen: "TCP Fast Open",
    syncookies: "SYN Cookies 防洪",
    twReuse: "TIME_WAIT 端口复用",
    finTimeout: "FIN_WAIT 超时 (秒)",
    keepaliveTime: "Keepalive 间隔 (秒)",
    sack: "选择性确认 (SACK)",
    timestamps: "TCP 时间戳",
    windowScaling: "窗口缩放",
    mtuProbing: "MTU 路径探测",
    nicSettings: "网卡设置",
    diagSettings: "网络诊断",
    diagTarget: "目标地址",
    diagCount: "次数",
    diagDnsServer: "DNS 服务器",
    diagDnsServerPlaceholder: "8.8.8.8 (可选)",
    diagOutput: "输出",
    diagRun: "执行",
    diagRunning: "执行中...",
    diagPlaceholder: "选择工具并执行诊断",
    diagNoTarget: "请输入目标地址",
    diagStop: "终止",
    diagStopped: "已终止",
  },
  "en-US": {
    appTitle: "Advanced Settings",
    refresh: "Refresh",
    save: "Save",
    saving: "Saving...",
    loading: "Loading...",
    saved: "Saved",
    about: "About",
    close: "Close",
    cancel: "Cancel",
    confirm: "OK",
    aboutDeclaration:
      "This community-maintained open source project is free and open source, intended only for learning and communication. Please follow local laws and platform terms.",
    communitySupport: "Community Support",
    sponsorSupport: "Sponsor Support",
    join: "Join",
    bootSettings: "Boot Settings",
    powerSettings: "Power Settings",
    sshSettings: "SSH Settings",
    cpuSettings: "CPU Settings",
    cpuExtra: "Other Options",
    cpuList: "CPU List",
    cpuName: "Name",
    cpuDriver: "Driver",
    currentFreq: "Current Freq",
    epp: "Energy Perf Preference (EPP)",
    boost: "CPU Boost",
    no_turbo: "Disable Turbo Boost",
    amd_pstate_prefcore: "AMD Preferred Core",
    displaySettings: "Display Settings",
    displayConnector: "Connector",
    displayStatus: "Status",
    displayConnected: "Connected",
    displayDisconnected: "Disconnected",
    displayMonitor: "Monitor",
    displayManufacturer: "Manufacturer",
    displayResolution: "Resolution",
    displayCurrentResolution: "Current Resolution",
    displayNativeResolution: "Native Resolution",
    displayRefreshRate: "Refresh Rate",
    displaySize: "Size",
    displayModes: "Supported Modes",
    displayDpms: "Power Management",
    displayEnabled: "Enabled",
    displayDisabled: "Disabled",
    displayForcedOff: "Turned Off",
    displayPowerOn: "Turn On",
    displayPowerOff: "Turn Off",
    displayPowerOffConfirm:
      "Are you sure you want to turn off this display? You may need physical access or reconnection to restore it.",
    displayPowerOnConfirm: "Are you sure you want to turn on this display?",
    dnsSettings: "DNS Settings",
    networkSettings: "Network Settings",
    proxySettings: "Proxy Settings",
    identitySettings: "Device Identity",
    deviceSettings: "Device Info",
    portSettings: "Port Info",
    applyGrub: "Update grub config",
    restartLogind: "Restart logind service",
    restartSsh: "Restart SSH service",
    restartIdentity: "Restart system info services",
    rootPasswordBlock: "Root password",
    rootPassword: "New root password",
    rootPasswordConfirm: "Confirm root password",
    passwordMismatch: "The root passwords do not match",
    minFreq: "Min frequency",
    maxFreq: "Max frequency",
    governor: "CPU governor",
    current: "Current",
    available: "Available",
    enabled: "Enabled",
    disguise: "Disguise",
    disabled: "Disabled",
    deviceId: "Device ID",
    original: "Original",
    mac: "MAC address",
    wol: "Wake-on-LAN",
    wolStatus: "WOL status",
    mode: "Mode",
    notAvailable: "Not available",
    speed: "Speed",
    duplex: "Duplex",
    autoneg: "Autoneg",
    mtu: "MTU",
    keep: "Keep",
    GRUB_TIMEOUT: "Boot menu timeout",
    GRUB_CMDLINE_LINUX_DEFAULT: "Default kernel parameters",
    GRUB_CMDLINE_LINUX: "Extra kernel parameters",
    GRUB_DEFAULT: "Default boot entry",
    GRUB_DISABLE_OS_PROBER: "Detect other systems",
    commonKernelParams: "Common Kernel Parameters",
    paramName: "Parameter",
    paramDesc: "Description",
    quietDesc: "Suppress kernel boot text output, show only critical errors",
    splashDesc: "Show graphical boot splash progress bar (requires plymouth)",
    nomodesetDesc:
      "Prevent kernel from loading graphics drivers early, use VESA mode",
    consoleTtySDesc:
      "Redirect kernel console output to serial port (ttyS0) at 115200 baud, ideal for headless servers and IPMI",
    netIfnames0Desc:
      "Disable predictable network interface naming, revert to traditional eth0/eth1 naming",
    panic5Desc:
      "Auto-reboot 5 seconds after kernel panic, improving system availability",
    nowatchdogDesc: "Disable watchdog timers to reduce interrupt overhead",
    pcieAspmOffDesc:
      "Disable PCIe link power management (ASPM), may fix device compatibility",
    blacklistDesc:
      "Blacklist specified module to prevent auto-loading (e.g. pcspkr beeper)",
    iommuPtDesc:
      "Enable IOMMU pass-through mode for better device passthrough performance",
    intelIommuDesc:
      "Enable Intel IOMMU (VT-d) support for PCIe device passthrough",
    amdIommuDesc:
      "Enable AMD IOMMU (AMD-Vi) support for PCIe device passthrough",
    intremapOffDesc:
      "Disable interrupt remapping, fix interrupt delivery issues on certain hardware",
    amdIommuIntrLegacyDesc:
      "AMD IOMMU legacy interrupt mode for old hardware passthrough compatibility",
    nox2apicDesc:
      "Disable x2APIC, fall back to xAPIC mode, fix interrupt issues on some platforms",
    intelPstateDisableDesc:
      "Disable Intel P-State driver, fall back to acpi-cpufreq frequency management",
    amdPstateDisableDesc:
      "Disable AMD P-State driver, fall back to acpi-cpufreq frequency management",
    splitLockDetectOffDesc:
      "Disable split lock detection, avoid #AC exception frequency throttling",
    hugepagesDesc:
      "Pre-allocate specified number of 2MB huge pages for DB/virtualization",
    thpNeverDesc:
      "Disable transparent huge pages to avoid allocation latency (for databases)",
    mitigationsOffDesc:
      "Disable CPU security mitigations (Spectre/Meltdown), faster but less secure",
    nosmpDesc: "Disable multi-core, run on single core only (for debugging)",
    maxcpusDesc: "Limit max number of CPU cores to use (e.g. maxcpus=4)",
    nohzFullDesc:
      "Enable tickless kernel mode to reduce timer interrupts (e.g. nohz_full=1-3)",
    irqaffinityDesc:
      "Bind hardware interrupts to specified CPU cores (e.g. irqaffinity=0)",
    maxCstate1Desc: "Limit CPU to C1 idle state at most, reduce wakeup latency",
    idlePollDesc:
      "Use polling idle loop instead of CPU sleep, lowest latency but highest power",
    nmiWatchdog0Desc: "Disable NMI watchdog timer to reduce interrupt overhead",
    audit0Desc: "Disable audit subsystem to reduce syscall overhead",
    sysrqDesc: "Always enable Magic SysRq key for emergency system recovery",
    HandlePowerKey: "Press power key",
    HandlePowerKeyLongPress: "Long-press power key",
    HandleRebootKey: "Press reboot key",
    HandleRebootKeyLongPress: "Long-press reboot key",
    HandleSuspendKey: "Press suspend key",
    HandleSuspendKeyLongPress: "Long-press suspend key",
    HandleHibernateKey: "Press hibernate key",
    HandleHibernateKeyLongPress: "Long-press hibernate key",
    HandleLidSwitch: "Close lid",
    HandleLidSwitchExternalPower: "Close lid on external power",
    HandleLidSwitchDocked: "Close lid while docked",
    PermitRootLogin: "Allow root login",
    PasswordAuthentication: "Allow password login",
    PubkeyAuthentication: "Allow key login",
    PermitEmptyPasswords: "Allow empty passwords",
    PermitTTY: "Allow TTY allocation",
    X11Forwarding: "Allow X11 forwarding",
    AllowTcpForwarding: "Allow TCP forwarding",
    AllowAgentForwarding: "Allow agent forwarding",
    GatewayPorts: "Allow remote gateway ports",
    http_proxy: "HTTP proxy",
    https_proxy: "HTTPS proxy",
    ftp_proxy: "FTP proxy",
    socks_proxy: "SOCKS proxy",
    no_proxy: "Proxy bypass list",
    proxyTargets: "Apply Proxy To",
    aptTarget: "APT Package Manager",
    dockerTarget: "Docker Daemon",
    pipTarget: "Python pip",
    npmTarget: "Node.js npm",
    gitTarget: "Git",
    min_freq: "Min frequency",
    max_freq: "Max frequency",
    device_id: "Device ID",
    poweroff: "Power off",
    reboot: "Reboot",
    suspend: "Suspend",
    hibernate: "Hibernate",
    ignore: "Ignore",
    lock: "Lock",
    yes: "Yes",
    no: "No",
    "prohibit-password": "Forbid passwords",
    "without-password": "Keys only",
    clientspecified: "Client specified",
    full: "Full",
    half: "Half",
    on: "On",
    off: "Off",
    d: "d Disabled",
    g: "g Magic packet",
    p: "p PHY activity",
    u: "u Unicast",
    b: "b Broadcast",
    m: "m Multicast",
    pciDevices: "PCI Devices",
    usbDevices: "USB Devices",
    tcpPorts: "TCP Ports",
    udpPorts: "UDP Ports",
    slot: "Slot",
    class: "Class",
    description: "Description",
    bus: "Bus",
    device: "Device",
    id: "ID",
    deviceId: "Device ID",
    driver: "Driver",
    proto: "Protocol",
    localAddress: "Local Address",
    port: "Port",
    processName: "Process",
    processPid: "PID",
    modules: "Kernel modules",
    state: "State",
    listen: "Listen",
    unconn: "Unconnected",
    noData: "No data",
    bridgeSettings: "Bridge Settings",
    bridgeName: "Bridge Name",
    bridgeType: "Bridge Type",
    bridgeTypeLinux: "Linux Bridge",
    bridgeTypeOvs: "OVS Bridge",
    ipType: "IP Type",
    ipAddress: "IP Address",
    ipPrefixlen: "Prefix Length",
    ipGateway: "Gateway",
    ipDns: "DNS",
    ipMtu: "MTU",
    ipDhcp: "DHCP",
    ipStatic: "Static",
    ipNone: "Unconfigured",
    ipEdit: "Edit",
    ipv4Address: "IPv4 Address",
    ipv4Prefixlen: "IPv4 Prefix",
    ipv4Gateway: "IPv4 Gateway",
    ipv4Dns: "IPv4 DNS",
    ipv6Address: "IPv6 Address",
    ipv6Prefixlen: "IPv6 Prefix",
    ipv6Gateway: "IPv6 Gateway",
    ipv6Dns: "IPv6 DNS",
    ip4Type: "IPv4 Type",
    ip6Type: "IPv6 Type",
    stp: "STP",
    forwardDelay: "Forward Delay",
    helloTime: "Hello Time",
    maxAge: "Max Age",
    members: "Members",
    actions: "Actions",
    createBridge: "Create Bridge",
    deleteBridge: "Delete",
    addMember: "Add Interface",
    removeMember: "Remove",
    toggleStp: "Toggle STP",
    enabled: "Enabled",
    disabled: "Disabled",
    forwarding: "Forwarding",
    learning: "Learning",
    listening: "Listening",
    blocking: "Blocking",
    selectInterface: "Select Interface",
    confirmDeleteBridge: "Are you sure you want to delete bridge",
    confirmRemoveMember:
      "Are you sure you want to remove interface from bridge",
    searchPort: "Search port/address/process",
    noMatch: "No match",
    processSettings: "Process Management",
    searchPTerm: "Terminate (-TERM)",
    processKill: "Force Kill (-KILL)",
    processStop: "Stop (-STOP)",
    processCont: "Continue (-CONT)",
    processConfirmTERM: "Send SIGTERM to process {pid}?",
    processConfirmKILL: "Send SIGKILL to process {pid}?",
    processConfirmSTOP: "Send SIGSTOP to process {pid}?",
    processConfirmCONT: "Send SIGCONT to process {pid}?",
    processSignalSent: "Signal sent",
    serviceSettings: "Service Management",
    searchService: "Search services...",
    serviceName: "Service",
    serviceDescription: "Description",
    serviceActive: "Active",
    serviceSub: "Sub",
    serviceEnabled: "Enabled",
    serviceStart: "Start Service",
    serviceStop: "Stop Service",
    serviceRestart: "Restart Service",
    serviceReload: "Reload Service",
    serviceEnable: "Enable Autostart",
    serviceDisable: "Disable Autostart",
    serviceConfirmStart: "Start service {name}?",
    serviceConfirmStop: "Stop service {name}?",
    serviceConfirmRestart: "Restart service {name}?",
    serviceConfirmReload: "Reload service {name}?",
    serviceConfirmEnable: "Enable autostart for service {name}?",
    serviceConfirmDisable: "Disable autostart for service {name}?",
    serviceActionDone: "Action executed",
    serviceStateRunning: "Running",
    serviceStateStopped: "Stopped",
    serviceStateFailed: "Failed",
    serviceStateStarting: "Starting",
    serviceStateStopping: "Stopping",
    serviceStateReloading: "Reloading",
    serviceEnabledYes: "Enabled",
    serviceEnabledNo: "Disabled",
    serviceEnabledStatic: "Static",
    serviceEnabledMasked: "Masked",
    serviceEnabledUnknown: "Unknown",
    serviceStatus: "View Status",
    serviceCat: "View Config",
    serviceEdit: "Edit Config",
    serviceStatusTitle: "Service Status - {name}",
    serviceCatTitle: "Service Config - {name}",
    serviceEditTitle: "Edit Config - {name}",
    serviceEditHint: "Saved to {path} and systemd daemon-reload is run",
    serviceEditSaved: "Config saved and systemd reloaded",
    serviceEditClearConfirm:
      "Content is empty. This will remove the override config for this service. Continue?",
    serviceEditorLabel: "Service config editor",
    bootAnalyze: "Boot Analysis",
    bootAnalyzeTitle: "Boot Timeline Analysis",
    analyzeTime: "Time",
    analyzeBlame: "Blame",
    analyzeCritical: "Critical Chain",
    analyzeBlameSummary: "{count} services, total {total}s",
    analyzeColUnit: "Unit",
    analyzeColTime: "Time",
    analyzeColShare: "Share",
    zoomReset: "Reset",
    processUser: "User",
    processCpu: "CPU%",
    processStat: "STAT",
    processMem: "Memory%",
    processTime: "Runtime",
    processCmd: "Command",
    killProcess: "Kill Process",
    killed: "Process killed",
    killed: "Process killed",
    tcpSettings: "Congestion Control",
    congestionControl: "Congestion Control Algorithm",
    fastopen: "TCP Fast Open",
    syncookies: "SYN Cookies (Flood Protection)",
    twReuse: "TIME_WAIT Port Reuse",
    finTimeout: "FIN_WAIT Timeout (sec)",
    keepaliveTime: "Keepalive Interval (sec)",
    sack: "Selective Ack (SACK)",
    timestamps: "TCP Timestamps",
    windowScaling: "Window Scaling",
    mtuProbing: "MTU Path Probing",
    nicSettings: "NIC Settings",
    diagSettings: "Network Diagnostics",
    diagTarget: "Target",
    diagCount: "Count",
    diagDnsServer: "DNS Server",
    diagDnsServerPlaceholder: "8.8.8.8 (optional)",
    diagOutput: "Output",
    diagRun: "Run",
    diagRunning: "Running...",
    diagPlaceholder: "Select a tool and run diagnostics",
    diagNoTarget: "Please enter a target address",
    diagStop: "Stop",
    diagStopped: "Stopped",
  },
};

const state = {
  active: "boot",
  data: {},
  language: "zh-CN",
  theme: "light",
  saving: false,
};

function safeDecode(value) {
  try {
    return decodeURIComponent(value || "");
  } catch (_error) {
    return value || "";
  }
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

function queryValue(name) {
  return new URLSearchParams(location.search).get(name) || "";
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
      window.parent.localStorage?.getItem(name) ||
      window.parent.sessionStorage?.getItem(name) ||
      ""
    );
  } catch (_error) {
    return "";
  }
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

function normalizeLanguage(value) {
  return safeDecode(value).replace("_", "-").toLowerCase().startsWith("zh")
    ? "zh-CN"
    : "en-US";
}

function normalizeTheme(value) {
  const theme = safeDecode(value).toLowerCase();
  if (theme.includes("dark") || theme === "night") return "dark";
  if (theme.includes("light") || theme === "day") return "light";
  if (theme === "10") return "light";
  if (theme === "20") return "dark";
  if (theme === "system" || theme === "auto" || theme === "os") {
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return "";
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
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function t(key, params) {
  let text =
    (I18N[state.language] || I18N["zh-CN"])[key] || I18N["zh-CN"][key] || key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.split(`{${k}}`).join(String(v));
    }
  }
  return text;
}

function applyPreferences({ rerender = false } = {}) {
  state.language = normalizeLanguage(
    cookieValue("language") ||
      queryValue("language") ||
      navigator.language ||
      "zh-CN",
  );
  state.theme = currentTheme();
  document.documentElement.lang = state.language;
  document.documentElement.dataset.theme = state.theme;
  document.body.dataset.theme = state.theme;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.title = t("appTitle");
  if (rerender) render();
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

function trunc(str, len) {
  str = String(str || "");
  return str.length > len ? str.slice(0, len) + "…" : str;
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
  if (!response.ok || !result.ok)
    throw new Error(result.message || `HTTP ${response.status}`);
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

function showConfirm(message) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirmModal");
    const msgEl = document.getElementById("confirmMessage");
    const okBtn = document.getElementById("confirmOk");
    const cancelBtn = document.getElementById("confirmCancel");
    msgEl.textContent = message;
    modal.classList.remove("hidden");
    const cleanup = (result) => {
      modal.classList.add("hidden");
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
      resolve(result);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
  });
}

function setSaving(saving) {
  state.saving = saving;
  const btn = document.getElementById("saveBtn");
  btn.disabled = saving;
  btn.textContent = saving ? t("saving") : t("save");
}

function fieldLabel(name) {
  return t(name);
}

function optionLabel(name, value) {
  if (name === "wol" && value) return wolStatusText(value);
  if (name === "mode" && value) return modeLabel(value);
  return value ? t(value) : `(${t("keep")})`;
}

function wolStatusText(value) {
  const text = String(value || "").trim();
  if (!text) return t("notAvailable");
  if (text === "d") return t("d");
  return text
    .split("")
    .map((item) => t(item))
    .join(", ");
}

function inputField(
  name,
  value = "",
  options = null,
  extra = "",
  multiline = false,
) {
  const label = fieldLabel(name);
  if (options) {
    return `<label class="field"><span title="${escapeHtml(name)}">${escapeHtml(label)}</span><select data-name="${escapeHtml(name)}" ${extra}>${options.map((item) => `<option value="${escapeHtml(item)}" ${String(value) === String(item) ? "selected" : ""}>${escapeHtml(optionLabel(name, item))}</option>`).join("")}</select></label>`;
  }
  if (multiline) {
    return `<label class="field wide"><span title="${escapeHtml(name)}">${escapeHtml(label)}</span><textarea data-name="${escapeHtml(name)}" spellcheck="false" ${extra}>${escapeHtml(value)}</textarea></label>`;
  }
  return `<label class="field"><span title="${escapeHtml(name)}">${escapeHtml(label)}</span><input data-name="${escapeHtml(name)}" value="${escapeHtml(value)}" spellcheck="false" ${extra}></label>`;
}

function wolField(value, options) {
  const selected = new Set(
    String(value || "")
      .split("")
      .filter(Boolean),
  );
  if (!selected.size) selected.add("d");
  if (selected.size > 1) selected.delete("d");
  return `
    <label class="field wide">
      <span title="wol">${escapeHtml(t("wol"))}</span>
      <input type="hidden" data-name="wol" value="${escapeHtml([...selected].join(""))}">
      <span class="choice-group" data-wol-group>
        ${options
          .map(
            (item) => `
          <label class="choice"><input type="checkbox" data-wol-option value="${escapeHtml(item)}" ${selected.has(item) ? "checked" : ""}><span>${escapeHtml(wolStatusText(item))}</span></label>
        `,
          )
          .join("")}
      </span>
    </label>
  `;
}

function collect(container) {
  const out = {};
  container.querySelectorAll("[data-name]").forEach((node) => {
    out[node.dataset.name] =
      node.type === "checkbox" ? (node.checked ? "on" : "") : node.value;
  });
  return out;
}

function fallbackLinkModes(currentSpeed) {
  const current = Number(currentSpeed) || 1000;
  const speeds = [10, 100, 1000, 2500, 5000, 10000].filter(
    (speed) => speed <= current,
  );
  if (!speeds.includes(current)) speeds.push(current);
  return speeds
    .sort((a, b) => a - b)
    .flatMap((speed) =>
      speed <= 100
        ? [
            { speed: String(speed), duplex: "half" },
            { speed: String(speed), duplex: "full" },
          ]
        : [{ speed: String(speed), duplex: "full" }],
    );
}

function modeValue(speed, duplex) {
  return `${speed || ""}|${duplex || "full"}`;
}

function modeLabel(value) {
  const [speed, duplex] = String(value || "").split("|");
  return `${speed || "-"} / ${optionLabel("duplex", duplex || "full")}`;
}

function syncNetworkAutonegFields(
  container = document.getElementById("networkList"),
) {
  container.querySelectorAll("[data-iface]").forEach((item) => {
    const autoneg = item.querySelector('[data-name="autoneg"]');
    const mode = item.querySelector('[data-name="mode"]');
    const enabled = autoneg?.value === "on";
    if (mode) mode.disabled = enabled;
  });
}

function renderNav() {
  document.getElementById("navList").innerHTML = sections
    .map(
      ([id, label]) => `
    <button class="nav-item ${state.active === id ? "active" : ""}" type="button" data-section="${id}"><span class="nav-icon" aria-hidden="true">${icons[id] || ""}</span><span>${escapeHtml(t(label))}</span></button>
  `,
    )
    .join("");
  document.getElementById("pageTitle").textContent = t(
    sections.find(([id]) => id === state.active)?.[1] || "appTitle",
  );
}

function renderBoot() {
  const parsed = state.data.boot?.parsed || {};
  document.getElementById("bootFields").innerHTML = bootFields
    .map((key) =>
      inputField(
        key,
        parsed[key] || "",
        null,
        "",
        key === "GRUB_CMDLINE_LINUX",
      ),
    )
    .join("");
  const tbody = document.getElementById("kernelParamBody");
  if (tbody) {
    tbody.innerHTML = kernelParams
      .map(
        ([param, descKey]) =>
          `<tr><td class="mono">${escapeHtml(param)}</td><td>${escapeHtml(t(descKey))}</td></tr>`,
      )
      .join("");
  }
}

function renderPower() {
  const parsed = state.data.power?.parsed || {};
  const options = [
    "",
    "poweroff",
    "reboot",
    "suspend",
    "hibernate",
    "ignore",
    "lock",
  ];
  document.getElementById("powerFields").innerHTML = powerFields
    .map((key) => inputField(key, parsed[key] || "", options))
    .join("");
}

function renderSsh() {
  const parsed = state.data.ssh?.parsed || {};
  document.getElementById("sshFields").innerHTML = sshFields
    .map((key) => {
      return inputField(key, parsed[key] || "", sshOptions[key]);
    })
    .join("");
  document.getElementById("rootPassword").value = "";
  document.getElementById("rootPasswordConfirm").value = "";
}

function renderCpu() {
  const policies = state.data.cpu?.policies || [];
  const cpus = state.data.cpu?.cpus || [];
  const extra = state.data.cpu?.extra || {};
  const governors = [
    ...new Set(
      policies
        .flatMap((item) => item.available_governors || [])
        .concat(cpus.flatMap((item) => item.available_governors || [])),
    ),
  ];
  const eppOptions = [
    ...new Set(
      policies
        .flatMap((item) => item.available_epp || [])
        .concat(cpus.flatMap((item) => item.available_epp || [])),
    ),
  ];
  const current = policies[0] || cpus[0] || {};
  document.getElementById("cpuFields").innerHTML =
    inputField("min_freq", current.min_freq || "") +
    inputField("max_freq", current.max_freq || "") +
    inputField(
      "governor",
      current.governor || "",
      governors.length ? governors : null,
    ) +
    (eppOptions.length ? inputField("epp", current.epp || "", eppOptions) : "");
  const extraHtml = [];
  if (extra.boost !== undefined) {
    extraHtml.push(inputField("boost", String(extra.boost), ["1", "0"]));
  }
  if (extra.no_turbo !== undefined) {
    extraHtml.push(inputField("no_turbo", String(extra.no_turbo), ["1", "0"]));
  }
  if (extra.amd_pstate_prefcore !== undefined) {
    extraHtml.push(
      inputField("amd_pstate_prefcore", String(extra.amd_pstate_prefcore), [
        "enabled",
        "disabled",
      ]),
    );
  }
  const extraSection = document.getElementById("cpuExtraSection");
  const extraFields = document.getElementById("cpuExtraFields");
  if (extraHtml.length) {
    extraFields.innerHTML = extraHtml.join("");
    extraSection.style.display = "";
  } else {
    extraSection.style.display = "none";
  }
  const items = policies.length ? policies : cpus;
  const tbody = document.querySelector("#cpuTable tbody");
  if (!tbody) return;
  const fmtFreq = (v) => {
    if (!v || v === "-") return "-";
    const n = Number(v);
    if (isNaN(n)) return escapeHtml(v);
    return (n / 1000000).toFixed(2) + " GHz";
  };
  tbody.innerHTML = items.length
    ? items
        .map((item) => {
          const driver = item.scaling_driver || "-";
          const gov = item.governor || "-";
          const epp = item.epp || "-";
          const boost =
            item.boost !== undefined
              ? item.boost === "1"
                ? `<span class="badge-driver">${t("enabled")}</span>`
                : `<span class="subtle">${t("disabled")}</span>`
              : "-";
          return `<tr>
      <td class="mono">${escapeHtml(item.name)}</td>
      <td class="mono">${escapeHtml(driver)}</td>
      <td class="mono">${fmtFreq(item.cur_freq)}</td>
      <td class="mono">${fmtFreq(item.min_freq)}</td>
      <td class="mono">${fmtFreq(item.max_freq)}</td>
      <td>${escapeHtml(gov)}</td>
      <td>${escapeHtml(epp)}</td>
      <td>${boost}</td>
    </tr>`;
        })
        .join("")
    : `<tr><td colspan="8" class="empty-cell">${escapeHtml(t("noData"))}</td></tr>`;
}

function renderDisplay() {
  const displays = state.data.display?.displays || [];
  const tbody = document.querySelector("#displayTable tbody");
  if (!tbody) return;
  tbody.innerHTML = displays.length
    ? displays
        .map((item) => {
          const isConnected = item.status === "connected";
          const isForcedOff = item.forced_off === true;
          const statusBadge = isConnected
            ? `<span class="badge-driver">${escapeHtml(t("displayConnected"))}</span>`
            : `<span class="subtle">${escapeHtml(t("displayDisconnected"))}</span>`;
          const monitorName = item.monitor_name || item.manufacturer || "-";
          const manufacturer = item.manufacturer || "-";
          const currentRes = item.current_resolution || "-";
          const nativeRes = item.native_resolution || "-";
          const refreshRate = item.current_rate
            ? `${item.current_rate} Hz`
            : item.vfreq_range || "-";
          const size = item.size_inch
            ? `${item.size_inch}" (${item.size_cm} cm)`
            : item.size_cm
              ? `${item.size_cm} cm`
              : "-";
          const dpms =
            item.dpms ||
            (item.drm_enabled === "enabled"
              ? "On"
              : item.drm_enabled === "disabled"
                ? "Off"
                : "-");
          const dpmsBadge = isForcedOff
            ? `<span class="subtle">${escapeHtml(t("displayDisabled"))}</span>`
            : dpms === "On"
              ? `<span class="badge-driver">${escapeHtml(t("displayEnabled"))}</span>`
              : dpms === "Off"
                ? `<span class="subtle">${escapeHtml(t("displayDisabled"))}</span>`
                : escapeHtml(dpms);
          const powerBtn = !isConnected
            ? `<span class="subtle">-</span>`
            : isForcedOff
              ? `<button type="button" class="ghost-btn display-power-btn" data-display-name="${escapeHtml(item.name)}" data-display-action="on">${escapeHtml(t("displayPowerOn"))}</button>`
              : `<button type="button" class="ghost-btn display-power-btn" data-display-name="${escapeHtml(item.name)}" data-display-action="off">${escapeHtml(t("displayPowerOff"))}</button>`;
          return `<tr>
      <td class="mono">${escapeHtml(item.connector)}</td>
      <td>${statusBadge}</td>
      <td>${escapeHtml(monitorName)}</td>
      <td class="mono">${escapeHtml(manufacturer)}</td>
      <td class="mono">${escapeHtml(currentRes)}</td>
      <td class="mono">${escapeHtml(nativeRes)}</td>
      <td class="mono">${escapeHtml(refreshRate)}</td>
      <td class="mono">${escapeHtml(size)}</td>
      <td>${dpmsBadge}</td>
      <td>${powerBtn}</td>
    </tr>`;
        })
        .join("")
    : `<tr><td colspan="10" class="empty-cell">${escapeHtml(t("noData"))}</td></tr>`;
}

function renderDns() {
  document.getElementById("resolvContent").value = state.data.dns?.resolv || "";
  document.getElementById("hostsContent").value = state.data.dns?.hosts || "";
}

function renderNetwork() {
  const saved = state.data.network?.saved || {};
  const list = state.data.network?.interfaces || [];
  document.getElementById("networkList").innerHTML = list
    .map((item) => {
      const cfg = saved[item.name] || {};
      const wolModes = [
        ...new Set(
          [
            "d",
            ...String(item.supported_wol || "").split(""),
            ...String(item.wol || "").split(""),
          ].filter(Boolean),
        ),
      ];
      const wolOptions = wolModes.length
        ? wolModes
        : ["d", "g", "p", "u", "b", "m"];
      const modes = (item.supported_link_modes || []).length
        ? item.supported_link_modes
        : fallbackLinkModes(item.speed);
      const modeOptions = [
        ...new Set(
          modes
            .map((mode) => modeValue(mode.speed, mode.duplex))
            .concat(
              item.speed
                ? [modeValue(item.speed, item.duplex || cfg.duplex || "full")]
                : [],
            )
            .filter(Boolean),
        ),
      ].sort(
        (a, b) =>
          Number(a.split("|")[0]) - Number(b.split("|")[0]) ||
          a.localeCompare(b),
      );
      const currentMode = modeValue(
        item.speed || cfg.speed || modeOptions[0]?.split("|")[0] || "",
        item.duplex || cfg.duplex || "full",
      );
      return `
      <div class="data-item" data-iface="${escapeHtml(item.name)}" data-link-modes="${escapeHtml(JSON.stringify(modes))}">
        <div class="data-title"><span>${escapeHtml(item.name)}</span><span>${escapeHtml(item.operstate || "")}</span></div>
        <div class="data-meta">MAC ${escapeHtml(item.mac || "-")} / ${t("wolStatus")} ${escapeHtml(wolStatusText(item.wol))} / ${t("mode")} ${escapeHtml(modeLabel(currentMode))}</div>
        <div class="grid">
          ${inputField("mac", item.mac || cfg.mac || "")}
          ${wolField(cfg.wol || item.wol || "d", wolOptions)}
          ${inputField("autoneg", item.autoneg || cfg.autoneg || "off", ["off", "on"])}
          ${inputField("mode", currentMode, modeOptions.length ? modeOptions : [currentMode])}
        </div>
      </div>
    `;
    })
    .join("");
  syncNetworkAutonegFields();
  renderTcp();
  renderBridges();
}

function renderTcp() {
  const tcp = state.data.network?.tcp || {};
  const saved = state.data.network?.saved || {};
  const savedTcp = saved.tcp || {};
  const availableCc = tcp.available_congestion_control || [];
  const ccOptions = availableCc.length
    ? availableCc
    : [tcp.congestion_control || "cubic"];
  const mtuProbingOptions = ["0", "1", "2"];
  const container = document.getElementById("tcpFields");
  if (!container) return;
  container.innerHTML = [
    inputField(
      "congestion_control",
      savedTcp.congestion_control || tcp.congestion_control || "cubic",
      ccOptions,
    ),
    inputField("fastopen", savedTcp.fastopen || tcp.fastopen || "1"),
    inputField("syncookies", savedTcp.syncookies || tcp.syncookies || "1", [
      "0",
      "1",
    ]),
    inputField("tw_reuse", savedTcp.tw_reuse || tcp.tw_reuse || "2", [
      "0",
      "1",
      "2",
    ]),
    inputField("fin_timeout", savedTcp.fin_timeout || tcp.fin_timeout || "60"),
    inputField(
      "keepalive_time",
      savedTcp.keepalive_time || tcp.keepalive_time || "7200",
    ),
    inputField("sack", savedTcp.sack || tcp.sack || "1", ["0", "1"]),
    inputField("timestamps", savedTcp.timestamps || tcp.timestamps || "1", [
      "0",
      "1",
    ]),
    inputField(
      "window_scaling",
      savedTcp.window_scaling || tcp.window_scaling || "1",
      ["0", "1"],
    ),
    inputField(
      "mtu_probing",
      savedTcp.mtu_probing || tcp.mtu_probing || "0",
      mtuProbingOptions,
    ),
  ].join("");
}

function bridgeMemberStateLabel(state) {
  const map = {
    forwarding: "forwarding",
    learning: "learning",
    listening: "listening",
    blocking: "blocking",
    disabled: "disabled",
  };
  return t(map[state] || state || "disabled");
}

function renderBridges() {
  const bridges = state.data.network?.bridges || [];
  const savedBridges = state.data.network?.saved_bridges || {};
  const availableIfaces = state.data.network?.available_ifaces || [];
  const bridgeNames = new Set(bridges.map((b) => b.name));
  const memberNames = new Set(
    bridges.flatMap((b) => b.members.map((m) => m.name)),
  );
  const freeIfaces = availableIfaces.filter(
    (n) => !bridgeNames.has(n) && !memberNames.has(n) && n !== "lo",
  );
  const container = document.getElementById("bridgeList");
  if (!container) return;
  container.innerHTML = bridges.length
    ? bridges
        .map((bridge) => {
          const saved = savedBridges[bridge.name] || {};
          const ip4Type =
            saved.ip4_type ||
            (saved.ip_type === "dhcp"
              ? saved.ipv4_enabled !== false
                ? "dhcp"
                : ""
              : saved.ip_type === "static"
                ? saved.ipv4_enabled !== false
                  ? "static"
                  : ""
                : "");
          const ip6Type =
            saved.ip6_type ||
            (saved.ip_type === "dhcp"
              ? saved.ipv6_enabled
                ? "dhcp"
                : ""
              : saved.ip_type === "static"
                ? saved.ipv6_enabled
                  ? "static"
                  : ""
                : "");
          const ipTypeLabel = (v) =>
            v === "dhcp"
              ? t("ipDhcp")
              : v === "static"
                ? t("ipStatic")
                : t("ipNone");
          const ip4Badge = ip4Type
            ? `<span class="badge-driver">IPv4 ${escapeHtml(ipTypeLabel(ip4Type))}</span>`
            : `<span class="subtle">IPv4 ${escapeHtml(ipTypeLabel(ip4Type))}</span>`;
          const ip6Badge = ip6Type
            ? `<span class="badge-driver">IPv6 ${escapeHtml(ipTypeLabel(ip6Type))}</span>`
            : `<span class="subtle">IPv6 ${escapeHtml(ipTypeLabel(ip6Type))}</span>`;
          const bridgeType = bridge.type || saved.bridge_type || "linux";
          const bridgeTypeLabel =
            bridgeType === "ovs" ? t("bridgeTypeOvs") : t("bridgeTypeLinux");
          const bridgeTypeBadge = `<span class="badge-driver">${escapeHtml(bridgeTypeLabel)}</span>`;
          const allAddrs = bridge.addrs || [];
          const ipv4Addrs = allAddrs.filter((a) => a.family === "inet");
          const ipv6Addrs = allAddrs.filter((a) => a.family === "inet6");
          const ipv4Display = ipv4Addrs.length
            ? ipv4Addrs.map((a) => `${a.address}/${a.prefixlen}`).join(", ")
            : "";
          const ipv6Display = ipv6Addrs.length
            ? ipv6Addrs.map((a) => `${a.address}/${a.prefixlen}`).join(", ")
            : "";
          const addrParts = [];
          if (ipv4Display) addrParts.push(`IPv4: ${ipv4Display}`);
          if (ipv6Display) addrParts.push(`IPv6: ${ipv6Display}`);
          const addrDisplay = addrParts.length ? addrParts.join(" / ") : "";
          const mtu = saved.ip_mtu || "";
          const dns = saved.ip_dns || "";
          const row2 = [bridgeTypeBadge, ip4Badge, ip6Badge];
          if (mtu) row2.push(`<span>MTU ${escapeHtml(mtu)}</span>`);
          if (dns) row2.push(`<span>DNS ${escapeHtml(dns)}</span>`);
          const row3 = addrDisplay
            ? [`<span class="mono">${escapeHtml(addrDisplay)}</span>`]
            : [];
          const row4 = [
            `<span>STP ${bridge.stp ? t("enabled") : t("disabled")}</span>`,
            `<span>${escapeHtml(t("forwardDelay"))} ${escapeHtml(bridge.forward_delay || "-")}</span>`,
            `<span>${escapeHtml(t("helloTime"))} ${escapeHtml(bridge.hello_time || "-")}</span>`,
            `<span>${escapeHtml(t("maxAge"))} ${escapeHtml(bridge.max_age || "-")}</span>`,
          ];
          const memberHtml = bridge.members.length
            ? bridge.members
                .map(
                  (m) =>
                    `<span class="badge-member">${escapeHtml(m.name)}<span class="member-state">${escapeHtml(bridgeMemberStateLabel(m.state))}</span><button type="button" class="member-remove-btn" data-bridge="${escapeHtml(bridge.name)}" data-member="${escapeHtml(m.name)}" title="${escapeHtml(t("removeMember"))}">×</button></span>`,
                )
                .join("")
            : `<span class="subtle">${escapeHtml(t("noData"))}</span>`;
          const ifaceOptions = freeIfaces.length
            ? freeIfaces
                .map(
                  (n) =>
                    `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`,
                )
                .join("")
            : "";
          const addMemberHtml = freeIfaces.length
            ? `<select class="bridge-add-select" data-bridge="${escapeHtml(bridge.name)}"><option value="">${escapeHtml(t("selectInterface"))}</option>${ifaceOptions}</select>`
            : "";
          const savedData = encodeURIComponent(JSON.stringify(saved));
          return `<div class="bridge-card" data-bridge-card="${escapeHtml(bridge.name)}">
      <div class="bridge-card-head">
        <span class="bridge-card-name">${escapeHtml(bridge.name)}</span>
        <div class="bridge-card-actions">
          <button type="button" class="ghost-btn bridge-edit-btn" data-bridge="${escapeHtml(bridge.name)}" data-bridge-type="${escapeHtml(bridgeType)}" data-saved="${savedData}">${escapeHtml(t("ipEdit"))}</button>
          <button type="button" class="ghost-btn bridge-delete-btn" data-bridge="${escapeHtml(bridge.name)}" data-bridge-type="${escapeHtml(bridgeType)}">${escapeHtml(t("deleteBridge"))}</button>
        </div>
      </div>
      ${row2.length ? `<div class="bridge-card-row">${row2.join("")}</div>` : ""}
      ${row3.length ? `<div class="bridge-card-row">${row3.join("")}</div>` : ""}
      <div class="bridge-card-row">${row4.join("")}</div>
      <div class="bridge-card-row bridge-card-members">
        ${memberHtml} ${addMemberHtml}
      </div>
    </div>`;
        })
        .join("")
    : `<div class="subtle-center">${escapeHtml(t("noData"))}</div>`;
}

function renderProxy() {
  const values = state.data.proxy?.values || {};
  const targets = state.data.proxy?.targets || {};
  document.getElementById("proxyFields").innerHTML = proxyFields
    .map((key) => inputField(key, values[key] || ""))
    .join("");
  document.getElementById("proxyTargets").innerHTML = proxyTargetList
    .map(
      (key) => `
    <label class="check"><input type="checkbox" data-proxy-target value="${escapeHtml(key)}" ${targets[key] ? "checked" : ""}><span>${escapeHtml(t(key + "Target"))}</span></label>
  `,
    )
    .join("");
}

function renderIdentity() {
  const identity = state.data.identity || {};
  document.getElementById("identityFields").innerHTML = `
    <div class="backup-tag"><span>${escapeHtml(t("original"))}</span><strong>${escapeHtml(identity.backup || "-")}</strong></div>
    <div class="identity-row">
      <label class="field identity-id"><span>${escapeHtml(t("device_id"))}</span><input data-name="device_id" value="${escapeHtml(identity.device_id || "")}" spellcheck="false"></label>
      <label class="switch-field"><span>${escapeHtml(t("disguise"))}</span><input data-name="enabled" type="checkbox" ${identity.backup_exists ? "checked" : ""}><i aria-hidden="true"></i></label>
    </div>
  `;
}

function renderDevice() {
  const device = state.data.device || {};
  const pci = device.pci || [];
  const usb = device.usb || [];
  const pciTbody = document.querySelector("#pciTable tbody");
  const usbTbody = document.querySelector("#usbTable tbody");
  if (!pciTbody || !usbTbody) return;
  pciTbody.innerHTML = pci.length
    ? pci
        .map(
          (item) => `<tr>
      <td class="mono">${escapeHtml(item.slot || "-")}</td>
      <td>${item.class_id ? `<span class="mono class-id">[${escapeHtml(item.class_id)}]</span> ` : ""}${escapeHtml(item.class || "-")}</td>
      <td>${escapeHtml(item.description || "-")}</td>
      <td class="mono">${escapeHtml(item.device_id || "-")}</td>
      <td>${item.driver ? `<span class="badge-driver">${escapeHtml(item.driver)}</span>` : "-"}</td>
    </tr>`,
        )
        .join("")
    : `<tr><td colspan="5" class="empty-cell">${escapeHtml(t("noData"))}</td></tr>`;
  usbTbody.innerHTML = usb.length
    ? usb
        .map(
          (item) => `<tr>
      <td class="mono">${escapeHtml(item.bus || "-")}</td>
      <td class="mono">${escapeHtml(item.device || "-")}</td>
      <td>${escapeHtml(item.description || "-")}</td>
      <td class="mono">${escapeHtml(item.id || "-")}</td>
      <td>${item.driver ? `<span class="badge-driver">${escapeHtml(item.driver)}</span>` : "-"}</td>
    </tr>`,
        )
        .join("")
    : `<tr><td colspan="5" class="empty-cell">${escapeHtml(t("noData"))}</td></tr>`;
}

function filterPortEntry(item, keyword) {
  if (!keyword) return true;
  const kw = keyword.toLowerCase();
  return [
    item.local_address,
    item.port,
    item.process_name,
    item.process_pid,
  ].some((v) =>
    String(v || "")
      .toLowerCase()
      .includes(kw),
  );
}

function renderPortTable(entries, tbody, keyword) {
  if (!tbody) return;
  const filtered = keyword
    ? entries.filter((item) => filterPortEntry(item, keyword))
    : entries;
  tbody.innerHTML = filtered.length
    ? filtered
        .map(
          (item) => `<tr>
      <td class="mono">${escapeHtml(item.local_address || "-")}</td>
      <td class="mono">${escapeHtml(item.port || "-")}</td>
      <td>${escapeHtml(item.process_name || "-")}</td>
      <td class="mono">${escapeHtml(item.process_pid || "-")}</td>
    </tr>`,
        )
        .join("")
    : `<tr><td colspan="4" class="empty-cell">${escapeHtml(keyword ? t("noMatch") : t("noData"))}</td></tr>`;
}

function renderPort() {
  const port = state.data.port || {};
  const keyword = (
    document.getElementById("portSearchInput")?.value || ""
  ).trim();
  const tcp = (port.tcp || [])
    .slice()
    .sort((a, b) => (parseInt(a.port) || 0) - (parseInt(b.port) || 0));
  const udp = (port.udp || [])
    .slice()
    .sort((a, b) => (parseInt(a.port) || 0) - (parseInt(b.port) || 0));
  renderPortTable(tcp, document.querySelector("#tcpTable tbody"), keyword);
  renderPortTable(udp, document.querySelector("#udpTable tbody"), keyword);
}

function renderProcess() {
  const processes = state.data.processes || [];
  const keyword = (document.getElementById("processSearchInput")?.value || "")
    .trim()
    .toLowerCase();
  const tbody = document.querySelector("#processTable tbody");
  if (!tbody) return;

  let filtered = processes;
  if (keyword) {
    try {
      const regex = new RegExp(keyword, "i");
      filtered = processes.filter((p) => {
        return (
          regex.test(p.user) || regex.test(p.cmd) || regex.test(String(p.pid))
        );
      });
    } catch (e) {
      filtered = processes.filter((p) => {
        const s = `${p.user} ${p.cmd} ${p.pid}`.toLowerCase();
        return s.includes(keyword);
      });
    }
  }

  tbody.innerHTML = filtered.length
    ? filtered
        .map(
          (p) => `<tr data-pid="${p.pid}">
            <td>${escapeHtml(p.user)}</td>
            <td>${escapeHtml(p.pid)}</td>
            <td>${escapeHtml(p.cpu)}</td>
            <td>${escapeHtml(p.mem)}</td>
            <td class="monospace">${escapeHtml(p.stat || "-")}</td>
            <td>${escapeHtml(p.time || "-")}</td>
            <td class="muted" title="${escapeHtml(p.cmd)}">${escapeHtml(trunc(p.cmd, 60))}</td>
          </tr>`,
        )
        .join("")
    : `<tr><td colspan="7" class="empty-cell">${escapeHtml(keyword ? t("noMatch") : t("noData"))}</td></tr>`;
}

function renderServices() {
  const services = state.data.services || [];
  const keyword = (document.getElementById("serviceSearchInput")?.value || "")
    .trim()
    .toLowerCase();
  const tbody = document.querySelector("#serviceTable tbody");
  if (!tbody) return;

  let filtered = services;
  if (keyword) {
    filtered = services.filter((s) =>
      `${s.name} ${s.description} ${s.active} ${s.enabled}`
        .toLowerCase()
        .includes(keyword),
    );
  }

  tbody.innerHTML = filtered.length
    ? filtered
        .map(
          (s) => `<tr data-service="${escapeHtml(s.name)}">
            <td class="mono">${escapeHtml(s.name)}</td>
            <td class="muted">${escapeHtml(trunc(s.description || "-", 60))}</td>
            <td><span class="badge-service ${escapeHtml(s.active)}">${escapeHtml(serviceStateText(s.active))}</span></td>
            <td>${escapeHtml(s.sub || "-")}</td>
            <td>${escapeHtml(serviceEnabledText(s.enabled))}</td>
          </tr>`,
        )
        .join("")
    : `<tr><td colspan="5" class="empty-cell">${escapeHtml(keyword ? t("noMatch") : t("noData"))}</td></tr>`;
}

function serviceStateText(active) {
  const map = {
    active: "serviceStateRunning",
    inactive: "serviceStateStopped",
    failed: "serviceStateFailed",
    activating: "serviceStateStarting",
    deactivating: "serviceStateStopping",
    reloading: "serviceStateReloading",
  };
  return t(map[active] || "serviceStateStopped");
}

function serviceEnabledText(enabled) {
  const map = {
    enabled: "serviceEnabledYes",
    disabled: "serviceEnabledNo",
    static: "serviceEnabledStatic",
    masked: "serviceEnabledMasked",
  };
  return t(map[enabled] || "serviceEnabledUnknown");
}

const PROCESS_MENU = [
  ["term", "processTerm"],
  ["kill", "processKill"],
  ["stop", "processStop"],
  ["cont", "processCont"],
];

const SERVICE_MENU = [
  ["start", "serviceStart"],
  ["stop", "serviceStop"],
  ["restart", "serviceRestart"],
  ["reload", "serviceReload"],
  ["enable", "serviceEnable"],
  ["disable", "serviceDisable"],
  ["status", "serviceStatus"],
  ["cat", "serviceCat"],
  ["edit", "serviceEdit"],
];

let _contextType = null; // "process" | "service"
let _contextTarget = null; // pid 或服务名
let _contextAction = null;

function showContextMenu(e, type, target) {
  e.preventDefault();
  _contextType = type;
  _contextTarget = target;
  _contextAction = null;
  const menu = document.getElementById("contextMenu");
  const items = type === "service" ? SERVICE_MENU : PROCESS_MENU;
  menu.innerHTML = items
    .map(
      ([action, key]) =>
        `<div class="context-menu-item" data-action="${action}"><span>${escapeHtml(t(key))}</span></div>`,
    )
    .join("");
  const x = Math.min(e.clientX, window.innerWidth - 160);
  const y = Math.min(
    e.clientY,
    window.innerHeight - (type === "service" ? 210 : 140),
  );
  menu.style.left = x + "px";
  menu.style.top = y + "px";
  menu.classList.remove("hidden");
}

function hideContextMenu() {
  document.getElementById("contextMenu").classList.add("hidden");
  _contextType = null;
  _contextTarget = null;
  _contextAction = null;
}

document.getElementById("contextMenu").addEventListener("click", (e) => {
  const item = e.target.closest(".context-menu-item");
  if (!item) return;
  const action = item.dataset.action;
  if (action) {
    handleMenuAction(action);
  }
});

document.addEventListener("contextmenu", (e) => {
  const processRow = e.target.closest("#processTable tbody tr");
  if (processRow) {
    showContextMenu(e, "process", processRow.dataset.pid);
    return;
  }
  const serviceRow = e.target.closest("#serviceTable tbody tr");
  if (serviceRow) {
    showContextMenu(e, "service", serviceRow.dataset.service);
    return;
  }
  hideContextMenu();
});

document.addEventListener("click", hideContextMenu);
document.addEventListener("scroll", hideContextMenu, true);

function handleMenuAction(action) {
  const type = _contextType;
  const target = _contextTarget;
  hideContextMenu();
  if (type === "service") {
    handleServiceAction(action, target);
  } else if (target !== null && target !== undefined) {
    handleProcessAction(action, target);
  }
}

function handleProcessAction(action, pid) {
  const msg = t(`processConfirm${action.toUpperCase()}`).replace("{pid}", pid);
  showConfirm(msg).then((ok) => {
    if (!ok) return;
    api("signalProcess", { pid, signal: action })
      .then(() => {
        showToast(t("processSignalSent"));
        loadProcesses();
      })
      .catch((err) => showToast(err.message || t("processSignalSent"), true));
  });
}

function handleServiceAction(action, name) {
  if (action === "status") {
    openServiceStatus(name);
    return;
  }
  if (action === "cat") {
    openServiceCat(name);
    return;
  }
  if (action === "edit") {
    openServiceEdit(name);
    return;
  }
  const cap = action.charAt(0).toUpperCase() + action.slice(1);
  const msg = t(`serviceConfirm${cap}`).replace("{name}", name);
  showConfirm(msg).then((ok) => {
    if (!ok) return;
    api("serviceAction", { name, op: action })
      .then(() => {
        showToast(t("serviceActionDone"));
        loadServices();
      })
      .catch((err) => showToast(err.message || t("serviceActionDone"), true));
  });
}

async function openServiceStatus(name) {
  try {
    const data = await api("serviceStatus", { name });
    showServiceModal(
      t("serviceStatusTitle").replace("{name}", name),
      data.content || "",
      false,
      "",
    );
  } catch (err) {
    showToast(err.message, true);
  }
}

async function openServiceCat(name) {
  try {
    const data = await api("serviceCat", { name });
    showServiceModal(
      t("serviceCatTitle").replace("{name}", name),
      data.content || "",
      false,
      "",
    );
  } catch (err) {
    showToast(err.message, true);
  }
}

async function openServiceEdit(name) {
  try {
    const data = await api("serviceEditRead", { name });
    const hint = t("serviceEditHint").replace("{path}", data.path || "");
    showServiceModal(
      t("serviceEditTitle").replace("{name}", name),
      data.content || "",
      true,
      name,
      hint,
    );
  } catch (err) {
    showToast(err.message, true);
  }
}

function showServiceModal(title, content, editable, name, hint) {
  const modal = document.getElementById("serviceModal");
  modal.classList.remove("analyze-modal");
  document.getElementById("serviceModalTitle").textContent = title;
  const pre = document.getElementById("serviceModalContent");
  const editor = document.getElementById("serviceModalEditor");
  const saveBtn = document.getElementById("serviceModalSave");
  const hintEl = document.getElementById("serviceModalHint");
  const svgEl = document.getElementById("serviceModalSvg");
  const zoomEl = document.getElementById("analyzeZoom");
  const dataEl = document.getElementById("serviceModalData");
  svgEl.classList.add("hidden");
  svgEl.innerHTML = "";
  zoomEl.classList.add("hidden");
  dataEl.classList.add("hidden");
  pre.textContent = content;
  pre.classList.toggle("hidden", editable);
  editor.value = content;
  editor.classList.toggle("hidden", !editable);
  saveBtn.classList.toggle("hidden", !editable);
  saveBtn.dataset.name = name || "";
  hintEl.textContent = hint || "";
  hintEl.classList.toggle("hidden", !hint);
  modal.classList.remove("hidden");
}

let _svgZoom = 1;
let _svgBaseW = 0;
let _svgBaseH = 0;

function showAnalyzeModal(svg, data) {
  const modal = document.getElementById("serviceModal");
  modal.classList.add("analyze-modal");
  document.getElementById("serviceModalTitle").textContent =
    t("bootAnalyzeTitle");
  const pre = document.getElementById("serviceModalContent");
  const editor = document.getElementById("serviceModalEditor");
  const saveBtn = document.getElementById("serviceModalSave");
  const hintEl = document.getElementById("serviceModalHint");
  pre.classList.add("hidden");
  editor.classList.add("hidden");
  saveBtn.classList.add("hidden");
  hintEl.classList.add("hidden");
  const svgEl = document.getElementById("serviceModalSvg");
  svgEl.innerHTML = svg || "";
  svgEl.classList.toggle("hidden", !svg);
  const zoomEl = document.getElementById("analyzeZoom");
  zoomEl.classList.toggle("hidden", !svg);
  if (svg) setupSvgZoom(svgEl);
  const dataEl = document.getElementById("serviceModalData");
  document.getElementById("analyzeTime").textContent =
    (data && data.time) || t("noData");
  document.getElementById("analyzeBlame").innerHTML = renderAnalyzeBlame(
    (data && data.blame) || "",
  );
  document.getElementById("analyzeCritical").textContent =
    (data && data.critical) || t("noData");
  dataEl.classList.remove("hidden");
  dataEl.querySelectorAll(".analyze-tab").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === "time");
  });
  dataEl.querySelectorAll(".analyze-panel").forEach((p) => {
    p.classList.toggle("hidden", p.dataset.tab !== "time");
  });
  modal.classList.remove("hidden");
}

function setupSvgZoom(svgEl) {
  const svg = svgEl.querySelector("svg");
  if (!svg) return;
  const w = parseFloat(svg.getAttribute("width")) || 0;
  const h = parseFloat(svg.getAttribute("height")) || 0;
  if (!w || !h) return;
  _svgBaseW = w;
  _svgBaseH = h;
  _svgZoom = 1;
  if (!svg.getAttribute("viewBox")) {
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  }
  applySvgZoom();
}

function applySvgZoom() {
  const svg = document.querySelector("#serviceModalSvg svg");
  if (!svg || !_svgBaseW || !_svgBaseH) return;
  svg.setAttribute("width", `${_svgBaseW * _svgZoom}px`);
  svg.setAttribute("height", `${_svgBaseH * _svgZoom}px`);
  document.getElementById("zoomLevel").textContent =
    `${Math.round(_svgZoom * 100)}%`;
}

function renderAnalyzeBlame(text) {
  const rows = [];
  for (const line of String(text || "").split("\n")) {
    const m = line.match(/^\s*(\d+(?:\.\d+)?)s\s+(.+)$/);
    if (m) rows.push({ time: parseFloat(m[1]), unit: m[2].trim() });
  }
  if (!rows.length) {
    return `<div class="muted">${escapeHtml(text || t("noData"))}</div>`;
  }
  const total = rows.reduce((a, r) => a + r.time, 0);
  const max = Math.max(...rows.map((r) => r.time));
  return `
    <div class="analyze-blame-summary">${t("analyzeBlameSummary", {
      count: rows.length,
      total: total.toFixed(2),
    })}</div>
    <div class="analyze-blame-scroll">
    <table class="analyze-blame-table">
      <thead><tr>
        <th>${escapeHtml(t("analyzeColUnit"))}</th>
        <th>${escapeHtml(t("analyzeColTime"))}</th>
        <th>${escapeHtml(t("analyzeColShare"))}</th>
      </tr></thead>
      <tbody>
        ${rows
          .map(
            (r) => `<tr>
          <td class="mono">${escapeHtml(r.unit)}</td>
          <td class="mono">${r.time.toFixed(3)}s</td>
          <td class="share-cell">
            <div class="bar-wrap"><div class="bar" style="width:${((r.time / max) * 100).toFixed(1)}%"></div></div>
            <span class="bar-label">${((r.time / total) * 100).toFixed(1)}%</span>
          </td>
        </tr>`,
          )
          .join("")}
      </tbody>
    </table>
    </div>`;
}

function closeServiceModal() {
  const modal = document.getElementById("serviceModal");
  modal.classList.remove("analyze-modal");
  modal.classList.add("hidden");
}

async function loadProcesses() {
  return api("readProcesses").then((data) => {
    state.data.processes = data.processes || [];
    renderProcess();
  });
}

async function loadServices() {
  return api("readServices").then((data) => {
    state.data.services = data.services || [];
    renderServices();
  });
}

let diagActive = "ping";
let diagRunning = false;
let diagAbortController = null;

function isIpv6(s) {
  return /^[0-9a-fA-F:]+$/.test(s) && s.includes(":");
}

function renderDiag() {
  document.querySelectorAll("#diagTabs .diag-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.diag === diagActive);
  });
  const forms = {
    ping: "diagPingForm",
    traceroute: "diagTracerouteForm",
    nslookup: "diagNslookupForm",
    arp: "diagArpForm",
  };
  Object.entries(forms).forEach(([key, id]) => {
    document.getElementById(id).classList.toggle("hidden", key !== diagActive);
  });
}

function switchDiag(tool) {
  diagActive = tool;
  renderDiag();
}

async function runDiag() {
  if (diagRunning) return;
  const output = document.getElementById("diagOutput");
  let tool, data;

  if (diagActive === "ping") {
    const target = (
      document.getElementById("diagPingTarget").value || ""
    ).trim();
    if (!target) {
      showToast(t("diagNoTarget"), true);
      return;
    }
    const rawCount = parseInt(document.getElementById("diagPingCount").value);
    const count = Number.isNaN(rawCount) ? 4 : Math.min(9999, rawCount);
    const ipv6 = isIpv6(target);
    tool = "ping";
    data = { target, count, ipv6 };
  } else if (diagActive === "traceroute") {
    const target = (
      document.getElementById("diagTracerouteTarget").value || ""
    ).trim();
    if (!target) {
      showToast(t("diagNoTarget"), true);
      return;
    }
    const ipv6 = isIpv6(target);
    tool = "traceroute";
    data = { target, ipv6 };
  } else if (diagActive === "nslookup") {
    const target = (
      document.getElementById("diagNslookupTarget").value || ""
    ).trim();
    if (!target) {
      showToast(t("diagNoTarget"), true);
      return;
    }
    const server = (
      document.getElementById("diagNslookupServer").value || ""
    ).trim();
    const ipv6 = isIpv6(target);
    tool = "nslookup";
    data = { target, server: server || undefined, ipv6 };
  } else if (diagActive === "arp") {
    tool = "arp";
    data = { ipv6: false };
  }

  diagRunning = true;
  const btn = document.getElementById("diagRunBtn");
  const stopBtn = document.getElementById("diagStopBtn");
  btn.classList.add("hidden");
  stopBtn.classList.remove("hidden");
  output.value = "";
  output.classList.remove("diag-error");

  diagAbortController = new AbortController();

  try {
    const response = await fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      credentials: "include",
      body: JSON.stringify({ action: "diagStream", tool, ...data }),
      signal: diagAbortController.signal,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${response.status}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        let eventType = "data";
        let eventData = "";
        for (const line of part.split("\n")) {
          if (line.startsWith("event: ")) eventType = line.slice(7).trim();
          else if (line.startsWith("data: ")) eventData = line.slice(6);
        }
        if (!eventData) continue;
        let parsed;
        try {
          parsed = JSON.parse(eventData);
        } catch {
          continue;
        }
        if (eventType === "data") {
          output.value += (output.value ? "\n" : "") + (parsed.line || "");
          output.scrollTop = output.scrollHeight;
        } else if (eventType === "done") {
          if (parsed.rc !== 0) output.classList.add("diag-error");
        } else if (eventType === "error") {
          output.value +=
            (output.value ? "\n" : "") + (parsed.message || "error");
          output.classList.add("diag-error");
        }
      }
    }
  } catch (e) {
    if (e.name === "AbortError") {
      output.value += (output.value ? "\n" : "") + t("diagStopped");
    } else {
      output.value = e.message;
      output.classList.add("diag-error");
    }
  } finally {
    diagRunning = false;
    diagAbortController = null;
    btn.classList.remove("hidden");
    stopBtn.classList.add("hidden");
  }
}

async function stopDiag() {
  if (!diagRunning) return;
  try {
    await fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      credentials: "include",
      body: JSON.stringify({ action: "diagStop" }),
    });
  } catch {}
  if (diagAbortController) {
    diagAbortController.abort();
  }
}

function renderPanels() {
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.panel !== state.active);
  });
  document
    .getElementById("saveBtn")
    .classList.toggle(
      "hidden",
      state.active === "identity" ||
        state.active === "device" ||
        state.active === "port" ||
        state.active === "process" ||
        state.active === "service" ||
        state.active === "display" ||
        state.active === "diag",
    );
}

function render() {
  renderNav();
  renderPanels();
  renderBoot();
  renderPower();
  renderSsh();
  renderCpu();
  renderDisplay();
  renderDns();
  renderNetwork();
  renderProxy();
  renderIdentity();
  renderDevice();
  renderProcess();
  renderServices();
  renderPort();
  renderDiag();
}

async function loadData() {
  document.getElementById("emptyState").classList.remove("hidden");
  document.getElementById("editor").classList.add("hidden");
  const data = await api("read");
  state.data = data;
  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("editor").classList.remove("hidden");
  render();
  loadServices().catch((error) => showToast(error.message, true));
}

async function saveActive() {
  if (state.saving) return;
  setSaving(true);
  try {
    let data;
    if (state.active === "boot") {
      data = await api("saveBoot", {
        changes: collect(document.getElementById("bootFields")),
        apply: document.getElementById("bootApply").checked,
      });
    } else if (state.active === "power") {
      data = await api("savePower", {
        changes: collect(document.getElementById("powerFields")),
        apply: document.getElementById("powerApply").checked,
      });
    } else if (state.active === "ssh") {
      const password = document.getElementById("rootPassword").value;
      const passwordConfirm = document.getElementById(
        "rootPasswordConfirm",
      ).value;
      if (password || passwordConfirm) {
        if (password !== passwordConfirm)
          throw new Error(t("passwordMismatch"));
      }
      data = await api("saveSsh", {
        changes: collect(document.getElementById("sshFields")),
        password,
        apply: document.getElementById("sshApply").checked,
      });
    } else if (state.active === "cpu") {
      data = await api("saveCpu", {
        settings: {
          ...collect(document.getElementById("cpuFields")),
          ...collect(document.getElementById("cpuExtraFields")),
        },
      });
    } else if (state.active === "dns") {
      data = await api("saveDns", {
        resolv: document.getElementById("resolvContent").value,
        hosts: document.getElementById("hostsContent").value,
      });
    } else if (state.active === "network") {
      const interfaces = [
        ...document.querySelectorAll("#networkList [data-iface]"),
      ].map((item) => {
        const values = collect(item);
        delete values.mtu;
        if (values.autoneg === "on") {
          delete values.mode;
        } else {
          const [speed, duplex] = String(values.mode || "").split("|");
          values.autoneg = "off";
          values.speed = speed;
          values.duplex = duplex || "full";
          delete values.mode;
        }
        return { name: item.dataset.iface, ...values };
      });
      data = await api("saveNetwork", {
        interfaces,
        tcp: collect(document.getElementById("tcpFields")),
      });
    } else if (state.active === "proxy") {
      const proxyTargets = {};
      document.querySelectorAll("[data-proxy-target]").forEach((el) => {
        proxyTargets[el.value] = el.checked;
      });
      data = await api("saveProxy", {
        proxy: collect(document.getElementById("proxyFields")),
        targets: proxyTargets,
      });
    } else if (state.active === "identity") {
      const values = collect(document.getElementById("identityFields"));
      data = await api("saveIdentity", {
        enabled: values.enabled === "on",
        device_id: values.device_id,
        apply: document.getElementById("identityApply").checked,
      });
    }
    state.data = { ...state.data, ...data };
    render();
    showToast(t("saved"));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setSaving(false);
  }
}

async function saveIdentityFromSwitch() {
  if (state.saving) return;
  setSaving(true);
  try {
    const values = collect(document.getElementById("identityFields"));
    const data = await api("saveIdentity", {
      enabled: values.enabled === "on",
      device_id: values.device_id,
      apply: document.getElementById("identityApply").checked,
    });
    state.data = { ...state.data, ...data };
    render();
    showToast(t("saved"));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setSaving(false);
  }
}

document.getElementById("navList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-section]");
  if (!button) return;
  state.active = button.dataset.section;
  renderNav();
  renderPanels();
});

document
  .getElementById("refreshBtn")
  .addEventListener("click", () =>
    loadData().catch((error) => showToast(error.message, true)),
  );
document
  .getElementById("saveBtn")
  .addEventListener("click", () =>
    saveActive().catch((error) => showToast(error.message, true)),
  );
document
  .getElementById("identityFields")
  .addEventListener("change", (event) => {
    if (event.target.dataset.name === "enabled")
      saveIdentityFromSwitch().catch((error) => showToast(error.message, true));
  });
document.getElementById("networkList").addEventListener("change", (event) => {
  const item = event.target.closest("[data-iface]");
  if (!item) return;
  if (event.target.dataset.wolOption !== undefined) {
    const checked = [...item.querySelectorAll("[data-wol-option]:checked")];
    if (event.target.value === "d" && event.target.checked) {
      item
        .querySelectorAll('[data-wol-option]:not([value="d"])')
        .forEach((node) => {
          node.checked = false;
        });
    } else if (event.target.value !== "d" && event.target.checked) {
      const disabled = item.querySelector('[data-wol-option][value="d"]');
      if (disabled) disabled.checked = false;
    }
    const selected = [...item.querySelectorAll("[data-wol-option]:checked")]
      .map((node) => node.value)
      .join("");
    const hidden = item.querySelector('[data-name="wol"]');
    if (hidden) hidden.value = selected || "d";
  } else if (event.target.dataset.name === "autoneg") {
    syncNetworkAutonegFields(item.parentElement);
  } else if (event.target.dataset.name === "mode") {
    const autoneg = item.querySelector('[data-name="autoneg"]');
    if (autoneg) autoneg.value = "off";
    syncNetworkAutonegFields(item.parentElement);
  }
});
document.getElementById("networkList").addEventListener("input", (event) => {
  const item = event.target.closest("[data-iface]");
  if (!item || event.target.dataset.name !== "mode") return;
  const autoneg = item.querySelector('[data-name="autoneg"]');
  if (autoneg) autoneg.value = "off";
  syncNetworkAutonegFields(item.parentElement);
});

document.getElementById("portSearchInput").addEventListener("input", () => {
  renderPort();
});
document.getElementById("processSearchInput").addEventListener("input", () => {
  renderProcess();
});
document.getElementById("serviceSearchInput").addEventListener("input", () => {
  renderServices();
});

document.getElementById("diagTabs").addEventListener("click", (event) => {
  const tab = event.target.closest("[data-diag]");
  if (tab) switchDiag(tab.dataset.diag);
});
document
  .getElementById("diagRunBtn")
  .addEventListener("click", () => runDiag());
document
  .getElementById("diagStopBtn")
  .addEventListener("click", () => stopDiag());

function showBridgeIpModal(name, saved, currentStp, bridgeType) {
  const modal = document.getElementById("confirmModal");
  const content =
    modal.querySelector(".confirm-content") ||
    modal.querySelector(".modal-content");
  const isConfirm = !!content;
  const origHtml = isConfirm ? content.innerHTML : "";
  const origStyle = content.getAttribute("style") || "";
  const curIp4Type =
    saved.ip4_type ||
    (saved.ip_type === "dhcp"
      ? saved.ipv4_enabled !== false
        ? "dhcp"
        : ""
      : saved.ip_type === "static"
        ? saved.ipv4_enabled !== false
          ? "static"
          : ""
        : "");
  const curIp6Type =
    saved.ip6_type ||
    (saved.ip_type === "dhcp"
      ? saved.ipv6_enabled
        ? "dhcp"
        : ""
      : saved.ip_type === "static"
        ? saved.ipv6_enabled
          ? "static"
          : ""
        : "");
  const ipTypeOpts = (cur) =>
    `<option value=""${!cur ? " selected" : ""}>${escapeHtml(t("ipNone"))}</option><option value="dhcp"${cur === "dhcp" ? " selected" : ""}>DHCP</option><option value="static"${cur === "static" ? " selected" : ""}>${escapeHtml(t("ipStatic"))}</option>`;
  content.setAttribute(
    "style",
    "width:min(680px,calc(100vw - 48px));max-height:88vh;overflow:auto;padding:20px;",
  );
  content.innerHTML = `
    <p class="modal-title">${escapeHtml(name)} - ${escapeHtml(t("ipEdit"))}</p>
    <div class="grid mb-16">
      <label class="field" id="bridgeModalMtuWrap"><span>${escapeHtml(t("ipMtu"))}</span><input id="bridgeModalMtu" type="text" value="${escapeHtml(saved.ip_mtu || "")}" placeholder="1500" spellcheck="false"></label>
      <label class="check check-end"><input id="bridgeModalStp" type="checkbox" ${currentStp ? "checked" : ""}><span>${escapeHtml(t("stp"))}</span></label>
    </div>
    <div class="mb-16">
      <p class="section-title">IPv4</p>
      <div class="grid mb-8">
        <label class="field"><span>${escapeHtml(t("ip4Type"))}</span><select id="bridgeModalIp4Type" class="ip-type-select">${ipTypeOpts(curIp4Type)}</select></label>
      </div>
      <div id="bridgeModalIpv4Static" class="${curIp4Type !== "static" ? "hidden" : ""}">
        <div class="grid mb-12">
          <label class="field"><span>${escapeHtml(t("ipv4Address"))}</span><input id="bridgeModalIpv4Addr" type="text" value="${escapeHtml(saved.ip_address || "")}" placeholder="192.168.1.100" spellcheck="false"></label>
          <label class="field"><span>${escapeHtml(t("ipv4Prefixlen"))}</span><input id="bridgeModalIpv4Prefix" type="text" value="${escapeHtml(saved.ip_prefixlen || "24")}" placeholder="24" spellcheck="false"></label>
          <label class="field"><span>${escapeHtml(t("ipv4Gateway"))}</span><input id="bridgeModalIpv4Gw" type="text" value="${escapeHtml(saved.ip_gateway || "")}" placeholder="192.168.1.1" spellcheck="false"></label>
          <label class="field"><span>${escapeHtml(t("ipv4Dns"))}</span><input id="bridgeModalIpv4Dns" type="text" value="${escapeHtml(saved.ip_dns || "")}" placeholder="8.8.8.8" spellcheck="false"></label>
        </div>
      </div>
    </div>
    <div class="mb-16">
      <p class="section-title">IPv6</p>
      <div class="grid mb-8">
        <label class="field"><span>${escapeHtml(t("ip6Type"))}</span><select id="bridgeModalIp6Type" class="ip-type-select">${ipTypeOpts(curIp6Type)}</select></label>
      </div>
      <div id="bridgeModalIpv6Static" class="${curIp6Type !== "static" ? "hidden" : ""}">
        <div class="grid mb-12">
          <label class="field"><span>${escapeHtml(t("ipv6Address"))}</span><input id="bridgeModalIpv6Addr" type="text" value="${escapeHtml(saved.ip6_address || "")}" placeholder="2001:db8::1" spellcheck="false"></label>
          <label class="field"><span>${escapeHtml(t("ipv6Prefixlen"))}</span><input id="bridgeModalIpv6Prefix" type="text" value="${escapeHtml(saved.ip6_prefixlen || "64")}" placeholder="64" spellcheck="false"></label>
          <label class="field"><span>${escapeHtml(t("ipv6Gateway"))}</span><input id="bridgeModalIpv6Gw" type="text" value="${escapeHtml(saved.ip6_gateway || "")}" placeholder="2001:db8::1" spellcheck="false"></label>
          <label class="field"><span>${escapeHtml(t("ipv6Dns"))}</span><input id="bridgeModalIpv6Dns" type="text" value="${escapeHtml(saved.ip6_dns || "")}" placeholder="2001:4860:4860::8888" spellcheck="false"></label>
        </div>
      </div>
    </div>
    <div class="confirm-actions">
      <button id="bridgeModalCancel" class="ghost-btn" type="button">${escapeHtml(t("cancel"))}</button>
      <button id="bridgeModalOk" class="primary-btn" type="button">${escapeHtml(t("confirm"))}</button>
    </div>
  `;
  modal.classList.remove("hidden");
  const ip4TypeSelect = document.getElementById("bridgeModalIp4Type");
  const ip6TypeSelect = document.getElementById("bridgeModalIp6Type");
  ip4TypeSelect.addEventListener("change", () => {
    document
      .getElementById("bridgeModalIpv4Static")
      .classList.toggle("hidden", ip4TypeSelect.value !== "static");
  });
  ip6TypeSelect.addEventListener("change", () => {
    document
      .getElementById("bridgeModalIpv6Static")
      .classList.toggle("hidden", ip6TypeSelect.value !== "static");
  });
  const cleanup = () => {
    modal.classList.add("hidden");
    content.innerHTML = origHtml;
    content.setAttribute("style", origStyle);
  };
  document
    .getElementById("bridgeModalCancel")
    .addEventListener("click", cleanup);
  document.getElementById("bridgeModalOk").addEventListener("click", () => {
    const ip4_type = ip4TypeSelect.value;
    const ip6_type = ip6TypeSelect.value;
    const ip_mtu = document.getElementById("bridgeModalMtu").value.trim();
    const stp = document.getElementById("bridgeModalStp").checked;
    const ip_address = document
      .getElementById("bridgeModalIpv4Addr")
      .value.trim();
    const ip_prefixlen =
      document.getElementById("bridgeModalIpv4Prefix").value.trim() || "24";
    const ip_gateway = document
      .getElementById("bridgeModalIpv4Gw")
      .value.trim();
    const ip_dns = document.getElementById("bridgeModalIpv4Dns").value.trim();
    const ip6_address = document
      .getElementById("bridgeModalIpv6Addr")
      .value.trim();
    const ip6_prefixlen =
      document.getElementById("bridgeModalIpv6Prefix").value.trim() || "64";
    const ip6_gateway = document
      .getElementById("bridgeModalIpv6Gw")
      .value.trim();
    const ip6_dns = document.getElementById("bridgeModalIpv6Dns").value.trim();
    cleanup();
    bridgeAction("update_ip", {
      name,
      ip4_type,
      ip6_type,
      ip_address,
      ip_prefixlen,
      ip_gateway,
      ip_dns,
      ip_mtu,
      ip6_address,
      ip6_prefixlen,
      ip6_gateway,
      ip6_dns,
      stp,
      bridge_type: bridgeType,
    });
  });
}

async function bridgeAction(action, data = {}) {
  if (state.saving) return;
  setSaving(true);
  try {
    const result = await api("saveBridge", { bridge_action: action, ...data });
    state.data.network = {
      ...state.data.network,
      bridges: result.bridges,
      saved_bridges: result.saved_bridges,
      available_ifaces: result.available_ifaces,
    };
    renderBridges();
    showToast(t("saved"));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setSaving(false);
  }
}

document.getElementById("createBridgeBtn").addEventListener("click", () => {
  const name = document.getElementById("bridgeNameInput").value.trim();
  const bridge_type = document.getElementById("bridgeTypeSelect").value;
  if (!name) return;
  bridgeAction("create", { name, bridge_type }).then(() => {
    document.getElementById("bridgeNameInput").value = "";
    document.getElementById("bridgeTypeSelect").value = "linux";
  });
});

document
  .getElementById("bridgeList")
  .addEventListener("click", async (event) => {
    const deleteBtn = event.target.closest(".bridge-delete-btn");
    if (deleteBtn) {
      const name = deleteBtn.dataset.bridge;
      const bridge_type = deleteBtn.dataset.bridgeType;
      if (await showConfirm(`${t("confirmDeleteBridge")} ${name}?`)) {
        bridgeAction("delete", { name, bridge_type });
      }
      return;
    }
    const removeBtn = event.target.closest(".member-remove-btn");
    if (removeBtn) {
      const name = removeBtn.dataset.bridge;
      const member = removeBtn.dataset.member;
      bridgeAction("remove_member", { name, member });
      return;
    }
    const editBtn = event.target.closest(".bridge-edit-btn");
    if (editBtn) {
      const name = editBtn.dataset.bridge;
      const bridge_type = editBtn.dataset.bridgeType;
      const saved = JSON.parse(
        decodeURIComponent(editBtn.dataset.saved || "{}"),
      );
      const bridge = (state.data.network?.bridges || []).find(
        (b) => b.name === name,
      );
      showBridgeIpModal(name, saved, bridge?.stp || false, bridge_type);
      return;
    }
  });

document.getElementById("bridgeList").addEventListener("change", (event) => {
  const addSelect = event.target.closest(".bridge-add-select");
  if (addSelect && addSelect.value) {
    const name = addSelect.dataset.bridge;
    const member = addSelect.value;
    bridgeAction("add_member", { name, member });
    return;
  }
});

async function displayAction(action, name) {
  if (state.saving) return;
  const confirmMsg =
    action === "off" ? t("displayPowerOffConfirm") : t("displayPowerOnConfirm");
  if (!(await showConfirm(confirmMsg))) return;
  setSaving(true);
  try {
    const result = await api("saveDisplay", { display_action: action, name });
    state.data.display = result.display;
    renderDisplay();
    showToast(t("saved"));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setSaving(false);
  }
}

document.getElementById("displayTable").addEventListener("click", (event) => {
  const btn = event.target.closest(".display-power-btn");
  if (!btn) return;
  displayAction(btn.dataset.displayAction, btn.dataset.displayName);
});

document
  .getElementById("aboutBtn")
  .addEventListener("click", () =>
    document.getElementById("aboutModal").classList.remove("hidden"),
  );
document
  .querySelectorAll("[data-close]")
  .forEach((button) =>
    button.addEventListener("click", () =>
      document.getElementById("aboutModal").classList.add("hidden"),
    ),
  );
document.getElementById("aboutModal").addEventListener("click", (event) => {
  if (event.target.id === "aboutModal")
    document.getElementById("aboutModal").classList.add("hidden");
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    document.getElementById("aboutModal").classList.add("hidden");
    document.getElementById("serviceModal").classList.add("hidden");
  }
});

document
  .getElementById("serviceModalClose")
  .addEventListener("click", closeServiceModal);
document.getElementById("serviceModal").addEventListener("click", (event) => {
  if (event.target.id === "serviceModal") closeServiceModal();
});
document
  .getElementById("serviceModalSave")
  .addEventListener("click", async () => {
    const name = document.getElementById("serviceModalSave").dataset.name;
    const content = document.getElementById("serviceModalEditor").value;
    if (!content.trim()) {
      const ok = await showConfirm(t("serviceEditClearConfirm"));
      if (!ok) return;
    }
    try {
      await api("serviceEditSave", { name, content });
      showToast(t("serviceEditSaved"));
      closeServiceModal();
      loadServices();
    } catch (err) {
      showToast(err.message, true);
    }
  });
document
  .getElementById("bootAnalyzeBtn")
  .addEventListener("click", async () => {
    try {
      const [plot, data] = await Promise.all([
        api("systemdAnalyzePlot"),
        api("systemdAnalyzeData"),
      ]);
      showAnalyzeModal(plot.svg || "", data);
    } catch (err) {
      showToast(err.message, true);
    }
  });
document.querySelectorAll(".analyze-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    document
      .querySelectorAll(".analyze-tab")
      .forEach((b) => b.classList.toggle("active", b === tab));
    document
      .querySelectorAll(".analyze-panel")
      .forEach((p) => p.classList.toggle("hidden", p.dataset.tab !== target));
  });
});
document.getElementById("zoomIn").addEventListener("click", () => {
  _svgZoom = Math.min(4, _svgZoom * 1.25);
  applySvgZoom();
});
document.getElementById("zoomOut").addEventListener("click", () => {
  _svgZoom = Math.max(0.1, _svgZoom / 1.25);
  applySvgZoom();
});
document.getElementById("zoomReset").addEventListener("click", () => {
  _svgZoom = 1;
  applySvgZoom();
});

applyPreferences();
window
  .matchMedia?.("(prefers-color-scheme: dark)")
  .addEventListener?.("change", () => applyPreferences({ rerender: true }));
window.addEventListener("storage", () => applyPreferences({ rerender: true }));
setInterval(() => applyPreferences(), 1500);

loadData().catch((error) => {
  document.getElementById("emptyState").textContent = error.message;
  showToast(error.message, true);
});
