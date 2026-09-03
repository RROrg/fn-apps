#!/usr/bin/env python3
import os
import re
import sys
import stat
import json
import time
import shutil
import hashlib
import argparse
import subprocess
import urllib.request
from pathlib import Path

FNPACK_VERSION = "1.2.3"
FNPACK_URLS = {
    "windows": f"https://static2.fnnas.com/fnpack/fnpack-{FNPACK_VERSION}-windows-amd64",
    "linux": f"https://static2.fnnas.com/fnpack/fnpack-{FNPACK_VERSION}-linux-amd64",
}
FYGOPACK_VERSION = "1.2.3"
FYGOPACK_URLS = {
    "windows": f"https://static2.fygonas.com/fygopack/fygopack-{FYGOPACK_VERSION}-windows-amd64",
    "linux": f"https://static2.fygonas.com/fygopack/fygopack-{FYGOPACK_VERSION}-linux-amd64",
}


WEB_APP_JS_URL = "https://cdn.jsdelivr.net/npm/@trimjs/web-app@latest/dist/index.js"


def is_windows():
    return sys.platform == "win32"


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def strip_config_value(value):
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    return value.replace('\\"', '"')


def parse_key_value_file(path):
    data = {}
    if not Path(path).is_file():
        return data
    for raw in read_text(path).splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*(.*?)\s*$", raw)
        if match:
            data[match.group(1)] = strip_config_value(match.group(2))
    return data


def parse_i18n(path):
    data = {}
    if not Path(path).is_file():
        return data
    section = ""
    for raw in read_text(path).splitlines():
        section_match = re.match(r"^\s*\[(.+)]\s*$", raw)
        if section_match:
            section = section_match.group(1).strip()
            continue
        value_match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*(.*?)\s*$", raw)
        if value_match and section:
            data[f"{section}.{value_match.group(1)}"] = strip_config_value(
                value_match.group(2)
            )
    return data


VAR_RE = re.compile(r"\$\{([A-Za-z0-9_.-]+)\.([A-Za-z0-9_.-]+)\}")


def resolve_manifest_value(appdir, key, *, lang="zh"):
    appdir = Path(appdir)
    manifest = parse_key_value_file(appdir / "manifest")
    value = manifest.get(key, "")
    i18n = parse_i18n(appdir / "i18n" / lang)

    def replace_var(match):
        ref = f"{match.group(1)}.{match.group(2)}"
        return i18n.get(ref, match.group(0))

    previous = None
    while previous != value:
        previous = value
        value = VAR_RE.sub(replace_var, value)
    return value


def run(cmd, *, cwd=None):
    printable = " ".join(str(part) for part in cmd)
    print(printable, flush=True)
    subprocess.run([str(part) for part in cmd], cwd=cwd, check=True)


def download_fnpack(root):
    binary = root / ("fnpack.exe" if is_windows() else "fnpack")
    # 用 fygopack 代替 fnpack
    url = FYGOPACK_URLS["windows" if is_windows() else "linux"]
    print(f"Downloading {url}", flush=True)
    urllib.request.urlretrieve(url, binary)
    if not is_windows():
        mode = binary.stat().st_mode
        binary.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return binary


def discover_apps(root, names):
    if names:
        candidates = [
            Path(name) if Path(name).is_absolute() else root / name for name in names
        ]
    else:
        candidates = sorted(
            [path for path in root.iterdir() if path.is_dir()],
            key=lambda item: item.name.lower(),
        )
    apps = []
    for app in candidates:
        if (app / "norelease").is_file():
            continue
        if not (app / "manifest").is_file():
            continue
        apps.append(app.resolve())
    return apps


def app_build_script(appdir):
    if (appdir / "build.py").is_file():
        return [sys.executable, str(appdir / "build.py")]
    if is_windows() and (appdir / "build.ps1").is_file():
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(appdir / "build.ps1"),
        ]
    if not is_windows() and (appdir / "build.sh").is_file():
        return ["bash", str(appdir / "build.sh")]
    return None


