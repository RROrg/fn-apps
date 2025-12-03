#!/usr/bin/env python3
"""Lightweight scheduler backend with REST API and static file hosting."""
from __future__ import annotations

import argparse
import base64
import getpass
import json
import logging
import os
import hashlib
import hmac
import signal
import socket
import sqlite3
import ssl
import threading
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Set
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from subprocess import CompletedProcess, TimeoutExpired, run

try:
    import grp
    import pwd
except ImportError:  # pragma: no cover - non-POSIX systems
    grp = None  # type: ignore
    pwd = None  # type: ignore
from urllib.parse import parse_qs, urlparse, urlsplit, urlunsplit

###############################################################################
# Helpers and configuration
###############################################################################

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
PARD_DIR = os.path.abspath(os.path.join(ROOT_DIR, os.pardir))
STATIC_ROOT = os.path.join(PARD_DIR, "www")
DEFAULT_DB_PATH = os.path.join(ROOT_DIR, "scheduler.db")
DEFAULT_AUTH_PATH = os.path.join(ROOT_DIR, "auth.json")
IS_WINDOWS = os.name == "nt"
DB_LATEST_VERSION = 2
def _detect_default_account() -> str:
    for env_key in ("SCHEDULER_DEFAULT_ACCOUNT", "USERNAME", "USER"):
        value = os.environ.get(env_key)
        if value:
            return value
    try:
        return getpass.getuser()
    except Exception:  # pragma: no cover - fallback only
        return "current_user"

DEFAULT_ACCOUNT_NAME = _detect_default_account()
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 28256
TASK_TIMEOUT = int(os.environ.get("SCHEDULER_TASK_TIMEOUT", "900"))
CONDITION_TIMEOUT = int(os.environ.get("SCHEDULER_CONDITION_TIMEOUT", "60"))
MAX_LOOKAHEAD_MINUTES = 60 * 24 * 366  # one leap year
EVENT_TYPE_SCRIPT = "script"
EVENT_TYPE_BOOT = "system_boot"
EVENT_TYPE_SHUTDOWN = "system_shutdown"
EVENT_TYPES = {EVENT_TYPE_SCRIPT, EVENT_TYPE_BOOT, EVENT_TYPE_SHUTDOWN}
ALLOWED_ACCOUNT_GIDS = (0, 1000, 1001)
POSIX_ACCOUNT_SUPPORT = os.name == "posix" and pwd is not None and grp is not None


class AuthConfig:
    def __init__(self, username: str, password_hash: str, realm: str = "Scheduler"):
        self.username = username
        self.password_hash = password_hash.lower()
        self.realm = realm or "Scheduler"

    def verify(self, username: str, password: str) -> bool:
        if username != self.username:
            return False
        hashed = hashlib.sha256(password.encode("utf-8")).hexdigest().lower()
        return hmac.compare_digest(hashed, self.password_hash)


def load_auth_config(path: Optional[str]) -> Optional[AuthConfig]:
    if not path:
        return None
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fp:
        raw = json.load(fp)
    enabled = raw.get("enabled", True)
    if not enabled:
        return None
    username = (raw.get("username") or "").strip()
    if not username:
        raise ValueError("auth 配置缺少 username")
    realm = (raw.get("realm") or "Scheduler").strip()
    password_hash = (raw.get("password_sha256") or "").strip()
    password_plain = raw.get("password")
    if password_hash and password_plain:
        raise ValueError("auth 配置请仅保留 password 或 password_sha256 之一")
    if password_plain:
        password_hash = hashlib.sha256(password_plain.encode("utf-8")).hexdigest()
    if not password_hash:
        raise ValueError("auth 配置缺少 password/password_sha256")
    return AuthConfig(username=username, password_hash=password_hash, realm=realm)


def _env_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_base_path(raw: Optional[str]) -> str:
    base = (raw or "/").strip()
    if not base:
        base = "/"
    if not base.startswith("/"):
        base = f"/{base}"
    if len(base) > 1 and base.endswith("/"):
        base = base.rstrip("/")
    return base or "/"


def strip_wrapping_quotes(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    if len(trimmed) >= 2 and trimmed[0] == trimmed[-1] and trimmed[0] in {'"', "'"}:
        return trimmed[1:-1]
    return trimmed


def resolve_listen_host(host: str, prefer_ipv6: bool) -> str:
    if not prefer_ipv6:
        return host
    if ":" in host:
        return host
    normalized = host.strip()
    if not normalized or normalized == "0.0.0.0":
        return "::"
    if normalized in {"127.0.0.1", "localhost"}:
        return "::1"
    raise ValueError("IPv6 模式下请提供合法的 IPv6 地址 (例如 ::)")


def generate_self_signed_cert(days: int, subject: str, openssl_bin: Optional[str] = None) -> tuple[str, str, str]:
    temp_dir = tempfile.mkdtemp(prefix="fn-scheduler-ssl-")
    cert_path = os.path.join(temp_dir, "cert.pem")
    key_path = os.path.join(temp_dir, "key.pem")
    cmd = [
        openssl_bin or os.environ.get("SCHEDULER_OPENSSL_BIN", "openssl"),
        "req",
        "-x509",
        "-nodes",
        "-newkey",
        "rsa:2048",
        "-days",
        str(days),
        "-subj",
        subject or "/CN=localhost",
        "-keyout",
        key_path,
        "-out",
        cert_path,
    ]
    try:
        completed = run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("系统未安装 openssl，无法自动生成证书，请手动提供 --ssl-cert/--ssl-key") from exc
    if completed.returncode != 0:
        error_text = completed.stderr or completed.stdout or "openssl 执行失败"
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"生成自签名证书失败: {error_text}")
    return cert_path, key_path, temp_dir


