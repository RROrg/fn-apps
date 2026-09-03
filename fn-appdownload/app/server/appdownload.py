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
import shutil
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


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


def _share_dir():
    # 共享数据目录：优先按 TRIM_APPDEST_VOL 推导（/vol1/@appshare/<app>），否则回退到软链路径
    vol = _env("TRIM_APPDEST_VOL")
    if vol:
        return Path(vol) / "@appshare" / APP_NAME
    return Path(f"/var/apps/{APP_NAME}/shares/{APP_NAME}")


APP_NAME = _env("TRIM_APPNAME", "fn-appdownload")
DB_NAME = "appcenter"
DB_USER = "postgres"
# 运行时数据目录：优先用 TRIM_PKGVAR，回退到 /var/apps/<app>/var
_pkgvar = _env("TRIM_PKGVAR")
VAR_DIR = Path(_pkgvar) if _pkgvar else Path(f"/var/apps/{APP_NAME}/var")
SHARE_DIR = _share_dir()
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

# V2 规范相关常量
V2_SCHEMA_VERSION = "2"
V2_ALLOWED_PLATFORMS = ("all", "x86", "arm")
V2_ALLOWED_ARCH_KEYS = ("all", "x86", "arm")
V2_FIXED_CATEGORIES = (
    "影音娱乐",
    "系统工具",
    "编程开发",
    "AI赋能",
    "生活服务",
    "智能智控",
    "教育学习",
    "游戏地带",
    "硬件驱动",
)


def _detect_arch():
    """检测当前设备架构，返回 'x86' 或 'arm'。"""
    machine = (os.uname().machine if hasattr(os, "uname") else "").lower()
    if machine.startswith(("arm", "aarch")):
        return "arm"
    return "x86"


def _resolve_relative_url(url, base_url):
    """将相对 URL 相对于 base_url 解析为绝对 URL。"""
    if not url:
        return ""
    if not isinstance(url, str):
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if not base_url:
        return url
    return urllib.parse.urljoin(base_url, url)


def _i18n_pick(obj, field_names, locale, base_obj=None):
    """按 V2 i18n 回退顺序取值。

    回退顺序：精确 locale -> 同语系 -> en-US -> zh-CN -> 基础字段
    """
    if not isinstance(obj, dict):
        return ""

    def locale_fallbacks(loc):
        loc = (loc or "").strip()
        if not loc:
            return ["en-US", "zh-CN"]
        candidates = [loc]
        # 同语系回退
        if loc.startswith("zh-"):
            candidates.append("zh-CN")
        elif loc.startswith("en-"):
            candidates.append("en-US")
        # 通用回退
        for fallback in ("en-US", "zh-CN"):
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    i18n = obj.get("i18n")
    if isinstance(i18n, dict):
        for candidate in locale_fallbacks(locale):
            entry = i18n.get(candidate)
            if isinstance(entry, dict):
                for name in field_names:
                    value = entry.get(name)
                    if value not in (None, ""):
                        return value
    # 基础字段回退
    if isinstance(base_obj, dict):
        for name in field_names:
            value = base_obj.get(name)
            if value not in (None, ""):
                return value
    else:
        for name in field_names:
            value = obj.get(name)
            if value not in (None, ""):
                return value
    return ""


def _normalize_platform(platform):
    """规范化 platform 字段为列表。"""
    if isinstance(platform, str):
        return [platform] if platform else []
    if isinstance(platform, list):
        return [str(p) for p in platform if isinstance(p, str)]
    return []


def _is_valid_sha256(value):
    """检查 sha256 格式是否合法。"""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def _select_package(packages, arch):
    """按 V2 规范选择安装包：优先当前架构，回退到 all。

    返回 (arch_key, package_dict) 或 (None, None)。
    """
    if not isinstance(packages, dict):
        return None, None
    # 优先当前架构
    pkg = packages.get(arch)
    if isinstance(pkg, dict) and pkg.get("download_url"):
        return arch, pkg
    # 回退到 all
    pkg = packages.get("all")
    if isinstance(pkg, dict) and pkg.get("download_url"):
        return "all", pkg
    return None, None


