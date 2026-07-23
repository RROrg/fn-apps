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
import socket
import socketserver
import subprocess
import sys
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit
from contextlib import contextmanager

APP_NAME = "fn-aptmng"

REQUEST_CONTEXT = threading.local()


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
                json_response({"ok": False, "message": str(exc)}, 500)


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


def json_response(payload, status=200):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    code = status if isinstance(status, int) else 200
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
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(body)


def request_body():
    request = current_request()
    if request != {}:
        method = request.get("method", "GET").upper()
        body = request.get("body", b"") or b""
        query_string = request.get("query", "") or ""
        if method in {"POST", "PUT", "PATCH"}:
            raw = body.decode("utf-8", "replace") if body else ""
            content_type = ""
            for key, value in request.get("headers", {}).items():
                if key.lower() == "content-type":
                    content_type = value
                    break
            if "application/json" in content_type:
                return json.loads(raw or "{}")
            parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
            return {key: values[-1] for key, values in parsed.items()}
        parsed = urllib.parse.parse_qs(query_string, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}
    return {}


def query_value(name, default=""):
    request = current_request()
    parsed = urllib.parse.parse_qs(request.get("query", ""), keep_blank_values=True)
    return (parsed.get(name) or [default])[-1]


def run_cmd(cmd, timeout=120):
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "command timed out"}
    except FileNotFoundError:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"command not found: {cmd[0]}",
        }


def parse_dpkg_list(output):
    packages = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            packages.append(
                {
                    "package": parts[0],
                    "version": parts[1],
                    "arch": parts[2],
                    "status": parts[3] if len(parts) > 3 else "unknown",
                    "description": parts[4] if len(parts) > 4 else "",
                }
            )
    return packages


def parse_apt_list(output):
    packages = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            packages.append(
                {
                    "package": parts[0],
                    "version": parts[1],
                }
            )
    return packages


def parse_show_output(output):
    info = {}
    current_key = None
    current_value = []
    for line in output.splitlines():
        if not line and current_key:
            info[current_key] = "\n".join(current_value).strip()
            current_key = None
            current_value = []
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)", line)
        if match:
            if current_key:
                info[current_key] = "\n".join(current_value).strip()
            current_key = match.group(1).lower()
            current_value = [match.group(2)]
        elif line.startswith(" ") and current_key:
            current_value.append(line.strip())
    if current_key:
        info[current_key] = "\n".join(current_value).strip()

    if not info.get("description"):
        for key in ("description-en", "description-en_us", "description-en-gb"):
            if info.get(key):
                info["description"] = info[key]
                break

    info.pop("description-md5", None)
    return info


def action_update():
    result = run_cmd(["apt-get", "update"])
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get update failed")
    return {"message": "apt source list updated", "output": result["stdout"]}


def action_list_installed():
    result = run_cmd(
        [
            "dpkg-query",
            "-W",
            "-f=${Package}\x1f${Version}\x1f${Architecture}\x1f${Status}\x1f${binary:Summary}\n",
        ]
    )
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "dpkg-query failed")
    packages = []
    for line in result["stdout"].splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\x1f")
        if len(parts) >= 3:
            packages.append(
                {
                    "package": parts[0],
                    "version": parts[1],
                    "arch": parts[2],
                    "status": parts[3] if len(parts) > 3 else "unknown",
                    "description": parts[4] if len(parts) > 4 else "",
                }
            )
    installed = [p for p in packages if "installed" in p.get("status", "").lower()]
    return {"packages": installed}


def action_list_upgradable():
    result = run_cmd(["apt", "list", "--upgradable", "-qq"])
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt list --upgradable failed")
    packages = []
    for line in result["stdout"].splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(
            r"^(\S+)/\S+\s+(\S+)\s+(\S+)\s+\[upgradable from:\s+(\S+)\]", line
        )
        if match:
            packages.append(
                {
                    "package": match.group(1),
                    "new_version": match.group(2),
                    "arch": match.group(3),
                    "old_version": match.group(4),
                }
            )
    return {"packages": packages}


def action_search(payload):
    keyword = payload.get("keyword", "").strip()
    if not keyword:
        raise RuntimeError("keyword is required")
    result = run_cmd(["apt-cache", "search", keyword])
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-cache search failed")
    packages = []
    for line in result["stdout"].splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" - ", 1)
        if len(parts) == 2:
            pkg_name = parts[0].strip()
            pkg_desc = parts[1].strip()
            packages.append({"package": pkg_name, "description": pkg_desc})
    return {"packages": packages}


