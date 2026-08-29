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
import pty
import re
import select
import signal
import socketserver
import stat
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-WParted")
# 运行时数据目录：优先用 TRIM_PKGVAR，回退到 /var/apps/<app>/var
_pkgvar = _env("TRIM_PKGVAR")
VAR_DIR = Path(_pkgvar) if _pkgvar else Path(f"/var/apps/{APP_NAME}/var")
VAR_DIR.mkdir(parents=True, exist_ok=True)
OPERATIONS_FILE = VAR_DIR / "operations.json"
REQUEST_CONTEXT = threading.local()
_lock = threading.Lock()

REQUIRED_TOOLS = {
    "lsblk": "util-linux",
    "parted": "parted",
    "fdisk": "fdisk",
    "mkfs.ext4": "e2fsprogs",
    "mkfs.xfs": "xfsprogs",
    "mkfs.btrfs": "btrfs-progs",
    "mkfs.f2fs": "f2fs-tools",
    "mkfs.ntfs": "ntfs-3g",
    "mkfs.fat": "dosfstools",
    "mkfs.exfat": "exfatprogs",
    "mkswap": "util-linux",
    "zpool": "openzfs-zfsutils",
    "blkid": "util-linux",
    "wipefs": "util-linux",
    "mount": "util-linux",
    "umount": "util-linux",
    "smartctl": "smartmontools",
    "e2fsck": "e2fsprogs",
    "resize2fs": "e2fsprogs",
}


def check_tools():
    available = {}
    missing = {}
    for tool, package in REQUIRED_TOOLS.items():
        found = False
        for item in os.environ.get("PATH", "/usr/sbin:/usr/bin:/sbin:/bin").split(":"):
            candidate = Path(item) / tool
            if candidate.exists() and os.access(candidate, os.X_OK):
                found = True
                break
        if found:
            available[tool] = True
        else:
            missing[tool] = package
    return available, missing


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
        headers = dict(self.headers.items())
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
    if base_path != "/" and path.startswith(base_path):
        return path[len(base_path) :] or "/"
    return path or "/"


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
            return
        return
    sys.stdout.write(f"Status: {status_text}\r\n")
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(body)


def request_body():
    request = current_request()
    body = request.get("body", b"")
    if not body:
        return {}
    return json.loads(body.decode("utf-8", "replace") or "{}")


def run(cmd, timeout=30, stdin_data=None):
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            input=stdin_data,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(cmd),
            "rc": 124,
            "stdout": (exc.stdout or "").strip(),
            "stderr": (
                (exc.stderr or "").strip() or f"Command timed out after {timeout}s"
            ),
        }
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def run_interactive(cmd, timeout=30, confirm="Yes\n"):
    master_fd, slave_fd = pty.openpty()  # pyright: ignore[reportAttributeAccessIssue]
    try:
        proc = subprocess.Popen(
            cmd, stdin=slave_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    finally:
        os.close(slave_fd)
    confirmed = False
    deadline = time.monotonic() + timeout
    stdout_data = b""
    stderr_data = b""
    while True:
        if proc.poll() is not None:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            proc.kill()
            break
        fds = [fd for fd in (proc.stdout, proc.stderr) if fd]
        if not fds:
            break
        try:
            r, _, _ = select.select(fds, [], [], min(remaining, 1.0))
        except (OSError, ValueError):
            break
        for fd in r:
            try:
                chunk = os.read(fd.fileno(), 4096)
                if not chunk:
                    continue
                if fd == proc.stderr:
                    stderr_data += chunk
                else:
                    stdout_data += chunk
            except OSError:
                continue
        if not confirmed and confirm:
            combined = (stderr_data + stdout_data).lower()
            if (
                b"continue?" in combined
                or b"acceptable to you?" in combined
                or b"are you sure" in combined
                or b"is this still acceptable" in combined
            ):
                try:
                    os.write(master_fd, confirm.encode())
                except OSError:
                    pass
                confirmed = True
    proc.wait()
    for fd in (proc.stdout, proc.stderr):
        if fd:
            try:
                while True:
                    chunk = os.read(fd.fileno(), 4096)
                    if not chunk:
                        break
                    if fd == proc.stderr:
                        stderr_data += chunk
                    else:
                        stdout_data += chunk
            except OSError:
                pass
    try:
        os.close(master_fd)
    except OSError:
        pass
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout": stdout_data.decode("utf-8", "replace").strip(),
        "stderr": stderr_data.decode("utf-8", "replace").strip(),
    }


def _safe_dev_path(name):
    if not name:
        return False
    if not name.startswith("/dev/"):
        return False
    if not re.match(r"^/dev/[A-Za-z0-9_./-]+$", name):
        return False
    # 拒绝路径穿越（..）与相对段（.），防止 /dev/../../etc 之类的逃逸
    return all(seg not in (".", "..") for seg in name.split("/"))


def safe_dev_name(name):
    return _safe_dev_path(name)


def safe_part_name(name):
    return _safe_dev_path(name)


def safe_fs_type(fs):
    return bool(fs and re.match(r"^[A-Za-z0-9_+-]+$", fs))


def safe_mount_point(mp):
    if not mp:
        return True
    if not mp.startswith("/") or not re.match(r"^/[A-Za-z0-9_./ -]*$", mp):
        return False
    # 拒绝路径穿越（..）与相对段（.）
    return all(seg not in (".", "..") for seg in mp.split("/"))


def safe_label(label):
    if not label:
        return True
    return bool(re.match(r"^[A-Za-z0-9_ .-]{0,128}$", label))


def human_size(sector_size, sectors):
    if not sectors or int(sectors) <= 0:
        return "0 B"
    total = int(sectors) * int(sector_size)
    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if abs(total) < 1024.0:
            return f"{total:.1f} {unit}"
        total /= 1024.0
    return f"{total:.1f} EiB"


LSBLK_WANTED_COLUMNS = [
    "NAME",
    "SIZE",
    "TYPE",
    "FSTYPE",
    "MOUNTPOINT",
    "MOUNTPOINTS",
    "LABEL",
    "UUID",
    "MODEL",
    "VENDOR",
    "ROTA",
    "LOG-SEC",
    "PTTYPE",
    "PARTFLAGS",
    "STATE",
    "OWNER",
    "GROUP",
    "MAJ:MIN",
    "PARTN",
    "PARTTYPE",
    "PARTUUID",
    "PARTLABEL",
]

_lsblk_supported_columns = None


