(function () {
  var T = {
    "Available Spare": "可用备用空间",
    "Available Reserved Space": "可用保留空间",
    "Controller Busy Time": "控制器忙碌时间",
    "Critical CompTime": "关键完成时间",
    "Critical Warning": "严重警告",
    "Data Units Read": "数据单元读取",
    "Data Units Written": "数据单元写入",
    "Host Reads": "主机读取",
    "Host Writes": "主机写入",
    "Media Errors": "介质错误",
    "Numb Err Log Entries": "错误日志条目数",
    "Percentage Used": "使用百分比",
    "Power Cycles": "开关机次数",
    "Power on Hours": "运行小时数",
    "Unsafe Shutdowns": "不安全关机",
    "Warning Temp Time": "警告温度时间",
    Temperature: "温度",
    Threshold: "阈值",
    Ideal: "理想",
    Worst: "最差",
    high: "高",
    low: "低",
    passed: "通过",
    warn: "警告",
    failed: "失败",
    visible: "可见",
    hidden: "隐藏",
    Export: "导出",
    Forever: "永久",
    forever: "永久",
    year: "年",
    month: "月",
    week: "周",
    day: "天",
    "Reallocated Sectors Count": "重新分配扇区计数",
    "Current Pending Sector Count": "当前待处理扇区计数",
    "Load Cycle Count": "加载循环计数",
    "Start/Stop Count": "启动/停止计数",
    "Spin-Up Time": "主轴启动时间",
    "Spin High Current": "主轴高电流",
    "Spin Buzz": "主轴嗡鸣",
    "Power-Off Retract Cycle": "断电缩回循环",
    "Power-off Retract Count": "断电缩回计数",
    "Offline Seek Performance": "离线寻道性能",
    "Shock During Write": "写入时震动",
    "Vibration During Write": "写入时振动",
    "Thermal Asperity Rate": "热粗糙率",
    "Torque Amplification Count": "扭矩放大计数",
    "G-Sense Error Rate": "G-Sense 错误率",
    "Soft Read Error Rate": "软读取错误率",
    "Soft ECC Correction": "软 ECC 纠正",
    "Run Out Cancel": "溢出取消",
    "Read Channel Margin": "读取通道裕量",
    "Read Error Retry Rate": "读取错误重试率",
    "Read Error Rate": "读取错误率",
    "Seek Error Rate": "寻道错误率",
    "Hardware ECC Recovered": "硬件 ECC 恢复",
    "Spin Retry Count": "主轴重试计数",
    "Throughput Performance": "吞吐性能",
    "UltraDMA CRC Error Count": "UltraDMA CRC 错误计数",
    "Reported Uncorrectable Errors": "报告的不可纠正错误",
    "Reallocation Event Count": "重新分配事件计数",
    "High Fly Writes": "高飞写入",
    "Temperature Difference": "温度差异",
    "Checksum Errors": "校验和错误",
    "Read Errors": "读取错误",
    "Write Errors": "写入错误",
    Reads: "读取",
    Writes: "写入",
    "Command Timeout": "命令超时",
    "Endurance Remaining": "剩余耐久度",
    "Media Wearout Indicator": "介质磨损指标",
    "Life Left": "剩余寿命",
    "Unexpected Power Loss Count": "意外断电次数",
    "Power Loss Protection Failure": "断电保护失败",
    "Program Fail Count Total": "编程失败计数",
    "Erase Fail Count": "擦除失败计数",
    "SSD Program Fail Count": "SSD 编程失败计数",
    "SSD Erase Fail Count": "SSD 擦除失败计数",
    "Wear Range Delta": "磨损范围增量",
    "Good Block Count": "良好块计数",
    "Average erase count": "平均擦除计数",
    "Total LBAs Read": "总 LBA 读取",
    "Total LBAs Written": "总 LBA 写入",
    "Total LBAs Read Expanded": "总 LBA 读取（扩展）",
    "Total LBAs Written Expanded": "总 LBA 写入（扩展）",
    "Read Correction Algorithm Invocations": "读取纠正算法调用",
    "Read Errors Corrected by ECC Delayed": "ECC 延迟纠正的读取错误",
    "Read Errors Corrected by ECC Fast": "ECC 快速纠正的读取错误",
    "Read Errors Corrected by ReReads/ReWrites": "重读/重写纠正的读取错误",
    "Read Total Errors Corrected": "读取总纠正错误",
    "Read Total Uncorrected Errors": "读取总不可纠正错误",
    "Write Correction Algorithm Invocations": "写入纠正算法调用",
    "Write Errors Corrected by ECC Delayed": "ECC 延迟纠正的写入错误",
    "Write Errors Corrected by ECC Fast": "ECC 快速纠正的写入错误",
    "Write Errors Corrected by ReReads/ReWrites": "重读/重写纠正的写入错误",
    "Write Total Errors Corrected": "写入总纠正错误",
    "Write Total Uncorrected Errors": "写入总不可纠正错误",
    "Pre-Fail": "预失败",
    "Old-Age": "老化",
    "Unknown Attribute Name": "未知属性名",
    "Device Type": "设备类型",
    "Device Model": "设备型号",
    "Firmware Version": "固件版本",
    "LU WWN Device Id": "LU WWN 设备ID",
    "Serial Number": "序列号",
    Interface: "接口",
    Capacity: "容量",
    Protocol: "协议",
    "Powered On": "已运行",
    Score: "评分",
    Status: "状态",
    Name: "名称",
    Value: "值",
    Weight: "权重",
    History: "历史",
    Attribute: "属性",
    Trend: "趋势",
    "Daily Writes": "每日写入",
    "Daily Reads": "每日读取",
    "R/W Ratio": "读写比",
    Intensity: "强度",
    Endurance: "耐久度",
    "Est. Remaining": "预计剩余",
    "TBs Read": "TB 读取",
    "TBs Written": "TB 写入",
    Workload: "负载",
    "Replacement Risk": "更换风险",
    "Dark Mode": "深色模式",
    System: "系统",
    "Display Title": "显示标题",
    "File Size": "文件大小",
    "Binary Units (GiB)": "二进制单位 (GiB)",
    Humanize: "人性化",
    "Line stroke": "线条样式",
    Smooth: "平滑",
    "Device Status - Thresholds": "设备状态 - 阈值",
    Both: "两者",
    "Notify - Level": "通知 - 级别",
    Fail: "仅失败",
    "Notify - Filter Attributes": "通知 - 过滤属性",
    Always: "始终",
    Enabled: "启用",
    Disabled: "禁用",
    "Fail Above": "失败高于",
    "Device WWN (optional)": "设备 WWN（可选）",
    "Heartbeat Notifications": "心跳通知",
    "Master toggle for all scheduled reports": "所有定时报告的主开关",
    "Smart = manufacturer failures, Scrutiny = threshold failures, Both = either":
      "Smart = 厂商故障，Scrutiny = 阈值故障，两者 = 任一",
    "Warn = notify on warnings and failures, Fail = notify on failures only":
      "警告 = 通知警告和失败，仅失败 = 仅通知失败",
    "Alert when smartctl encounters errors during device scan or data collection":
      "smartctl 在设备扫描或数据采集时遇到错误则告警",
    "Maximum notifications per hour across all types (0 = unlimited)":
      "每小时最大通知数（0 = 无限制）",
    "Stop sending notifications at this time (leave empty to disable)":
      "此时停止发送通知（留空则禁用）",
    'Periodic "all drives healthy" notification': '定期"所有硬盘健康"通知',
    "Notification Rate Limit (per hour)": "通知速率限制（每小时）",
    "Retrieve SCT Temperature History": "获取 SCT 温度历史",
    ATA: "ATA",
    NVMe: "NVMe",
    "Delete Device": "删除设备",
    "Drive health at a glance": "硬盘健康概览",
    "not yet implemented": "尚未实现",
    "Notification Channels": "通知渠道",
    "No notification channels configured. Add one below, or configure notify.urls in scrutiny.yaml.":
      "未配置通知渠道。请在下方添加，或在 scrutiny.yaml 中配置 notify.urls。",
    "Missed Ping Timeout Override (minutes)": "心跳超时覆盖（分钟）",
    "Override the global missed ping timeout for this device. 0 = use global (60 min)":
      "覆盖此设备的全局心跳超时。0 = 使用全局设置（60分钟）",
    "Current Helium Level": "当前氦气水平",
    "Data Address Mark errors": "数据地址标记错误",
    "Disk Shift": "磁盘偏移",
    "End-to-End error": "端到端错误",
    "Flying Height": "飞行高度",
    "Free Fall Events": "自由落体事件",
    "Free Fall Protection": "自由落体保护",
    "GMR Head Amplitude": "GMR 磁头振幅",
    "Grown Defect List": "增长缺陷列表",
    "Head Flying Hours": "磁头飞行小时",
    "Head Stability": "磁头稳定性",
    "Induced Op-Vibration Detection": "感应操作振动检测",
    "Load Friction": "加载摩擦",
    "Load/Unload Cycle Count": "加载/卸载循环计数",
    "Load/Unload Retry Count": "加载/卸载重试计数",
    "Loaded Hours": "加载小时数",
    "Minimum Spares Remaining": "最小剩余备用",
    "Multi-Zone Error Rate": "多区域错误率",
    "Newly Added Bad Flash Block": "新增坏闪存块",
    "Recalibration Retries or Calibration Retry Count": "重新校准重试计数",
    "SATA Downshift Error Count or Runtime Bad Block": "SATA 降速错误计数",
    "Seek Time Performance": "寻道时间性能",
    "Unused Reserved Block Count Total": "未使用保留块总数",
    "Used Reserved Block Count Total": "已使用保留块总数",
    "Attribute actions": "属性操作",
    "Device Label": "设备标签",
    "Device settings": "设备设置",
    "Device Settings": "设备设置",
    "Device UUID": "设备 UUID",
    "Failed to load device details:": "加载设备详情失败：",
    "Failed to remove override:": "移除覆盖失败：",
    "Failed to save override:": "保存覆盖失败：",
    "Failure %": "失败 %",
    "Failure Rate:": "失败率：",
    "Forced ": "已强制 ",
    "Force passed": "强制通过",
    "Force Status": "强制状态",
    "Ignore attribute": "忽略属性",
    Ignored: "已忽略",
    Manufacturer: "制造商",
    "Mixed R/W": "混合读写",
    "Model Family": "型号系列",
    Monitor: "监控",
    Norm: "标准化",
    Normalized: "标准化值",
    "Mute notifications": "静音通知",
    "No Devices Detected!": "未检测到设备！",
    "This will remove the device and all historical data from Scrutiny. ":
      "此操作将从 Scrutiny 中删除该设备及所有历史数据。",
    Health: "健康",
    "Age (Newest First)": "使用时间（最新优先）",
    "Age (Oldest First)": "使用时间（最旧优先）",
    "Capacity (Largest First)": "容量（最大优先）",
    "Capacity (Smallest First)": "容量（最小优先）",
    "Check Interval (minutes)": "检查间隔（分钟）",
    "Daily Report": "每日报告",
    "Daily Report Time": "每日报告时间",
    "Device Hours": "设备运行时间",
    "Directory to save PDF reports": "PDF 报告保存目录",
    "Discord Webhook URL": "Discord Webhook URL",
    Fahrenheit: "华氏度",
    "From Address": "发件地址",
    "Heartbeat Interval (hours)": "心跳间隔（小时）",
    "Hours between heartbeat notifications (default: 24)":
      "心跳通知间隔小时数（默认：24）",
    "How often to check (default: 5)": "检查频率（默认：5）",
    Label: "标签",
    "Label (optional)": "标签（可选）",
    "Leave empty for all devices": "留空表示所有设备",
    "Minimum time between repeat notifications per device (0 = use timeout)":
      "每设备重复通知最小间隔（0 = 使用超时设置）",
    "Monthly Report": "每月报告",
    "Monthly Report Time": "每月报告时间",
    "Seconds between health pushes (default: 60)":
      "健康推送间隔秒数（默认：60）",
    "Uptime Kuma Push Monitor URL (can also be set in scrutiny.yaml)":
      "Uptime Kuma 推送监控 URL（也可在 scrutiny.yaml 中设置）",
    "Missed Ping Timeout (minutes)": "心跳超时（分钟）",
    "Config/env URLs cannot be removed from UI": "配置/环境 URL 无法从界面删除",
    "all drives healthy": "所有硬盘健康",
    Action: "操作",
    Ignore: "忽略",
    Fragmentation: "碎片率",
    "Last Scrub": "上次清理",
    Never: "从未",
    "Unknown Pool": "未知池",
    "Error Summary": "错误摘要",
    "In Progress": "进行中",
    Completed: "已完成",
    Canceled: "已取消",
    "Failed to load ZFS pool details:": "加载 ZFS 池详情失败：",
    "Delete Pool": "删除池",
    "e.g. discord://token@webhookid": "例如 discord://token@webhookid",
    "click for more details.": "点击查看详情。",
    "Contains a normalized percentage (0 to 100%) of the remaining spare capacity available.":
      "包含可用剩余备用空间的标准化百分比（0 到 100%）。",
    "Contains the number of power cycles.": "包含开关机次数。",
    "Contains the number of hours the device has been powered on.":
      "包含设备已运行的小时数。",
    "Contains the current device temperature.": "包含当前设备温度。",
    "Contains the number of unsafe shutdowns.": "包含不安全关机次数。",
    "Contains the number of errors logged by the device.":
      "包含设备记录的错误数。",
    "Contains the number of media errors.": "包含介质错误数。",
    "Contains the number of data units written.": "包含已写入的数据单元数。",
    "Contains the number of data units read.": "包含已读取的数据单元数。",
    "Contains the amount of time the controller is busy.":
      "包含控制器忙碌的时间。",
    "Contains the critical warning state.": "包含严重警告状态。",
    "Contains the warning temperature time.": "包含警告温度时间。",
    "Contains the completion time.": "包含完成时间。",
    Raw: "原始值",
    "MDADM RAID": "MDADM RAID",
    "RAID Arrays": "RAID 阵列",
    "No MDADM arrays found": "未找到 MDADM 阵列",
    "Ensure the MDADM collector is running and correctly configured.":
      "请确保 MDADM 采集器正在运行且配置正确。",
    "Btrfs Filesystems": "Btrfs 文件系统",
    "Btrfs filesystem health and topology": "Btrfs 文件系统健康与拓扑",
    "Drive activity rates, intensity, and endurance":
      "硬盘活动率、强度和耐久度",
    "Smart = manufacturer failures, Scrutiny = threshold failures, ":
      "Smart = 厂商故障，Scrutiny = 阈值故障，",
    "Warn = notify on warnings and failures, Fail = notify on failures only":
      "警告 = 通知警告和失败，仅失败 = 仅通知失败",
    "Not set": "未设置",
    "Contains the amount of time the controller is busy with I/O commands. The controller is busy when there is a command outstanding to an I/O Queue (specifically, a command was issued via an I/O Submission Queue Tail doorbell write and the corresponding completion queue entry has not been posted yet to the associated I/O Completion Queue). This value is reported in minutes.":
      "包含控制器忙于处理 I/O 命令的时间。当 I/O 队列中有未完成的命令时（即通过 I/O 提交队列尾部门铃写入发出了命令，但相应的完成队列条目尚未发布到关联的 I/O 完成队列），控制器即为忙碌状态。此值以分钟为单位报告。",
    "Contains the amount of time in minutes that the controller is operational and the Composite Temperature is greater the Critical Composite Temperature Threshold (CCTEMP) field in the Identify Controller data structure.":
      "包含控制器运行且复合温度超过识别控制器数据结构中关键复合温度阈值（CCTEMP）字段的时间（以分钟为单位）。",
    "Contains the number of 512 byte data units the host has read from the controller; this value does not include metadata. This value is reported in thousands (i.e., a value of 1 corresponds to 1000 units of 512 bytes read) and is rounded up. When the LBA size is a value other than 512 bytes, the controller shall convert the amount of data read to 512 byte units.":
      "包含主机从控制器读取的 512 字节数据单元数；此值不包括元数据。此值以千为单位报告（即值 1 对应读取 1000 个 512 字节单元）并向上取整。当 LBA 大小不是 512 字节时，控制器应将读取的数据量转换为 512 字节单元。",
    "Contains the number of 512 byte data units the host has written to the controller; this value does not include metadata. This value is reported in thousands (i.e., a value of 1 corresponds to 1000 units of 512 bytes written) and is rounded up. When the LBA size is a value other than 512 bytes, the controller shall convert the amount of data written to 512 byte units.":
      "包含主机写入控制器的 512 字节数据单元数；此值不包括元数据。此值以千为单位报告（即值 1 对应写入 1000 个 512 字节单元）并向上取整。当 LBA 大小不是 512 字节时，控制器应将写入的数据量转换为 512 字节单元。",
    "Contains the number of read commands completed by the controller":
      "包含控制器完成的读取命令数",
    "Contains the number of write commands completed by the controller":
      "包含控制器完成的写入命令数",
    "Contains the number of occurrences where the controller detected an unrecovered data integrity error. Errors such as uncorrectable ECC, CRC checksum failure, or LBA tag mismatch are included in this field.":
      "包含控制器检测到不可恢复数据完整性错误的次数。不可纠正的 ECC、CRC 校验和失败或 LBA 标签不匹配等错误包含在此字段中。",
    "Contains the number of Error Information log entries over the life of the controller.":
      "包含控制器生命周期内的错误信息日志条目数。",
    "Contains a vendor specific estimate of the percentage of NVM subsystem life used based on the actual usage and the manufacturer\u2019s prediction of NVM life. A value of 100 indicates that the estimated endurance of the NVM in the NVM subsystem has been consumed, but may not indicate an NVM subsystem failure. The value is allowed to exceed 100. Percentages greater than 254 shall be represented as 255. This value shall be updated once per power-on hour (when the controller is not in a sleep state).":
      "包含基于实际使用情况和制造商 NVM 寿命预测的 NVM 子系统已用寿命百分比（厂商特定估算）。值 100 表示 NVM 子系统中 NVM 的估计耐久度已耗尽，但不一定表示 NVM 子系统故障。此值允许超过 100。超过 254 的百分比应表示为 255。此值应在每次开机时更新一次（当控制器未处于睡眠状态时）。",
    "Contains the number of power-on hours. Power on hours is always logging, even when in low power mode.":
      "包含开机小时数。开机小时数始终记录，即使在低功耗模式下也是如此。",
    "This count is incremented when a shutdown notification (CC.SHN) is not received prior to loss of power.":
      "当断电前未收到关机通知（CC.SHN）时，此计数递增。",
    Scrutiny: "Scrutiny",
  };

  function translateStr(text) {
    if (!text || typeof text !== "string") return text;
    for (var en in T) {
      if (text.indexOf(en) !== -1) {
        text = text.split(en).join(T[en]);
      }
    }
    return text;
  }

  function translateNode(node) {
    if (!node || node.nodeType !== 3) return;
    var text = node.textContent;
    if (!text || !text.trim()) return;
    var newText = translateStr(text);
    if (newText !== text) node.textContent = newText;
  }

  function translateElement(el) {
    if (!el) return;
    var walker = document.createTreeWalker(
      el,
      NodeFilter.SHOW_TEXT,
      null,
      false,
    );
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(translateNode);
  }

  function translateObj(obj) {
    if (!obj && typeof obj !== "object") return;
    if (Array.isArray(obj)) {
      for (var i = 0; i < obj.length; i++) {
        if (typeof obj[i] === "string") obj[i] = translateStr(obj[i]);
        else if (typeof obj[i] === "object") translateObj(obj[i]);
      }
    } else {
      for (var key in obj) {
        if (typeof obj[key] === "string") obj[key] = translateStr(obj[key]);
        else if (typeof obj[key] === "object") translateObj(obj[key]);
      }
    }
  }

  var origXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    this._trUrl = typeof url === "string" ? url : "";
    return origXHROpen.apply(this, arguments);
  };

  var origResponseTextDesc = Object.getOwnPropertyDescriptor(
    XMLHttpRequest.prototype,
    "responseText",
  );
  if (origResponseTextDesc && origResponseTextDesc.get) {
    Object.defineProperty(XMLHttpRequest.prototype, "responseText", {
      get: function () {
        var value = origResponseTextDesc.get.call(this);
        if (
          this._trUrl &&
          this._trUrl.indexOf("/api/") !== -1 &&
          this.readyState === 4
        ) {
          if (!this._trCached) {
            try {
              var data = JSON.parse(value);
              translateObj(data);
              this._trCached = JSON.stringify(data);
            } catch (e) {
              this._trCached = value;
            }
          }
          return this._trCached;
        }
        return value;
      },
      configurable: true,
    });
  }

  var origResponseDesc = Object.getOwnPropertyDescriptor(
    XMLHttpRequest.prototype,
    "response",
  );
  if (origResponseDesc && origResponseDesc.get) {
    Object.defineProperty(XMLHttpRequest.prototype, "response", {
      get: function () {
        var value = origResponseDesc.get.call(this);
        if (
          this._trUrl &&
          this._trUrl.indexOf("/api/") !== -1 &&
          this.readyState === 4 &&
          typeof value === "string"
        ) {
          if (!this._trRespCached) {
            try {
              var data = JSON.parse(value);
              translateObj(data);
              this._trRespCached = JSON.stringify(data);
            } catch (e) {
              this._trRespCached = value;
            }
          }
          return this._trRespCached;
        }
        if (
          this._trUrl &&
          this._trUrl.indexOf("/api/") !== -1 &&
          this.readyState === 4 &&
          typeof value === "object" &&
          value !== null
        ) {
          if (!this._trRespCached) {
            translateObj(value);
            this._trRespCached = true;
          }
        }
        return value;
      },
      configurable: true,
    });
  }

  var origFetch = window.fetch;
  window.fetch = function () {
    var args = arguments;
    var url = "";
    if (args[0] && typeof args[0] === "string") url = args[0];
    else if (args[0] && args[0].url) url = args[0].url;

    if (url.indexOf("/api/") === -1) {
      return origFetch.apply(this, args);
    }

    return origFetch.apply(this, args).then(function (resp) {
      var ct = resp.headers.get("content-type") || "";
      if (ct.indexOf("json") === -1) return resp;
      return resp.text().then(function (body) {
        try {
          var data = JSON.parse(body);
          translateObj(data);
          return new Response(JSON.stringify(data), {
            status: resp.status,
            statusText: resp.statusText,
            headers: resp.headers,
          });
        } catch (e) {
          return new Response(body, {
            status: resp.status,
            statusText: resp.statusText,
            headers: resp.headers,
          });
        }
      });
    });
  };

  function setupDOMTranslation() {
    translateElement(document.body);

    var obs = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        for (var j = 0; j < m.addedNodes.length; j++) {
          var node = m.addedNodes[j];
          if (node.nodeType === 1) translateElement(node);
          else if (node.nodeType === 3) translateNode(node);
        }
        if (m.type === "characterData") translateNode(m.target);
      }
    });

    obs.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    setInterval(function () {
      translateElement(document.body);
    }, 1000);
  }

  if (document.body) {
    setupDOMTranslation();
  } else {
    document.addEventListener("DOMContentLoaded", setupDOMTranslation);
  }
})();