def action_show(payload):
    package = payload.get("package", "").strip()
    if not package:
        raise RuntimeError("package name is required")
    result = run_cmd(["apt-cache", "show", package])
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-cache show failed")
    if not result["stdout"].strip():
        raise RuntimeError(f"package {package} not found")
    info = parse_show_output(result["stdout"])
    status_result = run_cmd(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Status}\n", package]
    )
    if status_result["returncode"] == 0 and status_result["stdout"].strip():
        parts = status_result["stdout"].strip().split("\t")
        if len(parts) >= 3:
            info["installed_version"] = parts[1]
            info["status"] = parts[2]
    return {"info": info}


def action_install(payload):
    package = payload.get("package", "").strip()
    if not package:
        raise RuntimeError("package name is required")
    result = run_cmd(["apt-get", "install", "-y", package], timeout=600)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get install failed")
    return {"message": f"package {package} installed", "output": result["stdout"]}


def action_remove(payload):
    package = payload.get("package", "").strip()
    if not package:
        raise RuntimeError("package name is required")
    purge = payload.get("purge", False)
    cmd = (
        ["apt-get", "purge", "-y", package]
        if purge
        else ["apt-get", "remove", "-y", package]
    )
    result = run_cmd(cmd, timeout=600)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get remove failed")
    return {"message": f"package {package} removed", "output": result["stdout"]}


def action_upgrade(payload):
    package = payload.get("package", "").strip()
    if package:
        result = run_cmd(
            ["apt-get", "install", "-y", "--only-upgrade", package], timeout=600
        )
    else:
        result = run_cmd(["apt-get", "upgrade", "-y"], timeout=600)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get upgrade failed")
    return {"message": "upgrade completed", "output": result["stdout"]}


def action_autoremove():
    result = run_cmd(["apt-get", "autoremove", "-y"], timeout=600)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get autoremove failed")
    return {"message": "autoremove completed", "output": result["stdout"]}


def action_clean():
    result = run_cmd(["apt-get", "clean"])
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get clean failed")
    return {"message": "cache cleaned", "output": result["stdout"]}


def action_fix_broken():
    result = run_cmd(["apt-get", "--fix-broken", "install", "-y"], timeout=600)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "apt-get --fix-broken install failed")
    return {"message": "broken dependencies fixed", "output": result["stdout"]}


def parse_source_line(line):
    parsed = {"type": "", "url": "", "suite": "", "components": "", "enabled": True}
    stripped = line.strip()
    if stripped.startswith("#"):
        stripped = stripped.lstrip("#").strip()
        parsed["enabled"] = False
    match = re.match(r"^(deb-src|deb)\s+(\S+)\s+(\S+)(?:\s+(.+))?$", stripped)
    if match:
        parsed["type"] = match.group(1)
        parsed["url"] = match.group(2)
        parsed["suite"] = match.group(3)
        parsed["components"] = match.group(4) or ""
    else:
        parsed["url"] = stripped
    return parsed


def action_sources():
    sources_list = Path("/etc/apt/sources.list")
    sources_d = Path("/etc/apt/sources.list.d")
    entries = []
    if sources_list.is_file():
        try:
            for line in sources_list.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines():
                stripped = line.strip()
                if (
                    not stripped
                    or stripped.startswith("#")
                    and not stripped.lstrip("#").strip()
                ):
                    continue
                if not stripped.lstrip("#").strip():
                    continue
                parsed = parse_source_line(stripped)
                if parsed["type"]:
                    entries.append(
                        {
                            "file": "/etc/apt/sources.list",
                            "line": stripped,
                            "type": parsed["type"],
                            "url": parsed["url"],
                            "suite": parsed["suite"],
                            "components": parsed["components"],
                            "enabled": parsed["enabled"],
                        }
                    )
        except Exception:
            pass
    if sources_d.is_dir():
        for f in sorted(sources_d.glob("*.list")):
            try:
                for line in f.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines():
                    stripped = line.strip()
                    if (
                        not stripped
                        or stripped.startswith("#")
                        and not stripped.lstrip("#").strip()
                    ):
                        continue
                    if not stripped.lstrip("#").strip():
                        continue
                    parsed = parse_source_line(stripped)
                    if parsed["type"]:
                        entries.append(
                            {
                                "file": str(f),
                                "line": stripped,
                                "type": parsed["type"],
                                "url": parsed["url"],
                                "suite": parsed["suite"],
                                "components": parsed["components"],
                                "enabled": parsed["enabled"],
                            }
                        )
            except Exception:
                pass
    return {"sources": entries}


