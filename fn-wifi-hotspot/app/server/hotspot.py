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
import shlex
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from contextlib import contextmanager
from ipaddress import IPv4Interface, ip_address
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.parse import parse_qs


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-wifi-hotspot")

_pkgvar = _env("TRIM_PKGVAR")
DATA_DIR = Path(_pkgvar) if _pkgvar else Path(f"/var/apps/{APP_NAME}/var")

CFG_FILE = DATA_DIR / "hotspot.env"
RUNTIME_STATE_FILE = DATA_DIR / "runtime.state"
DNSMASQ_CONF_FILE = DATA_DIR / "hotspot-dnsmasq.conf"
DNSMASQ_PID_FILE = DATA_DIR / "hotspot-dnsmasq.pid"
DNSMASQ_LEASE_FILE = DATA_DIR / "hotspot-dnsmasq.leases"

DEFAULTS = {
    "IFACE": "",
    "UPLINK_IFACE": "",
    "IP_CIDR": "192.168.12.1/24",
    "ALLOW_PORTS": "80,443,5666,5667,67-68/udp",
    "SSID": "fn-hotspot",
    "PASSWORD": "12345678",
    "COUNTRY": "",
    "BAND": "bg",
    "CHANNEL": "6",
    "CHANNEL_WIDTH": "20",
}

CONFIG_KEYS = [
    "IFACE",
    "UPLINK_IFACE",
    "IP_CIDR",
    "ALLOW_PORTS",
    "SSID",
    "PASSWORD",
    "COUNTRY",
    "BAND",
    "CHANNEL",
    "CHANNEL_WIDTH",
]

CURRENT_STEP = "init"
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
        self.server_name = "fn-wifi-hotspot"
        self.server_port = 0
        self.base_path = normalize_base_path(base_path)
        self.www_root = Path(www_root)
        super().__init__(socket_path, handler_cls)  # pyright: ignore[reportCallIssue]


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def command_exists(name):
    return shutil.which(name) is not None


