#!/usr/bin/env python3
"""Collect ITGC evidence from a Northwind Linux server.

Read only. Exports the server's local accounts and groups, who holds administrator
rights through sudo, the effective SSH settings, domain sign in restrictions, scheduled
jobs, time synchronisation and patch status into a dated evidence folder, with an
extraction log and SHA-256 hashes of every file.

Run on each server:  sudo python3 collect_host_evidence.py --out ~/evidence
"""

from __future__ import annotations

import argparse
import csv
import getpass
import grp
import hashlib
import os
import platform
import pwd
import re
import shlex
import socket
import stat
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

NO_LOGIN_SHELLS = {"/usr/sbin/nologin", "/sbin/nologin", "/bin/false", "/usr/bin/false", ""}
LOG: list[str] = []


def run(cmd: list[str], check: bool = False) -> str:
    """Runs a command, records it in the extraction log, and returns its output."""
    LOG.append("$ " + shlex.join(cmd))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        LOG.append("  (command not available on this server)")
        return ""
    if check and out.returncode:
        raise RuntimeError(f"{shlex.join(cmd)} failed: {out.stderr.strip()}")
    return out.stdout + (out.stderr if out.returncode else "")


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0).isoformat()


def file_info(path: Path) -> dict[str, str]:
    st = path.stat()
    return {
        "owner": pwd.getpwuid(st.st_uid).pw_name,
        "group": grp.getgrgid(st.st_gid).gr_name,
        "mode": oct(stat.S_IMODE(st.st_mode))[2:].zfill(4),
        "modified": utc(st.st_mtime),
    }


def package_of(path: Path) -> str:
    """The package that installed a file, from dpkg's records."""
    LOG.append("$ " + shlex.join(["dpkg", "-S", str(path)]))
    out = subprocess.run(["dpkg", "-S", str(path)], capture_output=True, text=True)
    if out.returncode:
        return "not from a package"
    return out.stdout.split(":", 1)[0].strip()


def shadow_entries() -> dict[str, list[str]]:
    entries = {}
    for line in Path("/etc/shadow").read_text().splitlines():
        fields = line.split(":")
        if len(fields) >= 8:
            entries[fields[0]] = fields
    return entries


def days_to_date(value: str) -> str:
    return (date(1970, 1, 1) + timedelta(days=int(value))).isoformat() if value.strip() else ""


def password_status(hash_field: str) -> str:
    if hash_field == "":
        return "No password (empty)"
    if hash_field.startswith("!") or hash_field.startswith("*"):
        return "Locked or not set"
    return "Set"


def write_csv(path: Path, header: list[str], rows: list[list]) -> int:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def local_accounts(folder: Path) -> tuple[int, int]:
    LOG.append("read /etc/passwd, /etc/group and /etc/shadow (password hashes are not copied)")
    shadow = shadow_entries()
    groups = list(grp.getgrall())
    rows = []
    for user in sorted(pwd.getpwall(), key=lambda u: u.pw_uid):
        sh = shadow.get(user.pw_name, [user.pw_name, "", "", "", "", "", "", "", ""])
        keys = Path(user.pw_dir) / ".ssh" / "authorized_keys"
        try:
            key_count = sum(
                1
                for line in keys.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            )
        except OSError:
            key_count = 0
        status = password_status(sh[1])
        shell_ok = user.pw_shell not in NO_LOGIN_SHELLS
        can_sign_in = shell_ok and (status == "Set" or key_count > 0)
        member_of = sorted(
            g.gr_name for g in groups if user.pw_name in g.gr_mem and g.gr_gid != user.pw_gid
        )
        rows.append(
            [
                user.pw_name,
                user.pw_uid,
                grp.getgrgid(user.pw_gid).gr_name,
                user.pw_gecos,
                user.pw_dir,
                user.pw_shell,
                "Yes" if can_sign_in else "No",
                status,
                days_to_date(sh[2]),
                sh[4],
                days_to_date(sh[7]) or "Never",
                key_count,
                ";".join(member_of),
            ]
        )
    n_users = write_csv(
        folder / "local-accounts.csv",
        [
            "username",
            "uid",
            "primary_group",
            "description",
            "home",
            "shell",
            "can_sign_in",
            "password",
            "password_last_changed",
            "password_max_days",
            "account_expires",
            "ssh_keys",
            "groups",
        ],
        rows,
    )
    group_rows = [
        [g.gr_name, g.gr_gid, ";".join(sorted(g.gr_mem))]
        for g in sorted(groups, key=lambda g: g.gr_gid)
    ]
    n_groups = write_csv(folder / "local-groups.csv", ["group", "gid", "members"], group_rows)
    return n_users, n_groups