def _probe_lsblk_columns():
    global _lsblk_supported_columns
    if _lsblk_supported_columns is not None:
        return _lsblk_supported_columns
    base_cols = [
        c
        for c in LSBLK_WANTED_COLUMNS
        if c not in ("PARTN", "PARTTYPE", "PARTUUID", "PARTLABEL")
    ]
    result = run(
        ["lsblk", "--json", "--bytes", "--output", ",".join(base_cols)], timeout=15
    )
    if result["rc"] != 0:
        _lsblk_supported_columns = [
            "NAME",
            "SIZE",
            "TYPE",
            "FSTYPE",
            "MOUNTPOINT",
            "LABEL",
            "UUID",
            "MODEL",
            "ROTA",
            "LOG-SEC",
            "PTTYPE",
            "MAJ:MIN",
        ]
        return _lsblk_supported_columns
    available = list(base_cols)
    for col in ("PARTN", "PARTTYPE", "PARTUUID", "PARTLABEL"):
        test_cols = available + [col]
        r = run(
            ["lsblk", "--json", "--bytes", "--output", ",".join(test_cols)], timeout=10
        )
        if r["rc"] == 0:
            available.append(col)
    _lsblk_supported_columns = available
    return available


def _build_lsblk_columns_str():
    available = _probe_lsblk_columns()
    return ",".join(available)


def _lsblk_has_part_columns():
    available = _probe_lsblk_columns()
    return any(c in available for c in ("PARTN", "PARTTYPE", "PARTUUID", "PARTLABEL"))


def _blkid_partinfo():
    info = {}
    result = run(["blkid", "-o", "export"], timeout=15)
    if result["rc"] != 0:
        return info
    dev = None
    for line in result["stdout"].splitlines():
        if not line:
            dev = None
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.lower()
        if key == "devname":
            dev = val
            info[dev] = {}
        elif dev and key in ("partn", "parttype", "partuuid", "partlabel"):
            info[dev][key] = val
    return info


def parse_lsblk():
    columns_str = _build_lsblk_columns_str()
    result = run(["lsblk", "--json", "--bytes", "--output", columns_str], timeout=15)
    if result["rc"] != 0:
        raise RuntimeError(f"lsblk failed: {result['stderr'] or result['stdout']}")
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse lsblk output")
    if not _lsblk_has_part_columns():
        blkid_info = _blkid_partinfo()
        if blkid_info:
            for bd in data.get("blockdevices", []):
                dev = (
                    f"/dev/{bd['name']}"
                    if not bd.get("name", "").startswith("/dev/")
                    else bd["name"]
                )
                extra = blkid_info.get(dev, {})
                for k, v in extra.items():
                    bd.setdefault(k, v)
                for child in bd.get("children", []) or []:
                    cdev = (
                        f"/dev/{child['name']}"
                        if not child.get("name", "").startswith("/dev/")
                        else child["name"]
                    )
                    cextra = blkid_info.get(cdev, {})
                    for k, v in cextra.items():
                        child.setdefault(k, v)
                    for sub in child.get("children", []) or []:
                        sdev = (
                            f"/dev/{sub['name']}"
                            if not sub.get("name", "").startswith("/dev/")
                            else sub["name"]
                        )
                        sextra = blkid_info.get(sdev, {})
                        for k, v in sextra.items():
                            sub.setdefault(k, v)
    return data


def build_device_tree(lsblk_data):
    devices = []
    blockdevices = lsblk_data.get("blockdevices", [])
    for bd in blockdevices:
        device = parse_block_device(bd)
        device["partitions"] = []
        children = bd.get("children", []) or []
        for child in children:
            part = parse_block_device(child)
            part["partitions"] = []
            sub_children = child.get("children", []) or []
            for sub in sub_children:
                part["partitions"].append(parse_block_device(sub))
            device["partitions"].append(part)
        devices.append(device)
    return devices


def parse_block_device(bd):
    name = bd.get("name", "")
    size_bytes = bd.get("size", 0)
    size_num = int(size_bytes) if size_bytes else 0
    log_sec = bd.get("log-sec", 512)
    sectors = size_num // int(log_sec) if int(log_sec) > 0 else 0
    mountpoints = bd.get("mountpoints", [])
    if not mountpoints:
        mp = bd.get("mountpoint", "")
        mountpoints = [mp] if mp else []
    mountpoints = [m for m in mountpoints if m]
    return {
        "name": name,
        "path": f"/dev/{name}" if not name.startswith("/dev/") else name,
        "size": size_num,
        "sizeHuman": human_size(1, size_num),
        "sectors": sectors,
        "sectorSize": int(log_sec),
        "type": bd.get("type", ""),
        "fstype": bd.get("fstype", "") or "",
        "mountpoint": mountpoints[0] if mountpoints else "",
        "mountpoints": mountpoints,
        "label": bd.get("label", "") or "",
        "uuid": bd.get("uuid", "") or "",
        "model": bd.get("model", "") or "",
        "vendor": bd.get("vendor", "") or "",
        "rota": bd.get("rota", None),
        "pttype": bd.get("pttype", "") or "",
        "partflags": bd.get("partflags", "") or "",
        "state": bd.get("state", "") or "",
        "owner": bd.get("owner", "") or "",
        "group": bd.get("group", "") or "",
        "partn": bd.get("partn", None),
        "parttype": bd.get("parttype", "") or "",
        "partuuid": bd.get("partuuid", "") or "",
        "partlabel": bd.get("partlabel", "") or "",
    }


def get_partition_table(device_path):
    if not safe_dev_name(device_path):
        raise RuntimeError("Invalid device name")
    result = run(["fdisk", "-l", device_path], timeout=15)
    if result["rc"] != 0:
        raise RuntimeError(f"fdisk failed: {result['stderr']}")
    return result["stdout"]


def get_smart_info(device_path):
    if not safe_dev_name(device_path):
        raise RuntimeError("Invalid device name")
    result = run(["smartctl", "-a", device_path], timeout=30)
    return result["stdout"] if result["rc"] == 0 else ""


