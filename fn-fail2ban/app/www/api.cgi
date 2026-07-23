# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import sys
import json
import shutil
import subprocess
import os
from typing import Tuple


def respond(obj, status=200):
    # Note: many environments ignore Status header for CGI; keep JSON body consistent
    print("Content-Type: application/json")
    print()
    print(json.dumps(obj, ensure_ascii=False))


def read_input_json():
    try:
        data = sys.stdin.read()
        if not data:
            return {}
        return json.loads(data)
    except Exception:
        return {}


def run_command(cmd, capture_output=True, text=True) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        if capture_output:
            p = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text
            )
            return p.returncode, (p.stdout or ""), (p.stderr or "")
        else:
            p = subprocess.run(cmd)
            return p.returncode, "", ""
    except Exception as e:
        return 1, "", str(e)


def getLoadJails():
    jails = []
    try:
        out = subprocess.check_output(
            ["fail2ban-client", "status"], stderr=subprocess.DEVNULL, text=True
        )
        for line in out.splitlines():
            if "Jail list:" in line:
                tail = line.split("Jail list:")[1].strip()
                if tail:
                    jails = [x.strip() for x in tail.split(",") if x.strip()]
                else:
                    idx = out.splitlines().index(line)
                    if idx + 1 < len(out.splitlines()):
                        jails = [
                            x.strip()
                            for x in out.splitlines()[idx + 1].split(",")
                            if x.strip()
                        ]
                break
    except Exception:
        pass

    return jails


def getJailStatus(jail):
    curreb = "0"
    totalb = "0"
    banips = ""
    try:
        out = subprocess.check_output(
            ["fail2ban-client", "status", jail], stderr=subprocess.DEVNULL, text=True
        )
        for line in out.splitlines():
            """
            Status for the jail: sshd
            |- Filter
            |  |- Currently failed: 0
            |  |- Total failed:     0
            |  `- Journal matches:  _SYSTEMD_UNIT=ssh.service
            `- Actions
            |- Currently banned: 0
            |- Total banned:     0
            `- Banned IP list:
            """
            if "Currently banned".lower() in line.lower():
                curreb = line.split(":")[1].strip()
            if "Total banned".lower() in line.lower():
                totalb = line.split(":")[1].strip()
            if "Banned IP list".lower() in line.lower():
                banips = line.split(":")[1].strip()
    except Exception:
        pass
    return curreb, totalb, banips


