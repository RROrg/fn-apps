# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import argparse
import base64
import json
import mimetypes
import os
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
from urllib.parse import unquote, urlsplit


def _env(name, default=""):
    return os.environ.get(name, "").strip() or default


APP_NAME = _env("TRIM_APPNAME", "fn-audioplayer")

SUPPORTED_FORMATS = {"mp3", "wav", "ogg", "flac", "m4a", "aac", "wma", "ape"}


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


def command_exists(name):
    return shutil.which(name) is not None


def run_ok(args, timeout=None, env=None):
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except FileNotFoundError:
        return False, "", f"{args[0]} not found"
    except Exception as exc:
        return False, "", str(exc)


def _pactl_available(audio_env=None):
    if not command_exists("pactl"):
        return False
    ok, _, _ = run_ok(["pactl", "info"], timeout=5, env=audio_env or get_audio_env())
    return ok


def ensure_audio_service():
    audio_env = get_audio_env()
    if _pactl_available(audio_env):
        return True
    if command_exists("pulseaudio"):
        run_ok(
            ["pulseaudio", "--start", "--fail=false", "--log-target=stderr"],
            timeout=8,
            env=audio_env,
        )
        for _ in range(20):
            audio_env = get_audio_env()
            if _pactl_available(audio_env):
                return True
            time.sleep(0.2)
    if command_exists("wpctl"):
        ok, _, _ = run_ok(["wpctl", "status"], timeout=5, env=audio_env)
        return ok
    return False


MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
    ".ape": "audio/x-ape",
}


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
            self.serve_api(path, parsed.query)
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
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def serve_api(self, path, query):
        from urllib.parse import parse_qs

        params = parse_qs(query, keep_blank_values=True)

        if path == "/api/health":
            self.json_response({"status": "ok", "service": APP_NAME})
        elif path == "/api/audio/info":
            self.handle_audio_info(params)
        elif path == "/api/audio/stream":
            self.handle_audio_stream(params)
        elif path == "/api/audio/metadata":
            self.handle_audio_metadata(params)
        elif path == "/api/audio/cover":
            self.handle_audio_cover(params)
        elif path == "/api/playlist/list":
            self.handle_playlist_list(params)
        elif path == "/api/lyrics":
            self.handle_lyrics(params)
        elif path == "/api/browse":
            self.handle_browse(params)
        elif path == "/api/output/devices":
            self.handle_output_devices()
        elif path == "/api/output/status":
            self.handle_output_status()
        elif path == "/api/output/play":
            self.handle_output_play()
        elif path == "/api/output/stop":
            self.handle_output_stop()
        elif path == "/api/output/pause":
            self.handle_output_pause()
        elif path == "/api/output/resume":
            self.handle_output_resume()
        elif path == "/api/output/seek":
            self.handle_output_seek()
        elif path == "/api/output/volume":
            self.handle_output_volume()
        else:
            self.json_response({"error": "Not found"}, 404)

    def json_response(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def handle_audio_info(self, params):
        file_param = self._get_param(params, "file")
        if not file_param:
            self.json_response({"error": "Missing file parameter"}, 400)
            return
        file_path = file_param
        if not os.path.exists(file_path):
            self.json_response({"error": "File not found"}, 404)
            return
        try:
            stats = os.stat(file_path)
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            self.json_response(
                {
                    "file": file_path,
                    "size": stats.st_size,
                    "format": ext,
                    "isSupported": ext in SUPPORTED_FORMATS,
                    "modifiedTime": stats.st_mtime,
                    "createdTime": stats.st_ctime,
                }
            )
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_audio_stream(self, params):
        file_param = self._get_param(params, "file")
        if not file_param:
            self.json_response({"error": "Missing file parameter"}, 400)
            return
        file_path = file_param
        if not os.path.exists(file_path):
            self.json_response({"error": "File not found"}, 404)
            return
        try:
            file_size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            mime_type = MIME_TYPES.get(ext, "audio/mpeg")

            if file_size == 0:
                self.send_response(HTTPStatus.NO_CONTENT)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            range_header = self.headers.get("Range", "").strip()
            max_stream_chunk = 1024 * 1024
            start = 0
            end = min(file_size - 1, max_stream_chunk - 1)

            if range_header:
                try:
                    range_value = (
                        range_header.replace("bytes=", "", 1).split(",", 1)[0].strip()
                    )
                    first, _, last = range_value.partition("-")
                    if first:
                        start = int(first)
                        end = (
                            int(last)
                            if last
                            else min(file_size - 1, start + max_stream_chunk - 1)
                        )
                    else:
                        suffix_length = int(last)
                        if suffix_length <= 0:
                            raise ValueError("Invalid suffix range")
                        start = max(0, file_size - suffix_length)
                        end = file_size - 1
                except (TypeError, ValueError):
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

            if start >= file_size or end < start:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            end = min(end, file_size - 1)
            content_length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(content_length))
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            if self.command != "HEAD":
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = f.read(min(remaining, 65536))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_audio_metadata(self, params):
        file_param = self._get_param(params, "file")
        if not file_param:
            self.json_response({"error": "Missing file parameter"}, 400)
            return
        file_path = file_param
        if not os.path.exists(file_path):
            self.json_response({"error": "File not found"}, 404)
            return
        try:
            basename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            stats = os.stat(file_path)
            title = os.path.splitext(basename)[0]
            artist = ""
            album = ""
            try:
                import mutagen

                mf = mutagen.File(file_path)
                if mf is not None:
                    tags = mf.tags
                    if tags is not None:
                        title = _get_tag(tags, ["title"], title)
                        artist = _get_tag(tags, ["artist"], "")
                        album = _get_tag(tags, ["album"], "")
            except Exception:
                pass
            self.json_response(
                {
                    "filename": basename,
                    "path": file_path,
                    "format": ext,
                    "size": stats.st_size,
                    "sizeReadable": format_file_size(stats.st_size),
                    "modifiedTime": stats.st_mtime,
                    "title": title,
                    "artist": artist,
                    "album": album,
                }
            )
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_audio_cover(self, params):
        file_param = self._get_param(params, "file")
        if not file_param:
            self.json_response({"error": "Missing file parameter"}, 400)
            return
        file_path = file_param
        if not os.path.exists(file_path):
            self.json_response({"error": "File not found"}, 404)
            return
        try:
            cover_data = None
            cover_mime = "image/jpeg"
            try:
                import mutagen

                mf = mutagen.File(file_path)
                if mf is not None:
                    cover_data, cover_mime = _extract_cover(mf)
            except Exception:
                pass
            if cover_data is None:
                dir_path = os.path.dirname(file_path)
                for name in (
                    "cover.jpg",
                    "cover.jpeg",
                    "cover.png",
                    "folder.jpg",
                    "folder.jpeg",
                    "folder.png",
                    "Cover.jpg",
                    "Cover.jpeg",
                    "Cover.png",
                    "Folder.jpg",
                    "Folder.jpeg",
                    "Folder.png",
                ):
                    candidate = os.path.join(dir_path, name)
                    if os.path.isfile(candidate):
                        with open(candidate, "rb") as f:
                            cover_data = f.read()
                        ext = os.path.splitext(name)[1].lower()
                        cover_mime = "image/png" if ext == ".png" else "image/jpeg"
                        break
            if cover_data is not None:
                self.send_response(200)
                self.send_header("Content-Type", cover_mime)
                self.send_header("Content-Length", str(len(cover_data)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(cover_data)
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_playlist_list(self, params):
        dir_param = self._get_param(params, "dir")
        dir_path = dir_param if dir_param else "/"
        if not os.path.exists(dir_path):
            self.json_response({"error": "Directory not found"}, 404)
            return
        try:
            files = []
            for name in sorted(os.listdir(dir_path)):
                ext = os.path.splitext(name)[1].lower().lstrip(".")
                if ext not in SUPPORTED_FORMATS:
                    continue
                full_path = os.path.join(dir_path, name)
                if not os.path.isfile(full_path):
                    continue
                stats = os.stat(full_path)
                files.append(
                    {
                        "name": name,
                        "path": full_path,
                        "size": stats.st_size,
                        "sizeReadable": format_file_size(stats.st_size),
                        "modifiedTime": stats.st_mtime,
                    }
                )
            self.json_response(
                {
                    "directory": dir_path,
                    "count": len(files),
                    "files": files,
                }
            )
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_lyrics(self, params):
        file_param = self._get_param(params, "file")
        if not file_param:
            self.json_response({"error": "Missing file parameter"}, 400)
            return
        file_path = file_param
        if not os.path.exists(file_path):
            self.json_response({"error": "File not found"}, 404)
            return
        try:
            base_name = os.path.splitext(file_path)[0]
            dir_path = os.path.dirname(file_path)
            lrc_content = None
            lrc_file = None
            for candidate in [base_name + ".lrc", base_name + ".LRC"]:
                if os.path.isfile(candidate):
                    lrc_file = candidate
                    break
            if lrc_file is None:
                for entry in os.listdir(dir_path):
                    entry_lower = entry.lower()
                    base_lower = os.path.basename(base_name).lower()
                    if entry_lower == base_lower + ".lrc":
                        lrc_file = os.path.join(dir_path, entry)
                        break
            if lrc_file and os.path.isfile(lrc_file):
                for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "big5", "latin-1"):
                    try:
                        with open(lrc_file, "r", encoding=enc) as f:
                            lrc_content = f.read()
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                if lrc_content is None:
                    with open(lrc_file, "rb") as f:
                        lrc_content = f.read().decode("utf-8", errors="replace")
            self.json_response(
                {
                    "found": lrc_content is not None,
                    "lyrics": lrc_content,
                    "lrcFile": os.path.basename(lrc_file) if lrc_file else None,
                }
            )
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_browse(self, params):
        dir_param = self._get_param(params, "dir")
        dir_path = dir_param if dir_param else "/"
        if not os.path.isdir(dir_path):
            self.json_response({"error": "Directory not found"}, 404)
            return
        try:
            entries = []
            try:
                items = sorted(os.listdir(dir_path))
            except PermissionError:
                self.json_response({"error": "Permission denied"}, 403)
                return
            for name in items:
                if name.startswith("."):
                    continue
                full_path = os.path.join(dir_path, name)
                try:
                    is_dir = os.path.isdir(full_path)
                    is_audio = (
                        os.path.isfile(full_path)
                        and os.path.splitext(name)[1].lower().lstrip(".")
                        in SUPPORTED_FORMATS
                    )
                    if not is_dir and not is_audio:
                        continue
                    entries.append(
                        {
                            "name": name,
                            "path": full_path,
                            "isDir": is_dir,
                            "isAudio": is_audio,
                        }
                    )
                except (PermissionError, OSError):
                    continue
            parent = os.path.dirname(dir_path) if dir_path != "/" else None
            self.json_response(
                {
                    "currentDir": dir_path,
                    "parentDir": parent,
                    "entries": entries,
                }
            )
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    @staticmethod
    def _get_param(params, name):
        values = params.get(name)
        return values[0] if values else None

    def _parse_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                return json.loads(body.decode("utf-8"))
        except Exception:
            pass
        return {}

    def handle_output_devices(self):
        devices = server_player.get_devices()
        self.json_response({"devices": devices})

    def handle_output_status(self):
        server_player.touch_poll()
        status = server_player.get_status()
        self.json_response(status)

    def handle_output_play(self):
        data = self._parse_json_body()
        file_path = data.get("file")
        if not file_path:
            self.json_response({"error": "Missing file parameter"}, 400)
            return
        if not os.path.exists(file_path):
            self.json_response({"error": "File not found"}, 404)
            return
        sink = data.get("sink")
        position = data.get("position", 0)
        server_player.play(file_path, sink=sink, position=position)
        self.json_response({"ok": True})

    def handle_output_stop(self):
        server_player.stop()
        self.json_response({"ok": True})

    def handle_output_pause(self):
        server_player.pause()
        self.json_response({"ok": True})

    def handle_output_resume(self):
        server_player.resume()
        self.json_response({"ok": True})

    def handle_output_seek(self):
        data = self._parse_json_body()
        position = data.get("position", 0)
        server_player.seek(position)
        self.json_response({"ok": True})

    def handle_output_volume(self):
        data = self._parse_json_body()
        volume = data.get("volume", 70)
        sink = data.get("sink")
        server_player.set_volume(volume, sink=sink)
        self.json_response({"ok": True})


def _get_tag(tags, keys, default=""):
    for key in keys:
        val = tags.get(key)
        if val is not None:
            if isinstance(val, list) and len(val) > 0:
                return str(val[0])
            return str(val)
    return default


def _extract_cover(mf):
    cover_data = None
    cover_mime = "image/jpeg"
    try:
        if hasattr(mf, "tags") and mf.tags is not None:
            tag_type = type(mf.tags).__name__
            if tag_type == "ID3":
                for frame in mf.tags.values():
                    if frame.FrameID == "APIC":
                        cover_data = frame.data
                        cover_mime = frame.mime or "image/jpeg"
                        break
            elif tag_type in ("VorbisComment",):
                pictures = mf.tags.get("metadata_block_picture", [])
                if pictures:
                    import base64 as b64

                    raw = b64.b64decode(str(pictures[0]))
                    from mutagen.flac import Picture

                    pic = Picture(raw)
                    cover_data = pic.data
                    cover_mime = pic.mime or "image/jpeg"
            elif tag_type == "_MP4Tags":
                covr = mf.tags.get("covr")
                if covr:
                    import mutagen.mp4

                    cover_data = bytes(covr[0])
                    img_format = covr[0].imageformat
                    if img_format == mutagen.mp4.MP4Cover.FORMAT_PNG:
                        cover_mime = "image/png"
                    else:
                        cover_mime = "image/jpeg"
            elif hasattr(mf, "pictures"):
                pics = mf.pictures
                if pics:
                    cover_data = pics[0].data
                    cover_mime = pics[0].mime or "image/jpeg"
    except Exception:
        pass
    return cover_data, cover_mime


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


def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{round(size * 100) / 100} {units[i]}"


class ServerPlayer:
    def __init__(self):
        self._process = None
        self._lock = threading.Lock()
        self._sink = None
        self._file = None
        self._volume = 70
        self._state = "stopped"
        self._start_time = 0
        self._pause_position = 0
        self._duration = 0
        self._start_offset = 0
        self._last_poll_time = 0
        self._watcher_thread = threading.Thread(target=self._watcher, daemon=True)
        self._watcher_thread.start()

    def _watcher(self):
        while True:
            time.sleep(3)
            with self._lock:
                if self._state in ("playing", "paused") and self._last_poll_time > 0:
                    if time.time() - self._last_poll_time > 5:
                        self._stop_internal()
                        self._state = "stopped"

    def touch_poll(self):
        with self._lock:
            self._last_poll_time = time.time()

    def get_devices(self):
        try:
            ensure_audio_service()
            result = subprocess.run(
                ["pactl", "list", "sinks"],
                capture_output=True,
                text=True,
                timeout=5,
                env=get_audio_env(),
            )
            devices = []
            current = {}
            for line in result.stdout.split("\n"):
                stripped = line.strip()
                if stripped.startswith("Sink #"):
                    if current.get("id"):
                        devices.append(current)
                    current = {"index": stripped.split("#")[1].strip()}
                elif stripped.startswith("Name:"):
                    current["id"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("Description:"):
                    current["name"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("State:"):
                    current["state"] = stripped.split(":", 1)[1].strip()
            if current.get("id"):
                devices.append(current)
            return devices
        except Exception:
            return []

    def play(self, file_path, sink=None, position=0):
        with self._lock:
            self._stop_internal()
            self._sink = sink
            self._file = file_path
            self._start_offset = position
            self._duration = self._get_duration(file_path)
            ensure_audio_service()
            env = get_audio_env()
            if sink:
                env["PULSE_SINK"] = sink
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
            if position > 0:
                cmd.extend(["-ss", str(position)])
            cmd.append(file_path)
            try:
                self._process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._state = "playing"
                self._start_time = time.time() - position
                self._pause_position = 0
                t = threading.Thread(target=self._monitor, daemon=True)
                t.start()
            except Exception:
                self._state = "stopped"

    def _get_duration(self, file_path):
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0

    def _monitor(self):
        proc = self._process
        if proc:
            proc.wait()
            with self._lock:
                if self._state in ("playing", "paused") and self._process is proc:
                    if proc.returncode == 0:
                        self._state = "ended"
                    else:
                        self._state = "stopped"
                    self._process = None

    def stop(self):
        with self._lock:
            self._stop_internal()
            self._state = "stopped"

    def _stop_internal(self):
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                pass
            if self._process.poll() is None:
                try:
                    self._process.kill()
                    self._process.wait(timeout=3)
                except Exception:
                    pass
            self._process = None

    def pause(self):
        with self._lock:
            if self._process and self._state == "playing":
                try:
                    self._process.send_signal(
                        signal.SIGSTOP  # pyright: ignore[reportAttributeAccessIssue]
                    )
                    self._state = "paused"
                    self._pause_position = time.time() - self._start_time
                except Exception:
                    pass

    def resume(self):
        with self._lock:
            if self._process and self._state == "paused":
                try:
                    self._process.send_signal(
                        signal.SIGCONT  # pyright: ignore[reportAttributeAccessIssue]
                    )
                    self._state = "playing"
                    self._start_time = time.time() - self._pause_position
                except Exception:
                    pass

    def set_volume(self, volume, sink=None):
        self._volume = volume
        target_sink = sink or self._sink
        if target_sink:
            try:
                ensure_audio_service()
                pulse_vol = int(65536 * volume / 100)
                subprocess.run(
                    ["pactl", "set-sink-volume", target_sink, str(pulse_vol)],
                    timeout=3,
                    env=get_audio_env(),
                )
            except Exception:
                pass

    def seek(self, position):
        with self._lock:
            file_path = self._file
            sink = self._sink
            was_playing = self._state == "playing"
            self._stop_internal()
        if was_playing and file_path:
            self.play(file_path, sink, position)
        else:
            with self._lock:
                self._state = "stopped"
                self._start_offset = position

    def get_status(self):
        with self._lock:
            position = 0
            if self._state == "playing":
                position = time.time() - self._start_time
            elif self._state == "paused":
                position = self._pause_position
            return {
                "state": self._state,
                "position": round(position, 2),
                "duration": round(self._duration, 2),
                "file": self._file,
                "sink": self._sink,
                "volume": self._volume,
            }


server_player = ServerPlayer()


def main():
    parser = argparse.ArgumentParser(description="fn-audioplayer Unix socket server")
    parser.add_argument("--unix-socket", required=True)
    parser.add_argument("--base-path", default="/app/fn-audioplayer")
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
