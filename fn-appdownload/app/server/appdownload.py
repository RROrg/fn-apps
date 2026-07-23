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
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit

APP_NAME = "fn-appdownload"
APP_CENTER_SOCKET = "/var/run/com.trim.app.center.sock"
VAR_DIR = Path(f"/var/apps/{APP_NAME}/var")
SHARE_DIR = Path(f"/var/apps/{APP_NAME}/shares/{APP_NAME}")
DEFAULT_DOWNLOAD_DIR = SHARE_DIR / "downloads"
SETTINGS_FILE = VAR_DIR / "settings.json"
DEFAULT_SETTINGS = {
    "downloadDir": str(DEFAULT_DOWNLOAD_DIR),
    "thirdPartySources": [
        {
            "name": "RROrg",
            "url": "https://raw.githubusercontent.com/RROrg/fn-apps/refs/heads/main/fnpack.json",
            "enabled": True,
        }
    ],
    "githubProxyEnabled": True,
    "githubProxyUrl": "https://gh-proxy.com/",
}

REQUEST_CONTEXT = threading.local()
TASKS_STATE = {"tasks": {}}

GITHUB_DOMAINS = (
    "https://github.com/",
    "https://api.github.com/",
    "https://raw.githubusercontent.com/",
    "https://user-images.githubusercontent.com/",
    "https://release-assets.githubusercontent.com/",
    "https://github-releases.githubusercontent.com/",
)


def apply_github_proxy(url, settings=None):
    if not url or not isinstance(url, str):
        return url or ""
    if settings is None:
        settings = read_settings()
    if not settings.get("githubProxyEnabled", True):
        return url
    proxy_url = str(settings.get("githubProxyUrl") or "").strip()
    if not proxy_url:
        return url
    proxy_base = proxy_url.rstrip("/")
    if url.startswith(proxy_base + "/") or url == proxy_base:
        return url
    for domain in GITHUB_DOMAINS:
        if url.startswith(domain):
            return proxy_base + "/" + url
    return url


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
    download_dir().mkdir(parents=True, exist_ok=True)


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