def action_add_source(payload):
    source_line = payload.get("line", "").strip()
    filename = payload.get("file", "fn-aptmng.list").strip()
    if not source_line:
        raise RuntimeError("source line is required")
    if not filename.endswith(".list"):
        filename += ".list"
    target = Path("/etc/apt/sources.list.d") / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if target.is_file():
        existing = target.read_text(encoding="utf-8", errors="replace")
    if not existing.endswith("\n"):
        existing += "\n"
    existing += source_line + "\n"
    target.write_text(existing, encoding="utf-8")
    return {"message": f"source added to {target}"}


def action_remove_source(payload):
    source_line = payload.get("line", "").strip()
    filename = payload.get("file", "fn-aptmng.list").strip()
    if not filename.endswith(".list"):
        filename += ".list"
    target = Path("/etc/apt/sources.list.d") / filename
    if not target.is_file():
        raise RuntimeError(f"source file {target} not found")
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    new_lines = [l for l in lines if l.strip() != source_line]
    target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"message": f"source removed from {target}"}


def action_toggle_source(payload):
    source_line = payload.get("line", "").strip()
    source_file = payload.get("file", "").strip()
    target = Path(source_file)
    if not target.is_file():
        raise RuntimeError(f"source file {target} not found")
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if (
            stripped == source_line
            or stripped.lstrip("#").strip() == source_line.lstrip("#").strip()
        ):
            found = True
            if stripped.startswith("#"):
                new_lines.append(stripped.lstrip("#").strip())
            else:
                new_lines.append("# " + stripped)
        else:
            new_lines.append(line)
    if not found:
        raise RuntimeError("source line not found in file")
    target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"message": "source toggled"}


def action_delete_source_file(payload):
    filename = payload.get("file", "").strip()
    if not filename:
        raise RuntimeError("file name is required")
    target = Path("/etc/apt/sources.list.d") / filename
    if not target.is_file():
        raise RuntimeError(f"source file {target} not found")
    target.unlink()
    return {"message": f"source file {filename} deleted"}


def action_health():
    return {"ok": True, "message": "fn-aptmng is running"}


def dispatch():
    payload = request_body()
    action = payload.get("action", "health")
    if action == "health":
        json_response({"ok": True, **action_health()})
    elif action == "update":
        json_response({"ok": True, **action_update()})
    elif action == "list_installed":
        json_response({"ok": True, **action_list_installed()})
    elif action == "list_upgradable":
        json_response({"ok": True, **action_list_upgradable()})
    elif action == "search":
        json_response({"ok": True, **action_search(payload)})
    elif action == "show":
        json_response({"ok": True, **action_show(payload)})
    elif action == "install":
        json_response({"ok": True, **action_install(payload)})
    elif action == "remove":
        json_response({"ok": True, **action_remove(payload)})
    elif action == "upgrade":
        json_response({"ok": True, **action_upgrade(payload)})
    elif action == "autoremove":
        json_response({"ok": True, **action_autoremove()})
    elif action == "clean":
        json_response({"ok": True, **action_clean()})
    elif action == "fix_broken":
        json_response({"ok": True, **action_fix_broken()})
    elif action == "sources":
        json_response({"ok": True, **action_sources()})
    elif action == "add_source":
        json_response({"ok": True, **action_add_source(payload)})
    elif action == "remove_source":
        json_response({"ok": True, **action_remove_source(payload)})
    elif action == "toggle_source":
        json_response({"ok": True, **action_toggle_source(payload)})
    elif action == "delete_source_file":
        json_response({"ok": True, **action_delete_source_file(payload)})
    else:
        json_response({"ok": False, "message": f"unsupported action: {action}"}, 400)


def main():
    parser = argparse.ArgumentParser(description="fn-aptmng Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-aptmng")
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
