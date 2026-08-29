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
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import urllib.parse
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-appsettings")
DB_NAME = "appcenter"
DB_USER = "postgres"

REQUEST_CONTEXT = threading.local()

APP_COLUMNS = [
    ("app_name", "text"),
    ("name", "text"),
    ("version", "text"),
    ("version_id", "int"),
    ("tags", "text"),
    ("maintainer", "text"),
    ("distributor", "text"),
    ("download_count", "bigint"),
    ("install_type", "text"),
    ("path", "text"),
    ("install_volume_id", "int"),
    ("data_share_volume_id", "int"),
    ("data_volume_id", "int"),
    ("manual_install", "bool"),
    ("is_stop", "bool"),
    ("is_uninstall", "bool"),
    ("is_beta", "bool"),
    ("is_docker", "bool"),
    ("min_size", "bigint"),
    ("service_url", "text"),
    ("source", "text"),
    ("source_id", "text"),
    ("status", "text"),
    ("is_non_manual_stop", "bool"),
    ("is_systemd_uint", "bool"),
    ("disable_authorization_path", "bool"),
    ("features", "text"),
    ("micro_app", "bool"),
    ("native_app", "bool"),
    ("file_types", "text_array"),
    ("is_power_off_stop", "int"),
    ("i18n_matadata", "text"),
    ("disabled_reason", "int"),
    ("disabled_at", "bigint"),
]

APP_READONLY_COLUMNS = {
    "version_id",
    "install_type",
    "path",
    "install_volume_id",
    "data_share_volume_id",
    "data_volume_id",
    "is_docker",
    "source_id",
    "status",
    "disabled_reason",
    "disabled_at",
}

SERVICE_COLUMNS = [
    ("service_name", "text"),
    ("title", "text"),
    ("desc", "text"),
    ("icon", "text"),
    ("type", "text"),
    ("url", "text"),
    ("default_url", "text"),
    ("is_admin", "bool"),
    ("control", "text"),
    ("full_url", "text"),
    ("no_display", "bool"),
    ("gateway_socket", "text"),
    ("gateway_prefix", "text"),
    ("file_types", "text"),
    ("i18n_matadata", "text"),
]

ENV_COLUMNS = [("k", "text"), ("v", "text")]


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
                if self.command == "GET" and api_query_action(query) == "icon":
                    serve_app_icon()
                    return
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


def api_query_action(query):
    parsed = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    return (parsed.get("action") or [""])[-1]


def query_value(name, default=""):
    request = current_request()
    parsed = urllib.parse.parse_qs(request.get("query", ""), keep_blank_values=True)
    return (parsed.get(name) or [default])[-1]


def send_binary_response(data, content_type, status=200):
    request = current_request()
    handler = request.get("handler", None)
    if handler is None:
        return
    code, _status_text = normalize_status(status)
    handler.send_response(code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "public, max-age=60")
    handler.end_headers()
    if handler.command != "HEAD":
        handler.wfile.write(data)


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


def sql_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def quote_ident(name):
    return '"' + str(name).replace('"', '""') + '"'


def nullable_text(value):
    if value is None:
        return "NULL"
    return sql_quote(value)