def get_detailed_partitions(device_path):
    if not safe_dev_name(device_path):
        raise RuntimeError("Invalid device name")
    result = run(
        ["parted", "-m", device_path, "unit", "MiB", "print", "free"], timeout=15
    )
    if result["rc"] != 0:
        raise RuntimeError(f"parted failed: {result['stderr']}")
    lines = result["stdout"].strip().splitlines()
    partitions = []
    free_spaces = []
    header_found = False
    disk_header_skipped = False
    for line in lines:
        if line.startswith("BYT;"):
            header_found = True
            continue
        if not header_found:
            continue
        if not disk_header_skipped:
            disk_header_skipped = True
            continue
        parts = line.split(":")
        if len(parts) < 5:
            continue
        fstype_field = parts[4].strip().rstrip(";") if len(parts) > 4 else ""
        if fstype_field == "free":
            free_spaces.append(
                {
                    "startMiB": (
                        parts[1].strip().rstrip("MiB")
                        if "MiB" in parts[1]
                        else parts[1].strip()
                    ),
                    "endMiB": (
                        parts[2].strip().rstrip("MiB")
                        if "MiB" in parts[2]
                        else parts[2].strip()
                    ),
                    "sizeMiB": (
                        parts[3].strip().rstrip("MiB")
                        if "MiB" in parts[3]
                        else parts[3].strip()
                    ),
                    "type": "free",
                }
            )
        else:
            part_info = {
                "number": parts[0].strip(),
                "startMiB": (
                    parts[1].strip().rstrip("MiB")
                    if "MiB" in parts[1]
                    else parts[1].strip()
                ),
                "endMiB": (
                    parts[2].strip().rstrip("MiB")
                    if "MiB" in parts[2]
                    else parts[2].strip()
                ),
                "sizeMiB": (
                    parts[3].strip().rstrip("MiB")
                    if "MiB" in parts[3]
                    else parts[3].strip()
                ),
                "fstype": fstype_field,
                "name": parts[5].strip() if len(parts) > 5 else "",
                "flags": parts[6].strip().rstrip(";") if len(parts) > 6 else "",
                "type": "partition",
            }
            partitions.append(part_info)
    return {"partitions": partitions, "freeSpaces": free_spaces}


def load_operations():
    try:
        if OPERATIONS_FILE.exists():
            return json.loads(OPERATIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"pending": [], "applied": []}


def save_operations(data):
    OPERATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    OPERATIONS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def api_disks(payload):
    lsblk_data = parse_lsblk()
    devices = build_device_tree(lsblk_data)
    json_response({"ok": True, "devices": devices})


def api_disk_detail(payload):
    body = payload
    device_path = body.get("device", "")
    if not safe_dev_name(device_path):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    fdisk_output = get_partition_table(device_path)
    parted_info = get_detailed_partitions(device_path)
    smart_output = get_smart_info(device_path)
    json_response(
        {
            "ok": True,
            "device": device_path,
            "fdisk": fdisk_output,
            "parted": parted_info,
            "smart": smart_output,
        }
    )


def _find_new_partition(device, start_mib, before_count=None):
    result = run(["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,START"], timeout=15)
    if result["rc"] != 0:
        return None
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        return None
    dev_name = device.split("/")[-1]
    for bd in data.get("blockdevices", []):
        if bd.get("name") != dev_name:
            continue
        for child in bd.get("children", []) or []:
            name = child.get("name", "")
            start = child.get("start", 0)
            if start and abs(int(start) / (1024 * 1024) - float(start_mib)) < 2:
                return f"/dev/{name}" if not name.startswith("/dev/") else name
        break
    # Fallback: only trust the last child if the partition count actually grew,
    # so we never mistake a pre-existing partition for the newly created one.
    if before_count is None:
        return None
    result2 = run(["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE"], timeout=15)
    if result2["rc"] != 0:
        return None
    try:
        data2 = json.loads(result2["stdout"] or "{}")
    except json.JSONDecodeError:
        return None
    for bd in data2.get("blockdevices", []):
        if bd.get("name") != dev_name:
            continue
        children = bd.get("children", []) or []
        if len(children) > before_count and children:
            last = children[-1]
            name = last.get("name", "")
            return f"/dev/{name}" if not name.startswith("/dev/") else name
        break
    return None


def _do_format(partition: str, fs_type: str, label: str = ""):
    fs_type = {"linux-swap": "swap"}.get(fs_type, fs_type)
    ready_error = _wait_for_partition(partition)
    if ready_error:
        return {"cmd": "", "rc": 1, "stdout": "", "stderr": ready_error}

    unmount_error = _unmount_partition(partition)
    if unmount_error:
        return {"cmd": "", "rc": 1, "stdout": "", "stderr": unmount_error}

    # mkfs can overwrite old signatures itself, but clearing them first avoids
    # stale RAID/LVM/FS probes racing with the formatter after a reformat.
    wipe_result = run(["wipefs", "-a", "-f", partition], timeout=30)
    if wipe_result["rc"] != 0:
        return wipe_result
    run(["udevadm", "settle", "--timeout=10"], timeout=15)
    fs_cmds = {
        "ext2": ["mkfs.ext2", "-F", "-E", "nodiscard"],
        "ext3": ["mkfs.ext3", "-F", "-E", "nodiscard"],
        "ext4": ["mkfs.ext4", "-F", "-E", "nodiscard"],
        "xfs": ["mkfs.xfs", "-f"],
        "zfs": ["zpool", "create", "-f"],
        "btrfs": ["mkfs.btrfs", "-f"],
        "f2fs": ["mkfs.f2fs", "-f"],
        "ntfs": ["mkfs.ntfs", "-f", "-Q"],
        "fat16": ["mkfs.fat", "-F", "16"],
        "fat32": ["mkfs.fat", "-F", "32"],
        "exfat": ["mkfs.exfat"],
        "swap": ["mkswap"],
    }
    cmd_base = fs_cmds.get(fs_type)
    if not cmd_base:
        return
    if fs_type == "zfs":
        pool_name = (
            label if label else "zpool_" + partition.split("/")[-1].replace(" ", "")
        )
        cmd = cmd_base + [pool_name, partition]
    else:
        cmd = list(cmd_base)
        if label and fs_type != "swap" and fs_type in _LABEL_FLAGS:
            lbl = label[: _LABEL_MAX.get(fs_type, 128)]
            cmd += [_LABEL_FLAGS[fs_type], lbl]
        cmd.append(partition)
    # USB/SATA devices may still be claimed briefly by udev after wipefs.  A
    # short, bounded retry is safer than formatting via a loop device, which
    # does not solve real block-device ownership and can mask the cause.
    result = run(cmd, timeout=300)
    if result["rc"] != 0 and _is_device_busy_error(result["stderr"]):
        run(["udevadm", "settle", "--timeout=10"], timeout=15)
        time.sleep(1)
        result = run(cmd, timeout=300)
    if result["rc"] == 0:
        os.sync()  # pyright: ignore[reportAttributeAccessIssue]
        run(["udevadm", "settle", "--timeout=10"], timeout=15)
    return result


def _wait_for_partition(partition, retries=5):
    """Wait for udev to publish a real partition block node."""
    for _ in range(retries):
        try:
            if stat.S_ISBLK(os.stat(partition).st_mode):
                kind = run(["lsblk", "-dn", "-o", "TYPE", partition], timeout=10)
                if kind["rc"] == 0 and kind["stdout"].strip() == "part":
                    return ""
        except OSError:
            pass
        run(["udevadm", "settle", "--timeout=5"], timeout=10)
        time.sleep(1)
    return f"Partition device is not ready: {partition}"


