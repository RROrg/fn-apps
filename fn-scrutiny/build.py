#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

RELEASES_URL = "https://github.com/Starosdev/scrutiny/releases"

ARCHS = ["x86_64", "aarch64"]

COLLECTOR_ASSET = {
    "x86_64": "scrutiny-collector-metrics-linux-amd64",
    "aarch64": "scrutiny-collector-metrics-linux-arm64",
}

WEB_ASSET = {
    "x86_64": "scrutiny-web-linux-amd64",
    "aarch64": "scrutiny-web-linux-arm64",
}

FRONTEND_ASSET = "scrutiny-web-frontend.tar.gz"


def _http_head(url, timeout=20):
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "fn-apps-builder")
    return urllib.request.urlopen(req, timeout=timeout)


def _asset_exists(version, asset):
    """Check an asset exists for a version via the download redirect (no API quota)."""
    try:
        _http_head(f"{RELEASES_URL}/download/v{version}/{asset}")
        return True
    except Exception:
        return False


def get_latest_version():
    required_assets = (
        list(COLLECTOR_ASSET.values()) + list(WEB_ASSET.values()) + [FRONTEND_ASSET]
    )

    # 1) Resolve the latest tag via the /releases/latest redirect (no api.github.com)
    try:
        resp = _http_head(f"{RELEASES_URL}/latest")
        tag = resp.geturl().rstrip("/").split("/")[-1]
        version = re.sub(r"^[vV]", "", tag)
        if version:
            missing = [a for a in required_assets if not _asset_exists(version, a)]
            if not missing:
                return version
            print(f"  Note: latest {version} is missing assets: {missing}")
    except Exception as e:
        print(f"  Note: failed to resolve latest tag: {e}")

    # 2) Fall back to the local manifest version
    local = parse_manifest(Path(__file__).resolve().parent / "manifest").get("version", "")
    if local:
        print(f"  Warning: falling back to local manifest version {local}")
        return local

    raise RuntimeError("Could not determine a version with all required assets")


def cache_dir():
    if sys.platform == "win32":
        d = Path(os.environ.get("TEMP", tempfile.gettempdir()))
    else:
        d = Path("/tmp")
    return d


def download_with_cache(url, dest):
    if dest.is_file():
        print(f"  Using cached: {dest}")
        return
    print(f"  Downloading {url}")
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "fn-apps-builder")
    with urllib.request.urlopen(req, timeout=120) as resp:
        with open(str(dest), "wb") as f:
            shutil.copyfileobj(resp, f)


def parse_manifest(path):
    data = {}
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*(\w+)\s*=\s*(.*?)\s*$", raw)
        if m:
            value = m.group(2).strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            data[m.group(1)] = value
    return data


def update_manifest_version(manifest_path, version):
    text = Path(manifest_path).read_text(encoding="utf-8")
    text = re.sub(
        r"^version\s*=.*$",
        f"version               = {version}",
        text,
        flags=re.MULTILINE,
    )
    Path(manifest_path).write_text(text, encoding="utf-8")


def make_tar_gz(output_path, source_dir, entries):
    with tarfile.open(str(output_path), "w:gz") as tar:
        for entry in entries:
            src = source_dir / entry
            if src.is_file():
                tar.add(str(src), arcname=entry)
            elif src.is_dir():
                tar.add(str(src), arcname=entry)


def main():
    parser = argparse.ArgumentParser(description="Build Scrutiny FPK package")
    parser.add_argument("version", nargs="?", help="Version to build (default: latest)")
    args = parser.parse_args()

    workdir = Path(__file__).resolve().parent
    version = args.version or get_latest_version()
    print(f"Building Scrutiny v{version} ...")

    cachedir = cache_dir()
    app_dir = workdir / "app"

    for arch in ARCHS:
        bin_dir = app_dir / "bin" / arch
        bin_dir.mkdir(parents=True, exist_ok=True)

        collector_asset = COLLECTOR_ASSET[arch]
        collector_url = f"{RELEASES_URL}/download/v{version}/{collector_asset}"
        collector_cache = cachedir / f"{collector_asset}-{version}"
        download_with_cache(collector_url, collector_cache)
        dest = bin_dir / "scrutiny-collector-metrics"
        shutil.copy2(str(collector_cache), str(dest))
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"  Done: app/bin/{arch}/scrutiny-collector-metrics")

        web_asset = WEB_ASSET[arch]
        web_url = f"{RELEASES_URL}/download/v{version}/{web_asset}"
        web_cache = cachedir / f"{web_asset}-{version}"
        download_with_cache(web_url, web_cache)
        dest = bin_dir / "scrutiny-web"
        shutil.copy2(str(web_cache), str(dest))
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"  Done: app/bin/{arch}/scrutiny-web")

    frontend_url = f"{RELEASES_URL}/download/v{version}/{FRONTEND_ASSET}"
    frontend_cache = cachedir / f"{FRONTEND_ASSET}-{version}"
    download_with_cache(frontend_url, frontend_cache)

    web_dir = app_dir / "www"
    if web_dir.is_dir():
        shutil.rmtree(str(web_dir))
    web_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(frontend_cache), "r:gz") as tar:
        tar.extractall(str(web_dir))
    print("  Done: app/www/")

    update_manifest_version(workdir / "manifest", version)

    manifest = parse_manifest(workdir / "manifest")
    appname = manifest.get("appname", "fn-scrutiny")
    pkg_version = manifest.get("version", version)
    platform = manifest.get("platform", "all")

    app_tgz = workdir / "app.tgz"
    fpk_name = f"{appname}_{platform}_v{pkg_version}.fpk"
    fpk_path = workdir.parent / fpk_name

    if app_tgz.is_file():
        app_tgz.unlink()
    if fpk_path.is_file():
        fpk_path.unlink()

    with tarfile.open(str(app_tgz), "w:gz") as tar:
        for item in app_dir.iterdir():
            tar.add(str(item), arcname=item.name)

    with tarfile.open(str(fpk_path), "w:gz") as tar:
        for name in [
            "cmd",
            "config",
            "i18n",
            "wizard",
            "app.tgz",
            "ICON.PNG",
            "ICON_256.PNG",
            "manifest",
        ]:
            src = workdir / name
            if src.is_file() or src.is_dir():
                tar.add(str(src), arcname=name)

    app_tgz.unlink()

    for arch in ARCHS:
        collector = app_dir / "bin" / arch / "scrutiny-collector-metrics"
        web = app_dir / "bin" / arch / "scrutiny-web"
        if collector.is_file():
            collector.unlink()
        if web.is_file():
            web.unlink()
    if web_dir.is_dir():
        shutil.rmtree(str(web_dir))

    print(f"Done: {fpk_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
