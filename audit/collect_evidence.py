#!/usr/bin/env python3
"""Collect ITGC evidence from the Northwind domain controller.

Read only. Exports the directory's users, group memberships, privileged groups and
password policy into a dated evidence folder, together with the raw source data,
an extraction log with record counts, and SHA-256 hashes of every file.

Run on the domain controller:  sudo python3 collect_evidence.py --out ~/evidence
"""

from __future__ import annotations

import argparse
import base64
import csv
import getpass
import hashlib
import os
import platform
import pwd
import shlex
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAM_LDB = os.environ.get("SAM_LDB", "/var/lib/samba/private/sam.ldb")
SAMBA_TOOL = shlex.split(os.environ.get("SAMBA_TOOL", "samba-tool"))
SMB_CONF = os.environ.get("SMB_CONF")
BASE_DN = "DC=northwind,DC=internal"
PRIVILEGED_GROUPS = ["Domain Admins", "Enterprise Admins", "Schema Admins", "Administrators"]
USER_FILTER = "(&(objectClass=user)(!(objectClass=computer)))"
USER_ATTRS = [
    "sAMAccountName",
    "givenName",
    "sn",
    "employeeID",
    "department",
    "title",
    "manager",
    "userAccountControl",
    "pwdLastSet",
    "lastLogonTimestamp",
    "whenCreated",
    "accountExpires",
    "memberOf",
    "description",
    "distinguishedName",
]

UAC_DISABLED = 0x2
UAC_DONT_EXPIRE_PASSWORD = 0x10000
NEVER = {0, 9223372036854775807}

LOG: list[str] = []


def run(cmd: list[str]) -> str:
    """Run a read only command, record it in the extraction log, return its output."""
    LOG.append("$ " + " ".join(shlex.quote(c) for c in cmd))
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def samba_tool(*args: str) -> str:
    conf = ["-s", SMB_CONF] if SMB_CONF else []
    return run([*SAMBA_TOOL, *args, *conf])


def parse_ldif(text: str) -> list[dict[str, list[str]]]:
    """Parse ldbsearch output: unfold continuation lines and decode base64 values."""
    records, current, lines = [], None, []
    for raw in text.splitlines():
        if raw.startswith(" ") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    for line in lines:
        if line.startswith("#") or line.startswith("ref:"):
            continue
        if not line.strip():
            if current:
                records.append(current)
            current = None
            continue
        if line.startswith("dn:"):
            current = {}
        if current is None or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if value.startswith(":"):
            value = base64.b64decode(value[1:].strip()).decode("utf-8", errors="replace")
        else:
            value = value.strip()
        current.setdefault(key, []).append(value)
    if current:
        records.append(current)
    return records


def first(rec: dict, key: str) -> str:
    return rec.get(key, [""])[0]


def filetime(value: str) -> str:
    """Windows FILETIME (100ns since 1601) to ISO 8601 UTC; blank if never set."""
    if not value or int(value) in NEVER:
        return ""
    stamp = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=int(value) // 10)
    return stamp.isoformat(timespec="seconds")


