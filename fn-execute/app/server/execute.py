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
import shlex
import socketserver
import subprocess
import sys
import threading
import urllib.parse
import uuid
from contextlib import contextmanager
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


_APP_NAME = _env("TRIM_APPNAME", "fn-execute")

REQUEST_CONTEXT = threading.local()

EXEC_TASKS = {}
EXEC_TASKS_LOCK = threading.Lock()


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
        if str(key).lower() == lowered:
            return value
    return ""


def run_script(task_id, file_path, args_str, cwd_str):
    with EXEC_TASKS_LOCK:
        task = EXEC_TASKS.get(task_id)
        if not task:
            return
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()

    target = Path(file_path)
    ext = target.suffix.lower()

    if ext == ".py":
        cmd = [sys.executable or "python3", str(target)]
    elif ext == ".sh":
        cmd = ["/bin/bash", str(target)]
    else:
        if os.access(str(target), os.X_OK):
            cmd = [str(target)]
        else:
            cmd = ["/bin/bash", str(target)]

    if args_str:
        try:
            cmd.extend(shlex.split(args_str))
        except ValueError:
            cmd.append(args_str)

    cwd = cwd_str if cwd_str else str(target.parent)

    # Build a clean child environment: keep TERM/LANG for predictable output,
    # drop the platform bearer token so it never leaks into executed scripts.
    env = dict(os.environ)
    env.pop("TRIM_API_TOKEN", None)
    env["TERM"] = "dumb"
    env["LANG"] = "C.UTF-8"

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        with EXEC_TASKS_LOCK:
            if task_id in EXEC_TASKS:
                EXEC_TASKS[task_id]["proc"] = proc

        def _read_stream(stream, key):
            try:
                for raw_line in iter(stream.readline, b""):
                    line = raw_line.decode("utf-8", errors="replace")
                    with EXEC_TASKS_LOCK:
                        if task_id in EXEC_TASKS:
                            EXEC_TASKS[task_id][key] += line
            except Exception:
                pass
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        t_out = threading.Thread(
            target=_read_stream, args=(proc.stdout, "stdout"), daemon=True
        )
        t_err = threading.Thread(
            target=_read_stream, args=(proc.stderr, "stderr"), daemon=True
        )
        t_out.start()
        t_err.start()

        proc.wait(timeout=300)
        t_out.join(timeout=5)
        t_err.join(timeout=5)

        exit_code = proc.returncode

        with EXEC_TASKS_LOCK:
            if task_id in EXEC_TASKS:
                EXEC_TASKS[task_id]["status"] = "done"
                EXEC_TASKS[task_id]["exit_code"] = exit_code
                EXEC_TASKS[task_id]["finished_at"] = datetime.now().isoformat()
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            proc.wait(timeout=5)
        with EXEC_TASKS_LOCK:
            if task_id in EXEC_TASKS:
                EXEC_TASKS[task_id]["status"] = "timeout"
                EXEC_TASKS[task_id]["exit_code"] = -1
                EXEC_TASKS[task_id]["stderr"] += "\n[Process killed after 300s timeout]"
                EXEC_TASKS[task_id]["finished_at"] = datetime.now().isoformat()
    except Exception as exc:
        with EXEC_TASKS_LOCK:
            if task_id in EXEC_TASKS:
                EXEC_TASKS[task_id]["status"] = "error"
                EXEC_TASKS[task_id]["exit_code"] = -1
                EXEC_TASKS[task_id]["stderr"] += str(exc)
                EXEC_TASKS[task_id]["finished_at"] = datetime.now().isoformat()


class ThreadingUnixHTTPServer(
    socketserver.ThreadingMixIn,
    socketserver.UnixStreamServer,  # pyright: ignore[reportAttributeAccessIssue]
):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path, handler_cls, *, base_path, www_root):
        self.server_name = _APP_NAME
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
        if path == "/api":
            self.serve_api(parsed.query)
            return
        self.serve_static(path)

    def serve_api(self, query):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        headers = {key: value for key, value in self.headers.items()}
        with request_context(
            self.command, query=query, headers=headers, body=body, handler=self
        ):
            try:
                dispatch()
            except Exception as exc:  # noqa: BLE001
                json_response(
                    {"ok": False, "message": str(exc)}, "500 Internal Server Error"
                )

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
        size = target.stat().st_size

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header(
            "Cache-Control",
            "no-store" if target.name == "index.html" else "public, max-age=60",
        )
        self.end_headers()
        if self.command != "HEAD":
            with target.open("rb") as handle:
                while True:
                    chunk = handle.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)


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
            # client disconnected mid-response; treat as normal, don't crash thread
            return
        return
    sys.stdout.write(f"Status: {status_text}\r\n")
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(body)


def request_body():
    request = current_request()
    if request:
        method = request.get("method", "GET").upper()
        body = request.get("body", b"") or b""
        query_string = request.get("query", "") or ""
        content_type = header_value(request.get("headers", {}), "Content-Type")
        if method in {"POST", "PUT", "PATCH"}:
            raw = body.decode("utf-8", "replace") if body else ""
            if "application/json" in content_type:
                try:
                    return json.loads(raw or "{}")
                except Exception:
                    return {}
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
            try:
                return json.loads(raw or "{}")
            except Exception:
                return {}
        parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}
    parsed = urllib.parse.parse_qs(
        os.environ.get("QUERY_STRING", ""), keep_blank_values=True
    )
    return {key: values[-1] for key, values in parsed.items()}


