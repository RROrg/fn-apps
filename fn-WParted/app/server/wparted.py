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
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit

APP_NAME = "fn-WParted"
STATE_DIR = Path("/var/lib/fn-WParted")
STATE_DIR.mkdir(parents=True, exist_ok=True)
OPERATIONS_FILE = STATE_DIR / "operations.json"
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
        previous = getattr(REQUEST_CONTEXT, "value", None)
        REQUEST_CONTEXT.value = {
            "method": self.command,
            "query": query or "",
            "body": body,
            "handler": self,
        }
        try:
            dispatch()
        except Exception as exc:
            json_response({"ok": False, "message": str(exc)}, 500)
        finally:
            if previous is None:
                del REQUEST_CONTEXT.value
            else:
                REQUEST_CONTEXT.value = previous


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


def json_response(payload, status=200):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    request = current_request()
    handler = request.get("handler", None)
    if handler is not None:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        if handler.command != "HEAD":
            handler.wfile.write(body)
        return


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


def safe_dev_name(name):
    return bool(name and re.match(r"^/dev/[A-Za-z0-9_./-]+$", name))


def safe_part_name(name):
    return bool(name and re.match(r"^/dev/[A-Za-z0-9_./-]+$", name))


def safe_fs_type(fs):
    return bool(fs and re.match(r"^[A-Za-z0-9_+-]+$", fs))


def safe_mount_point(mp):
    if not mp:
        return True
    return bool(re.match(r"^/[A-Za-z0-9_./ -]*$", mp))


def safe_label(label):
    if not label:
        return True
    return bool(re.match(r"^[A-Za-z0-9_ .-]{0,128}$", label))


def safe_uuid(u):
    if not u:
        return True
    return bool(re.match(r"^[A-Za-z0-9-]+$", u))


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


def api_disks():
    lsblk_data = parse_lsblk()
    devices = build_device_tree(lsblk_data)
    json_response({"ok": True, "devices": devices})


def api_disk_detail():
    body = request_body()
    device_path = body.get("device", "")
    if not safe_dev_name(device_path):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
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


def _find_new_partition(device, start_mib):
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
        if children:
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
    swap_result = run(["swapoff", partition], timeout=30)
    if swap_result["rc"] != 0 and "not found" not in swap_result["stderr"].lower():
        return (
            swap_result["stderr"] or swap_result["stdout"] or "Failed to disable swap"
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


def api_partition_create():
    body = request_body()
    device = body.get("device", "")
    start_mib = body.get("startMiB")
    end_mib = body.get("endMiB")
    fs_type = body.get("fstype", "ext4")
    part_type = body.get("partType", "primary")
    label = body.get("label", "")
    if not safe_dev_name(device):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
        return
    if start_mib is None or end_mib is None:
        json_response({"ok": False, "message": "startMiB and endMiB are required"}, 400)
        return
    if float(start_mib) < 1:
        start_mib = 1
    if float(end_mib) <= float(start_mib):
        json_response(
            {"ok": False, "message": "endMiB must be greater than startMiB"}, 400
        )
        return
    if not safe_fs_type(fs_type):
        json_response({"ok": False, "message": "Invalid filesystem type"}, 400)
        return
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
            {"ok": False, "message": f"Failed to create partition: {result['stderr']}"},
            500,
        )
        return
    run(["partprobe", device], timeout=10)
    run(["udevadm", "settle", "--timeout=5"], timeout=10)
    new_part = _find_new_partition(device, start_mib)
    if new_part and fs_type and fs_type != "unformatted":
        with _lock:
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
                500,
            )
            return
    elif fs_type and fs_type != "unformatted":
        json_response(
            {
                "ok": False,
                "message": "Partition was created but its device is not ready",
            },
            500,
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


def api_partition_delete():
    body = request_body()
    device = body.get("device", "")
    part_number = body.get("partNumber")
    if not safe_dev_name(device):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
        return
    if part_number is None:
        json_response({"ok": False, "message": "partNumber is required"}, 400)
        return
    cmd = ["parted", device, "rm", str(part_number)]
    result = run_interactive(cmd, timeout=60)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to delete partition: {result['stderr']}"},
            500,
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


def api_partition_resize():
    body = request_body()
    device = body.get("device", "")
    part_number = body.get("partNumber")
    start_mib = body.get("startMiB")
    end_mib = body.get("endMiB")
    if not safe_dev_name(device):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
        return
    if part_number is None or end_mib is None:
        json_response(
            {"ok": False, "message": "partNumber and endMiB are required"}, 400
        )
        return
    if start_mib is not None:
        cmd = [
            "parted",
            device,
            "resizepart",
            str(part_number),
            f"{start_mib}MiB",
            f"{end_mib}MiB",
        ]
    else:
        cmd = ["parted", device, "resizepart", str(part_number), f"{end_mib}MiB"]
    result = run_interactive(cmd, timeout=120)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to resize partition: {result['stderr']}"},
            500,
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


def api_partition_format():
    body = request_body()
    partition = body.get("partition", "")
    fs_type = body.get("fstype", "ext4")
    label = body.get("label", "")
    if not safe_part_name(partition):
        json_response({"ok": False, "message": "Invalid partition name"}, 400)
        return
    if not safe_fs_type(fs_type):
        json_response({"ok": False, "message": "Invalid filesystem type"}, 400)
        return
    if not safe_label(label):
        json_response({"ok": False, "message": "Invalid label"}, 400)
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
            {"ok": False, "message": "Another disk operation is in progress"}, 409
        )
        return
    try:
        result = _do_format(partition, fs_type, label)
    finally:
        _lock.release()
    if result is None or result["rc"] != 0:
        msg = result["stderr"] if result else "Unknown error"
        json_response(
            {"ok": False, "message": f"Failed to format partition: {msg}"}, 500
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


def api_partition_set_flag():
    body = request_body()
    device = body.get("device", "")
    part_number = body.get("partNumber")
    flag = body.get("flag", "")
    state = body.get("state", True)
    if not safe_dev_name(device):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
        return
    if part_number is None or not flag:
        json_response({"ok": False, "message": "partNumber and flag are required"}, 400)
        return
    if not re.match(r"^[a-z][a-z0-9-]*$", flag):
        json_response({"ok": False, "message": "Invalid flag name"}, 400)
        return
    state_str = "on" if state else "off"
    cmd = ["parted", "-s", device, "set", str(part_number), flag, state_str]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to set flag: {result['stderr']}"}, 500
        )
        return
    json_response({"ok": True, "message": f"Flag {flag} set to {state_str}"})