def generalized_time(value: str) -> str:
    """LDAP GeneralizedTime (20261027020500.0Z) to ISO 8601 UTC."""
    if not value:
        return ""
    stamp = datetime.strptime(value.split(".")[0], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return stamp.isoformat(timespec="seconds")


def cn(dn: str) -> str:
    return dn.split(",", 1)[0].split("=", 1)[1] if dn else ""


def container(dn: str) -> str:
    """The OU path of an object, without the domain part, for example Finance/Staff/Northwind."""
    parts = [p.split("=", 1)[1] for p in dn.split(",")[1:] if p.upper().startswith(("OU=", "CN="))]
    return "/".join(parts)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="folder to create the evidence folder in")
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("Run with sudo: the directory database is readable by root only.", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).replace(microsecond=0)
    folder = Path(args.out).expanduser() / f"directory-{now:%Y%m%dT%H%M%SZ}"
    folder.mkdir(parents=True, exist_ok=False)
    operator = os.environ.get("SUDO_USER") or getpass.getuser()

    # 1. Raw source: every user object, exactly as returned by the directory.
    raw = run(["ldbsearch", "-H", SAM_LDB, "-b", BASE_DN, USER_FILTER, *USER_ATTRS])
    (folder / "raw-users.ldif").write_text(raw)
    users = sorted(parse_ldif(raw), key=lambda r: first(r, "sAMAccountName").lower())

    dn_to_name = {
        first(u, "distinguishedName") or first(u, "dn"): first(u, "sAMAccountName") for u in users
    }

    # 2. User listing, one row per account.
    with (folder / "users.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "username",
                "given_name",
                "surname",
                "employee_id",
                "department",
                "job_title",
                "manager",
                "location",
                "enabled",
                "password_never_expires",
                "password_last_set",
                "last_logon",
                "created",
                "account_expires",
                "groups",
                "description",
            ]
        )
        for u in users:
            uac = int(first(u, "userAccountControl") or 0)
            manager_dn = first(u, "manager")
            w.writerow(
                [
                    first(u, "sAMAccountName"),
                    first(u, "givenName"),
                    first(u, "sn"),
                    first(u, "employeeID"),
                    first(u, "department"),
                    first(u, "title"),
                    dn_to_name.get(manager_dn, cn(manager_dn)),
                    container(first(u, "dn")),
                    "No" if uac & UAC_DISABLED else "Yes",
                    "Yes" if uac & UAC_DONT_EXPIRE_PASSWORD else "No",
                    filetime(first(u, "pwdLastSet")),
                    filetime(first(u, "lastLogonTimestamp")),
                    generalized_time(first(u, "whenCreated")),
                    filetime(first(u, "accountExpires")) or "Never",
                    ";".join(sorted(cn(g) for g in u.get("memberOf", []))),
                    first(u, "description"),
                ]
            )

    # 3. Group memberships, one row per group and member.
    groups = sorted(
        line.strip() for line in samba_tool("group", "list").splitlines() if line.strip()
    )
    member_rows = []
    for group in groups:
        for member in samba_tool("group", "listmembers", group).splitlines():
            if member.strip():
                member_rows.append([group, member.strip()])
    with (folder / "group-members.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "member"])
        w.writerows(member_rows)

    # 4. Privileged groups, listed separately for the privileged access tests.
    with (folder / "privileged-groups.txt").open("w") as f:
        for group in PRIVILEGED_GROUPS:
            members = sorted(
                m.strip()
                for m in samba_tool("group", "listmembers", group).splitlines()
                if m.strip()
            )
            f.write(f"{group} ({len(members)} members)\n")
            for m in members:
                f.write(f"  {m}\n")
            f.write("\n")

    # 5. Domain password and lockout policy.
    (folder / "password-policy.txt").write_text(samba_tool("domain", "passwordsettings", "show"))

    # 6. Extraction log: who, when, where, how, and record counts for completeness.
    counts = {
        "user objects in raw-users.ldif": raw.count("\ndn: ") + raw.startswith("dn: "),
        "rows in users.csv": len(users),
        "groups listed": len(groups),
        "rows in group-members.csv": len(member_rows),
    }
    log = [
        "Northwind Retail: directory evidence extraction",
        f"Extracted at (UTC):  {now.isoformat()}",
        f"Performed by:        {operator} (via sudo on the domain controller)",
        f"Host:                {platform.node()}",
        f"Source:              {SAM_LDB}",
        "Method:              read only queries; no changes were made to the directory",
        "",
        "Record counts (completeness check: the first two must match)",
        *[f"  {k}: {v}" for k, v in counts.items()],
        "",
        "Commands run",
        *[f"  {c}" for c in LOG],
    ]
    (folder / "extraction-log.txt").write_text("\n".join(log) + "\n")

    # 7. Hashes, verifiable later with: sha256sum -c SHA256SUMS
    files = sorted(p for p in folder.iterdir() if p.is_file())
    (folder / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files))

    if os.environ.get("SUDO_USER"):
        owner = pwd.getpwnam(os.environ["SUDO_USER"])
        for p in [folder.parent, folder, *folder.iterdir()]:
            os.chown(p, owner.pw_uid, owner.pw_gid)

    print(f"Evidence saved to {folder}")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if counts["user objects in raw-users.ldif"] != counts["rows in users.csv"]:
        print("WARNING: record counts do not match, check the extraction", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
