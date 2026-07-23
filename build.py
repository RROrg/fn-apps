#!/usr/bin/env python3
import os
import re
import sys
import stat
import json
import shutil
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


def resolve_manifest_value(app_dir, key, *, lang="zh"):
    app_dir = Path(app_dir)
    manifest = parse_key_value_file(app_dir / "manifest")
    value = manifest.get(key, "")
    i18n = parse_i18n(app_dir / "i18n" / lang)

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


def app_build_script(app_dir):
    if (app_dir / "build.py").is_file():
        return [sys.executable, str(app_dir / "build.py")]
    if is_windows() and (app_dir / "build.ps1").is_file():
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(app_dir / "build.ps1"),
        ]
    if not is_windows() and (app_dir / "build.sh").is_file():
        return ["bash", str(app_dir / "build.sh")]
    return None


def package_name(app_dir):
    app_name = resolve_manifest_value(app_dir, "appname")
    version = resolve_manifest_value(app_dir, "version")
    target_platform = (
        resolve_manifest_value(app_dir, "platform")
        or resolve_manifest_value(app_dir, "arch")
        or "all"
    )
    return app_name, version, target_platform


def build_app(root, fnpack, app_dir):
    app_name, version, target_platform = package_name(app_dir)
    print(f"Building {app_dir.name} ...", flush=True)

    script = app_build_script(app_dir)
    if script:
        before = {path.resolve() for path in root.glob("*.fpk")}
        run(script, cwd=root)
        app_name, version, target_platform = package_name(app_dir)
        target = root / f"{app_name}_{target_platform}_v{version}.fpk"
        if target.is_file():
            return target
        created = sorted(
            [
                path
                for path in root.glob(f"{app_name}_*_v*.fpk")
                if path.resolve() not in before
            ],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if created:
            return created[0]
    else:
        run([fnpack, "build", "--directory", app_dir], cwd=root)

    source = root / f"{app_name}.fpk"
    target = root / f"{app_name}_{target_platform}_v{version}.fpk"
    if source.is_file():
        if target.exists():
            target.unlink()
        source.replace(target)
    if not target.is_file():
        raise RuntimeError(f"missing output package: {target.name}")
    return target


def package_size(path):
    return f"{path.stat().st_size / 1024 / 1024:.3f}"


def app_metadata(root, app_dir, package_path, repo, tag):
    app_name, version, target_platform = package_name(app_dir)
    desc = resolve_manifest_value(app_dir, "desc")
    display_name = resolve_manifest_value(app_dir, "display_name")
    install_type = resolve_manifest_value(app_dir, "install_type")
    distributor = resolve_manifest_value(app_dir, "distributor")
    distributor_url = resolve_manifest_value(app_dir, "distributor_url")
    storage_label = "系统空间" if install_type == "root" else "存储空间"
    docker_string = (
        "true" if (app_dir / "app/docker/docker-compose.yaml").exists() else "false"
    )
    repo = repo or "RROrg/fn-apps"
    tag = tag or "local"
    return {
        "display_name": display_name,
        "platform": target_platform,
        "version": version,
        "desc": desc,
        "icon": f"https://raw.githubusercontent.com/{repo}/refs/heads/main/{app_dir.name}/ICON_256.PNG",
        "distributor": distributor,
        "distributor_url": distributor_url,
        "bug_report_url": f"https://github.com/{repo}/issues",
        "labels": "工具",
        "size": package_size(package_path),
        "download_url": f"https://github.com/{repo}/releases/download/{tag}/{package_path.name}",
        "install_type": storage_label,
        "isdocker": docker_string,
        "changelog": f"Initial release of {app_name} package.",
    }


def write_metadata(root, rows, repo, tag):
    apps_list = root / "apps-list.md"
    lines = [
        "| 应用名称 | 显示名称 | 版本 | 平台 | 描述 |",
        "|---------|---------|------|------|------|",
    ]
    for row in rows:
        meta = row["meta"]
        lines.append(
            f"| {row['app_name']} | {meta['display_name']} | v{meta['version']} | {meta['platform']} | {meta['desc']} |"
        )
    lines.append("")
    lines.append(f"![](https://img.shields.io/github/downloads/{repo}/{tag}/total)")
    apps_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fnpack = {row["app_dir"].name: row["meta"] for row in rows}
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
    parser.add_argument("--tag", default=os.environ.get("TAG", "local"))
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
    for app_dir in discover_apps(root, args.apps):
        package_path = build_app(root, fnpack, app_dir)
        app_name, _version, _platform = package_name(app_dir)
        if args.metadata:
            rows.append(
                {
                    "app_dir": app_dir,
                    "app_name": app_name,
                    "meta": app_metadata(
                        root, app_dir, package_path, args.repo, args.tag
                    ),
                }
            )

    if args.metadata:
        write_metadata(root, rows, args.repo, args.tag)


if __name__ == "__main__":
    main()
