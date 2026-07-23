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
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit

APP_NAME = "fn-installer"
APP_CENTER_SOCKET = "/var/run/com.trim.app.center.sock"
VAR_DIR = Path(f"/var/apps/{APP_NAME}/var")
SETTINGS_FILE = VAR_DIR / "settings.json"
SKIP_DIR_PREFIXES = (".", "@")
SKIP_DIR_NAMES = {
    "docker",
    "appcenter",
    "appcenter-downloads",
    "thumb",
    "mediasrv.transcode",
    "recycle",
    "lost+found",
    "proc",
    "sys",
    "dev",
}
MAX_SCAN_DEPTH = 3
MAX_RESULTS = 200
SCAN_TIMEOUT = 15

REQUEST_CONTEXT = threading.local()
INSTALL_TASKS = {}


def log(msg):
    sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    sys.stdout.flush()


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


def current_request():
    return getattr(REQUEST_CONTEXT, "value", {})


def header_value(headers, name):
    if not headers:
        return ""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


class ThreadingUnixHTTPServer(
    socketserver.ThreadingMixIn,
    socketserver.UnixStreamServer,  # pyright: ignore[reportAttributeAccessIssue]
):

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path, handler_cls, *, base_path, www_root):
        self.server_name = "fn-installer"
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
        if path.startswith("/api"):
            self.serve_api(parsed.query)
        else:
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
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

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


def ensure_dirs():
    VAR_DIR.mkdir(parents=True, exist_ok=True)


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
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        if handler.command != "HEAD":
            handler.wfile.write(body)
        return
    sys.stdout.write(f"Status: {status_text}\r\n")
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(body)


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


def incoming_token():
    request = current_request()
    if request == {}:
        return ""

    auth = header_value(request.get("headers", {}), "Authorization") or os.environ.get(
        "Authorization", ""
    )
    if auth.lower().startswith("trim "):
        return auth.split(None, 1)[1].strip()

    cookie = header_value(request.get("headers", {}), "Cookie") or os.environ.get(
        "HTTP_COOKIE", ""
    )
    if cookie:
        parsed = {}
        for part in str(cookie).split(";"):
            key, _, value = part.strip().partition("=")
            if key:
                parsed[key.lower()] = urllib.parse.unquote(value)

        for item_key, item_value in parsed.items():
            if "fnos-token" == item_key or "fnos-token" in item_key:
                return item_value
    return ""


def decode_chunked(data):
    output = bytearray()
    index = 0
    while index < len(data):
        line_end = data.find(b"\r\n", index)
        if line_end < 0:
            break
        size_text = data[index:line_end].split(b";", 1)[0].strip()
        try:
            size = int(size_text, 16)
        except ValueError:
            return data
        index = line_end + 2
        if size == 0:
            break
        output.extend(data[index : index + size])
        index += size + 2
    return bytes(output)


def unix_http(method, path, payload=None, timeout=30):
    if not os.path.exists(APP_CENTER_SOCKET):
        raise RuntimeError(f"app-center socket not found: {APP_CENTER_SOCKET}")
    token = incoming_token()
    if not token:
        raise RuntimeError("authorization token not found")
    body = b""
    headers = [
        f"{method} {path} HTTP/1.1",
        "Host: system",
        f"Authorization: trim {token}",
        "Accept: application/json",
        "Connection: close",
    ]
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers.extend(
            ["Content-Type: application/json", f"Content-Length: {len(body)}"]
        )
    request_data = ("\r\n".join(headers) + "\r\n\r\n").encode("utf-8") + body
    with socket.socket(
        socket.AF_UNIX,  # pyright: ignore[reportAttributeAccessIssue]
        socket.SOCK_STREAM,  # pyright: ignore[reportAttributeAccessIssue]
    ) as client:
        client.settimeout(timeout)
        client.connect(APP_CENTER_SOCKET)
        client.sendall(request_data)
        chunks = []
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    header, _, response_body = raw.partition(b"\r\n\r\n")
    header_text = header.decode("iso-8859-1", "replace")
    status_line = (
        header.splitlines()[0].decode("iso-8859-1", "replace") if header else ""
    )
    status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
    if "transfer-encoding: chunked" in header_text.lower():
        response_body = decode_chunked(response_body)
    text = response_body.decode("utf-8", "replace")
    if status_code >= 400:
        raise RuntimeError(f"app-center HTTP {status_code}: {text[:500]}")
    return json.loads(text or "{}")


def pick(obj, names, default=""):
    if not isinstance(obj, dict):
        return default
    for name in names:
        value = obj.get(name)
        if value not in (None, ""):
            return value
    return default


def _should_skip_dir(name):
    if name.startswith(SKIP_DIR_PREFIXES):
        return True
    if name in SKIP_DIR_NAMES:
        return True
    return False


def scan_fpk_in_dir(directory, depth=0, deadline=None):
    result = []
    if depth > MAX_SCAN_DEPTH:
        return result
    if deadline and time.time() > deadline:
        return result
    try:
        entries = list(os.scandir(directory))
    except (PermissionError, OSError):
        return result
    for entry in entries:
        if len(result) >= MAX_RESULTS:
            break
        if deadline and time.time() > deadline:
            break
        try:
            if entry.is_file(follow_symlinks=False) and entry.name.endswith(".fpk"):
                st = entry.stat()
                stem = entry.name[:-4]
                last_dash = stem.rfind("-")
                if last_dash > 0:
                    app_id = stem[:last_dash]
                    version = stem[last_dash + 1 :]
                else:
                    app_id = stem
                    version = ""
                result.append(
                    {
                        "name": entry.name,
                        "path": entry.path,
                        "appId": app_id,
                        "version": version,
                        "size": st.st_size,
                        "mtime": int(st.st_mtime),
                    }
                )
            elif entry.is_dir(follow_symlinks=False) and not _should_skip_dir(
                entry.name
            ):
                result.extend(scan_fpk_in_dir(entry.path, depth + 1, deadline))
        except (PermissionError, OSError):
            continue
    return result