def read_file_action(body):
    file_path = str(body.get("path") or "").strip()
    if not file_path:
        raise ValueError("Missing path parameter")
    if not file_path.startswith("/"):
        raise ValueError("Path must be absolute")

    target_path = Path(file_path)
    if not target_path.exists():
        raise FileNotFoundError("File not found: " + file_path)

    if target_path.is_dir():
        entries = []
        for child in sorted(target_path.iterdir(), key=lambda p: p.name.lower()):
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "type": "directory" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                }
            )
        return {"path": file_path, "type": "directory", "entries": entries}

    mime_type = mimetypes.guess_type(str(target_path))[0] or "application/octet-stream"
    info = {
        "path": file_path,
        "type": "file",
        "mime_type": mime_type,
        "size": target_path.stat().st_size,
        "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat(),
    }
    preview = None
    if mime_type.startswith("text/") or target_path.suffix.lower() in {
        ".json",
        ".py",
        ".sh",
        ".md",
        ".txt",
        ".xml",
        ".css",
        ".js",
        ".log",
    }:
        try:
            with target_path.open("rb") as handle:
                raw = handle.read(16384)
            preview_text = raw.decode("utf-8", errors="replace")
            preview = (
                preview_text
                if len(raw) < 16384
                else preview_text + "\n\n...preview truncated..."
            )
        except Exception as exc:  # noqa: BLE001
            preview = "Unable to read file: {0}".format(exc)
    info["preview"] = preview
    return info


def execute_action(body):
    file_path = str(body.get("path") or "").strip()
    args_str = str(body.get("args") or "")
    cwd_str = str(body.get("cwd") or "").strip()
    if not file_path:
        raise ValueError("Missing path parameter")
    if not file_path.startswith("/"):
        raise ValueError("Path must be absolute")

    target_path = Path(file_path)
    if not target_path.exists():
        raise FileNotFoundError("File not found: " + file_path)
    if target_path.is_dir():
        raise ValueError("Cannot execute a directory")

    task_id = uuid.uuid4().hex[:12]
    task = {
        "id": task_id,
        "file_path": file_path,
        "args": args_str,
        "cwd": cwd_str or str(target_path.parent),
        "status": "pending",
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "proc": None,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
    }

    with EXEC_TASKS_LOCK:
        EXEC_TASKS[task_id] = task

    t = threading.Thread(
        target=run_script, args=(task_id, file_path, args_str, cwd_str), daemon=True
    )
    t.start()

    return {"task_id": task_id, "status": "pending"}


def _task_payload(task):
    return {
        "id": task["id"],
        "file_path": task["file_path"],
        "args": task["args"],
        "status": task["status"],
        "exit_code": task["exit_code"],
        "stdout": task["stdout"],
        "stderr": task["stderr"],
        "created_at": task["created_at"],
        "started_at": task["started_at"],
        "finished_at": task["finished_at"],
    }


def read_task_action(body):
    task_id = str(body.get("task_id") or "").strip()
    with EXEC_TASKS_LOCK:
        task = EXEC_TASKS.get(task_id)
        if not task:
            raise KeyError("Task not found")
        payload = _task_payload(task)
    return payload


def stop_task_action(body):
    task_id = str(body.get("task_id") or "").strip()
    with EXEC_TASKS_LOCK:
        task = EXEC_TASKS.get(task_id)
        if not task:
            raise KeyError("Task not found")
        if task["status"] == "running":
            proc = task.get("proc")
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:  # noqa: BLE001
                    try:
                        proc.kill()
                    except Exception:  # noqa: BLE001
                        pass
            task["status"] = "killed"
            task["exit_code"] = -9
            task["stderr"] += "\n[Process killed by user]"
            task["finished_at"] = datetime.now().isoformat()
        payload = _task_payload(task)
    return payload


def dispatch():
    payload = request_body()
    action = str(payload.get("action") or "").strip()
    if action == "read_file":
        json_response({"ok": True, **read_file_action(payload)})
    elif action == "execute":
        json_response({"ok": True, **execute_action(payload)})
    elif action == "read_task":
        json_response({"ok": True, **read_task_action(payload)})
    elif action == "stop_task":
        json_response({"ok": True, **stop_task_action(payload)})
    elif action == "ping":
        json_response({"ok": True, "status": "ok"})
    elif not action:
        json_response({"ok": False, "message": "missing action"}, "400 Bad Request")
    else:
        json_response(
            {"ok": False, "message": "unsupported action: " + action}, "400 Bad Request"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="fn-execute minimal HTTP gateway")
    parser.add_argument("--socket", required=True, help="Unix socket path")
    parser.add_argument("--base-path", default="/", help="Base path to serve")
    parser.add_argument("--www-root", required=True, help="Static root directory")
    return parser.parse_args()


def main():
    args = parse_args()
    socket_path = os.path.abspath(args.socket)
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
        except OSError:
            pass

    httpd = ThreadingUnixHTTPServer(
        socket_path, Handler, base_path=args.base_path, www_root=args.www_root
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            httpd.server_close()
        except Exception:
            pass
        if os.path.exists(socket_path):
            os.remove(socket_path)


if __name__ == "__main__":
    main()