def _merge_package_fields(app_node, release_node, package_all, package_arch):
    """按 V2 规范合并字段：应用级 -> 版本级 -> packages.all -> packages.[arch]。"""
    merged = {}
    # 应用级
    if isinstance(app_node, dict):
        for key in (
            "run_as",
            "install_type",
            "is_docker",
            "service_port",
            "os_min_version",
            "os_max_version",
        ):
            if app_node.get(key) is not None:
                merged[key] = app_node.get(key)
    # 版本级
    if isinstance(release_node, dict):
        for key in (
            "run_as",
            "install_type",
            "is_docker",
            "service_port",
            "os_min_version",
            "os_max_version",
            "changelog",
            "updated_at",
        ):
            if release_node.get(key) is not None:
                merged[key] = release_node.get(key)
    # packages.all
    if isinstance(package_all, dict):
        for key in (
            "run_as",
            "install_type",
            "is_docker",
            "service_port",
            "os_min_version",
            "os_max_version",
            "changelog",
            "updated_at",
            "sha256",
            "size",
        ):
            if package_all.get(key) is not None:
                merged[key] = package_all.get(key)
    # packages.[arch]（最后覆盖）
    if isinstance(package_arch, dict):
        for key in (
            "run_as",
            "install_type",
            "is_docker",
            "service_port",
            "os_min_version",
            "os_max_version",
            "changelog",
            "updated_at",
            "sha256",
            "size",
            "download_url",
        ):
            if package_arch.get(key) is not None:
                merged[key] = package_arch.get(key)
    return merged


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


