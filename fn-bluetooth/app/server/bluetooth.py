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
import shlex
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.environ.get("DATA_DIR", ROOT_DIR)
APP_NAME = "fn-bluetooth"
SHARE_DIR = os.path.join(f"/var/apps/{APP_NAME}/shares/{APP_NAME}")
DEFAULT_RECEIVE_DIR = os.path.join(SHARE_DIR, "received")
CFG_FILE = os.environ.get("CFG_FILE", os.path.join(DATA_DIR, "bluetooth.env"))

CURRENT_STEP = "init"
QUERY = parse_qs(os.environ.get("QUERY_STRING", ""), keep_blank_values=True)
BODY = {}
REQUEST_CONTEXT = threading.local()


class ResponseDone(Exception):
    pass


def current_request():
    return getattr(REQUEST_CONTEXT, "value", {})


class ThreadingUnixHTTPServer(
    socketserver.ThreadingMixIn,
    socketserver.UnixStreamServer,  # pyright: ignore[reportAttributeAccessIssue]
):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path, handler_cls, *, base_path, www_root):
        self.server_name = "fn-bluetooth"
        self.server_port = 0
        self.base_path = normalize_base_path(base_path)
        self.www_root = Path(www_root)
        super().__init__(socket_path, handler_cls)  # pyright: ignore[reportCallIssue]


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def command_exists(name):
    return shutil.which(name) is not None