def scan_nas_fpk_files():
    deadline = time.time() + SCAN_TIMEOUT
    result = []
    try:
        volumes = [d for d in os.listdir("/vol") if os.path.isdir(f"/vol/{d}")]
    except OSError:
        volumes = []
    if not volumes:
        try:
            volumes = [d for d in os.listdir("/vol1") if os.path.isdir(f"/vol1/{d}")]
        except OSError:
            volumes = []
    for vol in volumes:
        if time.time() > deadline:
            break
        vol_path = f"/vol/{vol}" if os.path.isdir(f"/vol/{vol}") else f"/vol1/{vol}"
        try:
            entries = list(os.scandir(vol_path))
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if len(result) >= MAX_RESULTS:
                break
            if time.time() > deadline:
                break
            try:
                if entry.is_dir(follow_symlinks=False) and not _should_skip_dir(
                    entry.name
                ):
                    result.extend(
                        scan_fpk_in_dir(entry.path, depth=1, deadline=deadline)
                    )
            except (PermissionError, OSError):
                continue
    return result[:MAX_RESULTS]


def list_dir_entries(directory):
    result = []
    try:
        entries = list(os.scandir(directory))
    except (PermissionError, OSError):
        return result
    for entry in entries:
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
            info = {
                "name": entry.name,
                "path": entry.path,
                "isDir": is_dir,
            }
            if not is_dir and entry.name.endswith(".fpk"):
                st = entry.stat()
                stem = entry.name[:-4]
                last_dash = stem.rfind("-")
                if last_dash > 0:
                    info["appId"] = stem[:last_dash]
                    info["version"] = stem[last_dash + 1 :]
                else:
                    info["appId"] = stem
                    info["version"] = ""
                info["size"] = st.st_size
                info["mtime"] = int(st.st_mtime)
            if is_dir or entry.name.endswith(".fpk"):
                result.append(info)
        except (PermissionError, OSError):
            continue
    result.sort(key=lambda x: (not x["isDir"], x["name"].lower()))
    return result


