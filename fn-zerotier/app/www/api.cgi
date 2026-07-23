# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import base64
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs

SERVICE_NAME = "zerotier-one"
JOINED_MOON_REGISTRY_FILE = "fn-zerotier-moons.json"
CREATED_MOON_REGISTRY_FILE = "fn-zerotier-created-moons.json"
MOON_AUDIT_LOG_FILE = "fn-zerotier-moon-actions.log"
ZEROTIER_HOME_CANDIDATES = [
    os.environ.get("ZEROTIER_HOME", "").strip(),
    "/var/lib/zerotier-one",
    "/var/lib/zerotier-one-one",
]


def respond(obj):
    print("Content-Type: application/json")
    print()
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def command_exists(name):
    return shutil.which(name) is not None


def get_query_param(name):
    values = parse_qs(os.environ.get("QUERY_STRING", ""), keep_blank_values=True).get(
        name
    )
    return values[0] if values else None


def read_post_json():
    if os.environ.get("REQUEST_METHOD", "").upper() != "POST":
        return {}
    try:
        length = int(os.environ.get("CONTENT_LENGTH", "0") or 0)
    except ValueError:
        length = 0
    body = sys.stdin.read(length) if length else ""
    if not body:
        return {}
    try:
        return json.loads(body)
    except Exception:
        return {}


def run_cmd(cmd, timeout=20, cwd=None):
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode
    except Exception as exc:
        return False, "", str(exc), -1


def systemctl_available():
    return command_exists("systemctl")


