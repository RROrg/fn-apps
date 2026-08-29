# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import argparse
import json
import mimetypes
import os
import re
import signal
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-advancedsettings")
# 运行时数据目录：优先用 TRIM_PKGVAR，回退到 /var/apps/<app>/var
_pkgvar = _env("TRIM_PKGVAR")
STATE_FILE = Path(_pkgvar) if _pkgvar else Path(f"/var/apps/{APP_NAME}/var")
STATE_FILE = STATE_FILE / "settings.json"
NETWORK_APPLY = Path("/usr/local/sbin/fn-advancedsettings-network-apply")
NETWORK_SERVICE = Path("/etc/systemd/system/fn-advancedsettings-network.service")
BRIDGE_APPLY = Path("/usr/local/sbin/fn-advancedsettings-bridge-apply")
BRIDGE_SERVICE = Path("/etc/systemd/system/fn-advancedsettings-bridge.service")
CPU_APPLY = Path("/usr/local/sbin/fn-advancedsettings-cpu-apply")
CPU_SERVICE = Path("/etc/systemd/system/fn-advancedsettings-cpu.service")
DISPLAY_APPLY = Path("/usr/local/sbin/fn-advancedsettings-display-apply")
DISPLAY_SERVICE = Path("/etc/systemd/system/fn-advancedsettings-display.service")
TCP_SYSCTL_CONF = Path("/etc/sysctl.d/99-fn-advancedsettings-tcp.conf")
TCP_MODULES_LOAD = Path("/etc/modules-load.d/fn-advancedsettings-tcp.conf")
PROXY_PROFILE = Path("/etc/profile.d/fn-advancedsettings-proxy.sh")
PROXY_APT = Path("/etc/apt/apt.conf.d/99fn-advancedsettings-proxy")
PROXY_DOCKER_DIR = Path("/etc/systemd/system/docker.service.d")
PROXY_DOCKER_CONF = PROXY_DOCKER_DIR / "proxy.conf"
PROXY_PIP = Path("/etc/pip.conf")
PROXY_NPM = Path("/etc/npmrc")
PROXY_GIT = Path("/etc/gitconfig")
PROXY_KEYS = ["http_proxy", "https_proxy", "ftp_proxy", "socks_proxy", "no_proxy"]

PATHS = {
    "grub": Path("/etc/default/grub"),
    "logind": Path("/etc/systemd/logind.conf"),
    "sshd": Path("/etc/ssh/sshd_config"),
    "sshd_custom": Path("/etc/ssh/sshd_config.d/trim_sshd.conf"),
    "resolv": Path("/etc/resolv.conf"),
    "hosts": Path("/etc/hosts"),
    "environment": Path("/etc/environment"),
    "device_id": Path("/etc/device_id"),
}

REQUEST_CONTEXT = threading.local()
TCP_MODULES_PROBED = False
_diag_proc: subprocess.Popen | None = None
_diag_lock = threading.Lock()


class ThreadingUnixHTTPServer(
    socketserver.ThreadingMixIn,
    socketserver.UnixStreamServer,  # pyright: ignore[reportAttributeAccessIssue]
):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path, handler_cls, *, base_path, www_root):
        self.server_name = APP_NAME
        self.server_port = 0
        self.base_path = normalize_base_path(base_path)
        self.www_root = Path(www_root)
        super().__init__(socket_path, handler_cls)  # pyright: ignore[reportCallIssue]


class Handler(BaseHTTPRequestHandler):
    server: ThreadingUnixHTTPServer  # type: ignore[reportIncompatibleVariableOverride]
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.route()

    def do_HEAD(self):
        self.route()

    def do_POST(self):
        self.route()

    def do_PUT(self):
        self.route()

    def do_DELETE(self):
        self.route()

    def log_message(self, format, *args):
        sys.stdout.write(
            "%s - - [%s] %s\n"
            % (self.client_address, self.log_date_time_string(), format % args)
        )
        sys.stdout.flush()

    def route(self):
        parsed = urlsplit(self.path)
        if parsed.path == self.server.base_path:
            try:
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header(
                    "Location",
                    self.server.base_path
                    + "/"
                    + (("?" + parsed.query) if parsed.query else ""),
                )
                self.send_header("Content-Length", "0")
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError, OSError):
                # client disconnected; treat as normal
                return
            return
        path = strip_base_path(parsed.path, self.server.base_path)
        if path.startswith("/api"):
            self.serve_api(parsed.query)
            return
        self.serve_static(path)

    def serve_static(self, path):
        rel_path = unquote(path or "/")
        if rel_path in ("", "/"):
            rel_path = "/index.html"
        target = (self.server.www_root / rel_path.lstrip("/")).resolve()
        root = self.server.www_root.resolve()
        if root != target and root not in target.parents:
            self.send_error(HTTPStatus.BAD_REQUEST, "Bad request")
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content_type = (
            mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        )
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type = f"{content_type}; charset=utf-8"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Cache-Control",
            "no-store" if target.name == "index.html" else "public, max-age=60",
        )
        try:
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # client disconnected mid-response; treat as normal
            return

    def serve_api(self, query):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        headers = {key: value for key, value in self.headers.items()}
        with request_context(
            self.command, query=query, headers=headers, body=body, handler=self
        ):
            try:
                dispatch()
            except Exception as exc:
                json_response(
                    {"ok": False, "message": str(exc)}, "500 Internal Server Error"
                )


def normalize_base_path(path):
    if not path:
        return "/"
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized.rstrip("/") or "/"


def strip_base_path(path, base_path):
    normalized = path or "/"
    if base_path != "/" and normalized.startswith(base_path):
        normalized = normalized[len(base_path) :] or "/"
    return normalized


def current_request():
    return getattr(REQUEST_CONTEXT, "value", {})


@contextmanager
def request_context(method, query="", headers=None, body=b"", handler=None):
    previous = getattr(REQUEST_CONTEXT, "value", None)
    REQUEST_CONTEXT.value = {
        "method": (method or "GET").upper(),
        "query": query or "",
        "headers": headers or {},
        "body": body or b"",
        "handler": handler,
    }
    try:
        yield
    finally:
        if previous is None:
            if hasattr(REQUEST_CONTEXT, "value"):
                del REQUEST_CONTEXT.value
        else:
            REQUEST_CONTEXT.value = previous


def header_value(headers, name):
    if not headers:
        return ""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


def normalize_status(status):
    if isinstance(status, HTTPStatus):
        return status.value, f"{status.value} {status.phrase}"
    if isinstance(status, int):
        try:
            phrase = HTTPStatus(status).phrase
        except Exception:
            phrase = "OK"
        return status, f"{status} {phrase}"
    text = str(status or "200 OK").strip()
    if not text:
        return 200, "200 OK"
    first, _, rest = text.partition(" ")
    if first.isdigit():
        code = int(first)
        if not rest:
            try:
                rest = HTTPStatus(code).phrase
            except Exception:
                rest = ""
        return code, f"{code} {rest}".strip()
    return 200, "200 OK"


def json_response(payload, status="200 OK"):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    code, status_text = normalize_status(status)
    request = current_request()
    handler = request.get("handler", None)
    if handler is not None:
        try:
            handler.send_response(code)
            handler.send_header("Content-Type", "application/json; charset=utf-8")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            if handler.command != "HEAD":
                handler.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # client disconnected mid-response (e.g. gateway timeout / tab closed);
            # treat as normal and don't crash the request thread
            return
        return
    sys.stdout.write(f"Status: {status_text}\r\n")
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(body)


def sse_response():
    request = current_request()
    handler = request.get("handler", None)
    if handler is None:
        return None
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    return handler.wfile


def sse_send(wfile, event, data):
    payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    try:
        wfile.write(payload.encode("utf-8"))
        wfile.flush()
    except Exception:
        pass


def request_body():
    request = current_request()
    if request != {}:
        method = request.get("method", "GET").upper()
        body = request.get("body", b"") or b""
        query_string = request.get("query", "") or ""
        content_type = header_value(request.get("headers", {}), "Content-Type")
        if method in {"POST", "PUT", "PATCH"}:
            raw = body.decode("utf-8", "replace") if body else ""
            if "application/json" in content_type:
                return json.loads(raw or "{}")
            parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
            return {key: values[-1] for key, values in parsed.items()}
        parsed = urllib.parse.parse_qs(query_string, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    if method in {"POST", "PUT", "PATCH"}:
        length = int(os.environ.get("CONTENT_LENGTH") or 0)
        raw = sys.stdin.buffer.read(length).decode("utf-8", "replace") if length else ""
        content_type = os.environ.get("CONTENT_TYPE", "")
        if "application/json" in content_type:
            return json.loads(raw or "{}")
        parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}
    parsed = urllib.parse.parse_qs(
        os.environ.get("QUERY_STRING", ""), keep_blank_values=True
    )
    return {key: values[-1] for key, values in parsed.items()}


def read_text(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return default


def write_text(path, content, mode=0o644):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not (target.with_suffix(target.suffix + ".bak")).exists():
        try:
            target.with_suffix(target.suffix + ".bak").write_bytes(target.read_bytes())
        except Exception:
            pass
    target.write_text(content, encoding="utf-8")
    os.chmod(target, mode)


def run(cmd, timeout=30):
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def try_run_many(commands):
    results = []
    for cmd in commands:
        if not cmd[0] or not shutil_which(cmd[0]):
            continue
        result = run(cmd)
        results.append(result)
        if result["rc"] == 0:
            return [result]
    return results


def shutil_which(binary):
    for item in os.environ.get("PATH", "/usr/sbin:/usr/bin:/sbin:/bin").split(":"):
        candidate = Path(item) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(data):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def valid_iface_name(name):
    return bool(name and re.match(r"^[A-Za-z0-9_.:-]+$", str(name)))


def read_iface_addrs(name):
    result = run(["ip", "-j", "addr", "show", "dev", name], timeout=10)
    addrs = []
    try:
        for iface_info in json.loads(result["stdout"] or "[]"):
            for addr_info in iface_info.get("addr_info", []):
                if (
                    addr_info.get("family") in ("inet", "inet6")
                    and addr_info.get("scope") == "global"
                ):
                    addrs.append(
                        {
                            "family": addr_info["family"],
                            "address": addr_info.get("local", ""),
                            "prefixlen": addr_info.get("prefixlen", 0),
                        }
                    )
    except Exception:
        pass
    return addrs


def valid_bridge_name(name):
    return bool(name and re.match(r"^[A-Za-z0-9_.:-]+$", str(name)))


def clean_iface_name(name):
    return re.sub(r"[^A-Za-z0-9_.:-]", "", str(name or ""))


def normalize_network_state(state):
    raw = state.get("network", {})
    network = {}
    migrated_tcp = {}
    if isinstance(raw, dict):
        for name, cfg in raw.items():
            if name == "tcp" and isinstance(cfg, dict):
                migrated_tcp.update(cfg)
                continue
            if valid_iface_name(name) and isinstance(cfg, dict):
                network[name] = cfg
    if migrated_tcp and not isinstance(state.get("tcp"), dict):
        state["tcp"] = migrated_tcp
    state["network"] = network
    return network


def normalize_bridge_state(state):
    raw = state.get("bridges", {})
    bridges = {}
    if isinstance(raw, dict):
        for name, cfg in raw.items():
            if not valid_bridge_name(name):
                continue
            cfg = cfg if isinstance(cfg, dict) else {}
            members = []
            for member in cfg.get("members") or []:
                if valid_iface_name(member) and member not in members:
                    members.append(member)
            ip_type = str(cfg.get("ip_type") or "").strip()
            if ip_type not in ("dhcp", "static"):
                ip_type = ""
            bridge_type = str(cfg.get("bridge_type") or "").strip()
            if bridge_type not in ("linux", "ovs"):
                bridge_type = "linux"
            bridges[name] = {
                "bridge_type": bridge_type,
                "stp": bool(cfg.get("stp")),
                "members": members,
                "ip_type": ip_type,
                "ip4_type": str(cfg.get("ip4_type") or "").strip(),
                "ip6_type": str(cfg.get("ip6_type") or "").strip(),
                "ip_address": str(cfg.get("ip_address") or "").strip(),
                "ip_prefixlen": str(cfg.get("ip_prefixlen") or "").strip(),
                "ip_gateway": str(cfg.get("ip_gateway") or "").strip(),
                "ip_dns": str(cfg.get("ip_dns") or "").strip(),
                "ip_mtu": str(cfg.get("ip_mtu") or "").strip(),
                "ip6_address": str(cfg.get("ip6_address") or "").strip(),
                "ip6_prefixlen": str(cfg.get("ip6_prefixlen") or "").strip(),
                "ip6_gateway": str(cfg.get("ip6_gateway") or "").strip(),
                "ip6_dns": str(cfg.get("ip6_dns") or "").strip(),
            }
    state["bridges"] = bridges
    return bridges


def parse_kv_file(text, sep="="):
    parsed = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";") or sep not in line:
            continue
        key, value = line.split(sep, 1)
        parsed[key.strip()] = value.strip().strip('"')
    return parsed


def update_kv_lines(text, changes, *, sep="=", section=None, commented=True):
    lines = text.splitlines(True)
    out = []
    applied = set()
    current_section = None
    insert_at = None
    key_re = re.compile(r"^\s*#?\s*([A-Za-z0-9_.-]+)\s*" + re.escape(sep))
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and "]" in stripped:
            current_section = stripped[1 : stripped.index("]")]
            out.append(line)
            if current_section == section:
                insert_at = len(out)
            continue
        match = key_re.match(line)
        if match and (section is None or current_section == section):
            key = match.group(1)
            if key in changes:
                value = changes[key]
                applied.add(key)
                if value not in (None, ""):
                    prefix = "" if not commented else ""
                    q = '"' if sep == "=" and " " in str(value) else ""
                    out.append(f"{prefix}{key}{sep}{q}{value}{q}\n")
                continue
        out.append(line)
    missing = [
        key
        for key, value in changes.items()
        if key not in applied and value not in (None, "")
    ]
    if missing:
        insert = [
            f"{key}{sep}{value}\n" for key, value in changes.items() if key in missing
        ]
        if section and insert_at is None:
            out.extend([f"\n[{section}]\n"] + insert)
        elif section:
            out[insert_at:insert_at] = insert
        else:
            if out and not out[-1].endswith("\n"):
                out.append("\n")
            out.extend(insert)
    return "".join(out)


def read_service_active(name):
    result = (
        run(["systemctl", "is-active", name], timeout=8)
        if shutil_which("systemctl")
        else {"stdout": "unknown"}
    )
    return result.get("stdout") or "unknown"