def run_cmd(args, timeout=None, input_text=None, env_override=None):
    try:
        proc = subprocess.run(
            args,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env_override,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", f"{args[0]} not found"
    except Exception as exc:
        return 1, "", str(exc)


def run_ok(args, timeout=None, input_text=None, env_override=None):
    rc, stdout, stderr = run_cmd(
        args, timeout=timeout, input_text=input_text, env_override=env_override
    )
    return rc == 0, stdout, stderr


def trim(value):
    return (value or "").strip()


def shell_quote(value):
    return shlex.quote(str(value or ""))


def decode_shell_value(raw):
    raw = raw.strip()
    if raw == "":
        return ""
    try:
        parts = shlex.split(raw, posix=True)
    except ValueError:
        return raw.strip("\"'")
    return parts[0] if parts else ""


def load_shell_state(path):
    data = {}
    if not os.path.isfile(path):
        return data
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, raw_value = line.split("=", 1)
                data[key.strip()] = decode_shell_value(raw_value)
    except OSError:
        return {}
    return data


def write_shell_state(path, mapping):
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as handle:
        for key, value in mapping.items():
            handle.write(f"{key}={shell_quote(value)}\n")


def http_write(payload):
    request = current_request()
    handler = request.get("handler", None)
    if handler is not None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        if handler.command != "HEAD":
            handler.wfile.write(body)
        raise ResponseDone()
    sys.stdout.write(
        "Status: 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n"
    )
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    raise SystemExit(0)


def first_query_value(name):
    request = current_request()
    query = request.get("query", QUERY)
    values = query.get(name, [""])
    return values[0]


def ui_lang():
    lang = first_query_value("lang").lower()
    if lang in {"zh", "zh-cn", "zh_cn", "zh-hans"}:
        return "zh"
    if lang in {"en", "en-us", "en_us"}:
        return "en"
    header = (os.environ.get("HTTP_ACCEPT_LANGUAGE") or "").lower()
    return "zh" if "zh" in header else "en"


LOCALIZE_EXACT = {
    "bluetoothctl not found": "未找到 bluetoothctl 命令",
    "no bluetooth adapter": "未检测到蓝牙适配器",
    "adapter not available": "蓝牙适配器不可用",
    "device not found": "未找到设备",
    "pair failed": "配对失败",
    "connect failed": "连接失败",
    "disconnect failed": "断开连接失败",
    "remove failed": "移除设备失败",
    "trust failed": "信任设置失败",
    "scan failed to start": "启动扫描失败",
    "missing action": "缺少 action 参数",
    "invalid device address": "无效的设备地址",
    "file path required": "文件路径必填",
    "send failed": "发送失败",
    "obexctl not found": "未找到 obexctl 命令",
    "audio connect failed": "音频连接失败",
    "audio disconnect failed": "音频断开失败",
    "adapter power on failed": "开启蓝牙失败",
    "adapter power off failed": "关闭蓝牙失败",
    "adapter discoverable on failed": "设置可发现失败",
    "adapter discoverable off failed": "取消可发现失败",
    "agent register failed": "代理注册失败",
    "advertise failed to start": "启动广播失败",
    "advertise failed to stop": "停止广播失败",
    "profile register failed": "注册 Profile 失败",
    "profile unregister failed": "注销 Profile 失败",
    "invalid role": "无效的角色",
    "server alias required": "设备名称必填",
    "alias set failed": "设置设备名称失败",
    "device not responding": "设备无响应，可能已关机或超出范围",
    "device not responding, may be offline or out of range": "设备无响应，可能已关机或超出范围",
    "connection busy, please retry": "连接繁忙，请重试",
    "connection busy, please retry later": "连接繁忙，请稍后重试",
    "device refused connection": "设备拒绝连接",
    "bluetooth adapter not powered": "蓝牙适配器未开启",
    "service profile not available": "设备未开放可连接的蓝牙服务，请在设备上开启对应功能后重试",
    "service discovery failed": "服务发现失败",
    "connection attempt failed": "连接尝试失败",
    "connection cancelled": "连接已取消",
    "already connected": "设备已连接",
    "device already paired": "设备已配对",
    "another operation in progress, please retry": "有其他操作正在进行，请重试",
    "adapter not ready": "适配器未就绪",
    "operation not supported": "操作不支持",
    "authentication failed, please retry": "认证失败，请重试",
    "authentication cancelled": "认证已取消",
    "authentication rejected": "认证被拒绝",
    "authentication timed out": "认证超时",
    "operation failed": "操作失败",
    "bluetooth adapter not found": "未找到蓝牙适配器",
    "resource not available": "资源不可用",
    "invalid parameters": "参数无效",
    "connection timed out": "连接超时",
    "connection failed, device may be offline": "连接失败，设备可能已关机",
    "operation busy, please retry later": "操作繁忙，请稍后重试",
    "failed to create connection socket": "创建连接套接字失败",
    "invalid service record": "无效的服务记录",
    "device rejected connection": "设备拒绝连接",
    "device not found, please pair first": "未找到设备，请先配对",
    "file transfer failed, target device may not support file receiving": "文件传输失败，目标设备可能不支持文件接收",
    "file transfer timed out": "文件传输超时",
    "not connected to device": "未连接到设备",
    "network connection dropped": "网络连接已断开，请在设备端开启蓝牙网络共享后重试",
}

LOCALIZE_REGEX = [
    (r"^pair failed: (.+)$", r"配对失败：\1"),
    (r"^connect failed: (.+)$", r"连接失败：\1"),
    (r"^disconnect failed: (.+)$", r"断开连接失败：\1"),
    (r"^remove failed: (.+)$", r"移除设备失败：\1"),
    (r"^trust failed: (.+)$", r"信任设置失败：\1"),
    (r"^send failed: (.+)$", r"发送失败：\1"),
    (r"^unexpected error \((.+)\)$", r"意外错误：\1"),
]

LOCALIZE_PREFIXES = {
    "pair failed": "配对失败",
    "connect failed": "连接失败",
    "disconnect failed": "断开连接失败",
    "remove failed": "移除设备失败",
    "trust failed": "信任设置失败",
    "send failed": "发送失败",
}


def localize_msg(message):
    if not message or ui_lang() != "zh":
        return message
    if message in LOCALIZE_EXACT:
        return LOCALIZE_EXACT[message]
    prefix, sep, detail = message.partition(":")
    if sep and prefix in LOCALIZE_PREFIXES:
        return f"{LOCALIZE_PREFIXES[prefix]}：{localize_msg(detail.strip())}"
    localized = message
    for pattern, repl in LOCALIZE_REGEX:
        localized = re.sub(pattern, repl, localized)
    return localized


def sanitize_text(text):
    text = text or ""
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", text)
    return text.replace("\r", "")


BLUEZ_ERROR_MAP = {
    "br-connection-page-timeout": "device not responding",
    "br-connection-busy": "connection busy, please retry",
    "br-connection-refused": "device refused connection",
    "br-connection-adapter-not-powered": "bluetooth adapter not powered",
    "br-connection-profile-unavailable": "service profile not available",
    "br-connection-sdp-connect": "service discovery failed",
    "br-connection-create-socket": "failed to create connection socket",
    "br-connection-invalid-sdp": "invalid service record",
    "br-connection-attempt-failed": "connection attempt failed",
    "br-connection-canceled": "connection cancelled",
    "br-connection-already-connected": "already connected",
    "br-connection-reject": "device rejected connection",
    "br-connection-timeout": "connection timed out",
    "InProgress": "another operation in progress, please retry",
    "Already Connected": "already connected",
    "Already Exists": "device already paired",
    "Does Not Exist": "device not found",
    "Not Ready": "adapter not ready",
    "Not Supported": "operation not supported",
    "Authentication Failed": "authentication failed",
    "Authentication Canceled": "authentication cancelled",
    "Authentication Rejected": "authentication rejected",
    "Authentication Timeout": "authentication timed out",
    "Connection Attempt Failed": "connection attempt failed",
    "No Such Adapter": "bluetooth adapter not found",
    "Not Available": "resource not available",
    "Invalid Arguments": "invalid parameters",
}

PROFILE_UUIDS = [
    "0000110b-0000-1000-8000-00805f9b34fb",
    "0000111e-0000-1000-8000-00805f9b34fb",
    "00001108-0000-1000-8000-00805f9b34fb",
    "0000110e-0000-1000-8000-00805f9b34fb",
    "0000110c-0000-1000-8000-00805f9b34fb",
    "00001101-0000-1000-8000-00805f9b34fb",
]


def translate_bluez_error(raw):
    if not raw:
        return raw
    for key, msg in BLUEZ_ERROR_MAP.items():
        if key in raw:
            return msg
    return raw


def humanize_connect_error(dbus_err, btctl_err):
    combined = f"{dbus_err or ''} {btctl_err or ''}"
    translated = translate_bluez_error(combined)
    if translated != combined:
        return translated
    if (
        "page-timeout" in combined
        or "timed out" in combined.lower()
        or "timeout" in combined.lower()
    ):
        return "device not responding, may be offline or out of range"
    if "busy" in combined.lower() or "InProgress" in combined:
        return "connection busy, please retry later"
    if "refused" in combined.lower() or "reject" in combined.lower():
        return "device refused connection"
    if "Failed" in combined and "connect" in combined.lower():
        return "connection failed, device may be offline"
    if "org.bluez.Error.Failed" in combined:
        return "connection failed, please ensure device is powered on and in range"
    return combined


def humanize_pair_error(dbus_err, btctl_err):
    combined = f"{dbus_err or ''} {btctl_err or ''}"
    translated = translate_bluez_error(combined)
    if translated != combined:
        return translated
    if (
        "page-timeout" in combined
        or "timed out" in combined.lower()
        or "timeout" in combined.lower()
    ):
        return "device not responding, may be offline or out of range"
    if "Authentication" in combined:
        return "authentication failed, please retry"
    if "Already Exists" in combined:
        return "device already paired"
    if "busy" in combined.lower() or "InProgress" in combined:
        return "operation busy, please retry later"
    return combined


def error_response(http_status, message):
    http_write(
        {
            "ok": False,
            "error": sanitize_text(localize_msg(message or "")),
            "http_status": http_status,
        }
    )


def ok_response(payload=None):
    body = {"ok": True}
    if payload:
        body.update(payload)
    http_write(body)


def parse_form_body():
    request = current_request()
    if request != {}:
        return request.get("body", {})
    method = (os.environ.get("REQUEST_METHOD") or "GET").upper()
    if method != "POST":
        return {}
    try:
        length = int(os.environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    body = sys.stdin.read(length)
    return parse_qs(body, keep_blank_values=True)


def first_form_value(name):
    request = current_request()
    body = request.get("body", BODY)
    values = body.get(name, [""])
    return values[0]


def is_valid_bdaddr(addr):
    return bool(re.fullmatch(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", addr or ""))


def btctl_exec(commands, timeout=15):
    if not command_exists("bluetoothctl"):
        return 1, "", "bluetoothctl not found"
    cmd_str = "\n".join(commands) + "\nexit\n"
    rc, stdout, stderr = run_cmd(["bluetoothctl"], timeout=timeout, input_text=cmd_str)
    return rc, stdout, stderr


def parse_btctl_devices(output):
    devices = []
    current = None
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
        if m:
            current = {
                "address": m.group(1).upper(),
                "name": m.group(2).strip(),
                "alias": m.group(2).strip(),
                "type": "",
                "icon": "",
                "class": "",
                "paired": False,
                "trusted": False,
                "connected": False,
                "blocked": False,
                "rssi": None,
            }
            devices.append(current)
            continue
        if current:
            m = re.match(
                r"(Paired|Trusted|Connected|Blocked):\s*(yes|no)", line, re.IGNORECASE
            )
            if m:
                current[m.group(1).lower()] = m.group(2).lower() == "yes"
                continue
            m = re.match(r"Alias:\s*(.*)", line)
            if m:
                current["alias"] = m.group(1).strip()
                continue
            m = re.match(r"(Icon|Type):\s*(.*)", line)
            if m:
                current[m.group(1).lower()] = m.group(2).strip()
                continue
            m = re.match(r"Class:\s*(0x[0-9A-Fa-f]+)", line)
            if m:
                current["class"] = m.group(1)
                continue
            m = re.match(r"RSSI:\s*(-?[0-9]+)", line)
            if m:
                current["rssi"] = int(m.group(1))
                continue
    return devices


def get_adapter_info():
    if not command_exists("bluetoothctl"):
        return None
    rc, stdout, _ = btctl_exec(["show"], timeout=10)
    if rc != 0 and not stdout.strip():
        return None
    info = {
        "address": "",
        "name": "",
        "alias": "",
        "powered": False,
        "discoverable": False,
        "pairable": False,
        "discovering": False,
        "class": "",
    }
    for line in stdout.splitlines():
        line = line.strip()
        m = re.match(r"Controller\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
        if m:
            info["address"] = m.group(1).upper()
            info["name"] = m.group(2).strip()
            continue
        m = re.match(r"Alias:\s*(.*)", line)
        if m:
            info["alias"] = m.group(1).strip()
            continue
        for key in ["Powered", "Discoverable", "Pairable", "Discovering"]:
            m = re.match(rf"{key}:\s*(yes|no)", line, re.IGNORECASE)
            if m:
                info[key.lower()] = m.group(1).lower() == "yes"
                break
        m = re.match(r"Class:\s*(0x[0-9A-Fa-f]+)", line)
        if m:
            info["class"] = m.group(1)
    return info


def get_paired_devices():
    if not command_exists("bluetoothctl"):
        return []
    rc, stdout, _ = btctl_exec(["devices Paired"], timeout=10)
    devices = parse_btctl_devices(stdout)
    detailed = []
    for dev in devices:
        _, out2, _ = btctl_exec([f"info {dev['address']}"], timeout=10)
        parsed = parse_btctl_devices(out2)
        if parsed:
            dev.update(parsed[0])
        detailed.append(dev)
    return detailed


def get_scanned_devices():
    if not command_exists("bluetoothctl"):
        return []
    _, stdout, _ = btctl_exec(["devices"], timeout=10)
    devices = parse_btctl_devices(stdout)
    detailed = []
    for dev in devices:
        _, out2, _ = btctl_exec([f"info {dev['address']}"], timeout=10)
        parsed = parse_btctl_devices(out2)
        if parsed:
            dev.update(parsed[0])
        detailed.append(dev)
    return detailed


def classify_device_icon(device):
    icon = device.get("icon", "")
    name = (device.get("name", "") + " " + device.get("alias", "")).lower()
    if icon:
        return icon
    cod_icon = classify_cod_icon(device.get("class", ""))
    if cod_icon:
        return cod_icon
    if any(
        kw in name
        for kw in [
            "audio",
            "headphone",
            "speaker",
            "earphone",
            "headset",
            "airpods",
            "airpod",
            "freebuds",
            "jbl",
            "bose",
            "sony",
            "marshall",
        ]
    ):
        return "audio-headset"
    if "keyboard" in name:
        return "input-keyboard"
    if "mouse" in name:
        return "input-mouse"
    if any(kw in name for kw in ["display", "monitor", "tv"]):
        return "video-display"
    if any(kw in name for kw in ["phone", "mobile", "iphone"]):
        return "phone"
    if any(kw in name for kw in ["tablet", "ipad"]):
        return "input-tablet"
    if "printer" in name:
        return "printer"
    if "camera" in name:
        return "camera-photo"
    if any(
        kw in name
        for kw in [
            "gamepad",
            "controller",
            "joystick",
            "xbox",
            "playstation",
            "dualsense",
        ]
    ):
        return "input-gaming"
    return ""


def classify_cod_icon(cod_str):
    if not cod_str:
        return ""
    try:
        cod = int(cod_str, 16)
    except (ValueError, TypeError):
        return ""
    major_service = (cod >> 13) & 0x1F
    major_class = (cod >> 8) & 0x1F
    minor_class = (cod >> 2) & 0x3F
    if major_class == 1:
        return "computer"
    if major_class == 2:
        return "phone"
    if major_class == 3:
        return (
            "input-keyboard"
            if minor_class == 0x10
            else (
                "input-mouse"
                if minor_class == 0x20
                else "input-gaming" if minor_class == 0x30 else "input-keyboard"
            )
        )
    if major_class == 4:
        return "audio-headset"
    if major_class == 5:
        return "video-display"
    if major_class == 6:
        return "printer"
    if major_class == 7:
        return "camera-photo"
    return ""


def classify_device_type(device):
    icon = classify_device_icon(device)
    type_map = {
        "audio-headset": "audio",
        "audio-card": "audio",
        "audio-speakers": "audio",
        "audio-headphones": "audio",
        "input-keyboard": "keyboard",
        "input-mouse": "mouse",
        "input-tablet": "tablet",
        "input-gaming": "gamepad",
        "video-display": "display",
        "phone": "phone",
        "computer": "computer",
        "printer": "printer",
        "camera-photo": "camera",
    }
    return type_map.get(icon, "other")


def get_audio_env():
    env = os.environ.copy()
    if "PULSE_SERVER" in env and "pipewire" in env["PULSE_SERVER"].lower():
        del env["PULSE_SERVER"]
    if "PULSE_SERVER" not in env:
        system_socket = "/var/run/pulse/native"
        user_socket = f"/run/user/{os.getuid()}/pulse/native"  # pyright: ignore[reportAttributeAccessIssue]
        if os.path.exists(system_socket):
            env["PULSE_SERVER"] = system_socket
        elif os.path.exists(user_socket):
            env["PULSE_SERVER"] = user_socket
    if "XDG_RUNTIME_DIR" not in env:
        for d in [
            f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
            "/run/user/0",
        ]:
            if os.path.isdir(d):
                env["XDG_RUNTIME_DIR"] = d
                break
    return env


def _pactl_available(audio_env=None):
    if not command_exists("pactl"):
        return False
    ok, _, _ = run_ok(
        ["pactl", "info"], timeout=5, env_override=audio_env or get_audio_env()
    )
    return ok


def ensure_audio_service():
    audio_env = get_audio_env()
    if _pactl_available(audio_env):
        return True
    if command_exists("pulseaudio"):
        run_ok(
            ["pulseaudio", "--start", "--log-target=stderr"],
            timeout=8,
            env_override=audio_env,
        )
        for _ in range(20):
            audio_env = get_audio_env()
            if _pactl_available(audio_env):
                _ensure_audio_discovery()
                return True
            time.sleep(0.2)
    if command_exists("wpctl"):
        ok, _, _ = run_ok(["wpctl", "status"], timeout=5, env_override=audio_env)
        return ok
    return False


def _load_pulse_module(module_name, audio_env):
    ok, stdout, _ = run_ok(
        ["pactl", "list", "short", "modules"], timeout=5, env_override=audio_env
    )
    if ok and module_name in stdout:
        return
    run_ok(["pactl", "load-module", module_name], timeout=5, env_override=audio_env)


def get_audio_devices():
    sinks = []
    sources = []
    audio_env = get_audio_env()
    if command_exists("pactl"):
        rc, stdout, _ = run_ok(["pactl", "list", "sinks"], env_override=audio_env)
        if rc:
            current = {}
            for line in stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("Sink #"):
                    if current.get("name"):
                        sinks.append(current)
                    current = {"id": stripped.split("#")[1].strip(), "type": "sink"}
                elif stripped.startswith("Name:"):
                    current["name"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("Description:"):
                    current["displayName"] = stripped.split(":", 1)[1].strip()
            if current.get("name"):
                sinks.append(current)
        rc, stdout, _ = run_ok(["pactl", "list", "sources"], env_override=audio_env)
        if rc:
            current = {}
            for line in stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("Source #"):
                    if current.get("name"):
                        sources.append(current)
                    current = {"id": stripped.split("#")[1].strip(), "type": "source"}
                elif stripped.startswith("Name:"):
                    current["name"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("Description:"):
                    current["displayName"] = stripped.split(":", 1)[1].strip()
            if current.get("name"):
                sources.append(current)
    elif command_exists("wpctl"):
        rc, stdout, _ = run_ok(["wpctl", "status"], env_override=audio_env)
        if rc:
            for line in stdout.splitlines():
                m = re.match(r"\s*(\d+)\.\s+(.*)", line)
                if m:
                    entry = {
                        "id": m.group(1),
                        "name": m.group(2).strip(),
                        "displayName": m.group(2).strip(),
                    }
                    if "Sink" in line or "output" in line.lower():
                        entry["type"] = "sink"
                        sinks.append(entry)
                    elif "Source" in line or "input" in line.lower():
                        entry["type"] = "source"
                        sources.append(entry)
    return sinks, sources


def get_connected_audio_bt_devices():
    devices = get_paired_devices()
    return [
        dev
        for dev in devices
        if dev.get("connected") and classify_device_type(dev) == "audio"
    ]


def handle_adapter_info():
    info = get_adapter_info()
    if info is None:
        if not command_exists("bluetoothctl"):
            error_response("503 Service Unavailable", "bluetoothctl not found")
        error_response("503 Service Unavailable", "adapter not available")
    ok_response({"adapter": info})


def handle_adapter_power():
    action = first_form_value("action") or first_query_value("action")
    if action == "on":
        rc, _, _ = btctl_exec(["power on"], timeout=10)
        if rc != 0:
            error_response("500 Internal Server Error", "adapter power on failed")
        ensure_obex_server()
        ok_response()
    elif action == "off":
        stop_obex_server()
        rc, _, _ = btctl_exec(["power off"], timeout=10)
        if rc != 0:
            error_response("500 Internal Server Error", "adapter power off failed")
        ok_response()
    else:
        error_response("400 Bad Request", "missing action")


def handle_adapter_discoverable():
    action = first_form_value("action") or first_query_value("action")
    if action == "on":
        ensure_agent()
        rc, _, _ = btctl_exec(["discoverable on"], timeout=10)
        if rc != 0:
            error_response(
                "500 Internal Server Error", "adapter discoverable on failed"
            )
        ok_response()
    elif action == "off":
        rc, _, _ = btctl_exec(["discoverable off"], timeout=10)
        if rc != 0:
            error_response(
                "500 Internal Server Error", "adapter discoverable off failed"
            )
        ok_response()
    else:
        error_response("400 Bad Request", "missing action")


def handle_adapter_pairable():
    action = first_form_value("action") or first_query_value("action")
    if action == "on":
        ensure_agent()
        btctl_exec(["pairable on"], timeout=10)
        ok_response()
    elif action == "off":
        btctl_exec(["pairable off"], timeout=10)
        ok_response()
    else:
        error_response("400 Bad Request", "missing action")


SCAN_PID_FILE = os.path.join(DATA_DIR, "scan.pid")
AGENT_PID_FILE = os.path.join(DATA_DIR, "agent.pid")
SCAN_DURATION = 30
BRIDGE_NAME = "br-bt0"
BRIDGE_IP_DEFAULT = "192.168.7.1"
BRIDGE_CIDR_DEFAULT = "192.168.7.1/24"
DHCP_RANGE_START_DEFAULT = "192.168.7.10"
DHCP_RANGE_END_DEFAULT = "192.168.7.50"
TETHER_STATE_FILE = os.path.join(DATA_DIR, "tether.state")


def get_adapter_path():
    info = get_adapter_info()
    if not info or not info.get("address"):
        return None
    return "/org/bluez/hci0"


def get_device_path(addr):
    return f"/org/bluez/hci0/dev_{addr.replace(':', '_')}"


def dbus_call(dest, path, interface, method, timeout=10, args=None):
    if not command_exists("dbus-send"):
        return 1, "", "dbus-send not found"
    cmd = [
        "dbus-send",
        "--system",
        "--print-reply",
        "--type=method_call",
        f"--dest={dest}",
        path,
        f"{interface}.{method}",
    ]
    if args:
        cmd.extend(args)
    return run_cmd(cmd, timeout=timeout)


OBEX_AGENT_PATH = "/org/bluez/obex/auto_agent"


def _unregister_obex_agent():
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        xdg = os.environ.get(
            "XDG_RUNTIME_DIR",
            f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
        )
        bus = _dbus.bus.BusConnection(f"unix:path={xdg}/bus")
        mgr_obj = bus.get_object("org.bluez.obex", "/org/bluez/obex")
        mgr = _dbus.Interface(mgr_obj, "org.bluez.obex.AgentManager1")
        try:
            mgr.UnregisterAgent(OBEX_AGENT_PATH)
        except Exception:
            pass
        try:
            bus.close()
        except Exception:
            pass
    except Exception:
        pass


def _is_obex_agent_registered():
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        xdg = os.environ.get(
            "XDG_RUNTIME_DIR",
            f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
        )
        bus = _dbus.bus.BusConnection(f"unix:path={xdg}/bus")
        bus.get_object("org.bluez.obex", "/org/bluez/obex")
        try:
            bus.close()
        except Exception:
            pass
    except Exception as e:
        print(f"_is_obex_agent_registered: obexd not on session bus: {e}", flush=True)
        return False
    pid_file = os.path.join(DATA_DIR, "agent.pid")
    if not os.path.isfile(pid_file):
        rc, _, _ = run_cmd(["pgrep", "-f", "bt_agent.py"], timeout=3)
        if rc == 0:
            print(
                "_is_obex_agent_registered: no pid file but bt_agent.py running via pgrep",
                flush=True,
            )
            return True
        print(f"_is_obex_agent_registered: no agent.pid file at {pid_file}", flush=True)
        return False
    pid_str = ""
    try:
        with open(pid_file, "r") as f:
            pid_str = f.read().strip()
        if not pid_str:
            print("_is_obex_agent_registered: empty agent.pid", flush=True)
            return False
        pid = int(pid_str)
        os.kill(pid, 0)
    except (ProcessLookupError, ValueError, PermissionError, OSError) as e:
        print(
            f"_is_obex_agent_registered: agent pid {pid_str} not alive: {e}", flush=True
        )
        return False
    return True


def _wait_for_obex_agent(timeout=15):
    for _ in range(timeout * 2):
        if _is_obex_agent_registered():
            return True
        time.sleep(0.5)
    return False


def _restart_agent():
    stop_agent()
    time.sleep(0.5)
    return ensure_agent()


def _is_agent_process_alive():
    pid_file = os.path.join(DATA_DIR, "agent.pid")
    if not os.path.isfile(pid_file):
        return False
    try:
        with open(pid_file, "r") as f:
            pid_str = f.read().strip()
        if not pid_str:
            return False
        os.kill(int(pid_str), 0)
        return True
    except (ProcessLookupError, ValueError, PermissionError, OSError):
        return False


def ensure_agent():
    if _is_agent_process_alive():
        print("ensure_agent: agent already running, skip", flush=True)
        return True

    kill_btctl_processes()
    kill_agent_processes()
    _unregister_obex_agent()

    pid_file = os.path.join(DATA_DIR, "agent.pid")
    if os.path.isfile(pid_file):
        try:
            os.remove(pid_file)
        except OSError:
            pass
    agent_script = os.path.join(ROOT_DIR, "bt_agent.py")
    print(
        f"ensure_agent: agent_script={agent_script} exists={os.path.isfile(agent_script)} DATA_DIR={DATA_DIR} pid_file={pid_file}",
        flush=True,
    )
    if not os.path.isfile(agent_script):
        if not command_exists("bluetoothctl"):
            print("ensure_agent: no bt_agent.py and no bluetoothctl", flush=True)
            return False
        try:
            proc = subprocess.Popen(
                ["bluetoothctl"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            commands = "agent NoInputNoOutput\ndefault-agent\n"
            if proc.stdin is None:
                return False
            proc.stdin.write(commands.encode())
            proc.stdin.flush()
        except Exception:
            return False
        ensure_data_dir()
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        return True
    ensure_data_dir()
    try:
        log_path = os.path.join(DATA_DIR, "agent.log")
        log_fh = open(log_path, "a")
        proc = subprocess.Popen(
            [sys.executable, agent_script],
            stdout=log_fh,
            stderr=log_fh,
            start_new_session=True,
        )
        print(f"ensure_agent: started bt_agent.py pid={proc.pid}", flush=True)
    except Exception as e:
        print(f"ensure_agent: failed to start bt_agent.py: {e}", flush=True)
        return False
    with open(pid_file, "w") as f:
        f.write(str(proc.pid))
    print(f"ensure_agent: pid file written to {pid_file}", flush=True)
    _wait_for_obex_agent(timeout=20)
    alive = _is_agent_process_alive()
    print(f"ensure_agent: after wait, agent alive={alive}", flush=True)
    return True


def is_scan_running():
    if not os.path.isfile(SCAN_PID_FILE):
        return False
    try:
        with open(SCAN_PID_FILE, "r") as f:
            pid = f.read().strip()
        if not pid:
            return False
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, ValueError, PermissionError, OSError):
        try:
            os.remove(SCAN_PID_FILE)
        except OSError:
            pass
        return False


def start_scan_process():
    if is_scan_running():
        return True, ""
    try:
        proc = subprocess.Popen(
            ["timeout", str(SCAN_DURATION), "bluetoothctl", "scan", "on"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        pid = str(proc.pid)
    except Exception as exc:
        return False, str(exc)
    ensure_data_dir()
    with open(SCAN_PID_FILE, "w") as f:
        f.write(pid)
    return True, ""


def stop_scan_process():
    if os.path.isfile(SCAN_PID_FILE):
        try:
            with open(SCAN_PID_FILE, "r") as f:
                pid = f.read().strip()
            if pid:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
                try:
                    os.killpg(  # pyright: ignore[reportAttributeAccessIssue]
                        int(pid), signal.SIGTERM
                    )
                except (ProcessLookupError, PermissionError, OSError):
                    pass
        except (ValueError, OSError):
            pass
        try:
            os.remove(SCAN_PID_FILE)
        except OSError:
            pass
    if command_exists("dbus-send"):
        adapter_path = get_adapter_path()
        if adapter_path:
            run_cmd(
                [
                    "dbus-send",
                    "--system",
                    "--print-reply",
                    "--type=method_call",
                    "--dest=org.bluez",
                    adapter_path,
                    "org.bluez.Adapter1.StopDiscovery",
                ],
                timeout=5,
            )
    btctl_exec(["scan off"], timeout=10)


def get_rssi_map():
    rssi_map = {}
    if not command_exists("dbus-send"):
        return rssi_map
    rc, stdout, _ = run_cmd(
        [
            "dbus-send",
            "--system",
            "--print-reply",
            "--dest=org.bluez",
            "/",
            "org.freedesktop.DBus.ObjectManager",
            "GetManagedObjects",
        ],
        timeout=10,
    )
    if rc != 0:
        return rssi_map
    current_dev_addr = ""
    expect_rssi = False
    for line in stdout.splitlines():
        line = line.strip()
        m = re.match(r"object path\s+\"/org/bluez/hci0/dev_([^\"]+)\"", line)
        if m:
            current_dev_addr = m.group(1).replace("_", ":").upper()
            expect_rssi = False
            continue
        if current_dev_addr:
            if re.match(r"string\s+\"RSSI\"", line):
                expect_rssi = True
                continue
            if expect_rssi:
                rssi_m = re.search(r"int16\s+(-?\d+)", line)
                if rssi_m:
                    rssi_map[current_dev_addr] = int(rssi_m.group(1))
                expect_rssi = False
                current_dev_addr = ""
    return rssi_map


def get_connected_rssi():
    rssi_map = {}
    if not command_exists("hcitool"):
        return rssi_map
    rc, stdout, _ = run_cmd(["bluetoothctl", "devices", "Connected"], timeout=5)
    if rc != 0:
        return rssi_map
    for line in stdout.splitlines():
        m = re.match(r"Device\s+([0-9A-F:]{17})", line, re.IGNORECASE)
        if m:
            addr = m.group(1).upper()
            rc2, out2, _ = run_cmd(["hcitool", "rssi", addr], timeout=3)
            if rc2 == 0:
                rm = re.search(r"(-?\d+)", out2)
                if rm:
                    delta = int(rm.group(1))
                    estimated = -50 + delta
                    rssi_map[addr] = estimated
    return rssi_map


def is_device_connected(addr):
    if not is_valid_bdaddr(addr) or not command_exists("bluetoothctl"):
        return False
    rc, stdout, _ = btctl_exec([f"info {addr}"], timeout=5)
    if rc != 0:
        return False
    return bool(re.search(r"^Connected:\s*yes$", stdout, re.MULTILINE | re.IGNORECASE))


def is_network_connected(addr):
    dev_path = get_device_path(addr)
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        dev_obj = bus.get_object("org.bluez", dev_path)
        props = _dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        return bool(props.Get("org.bluez.Network1", "Connected"))
    except Exception:
        return False


def prepare_pan_interface(iface):
    if not iface:
        return
    run_cmd(["ip", "link", "set", iface, "up"], timeout=5)
    if command_exists("dhclient"):
        run_cmd(["dhclient", "-1", "-nw", iface], timeout=8)


def wait_for_network_stable(addr, seconds=5):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not is_network_connected(addr):
            return False
        time.sleep(0.5)
    return is_network_connected(addr)


def wait_for_device_stable(addr, seconds=8):
    deadline = time.time() + seconds
    disconnect_start = None
    while time.time() < deadline:
        if is_device_connected(addr):
            disconnect_start = None
        else:
            if disconnect_start is None:
                disconnect_start = time.time()
            elif time.time() - disconnect_start > 3:
                return False
        time.sleep(0.5)
    return is_device_connected(addr)


def network_connect(addr, timeout=20):
    dev_path = get_device_path(addr)
    if not dev_path:
        return 1, "device path not found"
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        dev_obj = bus.get_object("org.bluez", dev_path)
        props = _dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        has_network = False
        try:
            props.Get("org.bluez.Network1", "Connected")
            has_network = True
        except Exception:
            pass
        if not has_network:
            return 1, "network not supported"
        try:
            if bool(props.Get("org.bluez.Network1", "Connected")):
                return 0, str(props.Get("org.bluez.Network1", "Interface"))
        except Exception:
            pass
        network = _dbus.Interface(dev_obj, "org.bluez.Network1")
        last_err = ""
        for profile in ("nap", "panu", "gn"):
            try:
                iface = network.Connect(profile, timeout=timeout)
                iface = str(iface)
                prepare_pan_interface(iface)
                if wait_for_network_stable(addr):
                    return 0, iface
                last_err = "network connection dropped"
            except Exception as exc:
                last_err = str(exc)
                if "AlreadyConnected" in last_err or "Already Connected" in last_err:
                    return 0, ""
                if "UnknownMethod" in last_err or "doesn't exist" in last_err:
                    return 1, "network not supported"
        return 1, sanitize_text(last_err)
    except ImportError:
        last_err = ""
        for profile in ("nap", "panu", "gn"):
            rc, stdout, stderr = dbus_call(
                "org.bluez",
                dev_path,
                "org.bluez.Network1",
                "Connect",
                timeout=timeout,
                args=[f"string:{profile}"],
            )
            if rc == 0:
                if wait_for_network_stable(addr):
                    return 0, sanitize_text(stdout)
                last_err = "network connection dropped"
                continue
            err_text = sanitize_text(stderr or stdout)
            if "UnknownMethod" in err_text or "doesn't exist" in err_text:
                return 1, "network not supported"
            last_err = err_text
        return 1, last_err
    except Exception as exc:
        err = sanitize_text(str(exc))
        if "UnknownMethod" in err or "doesn't exist" in err:
            return 1, "network not supported"
        return 1, err


def refresh_device_before_connect(addr, timeout=8):
    if not is_valid_bdaddr(addr) or not command_exists("bluetoothctl"):
        return
    start_scan_process()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_device_connected(addr):
            return
        rc, stdout, _ = btctl_exec([f"info {addr}"], timeout=5)
        if rc == 0 and re.search(
            r"^(RSSI|TxPower|ManufacturerData|ServiceData):", stdout, re.MULTILINE
        ):
            return
        time.sleep(1)


def handle_scan_start():
    ok, err = start_scan_process()
    if not ok:
        error_response(
            "500 Internal Server Error", f"scan failed to start: {sanitize_text(err)}"
        )
    ok_response()


def handle_scan_stop():
    stop_scan_process()
    ok_response()


def handle_devices():
    paired = get_paired_devices()
    all_devices = get_scanned_devices()
    paired_addrs = {d["address"] for d in paired}
    unpaired = [d for d in all_devices if d["address"] not in paired_addrs]
    rssi_map = get_rssi_map()
    connected_rssi = get_connected_rssi()
    for dev in paired:
        dev["deviceType"] = classify_device_type(dev)
        dev["deviceIcon"] = classify_device_icon(dev)
        if dev.get("rssi") is None and dev["address"] in rssi_map:
            dev["rssi"] = rssi_map[dev["address"]]
        if dev.get("rssi") is None and dev["address"] in connected_rssi:
            dev["rssi"] = connected_rssi[dev["address"]]
    for dev in unpaired:
        dev["deviceType"] = classify_device_type(dev)
        dev["deviceIcon"] = classify_device_icon(dev)
        if dev.get("rssi") is None and dev["address"] in rssi_map:
            dev["rssi"] = rssi_map[dev["address"]]
        if dev.get("rssi") is None and dev["address"] in connected_rssi:
            dev["rssi"] = connected_rssi[dev["address"]]
    ok_response({"paired": paired, "available": unpaired})


def handle_device_info():
    addr = first_query_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    _, stdout, _ = btctl_exec([f"info {addr}"], timeout=10)
    devices = parse_btctl_devices(stdout)
    if not devices:
        error_response("404 Not Found", "device not found")
    dev = devices[0]
    dev["deviceType"] = classify_device_type(dev)
    dev["deviceIcon"] = classify_device_icon(dev)
    ok_response({"device": dev})


def handle_pair():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    stop_scan_process()
    time.sleep(0.3)
    kill_btctl_processes()
    time.sleep(0.5)
    ensure_agent()
    time.sleep(1.5)
    rc, err_msg = dbus_pair(addr, timeout=120)
    if rc == 0:
        ok_response()
        return
    kill_btctl_processes()
    time.sleep(0.5)
    ensure_agent()
    time.sleep(1)
    rc2, stdout2, stderr2 = btctl_pair_interactive(addr, timeout=30)
    if rc2 == 0:
        ok_response()
        return
    human_msg = humanize_pair_error(err_msg, sanitize_text(stderr2 or stdout2))
    error_response("500 Internal Server Error", f"pair failed: {human_msg}")


def dbus_pair(addr, timeout=120):
    dev_path = get_device_path(addr)
    if not dev_path:
        return 1, "device path not found"
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        device = _dbus.Interface(
            bus.get_object("org.bluez", dev_path),
            "org.bluez.Device1",
        )
        device.Pair(timeout=timeout)
        return 0, ""
    except ImportError:
        rc, stdout, stderr = dbus_call(
            "org.bluez", dev_path, "org.bluez.Device1", "Pair", timeout=timeout
        )
        if rc == 0:
            return 0, ""
        return 1, sanitize_text(stderr or stdout)
    except Exception as exc:
        err = str(exc)
        if "Already Exists" in err or "AlreadyConnected" in err:
            return 0, ""
        return 1, sanitize_text(err)


def kill_btctl_processes():
    try:
        subprocess.run(
            ["pkill", "-f", "bluetoothctl"], capture_output=True, timeout=3, check=False
        )
    except Exception:
        pass


def kill_agent_processes():
    try:
        subprocess.run(
            ["pkill", "-f", "bt_agent.py"], capture_output=True, timeout=3, check=False
        )
    except Exception:
        pass
    time.sleep(0.3)


def btctl_pair_interactive(addr, timeout=30):
    if not command_exists("bluetoothctl"):
        return 1, "", "bluetoothctl not found"
    try:
        master, slave = pty.openpty()  # type: ignore[attr-defined]
    except Exception:
        return btctl_pair_fallback(addr, timeout)
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            text=True,
        )
    except Exception as exc:
        try:
            os.close(master)
            os.close(slave)
        except OSError:
            pass
        return 1, "", str(exc)
    os.close(slave)
    commands = "agent on\ndefault-agent\npair {}\n".format(addr)
    try:
        os.write(master, commands.encode())
    except Exception:
        pass
    output_buf = b""
    paired = False
    failed = False
    start = time.time()
    while time.time() - start < timeout:
        import select as _select

        r, _, _ = _select.select([master], [], [], 0.5)
        if r:
            try:
                data = os.read(master, 4096)
                if not data:
                    break
                output_buf += data
                text = output_buf.decode(errors="replace")
                if "Confirm passkey" in text or "Request confirmation" in text:
                    try:
                        os.write(master, b"yes\n")
                    except Exception:
                        pass
                if "Pairing successful" in text:
                    paired = True
                    break
                if "Failed to pair" in text:
                    failed = True
                    break
            except OSError:
                break
    try:
        os.write(master, b"exit\n")
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        os.close(master)
    except OSError:
        pass
    stdout_text = output_buf.decode(errors="replace")
    if paired or "Pairing successful" in stdout_text:
        return 0, stdout_text, ""
    if failed or "Failed to pair" in stdout_text:
        return 1, stdout_text, ""
    return 1, stdout_text, "pair timeout"


def btctl_pair_fallback(addr, timeout=30):
    if not command_exists("bluetoothctl"):
        return 1, "", "bluetoothctl not found"
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        return 1, "", str(exc)
    if proc.stdin is None:
        return 1, "", "stdin not available"
    if proc.stdout is None:
        return 1, "", "stdout not available"
    commands = "agent on\ndefault-agent\npair {}\n".format(addr)
    try:
        proc.stdin.write(commands)
        proc.stdin.flush()
    except Exception:
        pass
    output_lines = []
    start = time.time()
    paired = False
    failed = False
    while time.time() - start < timeout:
        import select as _select

        r, _, _ = _select.select([proc.stdout], [], [], 0.5)
        if r:
            try:
                line = proc.stdout.readline()
            except Exception:
                break
            if not line:
                break
            output_lines.append(line.strip())
            if "Confirm passkey" in line or "Request confirmation" in line:
                try:
                    proc.stdin.write("yes\n")
                    proc.stdin.flush()
                except Exception:
                    pass
            if "Pairing successful" in line:
                paired = True
                break
            if "Failed to pair" in line:
                failed = True
                break
    try:
        proc.stdin.write("exit\n")
        proc.stdin.flush()
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    stdout_text = "\n".join(output_lines)
    if paired or "Pairing successful" in stdout_text:
        return 0, stdout_text, ""
    if failed or "Failed to pair" in stdout_text:
        return 1, stdout_text, ""
    return 1, stdout_text, "pair timeout"


def _ensure_audio_discovery():
    if command_exists("pactl"):
        audio_env = get_audio_env()
        if _pactl_available(audio_env):
            _load_pulse_module("module-bluetooth-policy", audio_env)
            _load_pulse_module("module-bluetooth-discover", audio_env)
            _load_pulse_module("module-bluez5-discover", audio_env)


def _trust_device(addr):
    dev_path = get_device_path(addr)
    if not dev_path:
        return
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        dev_obj = bus.get_object("org.bluez", dev_path)
        props = _dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        if not bool(props.Get("org.bluez.Device1", "Trusted")):
            props.Set("org.bluez.Device1", "Trusted", True)
            print(f"_trust_device: {addr} trusted", flush=True)
    except Exception as exc:
        print(f"_trust_device: dbus failed {exc}, trying dbus-send", flush=True)
        if command_exists("dbus-send"):
            run_cmd(
                [
                    "dbus-send",
                    "--system",
                    "--print-reply",
                    "--type=method_call",
                    "--dest=org.bluez",
                    dev_path,
                    "org.freedesktop.DBus.Properties.Set",
                    "string:org.bluez.Device1",
                    "string:Trusted",
                    "variant:boolean:true",
                ],
                timeout=10,
            )
        elif command_exists("bluetoothctl"):
            btctl_exec([f"trust {addr}"], timeout=10)


def handle_connect():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    if is_device_connected(addr):
        _ensure_audio_discovery()
        ok_response()
        return
    _trust_device(addr)
    refresh_device_before_connect(addr)
    last_err = ""
    print(f"handle_connect: {addr} starting btctl_connect_interactive", flush=True)
    rc2, stdout2, stderr2 = btctl_connect_interactive(addr, timeout=30)
    time.sleep(2)
    connected_now = is_device_connected(addr)
    print(
        f"handle_connect: btctl rc={rc2} connected={connected_now} stdout={stdout2[:200] if stdout2 else ''} stderr={stderr2[:200] if stderr2 else ''}",
        flush=True,
    )
    if connected_now:
        _trust_device(addr)
        if wait_for_device_stable(addr):
            _ensure_audio_discovery()
            ok_response()
            return
    if rc2 != 0:
        last_err = stderr2 or stdout2 or ""
    if is_device_connected(addr):
        _trust_device(addr)
        _ensure_audio_discovery()
        ok_response()
        return
    print(f"handle_connect: {addr} starting dbus_connect", flush=True)
    rc, err_msg = dbus_connect(addr, timeout=30)
    time.sleep(2)
    connected_now = is_device_connected(addr)
    print(
        f"handle_connect: dbus_connect rc={rc} err={err_msg} connected={connected_now}",
        flush=True,
    )
    if connected_now:
        _trust_device(addr)
        if wait_for_device_stable(addr):
            _ensure_audio_discovery()
            ok_response()
            return
    if rc != 0:
        last_err = err_msg or last_err
    if is_device_connected(addr):
        _trust_device(addr)
        _ensure_audio_discovery()
        ok_response()
        return
    print(f"handle_connect: {addr} starting network_connect", flush=True)
    rc_net, net_msg = network_connect(addr, timeout=20)
    time.sleep(1)
    print(
        f"handle_connect: network_connect rc={rc_net} msg={net_msg} connected={is_device_connected(addr)} network={is_network_connected(addr)}",
        flush=True,
    )
    if rc_net == 0:
        if is_network_connected(addr) or is_device_connected(addr):
            _ensure_audio_discovery()
            ok_response()
            return
    else:
        if net_msg and net_msg != "network not supported":
            last_err = net_msg or last_err
    if is_device_connected(addr):
        _trust_device(addr)
        _ensure_audio_discovery()
        ok_response()
        return
    print(f"handle_connect: {addr} trying individual profiles", flush=True)
    for uuid in PROFILE_UUIDS:
        print(f"handle_connect: {addr} trying ConnectProfile({uuid})", flush=True)
        rc_p, err_p = dbus_connect_profile(addr, uuid, timeout=15)
        time.sleep(1)
        connected_now = is_device_connected(addr)
        print(
            f"handle_connect: ConnectProfile({uuid}) rc={rc_p} err={err_p} connected={connected_now}",
            flush=True,
        )
        if connected_now or rc_p == 0:
            _trust_device(addr)
            _ensure_audio_discovery()
            ok_response()
            return
    if is_device_connected(addr):
        _trust_device(addr)
        _ensure_audio_discovery()
        ok_response()
        return
    print(f"handle_connect: {addr} all methods failed, last_err={last_err}", flush=True)
    human_msg = humanize_connect_error(last_err, "")
    if not human_msg:
        human_msg = "service profile not available"
    status = (
        "409 Conflict"
        if human_msg in ("service profile not available", "network connection dropped")
        else "500 Internal Server Error"
    )
    error_response(status, f"connect failed: {human_msg}")


def dbus_connect(addr, timeout=30):
    dev_path = get_device_path(addr)
    if not dev_path:
        return 1, "device path not found"
    props = None
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        dev_obj = bus.get_object("org.bluez", dev_path)
        props = _dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        try:
            if bool(props.Get("org.bluez.Device1", "Connected")):
                return 0, ""
        except Exception:
            pass
        device = _dbus.Interface(dev_obj, "org.bluez.Device1")
        device.Connect(timeout=timeout)
        return 0, ""
    except ImportError:
        rc, stdout, stderr = dbus_call(
            "org.bluez", dev_path, "org.bluez.Device1", "Connect", timeout=timeout
        )
        if rc == 0:
            return 0, ""
        err_text = sanitize_text(stderr or stdout)
        if (
            "br-connection-profile-unavailable" in err_text
            or "profile-unavailable" in err_text.lower()
        ):
            time.sleep(3)
            if is_device_connected(addr):
                return 0, ""
        if is_device_connected(addr):
            return 0, ""
        return 1, err_text
    except Exception as exc:
        err = str(exc)
        if "Already Connected" in err:
            return 0, ""
        if (
            "br-connection-profile-unavailable" in err
            or "Profile unavailable" in err
            or "profile-unavailable" in err.lower()
        ):
            time.sleep(3)
            if props is not None:
                try:
                    if bool(props.Get("org.bluez.Device1", "Connected")):
                        return 0, ""
                except Exception:
                    pass
            if is_device_connected(addr):
                return 0, ""
        if props is not None:
            try:
                if bool(props.Get("org.bluez.Device1", "Connected")):
                    return 0, ""
            except Exception:
                pass
        return 1, sanitize_text(err)


def dbus_connect_profile(addr, uuid, timeout=15):
    dev_path = get_device_path(addr)
    if not dev_path:
        return 1, "device path not found"
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        dev_obj = bus.get_object("org.bluez", dev_path)
        device = _dbus.Interface(dev_obj, "org.bluez.Device1")
        device.ConnectProfile(uuid, timeout=timeout)
        return 0, ""
    except ImportError:
        rc, stdout, stderr = dbus_call(
            "org.bluez",
            dev_path,
            "org.bluez.Device1",
            "ConnectProfile",
            timeout=timeout,
            args=[f"string:{uuid}"],
        )
        if rc == 0:
            return 0, ""
        err_text = sanitize_text(stderr or stdout)
        if "Already Connected" in err_text or "Already Exists" in err_text:
            return 0, ""
        return 1, err_text
    except Exception as exc:
        err = str(exc)
        if "Already Connected" in err or "Already Exists" in err:
            return 0, ""
        if (
            "br-connection-profile-unavailable" in err
            or "profile-unavailable" in err.lower()
        ):
            return 1, "profile not available"
        return 1, sanitize_text(err)


def btctl_connect_interactive(addr, timeout=20):
    if not command_exists("bluetoothctl"):
        return 1, "", "bluetoothctl not found"
    try:
        master, slave = pty.openpty()  # type: ignore[attr-defined]
    except Exception:
        return btctl_connect_fallback(addr, timeout)
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            text=True,
        )
    except Exception as exc:
        try:
            os.close(master)
            os.close(slave)
        except OSError:
            pass
        return 1, "", str(exc)
    os.close(slave)
    try:
        os.write(master, b"agent on\n")
        time.sleep(0.3)
        os.write(master, b"default-agent\n")
        time.sleep(0.3)
        os.write(master, f"connect {addr}\n".encode())
    except Exception:
        pass
    output_buf = b""
    connected = False
    failed = False
    start = time.time()
    while time.time() - start < timeout:
        import select as _select

        r, _, _ = _select.select([master], [], [], 0.5)
        if r:
            try:
                data = os.read(master, 4096)
                if not data:
                    break
                output_buf += data
                text = output_buf.decode(errors="replace")
                if (
                    "Confirm passkey" in text
                    or "Request confirmation" in text
                    or "Authorize service" in text
                ):
                    try:
                        os.write(master, b"yes\n")
                    except Exception:
                        pass
                if "Connection successful" in text:
                    connected = True
                    break
                if "Failed to connect" in text:
                    failed = True
                    break
            except OSError:
                break
    try:
        os.write(master, b"exit\n")
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        os.close(master)
    except OSError:
        pass
    stdout_text = output_buf.decode(errors="replace")
    if connected or "Connection successful" in stdout_text:
        return 0, stdout_text, ""
    if failed or "Failed to connect" in stdout_text:
        if is_device_connected(addr):
            return 0, stdout_text, ""
        return 1, stdout_text, ""
    if is_device_connected(addr):
        return 0, stdout_text, ""
    return 1, stdout_text, "connect timeout"


def btctl_connect_fallback(addr, timeout=20):
    if not command_exists("bluetoothctl"):
        return 1, "", "bluetoothctl not found"
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        return 1, "", str(exc)
    if proc.stdin is None:
        return 1, "", "stdin not available"
    if proc.stdout is None:
        return 1, "", "stdout not available"
    commands = "agent on\ndefault-agent\nconnect {}\n".format(addr)
    try:
        proc.stdin.write(commands)
        proc.stdin.flush()
    except Exception:
        pass
    output_lines = []
    start = time.time()
    connected = False
    failed = False
    while time.time() - start < timeout:
        import select as _select

        r, _, _ = _select.select([proc.stdout], [], [], 0.5)
        if r:
            try:
                line = proc.stdout.readline()
            except Exception:
                break
            if not line:
                break
            output_lines.append(line.strip())
            if (
                "Confirm passkey" in line
                or "Request confirmation" in line
                or "Authorize service" in line
            ):
                try:
                    proc.stdin.write("yes\n")
                    proc.stdin.flush()
                except Exception:
                    pass
            if "Connection successful" in line:
                connected = True
                break
            if "Failed to connect" in line:
                failed = True
                break
    try:
        proc.stdin.write("exit\n")
        proc.stdin.flush()
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    stdout_text = "\n".join(output_lines)
    if connected or "Connection successful" in stdout_text:
        return 0, stdout_text, ""
    if failed or "Failed to connect" in stdout_text:
        if is_device_connected(addr):
            return 0, stdout_text, ""
        return 1, stdout_text, ""
    if is_device_connected(addr):
        return 0, stdout_text, ""
    return 1, stdout_text, "connect timeout"


def handle_disconnect():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    dev_path = get_device_path(addr)
    rc, stdout, stderr = dbus_call(
        "org.bluez", dev_path, "org.bluez.Device1", "Disconnect", timeout=15
    )
    if rc != 0:
        btctl_exec([f"disconnect {addr}"], timeout=15)
    ok_response()


def handle_remove():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    dev_path = get_device_path(addr)
    adapter_path = get_adapter_path()
    rc = 0
    if adapter_path:
        rc, stdout, stderr = dbus_call(
            "org.bluez",
            adapter_path,
            "org.bluez.Adapter1",
            "RemoveDevice",
            timeout=15,
            args=[f"objpath:{dev_path}"],
        )
    if not adapter_path or rc != 0:
        btctl_exec([f"remove {addr}"], timeout=15)
    ok_response()


def handle_trust():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    dev_path = get_device_path(addr)
    if command_exists("dbus-send"):
        run_cmd(
            [
                "dbus-send",
                "--system",
                "--print-reply",
                "--type=method_call",
                "--dest=org.bluez",
                dev_path,
                "org.freedesktop.DBus.Properties.Set",
                "string:org.bluez.Device1",
                "string:Trusted",
                "variant:boolean:true",
            ],
            timeout=10,
        )
    else:
        btctl_exec([f"trust {addr}"], timeout=10)
    ok_response()


def handle_untrust():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    dev_path = get_device_path(addr)
    if command_exists("dbus-send"):
        run_cmd(
            [
                "dbus-send",
                "--system",
                "--print-reply",
                "--type=method_call",
                "--dest=org.bluez",
                dev_path,
                "org.freedesktop.DBus.Properties.Set",
                "string:org.bluez.Device1",
                "string:Trusted",
                "variant:boolean:false",
            ],
            timeout=10,
        )
    else:
        btctl_exec([f"untrust {addr}"], timeout=10)
    ok_response()


def handle_audio_status():
    audio_available = ensure_audio_service()
    audio_env = get_audio_env()
    if command_exists("pactl"):
        audio_available = _pactl_available(audio_env)
    elif command_exists("wpctl"):
        ok, _, _ = run_ok(["wpctl", "status"], timeout=5, env_override=audio_env)
        audio_available = ok
    sinks, sources = get_audio_devices()
    bt_audio = get_connected_audio_bt_devices() if audio_available else []
    default_sink = ""
    default_source = ""
    if audio_available and command_exists("pactl"):
        _, sink_out, _ = run_ok(
            ["pactl", "get-default-sink"], timeout=5, env_override=audio_env
        )
        default_sink = sink_out.strip()
        _, src_out, _ = run_ok(
            ["pactl", "get-default-source"], timeout=5, env_override=audio_env
        )
        default_source = src_out.strip()
    ok_response(
        {
            "sinks": sinks,
            "sources": sources,
            "bluetoothAudio": bt_audio,
            "defaultSink": default_sink,
            "defaultSource": default_source,
            "audioAvailable": audio_available,
        }
    )


def handle_audio_connect():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    ensure_audio_service()
    dev_path = get_device_path(addr)
    rc, _, _ = dbus_call(
        "org.bluez", dev_path, "org.bluez.Device1", "Connect", timeout=20
    )
    if rc != 0:
        btctl_exec([f"connect {addr}"], timeout=20)
    time.sleep(1)
    _ensure_audio_discovery()
    ok_response()


def handle_audio_disconnect():
    addr = first_form_value("address")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    dev_path = get_device_path(addr)
    rc, _, _ = dbus_call(
        "org.bluez", dev_path, "org.bluez.Device1", "Disconnect", timeout=15
    )
    if rc != 0:
        btctl_exec([f"disconnect {addr}"], timeout=15)
    ok_response()


def handle_audio_sink_set():
    sink_name = first_form_value("sink")
    if not sink_name:
        error_response("400 Bad Request", "sink name required")
    ensure_audio_service()
    audio_env = get_audio_env()
    if command_exists("pactl"):
        sinks_now, _ = get_audio_devices()
        found = any(s["name"] == sink_name for s in sinks_now)
        if not found:
            error_response("404 Not Found", f"sink not available: {sink_name}")
        stderr = ""
        for attempt in range(3):
            rc, _, stderr = run_ok(
                ["pactl", "set-default-sink", sink_name],
                timeout=5,
                env_override=audio_env,
            )
            if rc:
                ok_response()
                return
            if attempt < 2:
                time.sleep(0.5)
        error_response(
            "500 Internal Server Error",
            f"set default sink failed: {sanitize_text(stderr)}",
        )
    elif command_exists("wpctl"):
        run_ok(["wpctl", "set-default", sink_name], timeout=5, env_override=audio_env)
    ok_response()


def handle_audio_source_set():
    source_name = first_form_value("source")
    if not source_name:
        error_response("400 Bad Request", "source name required")
    ensure_audio_service()
    audio_env = get_audio_env()
    if command_exists("pactl"):
        _, sources_now = get_audio_devices()
        found = any(s["name"] == source_name for s in sources_now)
        if not found:
            error_response("404 Not Found", f"source not available: {source_name}")
        stderr = ""
        for attempt in range(3):
            rc, _, stderr = run_ok(
                ["pactl", "set-default-source", source_name],
                timeout=5,
                env_override=audio_env,
            )
            if rc:
                ok_response()
                return
            if attempt < 2:
                time.sleep(0.5)
        error_response(
            "500 Internal Server Error",
            f"set default source failed: {sanitize_text(stderr)}",
        )
    elif command_exists("wpctl"):
        run_ok(["wpctl", "set-default", source_name], timeout=5, env_override=audio_env)
    ok_response()


def humanize_obex_error(raw):
    if not raw:
        return raw
    if "connect timeout" in raw.lower() or "Failed to connect" in raw:
        return "device not responding, may be offline or out of range"
    if "OBEX Connect failed" in raw:
        return "device not responding, may be offline or out of range"
    if "OBEX session failed" in raw:
        return "device not responding, may be offline or out of range"
    if "Transfer failed" in raw:
        return "file transfer failed, target device may not support file receiving"
    if "Transfer error" in raw:
        return "file transfer failed, target device may not support file receiving"
    if "Transfer timeout" in raw.lower() or "transfer timeout" in raw.lower():
        return "file transfer timed out"
    if "br-connection-page-timeout" in raw:
        return "device not responding, may be offline or out of range"
    if "br-connection-busy" in raw:
        return "connection busy, please retry later"
    if "br-connection-refused" in raw:
        return "device refused connection"
    if "InProgress" in raw:
        return "another operation in progress, please retry"
    if "not connected" in raw.lower():
        return "not connected to device"
    return translate_bluez_error(raw)


def handle_send_file():
    addr = first_form_value("address")
    filepath = first_form_value("filepath")
    if not is_valid_bdaddr(addr):
        error_response("400 Bad Request", "invalid device address")
    if not filepath:
        error_response("400 Bad Request", "file path required")
    if not os.path.isfile(filepath):
        error_response("400 Bad Request", "file not found")
    if not command_exists("obexctl") and not command_exists("bluetoothctl"):
        error_response("503 Service Unavailable", "obexctl not found")
    paired = get_paired_devices()
    target = None
    for d in paired:
        if d["address"].upper() == addr.upper():
            target = d
            break
    if not target:
        error_response("400 Bad Request", "device not found, please pair first")
    elif not target.get("connected"):
        rc_c, err_c = dbus_connect(addr, timeout=15)
        if rc_c != 0:
            human_msg = humanize_connect_error(err_c, "")
            error_response("500 Internal Server Error", f"connect failed: {human_msg}")
            return
    ensure_obex_server()
    time.sleep(1)
    fname = os.path.basename(filepath)
    fsize = os.path.getsize(filepath)
    with _transfer_progress_lock:
        _transfer_progress.update(
            {
                "active": True,
                "direction": "send",
                "address": addr,
                "filename": fname,
                "size": fsize,
                "transferred": 0,
                "status": "sending",
            }
        )
    rc, out = _dbus_send_file(addr, filepath, timeout=90)
    if rc:
        with _transfer_progress_lock:
            _transfer_progress.update(
                {
                    "active": False,
                    "direction": "send",
                    "address": addr,
                    "filename": fname,
                    "size": fsize,
                    "transferred": fsize,
                    "status": "complete",
                }
            )
        _add_transfer_record("send", addr, fname, fsize, "success")
        ok_response()
        return
    if "python-dbus not available" not in out and command_exists("obexctl"):
        with _transfer_progress_lock:
            _transfer_progress.update({"status": "retrying"})
        rc2, out2 = obexctl_send_file(addr, filepath, timeout=90)
        if rc2:
            with _transfer_progress_lock:
                _transfer_progress.update(
                    {
                        "active": False,
                        "direction": "send",
                        "address": addr,
                        "filename": fname,
                        "size": fsize,
                        "transferred": fsize,
                        "status": "complete",
                    }
                )
            _add_transfer_record("send", addr, fname, fsize, "success")
            ok_response()
            return
        human_msg = humanize_obex_error(sanitize_text(out2))
        with _transfer_progress_lock:
            _transfer_progress.update(
                {
                    "active": False,
                    "direction": "send",
                    "address": addr,
                    "filename": fname,
                    "size": fsize,
                    "transferred": 0,
                    "status": "error",
                }
            )
        _add_transfer_record("send", addr, fname, fsize, "failed")
        error_response("500 Internal Server Error", f"send failed: {human_msg}")
        return
    human_msg = humanize_obex_error(sanitize_text(out))
    with _transfer_progress_lock:
        _transfer_progress.update(
            {
                "active": False,
                "direction": "send",
                "address": addr,
                "filename": fname,
                "size": fsize,
                "transferred": 0,
                "status": "error",
            }
        )
    _add_transfer_record("send", addr, fname, fsize, "failed")
    error_response("500 Internal Server Error", f"send failed: {human_msg}")


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x01|\x02")


def _strip_ansi(s):
    return _ANSI_RE.sub("", s)


def _obex_cleanup(client, session_path, bus):
    if client and session_path:
        try:
            client.RemoveSession(session_path)
        except Exception:
            pass
    if bus:
        try:
            bus.close()
        except Exception:
            pass


def _dbus_send_file(addr, filepath, timeout=60):
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]
    except ImportError:
        return 0, "python-dbus not available"
    xdg = f"/run/user/{os.getuid()}"  # pyright: ignore[reportAttributeAccessIssue]
    env = os.environ.copy()
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg}/bus"
    env["XDG_RUNTIME_DIR"] = xdg
    bus = None
    client = None
    session_path = None
    for attempt in range(3):
        try:
            bus = _dbus.bus.BusConnection(f"unix:path={xdg}/bus")
            obj = bus.get_object("org.bluez.obex", "/org/bluez/obex")
            client = _dbus.Interface(obj, "org.bluez.obex.Client1")
            session_path = client.CreateSession(addr, {"Target": _dbus.String("OPP")})
            break
        except Exception as exc:
            if bus:
                try:
                    bus.close()
                except Exception:
                    pass
                bus = None
            is_obex_refused = "0x53" in str(exc) or "OBEX Connect failed" in str(exc)
            if is_obex_refused and attempt < 2:
                if attempt == 0:
                    if command_exists("systemctl"):
                        try:
                            subprocess.run(
                                ["systemctl", "--user", "restart", "obex"],
                                env=env,
                                timeout=5,
                                capture_output=True,
                            )
                        except Exception:
                            pass
                        time.sleep(2)
                elif attempt == 1:
                    run_cmd(["bluetoothctl", "disconnect", addr], timeout=10)
                    time.sleep(3)
                    run_cmd(["bluetoothctl", "connect", addr], timeout=15)
                    time.sleep(2)
                    if command_exists("systemctl"):
                        try:
                            subprocess.run(
                                ["systemctl", "--user", "restart", "obex"],
                                env=env,
                                timeout=5,
                                capture_output=True,
                            )
                        except Exception:
                            pass
                        time.sleep(2)
                continue
            return 0, f"OBEX session failed: {exc}"
    assert bus is not None and session_path is not None
    try:
        session_obj = bus.get_object("org.bluez.obex", session_path)
        push = _dbus.Interface(session_obj, "org.bluez.obex.ObjectPush1")
        transfer_path, props = push.SendFile(filepath)
    except Exception as exc:
        _obex_cleanup(client, session_path, bus)
        return 0, f"SendFile failed: {exc}"
    p = dict(props)
    file_size = int(p.get("Size", 0))
    try:
        transfer_obj = bus.get_object("org.bluez.obex", transfer_path)
        transfer_props = _dbus.Interface(
            transfer_obj, "org.freedesktop.DBus.Properties"
        )
    except Exception as exc:
        _obex_cleanup(client, session_path, bus)
        return 0, f"Transfer monitoring failed: {exc}"
    transferred = 0
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = str(transfer_props.Get("org.bluez.obex.Transfer1", "Status"))
            transferred = int(
                transfer_props.Get("org.bluez.obex.Transfer1", "Transferred")
            )
        except Exception:
            time.sleep(2)
            try:
                status = str(transfer_props.Get("org.bluez.obex.Transfer1", "Status"))
                transferred = int(
                    transfer_props.Get("org.bluez.obex.Transfer1", "Transferred")
                )
            except Exception:
                if file_size > 0 and transferred >= file_size * 0.9:
                    with _transfer_progress_lock:
                        _transfer_progress["transferred"] = file_size
                        _transfer_progress["status"] = "complete"
                    _obex_cleanup(client, session_path, bus)
                    return 1, f"Transfer completed ({transferred}/{file_size})"
                break
        if status == "complete":
            with _transfer_progress_lock:
                _transfer_progress["transferred"] = transferred
                _transfer_progress["status"] = "complete"
            _obex_cleanup(client, session_path, bus)
            return 1, f"Transfer successful ({transferred}/{file_size})"
        if status == "error":
            with _transfer_progress_lock:
                _transfer_progress["transferred"] = transferred
                _transfer_progress["status"] = "error"
            _obex_cleanup(client, session_path, bus)
            return 0, f"Transfer error (transferred {transferred}/{file_size})"
        with _transfer_progress_lock:
            _transfer_progress["transferred"] = transferred
            _transfer_progress["status"] = status
        if file_size > 0 and transferred >= file_size:
            time.sleep(2)
            try:
                status2 = str(transfer_props.Get("org.bluez.obex.Transfer1", "Status"))
            except Exception:
                status2 = "unknown"
            _obex_cleanup(client, session_path, bus)
            if status2 in ("error",):
                return 0, f"Transfer error (transferred {transferred}/{file_size})"
            return 1, f"Transfer completed ({transferred}/{file_size})"
        time.sleep(1)
    _obex_cleanup(client, session_path, bus)
    if transferred >= file_size and transferred > 0:
        return 1, f"Transfer completed ({transferred}/{file_size})"
    return 0, f"Transfer timeout (transferred {transferred}/{file_size})"


def obexctl_send_file(addr, filepath, timeout=60):
    try:
        master, slave = pty.openpty()  # type: ignore[attr-defined]
    except Exception:
        return 0, "pty not available"
    env = os.environ.copy()
    xdg = f"/run/user/{os.getuid()}"  # pyright: ignore[reportAttributeAccessIssue]
    if os.path.exists(f"{xdg}/bus"):
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg}/bus"
        env["XDG_RUNTIME_DIR"] = xdg
    try:
        proc = subprocess.Popen(
            ["obexctl"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            text=True,
            env=env,
        )
    except Exception as exc:
        try:
            os.close(master)
            os.close(slave)
        except OSError:
            pass
        return 0, str(exc)
    os.close(slave)
    output_buf = b""
    connected = False
    client_ready = False
    sent = False
    failed = False
    connect_sent = False
    start = time.time()
    fsize = 0
    try:
        fsize = os.path.getsize(filepath)
    except OSError:
        pass
    _obex_progress_re = re.compile(r"Transferred:\s*(\d+)", re.IGNORECASE)
    while time.time() - start < timeout:
        import select as _select

        r, _, _ = _select.select([master], [], [], 1)
        if r:
            try:
                data = os.read(master, 4096)
                if not data:
                    break
                output_buf += data
                text = _strip_ansi(output_buf.decode(errors="replace"))
                if not client_ready and "[NEW] Client /org/bluez/obex" in text:
                    client_ready = True
                if client_ready and not connect_sent:
                    try:
                        os.write(master, f"connect {addr}\n".encode())
                        connect_sent = True
                    except Exception:
                        pass
                if (
                    not connected
                    and connect_sent
                    and ("Connection successful" in text or "Connected: yes" in text)
                ):
                    connected = True
                    try:
                        os.write(master, f"send {filepath}\n".encode())
                    except Exception:
                        pass
                if fsize > 0:
                    progress_matches = _obex_progress_re.findall(text)
                    if progress_matches:
                        try:
                            last_transferred = int(progress_matches[-1])
                            with _transfer_progress_lock:
                                _transfer_progress["transferred"] = min(
                                    last_transferred, fsize
                                )
                        except (ValueError, IndexError):
                            pass
                if "Transfer successful" in text or "Transfer complete" in text:
                    if fsize > 0:
                        with _transfer_progress_lock:
                            _transfer_progress["transferred"] = fsize
                    sent = True
                    break
                if "Transfer failed" in text:
                    failed = True
                    break
                if "Failed to connect" in text:
                    failed = True
                    break
                if "Status: error" in text:
                    failed = True
                    break
            except OSError:
                break
        if not client_ready and time.time() - start > 8:
            try:
                os.write(master, f"connect {addr}\n".encode())
                connect_sent = True
            except Exception:
                pass
    try:
        os.write(master, b"disconnect\nexit\n")
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        os.close(master)
    except OSError:
        pass
    text = _strip_ansi(output_buf.decode(errors="replace"))
    if sent:
        return 1, text
    if failed:
        return 0, text
    if not connected:
        return 0, f"connect timeout: {text[-200:]}"
    return 0, f"transfer timeout: {text[-200:]}"


def get_adapter_role():
    state_data = load_shell_state(CFG_FILE)
    return state_data.get("BT_ROLE", "client")


def save_adapter_role(role):
    state_data = load_shell_state(CFG_FILE)
    state_data["BT_ROLE"] = role
    write_shell_state(CFG_FILE, state_data)


def get_server_profiles():
    profiles = []
    if command_exists("bluetoothctl"):
        _, stdout, _ = btctl_exec(["show"], timeout=10)
        for line in stdout.splitlines():
            m = re.match(r"\s*UUID:\s+(.+?)\s+\(([0-9a-fA-F-]+)\)", line.strip())
            if m:
                profiles.append(
                    {"name": m.group(1).strip(), "uuid": m.group(2).strip()}
                )
    return profiles


def get_connected_to_us():
    devices = get_paired_devices()
    return [dev for dev in devices if dev.get("connected")]


def handle_role_get():
    role = get_adapter_role()
    info = get_adapter_info() or {}
    ok_response(
        {
            "role": role,
            "adapter": info,
            "serverActive": role == "server"
            and info.get("discoverable", False)
            and info.get("pairable", False),
        }
    )


def handle_role_set():
    role = first_form_value("role") or first_query_value("role")
    if role not in ("client", "server"):
        error_response("400 Bad Request", "invalid role")
    old_role = get_adapter_role()
    save_adapter_role(role)
    if role == "server":
        ensure_agent()
        btctl_exec(["power on", "discoverable on", "pairable on"], timeout=15)
        ensure_obex_server()
    elif old_role == "server":
        btctl_exec(["discoverable off"], timeout=10)
    ok_response({"role": role})


def handle_server_advertise():
    action = first_form_value("action") or first_query_value("action")
    if action == "on":
        ensure_agent()
        btctl_exec(["power on", "discoverable on", "pairable on"], timeout=15)
        ok_response()
    elif action == "off":
        btctl_exec(["discoverable off", "pairable off"], timeout=10)
        ok_response()
    else:
        error_response("400 Bad Request", "missing action")


def handle_server_alias():
    alias = first_form_value("alias") or first_query_value("alias")
    if not alias:
        error_response("400 Bad Request", "server alias required")
    rc, _, stderr = btctl_exec([f"set-alias {alias}"], timeout=10)
    if rc != 0:
        error_response(
            "500 Internal Server Error", f"alias set failed: {sanitize_text(stderr)}"
        )
    ok_response()


def handle_server_profiles():
    profiles = get_server_profiles()
    connected = get_connected_to_us()
    ok_response({"profiles": profiles, "connectedDevices": connected})


def handle_server_accept():
    ensure_obex_server()
    time.sleep(1)
    ensure_agent()
    agent_ok = _is_obex_agent_registered()
    if not agent_ok:
        _restart_agent()
        agent_ok = _is_obex_agent_registered()
    ok_response({"obexAgentReady": agent_ok})


def handle_incoming_devices():
    connected = get_connected_to_us()
    for dev in connected:
        dev["deviceType"] = classify_device_type(dev)
        dev["deviceIcon"] = classify_device_icon(dev)
    ok_response({"devices": connected})


def handle_status():
    adapter = get_adapter_info()
    paired_count = 0
    connected_count = 0
    if adapter:
        devices = get_paired_devices()
        paired_count = len(devices)
        connected_count = sum(1 for d in devices if d.get("connected"))
    obexd_running = run_cmd(["pgrep", "-x", "obexd"], timeout=3)[0] == 0
    obex_agent_ok = _is_obex_agent_registered() if obexd_running else False
    ok_response(
        {
            "available": adapter is not None,
            "powered": adapter.get("powered", False) if adapter else False,
            "pairedCount": paired_count,
            "connectedCount": connected_count,
            "obexdRunning": obexd_running,
            "obexAgentReady": obex_agent_ok,
        }
    )


RECEIVE_DIR = DEFAULT_RECEIVE_DIR
TRANSFER_HISTORY_FILE = os.path.join(DATA_DIR, "transfer_history.json")
_transfer_progress = {
    "active": False,
    "direction": "",
    "address": "",
    "filename": "",
    "size": 0,
    "transferred": 0,
    "status": "",
}
_transfer_progress_lock = threading.Lock()


def _start_receive_monitor():
    def _monitor():
        while True:
            try:
                import dbus as _dbus  # pyright: ignore[reportMissingImports]

                xdg = os.environ.get(
                    "XDG_RUNTIME_DIR",
                    f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
                )
                bus = _dbus.bus.BusConnection(f"unix:path={xdg}/bus")

                def _on_properties_changed(interface, changed, invalidated, path):
                    if interface != "org.bluez.obex.Transfer1":
                        return
                    with _transfer_progress_lock:
                        if "Status" in changed:
                            status = str(changed["Status"])
                            if _transfer_progress.get("direction") == "send":
                                pass
                            else:
                                _transfer_progress["status"] = status
                                if status in ("complete", "error"):
                                    fname = _transfer_progress.get("filename", "")
                                    fsize = _transfer_progress.get("size", 0)
                                    addr = _transfer_progress.get("address", "")
                                    rec_status = (
                                        "success" if status == "complete" else "failed"
                                    )
                                    _add_transfer_record(
                                        "receive", addr, fname, fsize, rec_status
                                    )
                                    _transfer_progress.update(
                                        {
                                            "active": False,
                                            "status": (
                                                "complete"
                                                if status == "complete"
                                                else "error"
                                            ),
                                        }
                                    )
                        if "Transferred" in changed:
                            if _transfer_progress.get("direction") != "send":
                                _transfer_progress["transferred"] = int(
                                    changed["Transferred"]
                                )

                bus.add_signal_receiver(
                    _on_properties_changed,
                    signal_name="PropertiesChanged",
                    dbus_interface="org.freedesktop.DBus.Properties",
                    bus_name="org.bluez.obex",
                )

                def _on_transfer_created(path, _dict):
                    d = dict(_dict)
                    fname = str(d.get("Name", ""))
                    fsize = int(d.get("Size", 0))
                    session_path = str(d.get("Session", ""))
                    addr = ""
                    try:
                        session_obj = bus.get_object("org.bluez.obex", session_path)
                        session_props = _dbus.Interface(
                            session_obj, "org.freedesktop.DBus.Properties"
                        )
                        addr = str(
                            session_props.Get("org.bluez.obex.Session1", "Destination")
                        )
                    except Exception:
                        pass
                    with _transfer_progress_lock:
                        _transfer_progress.update(
                            {
                                "active": True,
                                "direction": "receive",
                                "address": addr,
                                "filename": fname,
                                "size": fsize,
                                "transferred": 0,
                                "status": "receiving",
                            }
                        )

                bus.add_signal_receiver(
                    _on_transfer_created,
                    signal_name="TransferCreated",
                    dbus_interface="org.bluez.obex.ObjectPush1",
                    bus_name="org.bluez.obex",
                )
                bus.add_signal_receiver(
                    _on_transfer_created,
                    signal_name="TransferCreated",
                    dbus_interface="org.bluez.obex.Transfer1",
                    bus_name="org.bluez.obex",
                )

                while True:
                    bus.flush()
                    time.sleep(0.5)
            except Exception:
                pass
            time.sleep(5)

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()


def _load_transfer_history():
    if os.path.isfile(TRANSFER_HISTORY_FILE):
        try:
            with open(TRANSFER_HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_transfer_history(history):
    try:
        with open(TRANSFER_HISTORY_FILE, "w") as f:
            json.dump(history[:200], f)
    except Exception:
        pass


def _add_transfer_record(direction, address, filename, size, status):
    history = _load_transfer_history()
    history.insert(
        0,
        {
            "direction": direction,
            "address": address,
            "filename": filename,
            "size": size,
            "status": status,
            "time": int(time.time()),
        },
    )
    _save_transfer_history(history)


def handle_transfer_progress():
    with _transfer_progress_lock:
        ok_response(dict(_transfer_progress))


def handle_transfer_history():
    history = _load_transfer_history()
    ok_response({"history": history[:50]})


def handle_clear_transfer_history():
    _save_transfer_history([])
    ok_response()


def ensure_obex_server():
    global RECEIVE_DIR
    RECEIVE_DIR = DEFAULT_RECEIVE_DIR
    os.makedirs(RECEIVE_DIR, exist_ok=True)
    obex_override_dir = os.path.expanduser("~/.config/systemd/user/obex.service.d")
    os.makedirs(obex_override_dir, exist_ok=True)
    override_file = os.path.join(obex_override_dir, "override.conf")
    override_content = "[Service]\nExecStart=\nExecStart=/usr/libexec/bluetooth/obexd -r {0} -a -n\n".format(
        RECEIVE_DIR
    )
    need_restart = False
    try:
        existing = ""
        if os.path.isfile(override_file):
            with open(override_file) as f:
                existing = f.read()
        if existing != override_content:
            with open(override_file, "w") as f:
                f.write(override_content)
            need_restart = True
    except OSError:
        need_restart = True
    if command_exists("systemctl"):
        xdg = os.environ.get(
            "XDG_RUNTIME_DIR",
            f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
        )
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = xdg
        if need_restart:
            try:
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"],
                    env=env,
                    timeout=5,
                    capture_output=True,
                )
            except Exception:
                pass
        try:
            rc_check = subprocess.run(
                ["systemctl", "--user", "is-active", "obex"],
                env=env,
                timeout=5,
                capture_output=True,
                text=True,
            )
            if rc_check.stdout.strip() != "active" or need_restart:
                subprocess.run(
                    ["systemctl", "--user", "restart", "obex"],
                    env=env,
                    timeout=5,
                    capture_output=True,
                )
        except Exception:
            pass
    rc, _, _ = run_cmd(["pgrep", "-x", "obexd"], timeout=5)
    if rc != 0 and command_exists("obexd"):
        try:
            xdg = os.environ.get(
                "XDG_RUNTIME_DIR",
                f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
            )
            obex_env = os.environ.copy()
            obex_env["XDG_RUNTIME_DIR"] = xdg
            obex_env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg}/bus"
            subprocess.Popen(
                ["/usr/libexec/bluetooth/obexd", "-r", RECEIVE_DIR, "-a", "-n"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=obex_env,
            )
            time.sleep(2)
        except Exception:
            pass
    for _ in range(10):
        rc2, _, _ = run_cmd(["pgrep", "-x", "obexd"], timeout=3)
        if rc2 == 0:
            break
        time.sleep(1)
    for _ in range(10):
        try:
            import dbus as _dbus  # pyright: ignore[reportMissingImports]

            xdg = os.environ.get(
                "XDG_RUNTIME_DIR",
                f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
            )
            bus = _dbus.bus.BusConnection(f"unix:path={xdg}/bus")
            bus.get_object("org.bluez.obex", "/org/bluez/obex")
            try:
                bus.close()
            except Exception:
                pass
            break
        except Exception:
            time.sleep(1)
    if not _is_obex_agent_registered():
        time.sleep(3)
        if not _is_obex_agent_registered():
            ensure_agent()


def stop_obex_server():
    if command_exists("systemctl"):
        xdg = os.environ.get(
            "XDG_RUNTIME_DIR",
            f"/run/user/{os.getuid()}",  # pyright: ignore[reportAttributeAccessIssue]
        )
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = xdg
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "obex"],
                env=env,
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass
    elif command_exists("pkill"):
        run_cmd(["pkill", "-x", "obexd"], timeout=5)


def handle_received_files():
    global RECEIVE_DIR
    RECEIVE_DIR = DEFAULT_RECEIVE_DIR
    if not os.path.isdir(RECEIVE_DIR):
        ok_response({"files": []})
        return
    files = []
    for fname in sorted(
        os.listdir(RECEIVE_DIR),
        key=lambda f: os.path.getmtime(os.path.join(RECEIVE_DIR, f)),
        reverse=True,
    ):
        fpath = os.path.join(RECEIVE_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        st = os.stat(fpath)
        files.append(
            {
                "name": fname,
                "size": st.st_size,
                "time": int(st.st_mtime),
                "path": fpath,
            }
        )
    ok_response({"files": files[:50]})


def handle_delete_received():
    fname = first_form_value("name")
    if not fname or "/" in fname or ".." in fname:
        error_response("400 Bad Request", "invalid file name")
    fpath = os.path.join(RECEIVE_DIR, fname)
    if os.path.isfile(fpath):
        os.remove(fpath)
    ok_response()


def handle_clear_received():
    if os.path.isdir(RECEIVE_DIR):
        for fname in os.listdir(RECEIVE_DIR):
            fpath = os.path.join(RECEIVE_DIR, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
    ok_response()


def get_internet_interface():
    rc, stdout, _ = run_cmd(["ip", "route", "show", "default"], timeout=5)
    if rc == 0:
        for line in stdout.splitlines():
            parts = line.split()
            if "dev" in parts:
                idx = parts.index("dev")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
    return "eth0"


def is_tethering_active():
    return os.path.exists(f"/sys/class/net/{BRIDGE_NAME}")


_prev_traffic = {}
_prev_traffic_time = 0


def _read_iface_stats(iface):
    try:
        with open("/proc/net/dev") as f:
            for line in f:
                line = line.strip()
                if ":" not in line:
                    continue
                name, rest = line.split(":", 1)
                if name.strip() == iface:
                    parts = rest.split()
                    rx_bytes = int(parts[0])
                    tx_bytes = int(parts[8])
                    return rx_bytes, tx_bytes
    except Exception:
        pass
    return None, None


def _calc_traffic_speed(iface):
    global _prev_traffic, _prev_traffic_time
    rx, tx = _read_iface_stats(iface)
    now = time.time()
    if rx is None or tx is None:
        return 0, 0
    result_rx = 0
    result_tx = 0
    if iface in _prev_traffic and _prev_traffic_time > 0:
        dt = now - _prev_traffic_time
        if dt > 0:
            prev_rx, prev_tx = _prev_traffic[iface]
            result_rx = max(0, rx - prev_rx) / dt
            result_tx = max(0, tx - prev_tx) / dt
    _prev_traffic[iface] = (rx, tx)
    _prev_traffic_time = now
    return result_rx, result_tx


def get_tethering_clients():
    brif_path = f"/sys/class/net/{BRIDGE_NAME}/brif"
    if not os.path.isdir(brif_path):
        return 0, []
    try:
        interfaces = os.listdir(brif_path)
        arp_table = {}
        try:
            ok, out, _ = run_ok(["ip", "neigh", "show", "dev", BRIDGE_NAME])
            if ok and out:
                for line in out.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 3:
                        ip_addr = parts[0]
                        mac_addr = ""
                        for i, p in enumerate(parts):
                            if p == "lladdr" and i + 1 < len(parts):
                                mac_addr = parts[i + 1].lower()
                                break
                        if mac_addr and mac_addr != "00:00:00:00:00:00":
                            arp_table[mac_addr] = ip_addr
        except Exception:
            pass
        dhcp_leases = {}
        try:
            lease_file = os.path.join(DATA_DIR, "dnsmasq.log")
            if os.path.isfile(lease_file):
                with open(lease_file) as f:
                    for line in f:
                        if "DHCPACK" in line:
                            lparts = line.split()
                            for i, p in enumerate(lparts):
                                if p == "DHCPACK" and i + 2 < len(lparts):
                                    lease_mac = lparts[i + 1].lower()
                                    lease_ip = lparts[i + 2]
                                    dhcp_leases[lease_mac] = lease_ip
        except Exception:
            pass
        adapter_info = get_adapter_info()
        if not adapter_info:
            return 0, []
        bt_addr = adapter_info.get("address", "").lower().replace(":", "")
        bridge_rx_speed, bridge_tx_speed = _calc_traffic_speed(BRIDGE_NAME)
        clients = []
        seen_macs = set()
        for iface in interfaces:
            iface_mac = ""
            try:
                with open(f"/sys/class/net/{iface}/address") as f:
                    iface_mac = f.read().strip().lower()
            except OSError:
                pass
            iface_mac_clean = iface_mac.replace(":", "")
            if iface_mac_clean == bt_addr:
                for arp_mac, arp_ip in arp_table.items():
                    if arp_mac not in seen_macs:
                        seen_macs.add(arp_mac)
                        clients.append(
                            {
                                "interface": iface,
                                "mac": arp_mac,
                                "ip": arp_ip,
                                "rxSpeed": round(bridge_rx_speed),
                                "txSpeed": round(bridge_tx_speed),
                            }
                        )
                for lease_mac, lease_ip in dhcp_leases.items():
                    if lease_mac not in seen_macs:
                        seen_macs.add(lease_mac)
                        clients.append(
                            {
                                "interface": iface,
                                "mac": lease_mac,
                                "ip": lease_ip,
                                "rxSpeed": round(bridge_rx_speed),
                                "txSpeed": round(bridge_tx_speed),
                            }
                        )
                if not arp_table and not dhcp_leases:
                    clients.append(
                        {
                            "interface": iface,
                            "mac": "",
                            "ip": "",
                            "rxSpeed": round(bridge_rx_speed),
                            "txSpeed": round(bridge_tx_speed),
                        }
                    )
            else:
                iface_rx_speed, iface_tx_speed = _calc_traffic_speed(iface)
                client_ip = arp_table.get(iface_mac, "") or dhcp_leases.get(
                    iface_mac, ""
                )
                if iface_mac and iface_mac not in seen_macs:
                    seen_macs.add(iface_mac)
                    clients.append(
                        {
                            "interface": iface,
                            "mac": iface_mac,
                            "ip": client_ip,
                            "rxSpeed": round(iface_rx_speed),
                            "txSpeed": round(iface_tx_speed),
                        }
                    )
                elif iface_mac in seen_macs:
                    continue
                else:
                    clients.append(
                        {
                            "interface": iface,
                            "mac": "",
                            "ip": client_ip,
                            "rxSpeed": round(iface_rx_speed),
                            "txSpeed": round(iface_tx_speed),
                        }
                    )
        return len(interfaces), clients
    except OSError:
        return 0, []


def handle_tethering_status():
    active = is_tethering_active()
    clients_count, clients = get_tethering_clients() if active else (0, [])
    bridge_ip = BRIDGE_IP_DEFAULT
    if active and os.path.isfile(TETHER_STATE_FILE):
        st = load_shell_state(TETHER_STATE_FILE)
        bridge_ip = st.get("bridge_ip", BRIDGE_IP_DEFAULT)
    ok_response(
        {
            "active": active,
            "bridge": BRIDGE_NAME if active else "",
            "ip": bridge_ip if active else "",
            "clients": clients_count,
            "clientList": clients,
        }
    )


def ensure_nap_registered():
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        adapter_path = get_adapter_path()
        if not adapter_path:
            return False
        adapter = bus.get_object("org.bluez", adapter_path)
        nap = _dbus.Interface(adapter, "org.bluez.NetworkServer1")
        try:
            nap.Unregister("NAP")
        except Exception:
            pass
        nap.Register("NAP", BRIDGE_NAME)
        return True
    except Exception:
        return False


def handle_tethering_start():
    if is_tethering_active():
        ensure_nap_registered()
        ok_response({"message": "already active"})
        return
    if not command_exists("ip"):
        error_response("503 Service Unavailable", "ip command not found")
        return
    bridge_ip = first_form_value("bridge_ip") or BRIDGE_IP_DEFAULT
    parts = bridge_ip.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        subnet = ".".join(parts[:3])
        bridge_cidr = f"{bridge_ip}/24"
        dhcp_start = f"{subnet}.10"
        dhcp_end = f"{subnet}.50"
    else:
        bridge_ip = BRIDGE_IP_DEFAULT
        bridge_cidr = BRIDGE_CIDR_DEFAULT
        dhcp_start = DHCP_RANGE_START_DEFAULT
        dhcp_end = DHCP_RANGE_END_DEFAULT
    inet_iface = get_internet_interface()
    if command_exists("iptables"):
        for _ in range(5):
            rc, _, _ = run_cmd(
                ["iptables", "-D", "FORWARD", "-i", BRIDGE_NAME, "-j", "ACCEPT"],
                timeout=3,
            )
            if rc != 0:
                break
        for _ in range(5):
            rc, _, _ = run_cmd(
                [
                    "iptables",
                    "-D",
                    "FORWARD",
                    "-i",
                    BRIDGE_NAME,
                    "-o",
                    inet_iface,
                    "-j",
                    "ACCEPT",
                ],
                timeout=3,
            )
            if rc != 0:
                break
        for _ in range(5):
            rc, _, _ = run_cmd(
                [
                    "iptables",
                    "-D",
                    "FORWARD",
                    "-i",
                    inet_iface,
                    "-o",
                    BRIDGE_NAME,
                    "-m",
                    "state",
                    "--state",
                    "RELATED,ESTABLISHED",
                    "-j",
                    "ACCEPT",
                ],
                timeout=3,
            )
            if rc != 0:
                break
        for _ in range(5):
            rc, _, _ = run_cmd(
                [
                    "iptables",
                    "-t",
                    "nat",
                    "-D",
                    "POSTROUTING",
                    "-o",
                    inet_iface,
                    "-j",
                    "MASQUERADE",
                ],
                timeout=3,
            )
            if rc != 0:
                break
    run_cmd(["ip", "link", "add", "name", BRIDGE_NAME, "type", "bridge"], timeout=5)
    run_cmd(["ip", "addr", "add", bridge_cidr, "dev", BRIDGE_NAME], timeout=5)
    run_cmd(["ip", "link", "set", BRIDGE_NAME, "up"], timeout=5)
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write("1")
    except OSError:
        pass
    if command_exists("iptables"):
        run_cmd(
            [
                "iptables",
                "-I",
                "FORWARD",
                "-i",
                BRIDGE_NAME,
                "-o",
                inet_iface,
                "-j",
                "ACCEPT",
            ],
            timeout=5,
        )
        run_cmd(
            [
                "iptables",
                "-I",
                "FORWARD",
                "-i",
                inet_iface,
                "-o",
                BRIDGE_NAME,
                "-m",
                "state",
                "--state",
                "RELATED,ESTABLISHED",
                "-j",
                "ACCEPT",
            ],
            timeout=5,
        )
        run_cmd(
            ["iptables", "-I", "FORWARD", "-i", BRIDGE_NAME, "-j", "ACCEPT"], timeout=5
        )
        run_cmd(
            [
                "iptables",
                "-t",
                "nat",
                "-I",
                "POSTROUTING",
                "-o",
                inet_iface,
                "-j",
                "MASQUERADE",
            ],
            timeout=5,
        )
    if command_exists("systemctl"):
        run_cmd(["systemctl", "stop", "dnsmasq"], timeout=5)
        run_cmd(["systemctl", "mask", "dnsmasq"], timeout=5)
    elif command_exists("pkill"):
        run_cmd(["pkill", "dnsmasq"], timeout=5)
    time.sleep(0.5)
    if command_exists("dnsmasq"):
        dnsmasq_pid = os.path.join(DATA_DIR, "dnsmasq.pid")
        subprocess.Popen(
            [
                "dnsmasq",
                f"--interface={BRIDGE_NAME}",
                f"--dhcp-range={dhcp_start},{dhcp_end},12h",
                "--bind-dynamic",
                "--no-resolv",
                "--server=8.8.8.8",
                "--server=8.8.4.4",
                "--log-dhcp",
                f"--log-facility={os.path.join(DATA_DIR, 'dnsmasq.log')}",
                f"--pid-file={dnsmasq_pid}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)
    ensure_nap_registered()
    ensure_data_dir()
    with open(TETHER_STATE_FILE, "w") as f:
        f.write(f"inet_iface={shell_quote(inet_iface)}\n")
        f.write(f"bridge_ip={shell_quote(bridge_ip)}\n")
        f.write(f"bridge_cidr={shell_quote(bridge_cidr)}\n")
        f.write(f"dhcp_start={shell_quote(dhcp_start)}\n")
        f.write(f"dhcp_end={shell_quote(dhcp_end)}\n")
    ok_response()


def handle_tethering_stop():
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        adapter_path = get_adapter_path()
        if adapter_path:
            adapter = bus.get_object("org.bluez", adapter_path)
            nap = _dbus.Interface(adapter, "org.bluez.NetworkServer1")
            nap.Unregister("NAP")
    except Exception:
        pass
    if command_exists("pkill"):
        run_cmd(["pkill", "-f", f"dnsmasq.*{BRIDGE_NAME}"], timeout=5)
    inet_iface = "eth0"
    if os.path.isfile(TETHER_STATE_FILE):
        state = load_shell_state(TETHER_STATE_FILE)
        inet_iface = state.get("inet_iface", "eth0")
    if command_exists("iptables"):
        run_cmd(
            [
                "iptables",
                "-D",
                "FORWARD",
                "-i",
                BRIDGE_NAME,
                "-o",
                inet_iface,
                "-j",
                "ACCEPT",
            ],
            timeout=5,
        )
        run_cmd(
            [
                "iptables",
                "-D",
                "FORWARD",
                "-i",
                inet_iface,
                "-o",
                BRIDGE_NAME,
                "-m",
                "state",
                "--state",
                "RELATED,ESTABLISHED",
                "-j",
                "ACCEPT",
            ],
            timeout=5,
        )
        run_cmd(
            ["iptables", "-D", "FORWARD", "-i", BRIDGE_NAME, "-j", "ACCEPT"], timeout=5
        )
        run_cmd(
            [
                "iptables",
                "-t",
                "nat",
                "-D",
                "POSTROUTING",
                "-o",
                inet_iface,
                "-j",
                "MASQUERADE",
            ],
            timeout=5,
        )
    if is_tethering_active():
        run_cmd(["ip", "link", "set", BRIDGE_NAME, "down"], timeout=5)
        run_cmd(["ip", "addr", "flush", "dev", BRIDGE_NAME], timeout=5)
        run_cmd(["ip", "link", "delete", BRIDGE_NAME], timeout=5)
    if os.path.isfile(TETHER_STATE_FILE):
        os.remove(TETHER_STATE_FILE)
    if command_exists("systemctl"):
        run_cmd(["systemctl", "unmask", "dnsmasq"], timeout=5)
        run_cmd(["systemctl", "start", "dnsmasq"], timeout=5)
    ok_response()


def handle_tethering_stop_silent():
    try:
        import dbus as _dbus  # pyright: ignore[reportMissingImports]

        bus = _dbus.SystemBus()
        adapter_path = get_adapter_path()
        if adapter_path:
            adapter = bus.get_object("org.bluez", adapter_path)
            nap = _dbus.Interface(adapter, "org.bluez.NetworkServer1")
            nap.Unregister("NAP")
    except Exception:
        pass
    if command_exists("pkill"):
        run_cmd(["pkill", "-f", f"dnsmasq.*{BRIDGE_NAME}"], timeout=5)
    inet_iface = "eth0"
    if os.path.isfile(TETHER_STATE_FILE):
        state = load_shell_state(TETHER_STATE_FILE)
        inet_iface = state.get("inet_iface", "eth0")
    if command_exists("iptables"):
        run_cmd(
            [
                "iptables",
                "-D",
                "FORWARD",
                "-i",
                BRIDGE_NAME,
                "-o",
                inet_iface,
                "-j",
                "ACCEPT",
            ],
            timeout=5,
        )
        run_cmd(
            [
                "iptables",
                "-D",
                "FORWARD",
                "-i",
                inet_iface,
                "-o",
                BRIDGE_NAME,
                "-m",
                "state",
                "--state",
                "RELATED,ESTABLISHED",
                "-j",
                "ACCEPT",
            ],
            timeout=5,
        )
        run_cmd(
            ["iptables", "-D", "FORWARD", "-i", BRIDGE_NAME, "-j", "ACCEPT"], timeout=5
        )
        run_cmd(
            [
                "iptables",
                "-t",
                "nat",
                "-D",
                "POSTROUTING",
                "-o",
                inet_iface,
                "-j",
                "MASQUERADE",
            ],
            timeout=5,
        )
    if is_tethering_active():
        run_cmd(["ip", "link", "set", BRIDGE_NAME, "down"], timeout=5)
        run_cmd(["ip", "addr", "flush", "dev", BRIDGE_NAME], timeout=5)
        run_cmd(["ip", "link", "delete", BRIDGE_NAME], timeout=5)
    if os.path.isfile(TETHER_STATE_FILE):
        os.remove(TETHER_STATE_FILE)
    if command_exists("systemctl"):
        run_cmd(["systemctl", "unmask", "dnsmasq"], timeout=5)
        run_cmd(["systemctl", "start", "dnsmasq"], timeout=5)


ACTIONS = {
    "adapter_info": handle_adapter_info,
    "adapter_power": handle_adapter_power,
    "adapter_discoverable": handle_adapter_discoverable,
    "adapter_pairable": handle_adapter_pairable,
    "scan_start": handle_scan_start,
    "scan_stop": handle_scan_stop,
    "devices": handle_devices,
    "device_info": handle_device_info,
    "pair": handle_pair,
    "connect": handle_connect,
    "disconnect": handle_disconnect,
    "remove": handle_remove,
    "trust": handle_trust,
    "untrust": handle_untrust,
    "audio_status": handle_audio_status,
    "audio_connect": handle_audio_connect,
    "audio_disconnect": handle_audio_disconnect,
    "audio_sink_set": handle_audio_sink_set,
    "audio_source_set": handle_audio_source_set,
    "send_file": handle_send_file,
    "transfer_progress": handle_transfer_progress,
    "transfer_history": handle_transfer_history,
    "clear_transfer_history": handle_clear_transfer_history,
    "received_files": handle_received_files,
    "delete_received": handle_delete_received,
    "clear_received": handle_clear_received,
    "role_get": handle_role_get,
    "role_set": handle_role_set,
    "server_advertise": handle_server_advertise,
    "server_alias": handle_server_alias,
    "server_profiles": handle_server_profiles,
    "server_accept": handle_server_accept,
    "incoming_devices": handle_incoming_devices,
    "status": handle_status,
    "tethering_status": handle_tethering_status,
    "tethering_start": handle_tethering_start,
    "tethering_stop": handle_tethering_stop,
}


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


def parse_request_body(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b""
    if not raw:
        return {}
    text = raw.decode("utf-8", "replace")
    content_type = handler.headers.get("Content-Type", "")
    if "application/json" in content_type:
        payload = json.loads(text or "{}")
        return {
            key: ["" if value is None else str(value)] for key, value in payload.items()
        }
    return parse_qs(text, keep_blank_values=True)


def merge_query_action(path, query):
    parsed = parse_qs(query or "", keep_blank_values=True)
    if "action" not in parsed:
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "api":
            parsed["action"] = [parts[1]]
    return parsed


def dispatch_api(handler, api_path, query):
    request = current_request()
    try:
        REQUEST_CONTEXT.value = {
            "handler": handler,
            "body": parse_request_body(handler),
            "query": merge_query_action(api_path, query),
        }
        action = first_query_value("action")
        if action.endswith(".cgi"):
            action = action[:-4]
        if not action:
            error_response("400 Bad Request", "missing action")
        handler_fn = ACTIONS.get(action)
        if not handler_fn:
            error_response("404 Not Found", f"unknown action: {action}")
        else:
            handler_fn()
    except ResponseDone:
        return
    except Exception as exc:
        try:
            error_response(
                "500 Internal Server Error",
                f"unexpected error (step={CURRENT_STEP}): {exc}",
            )
        except ResponseDone:
            return
    finally:
        if request == {}:
            if hasattr(REQUEST_CONTEXT, "value"):
                del REQUEST_CONTEXT.value
        else:
            REQUEST_CONTEXT.value = request


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

    def log_message(self, format, *args):
        sys.stdout.write(
            "%s - - [%s] %s\n"
            % (self.client_address, self.log_date_time_string(), format % args)
        )
        sys.stdout.flush()

    def route(self):
        parsed = urlsplit(self.path)
        if parsed.path == self.server.base_path:
            location = self.server.base_path + "/"
            if parsed.query:
                location += "?" + parsed.query
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        path = strip_base_path(parsed.path, self.server.base_path)
        if path == "/api" or path.startswith("/api/"):
            dispatch_api(self, path, parsed.query)
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
        data_size = target.stat().st_size
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(data_size))
        self.send_header(
            "Cache-Control",
            (
                "no-store"
                if target.name in {"index.html", "app.js", "style.css"}
                else "public, max-age=3600"
            ),
        )
        self.end_headers()
        if self.command == "HEAD":
            return
        with target.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 256)
                if not chunk:
                    break
                self.wfile.write(chunk)


def stop_agent():
    kill_agent_processes()
    if os.path.isfile(AGENT_PID_FILE):
        try:
            os.remove(AGENT_PID_FILE)
        except OSError:
            pass


def start_bluetooth_service():
    if command_exists("systemctl"):
        run_cmd(["systemctl", "start", "bluetooth"], timeout=10)


def stop_bluetooth_service():
    if command_exists("systemctl"):
        run_cmd(["systemctl", "stop", "bluetooth"], timeout=10)


def cleanup():
    stop_scan_process()
    stop_agent()
    kill_btctl_processes()
    stop_obex_server()
    if is_tethering_active():
        handle_tethering_stop_silent()


def main():
    global DATA_DIR, CFG_FILE
    parser = argparse.ArgumentParser(description="fn-bluetooth Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-bluetooth")
    parser.add_argument("--www-root", required=True)
    parser.add_argument("--data-dir", default=DATA_DIR)
    args = parser.parse_args()

    DATA_DIR = args.data_dir
    CFG_FILE = os.path.join(DATA_DIR, "bluetooth.env")
    ensure_data_dir()

    if not command_exists("bluetoothctl"):
        start_bluetooth_service()

    if os.path.exists(args.unix_socket):
        os.unlink(args.unix_socket)
    server = ThreadingUnixHTTPServer(
        args.unix_socket, Handler, base_path=args.base_path, www_root=args.www_root
    )

    ensure_obex_server()
    ensure_agent()
    if is_tethering_active() or os.path.isfile(TETHER_STATE_FILE):
        ensure_nap_registered()
    _start_receive_monitor()

    def shutdown(_signum, _frame):
        cleanup()
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        server.serve_forever()
    finally:
        cleanup()
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)


if __name__ == "__main__":
    main()