def bool_sql(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    text = str(value).strip().lower()
    return "TRUE" if text in {"1", "t", "true", "yes", "on"} else "FALSE"


def int_sql(value, default="NULL"):
    if value in (None, ""):
        return default
    return str(int(value))


def text_array_sql(value):
    if value in (None, ""):
        return "NULL"
    text = str(value).strip()
    if not (text.startswith("{") and text.endswith("}")):
        try:
            items = json.loads(text)
            if isinstance(items, list):
                text = (
                    "{"
                    + ",".join(str(item).replace('"', '\\"') for item in items)
                    + "}"
                )
        except Exception:
            text = "{}"
    return f"{sql_quote(text)}::text[]"


def value_sql(value, kind):
    if kind == "bool":
        return bool_sql(value)
    if kind in {"int", "bigint"}:
        return int_sql(value)
    if kind == "text_array":
        return text_array_sql(value)
    return nullable_text(value)


def parse_json_output(text, fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception as exc:
        raise RuntimeError(f"database returned invalid JSON: {exc}")


def app_icon_path(app_id):
    app_id = int(app_id)
    path = run_sql(f"SELECT path FROM app WHERE id={app_id}")
    if not path:
        return None
    return Path(path) / "ICON.PNG"


def privilege_path_for_app(app):
    path = (app or {}).get("path")
    if not path:
        return None
    return Path(str(path)) / "config" / "privilege"


def privilege_path_for_app_id(app_id):
    path = run_sql(f"SELECT path FROM app WHERE id={int(app_id)}")
    if not path:
        return None
    return Path(path) / "config" / "privilege"


def read_run_as(app):
    target = privilege_path_for_app(app)
    if not target or not target.is_file():
        return "root"
    try:
        data = json.loads(target.read_text(encoding="utf-8", errors="replace") or "{}")
    except Exception:
        return "root"
    run_as = (data.get("defaults") or {}).get("run-as") or "root"
    return "package" if run_as == "package" else "root"


def write_run_as(app_id, run_as):
    target = privilege_path_for_app_id(app_id)
    if not target:
        raise RuntimeError("missing app path for privilege")
    try:
        data = (
            json.loads(target.read_text(encoding="utf-8") or "{}")
            if target.is_file()
            else {}
        )
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
        data["defaults"] = defaults
    defaults["run-as"] = "package" if run_as == "package" else "root"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def header_value(headers, name):
    if not headers:
        return ""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


def app_status_and_name(app_id):
    sql = (
        "SELECT COALESCE(row_to_json(t)::text, '{}') "
        f"FROM (SELECT app_name, status FROM app WHERE id={int(app_id)}) t"
    )
    try:
        row = json.loads(run_sql(sql) or "{}")
    except Exception:
        row = {}
    return str(row.get("app_name") or ""), str(row.get("status") or "")


def restart_action(app_name, action):
    appcenter_path = shutil.which("appcenter-cli")
    if not appcenter_path:
        raise RuntimeError("appcenter-cli not found")
    try:
        proc = subprocess.run(
            [appcenter_path, action, app_name],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
            check=False,
        )
        if proc.returncode == 0:
            return f"info: {action} {app_name} via appcenter-cli"
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"appcenter-cli rc={proc.returncode}: {detail}")
    except Exception as error:
        raise RuntimeError(str(error))


def restart_app_after_save(app_id):
    app_name, status = app_status_and_name(app_id)
    if not app_name:
        return ["warning: app row not found; restart skipped"]
    if app_name == APP_NAME:
        return [f"info: restart skipped for {APP_NAME} itself"]
    if status.strip().lower() != "running":
        return [f"info: {app_name} status is {status or 'unknown'}; restart skipped"]
    messages = []
    for action in ("stop", "start"):
        try:
            messages.append(restart_action(app_name, action))
        except Exception as error:
            messages.append(f"warning: {action} {app_name} failed: {error}")
            if action == "stop":
                break
    return messages


def serve_app_icon():
    app_id = query_value("id")
    if not app_id:
        json_response({"ok": False, "message": "missing app id"}, "400 Bad Request")
        return
    icon_path = app_icon_path(app_id)
    if not icon_path or not icon_path.is_file():
        json_response({"ok": False, "message": "icon not found"}, "404 Not Found")
        return
    content_type = mimetypes.guess_type(str(icon_path))[0] or "image/png"
    send_binary_response(icon_path.read_bytes(), content_type)


def list_data():
    apps_sql = """
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY t.id), '[]'::json)
FROM (
  SELECT id, app_name, name, version, version_id, tags, maintainer, distributor,
         download_count, install_type, path, install_volume_id, data_share_volume_id,
         data_volume_id, manual_install, is_stop, is_uninstall, is_beta, is_docker,
         min_size, service_url, source, source_id, status, is_non_manual_stop,
         is_systemd_uint, disable_authorization_path, features, micro_app, native_app,
         COALESCE(file_types::text, '') AS file_types, is_power_off_stop,
         i18n_matadata, disabled_reason, disabled_at, created_at, updated_at
  FROM app
) t
"""
    services_sql = """
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY t.app_id, t.id), '[]'::json)
FROM (
  SELECT id, app_id, service_name, title, "desc", icon, type, url, default_url,
         is_admin, control, full_url, no_display, gateway_socket, gateway_prefix,
         file_types, i18n_matadata, created_at, updated_at
  FROM app_service
) t
"""
    env_sql = """
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY t.app_id, t.id), '[]'::json)
FROM (
  SELECT id, app_id, k, v
  FROM app_env
) t
"""
    apps = parse_json_output(run_sql(apps_sql), [])
    return {
        "apps": apps,
        "services": parse_json_output(run_sql(services_sql), []),
        "env": parse_json_output(run_sql(env_sql), []),
        "runAs": {str(app.get("id")): read_run_as(app) for app in apps},
    }


def column_map(columns):
    return {name: kind for name, kind in columns}


def update_app(payload):
    app = payload.get("app")
    if not isinstance(app, dict) or not app.get("id"):
        raise RuntimeError("missing app")
    allowed = {
        name: kind
        for name, kind in column_map(APP_COLUMNS).items()
        if name not in APP_READONLY_COLUMNS
    }
    sets = []
    for name, value in app.items():
        if name in allowed:
            sets.append(f"{quote_ident(name)}={value_sql(value, allowed[name])}")
    if sets:
        sets.append("updated_at=now()")
        run_sql(f"UPDATE app SET {', '.join(sets)} WHERE id={int(app['id'])}")


def save_child(table, columns, item, app_id):
    allowed = column_map(columns)
    values = {key: item.get(key) for key in allowed if key in item}
    if item.get("_delete") and item.get("id"):
        run_sql(
            f"DELETE FROM {table} WHERE id={int(item['id'])} AND app_id={int(app_id)}"
        )
        return
    if item.get("id"):
        sets = [
            f"{quote_ident(name)}={value_sql(value, allowed[name])}"
            for name, value in values.items()
        ]
        if table == "app_service":
            sets.append("updated_at=now()")
        if sets:
            run_sql(
                f"UPDATE {table} SET {', '.join(sets)} "
                f"WHERE id={int(item['id'])} AND app_id={int(app_id)}"
            )
        return
    if not values:
        return
    names = ["app_id"] + list(values.keys())
    sql_values = [str(int(app_id))] + [
        value_sql(value, allowed[name]) for name, value in values.items()
    ]
    if table == "app_service":
        names.extend(["created_at", "updated_at"])
        sql_values.extend(["now()", "now()"])
    sql_names = ", ".join(quote_ident(name) for name in names)
    run_sql(f"INSERT INTO {table} ({sql_names}) VALUES ({', '.join(sql_values)})")


def save_data(payload):
    app = payload.get("app")
    if not isinstance(app, dict) or not app.get("id"):
        raise RuntimeError("missing app")
    app_id = int(app["id"])
    update_app(payload)
    if "runAs" in payload:
        write_run_as(app_id, payload.get("runAs"))
    for service in payload.get("services") or []:
        if isinstance(service, dict):
            save_child("app_service", SERVICE_COLUMNS, service, app_id)
    for env in payload.get("env") or []:
        if isinstance(env, dict):
            save_child("app_env", ENV_COLUMNS, env, app_id)
    restart_info = restart_app_after_save(app_id) if payload.get("restart") else []
    data = list_data()
    data["restartInfo"] = restart_info
    return data


def dispatch():
    payload = request_body()
    action = payload.get("action", "list")
    if action == "list":
        json_response({"ok": True, **list_data()})
    elif action == "icon":
        serve_app_icon()
    elif action == "save":
        json_response({"ok": True, **save_data(payload)})
    else:
        json_response({"ok": False, "message": "unsupported action"}, "400 Bad Request")


def main():
    parser = argparse.ArgumentParser(description="fn-appsettings Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-appsettings")
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