def read_json_file(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return fallback


def write_json_file(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_settings():
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        write_json_file(SETTINGS_FILE, DEFAULT_SETTINGS)
    data = read_json_file(SETTINGS_FILE, DEFAULT_SETTINGS)
    sources = data.get("thirdPartySources")
    if not isinstance(sources, list):
        data["thirdPartySources"] = []
    download_dir_value = str(data.get("downloadDir") or "").strip()
    if not download_dir_value:
        data["downloadDir"] = str(DEFAULT_DOWNLOAD_DIR)
    if data.get("githubProxyEnabled") is None:
        data["githubProxyEnabled"] = True
    if not data.get("githubProxyUrl"):
        data["githubProxyUrl"] = DEFAULT_SETTINGS.get(
            "githubProxyUrl", "https://gh-proxy.com/"
        )
    return data


def download_dir(settings=None):
    data = settings or read_json_file(SETTINGS_FILE, DEFAULT_SETTINGS)
    path = str(data.get("downloadDir") or DEFAULT_DOWNLOAD_DIR).strip()
    if not path.startswith("/"):
        path = str(DEFAULT_DOWNLOAD_DIR)
    return Path(path)


def read_tasks():
    tasks = TASKS_STATE
    if not isinstance(tasks.get("tasks"), dict):
        tasks["tasks"] = {}
    return tasks


def save_tasks(_data):
    return


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


def unix_http(method, path, payload=None, timeout=15, token_override=None):
    if not os.path.exists(APP_CENTER_SOCKET):
        raise RuntimeError(f"socket not found: {APP_CENTER_SOCKET}")
    token = token_override or incoming_token()
    if not token:
        raise RuntimeError(
            "app-center token not found; open the app from fnOS desktop so gateway headers can be captured"
        )
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
    request = ("\r\n".join(headers) + "\r\n\r\n").encode("utf-8") + body
    with socket.socket(
        socket.AF_UNIX,  # pyright: ignore[reportAttributeAccessIssue]
        socket.SOCK_STREAM,  # pyright: ignore[reportAttributeAccessIssue]
    ) as client:
        client.settimeout(timeout)
        client.connect(APP_CENTER_SOCKET)
        client.sendall(request)
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
        raise RuntimeError(f"app-center HTTP {status_code}: {text[:200]}")
    return json.loads(text or "{}")


def first_array(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("apps", "list", "items", "data", "result", "records"):
            found = first_array(value.get(key))
            if found:
                return found
    return []


def pick(obj, names, default=""):
    if not isinstance(obj, dict):
        return default
    for name in names:
        value = obj.get(name)
        if value not in (None, ""):
            return value
    return default


def task_key(store, app_id, version):
    return f"{store}:{app_id}:{version}"


def file_name_for(app_id, version):
    safe = "".join(
        ch if ch.isalnum() or ch in "._-" else "_" for ch in f"{app_id}-{version}"
    )
    return f"{safe}.fpk"


def download_path_for(app_id, version, settings=None):
    return download_dir(settings) / file_name_for(app_id, version)


def task_file_exists(task):
    app_id = str(task.get("appId", ""))
    version = str(task.get("version", ""))
    candidates = []
    if app_id and version:
        candidates.append(download_path_for(app_id, version))
    task_path = str(task.get("path") or "").strip()
    if task_path:
        candidates.append(Path(task_path))
    return any(path.exists() for path in candidates)


def file_status_for_apps(apps):
    files = {}
    if not isinstance(apps, list):
        return files
    for app in apps:
        if not isinstance(app, dict):
            continue
        store = str(app.get("store") or "")
        app_id = str(app.get("id") or "")
        version = str(app.get("version") or "")
        if not store or not app_id or not version:
            continue
        key = task_key(store, app_id, version)
        target = download_path_for(app_id, version)
        exists = target.exists()
        files[key] = {"exists": exists, "path": str(target) if exists else ""}
    return files


def is_done_status(status):
    normalized = str(status or "").lower()
    return normalized in {
        "done",
        "success",
        "succeed",
        "finished",
        "completed",
        "downloaded",
    } or status in {"已下载", "下载完成"}


def first_path_value(value):
    if isinstance(value, dict):
        for key in ("path", "downloadPath", "packagePath", "filePath", "targetPath"):
            found = value.get(key)
            if isinstance(found, str) and found.startswith("/"):
                return found
        for item in value.values():
            found = first_path_value(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = first_path_value(item)
            if found:
                return found
    return ""


def appcenter_download_dir(app_id, version):
    name = "".join(
        ch if ch.isalnum() or ch in "._-" else "_" for ch in f"{app_id}-{version}"
    )
    return Path("/vol1/appcenter-downloads") / f"{name}-tpk"


def source_path_for_official(task, raw):
    source_path = first_path_value(raw)
    if source_path:
        return source_path
    inferred = appcenter_download_dir(task.get("appId", ""), task.get("version", ""))
    return str(inferred) if inferred.is_dir() else ""


def package_official_download(app_id, version, source_path):
    source = Path(str(source_path))
    target = download_path_for(app_id, version)
    if target.exists():
        return str(target)
    if not source.is_dir():
        return ""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        subprocess.run(
            ["tar", "-czf", str(tmp), "-C", str(source), "."],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    except subprocess.CalledProcessError as exc:
        if tmp.exists():
            tmp.unlink()
        detail = (
            exc.stderr.decode("utf-8", "replace").strip()
            if exc.stderr
            else "tar failed"
        )
        raise RuntimeError(detail)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    tmp.replace(target)
    finalize_download_file(target)
    return str(target)


def finalize_download_file(path):
    target = Path(path)
    try:
        shutil.chown(target, user=APP_NAME, group="AppUsers")
    except Exception:
        pass
    try:
        target.chmod(0o640)
    except Exception:
        pass


def latest_map(latest_raw):
    result = {}
    for item in first_array(latest_raw):
        app_id = str(pick(item, ("appName", "name", "packageName", "id", "app_id")))
        if app_id:
            result[app_id] = item
    return result


def normalize_official_item(
    item,
    latest_by_app,
    tasks,
    override_version=None,
    override_source_id=None,
    settings=None,
):
    if settings is None:
        settings = read_settings()
    app_id = str(pick(item, ("appName", "name", "packageName", "id", "app_id")))
    latest = latest_by_app.get(app_id, {}) if app_id else {}
    version = override_version or str(
        pick(
            latest,
            ("version", "versionName", "releaseVersion"),
            pick(item, ("version", "versionName"), ""),
        )
    )
    key = task_key("official", app_id, version)
    task = tasks.get(key, {})
    status = task.get("status") or str(
        pick(item, ("downloadStatus", "status", "installStatus"), "")
    )
    target = download_path_for(app_id, version, settings)
    downloaded = target.exists()
    if downloaded:
        status = "downloaded"
    source_id = override_source_id or str(
        pick(
            latest,
            ("sourceID", "sourceId", "source_id"),
            pick(item, ("sourceID", "sourceId", "source_id"), ""),
        )
    )
    return {
        "id": app_id,
        "store": "official",
        "name": str(
            pick(
                item,
                ("displayName", "display_name", "title", "name", "appName"),
                app_id,
            )
        ),
        "version": version,
        "icon": apply_github_proxy(
            pick(item, ("icon", "iconUrl", "icon_url", "logo"), ""), settings
        ),
        "source": "官方商店",
        "sourceID": source_id,
        "packageSourceType": "cloud",
        "taskId": task.get("taskId", ""),
        "status": status,
        "downloaded": downloaded,
        "path": str(target) if downloaded else task.get("path", ""),
        "raw": item,
        "release": latest,
    }


def expand_upgrade_versions(item):
    upgrade_info = item.get("upgradeInfo")
    if not upgrade_info:
        return []
    if isinstance(upgrade_info, dict):
        upgrade_info = [upgrade_info]
    if not isinstance(upgrade_info, list):
        return []
    entries = []
    for entry in upgrade_info:
        if not isinstance(entry, dict):
            continue
        ver = str(
            entry.get("version")
            or entry.get("versionName")
            or entry.get("releaseVersion")
            or ""
        ).strip()
        if not ver:
            continue
        source_id = str(
            entry.get("sourceID")
            or entry.get("sourceId")
            or entry.get("source_id")
            or ""
        ).strip()
        entries.append({"version": ver, "sourceID": source_id})
    return entries


def official_apps(settings=None, token=None):
    if settings is None:
        settings = read_settings()
    tasks = read_tasks()["tasks"]
    app_raw_box: list[dict | None] = [None]
    latest_raw_box: list[dict | None] = [None]
    app_raw_error: list[Exception | None] = [None]
    latest_raw_error: list[Exception | None] = [None]

    def fetch_app_list():
        try:
            app_raw_box[0] = unix_http(
                "GET", "/app-center/v1/app/list?language=zh-CN", token_override=token
            )
        except Exception as exc:
            app_raw_error[0] = exc

    def fetch_latest():
        try:
            latest_raw_box[0] = unix_http(
                "GET",
                "/app-center/v1/app/latest-release?language=zh-CN",
                token_override=token,
            )
        except Exception as exc:
            latest_raw_error[0] = exc

    t1 = threading.Thread(target=fetch_app_list, daemon=True)
    t2 = threading.Thread(target=fetch_latest, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=20)
    t2.join(timeout=20)

    app_raw = app_raw_box[0] or {}
    latest_raw = latest_raw_box[0] or {}
    if app_raw_error[0] and not app_raw:
        raise app_raw_error[0]
    latest_by_app = latest_map(latest_raw)
    try:
        VAR_DIR.mkdir(parents=True, exist_ok=True)
        (VAR_DIR / "debug_app_list.json").write_text(
            json.dumps(app_raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    apps = []
    seen_keys = set()
    official_ids = set()
    for item in first_array(app_raw):
        main_app = normalize_official_item(
            item, latest_by_app, tasks, settings=settings
        )
        if main_app["id"]:
            official_ids.add(main_app["id"])
        main_key = task_key("official", main_app["id"], main_app["version"])
        if main_key not in seen_keys:
            seen_keys.add(main_key)
            apps.append(main_app)
        extra_entries = expand_upgrade_versions(item)
        if extra_entries:
            main_sid = main_app.get("sourceID", "")
            seen_keys.add(f"{main_app['id']}:{main_app['version']}:{main_sid}")
        for entry in extra_entries:
            ver = entry["version"]
            sid = entry.get("sourceID") or ""
            dedup_key = f"{main_app['id']}:{ver}:{sid}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            ver_key = task_key("official", main_app["id"], ver)
            if ver_key not in seen_keys:
                seen_keys.add(ver_key)
            override_sid = sid or None
            apps.append(
                normalize_official_item(
                    item,
                    latest_by_app,
                    tasks,
                    override_version=ver,
                    override_source_id=override_sid,
                    settings=settings,
                )
            )
    return {
        "apps": apps,
        "official_ids": official_ids,
        "raw": {"list": app_raw, "latestRelease": latest_raw},
    }


def load_source_json(url):
    url = apply_github_proxy(url)
    if url.startswith("file://"):
        return json.loads(
            Path(urllib.parse.urlparse(url).path).read_text(encoding="utf-8-sig")
        )
    if url.startswith("/") and Path(url).exists():
        return json.loads(Path(url).read_text(encoding="utf-8-sig"))
    separator = "&" if "?" in url else "?"
    cache_bust_url = f"{url}{separator}_={int(time.time())}"
    request = urllib.request.Request(
        cache_bust_url,
        headers={
            "User-Agent": f"{APP_NAME}/1.0",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8-sig"))


def _source_base_url(source_url):
    if not source_url:
        return ""
    base = source_url.rsplit("/", 1)[0] if "/" in source_url else ""
    return base


def normalize_third_party_item(app_id, item, source_name, source_url="", settings=None):
    if settings is None:
        settings = read_settings()
    version = str(pick(item, ("version", "versionName"), ""))
    download_path = download_path_for(app_id, version, settings)
    icon_value = pick(item, ("icon", "icon_url", "iconUrl"), "")
    download_url_value = pick(item, ("download_url", "downloadUrl", "url"), "")
    base = _source_base_url(source_url)
    if not icon_value and base and app_id:
        icon_value = f"{base}/{app_id}/ICON.PNG"
    if not download_url_value and base and app_id:
        download_url_value = f"{base}/{app_id}/{app_id}.fpk"
    icon_value = apply_github_proxy(icon_value, settings)
    return {
        "id": app_id,
        "store": "thirdparty",
        "name": str(
            pick(item, ("display_name", "displayName", "name", "title"), app_id)
        ),
        "version": version,
        "icon": icon_value,
        "source": source_name,
        "downloadUrl": download_url_value,
        "status": "downloaded" if download_path.exists() else "",
        "downloaded": download_path.exists(),
        "path": str(download_path) if download_path.exists() else "",
        "raw": item,
    }


def _parse_stem(stem, known_ids=None):
    if known_ids:
        sorted_ids = sorted(known_ids, key=len, reverse=True)
        for aid in sorted_ids:
            prefix = aid + "-"
            if stem.startswith(prefix):
                ver = stem[len(prefix) :]
                if ver:
                    return aid, ver
    last_dash = stem.rfind("-")
    if last_dash < 1:
        return None, None
    app_id = stem[:last_dash]
    version = stem[last_dash + 1 :]
    if not app_id or not version:
        return None, None
    return app_id, version


def orphaned_apps(known_keys, official_ids=None, all_known_ids=None, settings=None):
    if official_ids is None:
        official_ids = set()
    if settings is None:
        settings = read_settings()
    ddir = download_dir(settings)
    if not ddir.is_dir():
        return []
    apps = []
    for entry in sorted(ddir.iterdir()):
        if not entry.is_file() or entry.suffix != ".fpk":
            continue
        stem = entry.stem
        app_id, version = _parse_stem(stem, all_known_ids)
        if not app_id or not version:
            continue
        key = task_key("thirdparty", app_id, version)
        if key in known_keys:
            continue
        if app_id in official_ids:
            continue
        apps.append(
            {
                "id": app_id,
                "store": "thirdparty",
                "name": app_id,
                "version": version,
                "icon": "",
                "source": "",
                "downloadUrl": "",
                "status": "downloaded",
                "downloaded": True,
                "orphaned": True,
                "path": str(entry),
            }
        )
    return apps


def third_party_apps(official_ids=None, settings=None, token=None):
    if settings is None:
        settings = read_settings()
    apps = []
    errors = []
    known_keys = set()
    for source in settings.get("thirdPartySources", []):
        if not source.get("enabled", True):
            continue
        url = str(source.get("url", "")).strip()
        if not url:
            continue
        name = str(source.get("name") or url)
        try:
            data = load_source_json(url)
            if isinstance(data, dict):
                entries = data.items()
            else:
                entries = [(str(index), item) for index, item in enumerate(data or [])]
            for app_id, item in entries:
                if isinstance(item, dict):
                    apps.append(
                        normalize_third_party_item(
                            str(app_id), item, name, source_url=url, settings=settings
                        )
                    )
                    version = str(pick(item, ("version", "versionName"), ""))
                    known_keys.add(task_key("thirdparty", str(app_id), version))
        except Exception as exc:
            errors.append({"source": name, "url": url, "message": str(exc)})
    if official_ids is None:
        official_ids = set()
        try:
            official_raw = unix_http(
                "GET", "/app-center/v1/app/list?language=zh-CN", token_override=token
            )
            for item in first_array(official_raw):
                app_id = str(
                    pick(item, ("appName", "name", "packageName", "id", "app_id"))
                )
                if app_id:
                    official_ids.add(app_id)
        except Exception:
            pass
    appcenter_dir = Path("/vol1/@appcenter")
    if appcenter_dir.is_dir():
        for entry in appcenter_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                official_ids.add(entry.name)
    appmeta_dir = Path("/vol1/@appmeta")
    if appmeta_dir.is_dir():
        for entry in appmeta_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                official_ids.add(entry.name)
    all_known_ids = set()
    for a in apps:
        if a.get("id"):
            all_known_ids.add(a["id"])
    all_known_ids.update(official_ids)
    apps.extend(
        orphaned_apps(known_keys, official_ids, all_known_ids, settings=settings)
    )
    return {"apps": apps, "errors": errors}


def save_settings(payload):
    sources = payload.get("thirdPartySources", [])
    download_dir_value = str(payload.get("downloadDir") or DEFAULT_DOWNLOAD_DIR).strip()
    if not download_dir_value.startswith("/"):
        raise RuntimeError("download path must be an absolute path")
    clean_sources = []
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url", "")).strip()
            if not url:
                continue
            clean_sources.append(
                {
                    "name": str(source.get("name") or url).strip(),
                    "url": url,
                    "enabled": bool(source.get("enabled", True)),
                }
            )
    data = {
        "downloadDir": download_dir_value,
        "thirdPartySources": clean_sources,
        "githubProxyEnabled": bool(payload.get("githubProxyEnabled", True)),
        "githubProxyUrl": str(
            payload.get("githubProxyUrl")
            or DEFAULT_SETTINGS.get("githubProxyUrl", "https://gh-proxy.com/")
        ).strip(),
    }
    write_json_file(SETTINGS_FILE, data)
    download_dir(data).mkdir(parents=True, exist_ok=True)
    return data


def start_third_party_download(app):
    app_id = str(app.get("id", ""))
    version = str(app.get("version", ""))
    url = str(app.get("downloadUrl", ""))
    if not app_id or not version or not url:
        raise RuntimeError("missing third-party download fields")
    target = download_path_for(app_id, version)
    key = task_key("thirdparty", app_id, version)
    tasks = read_tasks()
    tasks["tasks"][key] = {
        "store": "thirdparty",
        "appId": app_id,
        "version": version,
        "status": "downloading",
        "url": url,
        "path": str(target),
        "fileExists": False,
        "updatedAt": int(time.time()),
    }
    save_tasks(tasks)
    worker = threading.Thread(
        target=download_worker, args=(key, url, str(target)), daemon=True
    )
    worker.start()
    return tasks["tasks"][key]


def update_task(key, **updates):
    tasks = read_tasks()
    current = tasks["tasks"].get(key, {})
    current.update(updates)
    current["updatedAt"] = int(time.time())
    tasks["tasks"][key] = current
    save_tasks(tasks)


def delete_download(app):
    app_id = str(app.get("id", ""))
    version = str(app.get("version", ""))
    store = str(app.get("store", ""))
    if not app_id or not version or not store:
        raise RuntimeError("missing app fields")
    key = task_key(store, app_id, version)
    target = download_path_for(app_id, version)
    if target.exists():
        target.unlink()
    tmp = target.with_suffix(target.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    tasks = read_tasks()
    tasks["tasks"][key] = {
        "store": store,
        "appId": app_id,
        "version": version,
        "status": "deleted",
        "deleted": True,
        "path": "",
        "fileExists": False,
        "updatedAt": int(time.time()),
    }
    save_tasks(tasks)
    return {"key": key, "path": str(target)}


def download_worker(key, url, target):
    ensure_dirs()
    url = apply_github_proxy(url)
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{target}.part"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response, open(
            tmp, "wb"
        ) as output:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                output.write(chunk)
        os.replace(tmp, target)
        update_task(key, status="downloaded", path=target, fileExists=True, error="")
        finalize_download_file(target)
    except Exception as exc:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        finally:
            update_task(key, status="failed", error=str(exc))


def official_download(app):
    app_id = str(app.get("id", ""))
    version = str(app.get("version", ""))
    source_id = str(app.get("sourceID", ""))
    if not app_id or not version or not source_id:
        raise RuntimeError("missing official download fields")
    payload = {
        "packageSourceType": app.get("packageSourceType") or "cloud",
        "appName": app_id,
        "sourceID": source_id,
        "version": version,
        "volumeID": int(app.get("volumeID") or 1),
    }
    result = unix_http("POST", "/app-center/v1/download/task", payload)
    task_id = str(
        pick(
            result,
            ("downloadTaskId", "taskId", "id"),
            pick(
                result.get("data", {}) if isinstance(result, dict) else {},
                ("downloadTaskId", "taskId", "id"),
                "",
            ),
        )
    )
    key = task_key("official", app_id, version)
    tasks = read_tasks()
    tasks["tasks"][key] = {
        "store": "official",
        "appId": app_id,
        "version": version,
        "sourceID": source_id,
        "taskId": task_id,
        "status": "downloading",
        "path": str(download_path_for(app_id, version)),
        "fileExists": False,
        "updatedAt": int(time.time()),
        "raw": result,
    }
    save_tasks(tasks)
    return tasks["tasks"][key]


def refresh_official_status(task_id):
    result = unix_http(
        "GET",
        f"/app-center/v1/download/status?downloadTaskId={urllib.parse.quote(task_id)}&language=zh-CN",
    )
    return result


def status_payload(apps=None, skip_remote=False):
    tasks = read_tasks()
    changed = False
    for key, task in list(tasks["tasks"].items()):
        exists = task_file_exists(task)
        if task.get("fileExists") != exists:
            task["fileExists"] = exists
            changed = True
        if is_done_status(task.get("status")) and not exists:
            age = int(time.time()) - int(task.get("updatedAt") or 0)
            if age > 10:
                task["status"] = "deleted"
                task["deleted"] = True
                task["path"] = ""
                task["fileExists"] = False
                task["updatedAt"] = int(time.time())
                changed = True
                continue
        if task.get("deleted"):
            continue
        if task.get("store") != "official" or not task.get("taskId"):
            continue
        if skip_remote:
            continue
        try:
            raw = refresh_official_status(str(task["taskId"]))
            status = str(
                pick(
                    raw,
                    ("status", "state", "downloadStatus"),
                    pick(
                        raw.get("data", {}) if isinstance(raw, dict) else {},
                        ("status", "state", "downloadStatus"),
                        "",
                    ),
                )
            )
            target = download_path_for(task.get("appId", ""), task.get("version", ""))
            if target.exists():
                finalize_download_file(target)
                status = "downloaded"
                task["fileExists"] = True
            else:
                source_path = source_path_for_official(task, raw)
                if source_path:
                    try:
                        packaged_path = package_official_download(
                            task.get("appId", ""), task.get("version", ""), source_path
                        )
                        if packaged_path:
                            task["path"] = packaged_path
                            task["status"] = "downloaded"
                            task["error"] = ""
                            task["fileExists"] = True
                            task["rawStatus"] = raw
                            task["updatedAt"] = int(time.time())
                            changed = True
                            continue
                    except Exception as exc:
                        task["status"] = "failed"
                        task["error"] = str(exc)
                        task["rawStatus"] = raw
                        task["updatedAt"] = int(time.time())
                        changed = True
                        continue
            if status:
                task["status"] = status
                task["rawStatus"] = raw
                if target.exists():
                    task["path"] = str(target)
                    task["error"] = ""
                    task["fileExists"] = True
                elif is_done_status(status):
                    source_path = source_path_for_official(task, raw)
                    if source_path:
                        try:
                            packaged_path = package_official_download(
                                task.get("appId", ""),
                                task.get("version", ""),
                                source_path,
                            )
                            if packaged_path:
                                task["path"] = packaged_path
                                task["status"] = "downloaded"
                                task["error"] = ""
                                task["fileExists"] = True
                        except Exception as exc:
                            task["status"] = "failed"
                            task["error"] = str(exc)
                task["updatedAt"] = int(time.time())
                changed = True
        except Exception:
            pass
    if changed:
        save_tasks(tasks)
    return {"tasks": tasks.get("tasks", {}), "files": file_status_for_apps(apps)}


def dispatch():
    ensure_dirs()
    payload = request_body()
    action = payload.get("action", "list")
    if action == "settings":
        json_response({"ok": True, "settings": read_settings()})
    elif action == "save-settings":
        json_response({"ok": True, "settings": save_settings(payload)})
    elif action == "app-list":
        settings = read_settings()
        token = incoming_token()
        official_result_box: list[dict | None] = [None]
        official_error_box: list[Exception | None] = [None]
        thirdparty_result_box: list[dict | None] = [None]
        thirdparty_error_box: list[Exception | None] = [None]

        def fetch_official():
            try:
                official_result_box[0] = official_apps(settings=settings, token=token)
            except Exception as exc:
                official_error_box[0] = exc

        def fetch_thirdparty():
            try:
                thirdparty_result_box[0] = third_party_apps(
                    settings=settings, token=token
                )
            except Exception as exc:
                thirdparty_error_box[0] = exc

        t_official = threading.Thread(target=fetch_official, daemon=True)
        t_thirdparty = threading.Thread(target=fetch_thirdparty, daemon=True)
        t_official.start()
        t_thirdparty.start()
        t_official.join(timeout=30)
        t_thirdparty.join(timeout=30)

        if official_error_box[0] and not official_result_box[0]:
            raise official_error_box[0]

        official_result = official_result_box[0] or {}
        official_ids = official_result.get("official_ids", set())
        thirdparty_result = thirdparty_result_box[0] or {}
        thirdparty_errors = thirdparty_result.get("errors", [])
        if thirdparty_error_box[0]:
            thirdparty_errors.append(
                {"source": "thirdparty", "message": str(thirdparty_error_box[0])}
            )

        all_apps = official_result.get("apps", []) + thirdparty_result.get("apps", [])
        tasks_data = status_payload(skip_remote=True)
        json_response(
            {
                "ok": True,
                "apps": all_apps,
                "errors": thirdparty_errors,
                "tasks": tasks_data.get("tasks", {}),
                "files": tasks_data.get("files", {}),
            }
        )
    elif action == "official-list":
        settings = read_settings()
        token = incoming_token()
        result = official_apps(settings=settings, token=token)
        tasks_data = status_payload()
        json_response(
            {
                "ok": True,
                "apps": result.get("apps", []),
                "tasks": tasks_data.get("tasks", {}),
                "raw": result.get("raw"),
            }
        )
    elif action == "thirdparty-list":
        settings = read_settings()
        token = incoming_token()
        result = third_party_apps(settings=settings, token=token)
        tasks_data = status_payload()
        json_response(
            {
                "ok": True,
                **result,
                "tasks": tasks_data.get("tasks", {}),
            }
        )
    elif action == "download":
        app = payload.get("app")
        if isinstance(app, str):
            app = json.loads(app)
        if not isinstance(app, dict):
            raise RuntimeError("missing app")
        task = (
            official_download(app)
            if app.get("store") == "official"
            else start_third_party_download(app)
        )
        json_response({"ok": True, "task": task})
    elif action == "delete":
        app = payload.get("app")
        if isinstance(app, str):
            app = json.loads(app)
        if not isinstance(app, dict):
            raise RuntimeError("missing app")
        json_response({"ok": True, "deleted": delete_download(app), **status_payload()})
    elif action == "status":
        json_response({"ok": True, **status_payload(payload.get("apps"))})
    else:
        json_response({"ok": False, "message": "unsupported action"}, "400 Bad Request")


def main():
    parser = argparse.ArgumentParser(description="fn-appdownload Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-appdownload")
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
