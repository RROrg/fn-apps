# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import argparse
import ipaddress
import json
import mimetypes
import os
import random
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, parse_qs


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-speedtest")
_pkgvar = _env("TRIM_PKGVAR")
STATE_DIR = Path(_pkgvar) if _pkgvar else Path(f"/var/apps/{APP_NAME}/var")
HOSTNAME = (
    socket.gethostname()
    if hasattr(socket, "gethostname")
    else os.uname().nodename  # pyright: ignore[reportAttributeAccessIssue]
)


def detect_server_ip():
    """Best-effort LAN IP of this host (the NAS). Used as the 'server' address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return None


_public_ip_cache = {"value": None, "checked_at": 0.0}
_public_ip_lock = threading.Lock()


def detect_public_ip():
    """Public (WAN) IP seen by the internet. Returns None on failure."""
    # This endpoint is requested by the initial UI load.  Keep it short and
    # cache it: serial 8-second curl timeouts previously held /api/info long
    # enough that none of the address fields rendered on an offline NAS.
    now = time.monotonic()
    with _public_ip_lock:
        if now - _public_ip_cache["checked_at"] < 600:
            return _public_ip_cache["value"]
    curl = shutil_which("curl")
    result = None
    if curl:
        for url in ("https://api64.ipify.org", "https://api.ipify.org"):
            try:
                proc = subprocess.run(
                    [curl, "-s", "--connect-timeout", "1", "--max-time", "3", url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=12,
                    check=False,
                )
                v = proc.stdout.decode().strip()
                try:
                    result = str(ipaddress.ip_address(v))
                    break
                except ValueError:
                    pass
            except Exception:
                continue
    with _public_ip_lock:
        _public_ip_cache.update(value=result, checked_at=time.monotonic())
    return result


def _clean_ip(value):
    """Return a sane client IP string, or None if the value is unusable
    (empty, loopback, or unix-socket placeholder). Strips a trailing port and
    IPv6 zone index so proxy headers / socket peers normalize cleanly."""
    if not value:
        return None
    value = value.strip()
    # Drop optional :port (IPv4:port or [IPv6]:port)
    if value.startswith("["):
        value = value[1:].split("]")[0]
    elif ":" in value and value.count(":") == 1 and value.rsplit(":", 1)[1].isdigit():
        value = value.rsplit(":", 1)[0]
    # Drop IPv6 zone index (fe80::1%eth0 -> fe80::1)
    value = value.split("%")[0].strip()
    if not value or value in ("127.0.0.1", "::1", "", "localhost"):
        return None
    return value


def detect_client_ip(handler):
    """Client IP as seen by the server. Honors proxy headers first (fnOS
    gateway usually injects X-Real-IP / X-Forwarded-For when proxying over the
    unix socket); falls back to the socket peer, filtering loopback/empty values
    that unix-socket servers report. Handles both IPv4 and IPv6."""
    # ``Forwarded`` is the RFC 7239 form used by a number of reverse proxies.
    # fnOS versions differ in which of these headers they preserve on the hop to
    # the app unix socket, so accept all common forms.
    forwarded = handler.headers.get("Forwarded")
    if forwarded:
        match = re.search(
            r'(?:^|[;,])\s*for="?([^;,"]+)', forwarded, flags=re.IGNORECASE
        )
        if match:
            ip = _clean_ip(match.group(1))
            if ip:
                return ip
    for hdr in ("X-Real-IP", "X-Forwarded-For", "X-Client-IP", "True-Client-IP"):
        raw = handler.headers.get(hdr)
        if raw:
            ip = _clean_ip(raw.split(",")[0])
            if ip:
                return ip
    try:
        peer = handler.client_address[0] if handler.client_address else None
        return _clean_ip(peer)
    except Exception:
        return None


def detect_link_speed_mbps():
    """Best-effort detection of the NIC link speed (Mbit/s) on the interface
    that owns the default route. Falls back to None when unavailable (Windows,
    macOS, or virtual interfaces without a reported speed)."""
    try:
        # Find the interface bound to the default route.
        iface = None
        try:
            with open("/proc/net/route", "r") as fh:
                for line in fh:
                    parts = line.split()
                    if (
                        len(parts) >= 4
                        and parts[1] == "00000000"
                        and parts[3] == "00000000"
                    ):
                        iface = parts[0]
                        break
        except OSError:
            iface = None
        if not iface:
            # Fall back to the first UP, non-loopback interface.
            for name in os.listdir("/sys/class/net"):
                if name == "lo":
                    continue
                try:
                    with open("/sys/class/net/%s/operstate" % name) as fh:
                        if fh.read().strip() == "up":
                            iface = name
                            break
                except OSError:
                    continue
        if iface:
            try:
                with open("/sys/class/net/%s/speed" % iface) as fh:
                    speed = int(fh.read().strip())
                if speed and speed > 0:
                    return speed
            except (OSError, ValueError):
                pass
    except Exception:
        pass
    return None


# Fallback public hosts used for server->internet latency probing.
INTERNET_PING_HOSTS = ["1.1.1.1", "8.8.8.8", "223.5.5.5"]
# Download sources are large, static test files hosted by separate datacenters.
# Cloudflare's /__down endpoint rate-limits frequent parallel requests (HTTP
# 429), which made repeat tests intermittently display a false 0 Mbps result.
# A stream is assigned to each host round-robin, so one throttled route cannot
# invalidate the whole test.
INTERNET_CDN = [
    # 实测可达且高速的国内大文件源（支持 HTTPS + Range + 数 GB 体积）。
    "https://mirrors.huaweicloud.com/ubuntu-releases/24.04.3/ubuntu-24.04.3-live-server-amd64.iso",
    "https://mirrors.tuna.tsinghua.edu.cn/ubuntu-releases/24.04.3/ubuntu-24.04.3-live-server-amd64.iso",
    # 海外兜底：国内镜像不可达时仍能出数
    "https://fsn1-speed.hetzner.com/100MB.bin",
    "https://nbg1-speed.hetzner.com/100MB.bin",
]
INTERNET_UPLOAD = [
    "https://speed.cloudflare.com/__up",
    "https://speedtest.fastly.net/__up",
    "https://dl.fastmirrors.net/__up",
    "https://speed.neu6.edu.cn/__up",
]

REQUEST_CONTEXT = threading.local()

_ServerBase = getattr(socketserver, "UnixStreamServer", socketserver.TCPServer)


class ThreadingUnixHTTPServer(
    socketserver.ThreadingMixIn, _ServerBase  # pyright: ignore[reportGeneralTypeIssues]
):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path, handler_cls, *, base_path, www_root):
        self.server_name = APP_NAME
        self.server_port = 0
        self.base_path = normalize_base_path(base_path)
        self.www_root = Path(www_root)
        super().__init__(socket_path, handler_cls)  # pyright: ignore[reportCallIssue]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def normalize_base_path(path):
    if not path:
        return "/"
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized.rstrip("/") or "/"


def strip_base_path(path, base_path):
    if base_path != "/" and path.startswith(base_path):
        return path[len(base_path) :] or "/"
    return path or "/"


def current_request():
    return getattr(REQUEST_CONTEXT, "value", {}) or {}


def header_value(headers, name):
    """Case-insensitive header lookup."""
    if not headers:
        return ""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


@contextmanager
def request_context(method, query="", headers=None, body=b"", path="", handler=None):
    """Push per-request context so helpers (json_response, request_body, ...)
    can find the active handler without threading globals."""
    previous = getattr(REQUEST_CONTEXT, "value", None)
    REQUEST_CONTEXT.value = {
        "method": (method or "GET").upper(),
        "query": query or "",
        "headers": headers or {},
        "body": body or b"",
        "path": path,
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


def normalize_status(status):
    """Normalize a status into (code, "code phrase"), an int, or a "200 OK" string."""
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
            # 客户端在响应发出前已断开（如外网测速中途取消），属正常情况，忽略
            return
        return
    sys.stdout.write(f"Status: {status_text}\r\n")
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(body)


def sse_response():
    handler = current_request().get("handler")
    if handler is None:
        return None
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    # SSE 需要长连接持续推流；Connection: close 会让 EventSource 立即关闭
    # 并不断重连，收不到任何事件（表盘停在 0.0）。保持 keep-alive 才能流式推送。
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    return handler.wfile


def sse_send(wfile, event, data):
    payload = "event: %s\ndata: %s\n\n" % (
        event,
        json.dumps(data, ensure_ascii=False),
    )
    try:
        wfile.write(payload.encode("utf-8"))
        wfile.flush()
    except Exception:
        pass


# 多流并行 HTTP 接力测速（对齐 LibreSpeed 思路：浏览器/服务端并发多连接打满带宽）。
# 这里服务端作为 client，并行启动多个 curl 进程，每个进程拉/推 20MB 随机数据到
# 公网 CDN / 上传端点，按墙钟窗口汇总总字节/总时间得平均速率，并实时推送各流瞬时值。
HTTP_STREAMS = 4  # 并行流数（下载/上传共用）
HTTP_BLOB_BYTES = 20_000_000  # 每流 20 MB，随机数据不可压缩


def _parallel_http_speed(kind, wfile, window=8, streams=None):
    """Wall-clock windowed server->internet throughput via parallel curl streams.

    kind: 'download' (GET from CDN) or 'upload' (POST to upload endpoint).
    Each worker thread keeps transferring (download / upload) for the whole
    `window` seconds while accumulating actual bytes, so the final average is a
    true windowed throughput — not a short burst sampled from a single object
    that finishes in <1s on a fast link.
    """
    curl = shutil_which("curl")
    if not curl:
        return None
    hosts = INTERNET_CDN if kind == "download" else INTERNET_UPLOAD
    if not hosts:
        return None

    stream_count = streams or HTTP_STREAMS
    t0 = time.time()
    deadline = t0 + window
    bytes_per_stream = [0] * stream_count
    ran_any = [False] * stream_count
    lock = threading.Lock()

    def worker(idx, host):
        total = 0
        ran = False
        while True:
            now = time.time()
            remaining = deadline - now
            if remaining <= 0:
                break
            seg = max(0.5, min(remaining, 2.0))
            try:
                if kind == "download":
                    cmd = [
                        curl,
                        "-sS",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{size_download}",
                        "--connect-timeout",
                        "3",
                        "--max-time",
                        str(seg + 0.5),
                        host,
                    ]
                else:
                    _ensure_wan_blob()
                    cmd = [
                        curl,
                        "-sS",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{size_upload}",
                        "--connect-timeout",
                        "3",
                        "--max-time",
                        str(seg + 0.5),
                        "--data-binary",
                        "@" + _WAN_BLOB_PATH,
                        host,
                    ]
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=seg + 2.0,
                )
                out = (proc.stdout or b"").decode().strip()
                if out:
                    n = int(float(out))
                    total += n
                    ran = ran or n > 0
                with lock:
                    bytes_per_stream[idx] = total
                    ran_any[idx] = ran
            except Exception:
                with lock:
                    bytes_per_stream[idx] = total
                    ran_any[idx] = ran
                break
        with lock:
            bytes_per_stream[idx] = total
            ran_any[idx] = ran

    threads = []
    for i in range(stream_count):
        t = threading.Thread(target=worker, args=(i, hosts[i % len(hosts)]))
        t.start()
        threads.append(t)

    # 主线程按节拍推送动画（各流累计字节 / 已流逝墙钟 = 瞬时平均总吞吐）。
    last_push = time.time()
    while any(t.is_alive() for t in threads):
        time.sleep(0.1)
        now = time.time()
        with lock:
            total = sum(bytes_per_stream)
            got = any(ran_any)
        if got and now - last_push >= 0.25 and now < deadline + 0.5:
            cur = (total * 8) / (max(now - t0, 0.001) * 1e6)
            sse_send(wfile, kind, round(cur, 1))
            last_push = now
    for t in threads:
        t.join()

    with lock:
        total = sum(bytes_per_stream)
        got = any(ran_any)
    if not got:
        # 全部流失败：返回诊断信息，便于前端/日志定位。
        diag = {
            "ok": False,
            "kind": kind,
            "reason": "all streams failed (endpoints unreachable / firewalled / no public network)",
            "tried": hosts[:stream_count],
        }
        sse_send(wfile, kind, None)
        sse_send(wfile, "diag", diag)
        return diag
    # 窗口平均总吞吐 = 各流累计字节之和 / 窗口时长。
    avg = (total * 8) / (max(time.time() - t0, 0.001) * 1e6)
    sse_send(wfile, kind, round(avg, 1))
    return round(avg, 1)


def request_body():
    request = current_request()
    body = request.get("body", b"")
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8", "replace") or "{}")
    except Exception:
        return {}


def shutil_which(binary):
    for item in os.environ.get("PATH", "/usr/sbin:/usr/bin:/sbin:/bin").split(":"):
        candidate = Path(item) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


class Handler(BaseHTTPRequestHandler):
    server: ThreadingUnixHTTPServer  # type: ignore[reportIncompatibleVariableOverride]
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.route()

    def do_HEAD(self):
        self.route()

    def do_POST(self):
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
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header(
                "Location",
                self.server.base_path
                + "/"
                + (("?" + parsed.query) if parsed.query else ""),
            )
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        path = strip_base_path(parsed.path, self.server.base_path)
        if path.startswith("/api") or path == "/echo":
            self.serve_api(path, parsed.query)
            return
        self.serve_static(path)

    def serve_static(self, path):
        rel = unquote(path or "/")
        if rel in ("", "/"):
            rel = "/index.html"
        target = (self.server.www_root / rel.lstrip("/")).resolve()
        root = self.server.www_root.resolve()
        if root != target and root not in target.parents:
            self.send_error(HTTPStatus.BAD_REQUEST, "Bad request")
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in {
            "application/javascript",
            "application/json",
        }:
            ctype = ctype + "; charset=utf-8"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Cache-Control",
            "no-store" if target.name == "index.html" else "public, max-age=60",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def serve_api(self, path, query):
        length = int(self.headers.get("Content-Length") or 0)
        # Upload data must be drained by /api/ul itself.  Reading it here first
        # buffered every 20 MB test body in Python and made the measured upload
        # rate depend on allocator/GC pressure instead of the actual link.
        # Other API requests are small control requests and can stay buffered.
        body = (
            b"" if path == "/api/ul" else (self.rfile.read(length) if length else b"")
        )
        headers = {key: value for key, value in self.headers.items()}
        with request_context(
            self.command,
            query=query,
            headers=headers,
            body=body,
            path=path,
            handler=self,
        ):
            try:
                dispatch(self, path)
            except Exception as exc:  # noqa: BLE001
                json_response(
                    {"ok": False, "message": str(exc)}, "500 Internal Server Error"
                )


def unquote(value):
    from urllib.parse import unquote as _u

    return _u(value)


# ---------------------------------------------------------------------------
# Measurement primitives (server -> internet)
# ---------------------------------------------------------------------------


def _ping_once_tcp(host, port=80, timeout=2.0):
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.monotonic() - start) * 1000.0
    except OSError:
        return None


def measure_latency(host, count=10, timeout=2.0):
    """ICMP ping when possible; fall back to repeated TCP-connect RTT."""
    samples = []
    ping_bin = shutil_which("ping")
    if ping_bin:
        try:
            proc = subprocess.run(
                [ping_bin, "-c", str(count), "-W", "2", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=count * 3 + 5,
                check=False,
            )
            out = proc.stdout.decode("utf-8", "replace")
            rtts = []
            for line in out.splitlines():
                if "time=" in line and "icmp_seq" in line:
                    try:
                        rtts.append(float(line.split("time=")[1].split()[0]))
                    except (ValueError, IndexError):
                        pass
            if rtts:
                s = sorted(rtts)
                n = len(s)
                return {
                    "min": round(s[0], 1),
                    "max": round(s[-1], 1),
                    "avg": round(sum(rtts) / n, 1),
                    "jitter": round(_jitter(rtts), 1),
                    "loss": round((count - n) / count * 100, 1),
                    "samples": [round(x, 1) for x in rtts],
                    "method": "icmp",
                }
        except Exception:
            pass
    # TCP-connect fallback
    for _ in range(count):
        r = _ping_once_tcp(host, timeout=timeout)
        if r is not None:
            samples.append(r)
        time.sleep(0.05)
    if not samples:
        return {
            "min": None,
            "max": None,
            "avg": None,
            "jitter": None,
            "loss": 100.0,
            "samples": [],
            "method": "tcp",
        }
    s = sorted(samples)
    n = len(s)
    return {
        "min": round(s[0], 1),
        "max": round(s[-1], 1),
        "avg": round(sum(samples) / n, 1),
        "jitter": round(_jitter(samples), 1),
        "loss": round((count - n) / count * 100, 1),
        "samples": [round(x, 1) for x in samples],
        "method": "tcp",
    }


def _jitter(samples):
    if len(samples) < 2:
        return 0.0
    diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, len(samples))]
    return sum(diffs) / len(diffs)


def internet_latency():
    for host in INTERNET_PING_HOSTS:
        stats = measure_latency(host, count=10)
        if stats["avg"] is not None:
            stats["host"] = host
            return stats
    return {
        "min": None,
        "max": None,
        "avg": None,
        "jitter": None,
        "loss": 100.0,
        "samples": [],
        "method": "icmp",
        "host": None,
    }


def internet_upload():
    """Server->internet upload, Mbit/s. Returns None if no usable upstream."""

    curl = shutil_which("curl")
    if curl:
        for host in INTERNET_UPLOAD:
            try:
                payload = os.urandom(20_000_000)  # ~20 MB, random => uncompressible
                proc = subprocess.run(
                    [
                        curl,
                        "-s",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{speed_upload}",
                        "--max-time",
                        "20",
                        "--data-binary",
                        "@-",
                        host,
                    ],
                    input=payload,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=40,
                    check=False,
                )
                v = proc.stdout.decode().strip()
                if v and float(v) > 0:
                    return float(v) * 8 / 1_000_000  # B/s -> Mbit/s
            except Exception:
                continue
    return None


def internet_throughput():
    """Measure server->internet throughput. Returns download AND upload (Mbit/s)."""

    curl = shutil_which("curl")
    if curl:
        dl = None
        for host in INTERNET_CDN:
            try:
                proc = subprocess.run(
                    [
                        curl,
                        "-s",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{speed_download}",
                        "--max-time",
                        "12",
                        "https://%s/__down?bytes=30000000" % host,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=20,
                    check=False,
                )
                v = proc.stdout.decode().strip()
                if v and float(v) > 0:
                    dl = float(v) * 8 / 1_000_000  # B/s -> Mbit/s
                    break
            except Exception:
                continue

        up = None
        for host in INTERNET_UPLOAD:
            try:
                payload = os.urandom(20_000_000)  # ~20 MB, random => uncompressible
                proc = subprocess.run(
                    [
                        curl,
                        "-s",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{speed_upload}",
                        "--max-time",
                        "20",
                        "--data-binary",
                        "@-",
                        host,
                    ],
                    input=payload,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=40,
                    check=False,
                )
                v = proc.stdout.decode().strip()
                if v and float(v) > 0:
                    up = float(v) * 8 / 1_000_000  # B/s -> Mbit/s
                    break
            except Exception:
                continue

        return {
            "method": "curl-cdn",
            "download": round(dl, 1) if dl else None,
            "upload": round(up, 1) if up else None,
            "ping": None,
        }
    return {"method": "none", "download": None, "upload": None, "ping": None}


# ---------------------------------------------------------------------------
# API dispatch
# ---------------------------------------------------------------------------


# ---- LAN 下载：预生成随机文件 + os.sendfile 零拷贝直发 -------------------
# 生成一次 256MB 随机文件，/api/dl 用 os.sendfile 从文件拷贝到连接套接字。
_DL_BLOB_PATH = os.path.join(STATE_DIR, "dl_blob.bin")
_DL_BLOB_SIZE = 256 * 1024 * 1024
_WAN_BLOB_PATH = os.path.join(STATE_DIR, "wan_upload_blob.bin")
# 100MB：窗口化上传时单条 curl 传输越长，连接/TLS 握手开销占比越小，吞吐越接近真实。
_WAN_BLOB_SIZE = 100_000_000
_dl_blob_lock = threading.Lock()
_dl_blob_ready = False
_wan_blob_ready = False


def _ensure_dl_blob():
    global _dl_blob_ready
    if (
        _dl_blob_ready
        and os.path.exists(_DL_BLOB_PATH)
        and os.path.getsize(_DL_BLOB_PATH) == _DL_BLOB_SIZE
    ):
        return
    with _dl_blob_lock:
        if (
            _dl_blob_ready
            and os.path.exists(_DL_BLOB_PATH)
            and os.path.getsize(_DL_BLOB_PATH) == _DL_BLOB_SIZE
        ):
            return
        tmp = _DL_BLOB_PATH + ".tmp"
        with open(tmp, "wb") as f:
            f.write(os.urandom(_DL_BLOB_SIZE))
        os.rename(tmp, _DL_BLOB_PATH)
        _dl_blob_ready = True


def _ensure_wan_blob():
    """Create one reusable, incompressible upload payload for all WAN workers."""
    global _wan_blob_ready
    if (
        _wan_blob_ready
        and os.path.exists(_WAN_BLOB_PATH)
        and os.path.getsize(_WAN_BLOB_PATH) == _WAN_BLOB_SIZE
    ):
        return
    with _dl_blob_lock:
        if (
            _wan_blob_ready
            and os.path.exists(_WAN_BLOB_PATH)
            and os.path.getsize(_WAN_BLOB_PATH) == _WAN_BLOB_SIZE
        ):
            return
        tmp = _WAN_BLOB_PATH + ".tmp"
        with open(tmp, "wb") as f:
            f.write(os.urandom(_WAN_BLOB_SIZE))
        os.replace(tmp, _WAN_BLOB_PATH)
        _wan_blob_ready = True


def _cleanup_temp_blobs():
    """Delete the pre-generated temp blobs after a speed test and reset the
    ready flags so the next run regenerates them fresh (avoids stale files
    and frees ~356MB of disk space between tests)."""
    global _dl_blob_ready, _wan_blob_ready
    with _dl_blob_lock:
        for p in (_DL_BLOB_PATH, _WAN_BLOB_PATH):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        _dl_blob_ready = False
        _wan_blob_ready = False


def _serve_dl_blob(handler, total):
    _ensure_dl_blob()
    sock = handler.connection.fileno()
    sent = 0
    try:
        with open(_DL_BLOB_PATH, "rb") as f:
            while sent < total:
                # 从 blob 循环读取（随机数据，重复无妨）；单次最多 64MB，
                # 避免单次 sendfile 过大导致内核侧阻塞过久。
                off = sent % _DL_BLOB_SIZE
                n = min(total - sent, _DL_BLOB_SIZE - off, 64 * 1024 * 1024)
                sent += os.sendfile(  # pyright: ignore[reportAttributeAccessIssue]
                    sock, f.fileno(), off, n
                )
    except Exception:
        pass


def dispatch(handler, path):
    # tiny echo used by the browser for LAN RTT timing
    if path == "/echo":
        length = int(handler.headers.get("Content-Length") or 0)
        if length:
            handler.rfile.read(min(length, 1 << 20))
        json_response({"ok": True, "t": time.time()})
        return

    if path == "/api/info":
        json_response(
            {
                "ok": True,
                "app": APP_NAME,
                "server": HOSTNAME,
                "timestamp": int(time.time()),
                "lanSpeedMbps": detect_link_speed_mbps(),
                "serverIp": detect_server_ip(),
                "publicIp": detect_public_ip(),
                "clientIp": detect_client_ip(handler),
                # 应用数据目录：供前端「打开数据目录」（sdk.openFileManager）使用。
                "dataDir": str(STATE_DIR),
                # 诊断：fnOS 经 unix socket 转发时 client_address 常为 ""，网关可能未透传真实 IP。
                # 这里把原始值一并返回，便于确认到底卡在哪一层。
                "clientAddrRaw": (
                    handler.client_address[0] if handler.client_address else None
                ),
                "xForwardedFor": handler.headers.get("X-Forwarded-For"),
                "xRealIp": handler.headers.get("X-Real-IP"),
            }
        )
        return

    if path == "/api/dl":
        # Stream N MB of random data so the browser can measure download rate.
        # 关键：用 os.sendfile 从预生成的随机文件零拷贝直发，在内核态完成拷贝且释放 GIL。
        qs = parse_qs(current_request().get("query", ""))
        try:
            mb = max(1, min(200, int((qs.get("mb") or ["50"])[0])))
        except ValueError:
            mb = 50
        total = mb * 1_000_000
        handler.send_response(200)
        handler.send_header("Content-Type", "application/octet-stream")
        handler.send_header("Content-Length", str(total))
        handler.send_header("Cache-Control", "no-store")
        # nginx 默认对未标记的代理响应开 proxy_buffering（缓冲大响应会拉低
        # 实测下载吞吐）。X-Accel-Buffering: no 让 nginx 对该响应直接流式透传，
        # 使前端测得的下载速率等于真实网络吞吐。
        handler.send_header("X-Accel-Buffering", "no")
        # 关键：os.sendfile 绕过 wfile 直写 socket fd，会使 http.server 的
        # wfile 缓冲状态与实际 socket 错位。trim_http_cgi 对后端用持久连接
        # 复用，复用错位连接会导致后续请求解析失败（invalid token）。
        # 故此处强制关闭连接，避免复用（下载本就是一次性大块传输）。
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.wfile.flush()
        handler.close_connection = True
        _serve_dl_blob(handler, total)
        return

    if path == "/api/ul":
        # Drain directly from the socket in bounded chunks.  This is intentional:
        # it provides real back-pressure all the way to the browser and avoids a
        # large in-memory request buffer skewing upload results.
        length = int(handler.headers.get("Content-Length") or 0)
        received = 0
        while received < length:
            chunk = handler.rfile.read(min(256 * 1024, length - received))
            if not chunk:
                break
            received += len(chunk)
        json_response({"ok": received == length, "bytes": received})
        return

    if path == "/api/internet":
        wfile = sse_response()
        if wfile is None:
            json_response(
                {"ok": False, "message": "stream unavailable"},
                "500 Internal Server Error",
            )
            return
        sse_send(wfile, "phase", {"stage": "latency"})
        lat = internet_latency()
        sse_send(wfile, "latency", lat)

        # Download phase: parallel curl streams (20MB/blob) so the gauge animates.
        sse_send(wfile, "phase", {"stage": "download"})
        dl = _parallel_http_speed("download", wfile, window=8)
        # A transient CDN connection failure should not turn into a misleading
        # 0 Mbps reading. Retry once with fewer streams, which also works on
        # networks that rate-limit bursts of parallel HTTPS connections.
        if not isinstance(dl, (int, float)) or dl <= 0:
            time.sleep(0.2)
            dl = _parallel_http_speed("download", wfile, window=10, streams=2)
        dl_val = dl if isinstance(dl, (int, float)) and dl > 0 else None

        # Upload phase: parallel curl streams (20MB/blob) so the gauge animates.
        sse_send(wfile, "phase", {"stage": "upload"})
        up = _parallel_http_speed("upload", wfile, window=8)
        if not isinstance(up, (int, float)) or up <= 0:
            time.sleep(0.2)
            up = _parallel_http_speed("upload", wfile, window=10, streams=2)
        up_val = up if isinstance(up, (int, float)) and up > 0 else None

        sse_send(
            wfile,
            "done",
            {
                "latency": lat,
                "download": dl_val,
                "upload": up_val,
                "diag": {
                    "download": dl if isinstance(dl, dict) else None,
                    "upload": up if isinstance(up, dict) else None,
                },
            },
        )
        # 测速结束：删除临时 blob（dl_blob.bin / wan_upload_blob.bin），释放磁盘空间。
        _cleanup_temp_blobs()
        return

    json_response({"ok": False, "message": "not found"}, "404 Not Found")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="fn-speedtest backend")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-speedtest")
    parser.add_argument("--www-root", required=True)
    args = parser.parse_args()

    socket_path = Path(args.unix_socket)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()

    server = ThreadingUnixHTTPServer(
        str(socket_path),
        Handler,
        base_path=args.base_path,
        www_root=args.www_root,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            socket_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