def run_sql(sql):
    proc = subprocess.run(
        [
            "psql",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-q",
            "-t",
            "-A",
            "-c",
            sql,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "psql failed").strip()
        raise RuntimeError(detail)
    return proc.stdout.strip()


def installed_apps_map():
    sql = (
        "SELECT COALESCE(json_object_agg(app_name, version), '{}'::json) "
        "FROM (SELECT app_name, version FROM app) t"
    )
    try:
        text = run_sql(sql)
        data = json.loads(text) if text else {}
        if not isinstance(data, dict):
            return {}
        result = {}
        for key, value in data.items():
            app_key = str(key or "").strip()
            if not app_key:
                continue
            result[app_key] = str(value or "")
            result[app_key.lower()] = str(value or "")
        return result
    except Exception:
        return {}


def version_sort_key(version):
    parts = re.split(r"[.\-_+]", str(version or ""))
    key = []
    for part in parts:
        key.append((1, int(part)) if part.isdigit() else (0, part))
    return key


def compare_versions(a, b):
    key_a, key_b = version_sort_key(a), version_sort_key(b)
    if key_a == key_b:
        return 0
    return 1 if key_a > key_b else -1


def install_status_for(app_id, version, installed):
    app_key = str(app_id or "").strip()
    installed_version = None
    if app_key:
        installed_version = installed.get(app_key)
        if installed_version is None:
            installed_version = installed.get(app_key.lower())
    if installed_version is None:
        return "not_installed"
    if not version:
        return "installed"
    cmp = compare_versions(version, installed_version)
    if cmp > 0:
        return "upgradable"
    if cmp < 0:
        return "downgradable"
    return "installed"


def annotate_install_status(apps):
    installed = installed_apps_map()
    for app in apps:
        if isinstance(app, dict):
            app["installStatus"] = install_status_for(
                app.get("id", ""), app.get("version", ""), installed
            )
    return apps


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


def appcenter_download_dir(app_id, version, volume_id=None):
    # vol 由前端确定（参照 loadVolumes 从 app-center 查默认下载卷）并传入，
    # 后端不再自行硬编码 /vol1
    name = "".join(
        ch if ch.isalnum() or ch in "._-" else "_" for ch in f"{app_id}-{version}"
    )
    vol = f"/vol{int(volume_id)}" if volume_id else _env("TRIM_APPDEST_VOL")
    base = (
        Path(vol) / "appcenter-downloads" if vol else Path("/vol1/appcenter-downloads")
    )
    return base / f"{name}-tpk"


def source_path_for_official(task, raw):
    source_path = first_path_value(raw)
    if source_path:
        return source_path
    inferred = appcenter_download_dir(
        task.get("appId", ""),
        task.get("version", ""),
        task.get("volumeID"),
    )
    return str(inferred) if inferred.is_dir() else ""


def package_official_download(app_id, version, source_path):
    """/volN/appcenter-downloads/ 下载目录 需要 root 权限"""
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
        shutil.chown(
            target,
            user=_env("TRIM_USERNAME", APP_NAME),
            group=_env("TRIM_GROUPNAME", "AppUsers"),
        )
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
        "volumeID": int(
            pick(
                item,
                ("volumeID", "volumeId", "volume_id", "installVolumeID"),
                "1",
            )
            or 1
        ),
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


def official_apps_from_raw(app_raw, latest_raw, settings=None):
    # app-center 原始数据由前端直接获取，后端仅做处理
    if settings is None:
        settings = read_settings()
    tasks = read_tasks()["tasks"]
    app_raw = app_raw or {}
    latest_raw = latest_raw or {}
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


def _runtime_locale():
    """获取运行时语言，优先 TRIM_SYS_LANGUAGE 环境变量。"""
    return _env("TRIM_SYS_LANGUAGE", "zh-CN")


def _is_v2_source(data):
    """检测数据是否为 V2 格式。"""
    return (
        isinstance(data, dict)
        and str(data.get("schema_version", "")).strip() == V2_SCHEMA_VERSION
    )


def _load_details_json(details_url, source_url):
    """加载 details_url 拆分模式的详情 JSON。"""
    absolute_url = _resolve_relative_url(details_url, source_url)
    return load_source_json(absolute_url), absolute_url


def _select_highest_version(releases, arch, os_version=""):
    """从 releases 中选择当前架构可用的最高版本。

    返回 (version_str, release_node) 或 (None, None)。
    """
    if not isinstance(releases, dict) or not releases:
        return None, None
    candidates = []
    for version, release_node in releases.items():
        if not isinstance(release_node, dict):
            continue
        packages = release_node.get("packages")
        if not isinstance(packages, dict):
            continue
        # 检查架构可用性
        arch_key, _ = _select_package(packages, arch)
        if arch_key is None:
            continue
        # 检查系统版本范围（os_min_version / os_max_version）
        if os_version:
            os_min = str(release_node.get("os_min_version") or "").strip()
            os_max = str(release_node.get("os_max_version") or "").strip()
            if os_min and compare_versions(os_version, os_min) < 0:
                continue
            if os_max and compare_versions(os_version, os_max) > 0:
                continue
        candidates.append((version, release_node))
    if not candidates:
        return None, None
    # 按版本号排序，选择最高版本
    candidates.sort(key=lambda item: version_sort_key(item[0]))
    return candidates[-1]


def normalize_v2_app_item(
    app_id,
    app_node,
    source_name,
    source_url="",
    settings=None,
    locale="",
    arch=None,
):
    """将 V2 应用节点规范化为内部应用对象。

    支持单文件模式和 details_url 拆分模式。
    返回 (app_dict, error_message)。成功时 error_message 为 None。
    """
    if settings is None:
        settings = read_settings()
    if not isinstance(app_node, dict):
        return None, "app node is not a dict"
    if arch is None:
        arch = _detect_arch()
    if not locale:
        locale = _runtime_locale()

    # 处理 details_url 拆分模式
    details_url = str(app_node.get("details_url") or "").strip()
    if details_url:
        try:
            details_data, details_base_url = _load_details_json(
                details_url, source_url
            )
        except Exception as exc:
            return None, f"details fetch failed: {exc}"
        if not isinstance(details_data, dict):
            return None, "details json is not a dict"
        # 校验 app_name 一致性
        details_app_name = str(details_data.get("app_name") or "").strip()
        if details_app_name and details_app_name != app_id:
            return None, f"app_name mismatch: {details_app_name} != {app_id}"
        # 合并：详情字段覆盖主索引同名字段
        merged_node = {}
        merged_node.update(app_node)
        merged_node.update(details_data)
        app_node = merged_node
        # 详情文件中的相对 URL 相对于详情 JSON 所在地址解析
        base_url_for_resources = details_base_url
    else:
        base_url_for_resources = source_url

    # 提取必填字段（合并后）
    display_name = _i18n_pick(
        app_node, ("display_name", "displayName"), locale, base_obj=app_node
    )
    if not display_name:
        display_name = str(
            pick(app_node, ("display_name", "displayName", "name", "title"), app_id)
        )
    desc = _i18n_pick(app_node, ("desc", "description"), locale, base_obj=app_node)
    if not desc:
        desc = str(pick(app_node, ("desc", "description"), ""))
    platform = _normalize_platform(app_node.get("platform"))
    if not platform:
        # V1 兼容：没有 platform 时默认 x86
        platform = ["x86"]
    # 校验 platform 值
    invalid_platforms = [p for p in platform if p not in V2_ALLOWED_PLATFORMS]
    if invalid_platforms:
        return None, f"invalid platform: {invalid_platforms}"
    # 检查当前架构是否适用
    if "all" not in platform and arch not in platform:
        return None, f"platform {platform} not supported on {arch}"

    categories = app_node.get("categories")
    if not isinstance(categories, list) or not categories:
        return None, "categories missing or not a list"
    # 校验分类
    invalid_categories = [c for c in categories if c not in V2_FIXED_CATEGORIES]
    if invalid_categories:
        return None, f"invalid categories: {invalid_categories}"

    icon_url = str(app_node.get("icon_url") or app_node.get("icon") or "").strip()
    icon_url = _resolve_relative_url(icon_url, base_url_for_resources)
    icon_url = apply_github_proxy(icon_url, settings)

    # 选择最高可用版本
    releases = app_node.get("releases")
    if not isinstance(releases, dict) or not releases:
        return None, "releases missing or not a dict"

    version, release_node = _select_highest_version(releases, arch)
    if version is None:
        return None, "no installable version for current arch"
    packages = release_node.get("packages", {})
    arch_key, package_node = _select_package(packages, arch)
    if arch_key is None:
        return None, "no valid package for current arch"
    package_all = packages.get("all", {}) if isinstance(packages, dict) else {}

    # 合并字段
    merged = _merge_package_fields(
        app_node, release_node, package_all, package_node
    )

    # 解析 download_url（必须存在于最终选中的分支中）
    download_url = str(package_node.get("download_url") or "").strip()
    if not download_url:
        return None, "download_url missing in selected package"
    download_url = _resolve_relative_url(download_url, base_url_for_resources)
    download_url = apply_github_proxy(download_url, settings)

    # sha256 校验
    sha256 = str(merged.get("sha256") or "").strip()
    if sha256 and not _is_valid_sha256(sha256):
        # 哈希格式错误，跳过该版本
        return None, f"invalid sha256 format: {sha256}"

    # size 校验
    size = merged.get("size")
    if size is not None and (not isinstance(size, int) or size < 0):
        return None, f"invalid size: {size}"

    # 预览图
    preview_urls = app_node.get("preview_urls") or []
    if isinstance(preview_urls, list):
        preview_urls = [
            apply_github_proxy(
                _resolve_relative_url(str(u), base_url_for_resources), settings
            )
            for u in preview_urls
            if isinstance(u, str) and u
        ][:8]
    else:
        preview_urls = []

    # 其他可选字段
    readme_url = str(app_node.get("readme_url") or "").strip()
    if readme_url:
        readme_url = _resolve_relative_url(readme_url, base_url_for_resources)
        readme_url = apply_github_proxy(readme_url, settings)
    bug_report_url = str(app_node.get("bug_report_url") or "").strip()
    if bug_report_url:
        bug_report_url = _resolve_relative_url(bug_report_url, base_url_for_resources)
        bug_report_url = apply_github_proxy(bug_report_url, settings)

    download_path = download_path_for(app_id, version, settings)
    downloaded = download_path.exists()

    # changelog i18n
    changelog = _i18n_pick(
        release_node, ("changelog",), locale, base_obj=release_node
    )
    if not changelog:
        changelog = str(release_node.get("changelog") or "")

    return {
        "id": app_id,
        "store": "thirdparty",
        "name": str(display_name),
        "version": version,
        "icon": icon_url,
        "source": source_name,
        "downloadUrl": download_url,
        "sha256": sha256,
        "size": size if isinstance(size, int) else None,
        "desc": desc,
        "categories": categories,
        "platform": platform,
        "previewUrls": preview_urls,
        "readmeUrl": readme_url,
        "bugReportUrl": bug_report_url,
        "maintainer": str(app_node.get("maintainer") or ""),
        "maintainerUrl": str(app_node.get("maintainer_url") or ""),
        "distributor": str(app_node.get("distributor") or ""),
        "distributorUrl": str(app_node.get("distributor_url") or ""),
        "runAs": str(merged.get("run_as") or ""),
        "installType": str(merged.get("install_type") or ""),
        "isDocker": bool(merged.get("is_docker")) if merged.get("is_docker") is not None else None,
        "servicePort": str(merged.get("service_port") or ""),
        "changelog": changelog,
        "updatedAt": str(release_node.get("updated_at") or merged.get("updated_at") or ""),
        "status": "downloaded" if downloaded else "",
        "downloaded": downloaded,
        "path": str(download_path) if downloaded else "",
        "raw": app_node,
    }, None


def _normalize_platform_value(value):
    """规范化 platform 字段为列表（V1 1.1.1 规范）。

    - String: "all" 或 "x86" 等单值
    - Array: ["all", "x86", "arm"]
    - 缺失/空: 返回空列表，由调用方按旧版规则默认 x86
    """
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return [str(p) for p in value if isinstance(p, str) and p]
    return []


def _resolve_v1_download_url(app_id, item, arch, base_url):
    """按 V1 1.1.1 规范解析 download_url，支持三级回退。

    优先级：
    1. 显式 download_url（arch_diff 覆盖后）
    2. /{app_name}/{app_name}_{arch}.fpk
    3. /{app_name}/{app_name}_all.fpk
    4. /{app_name}/{app_name}.fpk（仅 platform 缺失时，旧版兼容）
    """
    download_url = str(
        pick(item, ("download_url", "downloadUrl", "url"), "")
    ).strip()
    if download_url:
        return download_url
    if not base_url or not app_id:
        return ""
    # 架构专用包
    arch_url = f"{base_url}/{app_id}/{app_id}_{arch}.fpk"
    # 通用包 _all
    all_url = f"{base_url}/{app_id}/{app_id}_all.fpk"
    # 旧版兼容包（无 platform 时）
    legacy_url = f"{base_url}/{app_id}/{app_id}.fpk"
    # 返回所有候选，由调用方决定是否使用（此处返回首选 arch_url）
    # 实际使用时客户端无法预判 URL 是否可访问，按规范优先级返回第一个非空
    return arch_url


def _v1_download_url_candidates(app_id, item, arch, base_url, has_platform):
    """返回 download_url 候选列表，按优先级排序。"""
    download_url = str(
        pick(item, ("download_url", "downloadUrl", "url"), "")
    ).strip()
    candidates = []
    if download_url:
        candidates.append(download_url)
    if base_url and app_id:
        candidates.append(f"{base_url}/{app_id}/{app_id}_{arch}.fpk")
        candidates.append(f"{base_url}/{app_id}/{app_id}_all.fpk")
        # 仅 platform 缺失时回退到旧版命名
        if not has_platform:
            candidates.append(f"{base_url}/{app_id}/{app_id}.fpk")
    return candidates


def normalize_third_party_item(
    app_id, item, source_name, source_url="", settings=None, arch=None
):
    """V1 1.1.1 规范：将扁平格式的第三方应用项规范化为内部应用对象。

    实现完整规范：
    - platform 字段检测和架构过滤（缺失默认 x86）
    - arch_diff 架构差异覆盖（version/desc/size/download_url/changelog）
    - download_url 三级回退（_{arch}.fpk → _all.fpk → .fpk）
    - distributor/distributor_url 优先，author/author_url 兼容
    - labels、install_type、isdocker、size、changelog、bug_report_url 等字段

    返回 app_dict 或 None（架构不匹配或信息不全时）。
    """
    if settings is None:
        settings = read_settings()
    if not isinstance(item, dict):
        return None
    if arch is None:
        arch = _detect_arch()

    base = _source_base_url(source_url)

    # 1. platform 字段检测
    raw_platform = item.get("platform")
    has_platform = raw_platform is not None and (
        (isinstance(raw_platform, str) and raw_platform)
        or (isinstance(raw_platform, list) and raw_platform)
    )
    platform = _normalize_platform_value(raw_platform)
    if not platform:
        # V1 兼容：没有 platform 时默认 x86
        platform = ["x86"]

    # 2. 架构过滤：检测当前架构是否适用
    if "all" not in platform and arch not in platform:
        return None

    # 3. arch_diff 架构差异覆盖
    arch_diff = item.get("arch_diff")
    arch_overrides = {}
    if isinstance(arch_diff, dict):
        arch_overrides = arch_diff.get(arch, {}) or {}
        if not isinstance(arch_overrides, dict):
            arch_overrides = {}

    # 合并字段：arch_diff[arch] 覆盖通用字段
    # 支持覆盖的字段: version, desc, size, download_url, changelog
    def merged_field(name, fallback_names=()):
        """先查 arch_diff 覆盖，再查通用字段。"""
        value = arch_overrides.get(name)
        if value not in (None, ""):
            return value
        value = item.get(name)
        if value not in (None, ""):
            return value
        for alt in fallback_names:
            value = item.get(alt)
            if value not in (None, ""):
                return value
        return ""

    # 4. 提取字段
    version = str(merged_field("version", ("versionName", "")))
    if not version:
        return None

    display_name = str(
        pick(item, ("display_name", "displayName", "name", "title"), app_id)
    )
    desc = str(merged_field("desc", ("description", "")))
    labels = str(item.get("labels") or "")
    changelog = str(merged_field("changelog", ("",)))

    # distributor 优先，author 兼容
    distributor = str(
        pick(item, ("distributor", "author", "maintainer"), "")
    )
    distributor_url = str(
        pick(item, ("distributor_url", "author_url", "maintainer_url"), "")
    )
    bug_report_url = str(item.get("bug_report_url") or "")
    install_type = str(item.get("install_type") or "")
    isdocker_raw = item.get("isdocker")
    if isinstance(isdocker_raw, bool):
        is_docker = isdocker_raw
    else:
        is_docker = str(isdocker_raw or "").strip().lower() == "true"
    size_value = str(merged_field("size", ("",)))

    # 5. 图标 URL
    icon_value = str(pick(item, ("icon", "icon_url", "iconUrl"), ""))
    if not icon_value and base and app_id:
        icon_value = f"{base}/{app_id}/ICON.PNG"
    icon_value = apply_github_proxy(icon_value, settings)

    # 6. download_url 解析（含 arch_diff 覆盖和三级回退）
    download_url_value = str(merged_field("download_url", ("downloadUrl", "url")))
    if not download_url_value:
        # 回退到目录拼接
        candidates = _v1_download_url_candidates(
            app_id, item, arch, base, has_platform
        )
        # 过滤掉已尝试的显式 URL，取回退候选
        download_url_value = candidates[0] if candidates else ""
    download_url_value = apply_github_proxy(download_url_value, settings)

    if not download_url_value:
        # 信息不全，不录入
        return None

    # 7. 预览图目录
    preview_urls = []
    if base and app_id:
        # 预览图路径由前端按目录枚举，此处仅提供基础目录
        pass

    download_path = download_path_for(app_id, version, settings)
    downloaded = download_path.exists()

    return {
        "id": app_id,
        "store": "thirdparty",
        "name": display_name,
        "version": version,
        "icon": icon_value,
        "source": source_name,
        "downloadUrl": download_url_value,
        "desc": desc,
        "labels": labels,
        "categories": [c.strip() for c in labels.split(",") if c.strip()] if labels else [],
        "platform": platform,
        "distributor": distributor,
        "distributorUrl": distributor_url,
        "bugReportUrl": bug_report_url,
        "installType": install_type,
        "isDocker": is_docker,
        "size": size_value,
        "changelog": changelog,
        "status": "downloaded" if downloaded else "",
        "downloaded": downloaded,
        "path": str(download_path) if downloaded else "",
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


def third_party_apps(official_ids, settings=None):
    # official_ids 由前端处理官方应用后得到
    if settings is None:
        settings = read_settings()
    apps = []
    errors = []
    known_keys = set()
    arch = _detect_arch()
    locale = _runtime_locale()
    for source in settings.get("thirdPartySources", []):
        if not source.get("enabled", True):
            continue
        url = str(source.get("url", "")).strip()
        if not url:
            continue
        name = str(source.get("name") or url)
        try:
            data = load_source_json(url)
            if _is_v2_source(data):
                # V2 格式解析
                source_info = data.get("source_info") or {}
                # 源级 i18n 名称回退
                source_display_name = _i18n_pick(
                    source_info, ("name",), locale, base_obj=source_info
                )
                if not source_display_name:
                    source_display_name = str(source_info.get("name") or name)
                apps_node = data.get("apps")
                if not isinstance(apps_node, dict):
                    errors.append(
                        {
                            "source": name,
                            "url": url,
                            "message": "V2 source missing apps object",
                        }
                    )
                    continue
                for app_id, app_node in apps_node.items():
                    if not isinstance(app_node, dict):
                        continue
                    try:
                        app_obj, err = normalize_v2_app_item(
                            str(app_id),
                            app_node,
                            source_display_name,
                            source_url=url,
                            settings=settings,
                            locale=locale,
                            arch=arch,
                        )
                        if err:
                            # 应用级错误：跳过该应用，不影响其他应用
                            errors.append(
                                {
                                    "source": name,
                                    "url": url,
                                    "message": f"{app_id}: {err}",
                                }
                            )
                            continue
                        apps.append(app_obj)
                        known_keys.add(
                            task_key("thirdparty", str(app_id), app_obj["version"])
                        )
                    except Exception as exc:
                        errors.append(
                            {
                                "source": name,
                                "url": url,
                                "message": f"{app_id}: {exc}",
                            }
                        )
            else:
                # V1 兼容：扁平格式
                if isinstance(data, dict):
                    entries = data.items()
                else:
                    entries = [
                        (str(index), item) for index, item in enumerate(data or [])
                    ]
                for app_id, item in entries:
                    if isinstance(item, dict):
                        normalized = normalize_third_party_item(
                            str(app_id),
                            item,
                            name,
                            source_url=url,
                            settings=settings,
                            arch=arch,
                        )
                        # 架构不匹配或信息不全时返回 None，跳过该应用
                        if normalized is None:
                            continue
                        apps.append(normalized)
                        version = normalized.get("version", "")
                        known_keys.add(task_key("thirdparty", str(app_id), version))
        except Exception as exc:
            errors.append({"source": name, "url": url, "message": str(exc)})
    if official_ids is None:
        official_ids = set()
    vol = _env("TRIM_APPDEST_VOL")
    appcenter_dir = Path(vol) / "@appcenter" if vol else Path("/vol1/@appcenter")
    if appcenter_dir.is_dir():
        for entry in appcenter_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                official_ids.add(entry.name)
    appmeta_dir = Path(vol) / "@appmeta" if vol else Path("/vol1/@appmeta")
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
    # V2 新增：传递 sha256 和 size 用于校验
    expected_sha256 = str(app.get("sha256") or "").strip() or None
    expected_size = app.get("size")
    if expected_size is not None:
        expected_size = int(expected_size) if isinstance(expected_size, (int, float)) else None
    worker = threading.Thread(
        target=download_worker,
        args=(key, url, str(target)),
        kwargs={"expected_sha256": expected_sha256, "expected_size": expected_size},
        daemon=True,
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


def _compute_sha256(path):
    """计算文件的 SHA256 哈希值。"""
    import hashlib

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 256)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def download_worker(key, url, target, expected_sha256=None, expected_size=None):
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
        # V2 新增：size 校验
        if expected_size is not None and expected_size >= 0:
            actual_size = os.path.getsize(tmp)
            if actual_size != expected_size:
                raise RuntimeError(
                    f"size mismatch: expected {expected_size}, got {actual_size}"
                )
        # V2 新增：sha256 校验
        if expected_sha256:
            actual_sha256 = _compute_sha256(tmp)
            if actual_sha256.lower() != expected_sha256.lower():
                raise RuntimeError(
                    f"sha256 mismatch: expected {expected_sha256}, got {actual_sha256}"
                )
        os.replace(tmp, target)
        update_task(key, status="downloaded", path=target, fileExists=True, error="")
        finalize_download_file(target)
    except Exception as exc:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        finally:
            update_task(key, status="failed", error=str(exc))


def register_official_download(app, result):
    # 前端已调用 /app-center/v1/download/task，后端只注册任务状态
    app_id = str(app.get("id", ""))
    version = str(app.get("version", ""))
    source_id = str(app.get("sourceID", ""))
    volume_id = int(app.get("volumeID") or app.get("volume_id") or 1)
    if not app_id or not version or not source_id:
        raise RuntimeError("missing official download fields")
    result = result or {}
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
        "volumeID": volume_id,
        "status": "downloading",
        "path": str(download_path_for(app_id, version)),
        "fileExists": False,
        "updatedAt": int(time.time()),
        "raw": result,
    }
    save_tasks(tasks)
    return tasks["tasks"][key]


def status_payload(apps=None, status_results=None):
    # status_results: {taskKey: app-center 原始状态响应}，由前端直接从 /app-center/ 获取
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
        raw = (status_results or {}).get(key)
        if not raw:
            continue
        try:
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
    elif action == "process-apps":
        # app-center 原始数据（appList/latest）由前端直接获取，后端仅做处理
        settings = read_settings()
        app_raw = payload.get("appList") or {}
        latest_raw = payload.get("latest") or {}
        official_result = official_apps_from_raw(app_raw, latest_raw, settings=settings)
        official_ids = official_result.get("official_ids", set())
        try:
            thirdparty_result = third_party_apps(official_ids, settings=settings)
            thirdparty_errors = thirdparty_result.get("errors", [])
        except Exception as exc:
            thirdparty_result = {}
            thirdparty_errors = [{"source": "thirdparty", "message": str(exc)}]
        all_apps = official_result.get("apps", []) + thirdparty_result.get("apps", [])
        annotate_install_status(all_apps)
        tasks_data = status_payload(all_apps)
        json_response(
            {
                "ok": True,
                "apps": all_apps,
                "errors": thirdparty_errors,
                "tasks": tasks_data.get("tasks", {}),
                "files": tasks_data.get("files", {}),
            }
        )
    elif action == "download":
        app = payload.get("app")
        if isinstance(app, str):
            app = json.loads(app)
        if not isinstance(app, dict):
            raise RuntimeError("missing app")
        if app.get("store") == "official":
            # 前端已调用 /app-center/v1/download/task，后端只注册任务
            task = register_official_download(app, payload.get("taskResult"))
        else:
            task = start_third_party_download(app)
        json_response({"ok": True, "task": task})
    elif action == "delete":
        app = payload.get("app")
        if isinstance(app, str):
            app = json.loads(app)
        if not isinstance(app, dict):
            raise RuntimeError("missing app")
        json_response({"ok": True, "deleted": delete_download(app), **status_payload()})
    elif action == "status":
        status_results = payload.get("statusResults") or {}
        json_response(
            {"ok": True, **status_payload(payload.get("apps"), status_results)}
        )
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