def getSection(filename, section):
    """Extract a section's body (lines between headers) from an ini-style file.

    Returns an empty string if the section is not found.
    """
    try:
        with open(filename, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except Exception:
        return ""

    start = None
    end = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            name = s[1:-1].strip()
            if name == section:
                start = i
                break

    if start is None:
        return ""

    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if s.startswith("[") and s.endswith("]"):
            end = j
            break

    body_lines = lines[start + 1 : end] if end is not None else lines[start + 1 :]
    # preserve original newlines so the editor shows proper line breaks
    return "".join(body_lines)


def setSection(filename, section, content):
    """Replace or append a section in an ini-style file without touching other sections.

    `content` should be the body lines (without the [section] header).
    Handles duplicate sections by removing ALL occurrences before writing one.
    """
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        else:
            lines = []

        import re

        if content:
            content = re.sub(r"^\[.+\]\s*\n?", "", content, count=1, flags=re.MULTILINE)

        out_lines = []
        i = 0
        found = False
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith("[") and s.endswith("]") and s[1:-1].strip() == section:
                if not found:
                    new_section_lines = [f"[{section}]\n"]
                    if content:
                        for ln in content.splitlines():
                            new_section_lines.append(ln.rstrip("\n") + "\n")
                    out_lines.extend(new_section_lines)
                    found = True
                i += 1
                while i < len(lines):
                    sj = lines[i].strip()
                    if sj.startswith("[") and sj.endswith("]"):
                        break
                    i += 1
                continue
            out_lines.append(lines[i])
            i += 1

        if not found:
            new_section_lines = [f"[{section}]\n"]
            if content:
                for ln in content.splitlines():
                    new_section_lines.append(ln.rstrip("\n") + "\n")
            if out_lines and not out_lines[-1].endswith("\n"):
                out_lines[-1] = out_lines[-1] + "\n"
            out_lines.extend(new_section_lines)

        with open(filename, "w", encoding="utf-8") as fh:
            fh.writelines(out_lines)
        return True
    except Exception:
        return False


def removeSection(filename, section):
    """Remove a section (header and body) from the file. Returns True if removed."""
    try:
        if not os.path.exists(filename):
            return False
        with open(filename, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()

        out_lines = []
        i = 0
        removed = False
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith("[") and s.endswith("]") and s[1:-1].strip() == section:
                # skip this section
                removed = True
                i += 1
                while i < len(lines):
                    sj = lines[i].strip()
                    if sj.startswith("[") and sj.endswith("]"):
                        break
                    i += 1
                continue
            out_lines.append(lines[i])
            i += 1

        if not removed:
            return False

        with open(filename, "w", encoding="utf-8") as fh:
            fh.writelines(out_lines)
        return True
    except Exception:
        return False


FNOS_PATH = "/etc/fail2ban/jail.d/fnOS.conf"
AUDIT_LOG = "/var/apps/fn-fail2ban/var/audit.log"


def audit_log(action, jail=None, ip=None, note=None):
    try:
        d = {
            "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "action": action,
            "jail": jail,
            "ip": ip,
            "note": note,
            "pid": os.getpid(),
        }
        dstr = json.dumps(d, ensure_ascii=False)
        dn = os.path.dirname(AUDIT_LOG)
        if dn and not os.path.exists(dn):
            try:
                os.makedirs(dn, exist_ok=True)
            except Exception:
                pass
        with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(dstr + "\n")
    except Exception:
        pass


def getFileJails():
    """Read only the single fnOS.conf and return list of {jail: filename} entries."""
    jails = []
    fn = FNOS_PATH
    if not os.path.exists(fn):
        return jails
    try:
        with open(fn, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    jails.append({line[1:-1].strip(): os.path.basename(fn)})
    except Exception:
        pass
    return jails


def main():
    req = read_input_json()
    action = req.get("action", "")

    if action == "status":
        req = {}
        # service active
        status = "unknown"

        rc, out, err = run_command(["systemctl", "is-active", "fail2ban"])
        if rc == 0:
            status = out.strip()

        req["active"] = status == "active"
        req["jails"] = []

        config_warnings = []
        try:
            fn = FNOS_PATH
            if os.path.exists(fn):
                with open(fn, "r", encoding="utf-8", errors="ignore") as fh:
                    flines = fh.readlines()
                seen = {}
                for line in flines:
                    s = line.strip()
                    if s.startswith("[") and s.endswith("]"):
                        name = s[1:-1].strip()
                        seen[name] = seen.get(name, 0) + 1
                dupes = [k for k, v in seen.items() if v > 1]
                if dupes:
                    config_warnings.append("duplicate_sections:" + ",".join(dupes))
                for line in flines:
                    ls = line.strip()
                    if ls.startswith("logpath") and "=" in ls:
                        lp = ls.split("=", 1)[1].strip()
                        for p in lp.split(","):
                            p = p.strip()
                            if (
                                p
                                and p not in ("journal", "systemd")
                                and not p.startswith("journal")
                                and not os.path.exists(p)
                            ):
                                config_warnings.append("missing_log:" + p)
        except Exception:
            pass
        req["config_warnings"] = config_warnings

        # Jails
        jailfiles = getFileJails()
        loadjails = getLoadJails()
        for j in loadjails:
            curreb, totalb, banips = getJailStatus(j)
            req["jails"].append(
                {
                    "name": j,
                    "enabled": True,
                    "curBan": curreb,
                    "tolBan": totalb,
                    "banIPs": banips,
                }
            )

        # any jails found in the fnOS.conf but not loaded by fail2ban
        for f in jailfiles:
            j = list(f.keys())[0]
            if j not in set(loadjails):
                req["jails"].append(
                    {
                        "name": j,
                        "enabled": False,
                        "curBan": "0",
                        "tolBan": "0",
                        "banIPs": "",
                    }
                )

        respond(req)
        return

    if action == "read":
        # read the single fnOS.conf file
        jail = req.get("jail", "")
        content = req.get("content", "")
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return

        fn = FNOS_PATH
        if not os.path.exists(fn):
            respond({"success": False, "message": "未找到 fnOS.conf"})
            return
        try:
            content = getSection(fn, jail) if jail else ""
            respond({"success": True, "content": content})
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "ban" or action == "unban":
        jail = req.get("jail", "")
        ip = req.get("ip", "")
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return
        if not ip:
            respond({"success": False, "message": "缺少 ip 参数"})
            return

        # use fail2ban-client set <jail> banip|unbanip <ip>
        verb = "banip" if action == "ban" else "unbanip"
        rc, out, err = run_command(["fail2ban-client", "set", jail, verb, ip])
        if rc == 0:
            respond(
                {
                    "success": True,
                    "message": ("添加封禁成功" if action == "ban" else "解除封禁成功"),
                    "output": out,
                }
            )
            try:
                audit_log(action, jail=jail, ip=ip, note="ok")
            except Exception:
                pass
        else:
            respond(
                {
                    "success": False,
                    "message": ("添加封禁失败" if action == "ban" else "解除封禁失败"),
                    "output": err,
                }
            )
            try:
                audit_log(action, jail=jail, ip=ip, note=err.strip())
            except Exception:
                pass
        return

    # bulk ban / unban: accept `ips` as list or comma/space separated string
    if action == "bulkban" or action == "bulkunban":
        jail = req.get("jail", "")
        ips = req.get("ips", [])
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return
        # normalize ips
        try:
            if isinstance(ips, str):
                import re

                ips = [p.strip() for p in re.split(r"[\s,;]+", ips) if p.strip()]
            elif isinstance(ips, list):
                ips = [str(p).strip() for p in ips if str(p).strip()]
            else:
                ips = []
        except Exception:
            ips = []

        if not ips:
            respond(
                {"success": True, "message": "没有提供要处理的 IP 列表", "count": 0}
            )
            return

        verb = "banip" if action == "bulkban" else "unbanip"
        results = []
        for ip in ips:
            rc, out, err = run_command(["fail2ban-client", "set", jail, verb, ip])
            results.append({"ip": ip, "rc": rc, "out": out, "err": err})

        failed = [r for r in results if r["rc"] != 0]
        if not failed:
            respond(
                {
                    "success": True,
                    "message": (
                        "批量封禁完成" if action == "bulkban" else "批量解除封禁完成"
                    ),
                    "count": len(results),
                }
            )
            try:
                for r in results:
                    audit_log(action, jail=jail, ip=r.get("ip"), note="ok")
            except Exception:
                pass
        else:
            respond(
                {
                    "success": False,
                    "message": (
                        "部分批量封禁失败"
                        if action == "bulkban"
                        else "部分批量解除封禁失败"
                    ),
                    "failed": failed,
                    "count": len(results),
                }
            )
            try:
                for r in results:
                    audit_log(
                        action,
                        jail=jail,
                        ip=r.get("ip"),
                        note=(r.get("err") or "").strip(),
                    )
            except Exception:
                pass
        return

    if action == "clear":
        # Unban all IPs for a jail (batch)
        jail = req.get("jail", "")
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return

        # get current banned IPs
        curreb, totalb, banips = getJailStatus(jail)
        # parse banips into list
        ips = []
        if banips:
            # banips may be a comma/space separated string, or empty
            for part in [
                p.strip() for p in banips.replace(",", " ").replace(";", " ").split()
            ]:
                if part:
                    ips.append(part)

        if not ips:
            respond({"success": True, "message": "没有被封的 IP"})
            return

        results = []
        for ip in ips:
            rc, out, err = run_command(["fail2ban-client", "set", jail, "unbanip", ip])
            results.append({"ip": ip, "rc": rc, "out": out, "err": err})

        failed = [r for r in results if r["rc"] != 0]
        if not failed:
            respond({"success": True, "message": "清空成功", "count": len(results)})
            try:
                for r in results:
                    audit_log("clear_unban", jail=jail, ip=r.get("ip"), note="ok")
            except Exception:
                pass
        else:
            respond(
                {
                    "success": False,
                    "message": "部分解除封禁失败",
                    "failed": failed,
                    "count": len(results),
                }
            )
            try:
                for r in results:
                    audit_log(
                        "clear_unban",
                        jail=jail,
                        ip=r.get("ip"),
                        note=(r.get("err") or "").strip(),
                    )
            except Exception:
                pass
        return

    if action == "write":
        jail = req.get("jail", "")
        content = req.get("content", "")
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return
        if content is None:
            respond({"success": False, "message": "缺少 content 参数"})
            return

        try:
            fn = FNOS_PATH
            if not os.path.exists(fn):
                open(fn, "a").close()
            shutil.copy2(fn, fn + ".bak")
            setSection(fn, jail, content)

            created_logs = []
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("logpath") and "=" in line:
                    lp = line.split("=", 1)[1].strip()
                    for p in lp.split(","):
                        p = p.strip()
                        if p and not os.path.exists(p):
                            try:
                                pdir = os.path.dirname(p)
                                if pdir and not os.path.exists(pdir):
                                    os.makedirs(pdir, exist_ok=True)
                                open(p, "a").close()
                                created_logs.append(p)
                            except Exception:
                                pass

            rc, out, err = run_command(["fail2ban-client", "reload"])
            if rc == 0:
                try:
                    if os.path.exists(fn + ".bak"):
                        os.remove(fn + ".bak")
                except Exception:
                    pass
                try:
                    note = "write_ok"
                    if created_logs:
                        note += " created_log: " + ", ".join(created_logs)
                    audit_log("write", jail=jail, note=note)
                except Exception:
                    pass
                msg = "写入成功"
                if created_logs:
                    msg += "（已创建日志文件: " + ", ".join(created_logs) + "）"
                respond({"success": True, "message": msg, "created_logs": created_logs})
                return

            backup_has_dupes = False
            try:
                if os.path.exists(fn + ".bak"):
                    with open(
                        fn + ".bak", "r", encoding="utf-8", errors="ignore"
                    ) as fh:
                        seen = {}
                        for line in fh:
                            s = line.strip()
                            if s.startswith("[") and s.endswith("]"):
                                name = s[1:-1].strip()
                                seen[name] = seen.get(name, 0) + 1
                        backup_has_dupes = any(v > 1 for v in seen.values())
            except Exception:
                pass

            if backup_has_dupes:
                try:
                    if os.path.exists(fn + ".bak"):
                        os.remove(fn + ".bak")
                except Exception:
                    pass
                try:
                    audit_log(
                        "write",
                        jail=jail,
                        note=("write_reload_fail_no_rollback: " + (err or "").strip()),
                    )
                except Exception:
                    pass
                respond(
                    {"success": False, "message": "配置已写入但重载失败", "output": err}
                )
                return

            try:
                if os.path.exists(fn + ".bak"):
                    shutil.move(fn + ".bak", fn)
            except Exception:
                pass
            try:
                audit_log(
                    "write", jail=jail, note=("write_fail: " + (err or "").strip())
                )
            except Exception:
                pass
            respond({"success": False, "message": "写入失败", "output": err})
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "delete":
        # delete a jail section from fnOS.conf
        jail = req.get("jail", "")
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return

        fn = FNOS_PATH
        if not os.path.exists(fn):
            respond({"success": False, "message": "未找到 fnOS.conf"})
            return
        try:
            # backup
            shutil.copy2(fn, fn + ".bak")
            ok = removeSection(fn, jail)
            if not ok:
                respond({"success": False, "message": "未找到对应的 Jail 节"})
                return
            rc, out, err = run_command(["fail2ban-client", "reload"])
            if rc == 0:
                try:
                    if os.path.exists(fn + ".bak"):
                        os.remove(fn + ".bak")
                except Exception:
                    pass
                try:
                    audit_log("delete", jail=jail, note="delete_ok")
                except Exception:
                    pass
                respond({"success": True, "message": "删除成功"})
                return
            # reload failed: restore backup
            try:
                if os.path.exists(fn + ".bak"):
                    shutil.move(fn + ".bak", fn)
            except Exception:
                pass
            try:
                audit_log(
                    "delete", jail=jail, note=("delete_fail: " + (err or "").strip())
                )
            except Exception:
                pass
            respond(
                {"success": False, "message": "删除失败，reload 失败", "output": err}
            )
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "start":
        rc, out, err = run_command(["systemctl", "start", "fail2ban"])
        if rc == 0:
            try:
                audit_log("start", note="start_ok")
            except Exception:
                pass
            respond({"success": True, "message": "启动成功"})
        else:
            try:
                audit_log("start", note=("start_fail: " + (err or "").strip()))
            except Exception:
                pass
            respond({"success": False, "message": "启动失败", "output": err})
        return

    if action == "stop":
        rc, out, err = run_command(["systemctl", "stop", "fail2ban"])
        if rc == 0:
            try:
                audit_log("stop", note="stop_ok")
            except Exception:
                pass
            respond({"success": True, "message": "停止成功"})
        else:
            try:
                audit_log("stop", note=("stop_fail: " + (err or "").strip()))
            except Exception:
                pass
            respond({"success": False, "message": "停止失败", "output": err})
        return

    if action == "toggle":
        jail = req.get("jail", "")
        enabled = req.get("enabled", True)
        if not jail:
            respond({"success": False, "message": "缺少 jail 参数"})
            return
        fn = FNOS_PATH
        if not os.path.exists(fn):
            respond({"success": False, "message": "未找到 fnOS.conf"})
            return
        try:
            content = getSection(fn, jail)
            if content is None or content == "":
                respond({"success": False, "message": "未找到对应的 Jail 节"})
                return
            if enabled:
                content = (
                    content.replace("enabled = false", "enabled = true")
                    .replace("enabled = False", "enabled = true")
                    .replace("enabled=false", "enabled=true")
                    .replace("enabled=False", "enabled=true")
                )
                if "enabled" not in content:
                    content = "enabled = true\n" + content
            else:
                content = (
                    content.replace("enabled = true", "enabled = false")
                    .replace("enabled = True", "enabled = false")
                    .replace("enabled=true", "enabled=false")
                    .replace("enabled=True", "enabled=false")
                )
                if "enabled" not in content:
                    content = "enabled = false\n" + content
            shutil.copy2(fn, fn + ".bak")
            setSection(fn, jail, content)
            rc, out, err = run_command(["fail2ban-client", "reload"])
            if rc == 0:
                try:
                    if os.path.exists(fn + ".bak"):
                        os.remove(fn + ".bak")
                except Exception:
                    pass
                try:
                    audit_log("toggle", jail=jail, note=("enabled=" + str(enabled)))
                except Exception:
                    pass
                respond({"success": True, "message": "操作成功"})
                return
            try:
                if os.path.exists(fn + ".bak"):
                    shutil.move(fn + ".bak", fn)
            except Exception:
                pass
            respond({"success": False, "message": "重载失败", "output": err})
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "reload":
        rc, out, err = run_command(["fail2ban-client", "reload"])
        if rc == 0:
            try:
                audit_log("reload", note="reload_ok")
            except Exception:
                pass
            respond({"success": True, "message": "reload 成功", "output": out})
            return
        try:
            audit_log("reload", note=("reload_fail: " + (err or "").strip()))
        except Exception:
            pass
        respond(
            {"success": False, "message": "reload/restart 失败", "fail2ban-client": err}
        )
        return

    # audit fetch
    if action == "audit":
        flt = req.get("filter", "")
        limit = int(req.get("limit", 200) or 200)
        entries = []
        try:
            if os.path.exists(AUDIT_LOG):
                with open(AUDIT_LOG, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        if flt:
                            s = (
                                (obj.get("jail") or "")
                                + " "
                                + (obj.get("ip") or "")
                                + " "
                                + (obj.get("action") or "")
                                + " "
                                + (obj.get("note") or "")
                            )
                            if flt.lower() not in s.lower():
                                continue
                        entries.append(obj)
            # return last `limit` entries
            entries = entries[-limit:]
            respond({"success": True, "entries": entries})
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "log":
        lines_count = int(req.get("lines", 100) or 100)
        log_path = "/var/log/fail2ban.log"
        lines = []
        try:
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
                    all_lines = fh.readlines()
                    lines = [l.rstrip("\n") for l in all_lines[-lines_count:]]
            respond({"success": True, "lines": lines})
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "audit_clear":
        try:
            if os.path.exists(AUDIT_LOG):
                os.remove(AUDIT_LOG)
            respond({"success": True, "message": "审计日志已清空"})
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    if action == "check_logpath":
        paths = req.get("paths", [])
        if isinstance(paths, str):
            paths = [paths]
        results = {}
        for p in paths:
            p = p.strip()
            if not p:
                continue
            results[p] = os.path.exists(p)
        respond({"success": True, "results": results})
        return

    if action == "repair":
        try:
            fn = FNOS_PATH
            if not os.path.exists(fn):
                respond({"success": False, "message": "未找到 fnOS.conf"})
                return
            with open(fn, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            sections = {}
            current = None
            for line in lines:
                s = line.strip()
                if s.startswith("[") and s.endswith("]"):
                    current = s[1:-1].strip()
                    if current not in sections:
                        sections[current] = []
                    sections[current].append(line)
                elif current is not None:
                    sections[current].append(line)
            dupes = [
                k
                for k, v in sections.items()
                if sum(1 for l in v if l.strip().startswith("[")) > 1
            ]
            if not dupes:
                respond(
                    {"success": True, "message": "配置文件无重复段", "duplicates": []}
                )
                return
            for d in dupes:
                body = []
                skip = True
                for l in sections[d]:
                    ls = l.strip()
                    if (
                        ls.startswith("[")
                        and ls.endswith("]")
                        and ls[1:-1].strip() == d
                    ):
                        if skip:
                            body.append(l)
                            skip = False
                        continue
                    if not skip:
                        body.append(l)
                sections[d] = body
            out_lines = []
            written = set()
            for line in lines:
                s = line.strip()
                if s.startswith("[") and s.endswith("]"):
                    name = s[1:-1].strip()
                    if name in dupes and name in written:
                        continue
                    written.add(name)
                out_lines.append(line)
            with open(fn, "w", encoding="utf-8") as fh:
                fh.writelines(out_lines)

            created_logs = []
            with open(fn, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    ls = line.strip()
                    if ls.startswith("logpath") and "=" in ls:
                        lp = ls.split("=", 1)[1].strip()
                        for p in lp.split(","):
                            p = p.strip()
                            if (
                                p
                                and p not in ("journal", "systemd")
                                and not p.startswith("journal")
                                and not os.path.exists(p)
                            ):
                                try:
                                    pdir = os.path.dirname(p)
                                    if pdir and not os.path.exists(pdir):
                                        os.makedirs(pdir, exist_ok=True)
                                    open(p, "a").close()
                                    created_logs.append(p)
                                except Exception:
                                    pass

            rc, out, err = run_command(["fail2ban-client", "reload"])
            if rc == 0:
                try:
                    audit_log("repair", note="repair_ok")
                except Exception:
                    pass
                msg = "修复成功"
                if created_logs:
                    msg += "（已创建日志文件: " + ", ".join(created_logs) + "）"
                respond(
                    {
                        "success": True,
                        "message": msg,
                        "duplicates": dupes,
                        "created_logs": created_logs,
                    }
                )
            else:
                try:
                    audit_log(
                        "repair", note=("repair_reload_fail: " + (err or "").strip())
                    )
                except Exception:
                    pass
                respond(
                    {
                        "success": False,
                        "message": "已去重但重载失败",
                        "duplicates": dupes,
                        "output": err,
                    }
                )
        except Exception as e:
            respond({"success": False, "message": str(e)})
        return

    respond({"success": False, "message": "未知操作"})


if __name__ == "__main__":
    main()
