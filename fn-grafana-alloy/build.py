#!/usr/bin/env python3
import os
import re
import sys
import stat
import shutil
import tarfile
import zipfile
import tempfile
import platform
import urllib.request
import urllib.error

WORKDIR = os.path.dirname(os.path.abspath(__file__))

ARCHS = ["x86_64", "aarch64"]
ALLOY_ASSET = {
    "x86_64": "alloy-linux-amd64",
    "aarch64": "alloy-linux-arm64",
}


def get_latest_version():
    url = "https://github.com/grafana/alloy/releases/latest"
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=30)
        effective_url = resp.url
        tag = effective_url.rstrip("/").split("/")[-1]
        version = re.sub(r"^[vV]", "", tag)
        if not version:
            raise ValueError("Empty version")
        return version
    except Exception as e:
        print(f"ERROR: Failed to get latest version: {e}", file=sys.stderr)
        sys.exit(1)


def download_file(url, dest):
    if os.path.exists(dest):
        print(f"  Using cached: {dest}")
        return
    print(f"  Downloading from {url} ...")
    urllib.request.urlretrieve(url, dest)


def update_manifest_version(manifest_path, version):
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r"^version\s*=.*",
        f"version               = {version}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_manifest(manifest_path):
    result = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
    return result


def main():
    alloy_version = sys.argv[1] if len(sys.argv) > 1 else get_latest_version()
    print(f"Building Grafana Alloy v{alloy_version} ...")

    tmpdir = tempfile.gettempdir()

    for arch in ARCHS:
        asset = ALLOY_ASSET[arch]
        url = f"https://github.com/grafana/alloy/releases/download/v{alloy_version}/{asset}.zip"
        zipfile_path = os.path.join(tmpdir, f"{asset}-{alloy_version}.zip")

        print(f"Downloading Alloy for {arch} ...")
        download_file(url, zipfile_path)

        extract_dir = os.path.join(tmpdir, f"alloy-extract-{arch}")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zipfile_path, "r") as zf:
            zf.extractall(extract_dir)

        bin_dir = os.path.join(WORKDIR, "app", "bin", arch)
        os.makedirs(bin_dir, exist_ok=True)

        src = os.path.join(extract_dir, asset)
        dst = os.path.join(bin_dir, "alloy")
        shutil.move(src, dst)

        if platform.system() != "Windows":
            st = os.stat(dst)
            os.chmod(dst, st.st_mode | stat.S_IEXEC)

        shutil.rmtree(extract_dir, ignore_errors=True)
        print(f"  Done: app/bin/{arch}/alloy")

    manifest_path = os.path.join(WORKDIR, "manifest")
    update_manifest_version(manifest_path, alloy_version)

    manifest = parse_manifest(manifest_path)
    appname = manifest.get("appname", "")
    version = manifest.get("version", "")
    platform_val = manifest.get("platform", "")

    app_tgz = os.path.join(WORKDIR, "app.tgz")
    fpk_name = f"{appname}_{platform_val}_v{version}.fpk"
    fpk_path = os.path.join(os.path.dirname(WORKDIR), fpk_name)

    if os.path.exists(app_tgz):
        os.remove(app_tgz)
    if os.path.exists(fpk_path):
        os.remove(fpk_path)

    with tarfile.open(app_tgz, "w:gz") as tar:
        tar.add(os.path.join(WORKDIR, "app"), arcname=".")

    fpk_members = [
        "cmd",
        "config",
        "i18n",
        "wizard",
        "app.tgz",
        "ICON.PNG",
        "ICON_256.PNG",
        "manifest",
    ]
    with tarfile.open(fpk_path, "w:gz") as tar:
        for member in fpk_members:
            full_path = os.path.join(WORKDIR, member)
            if not os.path.exists(full_path):
                continue
            tar.add(full_path, arcname=member)

    if os.path.exists(app_tgz):
        os.remove(app_tgz)

    for arch in ARCHS:
        alloy_bin = os.path.join(WORKDIR, "app", "bin", arch, "alloy")
        if os.path.exists(alloy_bin):
            os.remove(alloy_bin)

    print(f"Done: {fpk_path}")


if __name__ == "__main__":
    main()
