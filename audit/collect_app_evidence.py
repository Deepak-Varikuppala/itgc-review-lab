#!/usr/bin/env python3
"""Collect change management and operations evidence from the Northwind app server.

Read only. Exports from Gitea's database (opened read only) the accounts, repository
access, pull requests, reviews and branch protection; from the repository itself the
commits on main; and from the server the deployment log, the deployment tool, the
production release, the backup log and the backup job. Writes a dated evidence folder
with an extraction log and SHA-256 hashes of every file.

Run on the app server:  sudo python3 collect_app_evidence.py --out ~/evidence
"""

from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GITEA_DB = os.environ.get("GITEA_DB", "/var/lib/gitea/data/gitea.db")
GITEA_CONF = os.environ.get("GITEA_CONF", "/etc/gitea/app.ini")
GITEA_REPOS = os.environ.get("GITEA_REPOS", "/var/lib/gitea/data/gitea-repositories")
ORG, REPO = "northwind", "finance-app"
APP_DIR = Path("/opt/northwind/finance-app")
DEPLOY_LOG = Path("/var/log/northwind/deployments.log")
BACKUP_LOG = Path("/var/log/northwind/backup.log")
DEPLOY_TOOL = Path("/usr/local/sbin/northwind-deploy")
BACKUP_TOOL = Path("/usr/local/sbin/northwind-backup")
BACKUP_CRON = Path("/etc/cron.d/northwind-backup")
BACKUP_DIR = Path("/var/backups/northwind")

ACCESS = {0: "none", 1: "read", 2: "write", 3: "admin", 4: "owner"}
REVIEW = {0: "pending", 1: "approved", 2: "comment", 3: "changes requested", 4: "request"}
USER_TYPE = {0: "individual", 1: "organisation", 2: "reserved", 3: "placeholder", 4: "bot"}
SECRET_WORDS = ("SECRET", "TOKEN", "PASSWD", "PASSWORD", "KEY")
LOG: list[str] = []
COUNTS: dict[str, int] = {}


def utc(unix: int | None) -> str:
    if not unix:
        return ""
    return datetime.fromtimestamp(unix, timezone.utc).isoformat()


def run(cmd: list[str]) -> str:
    LOG.append("$ " + shlex.join(cmd))
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(f"{shlex.join(cmd)} failed: {out.stderr.strip()}")
    return out.stdout


def query(db: sqlite3.Connection, sql: str, params: tuple = ()) -> list[tuple]:
    LOG.append("sql> " + " ".join(sql.split()))
    return db.execute(sql, params).fetchall()


def write_csv(path: Path, header: list[str], rows: list[list]) -> int:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def names(db: sqlite3.Connection, ids_json: str | None) -> str:
    ids = json.loads(ids_json) if ids_json and ids_json != "null" else []
    if not ids:
        return ""
    marks = ",".join("?" * len(ids))
    return ";".join(
        sorted(r[0] for r in db.execute(f"SELECT lower_name FROM user WHERE id IN ({marks})", ids))
    )