def sudoers_files() -> list[Path]:
    files = [Path("/etc/sudoers")]
    d = Path("/etc/sudoers.d")
    if d.is_dir():
        # sudo skips files whose names end in ~ or contain a dot.
        files += sorted(
            p for p in d.iterdir() if p.is_file() and not p.name.endswith("~") and "." not in p.name
        )
    return files


def group_members(name: str) -> list[str]:
    """Members of a local or domain group, as the server resolves them."""
    out = run(["getent", "group", name]).strip()
    if not out:
        return []
    fields = out.split(":")
    members = set(filter(None, fields[3].split(","))) if len(fields) > 3 else set()
    gid = fields[2] if len(fields) > 2 else ""
    for user in pwd.getpwall():
        if str(user.pw_gid) == gid:
            members.add(user.pw_name)
    return sorted(members)


def sudo_rules(folder: Path) -> int:
    LOG.append("read /etc/sudoers and every file in /etc/sudoers.d")
    raw, rules = [], []
    for path in sudoers_files():
        info = file_info(path)
        text = path.read_text()
        raw.append(
            f"### {path} (owner {info['owner']}, mode {info['mode']}, "
            f"modified {info['modified']})\n{text}\n"
        )
        for number, line in enumerate(text.splitlines(), start=1):
            line = line.split("#", 1)[0].strip() if not line.lstrip().startswith("#include") else ""
            if not line or line.startswith(
                ("Defaults", "Cmnd_Alias", "User_Alias", "Host_Alias", "Runas_Alias", "@include")
            ):
                continue
            match = re.match(r"^(\S+)\s+\S+\s*=\s*(\([^)]*\))?\s*(.*)$", line)
            if not match:
                continue
            principal, runas, rest = match.group(1), match.group(2) or "(root)", match.group(3)
            nopasswd = "NOPASSWD:" in rest
            commands = re.sub(r"\b(NO)?PASSWD:\s*", "", rest).strip()
            if principal.startswith("%"):
                kind, members = "group", group_members(principal[1:])
            else:
                kind, members = "user", [principal]
            for member in members or ["(no members)"]:
                rules.append(
                    [
                        member,
                        principal,
                        kind,
                        runas,
                        commands,
                        "Yes" if nopasswd else "No",
                        str(path),
                        number,
                        info["modified"],
                    ]
                )
    (folder / "sudoers.txt").write_text("\n".join(raw))
    return write_csv(
        folder / "sudo-rules.csv",
        [
            "account",
            "granted_to",
            "granted_to_type",
            "run_as",
            "commands",
            "no_password",
            "file",
            "line",
            "file_modified",
        ],
        rules,
    )


def ssh_settings(folder: Path) -> None:
    (folder / "sshd-effective.txt").write_text(run(["sshd", "-T"]))


def domain_membership(folder: Path) -> None:
    lines = ["# realm list", run(["realm", "list"]).strip() or "(not joined to a domain)", ""]
    conf = Path("/etc/sssd/sssd.conf")
    if conf.exists():
        LOG.append("read /etc/sssd/sssd.conf (sign in settings only)")
        keep = (
            "[",
            "access_provider",
            "simple_allow",
            "simple_deny",
            "use_fully_qualified",
            "ad_domain",
            "ad_gpo_access_control",
            "case_sensitive",
            "id_provider",
        )
        lines += ["# /etc/sssd/sssd.conf, sign in settings"]
        lines += [x for x in conf.read_text().splitlines() if x.strip().startswith(keep)]
        allowed = re.findall(r"^simple_allow_groups\s*=\s*(.+)$", conf.read_text(), re.M)
        for name in ",".join(allowed).split(","):
            if name.strip():
                members = ", ".join(group_members(name.strip()))
                lines += ["", f"# getent group {name.strip()}", members]
    (folder / "domain-sign-in.txt").write_text("\n".join(lines) + "\n")