def _unmount_partition(partition):
    # Only disable swap if the partition is actually an active swap device.
    # swapoff on a non-swap partition fails with EINVAL ("Invalid argument"),
    # which is expected and must not block formatting.
    swaps = run(["swapon", "--show=NAME", "--noheadings"], timeout=15)
    if swaps["rc"] == 0:
        active_swaps = {
            line.strip() for line in swaps["stdout"].splitlines() if line.strip()
        }
        if partition in active_swaps:
            swap_result = run(["swapoff", partition], timeout=30)
            if swap_result["rc"] != 0:
                return (
                    swap_result["stderr"]
                    or swap_result["stdout"]
                    or "Failed to disable swap"
                )

    mounts = run(["findmnt", "-rn", "-S", partition, "-o", "TARGET"], timeout=15)
    if mounts["rc"] not in (0, 1):
        return mounts["stderr"] or "Failed to inspect partition mounts"
    targets = sorted(
        (line.strip() for line in mounts["stdout"].splitlines() if line.strip()),
        key=len,
        reverse=True,
    )
    for target in targets:
        result = run(["umount", target], timeout=30)
        if result["rc"] != 0:
            return result["stderr"] or result["stdout"] or f"Failed to unmount {target}"
    verify = run(["findmnt", "-rn", "-S", partition], timeout=15)
    if verify["rc"] == 0 and verify["stdout"].strip():
        return f"Partition is still mounted: {verify['stdout'].splitlines()[0]}"
    return ""


def _partition_path(device, part_number):
    if device.startswith(("/dev/nvme", "/dev/mmcblk", "/dev/loop")):
        return f"{device}p{part_number}"
    return f"{device}{part_number}"


def _unmount_device(device):
    """Unmount/swapoff every partition under a whole disk before destructive ops."""
    result = run(["lsblk", "-rno", "NAME,TYPE", device], timeout=15)
    if result["rc"] != 0:
        return result["stderr"] or "Failed to list device partitions"
    errors = []
    for line in result["stdout"].splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[1] != "part":
            continue
        name = fields[0]
        part = f"/dev/{name}" if not name.startswith("/dev/") else name
        err = _unmount_partition(part)
        if err:
            errors.append(f"{part}: {err}")
    return "; ".join(errors) if errors else ""


def _count_partitions(device):
    result = run(["lsblk", "-J", "-b", "-o", "NAME,TYPE"], timeout=15)
    if result["rc"] != 0:
        return None
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        return None
    dev_name = device.split("/")[-1]
    for bd in data.get("blockdevices", []):
        if bd.get("name") == dev_name:
            return len(bd.get("children", []) or [])
    return None


