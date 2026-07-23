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
import socket
import socketserver
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


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


EXEC_TASKS = {}
EXEC_TASKS_LOCK = threading.Lock()


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
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env={**os.environ, "TERM": "dumb"},
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
        self.server_name = "fn-execute"
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
            self.serve_api(path, parsed.query)
            return
        self.serve_static(path)

    def serve_api(self, path, query):
        if path == "/api/file":
            self.serve_api_file(query)
            return
        if path == "/api/execute":
            self.serve_api_execute(query)
            return
        if path.startswith("/api/task/"):
            self.serve_api_task(path)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def serve_api_file(self, query):
        params = parse_qs(query, keep_blank_values=True)
        raw_path = params.get("path", [""])[0]
        file_path = unquote(raw_path or "").strip()
        if not file_path:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing path parameter"})
            return

        if not file_path.startswith("/"):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Path must be absolute"})
            return

        target_path = Path(file_path)
        if not target_path.exists():
            self.send_json(
                HTTPStatus.NOT_FOUND, {"error": "File not found", "path": file_path}
            )
            return

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
            self.send_json(
                HTTPStatus.OK,
                {
                    "path": file_path,
                    "type": "directory",
                    "entries": entries,
                },
            )
            return

        mime_type = (
            mimetypes.guess_type(str(target_path))[0] or "application/octet-stream"
        )
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
            except Exception as exc:
                preview = f"Unable to read file: {exc}"
        elif mime_type.startswith("image/"):
            preview = None

        info["preview"] = preview
        self.send_json(HTTPStatus.OK, info)

    def serve_api_execute(self, query):
        params = parse_qs(query, keep_blank_values=True)
        raw_path = params.get("path", [""])[0]
        file_path = unquote(raw_path or "").strip()
        args_str = unquote(params.get("args", [""])[0])
        cwd_str = unquote(params.get("cwd", [""])[0])

        if not file_path:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing path parameter"})
            return

        if not file_path.startswith("/"):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Path must be absolute"})
            return

        target_path = Path(file_path)
        if not target_path.exists():
            self.send_json(
                HTTPStatus.NOT_FOUND, {"error": "File not found", "path": file_path}
            )
            return

        if target_path.is_dir():
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Cannot execute a directory"}
            )
            return

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

        self.send_json(HTTPStatus.OK, {"task_id": task_id, "status": "pending"})

    def serve_api_task(self, path):
        parts = path.split("/")
        if len(parts) < 4:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid task URL"})
            return

        task_id = parts[3]
        action = parts[4] if len(parts) > 4 else None

        with EXEC_TASKS_LOCK:
            task = EXEC_TASKS.get(task_id)
            if not task:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Task not found"})
                return

            if action == "stop" and task["status"] == "running":
                proc = task.get("proc")
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                task["status"] = "killed"
                task["exit_code"] = -9
                task["stderr"] += "\n[Process killed by user]"
                task["finished_at"] = datetime.now().isoformat()

            resp = {
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

        self.send_json(HTTPStatus.OK, resp)

    def send_json(self, status, data):
        response_text = json.dumps(data, ensure_ascii=False)
        response_bytes = response_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response_bytes)

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