def cron_rows() -> list[list]:
    rows = []
    sources = [Path("/etc/crontab")] if Path("/etc/crontab").exists() else []
    if Path("/etc/cron.d").is_dir():
        sources += sorted(p for p in Path("/etc/cron.d").iterdir() if p.is_file())
    for path in sources:
        info = file_info(path)
        pkg = package_of(path)
        for line in path.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#") or re.match(r"^[A-Z_]+=", s):
                continue
            parts = s.split(None, 6) if not s.startswith("@") else s.split(None, 2)
            if s.startswith("@"):
                schedule, user, command = parts[0], parts[1], parts[2] if len(parts) > 2 else ""
            elif len(parts) >= 7:
                schedule, user, command = " ".join(parts[:5]), parts[5], parts[6]
            else:
                continue
            rows.append(
                ["cron", str(path), schedule, user, command, info["owner"], info["modified"], pkg]
            )
    for period in ("hourly", "daily", "weekly", "monthly"):
        d = Path(f"/etc/cron.{period}")
        if d.is_dir():
            for path in sorted(p for p in d.iterdir() if p.is_file() and p.name != ".placeholder"):
                info = file_info(path)
                rows.append(
                    [
                        "cron",
                        str(path),
                        period,
                        "root",
                        str(path),
                        info["owner"],
                        info["modified"],
                        package_of(path),
                    ]
                )
    spool = Path("/var/spool/cron/crontabs")
    if spool.is_dir():
        for path in sorted(spool.iterdir()):
            info = file_info(path)
            for line in path.read_text().splitlines():
                s = line.strip()
                if s and not s.startswith("#") and not re.match(r"^[A-Z_]+=", s):
                    parts = s.split(None, 5)
                    rows.append(
                        [
                            "user crontab",
                            str(path),
                            " ".join(parts[:5]),
                            path.name,
                            parts[5] if len(parts) > 5 else "",
                            info["owner"],
                            info["modified"],
                            "not from a package",
                        ]
                    )
    return rows


def timer_rows() -> list[list]:
    rows = []
    out = run(["systemctl", "list-timers", "--all", "--no-pager", "--no-legend", "--output=json"])
    try:
        import json

        timers = json.loads(out) if out.strip().startswith("[") else []
    except ValueError:
        timers = []
    for t in timers:
        unit = t.get("unit", "")
        service = t.get("activates", "")
        path = run(["systemctl", "show", "-P", "FragmentPath", unit]).strip()
        exec_start = run(["systemctl", "show", "-P", "ExecStart", service]).strip()
        user = run(["systemctl", "show", "-P", "User", service]).strip() or "root"
        cal = run(["systemctl", "show", "-P", "TimersCalendar", unit]).strip()
        p = Path(path) if path else None
        info = file_info(p) if p and p.exists() else {"owner": "", "modified": ""}
        command = re.search(r"argv\[\]=([^;]*)", exec_start)
        rows.append(
            [
                "systemd timer",
                path,
                cal or "(see unit)",
                user,
                command.group(1).strip() if command else exec_start,
                info["owner"],
                info["modified"],
                package_of(p) if p else "",
            ]
        )
    return rows


def scheduled_jobs(folder: Path) -> int:
    LOG.append("read /etc/crontab, /etc/cron.d, /etc/cron.<period> and /var/spool/cron/crontabs")
    return write_csv(
        folder / "scheduled-jobs.csv",
        [
            "kind",
            "source",
            "schedule",
            "runs_as",
            "command",
            "file_owner",
            "file_modified",
            "package",
        ],
        cron_rows() + timer_rows(),
    )


def time_sync(folder: Path) -> None:
    parts = [
        "# timedatectl",
        run(["timedatectl"]),
        "# chronyc -n tracking",
        run(["chronyc", "-n", "tracking"]),
        "# chronyc -n sources -v",
        run(["chronyc", "-n", "sources", "-v"]),
    ]
    (folder / "time-sync.txt").write_text("\n".join(parts))