logger = logging.getLogger("fn_scheduler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def list_allowed_accounts() -> List[str]:
    """Return distinct account names whose primary or supplemental group is allowed."""

    if not POSIX_ACCOUNT_SUPPORT:
        return [DEFAULT_ACCOUNT_NAME] if DEFAULT_ACCOUNT_NAME else []

    accounts: Set[str] = set()
    try:
        for entry in pwd.getpwall():  # type: ignore[attr-defined]
            if entry.pw_gid in ALLOWED_ACCOUNT_GIDS:
                accounts.add(entry.pw_name)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to enumerate passwd entries: %s", exc)

    for gid in ALLOWED_ACCOUNT_GIDS:
        try:
            group = grp.getgrgid(gid)  # type: ignore[attr-defined]
        except KeyError:
            continue
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to read group %s: %s", gid, exc)
            continue
        for member in group.gr_mem:
            if member:
                accounts.add(member)

    return sorted(accounts)


def ensure_account_allowed(account: str) -> str:
    allowed = list_allowed_accounts()
    if not allowed:
        if POSIX_ACCOUNT_SUPPORT:
            raise ValueError("系统中未找到属于 0/1000/1001 组的账号")
        raise ValueError("当前系统无法确定默认账号")
    if not POSIX_ACCOUNT_SUPPORT:
        default_account = allowed[0]
        if account and account != default_account:
            raise ValueError(f"Windows 环境仅支持使用账号 {default_account}")
        return default_account
    if account not in allowed:
        raise ValueError("账号必须属于系统组 0/1000/1001 的成员")
    return account


###############################################################################
# Cron expression parsing
###############################################################################

class CronExpression:
    """Minimal 5-field cron parser supporting ranges, lists, and steps."""

    FIELD_SPECS = (
        ("minute", 0, 59, 60),
        ("hour", 0, 23, 24),
        ("day", 1, 31, 31),
        ("month", 1, 12, 12),
        ("weekday", 0, 6, 7),
    )

    def __init__(self, expression: str):
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must contain 5 fields")
        self.fields: List[List[int]] = []
        self._wildcards: List[bool] = []
        for part, spec in zip(parts, self.FIELD_SPECS):
            expanded, wildcard = self._expand_field(part, spec)
            self.fields.append(expanded)
            self._wildcards.append(wildcard)

    def _expand_field(self, token: str, spec: tuple) -> tuple[List[int], bool]:
        name, min_value, max_value, span = spec
        values: set[int] = set()
        wildcard = False
        items = token.split(",")
        for raw_item in items:
            original_item = raw_item.strip() or "*"
            item = original_item
            step = 1
            if "/" in original_item:
                base, step_str = original_item.split("/", 1)
                item = base or "*"
                step = int(step_str)
                if step <= 0:
                    raise ValueError(f"Invalid step for {name}")
            expanded = self._expand_range(item, min_value, max_value)
            if not expanded:
                raise ValueError(f"Invalid {name} segment: {item}")
            start_val = expanded[0]
            for value in expanded:
                if (value - start_val) % step == 0:
                    values.add(value)
            wildcard = wildcard or (original_item == "*")
        if not values:
            raise ValueError(f"No values computed for {name}")
        if name == "weekday":
            normalized = set()
            for val in values:
                normalized.add(0 if val == 7 else val)
            values = normalized
        if not all(min_value <= v <= max_value for v in values):
            raise ValueError(f"{name} values out of range")
        full_span = len(values) == span
        return sorted(values), (wildcard or full_span)

    def _expand_range(self, item: str, min_value: int, max_value: int) -> List[int]:
        if item == "*":
            return list(range(min_value, max_value + 1))
        if item.isdigit():
            return [int(item)]
        if "-" in item:
            start_str, end_str = item.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            if start > end:
                raise ValueError("Cron range start greater than end")
            return list(range(start, end + 1))
        raise ValueError("Unsupported cron token")

    def next_after(self, moment: datetime) -> datetime:
        base = moment.replace(second=0, microsecond=0)
        candidate = base
        for _ in range(MAX_LOOKAHEAD_MINUTES):
            candidate += timedelta(minutes=1)
            if self._matches(candidate):
                return candidate
        raise ValueError("Unable to compute next run within lookahead window")

    def _matches(self, candidate: datetime) -> bool:
        minute, hour = candidate.minute, candidate.hour
        day, month = candidate.day, candidate.month
        weekday = candidate.weekday()
        dom_match = day in self.fields[2]
        dow_match = weekday in self.fields[4]
        dom_wildcard = self._wildcards[2]
        dow_wildcard = self._wildcards[4]

        if dom_wildcard and dow_wildcard:
            calendar_ok = True
        elif dom_wildcard:
            calendar_ok = dow_match
        elif dow_wildcard:
            calendar_ok = dom_match
        else:
            calendar_ok = dom_match or dow_match

        return minute in self.fields[0] and hour in self.fields[1] and month in self.fields[3] and calendar_ok


###############################################################################
# Database layer
###############################################################################

class Database:
    def __init__(self, path: str):
        self.path = path
        db_dir = os.path.dirname(path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA user_version;")
            (version,) = cur.fetchone()
            if version < 1:
                self._create_schema(cur)
                version = DB_LATEST_VERSION
                cur.execute(f"PRAGMA user_version={DB_LATEST_VERSION};")
            if version < 2:
                try:
                    cur.execute("ALTER TABLE tasks ADD COLUMN event_type TEXT NOT NULL DEFAULT 'script';")
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise
                cur.execute("PRAGMA user_version=2;")
                version = 2
            if version < DB_LATEST_VERSION:
                cur.execute(f"PRAGMA user_version={DB_LATEST_VERSION};")
            self._conn.commit()

    def _create_schema(self, cur: sqlite3.Cursor) -> None:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                account TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                schedule_expression TEXT,
                condition_script TEXT,
                condition_interval INTEGER NOT NULL DEFAULT 60,
                event_type TEXT NOT NULL DEFAULT 'script',
                is_active INTEGER NOT NULL DEFAULT 1,
                pre_task_ids TEXT NOT NULL DEFAULT '[]',
                script_body TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                last_condition_check_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                log TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_task_results_task ON task_results(task_id, started_at DESC);
            """
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # Utility methods -----------------------------------------------------
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["is_active"] = bool(data.get("is_active"))
        data["condition_interval"] = int(data.get("condition_interval", 60))
        data["pre_task_ids"] = json.loads(data.get("pre_task_ids") or "[]")
        data["event_type"] = data.get("event_type") or EVENT_TYPE_SCRIPT
        return data

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM tasks ORDER BY id ASC")
            rows = [self._row_to_dict(row) for row in cur.fetchall()]
        return rows

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
            row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = isoformat(utc_now())
        task = self._prepare_task_payload(payload, is_update=False)
        task["created_at"] = now
        task["updated_at"] = now
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO tasks (
                    name, account, trigger_type, schedule_expression, condition_script,
                    condition_interval, event_type, is_active, pre_task_ids, script_body,
                    last_run_at, next_run_at, last_condition_check_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["name"],
                    task["account"],
                    task["trigger_type"],
                    task.get("schedule_expression"),
                    task.get("condition_script"),
                    task["condition_interval"],
                    task["event_type"],
                    1 if task["is_active"] else 0,
                    json.dumps(task["pre_task_ids"]),
                    task["script_body"],
                    task.get("last_run_at"),
                    task.get("next_run_at"),
                    task.get("last_condition_check_at"),
                    task["created_at"],
                    task["updated_at"],
                ),
            )
            task_id = cur.lastrowid
            self._conn.commit()
        return self.get_task(task_id)  # type: ignore

    def update_task(self, task_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_task(task_id)
        if not existing:
            return None
        task = self._prepare_task_payload({**existing, **payload}, is_update=True)
        task["updated_at"] = isoformat(utc_now())
        with self._lock:
            self._conn.execute(
                """
                UPDATE tasks SET
                    name=?, account=?, trigger_type=?, schedule_expression=?, condition_script=?,
                    condition_interval=?, event_type=?, is_active=?, pre_task_ids=?, script_body=?,
                    last_run_at=?, next_run_at=?, last_condition_check_at=?, updated_at=?
                WHERE id=?
                """,
                (
                    task["name"],
                    task["account"],
                    task["trigger_type"],
                    task.get("schedule_expression"),
                    task.get("condition_script"),
                    task["condition_interval"],
                    task["event_type"],
                    1 if task["is_active"] else 0,
                    json.dumps(task["pre_task_ids"]),
                    task["script_body"],
                    task.get("last_run_at"),
                    task.get("next_run_at"),
                    task.get("last_condition_check_at"),
                    task["updated_at"],
                    task_id,
                ),
            )
            self._conn.commit()
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def record_result_start(self, task_id: int, trigger_reason: str) -> int:
        now = isoformat(utc_now())
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO task_results(task_id, status, trigger_reason, started_at)
                VALUES (?, 'running', ?, ?)
                """,
                (task_id, trigger_reason, now),
            )
            self._conn.commit()
            return cur.lastrowid

    def finalize_result(self, result_id: int, status: str, log_text: str) -> None:
        now = isoformat(utc_now())
        with self._lock:
            self._conn.execute(
                "UPDATE task_results SET status=?, finished_at=?, log=? WHERE id=?",
                (status, now, log_text, result_id),
            )
            self._conn.commit()

    def fetch_results(self, task_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM task_results WHERE task_id=? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (task_id, limit, offset),
            )
            rows = [dict(row) for row in cur.fetchall()]
        return rows

    def fetch_result(self, task_id: int, result_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM task_results WHERE task_id=? AND id=?",
                (task_id, result_id),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def delete_results(self, task_id: int, result_id: Optional[int] = None) -> int:
        with self._lock:
            if result_id is None:
                cur = self._conn.execute("DELETE FROM task_results WHERE task_id=?", (task_id,))
            else:
                cur = self._conn.execute(
                    "DELETE FROM task_results WHERE task_id=? AND id=?",
                    (task_id, result_id),
                )
            self._conn.commit()
            return cur.rowcount

    def get_latest_result(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM task_results WHERE task_id=? ORDER BY started_at DESC LIMIT 1",
                (task_id,),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def has_running_instance(self, task_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(1) FROM task_results WHERE task_id=? AND status='running'",
                (task_id,),
            )
            (count,) = cur.fetchone()
        return count > 0

    def update_last_run(self, task_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE tasks SET last_run_at=?, updated_at=? WHERE id=?",
                (isoformat(utc_now()), isoformat(utc_now()), task_id),
            )
            self._conn.commit()

    def schedule_next_run(self, task_id: int, expression: str, base: Optional[datetime] = None) -> Optional[str]:
        if not expression:
            return None
        cron = CronExpression(expression)
        next_dt = cron.next_after(base or utc_now())
        next_iso = isoformat(next_dt)
        with self._lock:
            self._conn.execute(
                "UPDATE tasks SET next_run_at=?, updated_at=? WHERE id=?",
                (next_iso, isoformat(utc_now()), task_id),
            )
            self._conn.commit()
        return next_iso

    def update_condition_check(self, task_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE tasks SET last_condition_check_at=?, updated_at=? WHERE id=?",
                (isoformat(utc_now()), isoformat(utc_now()), task_id),
            )
            self._conn.commit()

    def fetch_due_tasks(self, moment: datetime) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT * FROM tasks
                WHERE trigger_type='schedule' AND is_active=1 AND next_run_at IS NOT NULL AND next_run_at <= ?
                ORDER BY next_run_at ASC
                """,
                (isoformat(moment),),
            )
            rows = [self._row_to_dict(row) for row in cur.fetchall()]
        return rows

    def fetch_event_tasks(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE trigger_type='event' AND is_active=1"
        params: List[Any] = []
        if event_type:
            query += " AND event_type=?"
            params.append(event_type)
        query += " ORDER BY id ASC"
        with self._lock:
            cur = self._conn.execute(query, params)
            rows = [self._row_to_dict(row) for row in cur.fetchall()]
        return rows

    # Payload utilities ---------------------------------------------------
    def _prepare_task_payload(self, payload: Dict[str, Any], is_update: bool) -> Dict[str, Any]:
        trigger_type = payload.get("trigger_type", "schedule")
        if trigger_type not in {"schedule", "event"}:
            raise ValueError("trigger_type must be 'schedule' or 'event'")
        name = payload.get("name", "").strip()
        account_raw = payload.get("account", "")
        account = account_raw.strip()
        if not account and not POSIX_ACCOUNT_SUPPORT:
            account = DEFAULT_ACCOUNT_NAME
        if not name:
            raise ValueError("任务名称必填")
        if not account:
            raise ValueError("账号必填")
        account = ensure_account_allowed(account)
        script_body = payload.get("script_body", "").strip()
        if not script_body:
            raise ValueError("任务内容不能为空")

        is_active = bool(payload.get("is_active", True))
        schedule_expression_raw = payload.get("schedule_expression")
        schedule_expression = schedule_expression_raw.strip() if isinstance(schedule_expression_raw, str) else schedule_expression_raw
        condition_script_raw = payload.get("condition_script")
        condition_script = condition_script_raw.strip() if isinstance(condition_script_raw, str) else condition_script_raw
        condition_interval = max(10, int(payload.get("condition_interval", 60)))
        event_type_raw = payload.get("event_type")
        event_type = (event_type_raw or EVENT_TYPE_SCRIPT).strip() if isinstance(event_type_raw, str) else (event_type_raw or EVENT_TYPE_SCRIPT)
        pre_task_ids = payload.get("pre_task_ids") or []
        if isinstance(pre_task_ids, str):
            try:
                pre_task_ids = json.loads(pre_task_ids)
            except json.JSONDecodeError as exc:
                raise ValueError("前置任务格式错误") from exc
        current_id = payload.get("id")
        if current_id is not None:
            current_id = int(current_id)
        cleaned: List[int] = []
        for tid in pre_task_ids:
            tid_int = int(tid)
            if current_id is not None and tid_int == current_id:
                continue
            if tid_int not in cleaned:
                cleaned.append(tid_int)
        pre_task_ids = cleaned

        next_run_at: Optional[str] = payload.get("next_run_at")
        last_condition_check_at = payload.get("last_condition_check_at")

        if trigger_type == "schedule":
            if not schedule_expression:
                raise ValueError("定时任务需要 Cron 表达式")
            cron = CronExpression(schedule_expression)
            if not is_update or not next_run_at:
                next_run_at = isoformat(cron.next_after(utc_now()))
            condition_script = None
            event_type = EVENT_TYPE_SCRIPT
        else:
            if event_type not in EVENT_TYPES:
                raise ValueError("事件类型不支持")
            if event_type == EVENT_TYPE_SCRIPT:
                if not condition_script:
                    raise ValueError("事件任务需要条件脚本")
                last_condition_check_at = payload.get("last_condition_check_at")
            else:
                condition_script = None
                last_condition_check_at = None
            schedule_expression = None

        return {
            "name": name,
            "account": account,
            "trigger_type": trigger_type,
            "schedule_expression": schedule_expression,
            "condition_script": condition_script,
            "condition_interval": condition_interval,
            "event_type": event_type,
            "is_active": is_active,
            "pre_task_ids": pre_task_ids,
            "script_body": script_body,
            "last_run_at": payload.get("last_run_at"),
            "next_run_at": next_run_at,
            "last_condition_check_at": last_condition_check_at,
        }


###############################################################################
# Scheduler engine
###############################################################################

class TaskRunner(threading.Thread):
    def __init__(self, db: Database, task: Dict[str, Any], trigger_reason: str):
        super().__init__(daemon=True)
        self.db = db
        self.task = task
        self.trigger_reason = trigger_reason

    def run(self) -> None:
        task_id = self.task["id"]
        logger.info("Executing task %s (%s)", task_id, self.trigger_reason)
        result_id = self.db.record_result_start(task_id, self.trigger_reason)
        try:
            log_text, status = self._execute_script(self.task["script_body"], TASK_TIMEOUT)
        except Exception as exc:  # pylint: disable=broad-except
            status = "failed"
            log_text = f"任务执行异常: {exc!r}"
        finally:
            self.db.finalize_result(result_id, status, log_text)
            self.db.update_last_run(task_id)

    def _execute_script(self, script: str, timeout: int) -> tuple[str, str]:
        cmd = self._build_command(script)
        env = os.environ.copy()
        preexec_fn, home_dir = self._prepare_account_context()
        if home_dir:
            env["HOME"] = home_dir
        env.update(
            {
                "SCHEDULER_TASK_ID": str(self.task["id"]),
                "SCHEDULER_TASK_NAME": self.task["name"],
                "SCHEDULER_TASK_ACCOUNT": self.task["account"],
                "SCHEDULER_TRIGGER": self.trigger_reason,
            }
        )
        try:
            completed: CompletedProcess[str] = run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
                preexec_fn=preexec_fn,
            )
        except TimeoutExpired as exc:
            return f"任务执行超时 (>{timeout}s): {exc}", "failed"
        except Exception as exc:  # pylint: disable=broad-except
            return str(exc), "failed"
        output = (completed.stdout or "") + (completed.stderr or "")
        status = "success" if completed.returncode == 0 else "failed"
        return output.strip(), status

    @staticmethod
    def _build_command(script: str) -> List[str]:
        if os.name == "nt":
            return [
                "powershell",
                "-NoLogo",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ]
        return ["/bin/bash", "-c", script]

    def _prepare_account_context(self) -> tuple[Optional[Callable[[], None]], Optional[str]]:
        if not POSIX_ACCOUNT_SUPPORT:
            return (None, None)
        account = self.task.get("account")
        if not account:
            return (None, None)
        try:
            pw_record = pwd.getpwnam(account)  # type: ignore[attr-defined]
        except KeyError as exc:
            raise RuntimeError(f"账号 {account} 不存在，无法执行任务") from exc

        target_uid = pw_record.pw_uid
        target_gid = pw_record.pw_gid
        current_uid = os.geteuid()

        if current_uid == target_uid:
            return (None, pw_record.pw_dir)

        if current_uid != 0:
            raise PermissionError("调度服务需以 root 运行才能切换任务执行账号")

        supplemental: List[int] = []
        try:
            supplemental = [entry.gr_gid for entry in grp.getgrall() if account in entry.gr_mem]  # type: ignore[attr-defined]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("获取账号 %s 附加组失败: %s", account, exc)

        groups = sorted(set([target_gid, *supplemental]))

        def _changer() -> None:
            os.setgid(target_gid)
            if groups:
                os.setgroups(groups)
            os.setuid(target_uid)

        return (_changer, pw_record.pw_dir)


class SchedulerEngine:
    def __init__(self, db: Database):
        self.db = db
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self.thread.start()
        self._trigger_system_event(EVENT_TYPE_BOOT)

    def stop(self) -> None:
        self.stop_event.set()
        self._trigger_system_event(EVENT_TYPE_SHUTDOWN)
        self.thread.join(timeout=5)

    # Internal ------------------------------------------------------------
    def _loop(self) -> None:
        while not self.stop_event.is_set():
            now = utc_now()
            try:
                self._process_due_tasks(now)
                self._process_event_tasks(now)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Scheduler loop error: %s", exc)
            self.stop_event.wait(1)

    def _process_due_tasks(self, moment: datetime) -> None:
        for task in self.db.fetch_due_tasks(moment):
            if self.db.has_running_instance(task["id"]):
                logger.info("Task %s still running, skip", task["id"])
                continue
            if not self._dependencies_met(task):
                logger.info("Task %s waiting for dependencies", task["id"])
                # re-schedule shortly in future to retry
                self.db.schedule_next_run(task["id"], task["schedule_expression"], moment + timedelta(minutes=1))
                continue
            TaskRunner(self.db, task, "schedule").start()
            self.db.schedule_next_run(task["id"], task["schedule_expression"], moment)

    def _process_event_tasks(self, moment: datetime) -> None:
        for task in self.db.fetch_event_tasks(event_type=EVENT_TYPE_SCRIPT):
            last_check = parse_iso(task.get("last_condition_check_at"))
            interval = task.get("condition_interval", 60)
            if last_check and (moment - last_check).total_seconds() < interval:
                continue
            self.db.update_condition_check(task["id"])
            if not task.get("condition_script"):
                continue
            ok = self._run_condition(task)
            if not ok:
                continue
            if self.db.has_running_instance(task["id"]):
                continue
            if not self._dependencies_met(task):
                continue
            TaskRunner(self.db, task, "condition").start()

    def _run_condition(self, task: Dict[str, Any]) -> bool:
        command = TaskRunner._build_command(task["condition_script"])
        try:
            completed = run(
                command,
                capture_output=True,
                text=True,
                timeout=CONDITION_TIMEOUT,
                check=False,
            )
        except TimeoutExpired as exc:
            logger.warning("Condition script timeout for task %s: %s", task["id"], exc)
            return False
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Condition script for task %s failed: %s", task["id"], exc)
            return False
        if completed.returncode != 0:
            return False
        return True

    def _dependencies_met(self, task: Dict[str, Any]) -> bool:
        deps = task.get("pre_task_ids") or []
        for dep_id in deps:
            result = self.db.get_latest_result(dep_id)
            if not result or result.get("status") != "success":
                return False
        return True

    def _trigger_system_event(self, event_type: str) -> None:
        if event_type not in {EVENT_TYPE_BOOT, EVENT_TYPE_SHUTDOWN}:
            return
        trigger_reason = "system_boot" if event_type == EVENT_TYPE_BOOT else "system_shutdown"
        runners: List[TaskRunner] = []
        for task in self.db.fetch_event_tasks(event_type=event_type):
            if self.db.has_running_instance(task["id"]):
                continue
            if not self._dependencies_met(task):
                continue
            runner = TaskRunner(self.db, task, trigger_reason)
            runner.start()
            runners.append(runner)
        for runner in runners:
            runner.join()


###############################################################################
# HTTP layer
###############################################################################

class SchedulerContext:
    def __init__(self, db: Database, engine: SchedulerEngine):
        self.db = db
        self.engine = engine


class SchedulerHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address,
        handler_class,
        *,
        base_path: str = "/",
        prefer_ipv6: bool = False,
        auth_config: Optional[AuthConfig] = None,
    ):
        host = server_address[0] if server_address else ""
        port = server_address[1] if len(server_address) > 1 else 0
        use_ipv6 = False
        if (prefer_ipv6 or (host and ":" in host)) and socket.has_ipv6:
            use_ipv6 = True
        elif (prefer_ipv6 or (host and ":" in host)) and not socket.has_ipv6:
            raise RuntimeError("当前系统不支持 IPv6 监听")

        self.base_path = base_path or "/"
        if use_ipv6:
            self.address_family = socket.AF_INET6
            if len(server_address) == 2:
                server_address = (host, port, 0, 0)
        super().__init__(server_address, handler_class)
        if use_ipv6:
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except OSError:
                pass
        self.auth_config = auth_config


class SchedulerRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):  # type: ignore[override]
        super().__init__(*args, directory=directory or STATIC_ROOT, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if not self._ensure_base_path():
            return
        if self.path.startswith("/api/"):
            self._handle_api("GET")
            return
        self._serve_static()

    def do_HEAD(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if not self._ensure_base_path():
            return
        if self.path.startswith("/api/"):
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "HEAD not supported for API")
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if not self._ensure_base_path():
            return
        if self.path.startswith("/api/"):
            self._handle_api("POST")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unsupported path")

    def do_PUT(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if not self._ensure_base_path():
            return
        if self.path.startswith("/api/"):
            self._handle_api("PUT")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unsupported path")

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if not self._ensure_base_path():
            return
        if self.path.startswith("/api/"):
            self._handle_api("DELETE")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unsupported path")

    # Static --------------------------------------------------------------
    def _serve_static(self) -> None:
        # Fallback to index.html for SPA routes
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if not os.path.exists(path) and not os.path.splitext(self.path)[1]:
            self.path = "/index.html"
        return super().do_GET()

    # API routing ---------------------------------------------------------
    def _handle_api(self, method: str) -> None:
        parsed = urlparse(self.path)
        segments = [segment for segment in parsed.path.split("/") if segment][1:]  # drop 'api'
        try:
            if not segments:
                self._json_response({"message": "scheduler api"})
                return
            resource = segments[0]
            if resource == "health" and method == "GET":
                self._health()
                return
            if resource == "accounts" and method == "GET":
                self._list_accounts()
                return
            if resource == "tasks":
                self._handle_tasks(method, segments[1:])
                return
            if resource == "results" and len(segments) >= 2:
                task_id = int(segments[1])
                if len(segments) == 2 and method == "GET":
                    self._list_results(task_id)
                    return
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
        except ValueError as exc:
            self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("API error: %s", exc)
            self._json_response({"error": "internal server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _list_accounts(self) -> None:
        payload = {
            "data": list_allowed_accounts(),
            "meta": {
                "posix_supported": POSIX_ACCOUNT_SUPPORT,
                "default_account": DEFAULT_ACCOUNT_NAME,
            },
        }
        self._json_response(payload)

    def _handle_tasks(self, method: str, remainder: List[str]) -> None:
        ctx: SchedulerContext = self.server.app_context  # type: ignore[attr-defined]
        if method == "GET" and not remainder:
            tasks = ctx.db.list_tasks()
            for task in tasks:
                task["latest_result"] = ctx.db.get_latest_result(task["id"])
            self._json_response({"data": tasks})
            return
        if remainder and remainder[0] == "batch":
            if method != "POST":
                self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
                return
            payload = self._read_json()
            if payload is None:
                return
            self._batch_tasks(payload)
            return
        if not remainder:
            if method == "POST":
                payload = self._read_json()
                if payload is None:
                    return
                task = ctx.db.create_task(payload)
                self._json_response(task, status=HTTPStatus.CREATED)
                return
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            return
        task_id = int(remainder[0])
        if len(remainder) == 1:
            if method == "GET":
                task = ctx.db.get_task(task_id)
                if not task:
                    self.send_error(HTTPStatus.NOT_FOUND, "Task not found")
                    return
                task["latest_result"] = ctx.db.get_latest_result(task_id)
                self._json_response(task)
                return
            if method == "PUT":
                payload = self._read_json()
                if payload is None:
                    return
                task = ctx.db.update_task(task_id, payload)
                if not task:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._json_response(task)
                return
            if method == "DELETE":
                deleted = ctx.db.delete_task(task_id)
                if not deleted:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._json_response({"deleted": True})
                return
        if len(remainder) >= 2:
            action = remainder[1]
            if action == "run" and method == "POST":
                self._run_task(task_id)
                return
            if action == "toggle" and method == "POST":
                payload = self._read_json() or {}
                self._toggle_task(task_id, payload)
                return
            if action == "results":
                if method == "GET":
                    self._list_results(task_id)
                    return
                if method == "DELETE":
                    result_id = int(remainder[2]) if len(remainder) == 3 else None
                    deleted = ctx.db.delete_results(task_id, result_id)
                    self._json_response({"deleted": deleted})
                    return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _batch_tasks(self, payload: Dict[str, Any]) -> None:
        ctx: SchedulerContext = self.server.app_context  # type: ignore[attr-defined]
        action = (payload.get("action") or "").strip().lower()
        task_ids_payload = payload.get("task_ids")
        if not isinstance(task_ids_payload, list) or not task_ids_payload:
            raise ValueError("task_ids 不能为空")
        task_ids = []
        for raw in task_ids_payload:
            try:
                tid = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("task_ids 必须为整数") from exc
            if tid > 0 and tid not in task_ids:
                task_ids.append(tid)
        if not task_ids:
            raise ValueError("未提供有效的 task_ids")

        if action not in {"delete", "enable", "disable", "run"}:
            raise ValueError("action 不支持")

        result: Dict[str, List[int]] = {"missing": []}
        runners: List[TaskRunner] = []

        for task_id in task_ids:
            task = ctx.db.get_task(task_id)
            if not task:
                result.setdefault("missing", []).append(task_id)
                continue

            if action == "delete":
                if ctx.db.delete_task(task_id):
                    result.setdefault("deleted", []).append(task_id)
                else:
                    result.setdefault("missing", []).append(task_id)
                continue

            if action in {"enable", "disable"}:
                target_state = action == "enable"
                if bool(task["is_active"]) == target_state:
                    result.setdefault("unchanged", []).append(task_id)
                    continue
                ctx.db.update_task(task_id, {"is_active": target_state})
                result.setdefault("updated", []).append(task_id)
                continue

            if action == "run":
                if ctx.db.has_running_instance(task_id):
                    result.setdefault("running", []).append(task_id)
                    continue
                if not ctx.engine._dependencies_met(task):  # pylint: disable=protected-access
                    result.setdefault("blocked", []).append(task_id)
                    continue
                runner = TaskRunner(ctx.db, task, "manual")
                runner.start()
                runners.append(runner)
                result.setdefault("queued", []).append(task_id)

        payload = {"action": action, "result": result}
        self._json_response(payload)

    def _run_task(self, task_id: int) -> None:
        ctx: SchedulerContext = self.server.app_context  # type: ignore[attr-defined]
        task = ctx.db.get_task(task_id)
        if not task:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if ctx.db.has_running_instance(task_id):
            self._json_response({"error": "任务正在执行"}, status=HTTPStatus.CONFLICT)
            return
        if not ctx.engine._dependencies_met(task):  # pylint: disable=protected-access
            self._json_response({"error": "前置任务尚未成功"}, status=HTTPStatus.BAD_REQUEST)
            return
        TaskRunner(ctx.db, task, "manual").start()
        self._json_response({"queued": True})

    def _toggle_task(self, task_id: int, payload: Dict[str, Any]) -> None:
        ctx: SchedulerContext = self.server.app_context  # type: ignore[attr-defined]
        task = ctx.db.get_task(task_id)
        if not task:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        is_active = bool(payload.get("is_active", not task["is_active"]))
        updated = ctx.db.update_task(task_id, {"is_active": is_active})
        self._json_response(updated)

    def _list_results(self, task_id: int) -> None:
        ctx: SchedulerContext = self.server.app_context  # type: ignore[attr-defined]
        query = parse_qs(urlparse(self.path).query)
        limit = int(query.get("limit", [50])[0])
        offset = int(query.get("offset", [0])[0])
        results = ctx.db.fetch_results(task_id, limit=limit, offset=offset)
        self._json_response({"data": results})

    def _health(self) -> None:
        ctx: SchedulerContext = self.server.app_context  # type: ignore[attr-defined]
        tasks = ctx.db.list_tasks()
        payload = {
            "time": isoformat(utc_now()),
            "task_count": len(tasks),
        }
        self._json_response(payload)

    # Utilities -----------------------------------------------------------
    def _read_json(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return None

    def _json_response(self, payload: Any, status: HTTPStatus | int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_: str, *args: Any) -> None:  # noqa: D401
        logger.info("%s - - %s", self.address_string(), format_ % args)

    def _require_auth(self) -> bool:
        auth_config: Optional[AuthConfig] = getattr(self.server, "auth_config", None)  # type: ignore[attr-defined]
        if not auth_config:
            return True
        header = self.headers.get("Authorization")
        username, password = self._parse_basic_header(header)
        if username and password and auth_config.verify(username, password):
            return True
        self._send_auth_challenge(auth_config.realm)
        return False

    def _send_auth_challenge(self, realm: str) -> None:
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", f'Basic realm="{realm}", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Authentication required")

    @staticmethod
    def _parse_basic_header(header: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not header or not header.startswith("Basic "):
            return (None, None)
        token = header.split(" ", 1)[1].strip()
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except Exception:  # pylint: disable=broad-except
            return (None, None)
        if ":" not in decoded:
            return (None, None)
        username, password = decoded.split(":", 1)
        return (username, password)

    def _ensure_base_path(self) -> bool:
        base_path = getattr(self.server, "base_path", "/")  # type: ignore[attr-defined]
        if base_path in ("", "/"):
            return True
        parsed = urlsplit(self.path)
        if not parsed.path.startswith(base_path):
            self.send_error(HTTPStatus.NOT_FOUND, "Base path mismatch")
            return False
        stripped_path = parsed.path[len(base_path) :] or "/"
        if not stripped_path.startswith("/"):
            stripped_path = f"/{stripped_path}"
        rebuilt = parsed._replace(path=stripped_path)
        self.path = urlunsplit(rebuilt)
        return True


###############################################################################
# Entrypoint
###############################################################################

def run_server(
    host: str,
    port: int,
    db_path: str,
    ssl_cert: Optional[str] = None,
    ssl_key: Optional[str] = None,
    base_path: str = "/",
    prefer_ipv6: bool = False,
    enable_ssl: bool = False,
    auth_path: Optional[str] = None,
) -> None:
    db_path = strip_wrapping_quotes(db_path) or DEFAULT_DB_PATH
    ssl_cert = strip_wrapping_quotes(ssl_cert)
    ssl_key = strip_wrapping_quotes(ssl_key)
    base_path = strip_wrapping_quotes(base_path) or "/"
    auth_path = strip_wrapping_quotes(auth_path)

    database = Database(db_path)
    engine = SchedulerEngine(database)
    ctx = SchedulerContext(database, engine)
    handler_class = partial(SchedulerRequestHandler, directory=STATIC_ROOT)
    normalized_base = normalize_base_path(base_path)
    auth_config_path = auth_path or DEFAULT_AUTH_PATH
    auth_config = None
    if auth_config_path and os.path.exists(auth_config_path):
        auth_config = load_auth_config(auth_config_path)
    elif auth_path:
        logger.warning("auth 配置文件不存在: %s，Basic Auth 未启用", auth_config_path)
    if auth_config:
        logger.info("Basic Auth enabled for Web UI (realm=%s, user=%s)", auth_config.realm, auth_config.username)
    httpd = SchedulerHTTPServer(
        (host, port),
        handler_class,
        base_path=normalized_base,
        prefer_ipv6=prefer_ipv6,
        auth_config=auth_config,
    )
    httpd.app_context = ctx  # type: ignore[attr-defined]

    generated_cert_dir: Optional[str] = None
    if enable_ssl and not (ssl_cert and ssl_key):
        cert_days = int(os.environ.get("SCHEDULER_SSL_DAYS", "365"))
        cert_subject = os.environ.get("SCHEDULER_SSL_SUBJECT", "/CN=localhost")
        try:
            ssl_cert, ssl_key, generated_cert_dir = generate_self_signed_cert(cert_days, cert_subject)
            logger.info("Generated self-signed certificate (subject=%s, days=%s)", cert_subject, cert_days)
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError("启用 --ssl 失败：无法生成自签名证书，请确认 openssl 可用或手动提供证书") from exc

    scheme = "http"
    if ssl_cert or ssl_key:
        if not ssl_cert or not ssl_key:
            raise ValueError("启用 HTTPS 需要同时提供证书和私钥路径")
        if not os.path.exists(ssl_cert):
            raise FileNotFoundError(f"SSL 证书不存在: {ssl_cert}")
        if not os.path.exists(ssl_key):
            raise FileNotFoundError(f"SSL 私钥不存在: {ssl_key}")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        if hasattr(context, "minimum_version") and hasattr(ssl, "TLSVersion"):
            context.minimum_version = ssl.TLSVersion.TLSv1_2  # type: ignore[attr-defined]
        context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
        logger.info("HTTPS enabled using cert=%s key=%s", ssl_cert, ssl_key)

    shutdown_event = threading.Event()

    def _handle_signal(signum: int, _: Any | None) -> None:
        if shutdown_event.is_set():
            return
        shutdown_event.set()
        logger.info("Received signal %s, shutting down scheduler...", signum)
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    for sig_name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, sig_name):
            signal.signal(getattr(signal, sig_name), _handle_signal)

    logger.info(
        "Starting scheduler on %s://%s:%s%s (db=%s)",
        scheme,
        host,
        port,
        normalized_base,
        db_path,
    )
    engine.start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
    finally:
        engine.stop()
        database.close()
        httpd.server_close()
        if generated_cert_dir:
            shutil.rmtree(generated_cert_dir, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scheduler Service")
    parser.add_argument(
        "--host",
        default=os.environ.get("SCHEDULER_HOST", DEFAULT_HOST),
    )
    parser.add_argument(
        "--port",
        default=int(os.environ.get("SCHEDULER_PORT", DEFAULT_PORT)),
        type=int,
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("SCHEDULER_DB_PATH", DEFAULT_DB_PATH),
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--ssl-cert",
        default=os.environ.get("SCHEDULER_SSL_CERT"),
        help="PEM certificate file for enabling HTTPS",
    )
    parser.add_argument(
        "--ssl-key",
        default=os.environ.get("SCHEDULER_SSL_KEY"),
        help="PEM private key file for enabling HTTPS",
    )
    ssl_default = _env_truthy(os.environ.get("SCHEDULER_ENABLE_SSL"))
    parser.add_argument(
        "--ssl",
        dest="ssl",
        action="store_true",
        help="Enable HTTPS even when no cert/key provided (auto self-signed)",
    )
    parser.add_argument(
        "--no-ssl",
        dest="ssl",
        action="store_false",
        help="Disable HTTPS auto mode even if env is set",
    )
    parser.add_argument(
        "--auth",
        default=os.environ.get("SCHEDULER_AUTH"),
        help="Path to Basic Auth JSON config (default auth.json if present)",
    )
    parser.add_argument(
        "--base-path",
        default=os.environ.get("SCHEDULER_BASE_PATH", "/"),
        help="Base URL path to mount the scheduler under (default '/')",
    )
    ipv6_default = _env_truthy(os.environ.get("SCHEDULER_ENABLE_IPV6"))
    parser.add_argument(
        "--ipv6",
        dest="ipv6",
        action="store_true",
        help="Prefer IPv6 sockets (or set SCHEDULER_ENABLE_IPV6=1)",
    )
    parser.add_argument(
        "--no-ipv6",
        dest="ipv6",
        action="store_false",
        help="Force IPv4 sockets even if IPv6 env var is set",
    )
    parser.set_defaults(ipv6=ipv6_default, ssl=ssl_default)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    listen_host = resolve_listen_host(args.host, args.ipv6)
    run_server(
        listen_host,
        args.port,
        args.db,
        ssl_cert=args.ssl_cert,
        ssl_key=args.ssl_key,
        base_path=args.base_path,
        prefer_ipv6=args.ipv6,
        enable_ssl=args.ssl,
        auth_path=args.auth,
    )