def build_app(root, fnpack, appdir):
    appname = resolve_manifest_value(appdir, "appname")
    version = resolve_manifest_value(appdir, "version")
    platform = resolve_manifest_value(appdir, "platform") or "all"
    print(f"Building {appdir.name} ...", flush=True)

    web_app_js = appdir / "app/www/web-app.js"
    if web_app_js.is_file():
        print(f"Downloading {WEB_APP_JS_URL}", flush=True)
        urllib.request.urlretrieve(WEB_APP_JS_URL, web_app_js)

    script = app_build_script(appdir)
    if script:
        before = {path.resolve() for path in root.glob("*.fpk")}
        run(script, cwd=root)
        appname = resolve_manifest_value(appdir, "appname")
        version = resolve_manifest_value(appdir, "version")
        platform = resolve_manifest_value(appdir, "platform") or "all"
        target = root / f"{appname}_{platform}_v{version}.fpk"
        if target.is_file():
            return target
        created = sorted(
            [
                path
                for path in root.glob(f"{appname}_*_v*.fpk")
                if path.resolve() not in before
            ],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if created:
            return created[0]
    else:
        run([fnpack, "build", "--directory", appdir], cwd=root)

    source = root / f"{appname}.fpk"
    target = root / f"{appname}_{platform}_v{version}.fpk"
    if source.is_file():
        if target.exists():
            target.unlink()
        source.replace(target)
    if not target.is_file():
        raise RuntimeError(f"missing output package: {target.name}")
    return target


def package_size(path):
    return int(path.stat().st_size)


def package_sha256(path):
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


# FnDepot V2 允许的固定分类，不能自行创造分类名称
V2_CATEGORIES = {
    "影音娱乐",
    "系统工具",
    "编程开发",
    "AI赋能",
    "生活服务",
    "智能智控",
    "教育学习",
    "游戏地带",
    "硬件驱动",
}


def app_metadata(root, appdir, package_path, repo, tag):
    appname = resolve_manifest_value(appdir, "appname")
    version = resolve_manifest_value(appdir, "version")
    platform = resolve_manifest_value(appdir, "platform") or "all"
    desc = resolve_manifest_value(appdir, "desc")
    display_name = resolve_manifest_value(appdir, "display_name")
    distributor = resolve_manifest_value(appdir, "distributor") or ""
    distributor_url = resolve_manifest_value(appdir, "distributor_url") or ""
    maintainer = resolve_manifest_value(appdir, "maintainer") or ""
    maintainer_url = resolve_manifest_value(appdir, "maintainer_url") or ""
    install_type = resolve_manifest_value(appdir, "install_type") or ""
    service_port = resolve_manifest_value(appdir, "service_port") or ""

    is_docker = (appdir / "app/docker/docker-compose.yaml").is_file()
    repo = repo or "RROrg/fn-apps"
    tag = tag or "local"

    # run_as 从 config/privilege 读取，只允许 package/root；install_type 空串表示存储空间，root 表示系统空间
    try:
        runs_as = (
            json.loads((appdir / "config/privilege").read_text(encoding="utf-8"))
            .get("defaults", {})
            .get("run-as", "package")
        )
        runs_as = runs_as if runs_as in ("package", "root") else "package"
    except Exception:
        runs_as = "package"

    # 优先使用 manifest 的 category，否则回退到固定的“系统工具”
    category = (
        resolve_manifest_value(appdir, "category")
        if resolve_manifest_value(appdir, "category") in V2_CATEGORIES
        else "系统工具"
    )

    app_node = {
        "appname": appname,
        "display_name": display_name,
        "desc": desc,
        "platform": [platform],
        "categories": [category],
        "icon_url": (
            f"https://raw.githubusercontent.com/{repo}/refs/heads/main/{appdir.name}/ICON_256.PNG"
        ),
        "maintainer": maintainer or None,
        "maintainer_url": maintainer_url or None,
        "distributor": distributor or None,
        "distributor_url": distributor_url or None,
        "bug_report_url": f"https://github.com/{repo}/issues",
        "run_as": runs_as,
        "install_type": install_type,
        "is_docker": is_docker,
        "service_port": service_port,
        "releases": {
            version: {
                "changelog": f"Initial release of {appname} package.",
                "packages": {
                    platform: {
                        "download_url": (
                            f"https://github.com/{repo}/releases/download/{tag}/{package_path.name}"
                        ),
                        "sha256": package_sha256(package_path),
                        "size": package_size(package_path),
                    }
                },
            }
        },
    }
    return app_node


def write_metadata(root, rows, repo, tag):
    repo = repo or "RROrg/fn-apps"
    tag = tag or "local"

    apps_list = root / "apps-list.md"
    lines = [
        "| 应用名称 | 显示名称 | 版本 | 平台 | 描述 |",
        "|---------|---------|------|------|------|",
    ]
    for node in rows:
        lines.append(
            f"| {node['appname']} | {node['display_name']} | v{next(iter(node["releases"]))} | {node['platform'][0]} | {node['desc']} |"
        )
    lines.append("")
    lines.append(f"![](https://img.shields.io/github/downloads/{repo}/{tag}/total)")
    apps_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # FnDepot V2: apps 必须是对象，键名为 appname，节点内不再包含 appname
    apps = {}
    for node in rows:
        appname = node["appname"]
        apps[appname] = {key: value for key, value in node.items() if key != "appname"}

    fnpack = {
        "schema_version": "2",
        "source_info": {
            "name": "RROrg",
            "author": "Ing",
            "homepage": f"https://github.com/{repo}",
            "description": "RROrg 的 fnOS 第三方应用源",
        },
        "apps": apps,
    }
    (root / "fnpack.json").write_text(
        json.dumps(fnpack, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Build fn-apps packages")
    parser.add_argument(
        "apps", nargs="*", help="App directories to build. Defaults to all fn-* apps."
    )
    parser.add_argument(
        "--repo", default=os.environ.get("GITHUB_REPOSITORY", "RROrg/fn-apps")
    )
    parser.add_argument(
        "--tag", default=os.environ.get("TAG", "local"), help="Tag for Releases"
    )
    parser.add_argument(
        "--metadata", action="store_true", help="Write apps-list.md and fnpack.json"
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    os.chdir(root)

    fnpack = root / ("fnpack.exe" if is_windows() else "fnpack")
    if not fnpack.is_file():
        fnpack = download_fnpack(root)

    rows = []
    for appdir in discover_apps(root, args.apps):
        package_path = build_app(root, fnpack, appdir)
        if args.metadata:
            rows.append(app_metadata(root, appdir, package_path, args.repo, args.tag))

    if args.metadata:
        write_metadata(root, rows, args.repo, args.tag)


if __name__ == "__main__":
    main()