def api_partition_create(payload):
    body = payload
    device = body.get("device", "")
    start_mib = body.get("startMiB")
    end_mib = body.get("endMiB")
    fs_type = body.get("fstype", "ext4")
    part_type = body.get("partType", "primary")
    label = body.get("label", "")
    if not safe_dev_name(device):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    if start_mib is None or end_mib is None:
        json_response(
            {"ok": False, "message": "startMiB and endMiB are required"},
            "400 Bad Request",
        )
        return
    if float(start_mib) < 1:
        start_mib = 1
    if float(end_mib) <= float(start_mib):
        json_response(
            {"ok": False, "message": "endMiB must be greater than startMiB"},
            "400 Bad Request",
        )
        return
    if not safe_fs_type(fs_type):
        json_response(
            {"ok": False, "message": "Invalid filesystem type"}, "400 Bad Request"
        )
        return
    # The server is threaded.  Serialize destructive block operations so a
    # refresh or a second browser tab cannot interleave parted/mkfs calls.
    if not _lock.acquire(blocking=False):
        json_response(
            {"ok": False, "message": "Another disk operation is in progress"},
            "409 Conflict",
        )
        return
    try:
        before_count = _count_partitions(device)
        disk_info = run(["parted", "-m", device, "unit", "MiB", "print"], timeout=15)
        if disk_info["rc"] == 0:
            for line in disk_info["stdout"].splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[0] == device:
                    try:
                        disk_end = float(parts[1].rstrip("MiB"))
                        if float(end_mib) >= disk_end:
                            end_mib = disk_end - 1
                    except (ValueError, IndexError):
                        pass
                    break
        cmd = [
            "parted",
            device,
            "mkpart",
            part_type,
            fs_type,
            f"{start_mib}MiB",
            f"{end_mib}MiB",
        ]
        result = run_interactive(cmd, timeout=60)
        if result["rc"] != 0:
            json_response(
                {
                    "ok": False,
                    "message": f"Failed to create partition: {result['stderr']}",
                },
                "500 Internal Server Error",
            )
            return
        run(["partprobe", device], timeout=10)
        run(["udevadm", "settle", "--timeout=5"], timeout=10)
        new_part = _find_new_partition(device, start_mib, before_count)
        if new_part and fs_type and fs_type != "unformatted":
            format_result = _do_format(new_part, fs_type, label)
            if format_result is None or format_result["rc"] != 0:
                detail = (
                    format_result["stderr"] or format_result["stdout"]
                    if format_result
                    else "Unknown error"
                )
                json_response(
                    {
                        "ok": False,
                        "message": f"Partition was created but formatting failed: {detail}",
                    },
                    "500 Internal Server Error",
                )
                return
        elif fs_type and fs_type != "unformatted":
            json_response(
                {
                    "ok": False,
                    "message": "Partition was created but its device is not ready",
                },
                "500 Internal Server Error",
            )
            return
        if label:
            part_num = body.get("partNumber")
            if part_num:
                run(["parted", "-s", device, "name", str(part_num), label], timeout=30)
        ops = load_operations()
        ops["pending"].append(
            {
                "action": "create",
                "device": device,
                "startMiB": start_mib,
                "endMiB": end_mib,
                "fstype": fs_type,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_operations(ops)
        json_response({"ok": True, "message": "Partition created successfully"})
    finally:
        _lock.release()


def api_partition_delete(payload):
    body = payload
    device = body.get("device", "")
    part_number = body.get("partNumber")
    if not safe_dev_name(device):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    if part_number is None:
        json_response(
            {"ok": False, "message": "partNumber is required"}, "400 Bad Request"
        )
        return
    part_path = _partition_path(device, part_number)
    pool_guard = _pool_guard(part_path)
    if pool_guard:
        json_response({"ok": False, "message": pool_guard}, "400 Bad Request")
        return
    if not _lock.acquire(blocking=False):
        json_response(
            {"ok": False, "message": "Another disk operation is in progress"},
            "409 Conflict",
        )
        return
    try:
        unmount_error = _unmount_partition(_partition_path(device, part_number))
        if unmount_error:
            json_response(
                {
                    "ok": False,
                    "message": f"Failed to unmount partition: {unmount_error}",
                },
                "500 Internal Server Error",
            )
            return
        cmd = ["parted", device, "rm", str(part_number)]
        result = run_interactive(cmd, timeout=60)
        if result["rc"] != 0:
            json_response(
                {
                    "ok": False,
                    "message": f"Failed to delete partition: {result['stderr']}",
                },
                "500 Internal Server Error",
            )
            return
        run(["partprobe", device], timeout=10)
        run(["udevadm", "settle", "--timeout=5"], timeout=10)
        ops = load_operations()
        ops["pending"].append(
            {
                "action": "delete",
                "device": device,
                "partNumber": part_number,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_operations(ops)
        json_response({"ok": True, "message": "Partition deleted successfully"})
    finally:
        _lock.release()


def api_partition_resize(payload):
    body = payload
    device = body.get("device", "")
    part_number = body.get("partNumber")
    start_mib = body.get("startMiB")
    end_mib = body.get("endMiB")
    if not safe_dev_name(device):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    if part_number is None or end_mib is None:
        json_response(
            {"ok": False, "message": "partNumber and endMiB are required"},
            "400 Bad Request",
        )
        return
    # parted resizepart only accepts an END position; it cannot move the
    # partition start.  Reject start changes instead of building a malformed
    # command (moving the start requires delete + recreate).
    if start_mib is not None:
        json_response(
            {"ok": False, "message": "Moving the partition start is not supported"},
            "400 Bad Request",
        )
        return
    cmd = ["parted", device, "resizepart", str(part_number), f"{end_mib}MiB"]
    result = run_interactive(cmd, timeout=120)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to resize partition: {result['stderr']}"},
            "500 Internal Server Error",
        )
        return
    run(["partprobe", device], timeout=10)
    run(["udevadm", "settle", "--timeout=5"], timeout=10)
    ops = load_operations()
    ops["pending"].append(
        {
            "action": "resize",
            "device": device,
            "partNumber": part_number,
            "endMiB": end_mib,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    save_operations(ops)
    json_response({"ok": True, "message": "Partition resized successfully"})


def _is_device_busy_error(stderr):
    lower = stderr.lower()
    return any(
        k in lower
        for k in (
            "in use by the system",
            "device or resource busy",
            "will not make a filesystem",
        )
    )


_LABEL_FLAGS = {
    "ext2": "-L",
    "ext3": "-L",
    "ext4": "-L",
    "xfs": "-L",
    "btrfs": "-L",
    "f2fs": "-l",
    "ntfs": "-L",
    "fat16": "-n",
    "fat32": "-n",
    "exfat": "-n",
}

_LABEL_MAX = {"fat16": 11, "fat32": 11}


def api_partition_format(payload):
    body = payload
    partition = body.get("partition", "")
    fs_type = body.get("fstype", "ext4")
    label = body.get("label", "")
    if not safe_part_name(partition):
        json_response(
            {"ok": False, "message": "Invalid partition name"}, "400 Bad Request"
        )
        return
    if not safe_fs_type(fs_type):
        json_response(
            {"ok": False, "message": "Invalid filesystem type"}, "400 Bad Request"
        )
        return
    if not safe_label(label):
        json_response({"ok": False, "message": "Invalid label"}, "400 Bad Request")
        return
    pool_guard = _pool_guard(partition)
    if pool_guard:
        json_response({"ok": False, "message": pool_guard}, "400 Bad Request")
        return
    if not os.path.exists(partition):
        device = partition.rstrip("0123456789")
        if (
            partition.startswith("/dev/nvme")
            or partition.startswith("/dev/mmcblk")
            or partition.startswith("/dev/loop")
        ):
            import re as _re

            m = _re.match(r"(/dev/(?:nvme\d+n\d+|mmcblk\d+p|loop\d+p))\d+", partition)
            if m:
                device = m.group(1)
        run(["partprobe", device], timeout=10)
        run(["udevadm", "settle", "--timeout=5"], timeout=10)
        time.sleep(2)
    # The server is threaded.  Serialize destructive block operations so a
    # refresh or a second browser tab cannot interleave wipefs/mkfs calls.
    if not _lock.acquire(blocking=False):
        json_response(
            {"ok": False, "message": "Another disk operation is in progress"},
            "409 Conflict",
        )
        return
    try:
        result = _do_format(partition, fs_type, label)
    finally:
        _lock.release()
    if result is None or result["rc"] != 0:
        msg = result["stderr"] if result else "Unknown error"
        json_response(
            {"ok": False, "message": f"Failed to format partition: {msg}"},
            "500 Internal Server Error",
        )
        return
    ops = load_operations()
    ops["pending"].append(
        {
            "action": "format",
            "partition": partition,
            "fstype": fs_type,
            "label": label,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    save_operations(ops)
    json_response(
        {"ok": True, "message": f"Partition formatted as {fs_type} successfully"}
    )


def api_partition_set_flag(payload):
    body = payload
    device = body.get("device", "")
    part_number = body.get("partNumber")
    flag = body.get("flag", "")
    state = body.get("state", True)
    if not safe_dev_name(device):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    if part_number is None or not flag:
        json_response(
            {"ok": False, "message": "partNumber and flag are required"},
            "400 Bad Request",
        )
        return
    if not re.match(r"^[a-z][a-z0-9-]*$", flag):
        json_response({"ok": False, "message": "Invalid flag name"}, "400 Bad Request")
        return
    state_str = "on" if state else "off"
    cmd = ["parted", "-s", device, "set", str(part_number), flag, state_str]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to set flag: {result['stderr']}"},
            "500 Internal Server Error",
        )
        return
    json_response({"ok": True, "message": f"Flag {flag} set to {state_str}"})


def api_partition_mount(payload):
    body = payload
    partition = body.get("partition", "")
    mount_point = body.get("mountPoint", "")
    if not safe_part_name(partition):
        json_response(
            {"ok": False, "message": "Invalid partition name"}, "400 Bad Request"
        )
        return
    if not safe_mount_point(mount_point):
        json_response(
            {"ok": False, "message": "Invalid mount point"}, "400 Bad Request"
        )
        return
    if not mount_point:
        json_response(
            {"ok": False, "message": "mountPoint is required"}, "400 Bad Request"
        )
        return
    mounted = run(["findmnt", "-rn", "-S", partition, "-o", "TARGET"], timeout=15)
    if mounted["rc"] == 0 and mounted["stdout"].strip():
        json_response(
            {
                "ok": False,
                "message": f"Partition is already mounted at {mounted['stdout'].strip().splitlines()[0]}",
            },
            "400 Bad Request",
        )
        return
    Path(mount_point).mkdir(parents=True, exist_ok=True)
    cmd = ["mount", partition, mount_point]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to mount: {result['stderr']}"},
            "500 Internal Server Error",
        )
        return
    json_response({"ok": True, "message": f"Mounted {partition} at {mount_point}"})


def api_partition_umount(payload):
    body = payload
    target = body.get("target", "")
    if not target:
        json_response(
            {"ok": False, "message": "target (partition or mount point) is required"},
            "400 Bad Request",
        )
        return
    if not (safe_part_name(target) or safe_mount_point(target)):
        json_response({"ok": False, "message": "Invalid target"}, "400 Bad Request")
        return
    cmd = ["umount", target]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to unmount: {result['stderr']}"},
            "500 Internal Server Error",
        )
        return
    json_response({"ok": True, "message": f"Unmounted {target}"})


def api_disk_wipe(payload):
    body = payload
    device = body.get("device", "")
    method = body.get("method", "quick")
    if not safe_dev_name(device):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    pool_guard = _pool_guard(device)
    if pool_guard:
        json_response({"ok": False, "message": pool_guard}, "400 Bad Request")
        return
    if not _lock.acquire(blocking=False):
        json_response(
            {"ok": False, "message": "Another disk operation is in progress"},
            "409 Conflict",
        )
        return
    try:
        unmount_error = _unmount_device(device)
        if unmount_error:
            json_response(
                {"ok": False, "message": f"Failed to unmount device: {unmount_error}"},
                "500 Internal Server Error",
            )
            return
        if method == "zero":
            cmd = ["dd", "if=/dev/zero", f"of={device}", "bs=1M", "count=1"]
            result = run(cmd, timeout=60)
            if result["rc"] != 0:
                json_response(
                    {"ok": False, "message": f"Failed to wipe: {result['stderr']}"},
                    "500 Internal Server Error",
                )
                return
        cmd = ["wipefs", "-a", device]
        result = run(cmd, timeout=30)
        if result["rc"] != 0:
            json_response(
                {
                    "ok": False,
                    "message": f"Failed to wipe signatures: {result['stderr']}",
                },
                "500 Internal Server Error",
            )
            return
        json_response({"ok": True, "message": f"Device {device} wiped successfully"})
    finally:
        _lock.release()


def api_disk_label(payload):
    body = payload
    device = body.get("device", "")
    label_type = body.get("labelType", "gpt")
    if not safe_dev_name(device):
        json_response(
            {"ok": False, "message": "Invalid device name"}, "400 Bad Request"
        )
        return
    if label_type not in ("gpt", "msdos", "mbr"):
        json_response({"ok": False, "message": "Invalid label type"}, "400 Bad Request")
        return
    pool_guard = _pool_guard(device)
    if pool_guard:
        json_response({"ok": False, "message": pool_guard}, "400 Bad Request")
        return
    unmount_error = _unmount_device(device)
    if unmount_error:
        json_response(
            {"ok": False, "message": f"Failed to unmount device: {unmount_error}"},
            "500 Internal Server Error",
        )
        return
    cmd = ["parted", device, "mklabel", label_type]
    result = run_interactive(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {
                "ok": False,
                "message": f"Failed to create partition table: {result['stderr']}",
            },
            "500 Internal Server Error",
        )
        return
    json_response(
        {"ok": True, "message": f"Partition table {label_type} created on {device}"}
    )


def api_partition_check(payload):
    body = payload
    partition = body.get("partition", "")
    if not safe_part_name(partition):
        json_response(
            {"ok": False, "message": "Invalid partition name"}, "400 Bad Request"
        )
        return
    fstype = body.get("fstype", "")
    if not fstype:
        blkid_result = run(
            ["blkid", "-o", "value", "-s", "TYPE", partition], timeout=10
        )
        if blkid_result["rc"] == 0 and blkid_result["stdout"].strip():
            fstype = blkid_result["stdout"].strip().splitlines()[0]
    if fstype in ("ext2", "ext3", "ext4"):
        cmd = ["e2fsck", "-f", "-n", partition]
    elif fstype == "xfs":
        cmd = ["xfs_repair", "-n", partition]
    elif fstype == "btrfs":
        cmd = ["btrfs", "check", "--readonly", partition]
    elif fstype == "ntfs":
        cmd = ["ntfsfix", partition]
    elif fstype == "f2fs":
        cmd = ["fsck.f2fs", partition]
    elif fstype == "fat16" or fstype == "fat32":
        cmd = ["fsck.fat", "-n", partition]
    elif fstype == "exfat":
        cmd = ["exfatfsck", partition]
    elif fstype == "zfs":
        cmd = ["zpool", "scrub", partition]
    else:
        cmd = ["fsck", "-n", partition]
    result = run(cmd, timeout=120)
    json_response(
        {
            "ok": True,
            "partition": partition,
            "fstype": fstype,
            "rc": result["rc"],
            "output": result["stdout"],
            "errors": result["stderr"],
        }
    )


def api_partition_info(payload):
    body = payload
    partition = body.get("partition", "")
    if not safe_part_name(partition):
        json_response(
            {"ok": False, "message": "Invalid partition name"}, "400 Bad Request"
        )
        return
    blkid_result = run(["blkid", "-o", "export", partition], timeout=10)
    df_result = run(["df", "-h", partition], timeout=10)
    json_response(
        {
            "ok": True,
            "partition": partition,
            "blkid": blkid_result["stdout"],
            "df": df_result["stdout"],
        }
    )


def api_fs_resize(payload):
    body = payload
    partition = body.get("partition", "")
    fstype = body.get("fstype", "")
    mount_point = body.get("mountPoint", "")
    if not safe_part_name(partition):
        json_response(
            {"ok": False, "message": "Invalid partition name"}, "400 Bad Request"
        )
        return
    if not safe_fs_type(fstype):
        json_response(
            {"ok": False, "message": "Invalid filesystem type"}, "400 Bad Request"
        )
        return
    if fstype in ("ext2", "ext3", "ext4"):
        cmd = ["resize2fs", partition]
    elif fstype == "xfs":
        if not mount_point:
            json_response(
                {"ok": False, "message": "XFS resize requires mount point"},
                "400 Bad Request",
            )
            return
        cmd = ["xfs_growfs", mount_point]
    elif fstype == "btrfs":
        if not mount_point:
            json_response(
                {"ok": False, "message": "Btrfs resize requires mount point"},
                "400 Bad Request",
            )
            return
        cmd = ["btrfs", "filesystem", "resize", "max", mount_point]
    elif fstype == "ntfs":
        cmd = ["ntfsresize", "-f", partition]
    else:
        json_response(
            {"ok": False, "message": f"Unsupported filesystem for resize: {fstype}"},
            "400 Bad Request",
        )
        return
    result = run(cmd, timeout=120)
    if result["rc"] != 0:
        json_response(
            {
                "ok": False,
                "message": f"Failed to resize filesystem: {result['stderr']}",
            },
            "500 Internal Server Error",
        )
        return
    json_response({"ok": True, "message": f"Filesystem {fstype} resized successfully"})


def api_operations(payload):
    ops = load_operations()
    json_response({"ok": True, "operations": ops})


def api_operations_clear(payload):
    save_operations({"pending": [], "applied": []})
    json_response({"ok": True, "message": "Operations cleared"})


def api_check_tools(payload):
    available, missing = check_tools()
    json_response({"ok": True, "available": available, "missing": missing})


def _zfs_pools():
    """盘点 ZFS 存储池（支持跨盘/RAID 拓扑）。"""
    result = run(
        ["zpool", "list", "-Hp", "-o", "name,size,allocated,free,health"], timeout=20
    )
    if result["rc"] != 0:
        return []
    pools = {}
    for line in result["stdout"].splitlines():
        fields = line.split()
        if len(fields) < 5:
            continue
        pools[fields[0]] = {
            "name": fields[0],
            "source": "zfs",
            "type": "zpool",
            "size": int(fields[1]),
            "allocated": int(fields[2]),
            "free": int(fields[3]),
            "health": fields[4],
            "members": [],
        }
    status = run(["zpool", "status", "-P"], timeout=25)
    if status["rc"] == 0:
        cur_name = None
        vdev_type = ""
        in_config = False
        for line in status["stdout"].splitlines():
            stripped = line.strip()
            if stripped.startswith("pool:"):
                cur_name = (
                    stripped.split(None, 1)[1]
                    if len(stripped.split(None, 1)) > 1
                    else ""
                )
                in_config = False
                vdev_type = ""
                continue
            if stripped == "config:":
                in_config = True
                continue
            if not in_config or not cur_name:
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                continue
            if indent <= 2:
                # 顶层 vdev：可能为 raidz1-0 / mirror-0 等
                if "raidz" in stripped or "mirror" in stripped:
                    vdev_type = stripped.split()[0]
                elif cur_name in pools and not vdev_type:
                    vdev_type = stripped.split()[0]
                continue
            # 成员盘（多为缩进 4 或更深）
            toks = stripped.split()
            member = toks[0] if toks else ""
            if member.startswith("/dev/") and cur_name in pools:
                pools[cur_name]["members"].append(member)
                if vdev_type and pools[cur_name]["type"] == "zpool":
                    pools[cur_name]["type"] = vdev_type
    return list(pools.values())


def _md_pools():
    """盘点 Linux MD RAID 阵列（/proc/mdstat）。"""
    result = run(["cat", "/proc/mdstat"], timeout=5)
    if result["rc"] != 0:
        return []
    pools = []
    lines = result["stdout"].splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        m = re.match(r"^(md\d+)\s*:\s*(\S+)\s+(\S+)\s+(.*)$", line)
        if not m:
            continue
        name, state, level, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        members = []
        for tok in rest.split():
            dm = re.match(r"^([A-Za-z0-9_./-]+)\[(\d+)\](?:\((\w+)\))?$", tok)
            if dm:
                members.append(dm.group(1))
        size = 0
        health = ""
        for j in range(i + 1, min(i + 4, len(lines))):
            blk = lines[j].strip()
            sm = re.search(r"^(\d+)\s+blocks", blk)
            if sm:
                size = int(sm.group(1)) * 1024
            sm2 = re.search(r"\[(\d+)/(\d+)\]", blk)
            if sm2:
                health = f"{sm2.group(1)}/{sm2.group(2)} disks active"
            if not blk:
                break
        pools.append(
            {
                "name": name,
                "source": "md",
                "type": level,
                "state": state,
                "size": size,
                "health": health,
                "members": members,
            }
        )
    return pools


def _btrfs_pools():
    """盘点 Btrfs 文件系统（可能含多盘/raid）。

    挂载中的 btrfs 会用挂载点（如 /vol1、/vol2）作为友好名称，并解析真实
    容量（df）。未挂载的池退回 uuid 作为名称。
    """
    result = run(["btrfs", "filesystem", "show"], timeout=25)
    if result["rc"] != 0:
        return []
    # uuid -> 挂载点（仅当前已挂载的 btrfs）
    mounts = {}
    mres = run(["findmnt", "-t", "btrfs", "-o", "TARGET,UUID", "-rn"], timeout=10)
    if mres["rc"] == 0:
        for line in mres["stdout"].splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                mounts[parts[1]] = parts[0]
    pools = []
    cur = None
    for line in result["stdout"].splitlines():
        s = line.rstrip()
        if s.startswith("Label:") or s.startswith("label:"):
            if cur is not None:
                pools.append(cur)
            tok = s.split("uuid:")
            uuid = tok[1].split()[0] if len(tok) > 1 else ""
            multi = "multiple devices" in s
            cur = {
                "name": uuid,
                "source": "btrfs",
                "type": "multi-device" if multi else "single",
                "uuid": uuid,
                "members": [],
                "size": 0,
                "allocated": None,
                "free": None,
                "health": "",
            }
        elif cur is not None and (" path " in s or s.strip().startswith("/dev/")):
            toks = s.strip().split()
            if "path" in toks:
                idx = toks.index("path")
                if idx + 1 < len(toks):
                    cur["members"].append(toks[idx + 1])
            else:
                cur["members"].append(toks[0])
    if cur is not None:
        pools.append(cur)
    # 用挂载点名称 + df 容量丰富每个池
    for pool in pools:
        mp = mounts.get(pool["uuid"])
        if mp:
            pool["mountpoint"] = mp
            pool["name"] = mp  # 显示 /vol1、/vol2，而非字符串 UUID
        df_target = mp if mp else (pool["members"][0] if pool["members"] else "")
        if not df_target:
            continue
        dres = run(["df", "-B1", "-P", df_target], timeout=20)
        lines = dres["stdout"].splitlines() if dres["rc"] == 0 else []
        for ln in lines[1:]:
            fields = ln.split()
            if len(fields) >= 4 and fields[1].isdigit():
                pool["size"] = int(fields[1])
                pool["allocated"] = int(fields[2])
                pool["free"] = int(fields[3])
                break
    return pools


def storage_pools():
    """返回全部存储池/RAID 盘点结果。"""
    return _zfs_pools() + _md_pools() + _btrfs_pools()


def _lsblk_tree():
    """返回 lsblk 树（含 children），供构造池的顶层链路。"""
    result = run(["lsblk", "-J", "-o", "NAME"], timeout=15)
    if result["rc"] != 0:
        return []
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        return []
    return data.get("blockdevices", [])


def _name_chain_map():
    """lsblk 节点名 -> 从根到该节点的完整链路（示例：['nvme0n1','nvme0n1p3','md0']）。"""
    mapping = {}

    def walk(nodes, parents):
        for node in nodes:
            name = node.get("name")
            if not name:
                continue
            chain = parents + [name]
            mapping[name] = chain
            walk(node.get("children") or [], chain)

    walk(_lsblk_tree(), [])
    return mapping


def _attach_pool_topo(pools):
    """给存储池附加 topo 字段（物理分区 → RAID/LVM → 文件系统 → 挂载点）。

    仅用于 API 展示,不参与危险操作保护（pool_membership_lookup 不走这里）。
    """
    chains = _name_chain_map()
    for pool in pools:
        source = pool.get("source")
        if source == "md":
            chain = chains.get(pool.get("name"))
            if chain:
                pool["topo"] = list(chain)
        elif source == "btrfs":
            base = ""
            for member in pool.get("members", []):
                if member.startswith("/dev/mapper/"):
                    base = member.split("/")[-1]
                    break
            chain = list(chains.get(base, [])) if base else []
            if pool.get("mountpoint"):
                chain.append(pool["mountpoint"])
            pool["topo"] = chain
    return pools


def _merge_pools(pools):
    """把承载了 Btrfs 的 md 阵列并入对应存储空间，避免 md 与 /vol 重复成行。

    合并后仅显示存储空间条目（如 /vol1 或 /vol2），其 RAID/md 结构作为
    `raid` 字段内嵌在条目的链路中。没有任何上层文件系统的裸 md 阵列仍保留。
    """
    md_by_name = {}
    for pool in pools:
        if pool.get("source") == "md":
            md_by_name[pool["name"]] = pool
    absorbed = set()
    for pool in pools:
        if pool.get("source") != "btrfs":
            continue
        for node in pool.get("topo", []):
            if isinstance(node, str) and node in md_by_name:
                md = md_by_name[node]
                pool["raid"] = {
                    "name": md["name"],
                    "level": md["type"],
                    "health": md["health"],
                }
                absorbed.add(node)
                break
    return [p for p in pools if not (p.get("source") == "md" and p["name"] in absorbed)]


def _pool_member_dev_base(name):
    """返回设备名去掉分区后缀后的盘基名（sda1->sda, nvme0n1p3->nvme0n1）。"""
    # 带 p+数字 结尾（nvme/mmcblk/loop 分区）或裸数字结尾（sdX1）视作分区
    if re.search(r"p\d+$", name):
        return name[: name.rfind("p")]
    if re.match(r"^(nvme|mmcblk|loop|dm-)", name):
        return name  # 盘名自带数字，非分区
    return name.rstrip("0123456789") if name[-1:].isdigit() else name


def pool_membership_lookup(device):
    """返回某 /dev/ 设备（整盘或分区）所属的池名列表，用于危险操作保护。"""
    membership = {}
    for pool in storage_pools():
        for member in pool.get("members", []):
            key = member.split("/")[-1].lower()
            membership.setdefault(key, []).append(pool["name"])
    basename = device.split("/")[-1].lower()
    base = _pool_member_dev_base(basename)
    hit = set()
    for key, names in membership.items():
        key_l = key.lower()
        if key_l == basename or _pool_member_dev_base(key_l) == base:
            # 整盘查询会命中其分区成员；分区查询命中自身/同盘成员
            hit.update(names)
    return sorted(hit)


def api_storage_pools(payload):
    pools = storage_pools()
    _attach_pool_topo(pools)
    pools = _merge_pools(pools)
    json_response({"ok": True, "pools": pools})


def _pool_guard(device):
    """若 device 属于存储池/RAID 成员，返回禁止信息；否则返回 ''。"""
    pools = pool_membership_lookup(device)
    if not pools:
        return ""
    return (
        f"{device} is a member of storage pool/RAID ({', '.join(pools)}). "
        f"Modifying it will break the array. Destroy the pool first."
    )


def dispatch():
    ensure_dirs()
    request = current_request()
    if request == {}:
        raise RuntimeError("no request context")
    # ★ 与前端共用同一 {action, ...data} 契约：action 一律从 body 读取（对齐 appdownload）。
    payload = request_body()
    action = str(payload.get("action") or "disks").strip()

    if action == "disks":
        api_disks(payload)
    elif action == "disk-detail":
        api_disk_detail(payload)
    elif action == "partition-create":
        api_partition_create(payload)
    elif action == "partition-delete":
        api_partition_delete(payload)
    elif action == "partition-resize":
        api_partition_resize(payload)
    elif action == "partition-format":
        api_partition_format(payload)
    elif action == "partition-set-flag":
        api_partition_set_flag(payload)
    elif action == "partition-mount":
        api_partition_mount(payload)
    elif action == "partition-umount":
        api_partition_umount(payload)
    elif action == "disk-wipe":
        api_disk_wipe(payload)
    elif action == "disk-label":
        api_disk_label(payload)
    elif action == "partition-check":
        api_partition_check(payload)
    elif action == "partition-info":
        api_partition_info(payload)
    elif action == "fs-resize":
        api_fs_resize(payload)
    elif action == "operations":
        api_operations(payload)
    elif action == "operations-clear":
        api_operations_clear(payload)
    elif action == "check-tools":
        api_check_tools(payload)
    elif action == "storage-pools":
        api_storage_pools(payload)
    else:
        json_response(
            {"ok": False, "message": f"Unknown action: {action}"}, "404 Not Found"
        )


def main():
    parser = argparse.ArgumentParser(description="WParted Web Backend")
    parser.add_argument("--unix-socket", required=True, help="Unix socket path")
    parser.add_argument("--base-path", default="/app/fn-WParted", help="Base URL path")
    parser.add_argument("--www-root", required=True, help="Static files directory")
    args = parser.parse_args()

    if os.path.exists(args.unix_socket):
        os.unlink(args.unix_socket)

    server = ThreadingUnixHTTPServer(
        args.unix_socket,
        Handler,
        base_path=args.base_path,
        www_root=args.www_root,
    )
    os.chmod(args.unix_socket, 0o666)

    def shutdown(_signum, _frame):
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"WParted backend listening on {args.unix_socket}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)


if __name__ == "__main__":
    main()