def read_boot():
    text = read_text(PATHS["grub"])
    return {"content": text, "parsed": parse_kv_file(text), "path": str(PATHS["grub"])}


def save_boot(data):
    changes = data.get("changes") or {}
    content = data.get("content")
    source = content if content is not None else read_text(PATHS["grub"])
    write_text(PATHS["grub"], update_kv_lines(source, changes))
    results = []
    if data.get("apply"):
        results = try_run_many(
            [
                ["update-grub"],
                ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
                ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"],
            ]
        )
    if results:
        errors = [
            f'{r["cmd"]}: {r["stderr"] or r["stdout"] or "failed"}'
            for r in results
            if r.get("rc") != 0
        ]
        if errors:
            raise RuntimeError("; ".join(errors))
    return {"boot": read_boot(), "results": results}


POWER_FIELDS = [
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
]


def read_power():
    text = read_text(PATHS["logind"])
    return {
        "content": text,
        "parsed": parse_kv_file(text),
        "service": read_service_active("systemd-logind"),
    }


def save_power(data):
    changes = {
        key: (data.get("changes") or {}).get(key, "")
        for key in POWER_FIELDS
        if key in (data.get("changes") or {})
    }
    source = (
        data.get("content")
        if data.get("content") is not None
        else read_text(PATHS["logind"])
    )
    write_text(PATHS["logind"], update_kv_lines(source, changes, section="Login"))
    results = []
    if data.get("apply") and shutil_which("systemctl"):
        results.append(run(["systemctl", "restart", "systemd-logind"], timeout=20))
    if results:
        errors = [
            f'{r["cmd"]}: {r["stderr"] or r["stdout"] or "failed"}'
            for r in results
            if r.get("rc") != 0
        ]
        if errors:
            raise RuntimeError("; ".join(errors))
    return {"power": read_power(), "results": results}


SSH_FIELDS = [
    "PermitRootLogin",
    "PasswordAuthentication",
    "PubkeyAuthentication",
    "PermitEmptyPasswords",
    "PermitTTY",
    "X11Forwarding",
    "AllowTcpForwarding",
    "AllowAgentForwarding",
    "GatewayPorts",
]
SSH_DEFAULTS = {
    "PermitRootLogin": "prohibit-password",
    "PasswordAuthentication": "yes",
    "PubkeyAuthentication": "yes",
    "PermitEmptyPasswords": "no",
    "PermitTTY": "yes",
    "X11Forwarding": "no",
    "AllowTcpForwarding": "yes",
    "AllowAgentForwarding": "yes",
    "GatewayPorts": "no",
}
SSH_START_COMMANDS = [
    ["systemctl", "start", "ssh"],
    ["systemctl", "start", "sshd"],
    ["/etc/init.d/ssh", "start"],
]
SSH_RESTART_COMMANDS = [
    ["systemctl", "restart", "ssh"],
    ["systemctl", "restart", "sshd"],
    ["/etc/init.d/ssh", "restart"],
]


def ensure_sshd_runtime_dir():
    runtime_dir = Path("/run/sshd")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    os.chown(runtime_dir, 0, 0)  # pyright: ignore[reportAttributeAccessIssue]
    os.chmod(runtime_dir, 0o755)


def parse_sshd(text):
    parsed = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            parsed[parts[0]] = parts[1].strip()
    return parsed


def ensure_sshd_config():
    ensure_sshd_runtime_dir()
    PATHS["sshd_custom"].parent.mkdir(parents=True, exist_ok=True)
    if PATHS["sshd"].exists():
        return []
    results = try_run_many(SSH_START_COMMANDS)
    if PATHS["sshd"].exists():
        return results
    detail = "; ".join(
        f'{item["cmd"]}: {item["stderr"] or item["stdout"] or "failed"}'
        for item in results
        if item.get("rc") != 0
    )
    raise RuntimeError(
        f"{PATHS['sshd']} does not exist after starting SSH service"
        + (f": {detail}" if detail else "")
    )


def validate_sshd_content(content):
    sshd = shutil_which("sshd")
    if not sshd:
        return
    ensure_sshd_runtime_dir()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = run([sshd, "-t", "-f", tmp_path], timeout=10)
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass
    if result["rc"] != 0:
        raise RuntimeError(
            result["stderr"] or result["stdout"] or "invalid sshd config"
        )