def api_partition_mount():
    body = request_body()
    partition = body.get("partition", "")
    mount_point = body.get("mountPoint", "")
    if not safe_part_name(partition):
        json_response({"ok": False, "message": "Invalid partition name"}, 400)
        return
    if not safe_mount_point(mount_point):
        json_response({"ok": False, "message": "Invalid mount point"}, 400)
        return
    if not mount_point:
        json_response({"ok": False, "message": "mountPoint is required"}, 400)
        return
    Path(mount_point).mkdir(parents=True, exist_ok=True)
    cmd = ["mount", partition, mount_point]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to mount: {result['stderr']}"}, 500
        )
        return
    json_response({"ok": True, "message": f"Mounted {partition} at {mount_point}"})


def api_partition_umount():
    body = request_body()
    target = body.get("target", "")
    if not target:
        json_response(
            {"ok": False, "message": "target (partition or mount point) is required"},
            400,
        )
        return
    if not (safe_part_name(target) or safe_mount_point(target)):
        json_response({"ok": False, "message": "Invalid target"}, 400)
        return
    cmd = ["umount", target]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to unmount: {result['stderr']}"}, 500
        )
        return
    json_response({"ok": True, "message": f"Unmounted {target}"})


def api_disk_wipe():
    body = request_body()
    device = body.get("device", "")
    method = body.get("method", "quick")
    if not safe_dev_name(device):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
        return
    if method == "zero":
        cmd = ["dd", "if=/dev/zero", f"of={device}", "bs=1M", "count=1"]
        result = run(cmd, timeout=60)
        if result["rc"] != 0:
            json_response(
                {"ok": False, "message": f"Failed to wipe: {result['stderr']}"}, 500
            )
            return
    cmd = ["wipefs", "-a", device]
    result = run(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {"ok": False, "message": f"Failed to wipe signatures: {result['stderr']}"},
            500,
        )
        return
    json_response({"ok": True, "message": f"Device {device} wiped successfully"})


def api_disk_label():
    body = request_body()
    device = body.get("device", "")
    label_type = body.get("labelType", "gpt")
    if not safe_dev_name(device):
        json_response({"ok": False, "message": "Invalid device name"}, 400)
        return
    if label_type not in ("gpt", "msdos", "mbr"):
        json_response({"ok": False, "message": "Invalid label type"}, 400)
        return
    cmd = ["parted", device, "mklabel", label_type]
    result = run_interactive(cmd, timeout=30)
    if result["rc"] != 0:
        json_response(
            {
                "ok": False,
                "message": f"Failed to create partition table: {result['stderr']}",
            },
            500,
        )
        return
    json_response(
        {"ok": True, "message": f"Partition table {label_type} created on {device}"}
    )