def gitea(db: sqlite3.Connection, folder: Path) -> dict[str, int]:
    counts = {}
    (repo_id,) = query(
        db,
        "SELECT r.id FROM repository r JOIN user o ON o.id = r.owner_id "
        "WHERE o.lower_name = ? AND r.lower_name = ?",
        (ORG, REPO),
    )[0]

    rows = query(
        db,
        "SELECT lower_name, full_name, email, type, is_admin, is_active, "
        "prohibit_login, is_restricted, created_unix, last_login_unix "
        "FROM user ORDER BY lower_name",
    )
    counts["accounts in the Gitea user table"] = query(db, "SELECT COUNT(*) FROM user")[0][0]
    counts["rows in gitea-users.csv"] = write_csv(
        folder / "gitea-users.csv",
        [
            "username",
            "full_name",
            "email",
            "type",
            "site_administrator",
            "active",
            "sign_in_blocked",
            "restricted",
            "created",
            "last_sign_in",
        ],
        [
            [
                r[0],
                r[1],
                r[2],
                USER_TYPE.get(r[3], r[3]),
                "Yes" if r[4] else "No",
                "Yes" if r[5] else "No",
                "Yes" if r[6] else "No",
                "Yes" if r[7] else "No",
                utc(r[8]),
                utc(r[9]),
            ]
            for r in rows
        ],
    )

    # Who can do what to the repository: through organisation teams, and as collaborators.
    access = []
    for team, authorize, _all_repos, member, code_mode in query(
        db,
        """
            SELECT t.name, t.authorize, t.includes_all_repositories, u.lower_name,
                   COALESCE((SELECT access_mode FROM team_unit tu
                             WHERE tu.team_id = t.id AND tu.type = 1), 0)
            FROM team t JOIN user o ON o.id = t.org_id
            JOIN team_user m ON m.team_id = t.id JOIN user u ON u.id = m.uid
            WHERE o.lower_name = ?
              AND (t.includes_all_repositories = 1
                   OR EXISTS (SELECT 1 FROM team_repo tr WHERE tr.team_id = t.id
                              AND tr.repo_id = ?))
            ORDER BY t.name, u.lower_name""",
        (ORG, repo_id),
    ):
        mode = 4 if authorize == 4 else max(authorize, code_mode)
        access.append([f"{ORG}/{REPO}", member, ACCESS[mode], f"team {team}"])
    for member, mode in query(
        db,
        "SELECT u.lower_name, c.mode FROM collaboration c "
        "JOIN user u ON u.id = c.user_id WHERE c.repo_id = ?",
        (repo_id,),
    ):
        access.append([f"{ORG}/{REPO}", member, ACCESS.get(mode, mode), "collaborator"])
    for (member,) in query(db, "SELECT lower_name FROM user WHERE is_admin = 1 AND type = 0"):
        access.append([f"{ORG}/{REPO}", member, "admin", "Gitea site administrator"])
    counts["rows in gitea-repo-access.csv"] = write_csv(
        folder / "gitea-repo-access.csv",
        ["repository", "account", "access", "granted_through"],
        access,
    )

    prs = query(
        db,
        """
        SELECT i."index", i.name, a.lower_name, i.created_unix, p.has_merged, p.merged_unix,
               m.lower_name, p.merged_commit_id, p.head_branch, p.base_branch, i.content
        FROM pull_request p JOIN issue i ON i.id = p.issue_id
        JOIN user a ON a.id = i.poster_id LEFT JOIN user m ON m.id = p.merger_id
        WHERE p.base_repo_id = ? ORDER BY i."index" """,
        (repo_id,),
    )
    pr_rows = []
    for number, title, author, opened, merged, merged_at, merger, commit, head, base, body in prs:
        ticket = re.search(r"CHG-\d{4}-\d{4}", body or "")
        pr_rows.append(
            [
                number,
                title,
                author,
                utc(opened),
                "Yes" if merged else "No",
                utc(merged_at),
                merger or "",
                commit or "",
                head,
                base,
                ticket.group(0) if ticket else "",
            ]
        )
    counts["pull requests in the database"] = query(
        db, "SELECT COUNT(*) FROM issue WHERE repo_id = ? AND is_pull = 1", (repo_id,)
    )[0][0]
    counts["rows in gitea-pull-requests.csv"] = write_csv(
        folder / "gitea-pull-requests.csv",
        [
            "number",
            "title",
            "author",
            "opened",
            "merged",
            "merged_at",
            "merged_by",
            "merge_commit",
            "branch",
            "base",
            "ticket_in_description",
        ],
        pr_rows,
    )

    reviews = query(
        db,
        """
        SELECT i."index", u.lower_name, r.type, r.official, r.commit_id, r.created_unix,
               r.content
        FROM review r JOIN issue i ON i.id = r.issue_id JOIN user u ON u.id = r.reviewer_id
        WHERE i.repo_id = ? AND r.type != 0 ORDER BY i."index", r.created_unix""",
        (repo_id,),
    )
    counts["rows in gitea-reviews.csv"] = write_csv(
        folder / "gitea-reviews.csv",
        [
            "pull_request",
            "reviewer",
            "decision",
            "counts_towards_approval",
            "commit",
            "submitted",
            "comment",
        ],
        [
            [r[0], r[1], REVIEW.get(r[2], r[2]), "Yes" if r[3] else "No", r[4], utc(r[5]), r[6]]
            for r in reviews
        ],
    )

    protection = []
    for row in query(db, "SELECT * FROM protected_branch WHERE repo_id = ?", (repo_id,)):
        cols = [c[1] for c in db.execute("PRAGMA table_info(protected_branch)")]
        rule = dict(zip(cols, row, strict=True))
        protection.append(
            {
                "rule": rule["branch_name"],
                "direct_push_allowed": bool(rule["can_push"]),
                "direct_push_limited_to_listed_accounts": bool(rule["enable_whitelist"]),
                "accounts_allowed_to_push": names(db, rule["whitelist_user_i_ds"]),
                "force_push_allowed": bool(rule["can_force_push"]),
                "required_approvals": rule["required_approvals"],
                "approvals_limited_to_listed_accounts": bool(rule["enable_approvals_whitelist"]),
                "merge_limited_to_listed_accounts": bool(rule["enable_merge_whitelist"]),
                "blocked_by_rejected_review": bool(rule["block_on_rejected_reviews"]),
                "approvals_dismissed_when_new_commits_pushed": bool(
                    rule["dismiss_stale_approvals"]
                ),
                "status_checks_required": bool(rule["enable_status_check"]),
                "signed_commits_required": bool(rule["require_signed_commits"]),
                "administrators_cannot_override": bool(rule["block_admin_merge_override"]),
                "created": utc(rule["created_unix"]),
                "updated": utc(rule["updated_unix"]),
            }
        )
    (folder / "gitea-branch-protection.json").write_text(json.dumps(protection, indent=2) + "\n")
    counts["branch protection rules"] = len(protection)

    pushes = query(
        db,
        """
        SELECT a.created_unix, u.lower_name, a.ref_name, a.content
        FROM action a JOIN user u ON u.id = a.act_user_id
        WHERE a.repo_id = ? AND a.op_type = 5 AND a.user_id = a.act_user_id
          AND a.ref_name = 'refs/heads/main' ORDER BY a.created_unix""",
        (repo_id,),
    )
    push_rows = []
    for when, who, ref, content in pushes:
        try:
            commits = [c["Sha1"] for c in json.loads(content)["Commits"]]
        except (ValueError, KeyError, TypeError):
            commits = []
        if not commits:  # Gitea also logs an empty event when a branch is first created
            continue
        push_rows.append([utc(when), who, ref.removeprefix("refs/heads/"), ";".join(commits)])
    counts["rows in gitea-main-updates.csv"] = write_csv(
        folder / "gitea-main-updates.csv", ["time", "account", "branch", "commits"], push_rows
    )

    settings = []
    LOG.append(f"read {GITEA_CONF} (values of secret settings removed)")
    for line in Path(GITEA_CONF).read_text().splitlines():
        key = line.split("=", 1)[0].strip().upper()
        settings.append(
            f"{line.split('=', 1)[0].strip()} = (removed)"
            if "=" in line and any(w in key for w in SECRET_WORDS)
            else line
        )
    (folder / "gitea-settings.txt").write_text("\n".join(settings) + "\n")
    return counts


