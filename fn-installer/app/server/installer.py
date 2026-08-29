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


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-installer")
# 运行时数据目录：优先用 TRIM_PKGVAR，回退到 /var/apps/<app>/var
_pkgvar = _env("TRIM_PKGVAR")
VAR_DIR = Path(_pkgvar) if _pkgvar else Path(f"/var/apps/{APP_NAME}/var")
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


def api_list_files():
    body = request_body()
    directory = body.get("directory", "")
    deadline = time.time() + SCAN_TIMEOUT
    if directory:
        files = scan_fpk_in_dir(directory, depth=0, deadline=deadline)
    else:
        files = scan_nas_fpk_files()
    return {"ok": True, "files": files}


def api_list_dir():
    body = request_body()
    directory = str(body.get("directory", "/")).strip()
    if not directory:
        directory = "/"
    entries = list_dir_entries(directory)
    return {"ok": True, "directory": directory, "entries": entries}


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


def dispatch():
    ensure_dirs()
    payload = request_body()
    action = payload.get("action", "list")
    if action == "list-files":
        json_response(api_list_files())
    elif action == "list-dir":
        json_response(api_list_dir())
    elif action == "parse-fpk":
        json_response(api_parse_fpk())
    elif action == "volumes":
        json_response(api_volumes())
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

    if os.path.exists(args.unix_socket):
        os.unlink(args.unix_socket)

    server = ThreadingUnixHTTPServer(
        args.unix_socket,
        Handler,
        base_path=args.base_path,
        www_root=args.www_root,
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
