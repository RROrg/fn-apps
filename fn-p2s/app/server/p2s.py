# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import argparse
import gzip
import http.client
import json
import mimetypes
import os
import re
import select
import signal
import socket
import socketserver
import ssl
import sys
import urllib.parse
import zlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit

APP_NAME = "fn-p2s"
VAR_DIR = Path(f"/var/apps/{APP_NAME}/var")
SETTINGS_FILE = VAR_DIR / "mappings.json"
DEFAULT_SETTINGS = {"mappings": []}
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
STRIPPED_RESPONSE_HEADERS = {
    "content-security-policy",
    "content-security-policy-report-only",
    "cross-origin-embedder-policy",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
    "permissions-policy",
    "x-frame-options",
    "x-webkit-csp",
}
RESERVED_SLUGS = {"", "api", "app.js", "style.css", "index.html"}
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
BaseUnixServer = getattr(socketserver, "UnixStreamServer", socketserver.TCPServer)


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

    def do_PATCH(self):
        self.route()

    def do_DELETE(self):
        self.route()

    def do_OPTIONS(self):
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

        mapping, rest_path = mapping_for_path(path)
        if mapping:
            if mapping.get("inject") and rest_path == "/sw.js":
                self.serve_sw(mapping)
                return
            if rest_path == "/" and not parsed.path.endswith("/"):
                location = local_root(self, mapping)
                if parsed.query:
                    location += "?" + parsed.query
                self.send_empty(HTTPStatus.MOVED_PERMANENTLY, {"Location": location})
                return
            if is_websocket_upgrade(self.headers):
                self.forward_websocket(mapping, rest_path, parsed.query)
            else:
                self.forward_http(mapping, rest_path, parsed.query)
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

    def serve_sw(self, mapping):
        sw_path = self.server.www_root / "sw.js"
        if not sw_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Service Worker not found")
            return
        body = sw_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def serve_api(self, query):
        try:
            payload = request_payload(self, query)
            action = payload.get("action", "list")
            if action == "list":
                json_response(self, {"ok": True, "mappings": read_mappings()})
            elif action == "save":
                mapping = save_mapping(payload.get("mapping") or {})
                json_response(
                    self, {"ok": True, "mapping": mapping, "mappings": read_mappings()}
                )
            elif action == "delete":
                delete_mapping(str(payload.get("slug") or ""))
                json_response(self, {"ok": True, "mappings": read_mappings()})
            elif action == "test":
                mapping = normalize_mapping(
                    payload.get("mapping") or {},
                    existing_slug=str(payload.get("existingSlug") or ""),
                )
                json_response(self, {"ok": True, "reachable": test_mapping(mapping)})
            else:
                json_response(
                    self,
                    {"ok": False, "message": "unsupported action"},
                    HTTPStatus.BAD_REQUEST,
                )
        except Exception as exc:
            json_response(
                self,
                {"ok": False, "message": str(exc)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def forward_http(self, mapping, rest_path, query):
        upstream_path = rest_path or "/"
        if not upstream_path.startswith("/"):
            upstream_path = "/" + upstream_path
        if query:
            upstream_path += "?" + query

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = build_upstream_headers(self, mapping)

        conn_cls = (
            http.client.HTTPSConnection
            if mapping.get("scheme") == "https"
            else http.client.HTTPConnection
        )
        conn = conn_cls(mapping["host"], int(mapping["port"]), timeout=60)
        try:
            conn.request(self.command, upstream_path, body=body, headers=headers)
            response = conn.getresponse()
            response_body = response.read()
            response_headers = response.getheaders()
        except Exception as exc:
            self.send_text(502, f"Proxy error: {exc}")
            return
        finally:
            conn.close()

        response_body, decoded = decode_response_body(response_headers, response_body)
        content_type = header_lookup(response_headers, "Content-Type")
        is_html = "text/html" in (content_type or "").lower()
        response_body, content_length = maybe_rewrite_body(
            self, mapping, rest_path, response_body, content_type
        )

        self.send_response(response.status, response.reason)
        for name, value in response_headers:
            lower = name.lower()
            if lower in HOP_BY_HOP_HEADERS or lower == "content-length":
                continue
            if lower == "content-encoding" and decoded:
                continue
            if lower in STRIPPED_RESPONSE_HEADERS:
                continue
            if decoded and lower in {"etag", "last-modified"}:
                continue
            if is_html and lower in {"etag", "last-modified", "cache-control"}:
                continue
            if lower == "location":
                value = rewrite_location(self, mapping, value)
            elif lower == "refresh":
                value = rewrite_refresh(self, mapping, value)
            elif lower == "set-cookie":
                value = rewrite_cookie(self, mapping, value)
            self.send_header(name, value)
        self.send_header("Content-Length", str(content_length))
        if is_html:
            self.send_header("Cache-Control", "no-store")
        self.send_header(
            "X-Fn-P2S-Upstream",
            f"{mapping['scheme']}://{mapping['host']}:{mapping['port']}",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response_body)

    def forward_websocket(self, mapping, rest_path, query):
        upstream_path = rest_path or "/"
        if query:
            upstream_path += "?" + query
        try:
            upstream = socket.create_connection(
                (mapping["host"], int(mapping["port"])), timeout=20
            )
            if mapping.get("scheme") == "https":
                context = ssl.create_default_context()
                upstream = context.wrap_socket(
                    upstream, server_hostname=mapping["host"]
                )
            headers = build_websocket_headers(self, mapping, upstream_path)
            upstream.sendall(headers)
            response = read_until_header_end(upstream)
            self.connection.sendall(response)
            if not response.startswith(b"HTTP/1.1 101") and not response.startswith(
                b"HTTP/1.0 101"
            ):
                upstream.close()
                return
            relay_sockets(self.connection, upstream)
        except Exception as exc:
            try:
                self.send_text(502, f"WebSocket proxy error: {exc}")
            except Exception:
                pass

    def send_empty(self, status, headers=None):
        self.send_response(int(status))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_text(self, status, text):
        body = str(text).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def normalize_base_path(path):
    normalized = (path or "/").strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized.rstrip("/") or "/"


def strip_base_path(path, base_path):
    normalized = path or "/"
    if base_path != "/" and normalized.startswith(base_path):
        return normalized[len(base_path) :] or "/"
    return normalized


def normalize_public_path(path):
    normalized = (path or "").strip()
    if not normalized:
        return ""
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized.rstrip("/") or "/"


def join_public_paths(*parts):
    clean = []
    for part in parts:
        normalized = normalize_public_path(part)
        if normalized and normalized != "/":
            clean.append(normalized.strip("/"))
    return "/" + "/".join(clean) if clean else "/"


def configured_base_in_path(path, base_path):
    normalized = path or "/"
    base = normalize_base_path(base_path)
    if base == "/" or normalized == base or normalized.startswith(base + "/"):
        return base
    index = normalized.find(base)
    while index != -1:
        after_index = index + len(base)
        after_ok = after_index == len(normalized) or normalized[after_index] == "/"
        if after_ok:
            return normalized[:after_index]
        index = normalized.find(base, index + 1)
    return base


def forwarded_prefix(handler):
    for name in ("X-Forwarded-Prefix", "X-Script-Name"):
        value = handler.headers.get(name)
        if value:
            first = value.split(",", 1)[0]
            return normalize_public_path(first)
    return ""


def route_base_path(handler, path=None):
    return configured_base_in_path(
        path or urlsplit(handler.path).path, handler.server.base_path
    )


def public_base_path(handler, path=None):
    configured = handler.server.base_path
    derived = route_base_path(handler, path)
    prefix = forwarded_prefix(handler)
    if not prefix:
        return derived
    if prefix == derived or prefix.endswith(derived):
        return prefix
    if derived.startswith(prefix + "/"):
        return derived
    return join_public_paths(prefix, derived)


def ensure_dirs():
    VAR_DIR.mkdir(parents=True, exist_ok=True)


def read_settings():
    ensure_dirs()
    if not SETTINGS_FILE.exists():
        write_settings(DEFAULT_SETTINGS)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        data = DEFAULT_SETTINGS.copy()
    if not isinstance(data.get("mappings"), list):
        data["mappings"] = []
    clean = []
    for item in data["mappings"]:
        try:
            clean.append(normalize_mapping(item, allow_duplicate=True))
        except Exception:
            continue
    data["mappings"] = clean
    return data


def write_settings(data):
    ensure_dirs()
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


def read_mappings():
    return read_settings().get("mappings", [])


def normalize_mapping(raw, *, existing_slug="", allow_duplicate=False):
    if not isinstance(raw, dict):
        raise RuntimeError("mapping must be an object")
    slug = str(raw.get("slug") or "").strip().strip("/")
    if not SLUG_RE.match(slug) or slug.lower() in RESERVED_SLUGS:
        raise RuntimeError(
            "slug must be 1-64 letters, numbers, '-' or '_' and cannot be reserved"
        )
    host = str(raw.get("host") or "127.0.0.1").strip()
    if not host:
        host = "127.0.0.1"
    try:
        port = int(raw.get("port", 0))
    except Exception:
        port = 0
    if port < 1 or port > 65535:
        raise RuntimeError("port must be between 1 and 65535")
    scheme = str(raw.get("scheme") or "http").lower()
    if scheme not in {"http", "https"}:
        raise RuntimeError("scheme must be http or https")
    name = str(raw.get("name") or slug).strip()[:80]
    description = str(raw.get("description") or "").strip()[:240]
    enabled = raw.get("enabled") is not False
    inject = raw.get("inject") is True
    open_mode = str(raw.get("openMode") or "window").strip().lower()
    if open_mode not in {"window", "iframe"}:
        open_mode = "window"

    if not allow_duplicate:
        for item in read_mappings():
            if item["slug"] == slug and item["slug"] != existing_slug:
                raise RuntimeError("slug already exists")

    return {
        "slug": slug,
        "name": name or slug,
        "scheme": scheme,
        "host": host,
        "port": port,
        "enabled": enabled,
        "inject": inject,
        "openMode": open_mode,
        "description": description,
    }


def save_mapping(raw):
    existing_slug = (
        str(raw.get("existingSlug") or raw.get("slug") or "").strip().strip("/")
    )
    mapping = normalize_mapping(raw, existing_slug=existing_slug)
    data = read_settings()
    mappings = [
        item
        for item in data.get("mappings", [])
        if item.get("slug") != existing_slug and item.get("slug") != mapping["slug"]
    ]
    mappings.append(mapping)
    mappings.sort(key=lambda item: item["slug"].lower())
    data["mappings"] = mappings
    write_settings(data)
    return mapping


def delete_mapping(slug):
    slug = slug.strip().strip("/")
    data = read_settings()
    data["mappings"] = [
        item for item in data.get("mappings", []) if item.get("slug") != slug
    ]
    write_settings(data)


def mapping_for_path(path):
    parts = (path or "/").lstrip("/").split("/", 1)
    slug = parts[0]
    if not slug:
        return None, "/"
    rest = "/" + parts[1] if len(parts) > 1 else "/"
    for item in read_mappings():
        if item.get("slug") == slug and item.get("enabled", True):
            return item, rest
    return None, rest


def test_mapping(mapping):
    try:
        with socket.create_connection(
            (mapping["host"], int(mapping["port"])), timeout=3
        ):
            return True
    except Exception:
        return False


def request_payload(handler, query):
    method = handler.command.upper()
    if method in {"POST", "PUT", "PATCH"}:
        length = int(handler.headers.get("Content-Length") or 0)
        raw = handler.rfile.read(length).decode("utf-8", "replace") if length else ""
        if "application/json" in (handler.headers.get("Content-Type") or ""):
            return json.loads(raw or "{}")
        parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}
    parsed = urllib.parse.parse_qs(query, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def json_response(handler, payload, status=HTTPStatus.OK):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    handler.send_response(int(status))
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    if handler.command != "HEAD":
        handler.wfile.write(body)


def header_lookup(headers, name):
    target = name.lower()
    for key, value in headers:
        if key.lower() == target:
            return value
    return ""


def build_upstream_headers(handler, mapping):
    headers = {}
    for name, value in handler.headers.items():
        lower = name.lower()
        if lower in HOP_BY_HOP_HEADERS or lower == "host":
            continue
        if lower == "accept-encoding":
            headers[name] = "identity"
            continue
        if lower == "origin":
            headers[name] = rewrite_request_origin(handler, mapping, value)
            continue
        if lower == "referer":
            headers[name] = rewrite_request_referer(handler, mapping, value)
            continue
        headers[name] = value
    headers["Host"] = f"{mapping['host']}:{mapping['port']}"
    headers["X-Forwarded-Host"] = handler.headers.get("Host", "")
    headers["X-Forwarded-Proto"] = "https"
    headers["X-Forwarded-Prefix"] = local_prefix(handler, mapping)
    return headers


def local_prefix(handler, mapping):
    return f"{public_base_path(handler)}/{mapping['slug']}"


def local_root(handler, mapping):
    return local_prefix(handler, mapping) + "/"


def upstream_origin(mapping):
    return f"{mapping['scheme']}://{mapping['host']}:{mapping['port']}"


def rewrite_location(handler, mapping, value):
    if not value:
        return value
    parsed = urlsplit(value)
    origin = upstream_origin(mapping)
    if parsed.scheme and parsed.netloc:
        target_origin = f"{parsed.scheme}://{parsed.netloc}"
        if target_origin == origin:
            path = parsed.path or "/"
            return (
                local_prefix(handler, mapping)
                + path
                + (("?" + parsed.query) if parsed.query else "")
                + (("#" + parsed.fragment) if parsed.fragment else "")
            )
        return value
    if value.startswith("/"):
        return local_prefix(handler, mapping) + value
    return value


def rewrite_refresh(handler, mapping, value):
    if not value:
        return value

    def replace_url(match):
        return match.group(1) + rewrite_location(
            handler, mapping, match.group(2).strip()
        )

    return re.sub(r"(?i)(url\s*=\s*)([^;]+)", replace_url, value, count=1)


def rewrite_request_origin(handler, mapping, value):
    if not value:
        return value
    try:
        parsed = urlsplit(value)
        local_host = (handler.headers.get("Host") or "").lower()
        if parsed.netloc.lower() == local_host:
            return upstream_origin(mapping)
    except Exception:
        pass
    return value


def rewrite_request_referer(handler, mapping, value):
    if not value:
        return value
    try:
        parsed = urlsplit(value)
        local_host = (handler.headers.get("Host") or "").lower()
        prefix = local_prefix(handler, mapping)
        if parsed.netloc.lower() == local_host and parsed.path.startswith(prefix):
            path = parsed.path[len(prefix) :] or "/"
            return (
                upstream_origin(mapping)
                + path
                + (("?" + parsed.query) if parsed.query else "")
            )
    except Exception:
        pass
    return value


def rewrite_cookie(handler, mapping, value):
    prefix = local_prefix(handler, mapping)
    rewritten = re.sub(r"(?i)(;\s*path=)/", r"\1" + prefix + "/", value)
    rewritten = re.sub(r"(?i);\s*domain=[^;]*", "", rewritten)
    return rewritten


def decode_response_body(headers, body):
    encoding = (header_lookup(headers, "Content-Encoding") or "").lower().strip()
    if not body or not encoding or encoding in {"identity", "none"}:
        return body, False
    try:
        if encoding == "gzip":
            return gzip.decompress(body), True
        if encoding == "deflate":
            try:
                return zlib.decompress(body), True
            except zlib.error:
                return zlib.decompress(body, -zlib.MAX_WBITS), True
    except Exception:
        return body, False
    return body, False


CSS_URL_PATTERN = re.compile(
    r'(?P<prefix>url\(\s*["\']?)(?P<value>[^)"\']+)(?P<suffix>["\']?\s*\))',
    re.IGNORECASE,
)
CSS_IMPORT_PATTERN = re.compile(
    r'(?P<prefix>@import\s+(?:url\(\s*)?["\']?)(?P<value>[^)"\';]+)(?P<suffix>["\']?\s*\)?)(?P<tail>[^;]*;)',
    re.IGNORECASE,
)


def rewrite_css_body(handler, mapping, rest_path, body):
    try:
        text = body.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            text = body.decode("gb18030")
            encoding = "gb18030"
        except UnicodeDecodeError:
            return body, len(body)
    prefix = local_prefix(handler, mapping)
    css_url = prefix + rest_path

    def rewrite_css_url(value):
        value = value.strip()
        if not value or value.startswith(
            ("data:", "javascript:", "mailto:", "#", "http://", "https://", "//")
        ):
            return value
        if value.startswith("/"):
            return prefix + value
        return urllib.parse.urljoin(css_url, value)

    def rewrite_url(match):
        value = match.group("value").strip()
        new_value = rewrite_css_url(value)
        if new_value == value:
            return match.group(0)
        return match.group("prefix") + new_value + match.group("suffix")

    def rewrite_import(match):
        value = match.group("value").strip()
        new_value = rewrite_css_url(value)
        if new_value == value:
            return match.group(0)
        return (
            match.group("prefix")
            + new_value
            + match.group("suffix")
            + match.group("tail")
        )

    text = CSS_URL_PATTERN.sub(rewrite_url, text)
    text = CSS_IMPORT_PATTERN.sub(rewrite_import, text)
    next_body = text.encode(encoding)
    return next_body, len(next_body)


def maybe_rewrite_body(handler, mapping, rest_path, body, content_type):
    if handler.command == "HEAD":
        return b"", 0
    lowered = (content_type or "").lower()
    if "text/css" in lowered:
        return rewrite_css_body(handler, mapping, rest_path, body)
    if "text/html" not in lowered:
        return body, len(body)
    try:
        text = body.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            text = body.decode("gb18030")
            encoding = "gb18030"
        except UnicodeDecodeError:
            return body, len(body)
    text = rewrite_html_head(text, handler, mapping)
    if mapping.get("inject"):
        text = rewrite_html_urls(text, handler, mapping)
        text = remove_html_csp_meta(text)
        inject = proxy_bootstrap(handler, mapping, include_base=not has_base_tag(text))
        if "</head>" in text.lower():
            idx = text.lower().find("</head>")
            text = text[:idx] + inject + text[idx:]
        else:
            text = inject + text
    next_body = text.encode(encoding)
    return next_body, len(next_body)


def has_base_tag(text):
    return re.search(r"(?is)<base\b[^>]*>", text) is not None


def remove_html_csp_meta(text):
    return re.sub(
        r"(?is)<meta\b(?=[^>]*http-equiv\s*=\s*(['\"]?)content-security-policy\1)[^>]*>",
        "",
        text,
    )


HTML_ATTR_PATTERN = re.compile(
    r'(?is)(<(?:script|link|img|iframe|source|video|audio|embed|object|form|a|area|base)\b[^>]*?\b(?P<attr>srcset|src|href|action|data|poster)\s*=\s*)(["\'])(/[^"\']*?)\3',
)
HTML_SRCSET_PATTERN = re.compile(
    r'(?is)(\bsrcset\s*=\s*)(["\'])(/[^"\']*?)\2',
)


def rewrite_html_urls(text, handler, mapping):
    prefix = local_prefix(handler, mapping)

    def replace_attr(match):
        before = match.group(1)
        attr = match.group("attr").lower()
        quote = match.group(3)
        path = match.group(4)
        if path.startswith(prefix + "/") or path.startswith(prefix):
            return match.group(0)
        if attr == "srcset":
            return before + quote + rewrite_srcset(prefix, path) + quote
        return before + quote + prefix + path + quote

    text = HTML_ATTR_PATTERN.sub(replace_attr, text)

    def replace_srcset(match):
        value = match.group(3)
        if value.startswith(prefix + "/") or value.startswith(prefix):
            return match.group(0)
        return (
            match.group(1)
            + match.group(2)
            + rewrite_srcset(prefix, value)
            + match.group(2)
        )

    return HTML_SRCSET_PATTERN.sub(replace_srcset, text)


def rewrite_srcset(prefix, value):
    parts = []
    for candidate in str(value).split(","):
        chunks = candidate.strip().split()
        if (
            chunks
            and chunks[0].startswith("/")
            and not chunks[0].startswith(prefix + "/")
        ):
            chunks[0] = prefix + chunks[0]
        parts.append(" ".join(chunks))
    return ", ".join(parts)


def rewrite_html_head(text, handler, mapping):
    root = html_escape(local_root(handler, mapping))

    def replace_base(match):
        tag = match.group(0)
        if re.search(r"(?is)\bhref\s*=", tag):
            return re.sub(
                r"(?is)\bhref\s*=\s*(['\"])[^'\"]*\1", f'href="{root}"', tag, count=1
            )
        return tag[:-1].rstrip() + f' href="{root}">'

    rewritten, count = re.subn(r"(?is)<base\b[^>]*>", replace_base, text, count=1)
    if count:
        return rewritten
    base = f'<base href="{root}">'
    if re.search(r"(?is)<head\b[^>]*>", rewritten):
        return re.sub(r"(?is)(<head\b[^>]*>)", r"\1" + base, rewritten, count=1)
    return base + rewritten


def proxy_bootstrap(handler, mapping, include_base=True):
    root = json.dumps(local_root(handler, mapping), ensure_ascii=False)
    base = (
        '<base href="%s">' % html_escape(local_root(handler, mapping))
        if include_base
        else ""
    )
    return (
        "%s"
        '<script id="fn-p2s-bootstrap">(function(){'
        '"use strict";'
        'var root=%s,rootPath=root.replace(/\\/$/,"");'
        "var skip=/^(?:about|blob|data|javascript|mailto|tel):/i;"
        "function baseHref(){return document.baseURI||location.href;}"
        'function sameOrigin(x){return x.origin===location.origin||x.origin==="null"&&location.origin==="null"}'
        "function localUrl(u){try{if(u==null)return u;var raw=String(u);if(skip.test(raw))return u;"
        'var x=new URL(raw,baseHref());if(sameOrigin(x)&&x.pathname.charAt(0)==="/"&&x.pathname.indexOf(root)!==0&&x.pathname!==rootPath){x.pathname=rootPath+x.pathname;}'
        "return x.href;}catch(e){return u;}}"
        "function localWsUrl(u){try{var y=new URL(String(u),baseHref());var same=(y.hostname===location.hostname&&y.port===location.port);"
        'if(same&&y.pathname.charAt(0)==="/"&&y.pathname.indexOf(root)!==0&&y.pathname!==rootPath)y.pathname=rootPath+y.pathname;'
        'y.protocol=y.protocol==="https:"?"wss:":y.protocol==="http:"?"ws:":y.protocol;return y.href;}catch(e){var x=localUrl(u);return String(x).replace(/^http/,"ws");}}'
        'var _lp=Location.prototype,_opn=Object.getOwnPropertyDescriptor(_lp,"pathname");'
        'if(_opn){Object.defineProperty(_lp,"pathname",{'
        'get:function(){var r=_opn.get.call(this);return r===rootPath?"/":r.indexOf(rootPath+"/")===0?r.substring(rootPath.length):r;},'
        'set:function(v){var s=String(v);_opn.set.call(this,s.charAt(0)==="/"&&s.indexOf(rootPath+"/")!==0&&s!==rootPath?rootPath+s:s);},'
        "configurable:true,enumerable:true});}"
        'var _ohl=Object.getOwnPropertyDescriptor(_lp,"href");'
        'if(_ohl){Object.defineProperty(_lp,"href",{'
        "get:_ohl.get,"
        'set:function(v){var s=String(v);if(s.charAt(0)==="/"){_ohl.set.call(this,s.indexOf(rootPath+"/")!==0&&s!==rootPath?rootPath+s:s);}else{try{var u=new URL(s,_ohl.get.call(this));if(u.origin===location.origin&&u.pathname.charAt(0)==="/"&&u.pathname.indexOf(rootPath+"/")!==0&&u.pathname!==rootPath)u.pathname=rootPath+u.pathname;_ohl.set.call(this,u.href);}catch(e){_ohl.set.call(this,s);}}},'
        "configurable:true,enumerable:true});}"
        "var _as=_lp.assign;if(_as)_lp.assign=function(u){return _as.call(this,localUrl(u));};"
        "var _rp=_lp.replace;if(_rp)_lp.replace=function(u){return _rp.call(this,localUrl(u));};"
        "function patchCtor(name,mapper){var C=window[name];if(!C)return;var P=function(a,b){return b!==undefined?new C(mapper(a),b):new C(mapper(a));};"
        "try{Object.setPrototypeOf(P,C);P.prototype=C.prototype;window[name]=P;}catch(e){}}"
        'var f=window.fetch;if(f){window.fetch=function(r,i){try{if(typeof r==="string"||r instanceof URL){r=localUrl(r);}'
        "else if(window.Request&&r instanceof Request){r=new Request(localUrl(r.url),r);}}catch(e){}return f.call(this,r,i);};}"
        "var open=window.XMLHttpRequest&&XMLHttpRequest.prototype.open;if(open){XMLHttpRequest.prototype.open=function(m,u){arguments[1]=localUrl(u);return open.apply(this,arguments);};}"
        'patchCtor("WebSocket",localWsUrl);patchCtor("EventSource",localUrl);patchCtor("Worker",localUrl);patchCtor("SharedWorker",localUrl);'
        "var sb=navigator.sendBeacon;if(sb){navigator.sendBeacon=function(u,d){return sb.call(this,localUrl(u),d);};}"
        'var wo=window.open;if(wo){window.open=function(u,n,f){var t=String(n||"").toLowerCase();if(t==="_top"||t==="_parent"||t==="_self"){location.href=localUrl(u);return window;}return wo.call(this,u?localUrl(u):u,n,f);};}'
        '["pushState","replaceState"].forEach(function(n){var h=history[n];if(h){history[n]=function(s,t,u){if(u!==undefined)u=localUrl(u);return h.call(this,s,t,u);};}});'
        'var attrs={A:["href"],AREA:["href"],LINK:["href"],SCRIPT:["src"],IMG:["src","srcset"],IFRAME:["src"],SOURCE:["src","srcset"],VIDEO:["src","poster"],AUDIO:["src"],FORM:["action"],OBJECT:["data"],EMBED:["src"]};'
        'function mapSrcset(v){return String(v).split(",").map(function(p){var s=p.trim().split(/\\s+/);if(s[0])s[0]=localUrl(s[0]);return s.join(" ");}).join(", ");}'
        'function fixAttr(el,a){var v=el.getAttribute&&el.getAttribute(a);if(!v)return;el.setAttribute(a,a==="srcset"?mapSrcset(v):localUrl(v));}'
        "function fixEl(el){if(!el||el.nodeType!==1)return;var list=attrs[el.tagName];if(list)list.forEach(function(a){fixAttr(el,a);});}"
        "var sa=Element.prototype.setAttribute;Element.prototype.setAttribute=function(n,v){var a=String(n).toLowerCase();"
        'if((a==="href"||a==="src"||a==="action"||a==="poster"||a==="data")&&v!=null)v=localUrl(v);else if(a==="srcset"&&v!=null)v=mapSrcset(v);return sa.call(this,n,v);};'
        "function prop(proto,name,mapper){try{var d=Object.getOwnPropertyDescriptor(proto,name);if(!d||!d.set)return;Object.defineProperty(proto,name,{get:d.get,set:function(v){d.set.call(this,mapper(v));},configurable:true,enumerable:d.enumerable});}catch(e){}}"
        '[[window.HTMLAnchorElement&&HTMLAnchorElement.prototype,"href",localUrl],[window.HTMLAreaElement&&HTMLAreaElement.prototype,"href",localUrl],[window.HTMLLinkElement&&HTMLLinkElement.prototype,"href",localUrl],[window.HTMLScriptElement&&HTMLScriptElement.prototype,"src",localUrl],[window.HTMLImageElement&&HTMLImageElement.prototype,"src",localUrl],[window.HTMLIFrameElement&&HTMLIFrameElement.prototype,"src",localUrl],[window.HTMLFormElement&&HTMLFormElement.prototype,"action",localUrl]].forEach(function(x){if(x[0])prop(x[0],x[1],x[2]);});'
        'document.addEventListener("click",function(e){if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;'
        'var a=e.target&&e.target.closest&&e.target.closest("a[href]");if(!a)return;var href=a.getAttribute("href"),t=String(a.getAttribute("target")||"").toLowerCase();'
        'try{var u=new URL(href,baseHref());if(!skip.test(String(href||""))&&!sameOrigin(u)){e.preventDefault();window.open(u.href,"_blank","noopener");return;}}catch(ex){}'
        'if(t==="_top"||t==="_parent"){e.preventDefault();location.href=localUrl(href);}},false);'
        'document.addEventListener("submit",function(e){var f=e.target;if(!f||!f.getAttribute)return;var t=String(f.getAttribute("target")||"").toLowerCase();'
        'if(t==="_top"||t==="_parent"){f.setAttribute("target","_self");if(f.getAttribute("action"))f.setAttribute("action",localUrl(f.getAttribute("action")));}},true);'
        'Array.prototype.forEach.call(document.querySelectorAll("*"),fixEl);'
        'if(window.MutationObserver){new MutationObserver(function(ms){ms.forEach(function(m){Array.prototype.forEach.call(m.addedNodes,function(n){fixEl(n);if(n.querySelectorAll)Array.prototype.forEach.call(n.querySelectorAll("*"),fixEl);});});}).observe(document.documentElement,{childList:true,subtree:true});}'
        "if('serviceWorker' in navigator){navigator.serviceWorker.register(rootPath+'/sw.js',{scope:root}).catch(function(){});}"
        "})();</script>"
    ) % (base, root)


def html_escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def is_websocket_upgrade(headers):
    return (
        "upgrade" in (headers.get("Connection") or "").lower()
        and (headers.get("Upgrade") or "").lower() == "websocket"
    )


def build_websocket_headers(handler, mapping, upstream_path):
    lines = [
        f"{handler.command} {upstream_path} HTTP/1.1",
        f"Host: {mapping['host']}:{mapping['port']}",
    ]
    for name, value in handler.headers.items():
        lower = name.lower()
        if lower in {"host", "proxy-connection"}:
            continue
        lines.append(f"{name}: {value}")
    lines.extend(
        [
            f"X-Forwarded-Host: {handler.headers.get('Host', '')}",
            "X-Forwarded-Proto: https",
            f"X-Forwarded-Prefix: {local_prefix(handler, mapping)}",
            "",
            "",
        ]
    )
    return "\r\n".join(lines).encode("iso-8859-1", "replace")


def read_until_header_end(sock):
    chunks = []
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        if len(data) > 65536:
            break
    return data


def relay_sockets(left, right):
    sockets = [left, right]
    try:
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 60)
            if exceptional:
                break
            if not readable:
                continue
            for source in readable:
                target = right if source is left else left
                data = source.recv(65536)
                if not data:
                    return
                target.sendall(data)
    finally:
        try:
            right.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="fn-p2s port-to-path proxy")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-p2s")
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