def api_partition_check():
    body = request_body()
    partition = body.get("partition", "")
    if not safe_part_name(partition):
        json_response({"ok": False, "message": "Invalid partition name"}, 400)
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
        cmd = ["ntfsfix", "-n", partition]
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


def api_partition_info():
    body = request_body()
    partition = body.get("partition", "")
    if not safe_part_name(partition):
        json_response({"ok": False, "message": "Invalid partition name"}, 400)
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


def api_fs_resize():
    body = request_body()
    partition = body.get("partition", "")
    fstype = body.get("fstype", "")
    mount_point = body.get("mountPoint", "")
    if not safe_part_name(partition):
        json_response({"ok": False, "message": "Invalid partition name"}, 400)
        return
    if not safe_fs_type(fstype):
        json_response({"ok": False, "message": "Invalid filesystem type"}, 400)
        return
    if fstype in ("ext2", "ext3", "ext4"):
        cmd = ["resize2fs", partition]
    elif fstype == "xfs":
        if not mount_point:
            json_response(
                {"ok": False, "message": "XFS resize requires mount point"}, 400
            )
            return
        cmd = ["xfs_growfs", mount_point]
    elif fstype == "btrfs":
        if not mount_point:
            json_response(
                {"ok": False, "message": "Btrfs resize requires mount point"}, 400
            )
            return
        cmd = ["btrfs", "filesystem", "resize", "max", mount_point]
    elif fstype == "ntfs":
        cmd = ["ntfsresize", "-f", partition]
    else:
        json_response(
            {"ok": False, "message": f"Unsupported filesystem for resize: {fstype}"},
            400,
        )
        return
    result = run(cmd, timeout=120)
    if result["rc"] != 0:
        json_response(
            {
                "ok": False,
                "message": f"Failed to resize filesystem: {result['stderr']}",
            },
            500,
        )
        return
    json_response({"ok": True, "message": f"Filesystem {fstype} resized successfully"})


def api_operations():
    ops = load_operations()
    json_response({"ok": True, "operations": ops})


def api_operations_clear():
    save_operations({"pending": [], "applied": []})
    json_response({"ok": True, "message": "Operations cleared"})


def api_check_tools():
    available, missing = check_tools()
    json_response({"ok": True, "available": available, "missing": missing})


ROUTES = {
    "disks": api_disks,
    "disk-detail": api_disk_detail,
    "partition-create": api_partition_create,
    "partition-delete": api_partition_delete,
    "partition-resize": api_partition_resize,
    "partition-format": api_partition_format,
    "partition-set-flag": api_partition_set_flag,
    "partition-mount": api_partition_mount,
    "partition-umount": api_partition_umount,
    "disk-wipe": api_disk_wipe,
    "disk-label": api_disk_label,
    "partition-check": api_partition_check,
    "partition-info": api_partition_info,
    "fs-resize": api_fs_resize,
    "operations": api_operations,
    "operations-clear": api_operations_clear,
    "check-tools": api_check_tools,
}


def dispatch():
    request = current_request()
    if request == {}:
        raise RuntimeError("no request context")
    path = request.get("query", "")
    parts = path.split("&", 1)
    action = parts[0].strip()
    if not action:
        action = "disks"
    handler = ROUTES.get(action)
    if not handler:
        json_response({"ok": False, "message": f"Unknown action: {action}"}, 404)
        return
    handler()


def main():
    parser = argparse.ArgumentParser(description="WParted Web Backend")
    parser.add_argument("--unix-socket", required=True, help="Unix socket path")
    parser.add_argument("--base-path", default="/app/fn-WParted", help="Base URL path")
    parser.add_argument("--www-root", required=True, help="Static files directory")
    args = parser.parse_args()

    socket_path = args.unix_socket
    base_path = args.base_path
    www_root = args.www_root

    if os.path.exists(socket_path):
        os.unlink(socket_path)

    server = ThreadingUnixHTTPServer(
        socket_path, Handler, base_path=base_path, www_root=www_root
    )
    os.chmod(socket_path, 0o666)

    def shutdown(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"WParted backend listening on {socket_path}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