def change_root_password(password):
    if "\n" in password or "\r" in password:
        raise RuntimeError("root password cannot contain line breaks")
    proc = subprocess.run(
        ["chpasswd"],
        input=f"root:{password}\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = {
        "cmd": "chpasswd root",
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    if proc.returncode != 0:
        raise RuntimeError(
            result["stderr"] or result["stdout"] or "failed to change root password"
        )
    return result


def save_sshd(data):
    results = ensure_sshd_config()
    changes = {
        key: str(value)
        for key, value in (data.get("changes") or {}).items()
        if key in SSH_FIELDS
    }
    if not changes and not data.get("password"):
        return {"ssh": read_ssh(), "results": results}
    custom_text = read_text(PATHS["sshd_custom"])
    for key, value in changes.items():
        pattern = re.compile(rf"^[#\s]*{re.escape(key)}\b.*$\n?", re.MULTILINE)
        custom_text = pattern.sub("", custom_text)
        custom_text = custom_text.rstrip() + "\n" + f"{key} {value}" + "\n"
    main_text = read_text(PATHS["sshd"])
    validate_sshd_content(main_text + "\n" + custom_text)
    if data.get("password"):
        results.append(change_root_password(str(data.get("password"))))
    write_text(PATHS["sshd_custom"], custom_text)
    # 持久化到应用数据目录：系统升级会还原 /etc/ssh，据此在 read_ssh 时恢复
    state = load_state()
    state["ssh"] = custom_text
    save_state(state)
    if data.get("apply"):
        results.extend(try_run_many(SSH_RESTART_COMMANDS))
    if results:
        errors = [
            f'{r["cmd"]}: {r["stderr"] or r["stdout"] or "failed"}'
            for r in results
            if r.get("rc") != 0
        ]
        if errors:
            raise RuntimeError("; ".join(errors))
    return {"ssh": read_ssh(), "results": results}


def read_ssh():
    text = read_text(PATHS["sshd"])
    custom_text = read_text(PATHS["sshd_custom"])
    if not custom_text.strip():
        # /etc/ssh/sshd_config.d/trim_sshd.conf 可能被系统升级覆盖/清除，从持久化的 STATE_FILE 恢复
        saved = (load_state().get("ssh") or "").strip()
        if saved:
            custom_text = saved
            try:
                PATHS["sshd_custom"].parent.mkdir(parents=True, exist_ok=True)
                write_text(PATHS["sshd_custom"], custom_text)
            except Exception:
                pass
    parsed = {k: SSH_DEFAULTS.get(k, "") for k in SSH_FIELDS if k in SSH_DEFAULTS}
    parsed.update(parse_sshd(text))
    parsed.update(parse_sshd(custom_text))
    return {
        "content": text,
        "custom": custom_text,
        "parsed": parsed,
        "service": read_service_active("sshd"),
    }


def _display_set_forced_off(name, off):
    state = load_state()
    lst = set(state.get("display_off") or [])
    if off:
        lst.add(name)
    else:
        lst.discard(name)
    state["display_off"] = sorted(lst)
    save_state(state)


def _display_is_forced_off(name):
    return name in (load_state().get("display_off") or [])


def read_display():
    displays = []
    drm_dir = Path("/sys/class/drm")
    if not drm_dir.exists():
        return {"displays": displays}
    for card in sorted(drm_dir.iterdir(), key=lambda p: p.name):
        if not card.is_dir():
            continue
        status_path = card / "status"
        if not status_path.exists():
            continue
        status = read_text(status_path).strip()
        if status not in ("connected", "disconnected"):
            continue
        name = card.name
        connector = name.split("-", 1)[1] if "-" in name else name
        info = {
            "name": name,
            "connector": connector,
            "status": status,
            "enabled": status == "connected",
        }
        modes_path = card / "modes"
        if modes_path.exists():
            info["modes"] = read_text(modes_path).strip().split("\n")
        else:
            info["modes"] = []
        edid_path = card / "edid"
        if edid_path.exists():
            edid_data = edid_path.read_bytes()
            if len(edid_data) >= 128:
                try:
                    mfg_id = (
                        chr(64 + ((edid_data[8] >> 2) & 0x1F))
                        + chr(
                            64
                            + (
                                ((edid_data[8] & 0x3) << 3)
                                | ((edid_data[9] >> 5) & 0x7)
                            )
                        )
                        + chr(64 + (edid_data[9] & 0x1F))
                    )
                    info["manufacturer"] = mfg_id
                except Exception:
                    info["manufacturer"] = ""
                product_code = int.from_bytes(edid_data[10:12], "little")
                info["product_code"] = str(product_code)
                serial = int.from_bytes(edid_data[12:16], "little")
                if serial:
                    info["serial"] = str(serial)
                week = edid_data[16]
                year = edid_data[17] + 1990 if edid_data[17] else 0
                if year:
                    info["manufacture_year"] = str(year)
                if week and week <= 54:
                    info["manufacture_week"] = str(week)
                h_cm = edid_data[21]
                v_cm = edid_data[22]
                if h_cm and v_cm:
                    info["size_cm"] = f"{h_cm}×{v_cm}"
                    diag_inch = round((h_cm**2 + v_cm**2) ** 0.5 / 2.54, 1)
                    info["size_inch"] = str(diag_inch)
                for offset in range(54, 108, 18):
                    if offset + 5 > len(edid_data):
                        break
                    tag = edid_data[offset]
                    if tag == 0xFC:
                        descriptor = edid_data[offset + 5 : offset + 18]
                        info["monitor_name"] = (
                            descriptor.decode("ascii", errors="replace")
                            .strip()
                            .rstrip("\n")
                            .rstrip()
                        )
                    elif tag == 0xFD:
                        min_v = edid_data[offset + 5]
                        max_v = edid_data[offset + 6]
                        min_h = edid_data[offset + 7]
                        max_h = edid_data[offset + 8]
                        if min_v and max_v:
                            info["vfreq_range"] = f"{min_v}-{max_v} Hz"
                        if min_h and max_h:
                            info["hfreq_range"] = f"{min_h}-{max_h} kHz"
                    elif tag == 0xFE:
                        descriptor = edid_data[offset + 5 : offset + 18]
                        info["serial_string"] = (
                            descriptor.decode("ascii", errors="replace")
                            .strip()
                            .rstrip("\n")
                            .rstrip()
                        )
                    elif tag == 0xFF:
                        descriptor = edid_data[offset + 5 : offset + 18]
                        info["serial_string"] = (
                            descriptor.decode("ascii", errors="replace")
                            .strip()
                            .rstrip("\n")
                            .rstrip()
                        )
                    elif tag == 0:
                        pixel_clk = int.from_bytes(
                            edid_data[offset : offset + 2], "little"
                        )
                        if pixel_clk:
                            h_active = int.from_bytes(
                                edid_data[offset + 2 : offset + 4], "little"
                            )
                            v_active = int.from_bytes(
                                edid_data[offset + 5 : offset + 7], "little"
                            )
                            if h_active and v_active:
                                info["native_resolution"] = f"{h_active}×{v_active}"
        dpms_path = card / "dpms"
        if dpms_path.exists():
            info["dpms"] = read_text(dpms_path).strip()
        enabled_path = card / "enabled"
        if enabled_path.exists():
            info["drm_enabled"] = read_text(enabled_path).strip()
        info["forced_off"] = _display_is_forced_off(name)
        dithering_path = card / "dithering"
        if dithering_path.exists():
            info["dithering"] = read_text(dithering_path).strip()
        parent_card = None
        for parent in card.parents:
            if re.match(r"card\d+$", parent.name) and (parent / "dev").exists():
                parent_card = parent
                break
        if parent_card:
            dev_str = read_text(parent_card / "dev").strip()
            m = re.match(r"\d+:(\d+)", dev_str)
            if m:
                drm_minor = m.group(1)
                force_path = Path(
                    f"/sys/kernel/debug/dri/{drm_minor}/{connector}/force"
                )
                if force_path.exists():
                    try:
                        info["drm_force"] = read_text(force_path).strip()
                    except Exception:
                        pass
        if "drm_force" not in info:
            for minor_dir in _drm_debug_dirs():
                force_path = minor_dir / connector / "force"
                if force_path.exists():
                    try:
                        info["drm_force"] = read_text(force_path).strip()
                    except Exception:
                        pass
                    break
        displays.append(info)
    return {"displays": displays}


def _drm_force_connector(name, on):
    connector = name.split("-", 1)[1] if "-" in name else name
    value = "unspecified" if on else "off"
    for minor_dir in _drm_debug_dirs():
        force_path = minor_dir / connector / "force"
        if force_path.exists():
            try:
                force_path.write_text(value, encoding="utf-8")
                return True
            except Exception:
                pass
    return False


def _drm_debug_dirs():
    debug_dir = Path("/sys/kernel/debug/dri")
    if not debug_dir.exists():
        return []
    try:
        return sorted(
            [p for p in debug_dir.iterdir() if p.is_dir()], key=lambda p: p.name
        )
    except Exception:
        return []


def _drm_read_dpms_states():
    result = {}
    import ctypes
    import ctypes.util

    libdrm_path = ctypes.util.find_library("drm")
    if not libdrm_path:
        return result
    try:
        libdrm = ctypes.CDLL(libdrm_path)
    except OSError:
        return result

    DRM_MODE_OBJECT_CONNECTOR = 0xC0C0C0C0

    libdrm.drmModeGetResources.restype = ctypes.c_void_p
    libdrm.drmModeGetResources.argtypes = [ctypes.c_int]
    libdrm.drmModeFreeResources.argtypes = [ctypes.c_void_p]
    libdrm.drmModeObjectGetProperties.restype = ctypes.c_void_p
    libdrm.drmModeObjectGetProperties.argtypes = [
        ctypes.c_int,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    libdrm.drmModeFreeObjectProperties.argtypes = [ctypes.c_void_p]
    libdrm.drmModeGetProperty.restype = ctypes.c_void_p
    libdrm.drmModeGetProperty.argtypes = [ctypes.c_int, ctypes.c_uint32]
    libdrm.drmModeFreeProperty.argtypes = [ctypes.c_void_p]

    class DrmModeRes(ctypes.Structure):
        _fields_ = [
            ("count_fbs", ctypes.c_int),
            ("fb_id_ptr", ctypes.c_uint64),
            ("count_crtcs", ctypes.c_int),
            ("crtc_id_ptr", ctypes.c_uint64),
            ("count_connectors", ctypes.c_int),
            ("connector_id_ptr", ctypes.c_uint64),
            ("count_encoders", ctypes.c_int),
            ("encoder_id_ptr", ctypes.c_uint64),
            ("min_width", ctypes.c_uint32),
            ("max_width", ctypes.c_uint32),
            ("min_height", ctypes.c_uint32),
            ("max_height", ctypes.c_uint32),
        ]

    class DrmModeObjProps(ctypes.Structure):
        _fields_ = [
            ("count_props", ctypes.c_int),
            ("props_ptr", ctypes.c_uint64),
            ("prop_values_ptr", ctypes.c_uint64),
        ]

    class DrmModeProp(ctypes.Structure):
        _fields_ = [
            ("prop_id", ctypes.c_uint32),
            ("flags", ctypes.c_uint32),
            ("name", ctypes.c_char * 32),
            ("count_values", ctypes.c_int),
            ("values_ptr", ctypes.c_uint64),
            ("count_enums", ctypes.c_int),
            ("enums_ptr", ctypes.c_uint64),
            ("count_blobs", ctypes.c_int),
            ("blob_ids_ptr", ctypes.c_uint64),
        ]

    for card_dev in sorted(Path("/dev/dri").glob("card*")):
        try:
            fd = os.open(
                str(card_dev),
                os.O_RDWR
                | os.O_NONBLOCK  # pyright: ignore[reportAttributeAccessIssue]
                | os.O_CLOEXEC,  # pyright: ignore[reportAttributeAccessIssue]
            )
        except OSError:
            continue
        try:
            res_ptr = libdrm.drmModeGetResources(fd)
            if not res_ptr:
                continue
            try:
                res = ctypes.cast(res_ptr, ctypes.POINTER(DrmModeRes)).contents
                if res.count_connectors <= 0 or not res.connector_id_ptr:
                    continue
                conn_ids = list(
                    ctypes.cast(
                        ctypes.c_void_p(res.connector_id_ptr),
                        ctypes.POINTER(ctypes.c_uint32 * res.count_connectors),
                    ).contents
                )
            finally:
                libdrm.drmModeFreeResources(res_ptr)

            for cid in conn_ids:
                props_ptr = libdrm.drmModeObjectGetProperties(
                    fd, cid, DRM_MODE_OBJECT_CONNECTOR
                )
                if not props_ptr:
                    continue
                try:
                    props = ctypes.cast(
                        props_ptr, ctypes.POINTER(DrmModeObjProps)
                    ).contents
                    if props.count_props <= 0 or not props.props_ptr:
                        continue
                    prop_ids = ctypes.cast(
                        ctypes.c_void_p(props.props_ptr),
                        ctypes.POINTER(ctypes.c_uint32 * props.count_props),
                    ).contents
                    prop_values = ctypes.cast(
                        ctypes.c_void_p(props.prop_values_ptr),
                        ctypes.POINTER(ctypes.c_uint64 * props.count_props),
                    ).contents
                    conn_name = None
                    dpms_val = None
                    for i in range(props.count_props):
                        prop_ptr = libdrm.drmModeGetProperty(fd, prop_ids[i])
                        if not prop_ptr:
                            continue
                        try:
                            prop = ctypes.cast(
                                prop_ptr, ctypes.POINTER(DrmModeProp)
                            ).contents
                            pname = prop.name.decode("utf-8", errors="replace")
                            if pname == "DPMS":
                                dpms_val = int(prop_values[i])
                        finally:
                            libdrm.drmModeFreeProperty(prop_ptr)
                    if dpms_val is not None:
                        result[cid] = dpms_val
                finally:
                    libdrm.drmModeFreeObjectProperties(props_ptr)
        finally:
            os.close(fd)
    return result


def _drm_get_card_dev(name):
    card_path = Path(f"/sys/class/drm/{name}")
    try:
        card_path = card_path.resolve()
    except Exception:
        pass
    for parent in card_path.parents:
        if re.match(r"card\d+$", parent.name) and (parent / "dev").exists():
            dev_str = read_text(parent / "dev").strip()
            m = re.match(r"\d+:(\d+)", dev_str)
            if m:
                minor = int(m.group(1))
                card_dev = Path(f"/dev/dri/card{minor}")
                if card_dev.exists():
                    return card_dev, minor
    return None, None


def _drm_dpms_control(name, on):
    card_dev, minor = _drm_get_card_dev(name)
    if not card_dev:
        return False, "DRM card device not found"
    connector_name = name.split("-", 1)[1] if "-" in name else name
    import ctypes
    import ctypes.util

    libdrm_path = ctypes.util.find_library("drm")
    if not libdrm_path:
        return False, "libdrm not found"
    try:
        libdrm = ctypes.CDLL(libdrm_path)
    except OSError:
        return False, "failed to load libdrm"

    fd = os.open(
        str(card_dev),
        os.O_RDWR | os.O_CLOEXEC,  # pyright: ignore[reportAttributeAccessIssue]
    )
    try:
        libdrm.drmSetMaster.restype = ctypes.c_int
        libdrm.drmSetMaster.argtypes = [ctypes.c_int]
        is_master = libdrm.drmSetMaster(fd) == 0

        DRM_MODE_OBJECT_CONNECTOR = 0xC0C0C0C0

        libdrm.drmModeGetResources.restype = ctypes.c_void_p
        libdrm.drmModeGetResources.argtypes = [ctypes.c_int]
        libdrm.drmModeFreeResources.argtypes = [ctypes.c_void_p]
        libdrm.drmModeObjectGetProperties.restype = ctypes.c_void_p
        libdrm.drmModeObjectGetProperties.argtypes = [
            ctypes.c_int,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        libdrm.drmModeFreeObjectProperties.argtypes = [ctypes.c_void_p]
        libdrm.drmModeGetProperty.restype = ctypes.c_void_p
        libdrm.drmModeGetProperty.argtypes = [ctypes.c_int, ctypes.c_uint32]
        libdrm.drmModeFreeProperty.argtypes = [ctypes.c_void_p]
        libdrm.drmModeConnectorSetProperty.restype = ctypes.c_int
        libdrm.drmModeConnectorSetProperty.argtypes = [
            ctypes.c_int,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint64,
        ]

        class DrmModeRes(ctypes.Structure):
            _fields_ = [
                ("count_fbs", ctypes.c_int),
                ("fb_id_ptr", ctypes.c_uint64),
                ("count_crtcs", ctypes.c_int),
                ("crtc_id_ptr", ctypes.c_uint64),
                ("count_connectors", ctypes.c_int),
                ("connector_id_ptr", ctypes.c_uint64),
                ("count_encoders", ctypes.c_int),
                ("encoder_id_ptr", ctypes.c_uint64),
                ("min_width", ctypes.c_uint32),
                ("max_width", ctypes.c_uint32),
                ("min_height", ctypes.c_uint32),
                ("max_height", ctypes.c_uint32),
            ]

        class DrmModeObjProps(ctypes.Structure):
            _fields_ = [
                ("count_props", ctypes.c_int),
                ("props_ptr", ctypes.c_uint64),
                ("prop_values_ptr", ctypes.c_uint64),
            ]

        class DrmModeProp(ctypes.Structure):
            _fields_ = [
                ("prop_id", ctypes.c_uint32),
                ("flags", ctypes.c_uint32),
                ("name", ctypes.c_char * 32),
                ("count_values", ctypes.c_int),
                ("values_ptr", ctypes.c_uint64),
                ("count_enums", ctypes.c_int),
                ("enums_ptr", ctypes.c_uint64),
                ("count_blobs", ctypes.c_int),
                ("blob_ids_ptr", ctypes.c_uint64),
            ]

        res_ptr = libdrm.drmModeGetResources(fd)
        if not res_ptr:
            return False, "drmModeGetResources failed"

        try:
            res = ctypes.cast(res_ptr, ctypes.POINTER(DrmModeRes)).contents
            if res.count_connectors <= 0 or not res.connector_id_ptr:
                return False, "no connectors found"
            conn_ids = list(
                ctypes.cast(
                    ctypes.c_void_p(res.connector_id_ptr),
                    ctypes.POINTER(ctypes.c_uint32 * res.count_connectors),
                ).contents
            )
        finally:
            libdrm.drmModeFreeResources(res_ptr)

        dpms_prop_id = None
        target_conn_id = None
        target_dir = Path(f"/sys/class/drm/card{minor}-{connector_name}")
        target_connector_id_file = target_dir / "connector_id"
        target_cid = None
        if target_connector_id_file.exists():
            try:
                target_cid = int(read_text(target_connector_id_file).strip())
            except Exception:
                pass
        for cid in conn_ids:
            if target_cid is not None and cid != target_cid:
                continue
            props_ptr = libdrm.drmModeObjectGetProperties(
                fd, cid, DRM_MODE_OBJECT_CONNECTOR
            )
            if not props_ptr:
                continue
            try:
                props = ctypes.cast(props_ptr, ctypes.POINTER(DrmModeObjProps)).contents
                if props.count_props <= 0 or not props.props_ptr:
                    continue
                prop_ids = ctypes.cast(
                    ctypes.c_void_p(props.props_ptr),
                    ctypes.POINTER(ctypes.c_uint32 * props.count_props),
                ).contents
                for i in range(props.count_props):
                    prop_ptr = libdrm.drmModeGetProperty(fd, prop_ids[i])
                    if not prop_ptr:
                        continue
                    try:
                        prop = ctypes.cast(
                            prop_ptr, ctypes.POINTER(DrmModeProp)
                        ).contents
                        pname = prop.name.decode("utf-8", errors="replace")
                        if pname == "DPMS":
                            dpms_prop_id = prop_ids[i]
                            target_conn_id = cid
                            break
                    finally:
                        libdrm.drmModeFreeProperty(prop_ptr)
                if dpms_prop_id:
                    break
            finally:
                libdrm.drmModeFreeObjectProperties(props_ptr)

        if not dpms_prop_id or not target_conn_id:
            return False, f"DPMS property not found for {connector_name}"

        dpms_value = 0 if on else 3
        dpms_label = "On" if on else "Off"
        ret = libdrm.drmModeConnectorSetProperty(
            fd, target_conn_id, dpms_prop_id, dpms_value
        )
        if ret != 0:
            if not is_master:
                return False, "drmSetMaster failed"
            return (
                False,
                f"drmModeConnectorSetProperty(DPMS={dpms_label}) returned {ret}",
            )

        if on:
            _drm_force_connector(name, True)

        return True, None
    finally:
        try:
            libdrm.drmDropMaster.restype = ctypes.c_int
            libdrm.drmDropMaster.argtypes = [ctypes.c_int]
            libdrm.drmDropMaster(fd)
        except Exception:
            pass
        os.close(fd)


def _fbdev_blank(on):
    any_ok = False
    for fb in sorted(Path("/sys/class/graphics").glob("fb*")):
        blank_path = fb / "blank"
        if blank_path.exists():
            try:
                blank_path.write_text("0" if on else "3", encoding="utf-8")
                any_ok = True
            except Exception:
                pass
    return any_ok


def _backlight_power(on):
    any_ok = False
    backlight_dir = Path("/sys/class/backlight")
    if not backlight_dir.exists():
        return False
    for bl in sorted(backlight_dir.iterdir()):
        bl_power = bl / "bl_power"
        if bl_power.exists():
            try:
                bl_power.write_text("0" if on else "1", encoding="utf-8")
                any_ok = True
            except Exception:
                pass
    return any_ok


def _display_apply_power(name, on, repeat=1, delay=0.35):
    any_ok = False
    last_err = None
    rounds = max(1, int(repeat))
    for idx in range(rounds):
        ok, err = _drm_dpms_control(name, on)
        if ok:
            any_ok = True
        elif err:
            last_err = err

        if on and _drm_force_connector(name, True):
            any_ok = True

        if _backlight_power(on):
            any_ok = True
        if _fbdev_blank(on):
            any_ok = True

        if not on and not any_ok and _drm_force_connector(name, False):
            any_ok = True

        if idx < rounds - 1:
            time.sleep(delay)
    return any_ok, last_err


def save_display(data):
    action = data.get("display_action")
    name = data.get("name")
    if not name:
        raise RuntimeError("display name is required")
    status_path = Path(f"/sys/class/drm/{name}/status")
    if not status_path.exists() or read_text(status_path).strip() != "connected":
        raise RuntimeError("display is not connected")
    target_on = action == "on"
    if not target_on:
        _display_set_forced_off(name, True)
    any_ok, last_err = _display_apply_power(
        name, target_on, repeat=4 if not target_on else 1
    )
    if not any_ok and not target_on:
        _display_set_forced_off(name, False)
        if last_err:
            raise RuntimeError(last_err)
        raise RuntimeError(
            "No available method to control display power (need DRM DPMS, DRM debugfs, backlight, or fbdev)"
        )
    if target_on:
        _display_set_forced_off(name, False)
    write_display_service()
    return {"display": read_display()}


def write_display_service():
    off_names = sorted(load_state().get("display_off") or [])
    if off_names:
        module_path = Path(__file__).resolve()
        script = f"""#!/usr/bin/env python3
import importlib.util
import sys

module_path = Path({repr(str(module_path))})
off_names = {repr(off_names)}
if not off_names:
    sys.exit(0)

spec = importlib.util.spec_from_file_location('fn_advancedsettings_display', module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name in off_names:
    mod._display_apply_power(name, False, repeat=6, delay=0.5)
"""
        DISPLAY_APPLY.write_text(script, encoding="utf-8")
    else:
        DISPLAY_APPLY.write_text(
            "#!/bin/sh\n# No displays forced off\n", encoding="utf-8"
        )
    os.chmod(DISPLAY_APPLY, 0o755)
    DISPLAY_SERVICE.write_text(
        """[Unit]
Description=Apply fn advanced display DPMS settings
After=sysinit.target display-manager.service graphical.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fn-advancedsettings-display-apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""",
        encoding="utf-8",
    )
    if shutil_which("systemctl"):
        run(["systemctl", "daemon-reload"], timeout=15)
        run(["systemctl", "enable", "fn-advancedsettings-display.service"], timeout=15)


def read_cpu():
    cpus = []
    policies = []
    for cpu in sorted(
        Path("/sys/devices/system/cpu").glob("cpu[0-9]*"), key=lambda p: int(p.name[3:])
    ):
        gov_path = cpu / "cpufreq/scaling_governor"
        if gov_path.exists():
            cpu_info = {
                "name": cpu.name,
                "min_freq": read_text(cpu / "cpufreq/scaling_min_freq").strip(),
                "max_freq": read_text(cpu / "cpufreq/scaling_max_freq").strip(),
                "cur_freq": read_text(cpu / "cpufreq/scaling_cur_freq").strip(),
                "governor": read_text(gov_path).strip(),
                "available_governors": read_text(
                    cpu / "cpufreq/scaling_available_governors"
                )
                .strip()
                .split(),
                "scaling_driver": read_text(cpu / "cpufreq/scaling_driver").strip(),
            }
            epp_path = cpu / "cpufreq/energy_performance_preference"
            if epp_path.exists():
                cpu_info["epp"] = read_text(epp_path).strip()
                cpu_info["available_epp"] = (
                    read_text(cpu / "cpufreq/energy_performance_available_preferences")
                    .strip()
                    .split()
                )
            boost_path = cpu / "cpufreq/boost"
            if boost_path.exists():
                cpu_info["boost"] = read_text(boost_path).strip()
            cpus.append(cpu_info)
    policy_root = Path("/sys/devices/system/cpu/cpufreq")
    for policy in sorted(policy_root.glob("policy*"), key=lambda p: int(p.name[6:])):
        policy_info = {
            "name": policy.name,
            "min_freq": read_text(policy / "scaling_min_freq").strip(),
            "max_freq": read_text(policy / "scaling_max_freq").strip(),
            "cur_freq": read_text(policy / "scaling_cur_freq").strip()
            or read_text(policy / "cpuinfo_cur_freq").strip(),
            "governor": read_text(policy / "scaling_governor").strip(),
            "available_governors": read_text(policy / "scaling_available_governors")
            .strip()
            .split(),
            "scaling_driver": read_text(policy / "scaling_driver").strip(),
        }
        epp_path = policy / "energy_performance_preference"
        if epp_path.exists():
            policy_info["epp"] = read_text(epp_path).strip()
            policy_info["available_epp"] = (
                read_text(policy / "energy_performance_available_preferences")
                .strip()
                .split()
            )
        boost_path = policy / "boost"
        if boost_path.exists():
            policy_info["boost"] = read_text(boost_path).strip()
        policies.append(policy_info)
    extra = {}
    intel_pstate_dir = Path("/sys/devices/system/cpu/intel_pstate")
    if intel_pstate_dir.exists():
        extra["intel_pstate"] = True
        extra["intel_pstate_status"] = read_text(intel_pstate_dir / "status").strip()
        no_turbo_path = intel_pstate_dir / "no_turbo"
        if no_turbo_path.exists():
            extra["no_turbo"] = read_text(no_turbo_path).strip()
    amd_pstate_dir = Path("/sys/devices/system/cpu/amd_pstate")
    if amd_pstate_dir.exists():
        extra["amd_pstate"] = True
        extra["amd_pstate_status"] = read_text(amd_pstate_dir / "status").strip()
        prefcore_path = amd_pstate_dir / "prefcore"
        if prefcore_path.exists():
            extra["amd_pstate_prefcore"] = read_text(prefcore_path).strip()
    global_boost_path = Path("/sys/devices/system/cpu/cpufreq/boost")
    if global_boost_path.exists():
        extra["boost"] = read_text(global_boost_path).strip()
    return {"cpus": cpus, "policies": policies, "extra": extra}


def save_cpu(data):
    settings = data.get("settings") or {}
    targets = list(Path("/sys/devices/system/cpu/cpufreq").glob("policy*")) or [
        p / "cpufreq" for p in Path("/sys/devices/system/cpu").glob("cpu[0-9]*")
    ]
    errors = []
    for target in targets:
        for key, path_name in (
            ("min_freq", "scaling_min_freq"),
            ("max_freq", "scaling_max_freq"),
        ):
            if settings.get(key):
                ok, msg = write_sysfs(target / path_name, settings[key])
                if not ok:
                    errors.append(f"{target}: {msg}")
        if settings.get("governor"):
            ok, msg = write_sysfs(target / "scaling_governor", settings["governor"])
            if not ok:
                errors.append(f"{target}: {msg}")
        if settings.get("epp") and (target / "energy_performance_preference").exists():
            ok, msg = write_sysfs(
                target / "energy_performance_preference", settings["epp"]
            )
            if not ok:
                errors.append(f"{target} epp: {msg}")
    if settings.get("boost") is not None:
        boost_path = Path("/sys/devices/system/cpu/cpufreq/boost")
        if boost_path.exists():
            ok, msg = write_sysfs(boost_path, settings["boost"])
            if not ok:
                errors.append(f"boost: {msg}")
    if settings.get("no_turbo") is not None:
        no_turbo_path = Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
        if no_turbo_path.exists():
            ok, msg = write_sysfs(no_turbo_path, settings["no_turbo"])
            if not ok:
                errors.append(f"no_turbo: {msg}")
    if settings.get("amd_pstate_prefcore") is not None:
        prefcore_path = Path("/sys/devices/system/cpu/amd_pstate/prefcore")
        if prefcore_path.exists():
            ok, msg = write_sysfs(prefcore_path, settings["amd_pstate_prefcore"])
            if not ok:
                errors.append(f"amd_pstate_prefcore: {msg}")
    state = load_state()
    state["cpu"] = settings
    save_state(state)
    write_cpu_service(settings)
    if errors:
        raise RuntimeError("; ".join(errors))
    return {"cpu": read_cpu()}


def write_cpu_service(settings):
    lines = [
        "#!/bin/sh",
        "set -eu",
        'targets="/sys/devices/system/cpu/cpufreq/policy*"',
        "found=0",
    ]
    lines.append(
        'for target in $targets; do [ -d "$target" ] && found=1 && break; done'
    )
    lines.append(
        'if [ "$found" -eq 0 ]; then targets="/sys/devices/system/cpu/cpu[0-9]*/cpufreq"; fi'
    )
    lines.append("for target in $targets; do")
    lines.append('  [ -d "$target" ] || continue')
    if settings.get("min_freq"):
        lines.append(
            f"  [ -w \"$target/scaling_min_freq\" ] && printf '%s' {shell_quote(settings['min_freq'])} > \"$target/scaling_min_freq\" || true"
        )
    if settings.get("max_freq"):
        lines.append(
            f"  [ -w \"$target/scaling_max_freq\" ] && printf '%s' {shell_quote(settings['max_freq'])} > \"$target/scaling_max_freq\" || true"
        )
    if settings.get("governor"):
        lines.append(
            f"  [ -w \"$target/scaling_governor\" ] && printf '%s' {shell_quote(settings['governor'])} > \"$target/scaling_governor\" || true"
        )
    if settings.get("epp"):
        lines.append(
            f"  [ -w \"$target/energy_performance_preference\" ] && printf '%s' {shell_quote(settings['epp'])} > \"$target/energy_performance_preference\" || true"
        )
    lines.append("done")
    if settings.get("boost") is not None:
        lines.append(
            f"[ -w /sys/devices/system/cpu/cpufreq/boost ] && printf '%s' {shell_quote(str(settings['boost']))} > /sys/devices/system/cpu/cpufreq/boost || true"
        )
    if settings.get("no_turbo") is not None:
        lines.append(
            f"[ -w /sys/devices/system/cpu/intel_pstate/no_turbo ] && printf '%s' {shell_quote(str(settings['no_turbo']))} > /sys/devices/system/cpu/intel_pstate/no_turbo || true"
        )
    if settings.get("amd_pstate_prefcore") is not None:
        lines.append(
            f"[ -w /sys/devices/system/cpu/amd_pstate/prefcore ] && printf '%s' {shell_quote(str(settings['amd_pstate_prefcore']))} > /sys/devices/system/cpu/amd_pstate/prefcore || true"
        )
    CPU_APPLY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(CPU_APPLY, 0o755)
    CPU_SERVICE.write_text(
        """[Unit]
Description=Apply fn advanced CPU settings
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fn-advancedsettings-cpu-apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""",
        encoding="utf-8",
    )
    if shutil_which("systemctl"):
        run(["systemctl", "daemon-reload"], timeout=15)
        run(["systemctl", "enable", "fn-advancedsettings-cpu.service"], timeout=15)


def write_sysfs(path, value):
    try:
        Path(path).write_text(str(value), encoding="utf-8")
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def read_dns():
    return {"resolv": read_text(PATHS["resolv"]), "hosts": read_text(PATHS["hosts"])}


def save_dns(data):
    if "resolv" in data:
        write_text(PATHS["resolv"], str(data.get("resolv") or ""))
    if "hosts" in data:
        write_text(PATHS["hosts"], str(data.get("hosts") or ""))
    return {"dns": read_dns()}


def ethtool_value(iface, flag):
    if not shutil_which("ethtool"):
        return ""
    result = run(["ethtool", iface], timeout=8)
    if result["rc"] != 0:
        return ""
    match = re.search(
        rf"^\s*{re.escape(flag)}:\s*(.+)$", result["stdout"], re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def ethtool_info(iface):
    if not shutil_which("ethtool"):
        return {}
    result = run(["ethtool", iface], timeout=8)
    if result["rc"] != 0:
        return {}
    text = result["stdout"]
    info = {}
    for key in ["Speed", "Duplex", "Auto-negotiation", "Wake-on", "Supports Wake-on"]:
        match = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
        info[key] = match.group(1).strip() if match else ""
    modes = parse_ethtool_link_modes(
        text, "Supported link modes"
    ) or parse_ethtool_link_modes(text, "Advertised link modes")
    info["supported_link_modes"] = modes
    return info


def parse_ethtool_link_modes(text, title):
    modes = []
    in_modes = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith(f"{title}:"):
            in_modes = True
            stripped = stripped.split(":", 1)[1].strip()
        elif in_modes and re.match(r"^[A-Za-z][A-Za-z -]+:", stripped):
            break
        if in_modes:
            for speed, duplex in re.findall(r"(\d+)base\S*/(Half|Full)", stripped):
                item = {"speed": speed, "duplex": duplex.lower()}
                if item not in modes:
                    modes.append(item)
    return modes


def read_tcp():
    global TCP_MODULES_PROBED
    tcp = {}
    cc_path = Path("/proc/sys/net/ipv4/tcp_congestion_control")
    avail_path = Path("/proc/sys/net/ipv4/tcp_available_congestion_control")
    if cc_path.exists():
        tcp["congestion_control"] = read_text(cc_path).strip()
    if avail_path.exists():
        for mod in (
            []
            if TCP_MODULES_PROBED
            else [
                "tcp_bbr",
                "tcp_bbr2",
                "tcp_dctcp",
                "tcp_cdg",
                "tcp_nv",
                "tcp_veno",
                "tcp_westwood",
                "tcp_htcp",
                "tcp_hybla",
                "tcp_scalable",
                "tcp_lp",
                "tcp_yeah",
                "tcp_illinois",
            ]
        ):
            if shutil_which("modprobe"):
                run(["modprobe", mod], timeout=5)
        TCP_MODULES_PROBED = True
        tcp["available_congestion_control"] = read_text(avail_path).strip().split()
    fastopen_path = Path("/proc/sys/net/ipv4/tcp_fastopen")
    if fastopen_path.exists():
        tcp["fastopen"] = read_text(fastopen_path).strip()
    syncookies_path = Path("/proc/sys/net/ipv4/tcp_syncookies")
    if syncookies_path.exists():
        tcp["syncookies"] = read_text(syncookies_path).strip()
    tw_reuse_path = Path("/proc/sys/net/ipv4/tcp_tw_reuse")
    if tw_reuse_path.exists():
        tcp["tw_reuse"] = read_text(tw_reuse_path).strip()
    fin_timeout_path = Path("/proc/sys/net/ipv4/tcp_fin_timeout")
    if fin_timeout_path.exists():
        tcp["fin_timeout"] = read_text(fin_timeout_path).strip()
    keepalive_time_path = Path("/proc/sys/net/ipv4/tcp_keepalive_time")
    if keepalive_time_path.exists():
        tcp["keepalive_time"] = read_text(keepalive_time_path).strip()
    sack_path = Path("/proc/sys/net/ipv4/tcp_sack")
    if sack_path.exists():
        tcp["sack"] = read_text(sack_path).strip()
    timestamps_path = Path("/proc/sys/net/ipv4/tcp_timestamps")
    if timestamps_path.exists():
        tcp["timestamps"] = read_text(timestamps_path).strip()
    window_scaling_path = Path("/proc/sys/net/ipv4/tcp_window_scaling")
    if window_scaling_path.exists():
        tcp["window_scaling"] = read_text(window_scaling_path).strip()
    mtu_probing_path = Path("/proc/sys/net/ipv4/tcp_mtu_probing")
    if mtu_probing_path.exists():
        tcp["mtu_probing"] = read_text(mtu_probing_path).strip()
    return tcp


def list_network():
    items = []
    state = load_state()
    network = normalize_network_state(state)
    bridges = normalize_bridge_state(state)
    saved = dict(network)
    if isinstance(state.get("tcp"), dict):
        saved["tcp"] = state["tcp"]
    for iface in sorted(Path("/sys/class/net").iterdir(), key=lambda p: p.name):
        if iface.name == "lo":
            continue
        ethtool = ethtool_info(iface.name)
        speed = (ethtool.get("Speed") or "").replace("Mb/s", "").strip() or read_text(
            iface / "speed"
        ).strip()
        items.append(
            {
                "name": iface.name,
                "mac": read_text(iface / "address").strip(),
                "mtu": read_text(iface / "mtu").strip(),
                "operstate": read_text(iface / "operstate").strip(),
                "speed": speed,
                "duplex": (ethtool.get("Duplex") or "").lower(),
                "autoneg": (
                    "on"
                    if (ethtool.get("Auto-negotiation") or "").lower() == "on"
                    else "off"
                ),
                "wol": ethtool.get("Wake-on") or "",
                "supported_wol": ethtool.get("Supports Wake-on") or "",
                "supported_link_modes": ethtool.get("supported_link_modes") or [],
            }
        )
    return {
        "interfaces": items,
        "saved": saved,
        "saved_bridges": bridges,
        "bridges": read_bridges(),
        "available_ifaces": [i["name"] for i in items],
        "tcp": read_tcp(),
    }


BRIDGE_PORT_STATES = {
    0: "disabled",
    1: "listening",
    2: "learning",
    3: "forwarding",
    4: "blocking",
}


def read_ovs_bridges():
    bridges = []
    ovs_vsctl = shutil_which("ovs-vsctl")
    if not ovs_vsctl:
        return bridges
    try:
        result = run([ovs_vsctl, "list-br"], timeout=10)
        if result.get("rc") != 0:
            return bridges
        for line in (result.get("stdout") or "").splitlines():
            name = line.strip()
            if not name:
                continue
            stp = False
            try:
                stp_result = run(
                    [ovs_vsctl, "get", "Bridge", name, "stp_enable"], timeout=5
                )
                stp = stp_result.get("stdout", "").strip().lower() == "true"
            except Exception:
                pass
            members = []
            try:
                port_result = run([ovs_vsctl, "list-ports", name], timeout=5)
                for pname in (port_result.get("stdout") or "").splitlines():
                    pname = pname.strip()
                    if pname:
                        members.append(
                            {
                                "name": pname,
                                "state": "forwarding",
                                "priority": "-",
                                "cost": "-",
                            }
                        )
            except Exception:
                pass
            bridges.append(
                {
                    "name": name,
                    "type": "ovs",
                    "stp": stp,
                    "forward_delay": "-",
                    "hello_time": "-",
                    "max_age": "-",
                    "vlan_filtering": False,
                    "default_pvid": "1",
                    "members": members,
                    "addrs": read_iface_addrs(name),
                }
            )
    except Exception:
        pass
    return bridges


def read_bridges():
    bridges = []
    linux_names = set()
    for bridge_dir in sorted(Path("/sys/class/net").glob("*/bridge")):
        iface_dir = bridge_dir.parent
        name = iface_dir.name
        linux_names.add(name)
        stp = read_text(bridge_dir / "stp_state").strip()
        forward_delay = read_text(bridge_dir / "forward_delay").strip()
        hello_time = read_text(bridge_dir / "hello_time").strip()
        max_age = read_text(bridge_dir / "max_age").strip()
        vlan_filtering = (
            read_text(bridge_dir / "vlan_filtering").strip()
            if (bridge_dir / "vlan_filtering").exists()
            else "0"
        )
        default_pvid = (
            read_text(bridge_dir / "default_pvid").strip()
            if (bridge_dir / "default_pvid").exists()
            else "1"
        )
        members = []
        brif_dir = iface_dir / "brif"
        if brif_dir.exists():
            for member_dir in sorted(brif_dir.iterdir()):
                if not member_dir.is_dir():
                    continue
                mname = member_dir.name
                state_val = (
                    read_text(member_dir / "state").strip()
                    if (member_dir / "state").exists()
                    else ""
                )
                state_name = BRIDGE_PORT_STATES.get(
                    int(state_val) if state_val.isdigit() else -1,
                    state_val or "unknown",
                )
                priority = (
                    read_text(member_dir / "priority").strip()
                    if (member_dir / "priority").exists()
                    else "32"
                )
                cost = (
                    read_text(member_dir / "path_cost").strip()
                    if (member_dir / "path_cost").exists()
                    else "0"
                )
                members.append(
                    {
                        "name": mname,
                        "state": state_name,
                        "priority": priority,
                        "cost": cost,
                    }
                )
        bridges.append(
            {
                "name": name,
                "type": "linux",
                "stp": stp == "1",
                "forward_delay": forward_delay,
                "hello_time": hello_time,
                "max_age": max_age,
                "vlan_filtering": vlan_filtering == "1",
                "default_pvid": default_pvid,
                "members": members,
                "addrs": read_iface_addrs(name),
            }
        )
    for ovs_bridge in read_ovs_bridges():
        if ovs_bridge["name"] not in linux_names:
            bridges.append(ovs_bridge)
    return bridges


def save_bridge(data):
    results = []
    action = data.get("bridge_action")
    state = load_state()
    normalize_network_state(state)
    bridges = normalize_bridge_state(state)
    if action == "create":
        name = str(data.get("name") or "").strip()
        if not valid_bridge_name(name):
            raise RuntimeError("Invalid bridge name")
        if (Path("/sys/class/net") / name).exists():
            raise RuntimeError(f"Interface {name} already exists")
        bridge_type = str(data.get("bridge_type") or "linux").strip()
        if bridge_type not in ("linux", "ovs"):
            bridge_type = "linux"
        if bridge_type == "ovs":
            ovs_vsctl = shutil_which("ovs-vsctl")
            if not ovs_vsctl:
                raise RuntimeError("ovs-vsctl not found, Open vSwitch is not installed")
            results.append(run([ovs_vsctl, "add-br", name], timeout=15))
            stp = bool(data.get("stp"))
            if stp:
                results.append(
                    run(
                        [ovs_vsctl, "set", "Bridge", name, "stp_enable=true"],
                        timeout=10,
                    )
                )
            results.append(run(["ip", "link", "set", name, "up"], timeout=10))
        else:
            results.append(
                run(["ip", "link", "add", "name", name, "type", "bridge"], timeout=15)
            )
            stp = bool(data.get("stp"))
            if stp:
                stp_path = Path(f"/sys/class/net/{name}/bridge/stp_state")
                if stp_path.exists():
                    try:
                        stp_path.write_text("1", encoding="utf-8")
                    except Exception:
                        results.append(
                            run(
                                [
                                    "ip",
                                    "link",
                                    "set",
                                    name,
                                    "type",
                                    "bridge",
                                    "stp_state",
                                    "1",
                                ],
                                timeout=10,
                            )
                        )
            results.append(run(["ip", "link", "set", name, "up"], timeout=10))
        bridges[name] = {
            "bridge_type": bridge_type,
            "stp": stp,
            "members": [],
            "ip_type": "",
            "ip4_type": "",
            "ip6_type": "",
            "ip_address": "",
            "ip_prefixlen": "",
            "ip_gateway": "",
            "ip_dns": "",
            "ip_mtu": "",
            "ip6_address": "",
            "ip6_prefixlen": "",
            "ip6_gateway": "",
            "ip6_dns": "",
        }
    elif action == "delete":
        name = str(data.get("name") or "").strip()
        if not name:
            raise RuntimeError("Bridge name is required")
        saved_cfg = bridges.get(name, {})
        bridge_type = (
            saved_cfg.get("bridge_type") or str(data.get("bridge_type") or "").strip()
        )
        if bridge_type not in ("linux", "ovs"):
            bridge_type = (
                "ovs"
                if (
                    Path(f"/sys/class/net/{name}/bridge").exists() is False
                    and shutil_which("ovs-vsctl")
                )
                else "linux"
            )
        if bridge_type == "ovs" and shutil_which("ovs-vsctl"):
            results.append(run(["ip", "link", "set", name, "down"], timeout=10))
            results.append(run([shutil_which("ovs-vsctl"), "del-br", name], timeout=15))
        else:
            results.append(run(["ip", "link", "set", name, "down"], timeout=10))
            results.append(run(["ip", "link", "del", name], timeout=15))
        bridges.pop(name, None)
    elif action == "add_member":
        name = str(data.get("name") or "").strip()
        member = str(data.get("member") or "").strip()
        if not valid_bridge_name(name) or not valid_iface_name(member):
            raise RuntimeError("Bridge name and member are required")
        saved_cfg = bridges.get(name, {})
        bridge_type = (
            saved_cfg.get("bridge_type") or str(data.get("bridge_type") or "").strip()
        )
        if bridge_type not in ("linux", "ovs"):
            bridge_type = (
                "ovs"
                if (
                    Path(f"/sys/class/net/{name}/bridge").exists() is False
                    and shutil_which("ovs-vsctl")
                )
                else "linux"
            )
        if bridge_type == "ovs" and shutil_which("ovs-vsctl"):
            results.append(run(["ip", "link", "set", member, "up"], timeout=10))
            results.append(
                run([shutil_which("ovs-vsctl"), "add-port", name, member], timeout=10)
            )
        else:
            results.append(
                run(["ip", "link", "set", member, "master", name], timeout=10)
            )
        if name in bridges:
            members = bridges[name].setdefault("members", [])
            if member not in members:
                members.append(member)
    elif action == "remove_member":
        name = str(data.get("name") or "").strip()
        member = str(data.get("member") or "").strip()
        if not valid_bridge_name(name) or not valid_iface_name(member):
            raise RuntimeError("Bridge name and member are required")
        saved_cfg = bridges.get(name, {})
        bridge_type = (
            saved_cfg.get("bridge_type") or str(data.get("bridge_type") or "").strip()
        )
        if bridge_type not in ("linux", "ovs"):
            bridge_type = (
                "ovs"
                if (
                    Path(f"/sys/class/net/{name}/bridge").exists() is False
                    and shutil_which("ovs-vsctl")
                )
                else "linux"
            )
        if bridge_type == "ovs" and shutil_which("ovs-vsctl"):
            results.append(
                run([shutil_which("ovs-vsctl"), "del-port", name, member], timeout=10)
            )
        else:
            results.append(run(["ip", "link", "set", member, "nomaster"], timeout=10))
        if name in bridges:
            bridges[name].setdefault("members", [])
            if member in bridges[name]["members"]:
                bridges[name]["members"].remove(member)
    elif action == "update_ip":
        name = str(data.get("name") or "").strip()
        if not valid_bridge_name(name):
            raise RuntimeError("Bridge name is required")
        ip4_type = str(data.get("ip4_type") or "").strip()
        if ip4_type not in ("dhcp", "static"):
            ip4_type = ""
        ip6_type = str(data.get("ip6_type") or "").strip()
        if ip6_type not in ("dhcp", "static"):
            ip6_type = ""
        ip_address = str(data.get("ip_address") or "").strip()
        ip_prefixlen = str(data.get("ip_prefixlen") or "24").strip()
        ip_gateway = str(data.get("ip_gateway") or "").strip()
        ip_dns = str(data.get("ip_dns") or "").strip()
        ip_mtu = str(data.get("ip_mtu") or "").strip()
        ip6_address = str(data.get("ip6_address") or "").strip()
        ip6_prefixlen = str(data.get("ip6_prefixlen") or "64").strip()
        ip6_gateway = str(data.get("ip6_gateway") or "").strip()
        ip6_dns = str(data.get("ip6_dns") or "").strip()
        stp = data.get("stp")
        saved_cfg = bridges.get(name, {})
        bridge_type = (
            saved_cfg.get("bridge_type") or str(data.get("bridge_type") or "").strip()
        )
        if bridge_type not in ("linux", "ovs"):
            bridge_type = (
                "ovs"
                if (
                    Path(f"/sys/class/net/{name}/bridge").exists() is False
                    and shutil_which("ovs-vsctl")
                )
                else "linux"
            )
        if stp is not None:
            stp = bool(stp)
            if bridge_type == "ovs" and shutil_which("ovs-vsctl"):
                results.append(
                    run(
                        [
                            shutil_which("ovs-vsctl"),
                            "set",
                            "Bridge",
                            name,
                            f"stp_enable={'true' if stp else 'false'}",
                        ],
                        timeout=10,
                    )
                )
            else:
                stp_path = Path(f"/sys/class/net/{name}/bridge/stp_state")
                if stp_path.exists():
                    try:
                        stp_path.write_text("1" if stp else "0", encoding="utf-8")
                    except Exception:
                        results.append(
                            run(
                                [
                                    "ip",
                                    "link",
                                    "set",
                                    name,
                                    "type",
                                    "bridge",
                                    "stp_state",
                                    "1" if stp else "0",
                                ],
                                timeout=10,
                            )
                        )
                else:
                    results.append(
                        run(
                            [
                                "ip",
                                "link",
                                "set",
                                name,
                                "type",
                                "bridge",
                                "stp_state",
                                "1" if stp else "0",
                            ],
                            timeout=10,
                        )
                    )
        results.append(
            run(["ip", "addr", "flush", "dev", name, "scope", "global"], timeout=10)
        )
        if ip_mtu:
            results.append(run(["ip", "link", "set", name, "mtu", ip_mtu], timeout=10))
        if ip4_type == "static":
            if ip_address:
                results.append(
                    run(
                        [
                            "ip",
                            "addr",
                            "add",
                            f"{ip_address}/{ip_prefixlen or '24'}",
                            "dev",
                            name,
                        ],
                        timeout=10,
                    )
                )
            if ip_gateway:
                results.append(
                    run(
                        [
                            "ip",
                            "route",
                            "replace",
                            "default",
                            "via",
                            ip_gateway,
                            "dev",
                            name,
                        ],
                        timeout=10,
                    )
                )
        elif ip4_type == "dhcp":
            if shutil_which("dhclient"):
                results.append(run(["dhclient", "-1", "-4", name], timeout=30))
            elif shutil_which("udhcpc"):
                results.append(run(["udhcpc", "-i", name, "-n", "-q"], timeout=30))
        if ip6_type == "static":
            if ip6_address:
                results.append(
                    run(
                        [
                            "ip",
                            "addr",
                            "add",
                            f"{ip6_address}/{ip6_prefixlen or '64'}",
                            "dev",
                            name,
                        ],
                        timeout=10,
                    )
                )
            if ip6_gateway:
                results.append(
                    run(
                        [
                            "ip",
                            "-6",
                            "route",
                            "replace",
                            "default",
                            "via",
                            ip6_gateway,
                            "dev",
                            name,
                        ],
                        timeout=10,
                    )
                )
        elif ip6_type == "dhcp":
            if shutil_which("dhclient"):
                results.append(run(["dhclient", "-1", "-6", name], timeout=30))
            elif shutil_which("udhcpc"):
                results.append(run(["udhcpc", "-i", name, "-n", "-q"], timeout=30))
        dns_servers = []
        if ip4_type == "static":
            for ns in ip_dns.split(","):
                ns = ns.strip()
                if ns:
                    dns_servers.append(ns)
        if ip6_type == "static":
            for ns in ip6_dns.split(","):
                ns = ns.strip()
                if ns:
                    dns_servers.append(ns)
        if dns_servers:
            resolv_content = (
                "\n".join([f"nameserver {ns}" for ns in dns_servers]) + "\n"
            )
            try:
                Path("/etc/resolv.conf").write_text(resolv_content, encoding="utf-8")
            except Exception:
                pass
        if name not in bridges:
            bridges[name] = {
                "bridge_type": bridge_type,
                "stp": False,
                "members": [],
                "ip_type": "",
                "ip4_type": "",
                "ip6_type": "",
                "ip_address": "",
                "ip_prefixlen": "",
                "ip_gateway": "",
                "ip_dns": "",
                "ip_mtu": "",
                "ip6_address": "",
                "ip6_prefixlen": "",
                "ip6_gateway": "",
                "ip6_dns": "",
            }
        if stp is not None:
            bridges[name]["stp"] = stp
        bridges[name]["bridge_type"] = bridge_type
        bridges[name]["ip_type"] = ip4_type or ip6_type or ""
        bridges[name]["ip4_type"] = ip4_type
        bridges[name]["ip6_type"] = ip6_type
        bridges[name]["ip_address"] = ip_address
        bridges[name]["ip_prefixlen"] = ip_prefixlen or "24"
        bridges[name]["ip_gateway"] = ip_gateway
        bridges[name]["ip_dns"] = ip_dns
        bridges[name]["ip_mtu"] = ip_mtu
        bridges[name]["ip6_address"] = ip6_address
        bridges[name]["ip6_prefixlen"] = ip6_prefixlen or "64"
        bridges[name]["ip6_gateway"] = ip6_gateway
        bridges[name]["ip6_dns"] = ip6_dns
    elif action == "update_stp":
        name = str(data.get("name") or "").strip()
        stp = data.get("stp", False)
        if not valid_bridge_name(name):
            raise RuntimeError("Bridge name is required")
        saved_cfg = bridges.get(name, {})
        bridge_type = (
            saved_cfg.get("bridge_type") or str(data.get("bridge_type") or "").strip()
        )
        if bridge_type not in ("linux", "ovs"):
            bridge_type = (
                "ovs"
                if (
                    Path(f"/sys/class/net/{name}/bridge").exists() is False
                    and shutil_which("ovs-vsctl")
                )
                else "linux"
            )
        if bridge_type == "ovs" and shutil_which("ovs-vsctl"):
            results.append(
                run(
                    [
                        shutil_which("ovs-vsctl"),
                        "set",
                        "Bridge",
                        name,
                        f"stp_enable={'true' if stp else 'false'}",
                    ],
                    timeout=10,
                )
            )
        else:
            stp_path = Path(f"/sys/class/net/{name}/bridge/stp_state")
            if stp_path.exists():
                try:
                    stp_path.write_text("1" if stp else "0", encoding="utf-8")
                except Exception:
                    results.append(
                        run(
                            [
                                "ip",
                                "link",
                                "set",
                                name,
                                "type",
                                "bridge",
                                "stp_state",
                                "1" if stp else "0",
                            ],
                            timeout=10,
                        )
                    )
            else:
                results.append(
                    run(
                        [
                            "ip",
                            "link",
                            "set",
                            name,
                            "type",
                            "bridge",
                            "stp_state",
                            "1" if stp else "0",
                        ],
                        timeout=10,
                    )
                )
        if name in bridges:
            bridges[name]["stp"] = bool(stp)
    state["bridges"] = bridges
    save_state(state)
    write_bridge_service(bridges)
    if results:
        errors = [
            f'{r["cmd"]}: {r["stderr"] or r["stdout"] or "failed"}'
            for r in results
            if r.get("rc") != 0
        ]
        if errors:
            raise RuntimeError("; ".join(errors))
    return {
        "bridges": read_bridges(),
        "saved_bridges": bridges,
        "available_ifaces": [i["name"] for i in list_network()["interfaces"]],
        "results": results,
    }


def write_network_service(network):
    lines = ["#!/bin/sh", "set -eu"]
    for iface, cfg in sorted(network.items()):
        safe_iface = clean_iface_name(iface)
        if not safe_iface:
            continue
        if cfg.get("mac"):
            lines.append(f"ip link set dev {safe_iface} down || true")
            lines.append(
                f"ip link set dev {safe_iface} address {shell_quote(cfg['mac'])} || true"
            )
            lines.append(f"ip link set dev {safe_iface} up || true")
        if cfg.get("mtu"):
            lines.append(
                f"ip link set dev {safe_iface} mtu {shell_quote(cfg['mtu'])} || true"
            )
        if cfg.get("wol") and cfg["wol"] != "keep":
            lines.append(
                f"command -v ethtool >/dev/null 2>&1 && ethtool -s {safe_iface} wol {shell_quote(cfg['wol'])} || true"
            )
        if cfg.get("autoneg") == "on" and not cfg.get("speed"):
            lines.append(
                f"command -v ethtool >/dev/null 2>&1 && ethtool -s {safe_iface} autoneg on || true"
            )
        elif cfg.get("speed"):
            autoneg = "on" if cfg.get("autoneg", "off") == "on" else "off"
            lines.append(
                f"command -v ethtool >/dev/null 2>&1 && ethtool -s {safe_iface} speed {shell_quote(cfg['speed'])} duplex {shell_quote(cfg.get('duplex') or 'full')} autoneg {autoneg} || true"
            )
    NETWORK_APPLY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(NETWORK_APPLY, 0o755)
    NETWORK_SERVICE.write_text(
        """[Unit]
Description=Apply fn advanced network settings
After=network-pre.target
Before=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fn-advancedsettings-network-apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""",
        encoding="utf-8",
    )
    if shutil_which("systemctl"):
        run(["systemctl", "daemon-reload"], timeout=15)
        run(["systemctl", "enable", "fn-advancedsettings-network.service"], timeout=15)


def write_bridge_service(bridges):
    lines = ["#!/bin/sh", "set -eu"]
    for bname, bcfg in sorted(bridges.items()):
        safe_bname = clean_iface_name(bname)
        if not safe_bname:
            continue
        bridge_type = bcfg.get("bridge_type", "linux")
        if bridge_type == "ovs":
            lines.append(f"command -v ovs-vsctl >/dev/null 2>&1 || true")
            lines.append(f"ovs-vsctl add-br {safe_bname} 2>/dev/null || true")
            lines.append(
                f"ovs-vsctl set Bridge {safe_bname} stp_enable={'true' if bcfg.get('stp') else 'false'} 2>/dev/null || true"
            )
        else:
            lines.append(
                f"ip link add name {safe_bname} type bridge 2>/dev/null || true"
            )
            lines.append(
                f"ip link set {safe_bname} type bridge stp_state {'1' if bcfg.get('stp') else '0'} 2>/dev/null || true"
            )
        ip_mtu = bcfg.get("ip_mtu", "")
        if ip_mtu:
            lines.append(
                f"ip link set {safe_bname} mtu {shell_quote(ip_mtu)} 2>/dev/null || true"
            )
        lines.append(f"ip link set {safe_bname} up || true")
        for member in bcfg.get("members") or []:
            safe_member = clean_iface_name(member)
            if safe_member:
                lines.append(f"ip link set {safe_member} up || true")
                if bridge_type == "ovs":
                    lines.append(
                        f"ovs-vsctl add-port {safe_bname} {safe_member} 2>/dev/null || true"
                    )
                else:
                    lines.append(
                        f"ip link set {safe_member} master {safe_bname} || true"
                    )
        ip4_type = bcfg.get("ip4_type", "")
        ip6_type = bcfg.get("ip6_type", "")
        if ip4_type == "static":
            ip_addr = bcfg.get("ip_address", "")
            ip_prefix = bcfg.get("ip_prefixlen", "24") or "24"
            ip_gw = bcfg.get("ip_gateway", "")
            ip_dns = bcfg.get("ip_dns", "")
            if ip_addr:
                lines.append(
                    f"ip addr add {shell_quote(ip_addr + '/' + ip_prefix)} dev {safe_bname} 2>/dev/null || true"
                )
            if ip_gw:
                lines.append(
                    f"ip route replace default via {shell_quote(ip_gw)} dev {safe_bname} 2>/dev/null || true"
                )
        elif ip4_type == "dhcp":
            lines.append(
                f"command -v dhclient >/dev/null 2>&1 && dhclient -1 -4 {safe_bname} || true"
            )
            lines.append(
                f"command -v udhcpc >/dev/null 2>&1 && udhcpc -i {safe_bname} -n -q || true"
            )
        if ip6_type == "static":
            ip6_addr = bcfg.get("ip6_address", "")
            ip6_prefix = bcfg.get("ip6_prefixlen", "64") or "64"
            ip6_gw = bcfg.get("ip6_gateway", "")
            ip6_dns = bcfg.get("ip6_dns", "")
            if ip6_addr:
                lines.append(
                    f"ip addr add {shell_quote(ip6_addr + '/' + ip6_prefix)} dev {safe_bname} 2>/dev/null || true"
                )
            if ip6_gw:
                lines.append(
                    f"ip -6 route replace default via {shell_quote(ip6_gw)} dev {safe_bname} 2>/dev/null || true"
                )
        elif ip6_type == "dhcp":
            lines.append(
                f"command -v dhclient >/dev/null 2>&1 && dhclient -1 -6 {safe_bname} || true"
            )
            lines.append(
                f"command -v udhcpc >/dev/null 2>&1 && udhcpc -i {safe_bname} -n -q || true"
            )
        dns_entries = []
        if ip4_type == "static":
            for ns in bcfg.get("ip_dns", "").split(","):
                ns = ns.strip()
                if ns:
                    dns_entries.append(ns)
        if ip6_type == "static":
            for ns in bcfg.get("ip6_dns", "").split(","):
                ns = ns.strip()
                if ns:
                    dns_entries.append(ns)
        if dns_entries:
            resolv_content = "\\n".join([f"nameserver {ns}" for ns in dns_entries])
            lines.append(
                f"printf '{resolv_content}\\n' > /etc/resolv.conf 2>/dev/null || true"
            )
    BRIDGE_APPLY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(BRIDGE_APPLY, 0o755)
    BRIDGE_SERVICE.write_text(
        """[Unit]
Description=Apply fn advanced bridge settings
After=fn-advancedsettings-network.service network-pre.target
Before=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fn-advancedsettings-bridge-apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""",
        encoding="utf-8",
    )
    if shutil_which("systemctl"):
        run(["systemctl", "daemon-reload"], timeout=15)
        run(["systemctl", "enable", "fn-advancedsettings-bridge.service"], timeout=15)


def shell_quote(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def save_network(data):
    state = load_state()
    network = normalize_network_state(state)
    normalize_bridge_state(state)
    for item in data.get("interfaces") or []:
        name = item.get("name")
        if name and valid_iface_name(name):
            cfg = {k: v for k, v in item.items() if k != "name" and v not in (None, "")}
            cfg["name"] = name
            network[name] = cfg
    tcp = data.get("tcp") or {}
    if tcp:
        state["tcp"] = tcp
        apply_tcp(tcp)
    state["network"] = network
    save_state(state)
    write_network_service(network)
    write_bridge_service(state.get("bridges", {}))
    result = run([str(NETWORK_APPLY)], timeout=30)
    if result.get("rc") != 0:
        raise RuntimeError(
            f'{result["cmd"]}: {result["stderr"] or result["stdout"] or "failed"}'
        )
    return {"network": list_network(), "results": [result]}


TCP_SYSCTL_MAP = {
    "congestion_control": "net.ipv4.tcp_congestion_control",
    "fastopen": "net.ipv4.tcp_fastopen",
    "syncookies": "net.ipv4.tcp_syncookies",
    "tw_reuse": "net.ipv4.tcp_tw_reuse",
    "fin_timeout": "net.ipv4.tcp_fin_timeout",
    "keepalive_time": "net.ipv4.tcp_keepalive_time",
    "sack": "net.ipv4.tcp_sack",
    "timestamps": "net.ipv4.tcp_timestamps",
    "window_scaling": "net.ipv4.tcp_window_scaling",
    "mtu_probing": "net.ipv4.tcp_mtu_probing",
}

TCP_CC_MODULES = {
    "bbr": "tcp_bbr",
    "bbr2": "tcp_bbr2",
    "dctcp": "tcp_dctcp",
    "cdg": "tcp_cdg",
    "nv": "tcp_nv",
    "veno": "tcp_veno",
    "westwood": "tcp_westwood",
    "htcp": "tcp_htcp",
    "hybla": "tcp_hybla",
    "scalable": "tcp_scalable",
    "lp": "tcp_lp",
    "yeah": "tcp_yeah",
    "illinois": "tcp_illinois",
}


def apply_tcp(tcp):
    sysctl_lines = ["# Managed by fn-advancedsettings"]
    modules = []
    for key, sysctl_key in TCP_SYSCTL_MAP.items():
        value = tcp.get(key)
        if value is not None:
            sysctl_lines.append(f"{sysctl_key} = {value}")
            if shutil_which("sysctl"):
                run(["sysctl", "-w", f"{sysctl_key}={str(value)}"], timeout=10)
            if key == "congestion_control" and str(value) in TCP_CC_MODULES:
                mod_name = TCP_CC_MODULES[str(value)]
                modules.append(mod_name)
                if shutil_which("modprobe"):
                    run(["modprobe", mod_name], timeout=5)
    if len(sysctl_lines) > 1:
        TCP_SYSCTL_CONF.write_text("\n".join(sysctl_lines) + "\n", encoding="utf-8")
    else:
        try:
            TCP_SYSCTL_CONF.unlink()
        except FileNotFoundError:
            pass
    if modules:
        TCP_MODULES_LOAD.write_text(
            "\n".join(["# Managed by fn-advancedsettings"] + modules) + "\n",
            encoding="utf-8",
        )
    else:
        try:
            TCP_MODULES_LOAD.unlink()
        except FileNotFoundError:
            pass


def parse_environment_proxy():
    env = parse_kv_file(read_text(PATHS["environment"]))
    return {key: env.get(key, env.get(key.upper(), "")) for key in PROXY_KEYS}


def normalize_proxy_values(values):
    proxy = {}
    for key in PROXY_KEYS:
        value = str(values.get(key) or values.get(key.upper()) or "").strip()
        if not value:
            proxy[key] = ""
            continue
        if key == "no_proxy":
            proxy[key] = ",".join(
                [item.strip() for item in re.split(r"[,\s]+", value) if item.strip()]
            )
            continue
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in ("http", "https", "socks4", "socks5", "socks5h"):
            raise RuntimeError(
                f"{key} must start with http://, https://, socks4://, socks5://, or socks5h://"
            )
        if not parsed.netloc:
            raise RuntimeError(f"{key} is missing host")
        proxy[key] = value
    return proxy


def quote_double(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def write_environment_proxy(proxy):
    source = read_text(PATHS["environment"])
    existing = parse_kv_file(source)
    for key in PROXY_KEYS:
        value = proxy.get(key) or ""
        if value:
            existing[key] = value
            existing[key.upper()] = value
        else:
            existing.pop(key, None)
            existing.pop(key.upper(), None)
    proxy_keys = set(PROXY_KEYS + [key.upper() for key in PROXY_KEYS])
    kept_lines = []
    for line in source.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if match and match.group(1) in proxy_keys:
            continue
        kept_lines.append(line)
    proxy_lines = [
        f'{key}="{quote_double(existing[key])}"'
        for key in sorted(proxy_keys)
        if existing.get(key)
    ]
    lines = kept_lines
    if lines and proxy_lines and lines[-1].strip():
        lines.append("")
    lines.extend(proxy_lines)
    content = "\n".join(lines).rstrip() + ("\n" if lines else "")
    write_text(PATHS["environment"], content)


def save_proxy(data):
    proxy = normalize_proxy_values(data.get("proxy") or {})
    targets = data.get("targets") or {}
    write_environment_proxy(proxy)
    exports = ["# Managed by fn-advancedsettings"]
    for key in PROXY_KEYS:
        if proxy.get(key):
            exports.append(f"export {key}={shell_quote(proxy[key])}")
            exports.append(f"export {key.upper()}={shell_quote(proxy[key])}")
    if len(exports) > 1:
        PROXY_PROFILE.write_text("\n".join(exports) + "\n", encoding="utf-8")
        os.chmod(PROXY_PROFILE, 0o644)
    elif PROXY_PROFILE.exists():
        PROXY_PROFILE.unlink()
    if targets.get("apt"):
        apt_lines = []
        if proxy.get("http_proxy"):
            apt_lines.append(
                f'Acquire::http::Proxy "{quote_double(proxy["http_proxy"])}";'
            )
        if proxy.get("https_proxy"):
            apt_lines.append(
                f'Acquire::https::Proxy "{quote_double(proxy["https_proxy"])}";'
            )
        if apt_lines:
            PROXY_APT.write_text("\n".join(apt_lines) + "\n", encoding="utf-8")
        elif PROXY_APT.exists():
            PROXY_APT.unlink()
    else:
        if PROXY_APT.exists():
            PROXY_APT.unlink()
    if targets.get("docker"):
        PROXY_DOCKER_DIR.mkdir(parents=True, exist_ok=True)
        docker_lines = ["[Service]"]
        if proxy.get("http_proxy"):
            docker_lines.append(
                f'Environment="HTTP_PROXY={quote_double(proxy["http_proxy"])}"'
            )
            docker_lines.append(
                f'Environment="http_proxy={quote_double(proxy["http_proxy"])}"'
            )
        if proxy.get("https_proxy"):
            docker_lines.append(
                f'Environment="HTTPS_PROXY={quote_double(proxy["https_proxy"])}"'
            )
            docker_lines.append(
                f'Environment="https_proxy={quote_double(proxy["https_proxy"])}"'
            )
        if proxy.get("no_proxy"):
            docker_lines.append(
                f'Environment="NO_PROXY={quote_double(proxy["no_proxy"])}"'
            )
            docker_lines.append(
                f'Environment="no_proxy={quote_double(proxy["no_proxy"])}"'
            )
        if len(docker_lines) > 1:
            PROXY_DOCKER_CONF.write_text(
                "\n".join(docker_lines) + "\n", encoding="utf-8"
            )
        elif PROXY_DOCKER_CONF.exists():
            PROXY_DOCKER_CONF.unlink()
        run(["systemctl", "daemon-reload"], timeout=15)
    else:
        if PROXY_DOCKER_CONF.exists():
            PROXY_DOCKER_CONF.unlink()
            run(["systemctl", "daemon-reload"], timeout=15)
    if targets.get("pip"):
        pip_lines = ["[global]"]
        pip_proxy = proxy.get("http_proxy") or proxy.get("https_proxy") or ""
        if pip_proxy:
            pip_lines.append(f"proxy = {pip_proxy}")
            PROXY_PIP.write_text("\n".join(pip_lines) + "\n", encoding="utf-8")
        elif PROXY_PIP.exists():
            PROXY_PIP.unlink()
    else:
        if PROXY_PIP.exists():
            PROXY_PIP.unlink()
    if targets.get("npm"):
        npm_lines = []
        if proxy.get("http_proxy"):
            npm_lines.append(f"proxy = {proxy['http_proxy']}")
        if proxy.get("https_proxy"):
            npm_lines.append(f"https-proxy = {proxy['https_proxy']}")
        if proxy.get("no_proxy"):
            npm_lines.append(f"noproxy = {proxy['no_proxy']}")
        if npm_lines:
            PROXY_NPM.write_text("\n".join(npm_lines) + "\n", encoding="utf-8")
        elif PROXY_NPM.exists():
            PROXY_NPM.unlink()
    else:
        if PROXY_NPM.exists():
            PROXY_NPM.unlink()
    if targets.get("git"):
        git_lines = ["[http]"]
        git_proxy = (
            proxy.get("http_proxy")
            or proxy.get("https_proxy")
            or proxy.get("socks_proxy")
            or ""
        )
        if git_proxy:
            git_lines.append(f"\tproxy = {git_proxy}")
        if proxy.get("https_proxy"):
            git_lines.append(f"\tsslProxy = {proxy['https_proxy']}")
        if proxy.get("no_proxy"):
            no_proxy_list = ",".join(
                item.strip() for item in proxy["no_proxy"].split(",") if item.strip()
            )
            if no_proxy_list:
                git_lines.append(f"\tnoProxy = {no_proxy_list}")
        if len(git_lines) > 1:
            PROXY_GIT.write_text("\n".join(git_lines) + "\n", encoding="utf-8")
        elif PROXY_GIT.exists():
            PROXY_GIT.unlink()
    else:
        if PROXY_GIT.exists():
            PROXY_GIT.unlink()
    return {"proxy": read_proxy()}


def read_proxy():
    targets = {}
    targets["apt"] = PROXY_APT.exists()
    targets["docker"] = PROXY_DOCKER_CONF.exists()
    targets["pip"] = PROXY_PIP.exists()
    targets["npm"] = PROXY_NPM.exists()
    targets["git"] = PROXY_GIT.exists()
    return {"values": parse_environment_proxy(), "targets": targets}


def chattr(path, flag):
    if shutil_which("chattr"):
        run(["chattr", flag, str(path)], timeout=8)


def is_immutable(path):
    if not shutil_which("lsattr") or not Path(path).exists():
        return False
    parts = (run(["lsattr", str(path)], timeout=8).get("stdout") or "").split()
    return bool(parts) and "i" in parts[0]


def save_identity(data):
    path = PATHS["device_id"]
    enabled = bool(data.get("enabled"))
    value = str(data.get("device_id") or "")[:32]
    immutable = is_immutable(path)
    if immutable:
        chattr(path, "-i")
    if enabled and value:
        if path.exists() and not Path(str(path) + ".bak").exists():
            Path(str(path) + ".bak").write_bytes(path.read_bytes())
        path.write_text(value, encoding="utf-8")
    elif Path(str(path) + ".bak").exists():
        Path(str(path) + ".bak").replace(path)
    if immutable:
        chattr(path, "+i")
    results = []
    if data.get("apply") and shutil_which("systemctl"):
        results.append(
            run(
                [
                    "systemctl",
                    "restart",
                    "sysinfo_service.service",
                    "trim_main.service",
                ],
                timeout=30,
            )
        )
    if results:
        errors = [
            f'{r["cmd"]}: {r["stderr"] or r["stdout"] or "failed"}'
            for r in results
            if r.get("rc") != 0
        ]
        if errors:
            raise RuntimeError("; ".join(errors))
    return {"identity": read_identity(), "results": results}


def read_identity():
    path = PATHS["device_id"]
    return {
        "device_id": read_text(path).strip(),
        "backup": read_text(str(path) + ".bak").strip(),
        "backup_exists": Path(str(path) + ".bak").exists(),
    }


def read_device():
    pci = []
    pci_driver_map = {}
    if shutil_which("lspci"):
        result_k = run(["lspci", "-k"], timeout=15)
        if result_k["rc"] == 0:
            current_slot = ""
            current_driver = ""
            for line in result_k["stdout"].splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                header = re.match(r"^([0-9a-f:.]+)\s+", stripped)
                if header:
                    if current_slot:
                        pci_driver_map[current_slot] = current_driver
                    current_slot = header.group(1)
                    current_driver = ""
                else:
                    driver_match = re.match(r"Kernel driver in use:\s*(.+)", stripped)
                    if driver_match:
                        current_driver = driver_match.group(1).strip()
            if current_slot:
                pci_driver_map[current_slot] = current_driver
        result = run(["lspci", "-nn"], timeout=15)
        if result["rc"] == 0:
            for line in result["stdout"].splitlines():
                line = line.strip()
                if not line:
                    continue
                slot = ""
                cls = ""
                class_id = ""
                desc = line
                vendor_device = ""
                match = re.match(
                    r"^([0-9a-f:.]+)\s+(.+?)\s*\[([0-9a-f]{4})\]\s*:\s*(.+?)\s*\[([0-9a-f]{4}:[0-9a-f]{4})\]\s*(?:\(rev\s+\S+\))?\s*$",
                    line,
                )
                if match:
                    slot = match.group(1)
                    cls = match.group(2).strip()
                    class_id = match.group(3)
                    vendor_device = match.group(5)
                    desc = match.group(4).strip()
                else:
                    match2 = re.match(
                        r"^([0-9a-f:.]+)\s+(.+?)\s*\[([0-9a-f]{4})\]\s*:\s*(.+)$", line
                    )
                    if match2:
                        slot = match2.group(1)
                        cls = match2.group(2).strip()
                        class_id = match2.group(3)
                        desc = match2.group(4).strip()
                    else:
                        match3 = re.match(r"^([0-9a-f:.]+)\s+(.+)$", line)
                        if match3:
                            slot = match3.group(1)
                            desc = match3.group(2).strip()
                driver = pci_driver_map.get(slot, "")
                pci.append(
                    {
                        "slot": slot,
                        "class": cls,
                        "class_id": class_id,
                        "device_id": vendor_device,
                        "description": desc,
                        "driver": driver,
                    }
                )

    usb = []
    usb_sysfs_drivers = {}
    sysfs_usb = Path("/sys/bus/usb/devices")
    if sysfs_usb.exists():
        for dev_path in sysfs_usb.iterdir():
            if not re.match(r"^\d+-[\d.]+$", dev_path.name):
                continue
            vid_file = dev_path / "idVendor"
            pid_file = dev_path / "idProduct"
            try:
                vid = vid_file.read_text().strip() if vid_file.exists() else ""
                pid = pid_file.read_text().strip() if pid_file.exists() else ""
            except Exception:
                continue
            if not vid or not pid:
                continue
            drivers = set()
            for iface in sorted(dev_path.glob(f"{dev_path.name}:*")):
                drv_path = iface / "driver"
                try:
                    if drv_path.is_symlink():
                        drv_name = drv_path.resolve().name
                        if drv_name and drv_name != "usb":
                            drivers.add(drv_name)
                except Exception:
                    pass
            if not drivers:
                drv_path = dev_path / "driver"
                try:
                    if drv_path.is_symlink():
                        drv_name = drv_path.resolve().name
                        if drv_name and drv_name != "usb":
                            drivers.add(drv_name)
                except Exception:
                    pass
            if drivers:
                usb_sysfs_drivers[f"{vid}:{pid}"] = ", ".join(sorted(drivers))
    if shutil_which("lsusb"):
        result = run(["lsusb"], timeout=15)
        if result["rc"] == 0:
            for line in result["stdout"].splitlines():
                line = line.strip()
                if not line:
                    continue
                bus = ""
                device = ""
                id_vendor = ""
                desc = line
                match = re.match(
                    r"^Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-f]{4}:[0-9a-f]{4})\s*(.*)$",
                    line,
                )
                if match:
                    bus = match.group(1)
                    device = match.group(2)
                    id_vendor = match.group(3)
                    desc = match.group(4).strip()
                driver = usb_sysfs_drivers.get(id_vendor, "")
                usb.append(
                    {
                        "bus": bus,
                        "device": device,
                        "id": id_vendor,
                        "description": desc,
                        "driver": driver,
                    }
                )

    return {"pci": pci, "usb": usb}


def parse_ss_output(text, proto):
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("State") or line.startswith("Netid"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        state_val = parts[0]
        recv_q = parts[1]
        send_q = parts[2]
        local_addr = parts[3]
        peer_addr = parts[4]
        process = " ".join(parts[5:]) if len(parts) > 5 else ""
        port = ""
        addr = local_addr
        if ":" in local_addr:
            addr, port = local_addr.rsplit(":", 1)
        process_name = ""
        process_pid = ""
        if process:
            pid_match = re.search(r"pid=(\d+)", process)
            name_match = re.search(r'\("([^"]+)"', process)
            if pid_match:
                process_pid = pid_match.group(1)
            if name_match:
                process_name = name_match.group(1)
        entries.append(
            {
                "proto": proto,
                "state": state_val,
                "local_address": local_addr,
                "addr": addr,
                "port": port,
                "peer_address": peer_addr,
                "process": process,
                "process_name": process_name,
                "process_pid": process_pid,
                "recv_q": recv_q,
                "send_q": send_q,
            }
        )
    return entries


def read_port():
    tcp = []
    udp = []
    if shutil_which("ss"):
        result_tcp = run(["ss", "-tlnp"], timeout=15)
        if result_tcp["rc"] == 0:
            tcp = parse_ss_output(result_tcp["stdout"], "tcp")
        result_udp = run(["ss", "-ulnp"], timeout=15)
        if result_udp["rc"] == 0:
            udp = parse_ss_output(result_udp["stdout"], "udp")
    elif shutil_which("netstat"):
        result_tcp = run(["netstat", "-tlnp"], timeout=15)
        if result_tcp["rc"] == 0:
            tcp = parse_ss_output(result_tcp["stdout"], "tcp")
        result_udp = run(["netstat", "-ulnp"], timeout=15)
        if result_udp["rc"] == 0:
            udp = parse_ss_output(result_udp["stdout"], "udp")
    return {"tcp": tcp, "udp": udp}


def read_processes():
    processes = []
    result = run(["ps", "aux"], timeout=10)
    if result["rc"] == 0:
        for line in result["stdout"].splitlines()[1:]:  # Skip header
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            user, pid, cpu, mem, vsz, rss, tty, stat, start, time_str, cmd = parts
            processes.append(
                {
                    "user": user,
                    "pid": int(pid),
                    "cpu": cpu,
                    "mem": mem,
                    "stat": stat,
                    "time": time_str,
                    "cmd": cmd,
                }
            )
    return sorted(processes, key=lambda p: p["pid"])


def signal_process(pid, sig):
    signals = {
        "term": signal.SIGTERM,  # pyright: ignore[reportAttributeAccessIssue]
        "kill": signal.SIGKILL,  # pyright: ignore[reportAttributeAccessIssue]
        "stop": signal.SIGSTOP,  # pyright: ignore[reportAttributeAccessIssue]
        "cont": signal.SIGCONT,  # pyright: ignore[reportAttributeAccessIssue]
    }
    sig_int = signals.get(sig.lower())
    if sig_int is None:
        return {"ok": False, "message": f"Invalid signal: {sig}"}
    try:
        os.kill(int(pid), sig_int)
        return {"ok": True}
    except ProcessLookupError:
        return {"ok": False, "message": "Process not found"}
    except PermissionError:
        return {"ok": False, "message": "Permission denied"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


SERVICE_ACTIONS = ("start", "stop", "restart", "reload", "enable", "disable")


def list_services():
    """列出所有 systemd 服务单元及其状态。"""
    services = []
    if not shutil_which("systemctl"):
        return services
    # 先读 unit-files 拿到 enabled/disabled 状态（一次性，避免逐服务 is-enabled）
    enabled_map = {}
    result = run(
        [
            "systemctl",
            "list-unit-files",
            "--type=service",
            "--no-pager",
            "--no-legend",
            "--plain",
        ],
        timeout=15,
    )
    if result["rc"] == 0:
        for line in result["stdout"].splitlines():
            parts = line.split(None, 2)
            if len(parts) >= 2:
                enabled_map[parts[0]] = parts[1]
    result = run(
        [
            "systemctl",
            "list-units",
            "--type=service",
            "--all",
            "--no-pager",
            "--no-legend",
            "--plain",
        ],
        timeout=15,
    )
    if result["rc"] == 0:
        for line in result["stdout"].splitlines():
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            unit, load, active, sub, desc = parts
            if unit.endswith(".service"):
                services.append(
                    {
                        "name": unit[: -len(".service")],
                        "unit": unit,
                        "load": load,
                        "active": active,
                        "sub": sub,
                        "enabled": enabled_map.get(unit, "unknown"),
                        "description": desc,
                    }
                )
    return sorted(services, key=lambda s: s["name"])


def service_action(name, action):
    """对 systemd 服务执行 start/stop/restart/reload/enable/disable。"""
    if action not in SERVICE_ACTIONS:
        return {"ok": False, "message": f"Invalid action: {action}"}
    if not shutil_which("systemctl"):
        return {"ok": False, "message": "systemctl not found"}
    if not name or "." not in name:
        # 允许不带 .service 后缀，自动补全
        name = f"{name}.service" if name else ""
    result = run(["systemctl", action, name], timeout=60)
    if result["rc"] == 0:
        return {
            "ok": True,
            "message": (result["stdout"] or result["stderr"] or "").strip(),
        }
    return {
        "ok": False,
        "message": (result["stderr"] or result["stdout"] or "failed").strip(),
    }


def _normalize_service_name(name):
    """规范化服务名：补 .service 后缀，并拒绝路径穿越。"""
    if not name:
        return ""
    if ".." in name or "/" in name or "\x00" in name:
        return ""
    return f"{name}.service" if "." not in name else name


def service_cat(name):
    """返回服务单元文件内容（systemctl cat）。"""
    if not shutil_which("systemctl"):
        return {"ok": False, "message": "systemctl not found"}
    unit = _normalize_service_name(name)
    if not unit:
        return {"ok": False, "message": "Invalid service name"}
    result = run(["systemctl", "cat", unit], timeout=15)
    if result["rc"] == 0:
        return {"ok": True, "content": result["stdout"]}
    return {
        "ok": False,
        "message": (result["stderr"] or result["stdout"] or "failed").strip(),
    }


def service_status(name):
    """返回服务运行状态（systemctl status -l --no-pager）。"""
    if not shutil_which("systemctl"):
        return {"ok": False, "message": "systemctl not found"}
    unit = _normalize_service_name(name)
    if not unit:
        return {"ok": False, "message": "Invalid service name"}
    result = run(["systemctl", "status", "-l", "--no-pager", unit], timeout=15)
    content = (result["stdout"] or result["stderr"] or "").strip()
    return {"ok": True, "content": content or "no output"}


def service_edit_read(name):
    """读取服务 drop-in override 文件内容（/etc/systemd/system/<name>.d/override.conf）。"""
    unit = _normalize_service_name(name)
    if not unit:
        return {"ok": False, "message": "Invalid service name"}
    dropin = Path("/etc/systemd/system") / f"{unit}.d" / "override.conf"
    content = ""
    if dropin.exists():
        try:
            content = dropin.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"ok": False, "message": str(e)}
    return {"ok": True, "content": content, "path": str(dropin)}


def service_edit_save(name, content):
    """写入服务 drop-in override 文件并执行 daemon-reload；空内容则删除 override.conf。"""
    unit = _normalize_service_name(name)
    if not unit:
        return {"ok": False, "message": "Invalid service name"}
    dropin = Path("/etc/systemd/system") / f"{unit}.d" / "override.conf"
    try:
        if not (content or "").strip():
            # 空内容：删除 override.conf（若存在），并清理空目录
            if dropin.exists():
                dropin.unlink()
            dropin_dir = dropin.parent
            if dropin_dir.exists() and not any(dropin_dir.iterdir()):
                dropin_dir.rmdir()
        else:
            dropin.parent.mkdir(parents=True, exist_ok=True)
            dropin.write_text(content, encoding="utf-8")
            os.chmod(dropin, 0o644)
    except Exception as e:
        return {"ok": False, "message": str(e)}
    if shutil_which("systemctl"):
        result = run(["systemctl", "daemon-reload"], timeout=15)
        if result["rc"] != 0:
            return {
                "ok": False,
                "message": (result["stderr"] or "daemon-reload failed").strip(),
            }
    return {"ok": True}


def systemd_analyze_plot():
    """返回 systemd-analyze plot 生成的启动时间线 SVG。"""
    if not shutil_which("systemd-analyze"):
        return {"ok": False, "message": "systemd-analyze not found"}
    result = run(["systemd-analyze", "plot"], timeout=30)
    if result["rc"] == 0:
        return {"ok": True, "svg": result["stdout"]}
    return {
        "ok": False,
        "message": (result["stderr"] or result["stdout"] or "failed").strip(),
    }


def systemd_analyze_data():
    """返回启动分析的具体数据：总时间、服务耗时排行、关键启动链。"""
    if not shutil_which("systemd-analyze"):
        return {"ok": False, "message": "systemd-analyze not found"}
    result = {}
    for key, args in (
        ("time", ["time"]),
        ("blame", ["blame"]),
        ("critical", ["critical-chain"]),
    ):
        r = run(["systemd-analyze"] + args, timeout=20)
        result[key] = (r["stdout"] or r["stderr"] or "").strip()
    return {"ok": True, **result}


def diag_stream_start(
    target, tool, count=4, server=None, ipv6=False
) -> tuple[subprocess.Popen | None, str]:
    if tool == "ping":
        if ipv6:
            if shutil_which("ping6"):
                cmd = ["ping6"]
            else:
                cmd = [shutil_which("ping") or "ping", "-6"]
        else:
            cmd = [shutil_which("ping") or "ping"]
        if count >= 1:
            cmd += ["-c", str(count)]
        cmd.append(target)
    elif tool == "traceroute":
        if shutil_which("traceroute6") and ipv6:
            cmd = ["traceroute6", target]
        elif shutil_which("traceroute"):
            cmd = ["traceroute"]
            if ipv6:
                cmd += ["-6"]
            cmd.append(target)
        elif shutil_which("tracepath"):
            cmd = ["tracepath"]
            if ipv6:
                cmd += ["-6"]
            cmd.append(target)
        else:
            return None, "traceroute / tracepath not found"
    elif tool == "nslookup":
        if shutil_which("nslookup"):
            cmd = [shutil_which("nslookup")]
            if server:
                cmd += [target, server]
            else:
                cmd.append(target)
        elif shutil_which("dig"):
            cmd = ["dig"]
            if ipv6:
                cmd += ["AAAA"]
            else:
                cmd += ["A"]
            cmd.append(target)
            if server:
                cmd += ["@" + server]
            cmd += ["+noall", "+answer", "+comments"]
        else:
            return None, "nslookup / dig not found"
    elif tool == "arp":
        if ipv6:
            if shutil_which("ip"):
                cmd = ["ip", "-6", "neigh", "show"]
            elif shutil_which("ndp"):
                cmd = ["ndp", "-a"]
            else:
                return None, "ip / ndp not found"
        else:
            if shutil_which("ip"):
                cmd = ["ip", "neigh", "show"]
            elif shutil_which("arp"):
                cmd = ["arp", "-an"]
            else:
                return None, "ip / arp not found"
    else:
        return None, "unknown tool"
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        return proc, ""
    except Exception as exc:
        return None, str(exc)


def read_all():
    return {
        "ok": True,
        "boot": read_boot(),
        "power": read_power(),
        "ssh": read_ssh(),
        "cpu": read_cpu(),
        "dns": read_dns(),
        "network": list_network(),
        "proxy": read_proxy(),
        "identity": read_identity(),
        "device": read_device(),
        "port": read_port(),
        "processes": read_processes(),
        "display": read_display(),
    }


def safe_dispatch(fn, body):
    try:
        result = fn(body)
        json_response({"ok": True, **result})
    except Exception as e:
        json_response({"ok": False, "message": str(e)})


def dispatch():
    global _diag_proc
    body = request_body()
    action = body.get("action") or "read"
    if action == "read":
        json_response(read_all())
    elif action == "saveBoot":
        safe_dispatch(save_boot, body)
    elif action == "savePower":
        safe_dispatch(save_power, body)
    elif action == "saveSsh":
        safe_dispatch(save_sshd, body)
    elif action == "saveCpu":
        safe_dispatch(save_cpu, body)
    elif action == "saveDns":
        safe_dispatch(save_dns, body)
    elif action == "saveNetwork":
        safe_dispatch(save_network, body)
    elif action == "saveBridge":
        safe_dispatch(save_bridge, body)
    elif action == "saveProxy":
        safe_dispatch(save_proxy, body)
    elif action == "saveIdentity":
        safe_dispatch(save_identity, body)
    elif action == "readDevice":
        json_response({"ok": True, "device": read_device()})
    elif action == "readPort":
        json_response({"ok": True, "port": read_port()})
    elif action == "readProcesses":
        json_response({"ok": True, "processes": read_processes()})
    elif action == "signalProcess":
        pid = body.get("pid")
        sig = body.get("signal", "term")
        if not pid:
            json_response({"ok": False, "message": "pid required"}, "400 Bad Request")
            return
        json_response(signal_process(pid, sig))
    elif action == "readServices":
        json_response({"ok": True, "services": list_services()})
    elif action == "serviceAction":
        name = body.get("name")
        act = body.get("op") or body.get("action", "restart")
        if not name:
            json_response(
                {"ok": False, "message": "service name required"}, "400 Bad Request"
            )
            return
        json_response(service_action(name, act))
    elif action == "serviceCat":
        name = body.get("name")
        if not name:
            json_response(
                {"ok": False, "message": "service name required"}, "400 Bad Request"
            )
            return
        json_response(service_cat(name))
    elif action == "serviceStatus":
        name = body.get("name")
        if not name:
            json_response(
                {"ok": False, "message": "service name required"}, "400 Bad Request"
            )
            return
        json_response(service_status(name))
    elif action == "serviceEditRead":
        name = body.get("name")
        if not name:
            json_response(
                {"ok": False, "message": "service name required"}, "400 Bad Request"
            )
            return
        json_response(service_edit_read(name))
    elif action == "serviceEditSave":
        name = body.get("name")
        content = body.get("content", "")
        if not name:
            json_response(
                {"ok": False, "message": "service name required"}, "400 Bad Request"
            )
            return
        json_response(service_edit_save(name, content))
    elif action == "systemdAnalyzePlot":
        json_response(systemd_analyze_plot())
    elif action == "systemdAnalyzeData":
        json_response(systemd_analyze_data())
    elif action == "saveDisplay":
        safe_dispatch(save_display, body)
    elif action == "readDisplay":
        json_response({"ok": True, "display": read_display()})
    elif action == "diagStream":
        tool = body.get("tool", "ping")
        target = body.get("target", "")
        count = int(body.get("count", 4))
        server = body.get("server") or None
        ipv6 = body.get("ipv6", False)
        with _diag_lock:
            if _diag_proc is not None and _diag_proc.poll() is None:
                try:
                    _diag_proc.kill()
                except Exception:
                    pass
                try:
                    if _diag_proc.stdout:
                        _diag_proc.stdout.close()
                except Exception:
                    pass
            _diag_proc = None
        proc, err = diag_stream_start(target, tool, count, server, bool(ipv6))
        if err:
            json_response({"ok": False, "message": err}, "400 Bad Request")
            return
        assert proc is not None
        assert proc.stdout is not None
        with _diag_lock:
            _diag_proc = proc
        wfile = sse_response()
        assert wfile is not None
        try:
            for line in proc.stdout:
                sse_send(wfile, "data", {"line": line.rstrip("\n")})
            proc.wait()
            sse_send(wfile, "done", {"rc": proc.returncode})
        except Exception as exc:
            sse_send(wfile, "error", {"message": str(exc)})
            try:
                proc.kill()
            except Exception:
                pass
        finally:
            if proc.stdout:
                proc.stdout.close()
            try:
                wfile.close()
            except Exception:
                pass
            with _diag_lock:
                if _diag_proc is proc:
                    _diag_proc = None
    elif action == "diagStop":
        with _diag_lock:
            stopped = False
            if _diag_proc is not None and _diag_proc.poll() is None:
                try:
                    _diag_proc.kill()
                    stopped = True
                except Exception:
                    stopped = True
                try:
                    if _diag_proc.stdout:
                        _diag_proc.stdout.close()
                except Exception:
                    pass
                _diag_proc = None
        json_response({"ok": True, "stopped": stopped})
    else:
        json_response({"ok": False, "message": "unsupported action"}, "400 Bad Request")


def main():
    parser = argparse.ArgumentParser(description="fn advanced settings server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-advancedsettings")
    parser.add_argument("--www-root", required=True)
    args = parser.parse_args()
    if os.path.exists(args.unix_socket):
        os.unlink(args.unix_socket)
    server = ThreadingUnixHTTPServer(
        args.unix_socket, Handler, base_path=args.base_path, www_root=args.www_root
    )

    def shutdown(_signum, _frame):
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)


if __name__ == "__main__":
    main()
