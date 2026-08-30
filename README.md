# fn-apps

飞牛OS应用 仓库。

![Release](https://img.shields.io/github/v/release/RROrg/fn-apps?logo=github&style=flat-square)
![Downloads](https://img.shields.io/github/downloads/RROrg/fn-apps/total)

## 模块速览

| 应用名称 | 显示名称 | 版本 | 平台 | 描述 |
|---------|---------|------|------|------|
| fn-advancedsettings | 高级设置 | v1.1.1 | all | 管理启动设置、电源设置、屏幕设置、SSH设置、CPU设置、DNS设置、网络设置、代理设置、设备信息、端口信息、进程管理、服务管理、网络诊断。 |
| fn-appdownload | 应用坏心 | v1.1.3 | all | 官方商店和第三方源应用下载 |
| fn-appsettings | 应用设置 | v1.0.8 | all | 设置已安装应用的数据 |
| fn-audioplayer | 音频播放器 | v1.0.5 | all | 音频播放器应用，用于播放音频文件。支持包括 mp3、wav、flac、ogg、m4a、aac、wma、ape 等格式，会自动加载音频文件所在目录的歌词文件；支持客户端和服务端两种模式。 |
| fn-bluetooth | 蓝牙 | v1.0.3 | all | 蓝牙设备管理工具，支持配对连接音频设备、键鼠、文件传输、共享网络等功能。支持客户端模式（扫描连接）和服务端模式（接受连接）。 |
| fn-chromium | chromium | v1.0.4 | all | Chromium 是一个开源的网页浏览器项目，旨在为用户提供更安全、更快速和更稳定的浏览体验。 |
| fn-chromium-desktop | chromium-desktop | v1.0.3 | all | Chromium-desktop 是一个基于 KMS/DRM 的网页浏览器及音频支持，旨在本地显示器提供浏览器功能。 |
| fn-codeserver | code-server | v1.1.1 | all | code-server 是 VS Code 的在线版本，允许您通过浏览器进行代码编辑和开发。 |
| fn-execute | 执行器 | v1.0.4 | all | 执行器可直接在可执行程序上右键执行，支持 sh、py、pl、rb、js、ts、lua、bash、zsh、fish、bin、run 等格式的文件。 |
| fn-fail2ban | fail2ban | v1.0.6 | all | fail2ban 是一个开源的入侵防御工具，用于保护 Linux 服务器免受暴力破解攻击。 它通过监控日志文件，检测可疑的登录尝试，并自动封禁恶意 IP 地址，从而增强系统的安全性。 |
| fn-grafana-alloy | Grafana Alloy | v1.19.2 | all | 可观测性数据采集器，收集系统和应用日志并发送到 Loki。 |
| fn-guacamole | guacamole | v1.6.0-1 | all | Apache Guacamole 是一个无客户端的远程桌面网关，支持 RDP、VNC、SSH、telnet 等标准协议。 |
| fn-influxdb | InfluxDB | v2.9.1 | all | 高性能时序数据库，适用于指标、事件和分析工作负载。 |
| fn-installer | 安装器 | v1.0.5 | all | 安装器，用于安装本地 FPK 应用文件。支持右键安装。 |
| fn-iVentoy | iVentoy | v1.0.39-1 | all | iVentoy - PXE 启动服务器，支持通过局域网网络安装操作系统。 |
| fn-kodi | kodi | v1.0.8 | all | Kodi 是一个免费且开源的媒体播放器软件，用于播放视频、音频和图像。 |
| fn-linux-station | linux-station | v1.0.2 | all | Linux 工作站是一个基于 Linux 的桌面环境，旨在为用户提供一个高效、稳定和易用的工作环境。 |
| fn-open-vm-tools | open-vm-tools | v1.1.1 | all | Open-VM-Tools 是 VMware Tools 的开源替代品，旨在为运行在 VMware 环境中的虚拟机提供更好的性能和用户体验。 |
| fn-p2s | 端口代理 | v1.0.4 | all | 通过 fnOS 应用网关路径访问本机端口服务。 |
| fn-qemu-ga | qemu-ga | v1.1.1 | all | QEMU Guest Agent 是一个运行在虚拟机内部的守护进程，旨在通过与虚拟化主机的交互，执行一系列操作以增强虚拟机的管理能力。 |
| fn-scheduler | 任务计划 | v1.3.2 | all | 轻量级的任务计划应用，支持设置定时任务以自动执行脚本或命令，同时也支持基于条件的任务触发。 |
| fn-scrutiny | Scrutiny | v1.70.0 | all | 硬盘 S.M.A.R.T 健康监控，集成 Scrutiny Web 与 Collector，提供可视化硬盘健康状态追踪。依赖 InfluxDB。 |
| fn-speedtest | 网络测速 | v1.0.1 | all | 测量客户端到服务器的速率，以及服务器到外网的出口速率。 |
| fn-terminal | terminal | v1.1.2 | all | terminal (ttyd + tmux) 是一个基于 Web 的终端应用程序，允许用户通过浏览器访问和管理服务器终端会话，提供便捷的远程终端操作体验。 |
| fn-vfnOS | vfnOS | v1.0.4 | all | 在 fnOS/FygoOS 系统中创建异架构的 fnOS 虚拟机（x86_64 fnOS 下则创建 aarch64 的 fnOS 虚拟机, aarch64 fnOS 下则创建 x86_64 的 fnOS 虚拟机）。 |
| fn-vFygoOS | vFygoOS | v1.0.4 | all | 在 fnOS/FygoOS 系统中创建异架构的 FygoOS 虚拟机（x86_64 fnOS 下则创建 aarch64 的 FygoOS 虚拟机, aarch64 fnOS 下则创建 x86_64 的 FygoOS 虚拟机）。 |
| fn-vgmng | 存储池管理 | v1.0.5 | all | 存储池管理, 支持非飞牛存储池(其他NAS系统存储池)的管理。 |
| fn-VirtualHereServer | VirtualHereServer | v4.8.8 | all | VirtualHere USB 服务端，支持通过网络远程访问 USB 设备。 |
| fn-wifi-hotspot | 无线热点 | v1.1.9 | all | 无线热点创建工具，允许用户轻松地将计算机变成一个 Wi-Fi 热点，分享网络连接给其他设备。 |
| fn-WParted | WParted | v1.0.2 | all | 磁盘分区编辑器 - 创建、调整大小、删除、移动、复制、检查和格式化分区。 |
| fn-zerotier | ZeroTier | v1.0.9 | all | ZeroTier 是一个无中心的虚拟网络，无需配置即可连接设备。 |


## Images
fnOS 下载地址：https://raw.githubusercontent.com/RROrg/fn-apps/refs/heads/main/fnOS.json  
获取最新版本的 fnOS 镜像下载地址：
```shell
# E.g. 获取 fnOS-x86_64 最新版本的下载地址
curl -skL "https://raw.githubusercontent.com/RROrg/fn-apps/refs/heads/main/fnOS.json" \
| jq -r '[.[] | select(.name=="fnOS-x86_64")] | sort_by((.version | split(".") | map(tonumber)), .version) | last | .url'
```
FygoOS 下载地址：https://raw.githubusercontent.com/RROrg/fn-apps/refs/heads/main/FygoOS.json  
获取最新版本的 FygoOS 镜像下载地址：
```shell
# E.g. 获取 FygoOS-x86_64 最新版本的下载地址
curl -skL "https://raw.githubusercontent.com/RROrg/fn-apps/refs/heads/main/FygoOS.json" \
| jq -r '[.[] | select(.name=="FygoOS-x86_64")] | sort_by((.version | split(".") | map(tonumber)), .version) | last | .url'
```

## Proxmox VE
  ```
  # One Click Install fnOS VM on Proxmox VE:
  curl -fsSL https://github.com/RROrg/fn-apps/raw/refs/heads/main/pve.sh | bash -s -- --type fnos --arch x86_64

  Usage: ./pve.sh [--onboot <0|1>] [--arch <x86_64|aarch64>] [--efi <0|1>] [--iso <path>]
            [--storage <name>] [--v9ppath <path>] [--vfsdirid <dirid>]

    --onboot <0|1>             Enable VM on boot, default 1 (enable)
    --type <fnos|fygonas>      Type, support fnos and fygonas, default fnos
    --arch <x86_64|aarch64>    Architecture, support x86_64 and aarch64, default x86_64
    --efi <0|1>                Enable UEFI boot, default 1 (enable)
    --iso <path>               Local ISO path, use local ISO if set
    --storage <name>           Storage name for images, as local-lvm, default auto get
    --v9ppath <path>           Set to /path/to/9p to mount virtio 9p share
    --vfsdirid <dirid>         Set to <dirid> to mount virtio fs share
  ```

## 社区支持

- QQ 群：130359605 · [点击加入](https://qm.qq.com/q/xMUyJacSIw)

- [https://github.com/RROrg/fn-apps](https://github.com/RROrg/fn-apps)
- [https://github.com/Brian099/fn_fpk_packages](https://github.com/Brian099/fn_fpk_packages)
- [https://gitee.com/laoknas/fn_fpk_packages](https://gitee.com/laoknas/fn_fpk_packages)

- Issue：在 GitHub 提交问题/建议，描述部署环境、日志与复现步骤。
- PR：欢迎补充新模块、修复脚本或完善文档，遵循现有目录结构即可。

## 7: Sponsoring

- <img src="https://raw.githubusercontent.com/wjz304/wjz304/master/my/buymeacoffee.png" width="700">

## 8: License

- [GPL-V3](https://github.com/RROrg/fn-apps/blob/main/LICENSE)