def run_cmd(args, timeout=None, input_text=None):
    try:
        proc = subprocess.run(
            args,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", f"{args[0]} not found"
    except Exception as exc:
        return 1, "", str(exc)


def run_ok(args, timeout=None, input_text=None):
    rc, stdout, stderr = run_cmd(args, timeout=timeout, input_text=input_text)
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


def header_value(headers, name):
    if not headers:
        return ""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


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
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            if handler.command != "HEAD":
                handler.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # client disconnected mid-response; treat as normal
            return
        raise ResponseDone()
    sys.stdout.write(f"Status: {status_text}\r\n")
    sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
    sys.stdout.write("Cache-Control: no-store\r\n\r\n")
    sys.stdout.write(body.decode("utf-8"))
    sys.stdout.write("\n")
    raise SystemExit(0)


def err(code, status="400 Bad Request", **params):
    """错误响应统一为 {ok:false, code, params?}，前端按 code 映射多语言文案。"""
    payload = {"ok": False, "code": code}
    if params:
        payload["params"] = {
            key: value for key, value in params.items() if value not in (None, "")
        }
    json_response(payload, status)


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
            parsed = parse_qs(raw, keep_blank_values=True)
            return {key: values[-1] for key, values in parsed.items()}
        parsed = parse_qs(query_string, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    if method in {"POST", "PUT", "PATCH"}:
        length = int(os.environ.get("CONTENT_LENGTH") or 0)
        raw = sys.stdin.buffer.read(length).decode("utf-8", "replace") if length else ""
        content_type = os.environ.get("CONTENT_TYPE", "")
        if "application/json" in content_type:
            return json.loads(raw or "{}")
        parsed = parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}
    parsed = parse_qs(os.environ.get("QUERY_STRING", ""), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def first_value(name):
    payload = request_body()
    if isinstance(payload, dict):
        return payload.get(name, "")
    return ""


def sanitize_text(text):
    text = text or ""
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", text)
    return text.replace("\r", "")


def normalize_country(value):
    return trim(value).upper()


def normalize_parent_wifi_iface(iface):
    iface = trim(iface)
    if not iface or not command_exists("iw"):
        return iface
    current = iface
    while current.endswith("ap") and len(current) > 2:
        candidate = current[:-2]
        ok, _, _ = run_ok(["iw", "dev", candidate, "info"])
        if not ok:
            break
        current = candidate
    return current


def is_iface_name(value):
    return bool(re.fullmatch(r"[a-zA-Z0-9_.:-]{1,64}", value or ""))


def is_ipv4_cidr(value):
    try:
        IPv4Interface(value)
        return True
    except Exception:
        return False


def allow_ports_to_rules(spec):
    spec = trim(spec)
    rules = []
    if not spec:
        return rules
    for token in spec.split(","):
        token = trim(token)
        if not token:
            continue
        proto = "tcp"
        port_part = token
        if "/" in token:
            port_part, proto = token.rsplit("/", 1)
            proto = trim(proto).lower()
        if proto not in {"tcp", "udp"}:
            raise ValueError(
                f"allowPorts: protocol must be tcp or udp (token: {token})"
            )
        port_part = trim(port_part)
        if not port_part:
            raise ValueError(f"allowPorts: missing port (token: {token})")
        if "-" in port_part:
            start_s, end_s = [trim(part) for part in port_part.split("-", 1)]
        else:
            start_s = end_s = port_part
        if not start_s.isdigit() or not end_s.isdigit():
            raise ValueError(f"allowPorts: port must be number (token: {token})")
        start = int(start_s)
        end = int(end_s)
        if start < 1 or end < 1 or start > 65535 or end > 65535:
            raise ValueError(f"allowPorts: port out of range 1-65535 (token: {token})")
        if start > end:
            raise ValueError(f"allowPorts: invalid range start>end (token: {token})")
        rules.append((proto, start, end))
    return rules


def load_cfg():
    cfg = dict(DEFAULTS)
    stored = load_shell_state(CFG_FILE)
    for key in CONFIG_KEYS:
        if key in stored:
            cfg[key] = stored[key]
    cfg["IFACE"] = normalize_parent_wifi_iface(cfg["IFACE"])
    return cfg


def save_cfg(cfg):
    mapping = {
        "IFACE": normalize_parent_wifi_iface(cfg.get("IFACE", "")),
        "UPLINK_IFACE": cfg.get("UPLINK_IFACE", ""),
        "IP_CIDR": cfg.get("IP_CIDR", ""),
        "ALLOW_PORTS": cfg.get("ALLOW_PORTS", ""),
        "SSID": cfg.get("SSID", ""),
        "PASSWORD": cfg.get("PASSWORD", ""),
        "COUNTRY": normalize_country(cfg.get("COUNTRY", "")),
        "BAND": cfg.get("BAND", ""),
        "CHANNEL": cfg.get("CHANNEL", ""),
        "CHANNEL_WIDTH": cfg.get("CHANNEL_WIDTH", ""),
    }
    try:
        write_shell_state(CFG_FILE, mapping)
        return True
    except OSError:
        return False


def wifi_ifaces():
    values = []
    if command_exists("nmcli"):
        ok, stdout, _ = run_ok(["nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"])
        if ok:
            for line in stdout.splitlines():
                if not line:
                    continue
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                dev, dev_type = parts
                if dev_type == "wifi-p2p":
                    continue
                if dev_type == "wifi" or "wireless" in dev_type:
                    values.append(normalize_parent_wifi_iface(dev))
            return list(dict.fromkeys([value for value in values if value]))
    if command_exists("iw"):
        ok, stdout, _ = run_ok(["iw", "dev"])
        if ok:
            for line in stdout.splitlines():
                match = re.match(r"\s*Interface\s+(\S+)", line)
                if match:
                    dev = match.group(1)
                    if not dev.startswith("p2p-") and not dev.startswith("p2p-dev-"):
                        values.append(normalize_parent_wifi_iface(dev))
    return list(dict.fromkeys([value for value in values if value]))


def iface_is_wifi(device):
    if not device:
        return False
    if not command_exists("nmcli"):
        return True
    ok, stdout, _ = run_ok(["nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"])
    if not ok:
        return False
    for line in stdout.splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2 or parts[0] != device:
            continue
        if parts[1] == "wifi-p2p":
            return False
        return parts[1] == "wifi" or "wireless" in parts[1]
    return False


def ensure_iface(cfg):
    iface = normalize_parent_wifi_iface(cfg.get("IFACE", ""))
    if not iface:
        candidates = [dev for dev in wifi_ifaces() if not dev.startswith("p2p")]
        if not candidates:
            candidates = wifi_ifaces()
        iface = candidates[0] if candidates else ""
    cfg["IFACE"] = normalize_parent_wifi_iface(iface)
    return cfg["IFACE"]


def require_wifi_iface(cfg):
    iface = ensure_iface(cfg)
    if not iface:
        return 2
    return 0 if iface_is_wifi(iface) else 1


def iw_reg_country():
    if not command_exists("iw"):
        return ""
    ok, stdout, _ = run_ok(["iw", "reg", "get"])
    if not ok:
        return ""
    for line in stdout.splitlines():
        match = re.match(r"^country\s+([A-Za-z0-9]{2}):", line)
        if match:
            return match.group(1)
    return ""


def iw_channels_for_band(band):
    if not command_exists("iw"):
        return []
    ok, stdout, _ = run_ok(["iw", "list"])
    if not ok:
        return []
    band_pat = "Band 1:" if band in {"bg", "2.4g", "2g"} else "Band 2:"
    in_band = False
    channels = []
    for line in stdout.splitlines():
        if re.match(rf"^\s*{re.escape(band_pat)}", line):
            in_band = True
            continue
        if in_band and re.match(r"^\s*Band", line):
            in_band = False
        if not in_band:
            continue
        match = re.match(r"^\s*\*?\s*([0-9]+) MHz \[([0-9]+)\](.*)$", line)
        if not match:
            continue
        freq, channel, tail = match.groups()
        state = "disabled" if ("disabled" in tail or "no IR" in tail) else "supported"
        channels.append(f"{channel}:{freq}:{state}")
    return channels


def iw_channel_line(channel):
    if not channel or not command_exists("iw"):
        return ""
    ok, stdout, _ = run_ok(["iw", "list"])
    if not ok:
        return ""
    for line in stdout.splitlines():
        if re.match(rf"^\s*\*\s+[0-9]+ MHz \[{re.escape(str(channel))}\].*$", line):
            return line.strip()
    return ""


def validate_runtime_channel(cfg):
    line = iw_channel_line(cfg.get("CHANNEL", ""))
    if not line:
        return None
    regdom = iw_reg_country()
    channel = cfg.get("CHANNEL", "")
    if "disabled" in line:
        return {"code": "channel_disabled", "channel": channel, "regdom": regdom}
    if "no IR" in line:
        return {"code": "channel_no_ir", "channel": channel, "regdom": regdom}
    return None


def apply_regdom(country):
    country = normalize_country(country)
    if not country:
        return True
    if not command_exists("iw"):
        return False
    ok, _, _ = run_ok(["iw", "reg", "set", country])
    return ok


def is_regdom_changeable():
    """探测当前系统能否修改国家码（regdom）。若能生效则视为可修改，否则视为锁定。"""
    if not command_exists("iw"):
        return False
    original = iw_reg_country()
    probe = "US" if original not in {"US", ""} else "JP"
    if not apply_regdom(probe):
        return False
    changed = iw_reg_country()
    if original in ("", "00"):
        apply_regdom("00")
    else:
        apply_regdom(original)
    return bool(changed) and changed == probe


def wifi_driver_name(device):
    if not device or not command_exists("ethtool"):
        return ""
    ok, stdout, _ = run_ok(["ethtool", "-i", device])
    if not ok:
        return ""
    for line in stdout.splitlines():
        if line.startswith("driver:"):
            return trim(line.split(":", 1)[1])
    return ""


def wifi_txpower_dbm(device):
    if not device or not command_exists("iw"):
        return ""
    ok, stdout, _ = run_ok(["iw", "dev", device, "info"])
    if not ok:
        return ""
    match = re.search(r"txpower\s+([0-9.]+)\s+dBm", stdout)
    return match.group(1) if match else ""


def wifi_txpower_is_suspiciously_low(device):
    tx_power = wifi_txpower_dbm(device)
    if not tx_power:
        return False
    try:
        return float(tx_power) <= 3.5
    except ValueError:
        return False


def wifi_low_power_info(device):
    driver = wifi_driver_name(device) or "unknown"
    tx_power = wifi_txpower_dbm(device) or "unknown"
    if driver == "mt7921e" and wifi_txpower_is_suspiciously_low(device):
        return {"driver": driver, "txPower": tx_power}
    return None


def wifi_low_power_notice(device):
    info = wifi_low_power_info(device)
    if not info:
        return ""
    return (
        f"Warning: driver '{info['driver']}' is reporting very low transmit power ({info['txPower']} dBm). "
        "Hotspot can start, but discovery/range may be poor. Try 2.4GHz/20MHz first; "
        "if coverage is still weak, this points to an mt7921e driver/firmware power issue rather than hotspot setup."
    )


def detect_route_dev(target="1.1.1.1"):
    if not command_exists("ip"):
        return ""
    ok, stdout, _ = run_ok(["ip", "-4", "route", "get", target])
    if not ok:
        return ""
    parts = stdout.split()
    for idx, token in enumerate(parts):
        if token == "dev" and idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def load_runtime_state():
    return load_shell_state(RUNTIME_STATE_FILE)


def write_runtime_state(**fields):
    data = {key: value for key, value in fields.items() if trim(value) != ""}
    merged = dict(load_runtime_state())
    merged.update(data)
    if not merged:
        try:
            os.remove(RUNTIME_STATE_FILE)
        except FileNotFoundError:
            pass
        return
    write_shell_state(RUNTIME_STATE_FILE, merged)


def write_nat_state(hotspot_iface, uplink_iface, parent_iface="", virtual_iface=""):
    write_runtime_state(
        HOTSPOT_IFACE=hotspot_iface,
        NAT_UPLINK_IFACE=uplink_iface,
        HOTSPOT_PARENT_IFACE=parent_iface,
        HOTSPOT_VIRTUAL_IFACE=virtual_iface,
    )


def load_nat_state():
    data = load_runtime_state()
    return {
        "HOTSPOT_IFACE": data.get("HOTSPOT_IFACE", ""),
        "NAT_UPLINK_IFACE": data.get("NAT_UPLINK_IFACE", ""),
        "HOTSPOT_PARENT_IFACE": data.get("HOTSPOT_PARENT_IFACE", ""),
        "HOTSPOT_VIRTUAL_IFACE": data.get("HOTSPOT_VIRTUAL_IFACE", ""),
    }


def clear_nat_state():
    write_runtime_state(
        HOTSPOT_IFACE="",
        NAT_UPLINK_IFACE="",
        HOTSPOT_PARENT_IFACE="",
        HOTSPOT_VIRTUAL_IFACE="",
    )


def encode_rules(rules):
    tokens = []
    for proto, start, end in rules:
        tokens.append(f"{proto}:{start}" if start == end else f"{proto}:{start}-{end}")
    return ",".join(tokens)


def decode_rules(text):
    rules = []
    for token in (trim(text) or "").split(","):
        token = trim(token)
        if not token or ":" not in token:
            continue
        proto, _, range_part = token.partition(":")
        proto = trim(proto).lower()
        if proto not in {"tcp", "udp"}:
            continue
        start_s, _, end_s = [trim(part) for part in range_part.partition("-")]
        if not end_s:
            end_s = start_s
        if not start_s.isdigit() or not end_s.isdigit():
            continue
        start, end = int(start_s), int(end_s)
        if start < 1 or end > 65535 or start > end:
            continue
        rules.append((proto, start, end))
    return rules


def effective_ip_cidr(cfg):
    return trim(cfg.get("IP_CIDR", "")) or DEFAULTS["IP_CIDR"]


def hotspot_lan_details(cidr):
    try:
        iface = IPv4Interface(cidr)
    except Exception:
        return None
    network = iface.network
    gateway = int(iface.ip)
    first = int(network.network_address) + 1
    last = int(network.broadcast_address) - 1
    if last < first:
        return None
    start = max(first, int(network.network_address) + 10)
    if start == gateway:
        start += 1
    if start > last:
        start = first
        if start == gateway:
            start += 1
    end = last
    if end == gateway:
        end -= 1
    if start > end:
        return None
    return {
        "cidr": str(iface),
        "gateway": str(iface.ip),
        "netmask": str(network.netmask),
        "start": str(type(iface.ip)(start)),
        "end": str(type(iface.ip)(end)),
    }


def system_nameservers():
    values = []
    for line in read_text("/etc/resolv.conf").splitlines():
        match = re.match(r"^nameserver\s+(\S+)", line.strip())
        if match:
            candidate = match.group(1)
            try:
                if ip_address(candidate).version == 4:
                    values.append(candidate)
            except ValueError:
                continue
    return list(dict.fromkeys(values))


def read_pid_file(path):
    raw = trim(read_text(path))
    return int(raw) if raw.isdigit() else 0


def stop_local_dnsmasq():
    pid = read_pid_file(DNSMASQ_PID_FILE)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            pass
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            except OSError:
                break
            time.sleep(0.1)
    for path in (DNSMASQ_PID_FILE, DNSMASQ_CONF_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def write_local_dnsmasq_config(hotspot_iface, cfg):
    details = hotspot_lan_details(effective_ip_cidr(cfg))
    if not details:
        raise ValueError("ipCidr: invalid IPv4 CIDR (e.g. 192.168.12.1/24)")
    resolvers = system_nameservers()
    lines = [
        "port=0",
        "bind-interfaces",
        "except-interface=lo",
        "dhcp-authoritative",
        f"interface={hotspot_iface}",
        f"listen-address={details['gateway']}",
        f"dhcp-range={details['start']},{details['end']},{details['netmask']},1h",
        f"dhcp-option=option:router,{details['gateway']}",
        f"pid-file={DNSMASQ_PID_FILE}",
        f"dhcp-leasefile={DNSMASQ_LEASE_FILE}",
    ]
    if resolvers:
        lines.append(f"dhcp-option=option:dns-server,{','.join(resolvers)}")
    ensure_data_dir()
    with open(DNSMASQ_CONF_FILE, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return details


def start_local_dnsmasq(hotspot_iface, cfg):
    if not command_exists("dnsmasq"):
        return False, "dnsmasq not found"
    stop_local_dnsmasq()
    try:
        write_local_dnsmasq_config(hotspot_iface, cfg)
    except ValueError as exc:
        return False, str(exc)
    except OSError as exc:
        return False, f"dnsmasq config write failed: {exc}"
    ok, stdout, stderr = run_ok(
        ["dnsmasq", "--test", f"--conf-file={DNSMASQ_CONF_FILE}"]
    )
    if not ok:
        return False, f"dnsmasq failed to start: {sanitize_text(stderr or stdout)}"
    ok, stdout, stderr = run_ok(["dnsmasq", f"--conf-file={DNSMASQ_CONF_FILE}"])
    if not ok:
        return False, f"dnsmasq failed to start: {sanitize_text(stderr or stdout)}"
    return True, ""


def iptables_allow_port(iface, proto, start, end):
    if not iface or not command_exists("iptables"):
        return
    dport = str(start) if start == end else f"{start}:{end}"
    check_cmd = [
        "iptables",
        "-C",
        "INPUT",
        "-i",
        iface,
        "-p",
        proto,
        "--dport",
        dport,
        "-m",
        "comment",
        "--comment",
        "fn-hotspot-allow",
        "-j",
        "ACCEPT",
    ]
    add_cmd = [
        "iptables",
        "-A",
        "INPUT",
        "-i",
        iface,
        "-p",
        proto,
        "--dport",
        dport,
        "-m",
        "comment",
        "--comment",
        "fn-hotspot-allow",
        "-j",
        "ACCEPT",
    ]
    ok, _, _ = run_ok(check_cmd)
    if not ok:
        run_cmd(add_cmd)


def iptables_remove_port(iface, proto, start, end):
    if not iface or not command_exists("iptables"):
        return
    dport = str(start) if start == end else f"{start}:{end}"
    run_cmd(
        [
            "iptables",
            "-D",
            "INPUT",
            "-i",
            iface,
            "-p",
            proto,
            "--dport",
            dport,
            "-m",
            "comment",
            "--comment",
            "fn-hotspot-allow",
            "-j",
            "ACCEPT",
        ]
    )


def load_ports_state():
    data = load_runtime_state()
    return data.get("PORTS_IFACE", ""), decode_rules(data.get("PORTS_RULES", ""))


def write_ports_state(iface, rules):
    write_runtime_state(PORTS_IFACE=iface, PORTS_RULES=encode_rules(rules))


def remove_allow_ports():
    iface, rules = load_ports_state()
    for proto, start, end in rules:
        iptables_remove_port(iface, proto, start, end)
    write_runtime_state(PORTS_IFACE="", PORTS_RULES="")


def apply_allow_ports(hotspot_iface, spec):
    if not hotspot_iface:
        return
    remove_allow_ports()
    rules = allow_ports_to_rules(spec)
    if not rules:
        write_ports_state(hotspot_iface, [])
        return
    for proto, start, end in rules:
        iptables_allow_port(hotspot_iface, proto, start, end)
    write_ports_state(hotspot_iface, rules)


def ensure_ip_forward():
    if command_exists("sysctl"):
        run_cmd(["sysctl", "-w", "net.ipv4.ip_forward=1"])


def iptables_apply_nat(hotspot, uplink):
    if not hotspot or not uplink or not command_exists("iptables"):
        return
    checks = [
        (
            [
                "iptables",
                "-t",
                "nat",
                "-C",
                "POSTROUTING",
                "-o",
                uplink,
                "-j",
                "MASQUERADE",
            ],
            [
                "iptables",
                "-t",
                "nat",
                "-A",
                "POSTROUTING",
                "-o",
                uplink,
                "-j",
                "MASQUERADE",
            ],
        ),
        (
            ["iptables", "-C", "FORWARD", "-i", hotspot, "-o", uplink, "-j", "ACCEPT"],
            ["iptables", "-A", "FORWARD", "-i", hotspot, "-o", uplink, "-j", "ACCEPT"],
        ),
        (
            ["iptables", "-C", "FORWARD", "-i", uplink, "-o", hotspot, "-j", "ACCEPT"],
            ["iptables", "-A", "FORWARD", "-i", uplink, "-o", hotspot, "-j", "ACCEPT"],
        ),
    ]
    for check_cmd, add_cmd in checks:
        ok, _, _ = run_ok(check_cmd)
        if not ok:
            run_cmd(add_cmd)


def iptables_remove_nat(hotspot, uplink):
    if not hotspot or not uplink or not command_exists("iptables"):
        return
    run_cmd(
        ["iptables", "-t", "nat", "-D", "POSTROUTING", "-o", uplink, "-j", "MASQUERADE"]
    )
    run_cmd(["iptables", "-D", "FORWARD", "-i", hotspot, "-o", uplink, "-j", "ACCEPT"])
    run_cmd(["iptables", "-D", "FORWARD", "-i", uplink, "-o", hotspot, "-j", "ACCEPT"])


def apply_hotspot_nat(hotspot, uplink, parent_iface="", virtual_iface=""):
    if not hotspot:
        return
    if not uplink:
        uplink = detect_route_dev("1.1.1.1")
    write_nat_state(hotspot, uplink or "", parent_iface or "", virtual_iface or "")
    if not uplink:
        return
    ensure_ip_forward()
    iptables_apply_nat(hotspot, uplink)


def remove_hotspot_nat():
    state = load_nat_state()
    if state["HOTSPOT_IFACE"] and state["NAT_UPLINK_IFACE"]:
        iptables_remove_nat(state["HOTSPOT_IFACE"], state["NAT_UPLINK_IFACE"])
    clear_nat_state()


def iw_supports_sta_ap():
    if not command_exists("iw"):
        return False
    ok, stdout, _ = run_ok(["iw", "list"])
    if not ok:
        return False
    in_section = False
    for line in stdout.splitlines():
        if "valid interface combinations" in line:
            in_section = True
            continue
        if in_section and line and not line.startswith((" ", "\t")):
            in_section = False
        if (
            in_section
            and line.lstrip().startswith("*")
            and "managed" in line
            and re.search(r"(^|\s)AP(\s|$)", line)
        ):
            return True
    return False


def mk_ap_iface_name(base):
    base = trim(base)
    suffix = "ap"
    if len(base + suffix) <= 15:
        return base + suffix
    prefix_len = max(1, 15 - len(suffix))
    return base[:prefix_len] + suffix


def ensure_virtual_ap_iface(parent, ap_iface):
    if not parent or not ap_iface or not command_exists("iw"):
        return False
    ok, _, _ = run_ok(["iw", "dev", ap_iface, "info"])
    if ok:
        return True
    ok, _, _ = run_ok(
        ["iw", "dev", parent, "interface", "add", ap_iface, "type", "__ap"]
    )
    if not ok:
        return False
    if command_exists("ip"):
        run_cmd(["ip", "link", "set", ap_iface, "up"])
    if command_exists("nmcli"):
        run_cmd(["nmcli", "dev", "set", ap_iface, "managed", "yes"])
    return True


def delete_virtual_ap_iface(iface):
    if not iface or not command_exists("iw"):
        return
    ok, _, _ = run_ok(["iw", "dev", iface, "info"])
    if not ok:
        return
    if command_exists("nmcli"):
        run_cmd(["nmcli", "dev", "set", iface, "managed", "no"])
    if command_exists("ip"):
        run_cmd(["ip", "link", "set", iface, "down"])
    run_cmd(["iw", "dev", iface, "del"])


def validate_cfg(cfg):
    """后端兜底校验，返回第一个出错的 field 名（前端已做主校验）。"""
    uplink = cfg.get("UPLINK_IFACE", "")
    ip_cidr = cfg.get("IP_CIDR", "")
    allow_ports = cfg.get("ALLOW_PORTS", "")
    ssid = cfg.get("SSID", "")
    password = cfg.get("PASSWORD", "")
    country = normalize_country(cfg.get("COUNTRY", ""))
    band = cfg.get("BAND", "")
    channel = str(cfg.get("CHANNEL", ""))
    channel_width = str(cfg.get("CHANNEL_WIDTH", ""))
    if uplink and not is_iface_name(uplink):
        return "uplinkIface"
    if ip_cidr and not is_ipv4_cidr(ip_cidr):
        return "ipCidr"
    if allow_ports:
        try:
            allow_ports_to_rules(allow_ports)
        except ValueError:
            return "allowPorts"
    if not ssid:
        return "ssid"
    if len(password) < 8:
        return "password"
    if country and country != "00" and not re.fullmatch(r"[A-Z]{2}", country):
        return "country"
    if band not in {"bg", "a"}:
        return "band"
    if not channel.isdigit():
        return "channel"
    channel_num = int(channel)
    if band == "bg" and not (1 <= channel_num <= 14):
        return "channel"
    if band == "a" and channel_num < 34:
        return "channel"
    if channel_width not in {"20", "40", "80", "160"}:
        return "channelWidth"
    if band == "bg" and channel_width not in {"20", "40"}:
        return "channelWidth"
    return None


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def parse_station_dump(text):
    stations = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Station "):
            if current:
                stations.append(current)
            current = {
                "mac": line.split()[1].lower(),
                "signalDbm": None,
                "connectedSeconds": None,
                "rxBytes": None,
                "txBytes": None,
            }
        elif current is not None and line.startswith("signal:"):
            match = re.search(r"signal:\s*(-?\d+)", line)
            if match:
                current["signalDbm"] = int(match.group(1))
        elif current is not None and line.startswith("connected time:"):
            match = re.search(r"connected time:\s*(\d+)", line)
            if match:
                current["connectedSeconds"] = int(match.group(1))
        elif current is not None and line.startswith("rx bytes:"):
            match = re.search(r"rx bytes:\s*(\d+)", line)
            if match:
                current["rxBytes"] = int(match.group(1))
        elif current is not None and line.startswith("tx bytes:"):
            match = re.search(r"tx bytes:\s*(\d+)", line)
            if match:
                current["txBytes"] = int(match.group(1))
    if current:
        stations.append(current)
    return stations


def ipv4_in_cidr(ip_addr, cidr):
    try:
        network = IPv4Interface(cidr).network
        host = IPv4Interface(f"{ip_addr}/32").ip
        return host in network
    except Exception:
        return False


def filter_ip_for_hotspot(ip_addr, cidr):
    return ip_addr if ip_addr and cidr and ipv4_in_cidr(ip_addr, cidr) else ""


def parse_neighbors(hotspot_dev, cidr):
    if not command_exists("ip"):
        return {}
    ok, stdout, _ = run_ok(["ip", "neigh", "show", "dev", hotspot_dev])
    if not ok:
        return {}
    neighbors = {}
    for line in stdout.splitlines():
        parts = line.split()
        if "lladdr" not in parts:
            continue
        index = parts.index("lladdr")
        if index + 1 >= len(parts):
            continue
        ip_addr = filter_ip_for_hotspot(parts[0], cidr)
        mac = parts[index + 1].lower()
        if ip_addr:
            neighbors[mac] = ip_addr
    return neighbors


def parse_lease_hosts(cidr):
    hosts_by_mac = {}
    hosts_by_ip = {}
    ip_by_mac = {}
    patterns = [
        "/var/lib/NetworkManager/dnsmasq-*.leases",
        "/var/lib/misc/dnsmasq.leases",
        "/tmp/dnsmasq.leases",
        DNSMASQ_LEASE_FILE,
    ]
    paths = []
    for pattern in patterns:
        pattern = str(pattern)
        if "*" in pattern:
            import glob

            paths.extend(sorted(glob.glob(pattern)))
        else:
            paths.append(pattern)
    for path in paths:
        for line in read_text(path).splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            mac = parts[1].lower()
            ip_addr = filter_ip_for_hotspot(parts[2], cidr)
            host = parts[3]
            if host not in {"", "*", "-"}:
                hosts_by_mac[mac] = host
            if ip_addr:
                ip_by_mac[mac] = ip_addr
                if host not in {"", "*", "-"}:
                    hosts_by_ip[ip_addr] = host
    return hosts_by_mac, hosts_by_ip, ip_by_mac


def resolve_hostname(ip_addr):
    if not ip_addr or not command_exists("getent"):
        return ""
    ok, stdout, _ = run_ok(["getent", "hosts", ip_addr])
    if not ok:
        return ""
    parts = stdout.split()
    return parts[1] if len(parts) > 1 else ""


def handle_config_get():
    global CURRENT_STEP
    CURRENT_STEP = "config_get"
    cfg = load_cfg()
    original_regdom = iw_reg_country()
    requested_country = first_value("countryCode")
    if requested_country:
        apply_regdom(requested_country)
    regdom = iw_reg_country()
    if requested_country and requested_country != regdom:
        err("country_unsupported", "400 Bad Request", country=requested_country)
    ch_bg = iw_channels_for_band("bg")
    ch_a = iw_channels_for_band("a")
    if requested_country and regdom != original_regdom:
        apply_regdom(original_regdom or "00")
    json_response(
        {
            "ok": True,
            **{
                "config": {
                    "iface": cfg["IFACE"],
                    "uplinkIface": cfg["UPLINK_IFACE"],
                    "ipCidr": cfg["IP_CIDR"],
                    "allowPorts": cfg["ALLOW_PORTS"],
                    "ssid": cfg["SSID"],
                    "password": cfg["PASSWORD"],
                    "countryCode": cfg["COUNTRY"],
                    "band": cfg["BAND"],
                    "channel": cfg["CHANNEL"],
                    "channelWidth": cfg["CHANNEL_WIDTH"],
                },
                "regdom": regdom,
                "countryLocked": not is_regdom_changeable(),
                "channelOptions": {"bg": ch_bg, "a": ch_a},
            },
        }
    )


def handle_config_set():
    global CURRENT_STEP
    CURRENT_STEP = "config_set"
    cfg = load_cfg()
    cfg.update(
        {
            "IFACE": first_value("iface"),
            "UPLINK_IFACE": first_value("uplinkIface"),
            "IP_CIDR": first_value("ipCidr"),
            "ALLOW_PORTS": first_value("allowPorts"),
            "SSID": first_value("ssid"),
            "PASSWORD": first_value("password"),
            "COUNTRY": first_value("countryCode"),
            "BAND": first_value("band"),
            "CHANNEL": first_value("channel"),
            "CHANNEL_WIDTH": first_value("channelWidth"),
        }
    )
    ensure_iface(cfg)
    cfg["IFACE"] = normalize_parent_wifi_iface(cfg.get("IFACE", ""))
    cfg_error = validate_cfg(cfg)
    if cfg_error:
        err("config_invalid", "400 Bad Request", field=cfg_error)
    # 运行中修改配置时：先校验新信道在当前国家码下是否可用。
    # 若不可用（disabled/no IR），直接在此拒绝并保持当前热点运行，绝不先停后启。
    runtime_error = validate_runtime_channel(cfg)
    if runtime_error:
        err(
            runtime_error["code"],
            "400 Bad Request",
            channel=runtime_error["channel"],
            regdom=runtime_error["regdom"] or cfg["COUNTRY"],
        )
    if not save_cfg(cfg):
        err("save_failed", "500 Internal Server Error")
    json_response({"ok": True})


def handle_status():
    global CURRENT_STEP
    CURRENT_STEP = "status"
    cfg = load_cfg()
    ensure_iface(cfg)
    nat_state = load_nat_state()
    parent_iface = cfg["IFACE"]
    hotspot_iface = nat_state["HOTSPOT_IFACE"] or parent_iface
    state = "unknown"
    active = ""
    if command_exists("nmcli"):
        ok, stdout, _ = run_ok(
            ["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "dev", "status"]
        )
        if ok:
            for line in stdout.splitlines():
                if line.startswith(f"{hotspot_iface}:"):
                    parts = line.split(":")
                    state = parts[1] if len(parts) > 1 else "unknown"
                    active = ":".join(parts[2:]) if len(parts) > 2 else ""
                    break
    running = active == cfg["SSID"]
    sta_ap_concurrent = iw_supports_sta_ap()
    parent_active_connection = ""
    if command_exists("nmcli"):
        ok, stdout, _ = run_ok(
            ["nmcli", "-g", "GENERAL.CONNECTION", "dev", "show", parent_iface]
        )
        if ok and stdout.splitlines():
            parent_active_connection = trim(stdout.splitlines()[0])
            if parent_active_connection == "--":
                parent_active_connection = ""
    will_disconnect_sta = (
        hotspot_iface == parent_iface
        and not sta_ap_concurrent
        and bool(parent_active_connection)
    )
    ip_addr = ""
    if command_exists("ip"):
        ok, stdout, _ = run_ok(["ip", "-4", "addr", "show", "dev", hotspot_iface])
        if ok:
            match = re.search(r"inet\s+([^\s]+)", stdout)
            if match:
                ip_addr = match.group(1)
    tx_power = wifi_txpower_dbm(hotspot_iface)
    driver = wifi_driver_name(hotspot_iface)
    effective_uplink = (
        nat_state["NAT_UPLINK_IFACE"]
        or cfg["UPLINK_IFACE"]
        or detect_route_dev("1.1.1.1")
    )
    internet_status = False
    internet_reason = "null"
    if command_exists("curl"):
        ok, _, _ = run_ok(
            [
                "curl",
                "--max-time",
                "3",
                "-I",
                "http://1.1.1.1",
                "--silent",
                "--output",
                "/dev/null",
            ]
        )
        if ok:
            internet_status = True
        else:
            internet_reason = f"curl failed on dev {hotspot_iface}"
    json_response(
        {
            "ok": True,
            **{
                "status": {
                    "running": running,
                    "iface": parent_iface,
                    "hotspotIface": hotspot_iface,
                    "state": state,
                    "activeConnection": active,
                    "parentActiveConnection": parent_active_connection,
                    "staApConcurrent": sta_ap_concurrent,
                    "willDisconnectSta": will_disconnect_sta,
                    "ip": ip_addr,
                    "txPowerDbm": tx_power,
                    "wifiDriver": driver,
                    "lowTxPower": wifi_txpower_is_suspiciously_low(hotspot_iface),
                    "uplinkIface": cfg["UPLINK_IFACE"],
                    "effectiveUplinkIface": effective_uplink,
                    "internetStatus": internet_status,
                    "internetReason": internet_reason,
                }
            },
        }
    )


def nmcli_connection_down(connection_id):
    if connection_id:
        run_cmd(["nmcli", "con", "down", "id", connection_id])


def nmcli_connection_delete(connection_id):
    if connection_id:
        run_cmd(["nmcli", "con", "delete", connection_id])


def nmcli_device_disconnect(device):
    if device:
        run_cmd(["nmcli", "device", "disconnect", device])


def restore_previous_connection(sta_prev_con):
    if sta_prev_con:
        run_cmd(["nmcli", "con", "up", "id", sta_prev_con])


def nmcli_ap_mode_supported():
    if not command_exists("iw"):
        return True
    ok, stdout, _ = run_ok(["iw", "list"])
    return bool(ok and re.search(r"^\s*\*\s+AP\b", stdout, flags=re.MULTILINE))


def set_auto_restore(enabled):
    write_runtime_state(AUTO_RESTORE="1" if enabled else "0")


def run_start():
    """执行一次热点开启的完整流程。返回 (ok, payload)：
    ok=True  payload={"output":..., "notice":...}；ok=False payload={"status":..., "code":..., "params":...}。
    供 handle_start（HTTP）与 restore_on_boot（系统重启后自启）共用。"""
    cfg = load_cfg()
    cfg_error = validate_cfg(cfg)
    if cfg_error:
        return False, {
            "status": "400 Bad Request",
            "code": "config_invalid",
            "params": {"field": cfg_error},
        }
    if cfg["COUNTRY"]:
        apply_regdom(cfg["COUNTRY"])
    runtime_error = validate_runtime_channel(cfg)
    if runtime_error:
        return False, {
            "status": "400 Bad Request",
            "code": runtime_error["code"],
            "params": {
                "channel": runtime_error["channel"],
                "regdom": runtime_error["regdom"] or cfg["COUNTRY"],
            },
        }
    remove_allow_ports()
    if cfg["UPLINK_IFACE"]:
        run_cmd(["nmcli", "dev", "connect", cfg["UPLINK_IFACE"]])
    iface_status = require_wifi_iface(cfg)
    if iface_status == 2:
        return False, {
            "status": "400 Bad Request",
            "code": "no_wifi_iface",
            "params": {},
        }
    if iface_status == 1:
        return False, {
            "status": "400 Bad Request",
            "code": "iface_not_wifi",
            "params": {"iface": cfg["IFACE"]},
        }
    parent_iface = cfg["IFACE"]
    hotspot_iface = cfg["IFACE"]
    virtual_iface = ""
    sta_prev_con = ""
    if command_exists("nmcli"):
        ok, stdout, _ = run_ok(
            ["nmcli", "-g", "GENERAL.CONNECTION", "dev", "show", cfg["IFACE"]]
        )
        if ok and stdout.splitlines():
            sta_prev_con = trim(stdout.splitlines()[0])
            if sta_prev_con == "--":
                sta_prev_con = ""
    if sta_prev_con and iw_supports_sta_ap():
        virtual_iface = mk_ap_iface_name(cfg["IFACE"])
        if ensure_virtual_ap_iface(cfg["IFACE"], virtual_iface):
            hotspot_iface = virtual_iface
        else:
            virtual_iface = ""
    if cfg["UPLINK_IFACE"] and cfg["UPLINK_IFACE"] == hotspot_iface:
        return False, {
            "status": "400 Bad Request",
            "code": "uplink_same_as_hotspot",
            "params": {"iface": hotspot_iface},
        }
    if (
        cfg["UPLINK_IFACE"]
        and cfg["UPLINK_IFACE"] == cfg["IFACE"]
        and hotspot_iface == cfg["IFACE"]
    ):
        return False, {
            "status": "400 Bad Request",
            "code": "uplink_same_as_hotspot",
            "params": {"iface": cfg["IFACE"]},
        }
    if not nmcli_ap_mode_supported():
        return False, {
            "status": "400 Bad Request",
            "code": "ap_not_supported",
            "params": {"iface": cfg["IFACE"]},
        }
    ip_cidr = effective_ip_cidr(cfg)
    if sta_prev_con:
        nmcli_connection_down(sta_prev_con)
    nmcli_connection_down(cfg["SSID"])
    nmcli_connection_delete(cfg["SSID"])
    nmcli_device_disconnect(hotspot_iface)
    stop_local_dnsmasq()
    ok, stdout, stderr = run_ok(
        [
            "nmcli",
            "con",
            "add",
            "type",
            "wifi",
            "ifname",
            hotspot_iface,
            "con-name",
            cfg["SSID"],
            "autoconnect",
            "no",
            "ssid",
            cfg["SSID"],
        ]
    )
    out = stdout or stderr

    def cleanup():
        nmcli_connection_down(cfg["SSID"])
        nmcli_connection_delete(cfg["SSID"])
        nmcli_device_disconnect(hotspot_iface)
        restore_previous_connection(sta_prev_con)

    def fail(status, code, **params):
        cleanup()
        return False, {"status": status, "code": code, "params": dict(params)}

    if not ok:
        return fail(
            "500 Internal Server Error",
            "nmcli_add_failed",
            detail=sanitize_text(out)[:300],
        )
    mod_cmd = [
        "nmcli",
        "con",
        "mod",
        cfg["SSID"],
        "802-11-wireless.mode",
        "ap",
        "802-11-wireless.band",
        cfg["BAND"],
        "802-11-wireless.channel",
        cfg["CHANNEL"],
        "802-11-wireless.powersave",
        "2",
        "802-11-wireless-security.key-mgmt",
        "wpa-psk",
        "802-11-wireless-security.psk",
        cfg["PASSWORD"],
        "802-11-wireless-security.proto",
        "rsn",
        "802-11-wireless-security.pairwise",
        "ccmp",
        "ipv4.method",
        "manual",
        "ipv4.addresses",
        ip_cidr,
        "ipv4.never-default",
        "yes",
        "ipv6.method",
        "disabled",
    ]
    ok, _, stderr = run_ok(mod_cmd)
    if not ok:
        return fail(
            "500 Internal Server Error",
            "nmcli_mod_failed",
            detail=sanitize_text(stderr)[:300],
        )
    width = cfg["CHANNEL_WIDTH"]
    if width == "20":
        run_cmd(["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.ht-mode", ""])
        run_cmd(["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.vht-mode", ""])
    elif width == "40":
        ok, _, _ = run_ok(
            ["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.ht-mode", "HT40+"]
        )
        if not ok:
            run_cmd(
                ["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.ht-mode", "HT40-"]
            )
        run_cmd(["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.vht-mode", ""])
    elif width == "80":
        run_cmd(
            ["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.vht-mode", "VHT80"]
        )
        run_cmd(["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.ht-mode", ""])
    elif width == "160":
        run_cmd(
            ["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.vht-mode", "VHT160"]
        )
        run_cmd(["nmcli", "con", "mod", cfg["SSID"], "802-11-wireless.ht-mode", ""])
    wait_secs = os.environ.get("NMCLI_WAIT_SECS", "20")
    ok, stdout, stderr = run_ok(
        ["nmcli", "--wait", wait_secs, "con", "up", "id", cfg["SSID"]]
    )
    nmcli_out = stdout or stderr
    if not ok:
        if "timed out" in nmcli_out.lower():
            return fail(
                "504 Gateway Timeout",
                "setup_timeout",
                wait=wait_secs,
                detail=sanitize_text(nmcli_out)[:300],
            )
        return fail(
            "500 Internal Server Error",
            "nmcli_up_failed",
            detail=sanitize_text(nmcli_out)[:300],
        )
    ok, dnsmasq_error = start_local_dnsmasq(hotspot_iface, cfg)
    if not ok:
        return fail(
            "500 Internal Server Error",
            "dnsmasq_failed",
            detail=sanitize_text(dnsmasq_error)[:300],
        )
    apply_hotspot_nat(hotspot_iface, cfg["UPLINK_IFACE"], parent_iface, virtual_iface)
    apply_allow_ports(hotspot_iface, cfg["ALLOW_PORTS"])
    set_auto_restore(True)
    return True, {
        "output": sanitize_text(out),
        "notice": sanitize_text(wifi_low_power_notice(hotspot_iface)),
    }


def handle_start():
    global CURRENT_STEP
    CURRENT_STEP = "start"
    ok, payload = run_start()
    if ok:
        json_response({"ok": True, **payload})
    json_response(
        {"ok": False, "code": payload["code"], "params": payload.get("params", {})},
        payload["status"],
    )


def handle_stop():
    global CURRENT_STEP
    CURRENT_STEP = "stop"
    cfg = load_cfg()
    ensure_iface(cfg)
    nat_state = load_nat_state()
    virtual_iface = nat_state["HOTSPOT_VIRTUAL_IFACE"]
    remove_hotspot_nat()
    remove_allow_ports()
    stop_local_dnsmasq()
    _, out2, err2 = run_cmd(["nmcli", "con", "down", "id", cfg["SSID"]])
    _, out3, err3 = run_cmd(["nmcli", "con", "delete", cfg["SSID"]])
    if virtual_iface and virtual_iface != cfg["IFACE"]:
        delete_virtual_ap_iface(virtual_iface)
    set_auto_restore(False)
    json_response({"ok": True, "output": sanitize_text(f"{out2}{err2}{out3}{err3}")})


def handle_clients():
    global CURRENT_STEP
    CURRENT_STEP = "clients"
    cfg = load_cfg()
    ensure_iface(cfg)
    nat_state = load_nat_state()
    hotspot_dev = nat_state["HOTSPOT_IFACE"] or cfg["IFACE"]
    if command_exists("iw"):
        ok, stdout, _ = run_ok(["iw", "dev", hotspot_dev, "info"])
        if ok and "type AP" not in stdout:
            json_response({"ok": True, **{"clients": []}})
    stations = []
    if command_exists("iw"):
        ok, stdout, _ = run_ok(["iw", "dev", hotspot_dev, "station", "dump"])
        if ok:
            stations = parse_station_dump(stdout)
    ip_cidr = effective_ip_cidr(cfg)
    neighbors = parse_neighbors(hotspot_dev, ip_cidr)
    hosts_by_mac, hosts_by_ip, ip_by_mac = parse_lease_hosts(ip_cidr)
    clients = []
    seen = set()

    def emit_client(
        mac, ip_addr, signal=None, connected=None, rx_bytes=None, tx_bytes=None
    ):
        mac = (mac or "").lower()
        if not mac or mac in seen:
            return
        seen.add(mac)
        hostname = hosts_by_mac.get(mac, "")
        if not hostname and ip_addr:
            hostname = hosts_by_ip.get(ip_addr, "") or resolve_hostname(ip_addr)
        item = {"mac": mac}
        if hostname:
            item["hostname"] = hostname
        if ip_addr:
            item["ip"] = ip_addr
        if signal is not None:
            item["signalDbm"] = signal
        if connected is not None:
            item["connectedSeconds"] = connected
        if rx_bytes is not None:
            item["rxBytes"] = rx_bytes
        if tx_bytes is not None:
            item["txBytes"] = tx_bytes
        clients.append(item)

    for station in stations:
        ip_addr = ip_by_mac.get(station["mac"], "") or neighbors.get(station["mac"], "")
        emit_client(
            station["mac"],
            ip_addr,
            station.get("signalDbm"),
            station.get("connectedSeconds"),
            station.get("rxBytes"),
            station.get("txBytes"),
        )
    if not stations:
        for mac, ip_addr in neighbors.items():
            emit_client(mac, ip_addr)
    json_response({"ok": True, **{"clients": clients}})


def handle_ifaces():
    global CURRENT_STEP
    CURRENT_STEP = "ifaces"
    json_response({"ok": True, **{"ifaces": wifi_ifaces()}})


def handle_uplinks():
    global CURRENT_STEP
    CURRENT_STEP = "uplinks"
    if not command_exists("nmcli"):
        json_response({"ok": True, **{"uplinks": []}})
    ok, stdout, _ = run_ok(["nmcli", "-t", "-f", "DEVICE", "dev", "status"])
    if not ok:
        json_response({"ok": True, **{"uplinks": []}})
    uplinks = []
    for device in stdout.splitlines():
        device = trim(device)
        if not device or device == "lo" or device.startswith("p2p"):
            continue
        if re.match(
            r"^(veth|docker|br-|virbr|vnet|tap|tun|wg|zt|tailscale|vboxnet|vmnet)",
            device,
        ):
            continue
        uplinks.append(device)
    json_response({"ok": True, **{"uplinks": uplinks}})


def handle_kick():
    global CURRENT_STEP
    CURRENT_STEP = "kick"
    cfg = load_cfg()
    ensure_iface(cfg)
    nat_state = load_nat_state()
    hotspot_dev = nat_state["HOTSPOT_IFACE"] or cfg["IFACE"]
    mac = trim(first_value("mac")).lower()
    if not re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", mac):
        err("client_invalid_mac", "400 Bad Request", mac=mac)
    if not hotspot_dev:
        err("client_no_wifi_iface", "400 Bad Request")
    if not command_exists("iw"):
        err("client_iw_missing", "500 Internal Server Error")
    ok, stdout, stderr = run_ok(["iw", "dev", hotspot_dev, "station", "del", mac])
    out = stdout or stderr
    if ok:
        if command_exists("ip"):
            ok_neigh, neigh_stdout, _ = run_ok(
                ["ip", "neigh", "show", "dev", hotspot_dev]
            )
            if ok_neigh:
                for line in neigh_stdout.splitlines():
                    parts = line.split()
                    if "lladdr" in parts:
                        index = parts.index("lladdr")
                        if index + 1 < len(parts) and parts[index + 1].lower() == mac:
                            run_cmd(
                                ["ip", "neigh", "del", parts[0], "dev", hotspot_dev]
                            )
                            break
        json_response({"ok": True, "output": sanitize_text(out)})
    err("kick_failed", "500 Internal Server Error", detail=sanitize_text(out)[:300])


def handle_stpre():
    global CURRENT_STEP
    CURRENT_STEP = "stpre"
    cfg = load_cfg()
    cfg_error = validate_cfg(cfg)
    if cfg_error:
        json_response(
            {
                "ok": True,
                **{
                    "abort": True,
                    "code": "config_invalid",
                    "params": {"field": cfg_error},
                },
            }
        )
    warnings = []
    iface_status = require_wifi_iface(cfg)
    if iface_status == 1:
        json_response(
            {
                "ok": True,
                **{
                    "abort": True,
                    "code": "iface_not_wifi",
                    "params": {"iface": cfg["IFACE"]},
                },
            }
        )
    if iface_status == 2:
        json_response(
            {
                "ok": True,
                **{
                    "abort": True,
                    "code": "no_wifi_iface",
                    "params": {},
                },
            }
        )
    sta_prev_con = ""
    if command_exists("nmcli"):
        ok, stdout, _ = run_ok(
            ["nmcli", "-g", "GENERAL.CONNECTION", "dev", "show", cfg["IFACE"]]
        )
        if ok and stdout.splitlines():
            sta_prev_con = trim(stdout.splitlines()[0])
            if sta_prev_con == "--":
                sta_prev_con = ""
    regdom = iw_reg_country() or "00"
    if regdom == "00":
        warnings.append({"code": "country_00", "params": {"regdom": regdom}})
    if not iw_supports_sta_ap():
        if sta_prev_con:
            warnings.append(
                {
                    "code": "no_sta_ap_disconnect",
                    "params": {"con": sta_prev_con, "iface": cfg["IFACE"]},
                }
            )
        else:
            warnings.append(
                {
                    "code": "no_sta_ap_interrupt",
                    "params": {"iface": cfg["IFACE"]},
                }
            )
    if cfg["UPLINK_IFACE"] and cfg["UPLINK_IFACE"] == cfg["IFACE"]:
        json_response(
            {
                "ok": True,
                **{
                    "abort": True,
                    "code": "uplink_same_as_hotspot",
                    "params": {"iface": cfg["IFACE"]},
                },
            }
        )
    if not nmcli_ap_mode_supported():
        json_response(
            {
                "ok": True,
                **{
                    "abort": True,
                    "code": "ap_not_supported",
                    "params": {"iface": cfg["IFACE"]},
                },
            }
        )
    runtime_error = validate_runtime_channel(cfg)
    if runtime_error:
        warnings.append(
            {
                "code": runtime_error["code"],
                "params": {
                    "channel": runtime_error["channel"],
                    "regdom": runtime_error["regdom"],
                },
            }
        )
    power_info = wifi_low_power_info(cfg["IFACE"])
    if power_info:
        warnings.append({"code": "low_tx_power", "params": power_info})
    if warnings:
        json_response({"ok": True, **{"warnings": warnings}})
    json_response({"ok": True})


ACTIONS = {
    "config_get": handle_config_get,
    "config_set": handle_config_set,
    "status": handle_status,
    "start": handle_start,
    "stop": handle_stop,
    "clients": handle_clients,
    "ifaces": handle_ifaces,
    "uplinks": handle_uplinks,
    "kick": handle_kick,
    "stpre": handle_stpre,
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


def dispatch():
    payload = request_body()
    action = payload.get("action") if isinstance(payload, dict) else ""
    if isinstance(action, str) and action.endswith(".cgi"):
        action = action[:-4]
    if not action:
        err("missing_action", "400 Bad Request")
        return
    handler_fn = ACTIONS.get(action)
    if not handler_fn:
        err("unsupported_action", "400 Bad Request", action=action)
        return
    handler_fn()


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

    def serve_api(self, query):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        headers = {key: value for key, value in self.headers.items()}
        with request_context(
            self.command, query=query, headers=headers, body=body, handler=self
        ):
            try:
                dispatch()
            except ResponseDone:
                return
            except Exception as exc:
                try:
                    err(
                        "unexpected",
                        "500 Internal Server Error",
                        step=CURRENT_STEP,
                        detail=sanitize_text(str(exc))[:300],
                    )
                except ResponseDone:
                    return

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


def restore_on_boot():
    """系统重启后，若上次热点仍在运行（AUTO_RESTORE=1），后台自动重新开启。"""
    from threading import Timer

    def _do():
        try:
            if load_runtime_state().get("AUTO_RESTORE", "") != "1":
                return
            ok, payload = run_start()
            if ok:
                sys.stdout.write("restore_on_boot: hotspot auto-restored\n")
            else:
                sys.stdout.write(
                    f"restore_on_boot: auto-restore failed {payload.get('status')}: "
                    f"{payload.get('code', '')}\n"
                )
        except Exception as exc:
            sys.stdout.write(f"restore_on_boot: error {exc}\n")

    Timer(3.0, _do).start()


def main():
    global DATA_DIR, RUNTIME_STATE_FILE
    global DNSMASQ_CONF_FILE, DNSMASQ_PID_FILE, DNSMASQ_LEASE_FILE, CFG_FILE
    parser = argparse.ArgumentParser(description="fn-wifi-hotspot Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-wifi-hotspot")
    parser.add_argument("--www-root", required=True)
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()

    # 数据目录：显式 --data-dir 覆盖 TRIM_PKGVAR 推导的默认值，统一用 Path
    DATA_DIR = Path(args.data_dir)
    CFG_FILE = DATA_DIR / "hotspot.env"
    RUNTIME_STATE_FILE = DATA_DIR / "runtime.state"
    DNSMASQ_CONF_FILE = DATA_DIR / "hotspot-dnsmasq.conf"
    DNSMASQ_PID_FILE = DATA_DIR / "hotspot-dnsmasq.pid"
    DNSMASQ_LEASE_FILE = DATA_DIR / "hotspot-dnsmasq.leases"
    ensure_data_dir()

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
    restore_on_boot()
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if os.path.exists(args.unix_socket):
            os.unlink(args.unix_socket)


if __name__ == "__main__":
    main()