def repository(folder: Path) -> int:
    bare = Path(GITEA_REPOS) / ORG / f"{REPO}.git"
    out = run(
        [
            "git",
            "-c",
            f"safe.directory={bare}",
            "-C",
            str(bare),
            "log",
            "--first-parent",
            "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%cn%x1f%cI%x1f%s",
            "main",
        ]
    )
    rows = [line.split("\x1f") for line in out.splitlines() if line]
    total = run(
        [
            "git",
            "-c",
            f"safe.directory={bare}",
            "-C",
            str(bare),
            "rev-list",
            "--count",
            "--first-parent",
            "main",
        ]
    ).strip()
    COUNTS["commits on main (git rev-list --count)"] = int(total)
    return write_csv(
        folder / "git-main-commits.csv",
        ["commit", "author", "author_email", "authored", "committer", "committed", "subject"],
        rows,
    )


def server(folder: Path) -> dict[str, int]:
    counts = {}
    for src, name in [(DEPLOY_LOG, "deployments.log"), (BACKUP_LOG, "backup.log")]:
        LOG.append(f"copied {src}")
        shutil.copyfile(src, folder / name)
        counts[f"lines in {name}"] = sum(1 for line in src.read_text().splitlines() if line)

    def described(path: Path) -> str:
        st = path.stat()
        return (
            f"### {path}  sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"modified {utc(int(st.st_mtime))}\n{path.read_text()}"
        )

    LOG.append(f"read {DEPLOY_TOOL}, {BACKUP_TOOL} and {BACKUP_CRON}")
    (folder / "deploy-tool.txt").write_text(described(DEPLOY_TOOL))
    backup_files = sorted(BACKUP_DIR.glob("finance-*.db.gz"))
    listing = "\n".join(
        f"{p.name}  {p.stat().st_size} bytes  modified {utc(int(p.stat().st_mtime))}"
        for p in backup_files
    )
    LOG.append(f"listed {BACKUP_DIR}")
    (folder / "backup-job.txt").write_text(
        described(BACKUP_CRON)
        + "\n"
        + described(BACKUP_TOOL)
        + f"\n### Backup files in {BACKUP_DIR}\n{listing}\n"
    )

    commit = run(
        ["git", "-c", f"safe.directory={APP_DIR}", "-C", str(APP_DIR), "rev-parse", "HEAD"]
    ).strip()
    version = (APP_DIR / "VERSION").read_text().strip()
    status = subprocess.run(
        ["systemctl", "is-active", "finance-app"], capture_output=True, text=True
    ).stdout.strip()
    LOG.append("$ systemctl is-active finance-app")
    (folder / "production-release.txt").write_text(
        f"Production checkout: {APP_DIR}\nCommit: {commit}\nVersion: {version}\n"
        f"Service finance-app: {status}\n"
    )
    return counts


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="folder to create the evidence folder in")
    args = parser.parse_args()
    if os.geteuid() != 0:
        print(
            "Run with sudo: Gitea's database and the server logs are readable by root only.",
            file=sys.stderr,
        )
        return 1

    now = datetime.now(timezone.utc).replace(microsecond=0)
    folder = Path(args.out).expanduser() / f"app-{now:%Y%m%dT%H%M%SZ}"
    folder.mkdir(parents=True, exist_ok=False)
    operator = os.environ.get("SUDO_USER") or getpass.getuser()

    db = sqlite3.connect(f"file:{GITEA_DB}?mode=ro", uri=True)
    counts = gitea(db, folder)
    db.close()
    rows = repository(folder)
    counts.update(COUNTS)
    counts["rows in git-main-commits.csv"] = rows
    counts.update(server(folder))

    log = [
        "Northwind Retail: app server evidence extraction",
        f"Extracted at (UTC):  {now.isoformat()}",
        f"Performed by:        {operator} (via sudo on the app server)",
        f"Host:                {platform.node()}",
        f"Sources:             Gitea database {GITEA_DB} (opened read only), the repository "
        f"under {GITEA_REPOS}, and the server's logs and configuration",
        "Method:              read only queries and file reads; nothing was changed",
        "",
        "Record counts (completeness check: where a source count is shown, the rows",
        "written from it must match)",
        *[f"  {k}: {v}" for k, v in counts.items()],
        "",
        "Commands and queries run",
        *[f"  {c}" for c in LOG],
    ]
    (folder / "extraction-log.txt").write_text("\n".join(log) + "\n")
    files = sorted(p for p in folder.iterdir() if p.is_file())
    (folder / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files))
    print(f"Evidence written to {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