def parse_fpk_manifest(fpk_path):
    for tar_flag in ("-xzf", "-xf"):
        for manifest_name in (
            "manifest",
            "./manifest",
            "META-INF/manifest",
            "./META-INF/manifest",
        ):
            try:
                proc = subprocess.run(
                    ["tar", tar_flag, str(fpk_path), "-O", manifest_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    manifest = {}
                    for line in proc.stdout.strip().splitlines():
                        if "=" in line:
                            key, _, value = line.partition("=")
                            manifest[key.strip()] = value.strip()
                    if manifest:
                        return manifest
            except Exception:
                continue

    try:
        proc = subprocess.run(
            ["tar", "-tzf", str(fpk_path)], capture_output=True, text=True, timeout=10
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["tar", "-tf", str(fpk_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.strip().splitlines():
                name = line.strip().lstrip("./")
                if name.endswith("manifest") or name == "manifest":
                    try:
                        extract_proc = subprocess.run(
                            ["tar", "-xf", str(fpk_path), "-O", line.strip()],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        if extract_proc.returncode == 0 and extract_proc.stdout.strip():
                            manifest = {}
                            for mline in extract_proc.stdout.strip().splitlines():
                                if "=" in mline:
                                    key, _, value = mline.partition("=")
                                    manifest[key.strip()] = value.strip()
                            if manifest:
                                return manifest
                    except Exception:
                        continue
    except Exception:
        pass

    return None


def get_language():
    request = current_request()
    if request != {}:
        query = request.get("query", "")
        parsed = urllib.parse.parse_qs(query, keep_blank_values=True)
        lang = parsed.get("language", [None])[0]
        if lang:
            return lang
        cookie = header_value(request.get("headers", {}), "Cookie") or ""
        for part in cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key.strip().lower() == "language":
                return urllib.parse.unquote(value)
    return "zh-CN"


def api_list_files():
    body = request_body()
    directory = body.get("directory", "")
    deadline = time.time() + SCAN_TIMEOUT
    if directory:
        files = scan_fpk_in_dir(directory, depth=0, deadline=deadline)
    else:
        files = scan_nas_fpk_files()
    return {"ok": True, "files": files}


def _get_installed_apps():
    try:
        result = unix_http("GET", "/app-center/v1/app/list?language=zh-CN")
        items = []
        if isinstance(result, dict):
            data = result.get("data", result)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                for key in ("apps", "list", "items"):
                    val = data.get(key)
                    if isinstance(val, list):
                        items = val
                        break
                if not items and isinstance(data, dict):
                    items = [data]
        return items
    except Exception:
        return []


def _find_installed_app(app_name):
    if not app_name:
        return None
    apps = _get_installed_apps()
    for app in apps:
        if not isinstance(app, dict):
            continue
        name = str(
            app.get("appName", "") or app.get("name", "") or app.get("packageName", "")
        ).strip()
        if name == app_name:
            installed_version = str(app.get("installedVersion", "") or "").strip()
            installed_volume = str(app.get("installedVolumeID", "") or "").strip()
            if installed_version or installed_volume:
                return app
            return None
    return None


def api_list_dir():
    body = request_body()
    directory = str(body.get("directory", "/")).strip()
    if not directory:
        directory = "/"
    entries = list_dir_entries(directory)
    return {"ok": True, "directory": directory, "entries": entries}


def api_download_task():
    body = request_body()
    file_path = str(body.get("filePath", "")).strip()
    if not file_path:
        raise RuntimeError("filePath is required")
    if not os.path.isfile(file_path):
        raise RuntimeError(f"file not found: {file_path}")
    if not file_path.endswith(".fpk"):
        raise RuntimeError("only .fpk files are supported")

    manifest = parse_fpk_manifest(file_path)
    app_name = ""
    version = ""
    if manifest:
        app_name = manifest.get("appname", "")
        version = manifest.get("version", "")

    if not app_name:
        stem = Path(file_path).stem
        last_dash = stem.rfind("-")
        if last_dash > 0:
            app_name = stem[:last_dash]
            version = stem[last_dash + 1 :]

    volume_id = 1
    for prefix in ("/vol1/", "/vol2/", "/vol3/"):
        if file_path.startswith(prefix):
            try:
                volume_id = int(prefix.replace("/vol", "").replace("/", ""))
            except ValueError:
                volume_id = 1
            break

    language = get_language()
    payload = {
        "packageSourceType": "file",
        "path": file_path,
    }

    result = unix_http("POST", "/app-center/v1/download/task", payload)

    data = result.get("data", result) if isinstance(result, dict) else result
    if not isinstance(data, dict):
        data = result
    task_id = str(
        pick(
            data,
            ("downloadTaskId", "taskId", "id"),
            pick(
                result,
                ("downloadTaskId", "taskId", "id"),
                "",
            ),
        )
    )
    if not task_id:
        raise RuntimeError(
            f"failed to create download task: {json.dumps(result, ensure_ascii=False)[:500]}"
        )

    task_key = f"parse:{file_path}"
    INSTALL_TASKS[task_key] = {
        "filePath": file_path,
        "appName": app_name,
        "version": version,
        "taskId": task_id,
        "phase": "parsing",
        "status": "running",
        "progress": 0,
        "error": "",
        "raw": result,
        "createdAt": int(time.time()),
    }

    return {"ok": True, "taskId": task_id, "appName": app_name, "version": version}


def api_download_status():
    body = request_body()
    task_id = str(body.get("taskId", "")).strip()
    if not task_id:
        raise RuntimeError("taskId is required")

    language = get_language()
    result = unix_http(
        "GET",
        f"/app-center/v1/download/status?downloadTaskId={urllib.parse.quote(task_id)}&language={language}",
    )

    data = result.get("data", result) if isinstance(result, dict) else result
    if not isinstance(data, dict):
        data = result

    raw_status = pick(data, ("status", "downloadStatus"), "")
    progress = data.get("progress", 0)
    is_done = False
    status_value = ""

    if isinstance(raw_status, (int, float)):
        status_int = int(raw_status)
        if status_int == 0:
            status_value = "pending"
        elif status_int == 1:
            status_value = "running"
        elif status_int == 2:
            is_done = True
            status_value = "success"
        elif status_int == 3:
            is_done = True
            status_value = "failed"
        elif status_int == 4:
            is_done = True
            status_value = "cancelled"
        elif status_int == 5:
            is_done = True
            status_value = "notfound"
        else:
            status_value = str(raw_status)
    elif isinstance(raw_status, str):
        lower = raw_status.lower()
        if lower in (
            "done",
            "success",
            "succeed",
            "finished",
            "completed",
            "downloaded",
        ):
            is_done = True
            status_value = "success"
        elif lower in ("fail", "failed", "error"):
            is_done = True
            status_value = "failed"
        elif lower in ("cancel", "cancelled", "canceled"):
            is_done = True
            status_value = "cancelled"
        else:
            status_value = raw_status

    app_name = str(pick(data, ("appName", "app_name"), ""))
    version = str(pick(data, ("version", "app_version"), ""))

    if not app_name or not version:
        for key, task in INSTALL_TASKS.items():
            if task.get("taskId") == task_id:
                if not app_name and task.get("appName"):
                    app_name = task["appName"]
                if not version and task.get("version"):
                    version = task["version"]
                break

    for key, task in INSTALL_TASKS.items():
        if task.get("taskId") == task_id:
            task["progress"] = progress
            task["status"] = status_value
            if is_done:
                task["phase"] = "parsed" if status_value == "success" else "failed"
            if app_name:
                task["appName"] = app_name
            if version:
                task["version"] = version
            if isinstance(data, dict):
                if data.get("packageType"):
                    task["packageType"] = data["packageType"]
                if data.get("path"):
                    task["packagePath"] = data["path"]
            break

    installed = False
    installed_info = {}
    can_update = False

    if isinstance(data, dict):
        if "installed" in data:
            installed = bool(data["installed"])
        if "installedInfo" in data and isinstance(data["installedInfo"], dict):
            installed_info = data["installedInfo"]
        if "canUpgrade" in data:
            can_update = bool(data["canUpgrade"])

    if is_done and status_value == "success" and app_name:
        if not installed:
            existing = _find_installed_app(app_name)
            if existing:
                installed = True
                installed_version = str(
                    existing.get("installedVersion", "") or existing.get("version", "")
                ).strip()
                if not installed_info:
                    installed_info = {
                        "name": existing.get("displayName", "")
                        or existing.get("name", "")
                        or app_name,
                        "version": installed_version,
                        "volumeID": existing.get("installedVolumeID", "")
                        or existing.get("volumeID", ""),
                    }
        if installed and version:
            installed_version = (
                installed_info.get("version", "") if installed_info else ""
            )
            if not installed_version:
                existing = _find_installed_app(app_name)
                if existing:
                    installed_version = str(
                        existing.get("installedVersion", "")
                        or existing.get("version", "")
                    ).strip()
                    if not installed_info:
                        installed_info = {
                            "name": existing.get("displayName", "")
                            or existing.get("name", "")
                            or app_name,
                            "version": installed_version,
                            "volumeID": existing.get("installedVolumeID", "")
                            or existing.get("volumeID", ""),
                        }
            if installed_version and version != installed_version:
                can_update = True

    return {
        "ok": True,
        "taskId": task_id,
        "status": status_value,
        "progress": progress,
        "isDone": is_done,
        "appName": app_name,
        "version": version,
        "installed": installed,
        "installedInfo": installed_info,
        "canUpdate": can_update,
    }


def api_volumes():
    volumes = []
    for vol_path in ("/vol1", "/vol2", "/vol3", "/vol"):
        if not os.path.isdir(vol_path):
            continue
        try:
            stat = os.statvfs(vol_path)  # pyright: ignore[reportAttributeAccessIssue]
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            used = total - free
            vol_id = vol_path.lstrip("/vol")
            try:
                vol_id = int(vol_id) if vol_id else 1
            except ValueError:
                vol_id = 1
            volumes.append(
                {
                    "id": vol_id,
                    "name": os.path.basename(vol_path),
                    "path": vol_path,
                    "size": total,
                    "used": used,
                }
            )
        except (PermissionError, OSError):
            continue
    if not volumes:
        volumes = [{"id": 1, "name": "vol1", "path": "/vol1", "size": 0, "used": 0}]
    return {"ok": True, "volumes": volumes}


def api_default_volume():
    try:
        result = unix_http("GET", "/app-center/v1/common/remember-volume/config")
        data = result.get("data", result) if isinstance(result, dict) else result
        volume_id = 1
        if isinstance(data, dict):
            vid = data.get("downloadAndInstallVolumeID") or data.get("volumeID")
            if vid is not None:
                try:
                    volume_id = int(vid)
                except (ValueError, TypeError):
                    volume_id = 1
        return {"ok": True, "volumeID": volume_id}
    except Exception:
        return {"ok": True, "volumeID": 1}


def wizard_defaults_from_items(items):
    defaults = {}
    if not isinstance(items, list):
        return defaults
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("items")
        if isinstance(nested, list):
            defaults.update(wizard_defaults_from_items(nested))
            continue
        field = item.get("field") or item.get("key") or item.get("name")
        if not field:
            continue
        value = item.get("initValue", item.get("defaultValue", item.get("value", "")))
        defaults[str(field)] = value
    return defaults


def wizard_defaults_from_info(info):
    data = info.get("data", info) if isinstance(info, dict) else {}
    wizard_info = data.get("wizardInfo", data) if isinstance(data, dict) else {}
    if not isinstance(wizard_info, dict):
        return {}
    return wizard_defaults_from_items(
        wizard_info.get("wizardContent")
        or wizard_info.get("steps")
        or data.get("wizard")
        or data.get("wizardData")
        or []
    )


def custom_parameters_list(parameters):
    if isinstance(parameters, list):
        return parameters
    if not isinstance(parameters, dict):
        return []
    result = []
    for key, value in parameters.items():
        result.append(
            {
                "key": str(key),
                "value": "" if value is None else str(value),
            }
        )
    return result


def api_install_info():
    body = request_body()
    app_name = str(body.get("appName", "")).strip()
    version = str(body.get("version", "")).strip()
    download_task_id = str(body.get("downloadTaskId", "")).strip()
    is_update = bool(body.get("isUpdate") or body.get("upgrade"))

    if not app_name and download_task_id:
        for key, task in INSTALL_TASKS.items():
            if task.get("taskId") == download_task_id:
                if not app_name and task.get("appName"):
                    app_name = task["appName"]
                if not version and task.get("version"):
                    version = task["version"]
                break

    if not app_name:
        raise RuntimeError("appName is required")

    existing = _find_installed_app(app_name)
    installed = existing is not None
    installed_info = {}
    can_update = False
    if existing:
        installed_version = str(
            existing.get("installedVersion", "") or existing.get("version", "")
        ).strip()
        installed_info = {
            "name": existing.get("displayName", "")
            or existing.get("name", "")
            or app_name,
            "version": installed_version,
            "volumeID": existing.get("installedVolumeID", "")
            or existing.get("volumeID", ""),
        }
        if version and installed_version and version != installed_version:
            can_update = True
            is_update = True

    language = get_language()
    resolved_package_type = "file"
    for key, task in INSTALL_TASKS.items():
        if task.get("appName") == app_name and task.get("packageType"):
            resolved_package_type = task["packageType"]
            break

    if is_update and installed:
        url = f"/app-center/v1/update/info?updateVersion={urllib.parse.quote(version)}&appName={urllib.parse.quote(app_name)}&packageType={resolved_package_type}&language={language}"
    else:
        url = f"/app-center/v1/install/info?version={urllib.parse.quote(version)}&appName={urllib.parse.quote(app_name)}&packageType={resolved_package_type}&language={language}"

    last_error = None
    for attempt in range(10):
        result = unix_http("GET", url)
        code = result.get("code", 0) if isinstance(result, dict) else 0
        if code == 0:
            INSTALL_TASKS[f"install-info:{app_name}:{version}"] = {
                "appName": app_name,
                "version": version,
                "wizardDefaults": wizard_defaults_from_info(result),
                "raw": result,
                "createdAt": int(time.time()),
            }
            return {
                "ok": True,
                "info": result,
                "installed": installed,
                "installedInfo": installed_info,
                "canUpdate": can_update,
            }
        if code == 10100:
            last_error = result
            time.sleep(2)
            continue
        if code == 10371 and is_update and installed:
            existing = _find_installed_app(app_name)
            upgrade_info = (
                existing.get("upgradeInfo") if isinstance(existing, dict) else None
            )
            if isinstance(upgrade_info, dict) and upgrade_info.get("version"):
                cloud_version = str(upgrade_info.get("version", "")).strip()
                source_id = upgrade_info.get("sourceID") or (
                    existing.get("sourceID") if isinstance(existing, dict) else None
                )
                version_id = upgrade_info.get("versionID")
                cloud_url = f"/app-center/v1/update/info?updateVersion={urllib.parse.quote(cloud_version)}&appName={urllib.parse.quote(app_name)}&packageType=cloud&language={language}"
                if source_id:
                    cloud_url += f"&sourceID={str(source_id)}"
                if version_id:
                    cloud_url += f"&versionID={str(version_id)}"
                cloud_result = unix_http("GET", cloud_url)
                cloud_code = (
                    cloud_result.get("code", 0) if isinstance(cloud_result, dict) else 0
                )
                if cloud_code == 0:
                    INSTALL_TASKS[f"install-info:{app_name}:{version}"] = {
                        "appName": app_name,
                        "version": version,
                        "wizardDefaults": wizard_defaults_from_info(cloud_result),
                        "raw": cloud_result,
                        "createdAt": int(time.time()),
                    }
                    return {
                        "ok": True,
                        "info": cloud_result,
                        "installed": installed,
                        "installedInfo": installed_info,
                        "canUpdate": can_update,
                    }
            fallback_url = f"/app-center/v1/install/info?version={urllib.parse.quote(version)}&appName={urllib.parse.quote(app_name)}&packageType={resolved_package_type}&language={language}"
            fallback_result = unix_http("GET", fallback_url)
            fallback_code = (
                fallback_result.get("code", 0)
                if isinstance(fallback_result, dict)
                else 0
            )
            if fallback_code == 0:
                INSTALL_TASKS[f"install-info:{app_name}:{version}"] = {
                    "appName": app_name,
                    "version": version,
                    "wizardDefaults": wizard_defaults_from_info(fallback_result),
                    "raw": fallback_result,
                    "createdAt": int(time.time()),
                }
                return {
                    "ok": True,
                    "info": fallback_result,
                    "installed": installed,
                    "installedInfo": installed_info,
                    "canUpdate": can_update,
                }
            last_error = fallback_result
            break
        last_error = result
        break

    raise RuntimeError(
        f"install info failed: {json.dumps(last_error, ensure_ascii=False)[:500]}"
    )


def _try_cloud_download(app_name, version, language):
    existing = _find_installed_app(app_name)
    if not existing or not isinstance(existing, dict):
        log(f"_try_cloud_download: app {app_name} not found in installed list")
        return None
    upgrade_info = existing.get("upgradeInfo")
    if not isinstance(upgrade_info, dict):
        log(f"_try_cloud_download: no upgradeInfo for {app_name}")
        return None
    upgrade_version = str(upgrade_info.get("version", "")).strip()
    if not upgrade_version:
        log(f"_try_cloud_download: no upgrade version for {app_name}")
        return None
    source_id = upgrade_info.get("sourceID") or existing.get("sourceID")
    version_id = upgrade_info.get("versionID")
    download_payload = {
        "appName": app_name,
        "version": upgrade_version,
    }
    if source_id:
        download_payload["sourceID"] = str(source_id)
    if version_id:
        download_payload["versionID"] = str(version_id)
    log(
        f"_try_cloud_download: payload={json.dumps(download_payload, ensure_ascii=False)}"
    )
    result = unix_http("POST", "/app-center/v1/download/task", download_payload)
    log(f"_try_cloud_download: response={json.dumps(result, ensure_ascii=False)[:500]}")
    code = result.get("code", 0) if isinstance(result, dict) else 0
    if code != 0 and not (isinstance(result, dict) and result.get("data")):
        log(f"_try_cloud_download: download/task failed with code {code}")
        return None
    data = result.get("data", result) if isinstance(result, dict) else result
    if not isinstance(data, dict):
        data = result
    task_id = str(pick(data, ("downloadTaskId", "taskId", "id"), ""))
    if not task_id:
        log(f"_try_cloud_download: no taskId in response")
        return None
    log(
        f"_try_cloud_download: download task created, taskId={task_id}, polling status..."
    )
    for i in range(120):
        time.sleep(1)
        status_result = unix_http(
            "GET",
            f"/app-center/v1/download/status?downloadTaskId={urllib.parse.quote(task_id)}&language={language}",
        )
        status_data = (
            status_result.get("data", status_result)
            if isinstance(status_result, dict)
            else status_result
        )
        if not isinstance(status_data, dict):
            status_data = status_result
        raw_status = pick(status_data, ("status", "downloadStatus"), "")
        if isinstance(raw_status, (int, float)):
            status_int = int(raw_status)
        elif isinstance(raw_status, str):
            try:
                status_int = int(raw_status)
            except ValueError:
                lower = raw_status.lower()
                if lower in (
                    "done",
                    "success",
                    "succeed",
                    "finished",
                    "completed",
                    "downloaded",
                ):
                    status_int = 2
                elif lower in ("fail", "failed", "error"):
                    status_int = 3
                else:
                    status_int = 0
        else:
            status_int = 0
        if status_int == 2:
            package_type = str(
                status_data.get("packageType", "")
                or status_data.get("packageSourceType", "")
            ).strip()
            package_path = str(status_data.get("path", "")).strip()
            log(
                f"_try_cloud_download: download complete, packageType={package_type}, path={package_path}"
            )
            return {
                "packageType": package_type,
                "path": package_path,
                "version": upgrade_version,
            }
        if status_int in (3, 4, 5):
            log(f"_try_cloud_download: download failed with status {status_int}")
            return None
        if i % 10 == 0:
            log(f"_try_cloud_download: polling {i}, status={status_int}")
    log(f"_try_cloud_download: download timed out after 120s")
    return None


def _try_cloud_update(
    app_name, version, language, system_parameters, custom_parameters
):
    download_info = _try_cloud_download(app_name, version, language)
    if not download_info or not isinstance(download_info, dict):
        return None
    package_type = download_info.get("packageType", "path")
    package_path = download_info.get("path", "")
    upgrade_version = download_info.get("version", version)
    if package_type == "file" and package_path:
        package_type = "path"
    install_payload = {
        "appName": app_name,
        "version": upgrade_version,
        "packageType": package_type,
        "volumeID": system_parameters.get("installVolumeID", 1),
        "installVolumeID": system_parameters.get("installVolumeID", 1),
        "dataVolumeID": system_parameters.get(
            "dataVolumeID", system_parameters.get("installVolumeID", 1)
        ),
        "language": language,
        "immediateStart": True,
        "upgrade": True,
    }
    if package_path and package_type == "path":
        install_payload["path"] = package_path
    install_payload["systemParameters"] = system_parameters
    if custom_parameters:
        install_payload["customParameters"] = custom_parameters_list(custom_parameters)
    log(
        f"_try_cloud_update: install/task payload={json.dumps(install_payload, ensure_ascii=False)}"
    )
    result = unix_http("POST", "/app-center/v1/install/task", install_payload)
    log(
        f"_try_cloud_update: install/task response={json.dumps(result, ensure_ascii=False)[:500]}"
    )
    code = result.get("code", 0) if isinstance(result, dict) else 0
    if code == 0 or (isinstance(result, dict) and result.get("data")):
        return result
    update_payload = {
        "appName": app_name,
        "packageType": package_type,
        "updateVersion": upgrade_version,
        "language": language,
        "immediateStart": True,
        "systemParameters": {
            "installVolumeID": system_parameters.get("installVolumeID", 1),
            "dataVolumeID": system_parameters.get(
                "dataVolumeID", system_parameters.get("installVolumeID", 1)
            ),
        },
    }
    if package_path and package_type == "path":
        update_payload["path"] = package_path
    if custom_parameters:
        update_payload["customParameters"] = custom_parameters_list(custom_parameters)
    existing = _find_installed_app(app_name)
    if existing and isinstance(existing, dict):
        upgrade_info = existing.get("upgradeInfo")
        if isinstance(upgrade_info, dict):
            source_id = upgrade_info.get("sourceID") or existing.get("sourceID")
            version_id = upgrade_info.get("versionID")
            if source_id:
                update_payload["sourceID"] = str(source_id)
            if version_id:
                update_payload["versionID"] = str(version_id)
    log(
        f"_try_cloud_update: update/task payload={json.dumps(update_payload, ensure_ascii=False)}"
    )
    result = unix_http("POST", "/app-center/v1/update/task", update_payload)
    log(
        f"_try_cloud_update: update/task response={json.dumps(result, ensure_ascii=False)[:500]}"
    )
    code = result.get("code", 0) if isinstance(result, dict) else 0
    if code == 0 or (isinstance(result, dict) and result.get("data")):
        return result
    return None


def api_install_task():
    body = request_body()
    app_name = str(body.get("appName", "")).strip()
    version = str(body.get("version", "")).strip()
    volume_id = int(
        body.get("volumeID")
        or body.get("volume_id")
        or body.get("installVolumeID")
        or body.get("dataVolumeID")
        or 1
    )
    wizard_data = body.get("wizardData", {})
    system_parameters = body.get("systemParameters", {})
    custom_parameters = body.get("customParameters", {})
    custom_parameters_dict = {}
    if isinstance(custom_parameters, list):
        for item in custom_parameters:
            if not isinstance(item, dict):
                continue
            key = item.get("field") or item.get("name") or item.get("key")
            if key:
                custom_parameters_dict[str(key)] = item.get("value", "")
    elif isinstance(custom_parameters, dict):
        custom_parameters_dict = custom_parameters
    if not isinstance(wizard_data, dict):
        wizard_data = {}
    if not isinstance(system_parameters, dict):
        system_parameters = {}
    if not app_name:
        raise RuntimeError("appName is required")
    if not version:
        for key, task in INSTALL_TASKS.items():
            if task.get("appName") == app_name and task.get("version"):
                version = task["version"]
                break
    if not version:
        raise RuntimeError("version is required for install")

    language = get_language()
    is_update = bool(body.get("isUpdate") or body.get("upgrade"))
    if is_update and not body.get("volumeID") and not body.get("volume_id"):
        existing = _find_installed_app(app_name)
        if existing:
            vid = existing.get("installedVolumeID") or existing.get("volumeID")
            if vid:
                try:
                    volume_id = int(vid)
                except (ValueError, TypeError):
                    pass

    resolved_package_type = "file"
    for key, task in INSTALL_TASKS.items():
        if task.get("appName") == app_name and task.get("packageType"):
            resolved_package_type = task["packageType"]
            break

    merged_custom_parameters = {}
    cached_info = INSTALL_TASKS.get(f"install-info:{app_name}:{version}", {})
    cached_wizard_defaults = cached_info.get("wizardDefaults", {})
    if isinstance(cached_wizard_defaults, dict):
        merged_custom_parameters.update(cached_wizard_defaults)
    merged_custom_parameters.update(wizard_data)
    merged_custom_parameters.update(custom_parameters_dict)

    merged_system_parameters = {}
    merged_system_parameters.update(system_parameters)
    merged_system_parameters.update(
        {
            "installVolumeID": volume_id,
            "dataVolumeID": volume_id,
            "INSTALL_VOLUME_ID": str(volume_id),
        }
    )

    install_payload = {
        "appName": app_name,
        "version": version,
        "packageType": resolved_package_type,
        "volumeID": volume_id,
        "installVolumeID": volume_id,
        "dataVolumeID": volume_id,
        "language": language,
        "immediateStart": True,
    }
    if wizard_data:
        install_payload["wizardData"] = wizard_data
    install_payload["systemParameters"] = merged_system_parameters
    if merged_custom_parameters:
        install_payload["customParameters"] = custom_parameters_list(
            merged_custom_parameters
        )

    update_payload = {
        "appName": app_name,
        "packageType": resolved_package_type,
        "updateVersion": version,
        "language": language,
        "immediateStart": True,
        "systemParameters": {
            "installVolumeID": volume_id,
            "dataVolumeID": volume_id,
        },
    }
    if merged_custom_parameters:
        update_payload["customParameters"] = custom_parameters_list(
            merged_custom_parameters
        )

    code_messages = {
        10100: "invalid parameters or app not ready for installation",
        10101: "app already installed",
        10102: "install volume unavailable",
        10103: "package not found or not downloaded",
        10104: "install conflict with existing app",
        10236: "app already installed",
        10371: "update package not available",
    }

    result = None
    used_update_api = False

    if is_update:
        log(
            f"is_update=true, trying update/task with packageType={resolved_package_type}"
        )
        result = unix_http("POST", "/app-center/v1/update/task", update_payload)
        log(f"update/task response: {json.dumps(result, ensure_ascii=False)[:500]}")
        code = result.get("code", 0) if isinstance(result, dict) else 0
        if code == 0 or (isinstance(result, dict) and result.get("data")):
            used_update_api = True
        else:
            log(
                f"update/task failed (code={code}), trying install/task with upgrade=true"
            )
            install_upgrade_payload = dict(install_payload)
            install_upgrade_payload["upgrade"] = True
            result = unix_http(
                "POST", "/app-center/v1/install/task", install_upgrade_payload
            )
            log(
                f"install/task (upgrade) response: {json.dumps(result, ensure_ascii=False)[:500]}"
            )
            code = result.get("code", 0) if isinstance(result, dict) else 0
            if code == 0 or (isinstance(result, dict) and result.get("data")):
                pass
            elif code in (10236, 10371, 10100):
                log(
                    f"install/task upgrade failed (code={code}), trying cloud download + install"
                )
                cloud_result = _try_cloud_update(
                    app_name,
                    version,
                    language,
                    merged_system_parameters,
                    merged_custom_parameters,
                )
                if cloud_result is not None:
                    result = cloud_result
                    used_update_api = True
                else:
                    log(f"cloud update also failed, returning last error")
            else:
                log(f"install/task upgrade failed with unexpected code={code}")

    if result is None:
        log(f"not update path, trying install/task")
        result = unix_http("POST", "/app-center/v1/install/task", install_payload)
        log(f"install/task response: {json.dumps(result, ensure_ascii=False)[:500]}")
        code = result.get("code", 0) if isinstance(result, dict) else 0
        if code != 0 and not (isinstance(result, dict) and result.get("data")):
            if code == 10236:
                log(f"install/task got 10236 (already installed), trying cloud update")
                cloud_result = _try_cloud_update(
                    app_name,
                    version,
                    language,
                    merged_system_parameters,
                    merged_custom_parameters,
                )
                if cloud_result is not None:
                    result = cloud_result
                    used_update_api = True

    if isinstance(result, dict) and result.get("code") and not result.get("data"):
        error_code = result.get("code", 0)
        error_msg = result.get("msg", "") or result.get("message", "")
        hint = code_messages.get(error_code, "unknown error")
        raise RuntimeError(f"install failed ({error_code}): {error_msg or hint}")

    data = result.get("data", result) if isinstance(result, dict) else result
    if not isinstance(data, dict):
        data = result
    install_task_id = str(
        pick(
            data,
            ("installTaskId", "taskId", "id"),
            pick(
                result,
                ("installTaskId", "taskId", "id"),
                "",
            ),
        )
    )
    if not install_task_id:
        raise RuntimeError(
            f"failed to create install task: {json.dumps(result, ensure_ascii=False)[:500]}"
        )

    task_key = f"install:{app_name}"
    INSTALL_TASKS[task_key] = {
        "appName": app_name,
        "version": version,
        "volumeID": volume_id,
        "installVolumeID": volume_id,
        "dataVolumeID": volume_id,
        "taskId": install_task_id,
        "phase": "installing",
        "status": "running",
        "progress": 0,
        "error": "",
        "isUpdate": is_update,
        "usedUpdateApi": used_update_api,
        "raw": result,
        "createdAt": int(time.time()),
    }

    return {
        "ok": True,
        "taskId": install_task_id,
        "appName": app_name,
        "isUpdate": is_update,
    }


def api_install_status():
    body = request_body()
    app_name = str(body.get("appName", "")).strip()
    task_id = str(body.get("taskId", "")).strip()
    is_update = bool(body.get("isUpdate"))
    if not app_name:
        raise RuntimeError("appName is required")

    language = get_language()
    task_key = f"install:{app_name}"
    used_update_api = False
    if task_key in INSTALL_TASKS:
        if not task_id:
            task_id = str(INSTALL_TASKS[task_key].get("taskId", ""))
        stored_is_update = INSTALL_TASKS[task_key].get("isUpdate", False)
        is_update = stored_is_update
        used_update_api = INSTALL_TASKS[task_key].get("usedUpdateApi", False)

    if not task_id:
        raise RuntimeError("install taskId is required")

    def query_install_status(tid, use_update_api):
        if use_update_api:
            return unix_http(
                "POST",
                "/app-center/v1/update/status",
                {"taskId": tid, "language": language},
            )
        return unix_http(
            "POST",
            "/app-center/v1/common/task-status",
            {"taskId": tid, "language": language},
        )

    result = query_install_status(task_id, used_update_api)
    data = result.get("data", result) if isinstance(result, dict) else result
    if isinstance(data, dict):
        raw_status = pick(data, ("status", "installStatus"), "")
        if isinstance(raw_status, (int, float)) and int(raw_status) == 5:
            fallback_result = query_install_status(task_id, not used_update_api)
            fallback_data = (
                fallback_result.get("data", fallback_result)
                if isinstance(fallback_result, dict)
                else fallback_result
            )
            if isinstance(fallback_data, dict):
                fallback_status = pick(fallback_data, ("status", "installStatus"), "")
                if (
                    isinstance(fallback_status, (int, float))
                    and int(fallback_status) != 5
                ):
                    result = fallback_result
                    data = fallback_data

    data = result.get("data", result) if isinstance(result, dict) else result
    if not isinstance(data, dict):
        data = result

    raw_status = pick(data, ("status", "installStatus"), "")
    progress = data.get("progress", 0)
    output_text = str(pick(data, ("outputText", "message", "msg"), ""))
    if not output_text and isinstance(result, dict):
        output_text = str(result.get("msg", "") or result.get("message", "") or "")
    error_code = (
        data.get("errorCode")
        or data.get("code")
        or (result.get("code") if isinstance(result, dict) else 0)
    )
    if error_code and not output_text:
        output_text = f"error code: {error_code}"
    is_done = False
    status_value = ""

    if isinstance(raw_status, (int, float)):
        status_int = int(raw_status)
        if status_int == 0:
            status_value = "pending"
        elif status_int == 1:
            status_value = "running"
        elif status_int == 2:
            is_done = True
            status_value = "success"
        elif status_int == 3:
            is_done = True
            status_value = "failed"
        elif status_int == 4:
            is_done = True
            status_value = "cancelled"
        elif status_int == 5:
            is_done = True
            status_value = "failed"
            if not output_text:
                output_text = (
                    "task not found in app center, install may have failed to start"
                )
        else:
            status_value = str(raw_status)
    elif isinstance(raw_status, str):
        lower = raw_status.lower()
        if lower in (
            "done",
            "success",
            "succeed",
            "finished",
            "completed",
            "installed",
        ):
            is_done = True
            status_value = "success"
        elif lower in ("fail", "failed", "error"):
            is_done = True
            status_value = "failed"
        elif lower in ("cancel", "cancelled", "canceled"):
            is_done = True
            status_value = "cancelled"
        else:
            status_value = raw_status

    if task_key in INSTALL_TASKS:
        INSTALL_TASKS[task_key]["progress"] = progress
        INSTALL_TASKS[task_key]["status"] = status_value
        if is_done:
            INSTALL_TASKS[task_key]["phase"] = "done"

    return {
        "ok": True,
        "appName": app_name,
        "taskId": task_id,
        "status": status_value,
        "progress": progress,
        "message": output_text,
        "isDone": is_done,
    }


def api_parse_fpk():
    body = request_body()
    file_path = str(body.get("filePath", "")).strip()
    if not file_path:
        raise RuntimeError("filePath is required")
    if not os.path.isfile(file_path):
        raise RuntimeError(f"file not found: {file_path}")

    manifest = parse_fpk_manifest(file_path)
    if not manifest:
        return {"ok": True, "manifest": None}

    return {"ok": True, "manifest": manifest}


def api_task_status():
    body = request_body()
    task_id = str(body.get("taskId", "")).strip()
    phase = str(body.get("phase", "")).strip()
    app_name = str(body.get("appName", "")).strip()

    for key, task in INSTALL_TASKS.items():
        if task_id and task.get("taskId") == task_id:
            return {"ok": True, "task": task}
        if app_name and task.get("appName") == app_name and task.get("phase") == phase:
            return {"ok": True, "task": task}

    return {"ok": True, "task": {}}


def api_installed_app():
    body = request_body()
    app_name = str(body.get("appName", "")).strip()
    if not app_name:
        return {"ok": True, "installed": False, "installedInfo": {}}
    existing = _find_installed_app(app_name)
    if not existing:
        return {"ok": True, "installed": False, "installedInfo": {}}
    installed_version = str(
        existing.get("installedVersion", "") or existing.get("version", "")
    ).strip()
    return {
        "ok": True,
        "installed": True,
        "installedInfo": {
            "name": existing.get("displayName", "")
            or existing.get("name", "")
            or app_name,
            "version": installed_version,
            "volumeID": existing.get("installedVolumeID", "")
            or existing.get("volumeID", ""),
        },
    }


def dispatch():
    ensure_dirs()
    payload = request_body()
    action = payload.get("action", "list")
    if action == "list-files":
        json_response(api_list_files())
    elif action == "list-dir":
        json_response(api_list_dir())
    elif action == "parse-task":
        json_response(api_download_task())
    elif action == "parse-status":
        json_response(api_download_status())
    elif action == "install-info":
        json_response(api_install_info())
    elif action == "install-task":
        json_response(api_install_task())
    elif action == "install-status":
        json_response(api_install_status())
    elif action == "parse-fpk":
        json_response(api_parse_fpk())
    elif action == "task-status":
        json_response(api_task_status())
    elif action == "volumes":
        json_response(api_volumes())
    elif action == "default-volume":
        json_response(api_default_volume())
    elif action == "installed-app":
        json_response(api_installed_app())
    else:
        json_response(
            {"ok": False, "message": f"unsupported action: {action}"}, "400 Bad Request"
        )


def main():
    parser = argparse.ArgumentParser(description="fn-installer Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-installer")
    parser.add_argument("--www-root", required=True)
    args = parser.parse_args()

    try:
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)
    except OSError:
        pass

    server = ThreadingUnixHTTPServer(
        args.unix_socket,
        Handler,
        base_path=args.base_path,
        www_root=args.www_root,
    )

    def shutdown(_signum, _frame):
        server.server_close()
        try:
            if os.path.exists(args.unix_socket):
                os.unlink(args.unix_socket)
        except OSError:
            pass
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