def patching(folder: Path) -> None:
    lists = Path("/var/lib/apt/lists")
    newest = max((p.stat().st_mtime for p in lists.glob("*_InRelease")), default=0)
    sim = run(["apt-get", "-s", "-o", "Debug::NoLocking=1", "dist-upgrade"])
    pending = [x for x in sim.splitlines() if x.startswith("Inst ")]
    security = [x for x in pending if "-security" in x]
    history = Path("/var/log/apt/history.log")
    runs = []
    if history.exists():
        LOG.append("read /var/log/apt/history.log")
        text = history.read_text(errors="replace")
        for block in text.split("\n\n"):
            start = re.search(r"^Start-Date: (.+)$", block, re.M)
            cmd = re.search(r"^Commandline: (.+)$", block, re.M)
            if start:
                runs.append(f"{start.group(1)}  {cmd.group(1) if cmd else ''}")
    auto = Path("/etc/apt/apt.conf.d/20auto-upgrades")
    lines = [
        f"Package lists last refreshed (UTC): {utc(newest) if newest else 'unknown'}",
        f"Updates available: {len(pending)}",
        f"Of which from the security archive: {len(security)}",
        "",
        "# Pending updates (apt-get -s dist-upgrade, simulated: nothing was installed)",
        *pending,
        "",
        "# Automatic updates: /etc/apt/apt.conf.d/20auto-upgrades",
        auto.read_text().strip() if auto.exists() else "(file not present)",
        "",
        "# unattended-upgrades service",
        run(["systemctl", "is-enabled", "unattended-upgrades"]).strip(),
        "",
        "# Package installs and upgrades (/var/log/apt/history.log)",
        *runs[-30:],
    ]
    (folder / "patching.txt").write_text("\n".join(lines) + "\n")


def last_logins(folder: Path) -> None:
    text = run(["last", "-F", "-w", "-n", "200"]) or run(["wtmpdb", "last", "-n", "200"])
    (folder / "last-logins.txt").write_text(text)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="folder to create the evidence folder in")
    args = parser.parse_args()
    if os.geteuid() != 0:
        print(
            "Run with sudo: /etc/shadow and the sudoers files are readable by root only.",
            file=sys.stderr,
        )
        return 1

    now = datetime.now(timezone.utc).replace(microsecond=0)
    host = socket.gethostname()
    folder = Path(args.out).expanduser() / f"host-{host}-{now:%Y%m%dT%H%M%SZ}"
    folder.mkdir(parents=True, exist_ok=False)
    operator = os.environ.get("SUDO_USER") or getpass.getuser()

    (folder / "host.txt").write_text(
        "\n".join(
            [
                f"Hostname: {host}",
                f"Fully qualified name: {socket.getfqdn()}",
                f"Kernel: {platform.release()}",
                *[
                    x
                    for x in Path("/etc/os-release").read_text().splitlines()
                    if x.startswith(("PRETTY_NAME", "VERSION_ID"))
                ],
                "",
                "# ip -brief address",
                run(["ip", "-brief", "address"]).strip(),
                "",
                "# uptime",
                run(["uptime"]).strip(),
            ]
        )
        + "\n"
    )
    n_users, n_groups = local_accounts(folder)
    n_rules = sudo_rules(folder)
    ssh_settings(folder)
    domain_membership(folder)
    n_jobs = scheduled_jobs(folder)
    time_sync(folder)
    patching(folder)
    last_logins(folder)

    passwd_lines = sum(1 for x in Path("/etc/passwd").read_text().splitlines() if x.strip())
    log = [
        "Northwind Retail: server evidence extraction",
        f"Extracted at (UTC):  {now.isoformat()}",
        f"Performed by:        {operator} (via sudo on the server)",
        f"Host:                {host}",
        "Method:              read only commands and file reads; nothing on the server was changed",
        "",
        "Record counts (completeness check: the first two must match)",
        f"  lines in /etc/passwd: {passwd_lines}",
        f"  rows in local-accounts.csv: {n_users}",
        f"  rows in local-groups.csv: {n_groups}",
        f"  rows in sudo-rules.csv: {n_rules}",
        f"  rows in scheduled-jobs.csv: {n_jobs}",
        "",
        "Commands run and files read",
        *[f"  {c}" for c in LOG],
    ]
    (folder / "extraction-log.txt").write_text("\n".join(log) + "\n")
    files = sorted(p for p in folder.iterdir() if p.is_file())
    (folder / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files))
    print(f"Evidence written to {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