def service_active():
    if not systemctl_available():
        return False
    return (
        subprocess.run(
            ["systemctl", "is-active", "--quiet", SERVICE_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def service_enabled():
    if not systemctl_available():
        return False
    return (
        subprocess.run(
            ["systemctl", "is-enabled", "--quiet", SERVICE_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def systemctl_exec(*args):
    if not systemctl_available():
        return False, "", "systemctl 不可用", -1
    return run_cmd(["systemctl", *args], timeout=30)


def zerotier_json(*args):
    if not command_exists("zerotier-cli"):
        return None, "zerotier-cli not found"
    ok, out, err, _ = run_cmd(["zerotier-cli", "-j", *args])
    if not ok:
        return None, (err or out or "command failed").strip()
    try:
        return json.loads(out or "null"), None
    except Exception as exc:
        return None, f"invalid json: {exc}"


def zerotier_exec(*args):
    if not command_exists("zerotier-cli"):
        return False, "", "zerotier-cli not found", -1
    return run_cmd(["zerotier-cli", *args])


def zerotier_idtool_base_cmd():
    if command_exists("zerotier-idtool"):
        return ["zerotier-idtool"]
    if command_exists("zerotier-one"):
        return ["zerotier-one", "-i"]
    return None


def zerotier_idtool_exec(*args, timeout=60, cwd=None):
    base_cmd = zerotier_idtool_base_cmd()
    if not base_cmd:
        return False, "", "zerotier-idtool not found", -1
    return run_cmd([*base_cmd, *args], timeout=timeout, cwd=cwd)


def read_text_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except Exception:
        return ""


def current_timestamp():
    return int(time.time() * 1000)


def zerotier_home_dirs():
    seen = set()
    result = []
    for raw_path in ZEROTIER_HOME_CANDIDATES:
        if not raw_path:
            continue
        normalized = os.path.normpath(raw_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def zerotier_state_dir():
    for base_dir in zerotier_home_dirs():
        if os.path.isdir(base_dir):
            return base_dir
    return "/var/lib/zerotier-one"


def registry_path(filename):
    return os.path.join(zerotier_state_dir(), filename)


def moon_audit_log_path():
    return registry_path(MOON_AUDIT_LOG_FILE)


def joined_moon_registry_path():
    return registry_path(JOINED_MOON_REGISTRY_FILE)


def created_moon_registry_path():
    return registry_path(CREATED_MOON_REGISTRY_FILE)


def load_json_list(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_json_list(path, items):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False, indent=2)
    except Exception:
        return False
    return True


def append_moon_audit(action, world_id="", seed="", detail=""):
    path = moon_audit_log_path()
    line = json.dumps(
        {
            "timestamp": current_timestamp(),
            "action": action,
            "worldId": world_id or "",
            "seed": seed or "",
            "detail": detail or "",
        },
        ensure_ascii=False,
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return False
    return True


def load_joined_moon_registry():
    return load_json_list(joined_moon_registry_path())


def save_joined_moon_registry(moons):
    return save_json_list(joined_moon_registry_path(), moons)


def normalize_created_moon_sort_indexes(moons):
    normalized = []
    used_indexes = set()
    changed = False
    for index, item in enumerate(moons, start=1):
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        try:
            sort_index = int(normalized_item.get("sortIndex") or 0)
        except Exception:
            sort_index = 0
        if sort_index <= 0 or sort_index in used_indexes:
            sort_index = index
        if normalized_item.get("sortIndex") != sort_index:
            changed = True
        normalized_item["sortIndex"] = sort_index
        used_indexes.add(sort_index)
        normalized.append(normalized_item)
    return normalized, changed


def load_created_moon_registry():
    path = created_moon_registry_path()
    moons = load_json_list(path)
    normalized, changed = normalize_created_moon_sort_indexes(moons)
    if changed:
        save_json_list(path, normalized)
    return normalized


def save_created_moon_registry(moons):
    return save_json_list(created_moon_registry_path(), moons)


def joined_moon_registry_entry(world_id, seed):
    return {
        "id": world_id,
        "active": True,
        "waiting": False,
        "source": "joined",
        "timestamp": current_timestamp(),
        "roots": [
            {
                "identity": seed,
                "stableEndpoints": [],
            }
        ],
    }


def created_moon_registry_entry(
    world_id,
    seed,
    root_identity,
    stable_endpoints,
    active=False,
    timestamp=None,
    sort_index=0,
    orbit_command="",
    moon_file_name="",
    moon_file_base64="",
):
    normalized_endpoints = [
        str(item or "").strip()
        for item in stable_endpoints or []
        if str(item or "").strip()
    ]
    identity = (root_identity or "").strip() or seed
    return {
        "id": world_id,
        "active": bool(active),
        "waiting": False,
        "source": "created",
        "seed": seed,
        "rootIdentity": identity,
        "timestamp": timestamp or current_timestamp(),
        "sortIndex": int(sort_index or 0),
        "orbitCommand": orbit_command,
        "moonFileName": moon_file_name,
        "moonFileBase64": moon_file_base64,
        "roots": [
            {
                "identity": identity,
                "stableEndpoints": normalized_endpoints,
            }
        ],
    }


def upsert_joined_moon_registry(world_id, seed, active=True):
    moons = [item for item in load_joined_moon_registry() if item.get("id") != world_id]
    entry = joined_moon_registry_entry(world_id, seed)
    entry["active"] = bool(active)
    moons.append(entry)
    save_joined_moon_registry(moons)


def upsert_created_moon_registry(entry):
    world_id = entry.get("id")
    if not world_id:
        return False
    moons = [
        item for item in load_created_moon_registry() if item.get("id") != world_id
    ]
    moons.append(entry)
    return save_created_moon_registry(moons)


def remove_joined_moon_registry(world_id):
    moons = [item for item in load_joined_moon_registry() if item.get("id") != world_id]
    save_joined_moon_registry(moons)


def remove_created_moon_registry(world_id):
    moons = [
        item for item in load_created_moon_registry() if item.get("id") != world_id
    ]
    save_created_moon_registry(moons)


def find_joined_moon_registry(world_id):
    for item in load_joined_moon_registry():
        if item.get("id") == world_id:
            return item
    return None


def find_created_moon_registry(world_id):
    for item in load_created_moon_registry():
        if item.get("id") == world_id:
            return item
    return None


def next_created_moon_sort_index():
    max_sort_index = 0
    for item in load_created_moon_registry():
        try:
            max_sort_index = max(max_sort_index, int(item.get("sortIndex") or 0))
        except Exception:
            continue
    return max_sort_index + 1


def created_moon_seed(entry):
    seed = (entry or {}).get("seed") or ""
    if seed:
        return seed
    roots = (entry or {}).get("roots") or []
    if roots and isinstance(roots[0], dict):
        return extract_address_from_identity(roots[0].get("identity") or "")
    return ""


def created_moon_identity(entry):
    identity = (entry or {}).get("rootIdentity") or ""
    if identity:
        return identity
    roots = (entry or {}).get("roots") or []
    if roots and isinstance(roots[0], dict):
        return (roots[0].get("identity") or "").strip()
    return ""


def created_moon_stable_endpoints(entry):
    roots = (entry or {}).get("roots") or []
    if roots and isinstance(roots[0], dict):
        return roots[0].get("stableEndpoints") or []
    return []


def save_created_moon_entry(
    world_id,
    seed,
    root_identity,
    stable_endpoints,
    active=False,
    timestamp=None,
    sort_index=0,
    orbit_command="",
    moon_file_name="",
    moon_file_base64="",
):
    return upsert_created_moon_registry(
        created_moon_registry_entry(
            world_id,
            seed,
            root_identity,
            stable_endpoints,
            active=active,
            timestamp=timestamp,
            sort_index=sort_index,
            orbit_command=orbit_command,
            moon_file_name=moon_file_name,
            moon_file_base64=moon_file_base64,
        )
    )


def normalize_created_moons(moons):
    normalized = []
    for index, item in enumerate(moons, start=1):
        if not isinstance(item, dict):
            continue
        world_id = normalize_world_id(item.get("id"))
        seed = created_moon_seed(item)
        identity = created_moon_identity(item)
        if not world_id or not seed:
            continue
        stable_endpoints = []
        roots = item.get("roots") or []
        if roots and isinstance(roots[0], dict):
            stable_endpoints = roots[0].get("stableEndpoints") or []
        normalized.append(
            created_moon_registry_entry(
                world_id,
                seed,
                identity,
                stable_endpoints,
                active=bool(item.get("active")),
                timestamp=item.get("timestamp") or 0,
                sort_index=item.get("sortIndex") or index,
                orbit_command=item.get("orbitCommand") or "",
                moon_file_name=item.get("moonFileName") or "",
                moon_file_base64=item.get("moonFileBase64") or "",
            )
        )
    return sorted(
        normalized,
        key=lambda item: (int(item.get("sortIndex") or 0), item.get("id") or ""),
    )


def merge_moons(cli_moons, registry_moons):
    merged = {}

    for registry_moon in registry_moons:
        if not isinstance(registry_moon, dict):
            continue
        world_id = registry_moon.get("id")
        if not world_id:
            continue
        item = dict(registry_moon)
        item["active"] = bool(item.get("active", True))
        merged[world_id] = item

    for cli_moon in cli_moons:
        if not isinstance(cli_moon, dict):
            continue
        world_id = cli_moon.get("id")
        if not world_id:
            continue
        registry_moon = merged.get(world_id, {})
        item = dict(registry_moon)
        item.update(cli_moon)
        item["active"] = True
        if not item.get("roots") and registry_moon.get("roots"):
            item["roots"] = registry_moon.get("roots")
        merged[world_id] = item

    return sorted(
        merged.values(),
        key=lambda item: (
            0 if item.get("active", True) else 1,
            -(item.get("timestamp") or 0),
        ),
    )


def find_zerotier_identity_file(filename):
    for base_dir in zerotier_home_dirs():
        candidate = os.path.join(base_dir, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def extract_address_from_identity(identity):
    value = (identity or "").strip().lower()
    match = re.match(r"([0-9a-f]{10}):", value)
    return match.group(1) if match else ""


def normalize_world_id(value):
    normalized = (value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{10}", normalized):
        return normalized
    if re.fullmatch(r"0{6}[0-9a-f]{10}", normalized):
        return normalized[-10:]
    return ""


def get_local_identity_public():
    public_path = find_zerotier_identity_file("identity.public")
    if public_path:
        identity_public = read_text_file(public_path)
        if identity_public:
            return identity_public, None

    secret_path = find_zerotier_identity_file("identity.secret")
    if secret_path:
        ok, out, err, _ = zerotier_idtool_exec("getpublic", secret_path)
        identity_public = (out or "").strip()
        if ok and identity_public:
            return identity_public, None
        if err:
            return None, (err or out or "读取 identity.public 失败").strip()

    return None, "未找到可用的 identity.public，请确认 ZeroTier 已正确安装并初始化"


def collect_moon_create_info():
    base_cmd = zerotier_idtool_base_cmd()
    root_identity, identity_error = get_local_identity_public()
    seed = extract_address_from_identity(root_identity)
    world_id = normalize_world_id(seed)

    error = None
    if not base_cmd:
        error = "系统中未找到 zerotier-idtool，无法生成 moon 文件"
    elif identity_error:
        error = identity_error

    return {
        "supported": error is None,
        "rootIdentity": root_identity or "",
        "seed": seed,
        "worldId": world_id,
        "error": error,
    }


def collect_status():
    installed = command_exists("zerotier-cli")
    info, info_error = (None, None)
    networks, networks_error = ([], None)
    peers, peers_error = ([], None)
    moons, moons_error = ([], None)
    moon_create = collect_moon_create_info()

    if installed:
        info, info_error = zerotier_json("info")
        networks, networks_error = zerotier_json("listnetworks")
        peers, peers_error = zerotier_json("listpeers")
        moons, moons_error = zerotier_json("listmoons")
        if not isinstance(networks, list):
            networks = []
        if not isinstance(peers, list):
            peers = []
        if not isinstance(moons, list):
            moons = []

    created_moons = normalize_created_moons(load_created_moon_registry())
    created_moon_ids = {item.get("id") for item in created_moons if item.get("id")}
    joined_moons = [
        item
        for item in merge_moons(moons, load_joined_moon_registry())
        if item.get("id") not in created_moon_ids
    ]

    online_peers = sum(
        1
        for peer in peers
        if isinstance(peer.get("latency"), int) and peer.get("latency", -1) >= 0
    )

    return {
        "ok": True,
        "service": {
            "name": SERVICE_NAME,
            "installed": installed,
            "active": service_active(),
            "enabled": service_enabled(),
        },
        "info": info or {},
        "networks": networks,
        "peers": peers[:12],
        "moons": joined_moons,
        "joinedMoons": joined_moons,
        "createdMoons": created_moons,
        "moonCreate": moon_create,
        "peerSummary": {
            "total": len(peers),
            "online": online_peers,
        },
        "errors": {
            "info": info_error,
            "networks": networks_error,
            "peers": peers_error,
            "moons": moons_error,
        },
    }


def validate_hex_id(value, length, field_label):
    normalized = (value or "").strip().lower()
    if not re.fullmatch(rf"[0-9a-f]{{{length}}}", normalized):
        respond(
            {
                "ok": False,
                "error": f"{field_label} 必须是 {length} 位十六进制字符串",
            }
        )
    return normalized


def validate_network_id(network_id):
    return validate_hex_id(network_id, 16, "network id")


def validate_moon_world_id(world_id):
    normalized = (world_id or "").strip().lower()
    world_id = normalize_world_id(normalized)
    if world_id:
        return world_id
    respond(
        {
            "ok": False,
            "error": "moon world id 必须是 10 位十六进制，或 6 个前导 0 加 10 位地址的 16 位十六进制字符串",
        }
    )


def validate_moon_seed(seed):
    return validate_hex_id(seed, 10, "moon seed")


def parse_stable_endpoints(value):
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[\n,;]+", str(value or ""))

    endpoints = []
    seen = set()
    for raw_item in raw_items:
        endpoint = str(raw_item or "").strip()
        if not endpoint:
            continue
        if not re.fullmatch(r"[^\s]+/\d{1,5}", endpoint):
            respond(
                {
                    "ok": False,
                    "error": "Stable Endpoint 格式错误，请使用 IP/端口，例如 203.0.113.10/9993",
                }
            )
        if endpoint in seen:
            continue
        seen.add(endpoint)
        endpoints.append(endpoint)

    if not endpoints:
        respond({"ok": False, "error": "请至少填写一个 Stable Endpoint"})
    return endpoints


def moon_summary(world):
    if not isinstance(world, dict):
        return None
    roots = world.get("roots")
    if not isinstance(roots, list):
        roots = []
    return {
        "id": world.get("id") or "",
        "active": bool(world.get("active", True)),
        "waiting": bool(world.get("waiting")),
        "timestamp": world.get("timestamp") or 0,
        "rootCount": len(roots),
        "roots": roots,
        "source": world.get("source") or "joined",
        "orbitCommand": world.get("orbitCommand") or "",
        "moonFileName": world.get("moonFileName") or "",
        "moonFileBase64": world.get("moonFileBase64") or "",
    }


def build_moon_artifacts(root_identity, seed, requested_world_id, stable_endpoints):
    world_id = validate_moon_world_id(requested_world_id) if requested_world_id else ""
    moon_bytes = b""
    with tempfile.TemporaryDirectory(prefix="fn-zerotier-moon-") as temp_dir:
        ok, out, err, _ = zerotier_idtool_exec("initmoon", root_identity, cwd=temp_dir)
        if not ok:
            respond({"ok": False, "error": (err or out or "initmoon 执行失败").strip()})
        try:
            moon_json = json.loads(out or "{}")
        except Exception as exc:
            respond({"ok": False, "error": f"initmoon 返回了无效 JSON: {exc}"})
            return None
        roots = moon_json.get("roots")
        if not isinstance(roots, list) or not roots:
            respond({"ok": False, "error": "initmoon 未生成有效的 roots 信息"})

        roots[0]["stableEndpoints"] = stable_endpoints
        world_id = world_id or normalize_world_id(moon_json.get("id") or seed)
        if not world_id:
            respond({"ok": False, "error": "生成的 moon world id 无效"})
        moon_json["id"] = world_id

        json_path = os.path.join(temp_dir, "moon.json")
        try:
            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(moon_json, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            respond({"ok": False, "error": f"写入 moon 配置失败: {exc}"})

        ok, out, err, _ = zerotier_idtool_exec("genmoon", json_path, cwd=temp_dir)
        if not ok:
            respond({"ok": False, "error": (err or out or "genmoon 执行失败").strip()})

        moon_files = sorted(glob.glob(os.path.join(temp_dir, "*.moon")))
        if not moon_files:
            respond({"ok": False, "error": "已执行 genmoon，但未找到输出的 moon 文件"})
        moon_path = moon_files[0]
        moon_filename = os.path.basename(moon_path)

        try:
            with open(moon_path, "rb") as handle:
                moon_bytes = handle.read()
        except Exception as exc:
            respond({"ok": False, "error": f"读取生成的 moon 文件失败: {exc}"})

    return {
        "worldId": world_id,
        "seed": seed,
        "rootIdentity": root_identity,
        "stableEndpoints": stable_endpoints,
        "moonJson": json.dumps(moon_json, ensure_ascii=False, indent=2),
        "moonFileName": moon_filename,
        "moonFileBase64": base64.b64encode(moon_bytes).decode("ascii"),
        "orbitCommand": f"zerotier-cli orbit {world_id} {seed}",
        "genmoonOutput": (out or "").strip(),
    }


def ensure_service_active():
    if not systemctl_available():
        respond({"ok": False, "error": "systemctl 不可用"})
    if not service_active():
        respond({"ok": False, "error": "ZeroTier 服务未启动，请先在应用中启动服务"})


def handle_join(body):
    network_id = validate_network_id(body.get("network"))
    ensure_service_active()
    ok, out, err, _ = zerotier_exec("join", network_id)
    if not ok:
        respond({"ok": False, "error": (err or out or "join failed").strip()})
    payload = collect_status()
    payload["message"] = f"已发起加入网络 {network_id}"
    respond(payload)


def handle_leave(body):
    network_id = validate_network_id(body.get("network"))
    ok, out, err, _ = zerotier_exec("leave", network_id)
    if not ok:
        respond({"ok": False, "error": (err or out or "leave failed").strip()})
    payload = collect_status()
    payload["message"] = f"已离开网络 {network_id}"
    respond(payload)


def handle_network_set(body):
    network_id = validate_network_id(body.get("network"))
    settings = body.get("settings") or {}
    if not isinstance(settings, dict) or not settings:
        respond({"ok": False, "error": "没有需要更新的网络设置"})

    has_valid_setting = False
    for key in ("allowManaged", "allowGlobal", "allowDefault", "allowDNS"):
        if key in settings:
            has_valid_setting = True
            ok, out, err, _ = run_cmd(
                [
                    "zerotier-cli",
                    "set",
                    network_id,
                    f"{key}={'1' if bool(settings[key]) else '0'}",
                ]
            )
            if not ok:
                respond(
                    {
                        "ok": False,
                        "error": (err or out or f"更新网络设置 {key} 失败").strip(),
                    }
                )

    if not has_valid_setting:
        respond({"ok": False, "error": "没有有效的网络设置"})

    payload = collect_status()
    payload["message"] = f"网络 {network_id} 设置已更新"
    respond(payload)


def handle_moon_join(body):
    world_id = validate_moon_world_id(body.get("worldId"))
    seed = validate_moon_seed(body.get("seed"))
    if find_created_moon_registry(world_id):
        respond(
            {
                "ok": False,
                "error": f"moon {world_id} 已在“已创建 Moon”中，请在已创建列表里启动或移除",
            }
        )
    ensure_service_active()
    ok, out, err, _ = zerotier_exec("orbit", world_id, seed)
    if not ok:
        append_moon_audit(
            "moon_join_failed",
            world_id if world_id else "",
            seed,
            (err or out or "加入 moon 失败").strip(),
        )
        respond({"ok": False, "error": (err or out or "加入 moon 失败").strip()})
    upsert_joined_moon_registry(world_id, seed, active=True)
    append_moon_audit("moon_join", world_id if world_id else "", seed, "joined moon")
    payload = collect_status()
    payload["message"] = f"已加入 moon {world_id}"
    payload["moon"] = moon_summary(
        next(
            (
                item
                for item in payload.get("joinedMoons", [])
                if item.get("id") == world_id
            ),
            None,
        )
    )
    respond(payload)


def handle_moon_start(body):
    world_id = validate_moon_world_id(body.get("worldId"))
    entry = find_created_moon_registry(world_id)
    if not entry:
        respond({"ok": False, "error": f"未找到已创建的 moon {world_id}"})
    seed = validate_moon_seed(created_moon_seed(entry))
    ensure_service_active()
    ok, out, err, _ = zerotier_exec("orbit", world_id, seed)
    if not ok:
        append_moon_audit(
            "moon_start_failed",
            world_id if world_id else "",
            seed,
            (err or out or "启动 moon 失败").strip(),
        )
        respond({"ok": False, "error": (err or out or "启动 moon 失败").strip()})
    save_created_moon_entry(
        world_id,
        seed,
        created_moon_identity(entry),
        created_moon_stable_endpoints(entry),
        active=True,
        timestamp=current_timestamp(),
        sort_index=entry.get("sortIndex") if entry else 0,
        orbit_command=(
            entry.get("orbitCommand")
            if entry
            else f"zerotier-cli orbit {world_id} {seed}"
        ),
        moon_file_name=entry.get("moonFileName") if entry else "",
        moon_file_base64=entry.get("moonFileBase64") if entry else "",
    )
    append_moon_audit(
        "moon_start", world_id if world_id else "", seed, "started created moon"
    )
    payload = collect_status()
    payload["message"] = f"已启动 moon {world_id}"
    respond(payload)


def handle_moon_stop(body):
    world_id = validate_moon_world_id(body.get("worldId"))
    entry = find_created_moon_registry(world_id)
    if not entry:
        respond({"ok": False, "error": f"未找到已创建的 moon {world_id}"})
    ok, out, err, _ = zerotier_exec("deorbit", world_id)
    if not ok:
        append_moon_audit(
            "moon_stop_failed",
            world_id if world_id else "",
            created_moon_seed(entry),
            (err or out or "停止 moon 失败").strip(),
        )
        respond({"ok": False, "error": (err or out or "停止 moon 失败").strip()})
    seed = created_moon_seed(entry)
    save_created_moon_entry(
        world_id,
        seed,
        created_moon_identity(entry),
        created_moon_stable_endpoints(entry),
        active=False,
        timestamp=current_timestamp(),
        sort_index=entry.get("sortIndex", 0) if entry else 0,
        orbit_command=(
            entry.get("orbitCommand")
            if entry
            else f"zerotier-cli orbit {world_id} {seed}"
        ),
        moon_file_name=entry.get("moonFileName") if entry else "",
        moon_file_base64=entry.get("moonFileBase64") if entry else "",
    )
    append_moon_audit(
        "moon_stop",
        world_id if world_id else "",
        created_moon_seed(entry),
        "stopped created moon",
    )
    payload = collect_status()
    payload["message"] = f"已停止 moon {world_id}"
    respond(payload)


def handle_moon_leave(body):
    world_id = validate_moon_world_id(body.get("worldId"))
    if find_created_moon_registry(world_id):
        respond(
            {
                "ok": False,
                "error": f"moon {world_id} 属于“已创建 Moon”，请使用创建列表里的移除操作",
            }
        )
    entry = find_joined_moon_registry(world_id)
    active = bool(entry.get("active", True)) if entry else True
    if active:
        ok, out, err, _ = zerotier_exec("deorbit", world_id)
        if not ok:
            append_moon_audit(
                "moon_leave_failed",
                world_id if world_id else "",
                "",
                (err or out or "移除 moon 失败").strip(),
            )
            respond({"ok": False, "error": (err or out or "移除 moon 失败").strip()})
    remove_joined_moon_registry(world_id)
    append_moon_audit(
        "moon_leave", world_id if world_id else "", "", "removed joined moon"
    )
    payload = collect_status()
    payload["message"] = f"已移除已加入 moon {world_id}"
    respond(payload)


def handle_moon_update(body):
    old_world_id = validate_moon_world_id(body.get("oldWorldId"))
    world_id = validate_moon_world_id(body.get("worldId"))
    old_entry = find_created_moon_registry(old_world_id)
    if not old_entry:
        respond({"ok": False, "error": f"未找到已创建的 moon {old_world_id}"})
    seed = validate_moon_seed(created_moon_seed(old_entry))
    root_identity = created_moon_identity(old_entry)
    stable_endpoints = parse_stable_endpoints(body.get("stableEndpoints"))
    result = build_moon_artifacts(root_identity, seed, world_id, stable_endpoints)

    old_active = bool(old_entry.get("active")) if old_entry else False
    warning = None
    if old_active and old_world_id != world_id:
        ensure_service_active()
        ok, out, err, _ = zerotier_exec("orbit", world_id, seed)
        if not ok:
            append_moon_audit(
                "moon_update_failed",
                world_id if world_id else "",
                seed,
                (err or out or "更新 moon 失败").strip(),
            )
            respond({"ok": False, "error": (err or out or "更新 moon 失败").strip()})
        ok, out, err, _ = zerotier_exec("deorbit", old_world_id)
        if not ok:
            warning = (
                err or out or f"新 moon 已启动，但旧 moon {old_world_id} 停止失败"
            ).strip()

    remove_created_moon_registry(old_world_id)
    remove_joined_moon_registry(old_world_id)
    save_created_moon_entry(
        world_id,
        seed,
        root_identity,
        stable_endpoints,
        active=old_active,
        timestamp=current_timestamp(),
        sort_index=old_entry.get("sortIndex") if old_entry else 0,
        orbit_command=result.get("orbitCommand") if old_entry else "",
        moon_file_name=result.get("moonFileName") if old_entry else "",
        moon_file_base64=result.get("moonFileBase64") if old_entry else "",
    )
    append_moon_audit(
        "moon_update",
        world_id if world_id else "",
        seed,
        f"updated from {old_world_id}",
    )

    payload = collect_status()
    payload["message"] = f"已更新 moon {world_id}"
    if warning:
        payload["message"] = warning
    payload["moon"] = moon_summary(
        next(
            (
                item
                for item in payload.get("createdMoons", [])
                if item.get("id") == world_id
            ),
            None,
        )
    )
    payload["moonCreateResult"] = result
    respond(payload)


def handle_moon_create(body):
    moon_create = collect_moon_create_info()
    if not moon_create.get("supported"):
        respond(
            {
                "ok": False,
                "error": moon_create.get("error") or "当前环境不支持创建 moon",
            }
        )

    root_identity = moon_create.get("rootIdentity") or ""
    seed = moon_create.get("seed") or ""
    stable_endpoints = parse_stable_endpoints(body.get("stableEndpoints"))
    result = build_moon_artifacts(
        root_identity, seed, body.get("worldId"), stable_endpoints
    )

    save_created_moon_entry(
        result.get("worldId") or "",
        seed,
        root_identity,
        stable_endpoints,
        active=False,
        timestamp=current_timestamp(),
        sort_index=next_created_moon_sort_index(),
        orbit_command=result.get("orbitCommand") or "",
        moon_file_name=result.get("moonFileName") or "",
        moon_file_base64=result.get("moonFileBase64") or "",
    )
    remove_joined_moon_registry(result.get("worldId") or "")
    append_moon_audit("moon_create", result.get("worldId") or "", seed, "created moon")

    payload = collect_status()
    payload["message"] = f"已创建 moon {result.get('worldId') or ''}"
    payload["moonCreateResult"] = result
    payload["moon"] = moon_summary(
        next(
            (
                item
                for item in payload.get("createdMoons", [])
                if item.get("id") == result.get("worldId")
            ),
            None,
        )
    )
    respond(payload)


def handle_moon_remove(body):
    world_id = validate_moon_world_id(body.get("worldId"))
    entry = find_created_moon_registry(world_id)
    if not entry:
        respond({"ok": False, "error": f"未找到已创建的 moon {world_id}"})
        return
    if bool(entry.get("active")):
        ok, out, err, _ = zerotier_exec("deorbit", world_id)
        if not ok:
            append_moon_audit(
                "moon_remove_failed",
                world_id if world_id else "",
                created_moon_seed(entry),
                (err or out or "移除 moon 失败").strip(),
            )
            respond({"ok": False, "error": (err or out or "移除 moon 失败").strip()})
    remove_created_moon_registry(world_id)
    remove_joined_moon_registry(world_id)
    append_moon_audit(
        "moon_remove",
        world_id if world_id else "",
        created_moon_seed(entry),
        "removed created moon",
    )
    payload = collect_status()
    payload["message"] = f"已移除已创建 moon {world_id}"
    respond(payload)


def main():
    action = (get_query_param("action") or "status").strip().lower()
    if action == "status":
        respond(collect_status())

    body = read_post_json()
    if action == "join":
        handle_join(body)
    if action == "leave":
        handle_leave(body)
    if action == "network_set":
        handle_network_set(body)
    if action == "moon_join":
        handle_moon_join(body)
    if action == "moon_start":
        handle_moon_start(body)
    if action == "moon_stop":
        handle_moon_stop(body)
    if action == "moon_leave":
        handle_moon_leave(body)
    if action == "moon_remove":
        handle_moon_remove(body)
    if action == "moon_update":
        handle_moon_update(body)
    if action == "moon_create":
        handle_moon_create(body)

    respond({"ok": False, "error": "unknown action"})


if __name__ == "__main__":
    main()
