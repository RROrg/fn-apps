# fn-scheduler

任务调度应用，提供 Web UI 配置定时/条件触发脚本，并使用 SQLite 持久化任务与执行历史。

## 功能概览
- 可配置两种触发方式：
  - **定时**：标准 5 字段 Cron 表达式（分钟 小时 日 月 周）。
  - **事件**：支持三种子类型——条件脚本轮询、系统开机触发、系统关机触发。
- 支持设置是否启用、运行账号标识、前置任务依赖以及脚本内容（账号仅可从系统组 0 / 1000 / 1001 的成员中选择，并在支持的系统上以该账号身份执行任务）。
- 任务执行历史可查看/删除/清空，并展示输出日志。
- SQLite 数据库存储任务与 `task_results` 记录。
- 单进程后端内置调度引擎 + 原生 HTTP/静态文件服务，无第三方依赖。
- 列表多选后可批量删除、启用/停用或立即运行任务。

## 运行方式
### 通过应用脚本
默认 `cmd/main` 会调用 `app/server/start.sh`，环境变量说明：
- `SCHEDULER_PORT`：HTTP 服务端口，默认 `28256`。
- `SCHEDULER_DB_PATH`：SQLite 路径，默认为 `${TRIM_PKGVAR}/scheduler.db`。
- `SCHEDULER_TASK_TIMEOUT`：任务脚本最长执行秒数（默认 900）。
- `SCHEDULER_CONDITION_TIMEOUT`：事件条件脚本检测超时（默认 60）。
- `SCHEDULER_SSL_CERT` / `SCHEDULER_SSL_KEY`：若同时指定，则使用对应 PEM 证书/私钥启用 HTTPS 服务。
- `SCHEDULER_ENABLE_SSL`：设为 `1/true/on/yes` 时，即使未提供证书也会请求使用 HTTPS（自动生成自签名证书，需要系统安装 `openssl`）。
- `SCHEDULER_BASE_PATH`：将 Web 与 API 挂载在指定前缀（如 `/scheduler`），便于与反向代理集成。
- `SCHEDULER_ENABLE_IPV6`：设为 `1/true/on/yes` 时默认使用 IPv6 (`::`) 监听地址，可与 `SCHEDULER_HOST` 联合定制。
- `SCHEDULER_SSL_SUBJECT` / `SCHEDULER_SSL_DAYS` / `SCHEDULER_OPENSSL_BIN`：自签名模式下分别控制证书主题、有效期天数及 `openssl` 可执行文件路径。
- `SCHEDULER_AUTH`：当需要启用 Basic Auth 时，指向一个 JSON 配置文件（默认读取 `app/auth.json`，可使用 `app/auth.sample.json` 复制修改）。

### 手动启动（开发/调试）
```bash
cd fn-scheduler/app/server
python3 scheduler_service.py \
  --host 0.0.0.0 \
  --port 28256 \
  --db ./scheduler.db \
  --ssl-cert ./server.crt \
  --ssl-key ./server.key \
  --base-path /scheduler \
  --ipv6
```
若未提供证书则默认使用 HTTP；提供证书后通过 `https://<host>:28256<base-path>/` 访问（如 `https://[::1]:28256/scheduler/`）。
`--base-path` 便于在反向代理下挂载于子路径；`--ipv6` 会优先使用 IPv6 套接字（默认 wildcard 地址为 `::`）。
如需快速体验 HTTPS 又不想准备证书，可简单添加 `--ssl`（或设置 `SCHEDULER_ENABLE_SSL=1`）：服务会自动调用 `openssl` 生成临时自签名证书，并在退出时清理。请确保运行环境可执行 `openssl`，或改为显式提供 `--ssl-cert/--ssl-key`。

### Web UI Basic Auth
- 默认会尝试读取 `./auth.json`；修改其中的 `username` / `password`，或改用 `password_sha256`（64 位十六进制 SHA-256 值）。
- 也可以通过 `--auth /path/to/auth.json`（或设置 `SCHEDULER_AUTH`）指定任意路径；配置文件不存在时 Basic Auth 不启用。
- 配置示例：

```json
{
  "enabled": true,
  "realm": "Scheduler",
  "username": "admin",
  "password": "change_me"
}
```

将 `password` 替换成实际口令后保存，重启服务即可对整个 Web UI（静态页面 + REST API）启用 Basic Auth。若希望避免明文密码，可删除 `password` 字段、保留 `password_sha256`（即 `echo -n "your_password" | sha256sum` 的结果）。

## 数据库结构
见 `docs/design.md`，包含 `tasks` 与 `task_results` 表字段说明及 REST API 列表。

## 注意事项
- 任务脚本默认通过 `/bin/bash -c`（Linux）或 `powershell`（Windows）执行。服务以 root 运行时会在启动子进程前切换为所选账号（仅支持系统组 0/1000/1001 的成员）；若服务本身并非 root，则需选择与当前用户一致的账号；Windows 环境下默认使用当前登录账号，无法在任务中切换。
- 前置任务依赖会在依赖任务最近一次成功后才放行执行。
- 事件任务的条件脚本需快速返回（默认 60s 超时），长时间阻塞会影响检查频率。
- 系统开/关机事件依赖服务启动与停止过程触发，请确保退出前给予任务足够时间执行完毕。
