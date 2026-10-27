#!/usr/bin/env python3
"""Loads Northwind's change history into Gitea, as part of building the app server lab.

The app server is built after the audit period, so its history is recreated from
data/changes.json (written by history.py). Every change goes through Gitea itself: the
author pushes a branch and opens a pull request, the reviewer approves it, and the
merger merges it, all through the Gitea API acting as each person. Gitea records those
events with the time they happened, which is the build time, so a second step moves each
record to the time in the history.

    build_repo.py build     --token-file <admin token> [--gitea URL]   (Gitea running)
    build_repo.py backdate  --db /var/lib/gitea/data/gitea.db          (Gitea stopped)
    build_repo.py deploylog --out /var/log/northwind/deployments.log

The build step writes build-state.json, which the other two steps read.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
CHANGES = HERE / "data" / "changes.json"
APP_FILES = HERE / "files"
ORG, REPO = "northwind", "finance-app"
EMAIL_DOMAIN = "northwind.internal"

# Gitea accounts. Dates are when each account was created, before the period.
PEOPLE = {
    "james.carter": {"full_name": "James Carter", "created": "2025-11-03T09:05:00+00:00"},
    "ryan.patel": {"full_name": "Ryan Patel", "created": "2025-11-03T09:12:00+00:00"},
    "aisha.khan": {
        "full_name": "Aisha Khan",
        "created": "2025-11-10T10:30:00+00:00",
        "admin": True,
    },
    "leo.martin": {"full_name": "Leo Martin", "created": "2026-01-05T09:40:00+00:00"},
    "svc-deploy": {
        "full_name": "Deployment service account",
        "created": "2025-11-03T09:20:00+00:00",
    },
}
ADMIN_CREATED = "2025-11-03T09:00:00+00:00"
ORG_CREATED = "2025-11-03T09:10:00+00:00"
PROTECTION_SET = "2026-02-02T11:00:00+00:00"
OWNERS = ["james.carter", "ryan.patel"]
DEVELOPERS = ["aisha.khan", "leo.martin"]
DEPLOY_READERS = ["svc-deploy"]

# Gitea action types (models/activities/action.go).
ACT_COMMIT, ACT_CREATE_PR, ACT_MERGE_PR, ACT_DELETE_BRANCH, ACT_APPROVE = 5, 7, 11, 17, 21
COMMENT_REVIEW = 22


def ts(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp())


def iso(value: str, minutes: int = 0) -> str:
    return (datetime.fromisoformat(value) + timedelta(minutes=minutes)).isoformat()


def load_changes() -> dict:
    return json.loads(CHANGES.read_text())


class Gitea:
    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        sudo: str | None = None,
        ok: tuple[int, ...] = (200, 201, 204),
    ) -> dict | list:
        req = urllib.request.Request(
            f"{self.url}/api/v1{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        if sudo:
            req.add_header("Sudo", sudo)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode()
                status = resp.status
        except urllib.error.HTTPError as err:
            text, status = err.read().decode(), err.code
        if status not in ok:
            raise RuntimeError(f"{method} {path} as {sudo or 'admin'} returned {status}: {text}")
        return json.loads(text) if text.strip() else {}


def git(repo: Path, *args: str, env: dict | None = None) -> str:
    full_env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(repo.parent), **(env or {})}
    out = subprocess.run(
        ["git", "-C", str(repo), *args], env=full_env, capture_output=True, text=True
    )
    if out.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def identity(
    user: str, when: str, committer: str | None = None, commit_time: str | None = None
) -> dict:
    committer = committer or user
    return {
        "GIT_AUTHOR_NAME": PEOPLE[user]["full_name"],
        "GIT_AUTHOR_EMAIL": f"{user}@{EMAIL_DOMAIN}",
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_NAME": PEOPLE[committer]["full_name"],
        "GIT_COMMITTER_EMAIL": f"{committer}@{EMAIL_DOMAIN}",
        "GIT_COMMITTER_DATE": commit_time or when,
    }


def wait_until_quiet(db_path: Path) -> None:
    """Gitea writes activity records from a background queue. Waits until it has caught up."""
    last, quiet = -1, 0
    while quiet < 5:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30) as db:
            count = sum(
                db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("action", "notification", "comment", "branch")
            )
        quiet = quiet + 1 if count == last else 0
        last = count
        time.sleep(1)


def wait_for_merge(api: Gitea, number: int) -> dict:
    for _ in range(60):
        pr = api.call("GET", f"/repos/{ORG}/{REPO}/pulls/{number}")
        if pr.get("merged"):
            return pr
        time.sleep(0.5)
    raise RuntimeError(f"pull request #{number} did not show as merged")


def merge(api: Gitea, number: int, user: str) -> None:
    """Merges a pull request, waiting while Gitea is still checking it after a push."""
    for _ in range(120):
        pr = api.call("GET", f"/repos/{ORG}/{REPO}/pulls/{number}")
        if pr.get("mergeable"):
            result = api.call(
                "POST",
                f"/repos/{ORG}/{REPO}/pulls/{number}/merge",
                {"Do": "fast-forward-only", "delete_branch_after_merge": True},
                sudo=user,
                ok=(200, 405),
            )
            if "try again later" not in str(result.get("message", "")):
                return
        time.sleep(0.5)
    raise RuntimeError(f"pull request #{number} could not be merged")


def wait_for(api: Gitea, path: str, ready, what: str) -> None:
    """Gitea processes pushes in the background, so wait until the API reflects one."""
    for _ in range(120):
        result = api.call("GET", path, ok=(200, 404))
        if ready(result):
            return
        time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for {what}")


def setup_accounts(api: Gitea, passwords_out: Path) -> dict[str, str]:
    """Creates the people, the organisation, its teams and the repository."""
    passwords = {}
    existing = {u["login"] for u in api.call("GET", "/admin/users?limit=50")}
    for user, info in PEOPLE.items():
        if user in existing:
            continue
        passwords[user] = secrets.token_urlsafe(15)
        api.call(
            "POST",
            "/admin/users",
            {
                "username": user,
                "email": f"{user}@{EMAIL_DOMAIN}",
                "full_name": info["full_name"],
                "password": passwords[user],
                "must_change_password": False,
                "source_id": 0,
                "login_name": user,
                "send_notify": False,
            },
        )
        if info.get("admin"):
            api.call(
                "PATCH", f"/admin/users/{user}", {"admin": True, "login_name": user, "source_id": 0}
            )
    if passwords:
        with passwords_out.open("a") as f:
            for user, pw in passwords.items():
                f.write(f"{user},{pw}\n")
        os.chmod(passwords_out, 0o600)

    # Only the Head of IT may create organisations.
    if not api.call("GET", f"/orgs/{ORG}", ok=(200, 404)).get("id"):
        api.call(
            "PATCH",
            "/admin/users/james.carter",
            {"allow_create_organization": True, "login_name": "james.carter", "source_id": 0},
        )
        api.call(
            "POST",
            "/orgs",
            {"username": ORG, "full_name": "Northwind Retail", "visibility": "private"},
            sudo="james.carter",
        )
    teams = {t["name"]: t["id"] for t in api.call("GET", f"/orgs/{ORG}/teams")}
    for user in OWNERS:
        api.call("PUT", f"/teams/{teams['Owners']}/members/{user}")
    units = ["repo.code", "repo.issues", "repo.pulls", "repo.releases"]
    for name, permission, members, description in [
        ("Developers", "write", DEVELOPERS, "Developers of Northwind's applications"),
        ("Deploy", "read", DEPLOY_READERS, "Accounts that deploy to production"),
    ]:
        if name not in teams:
            teams[name] = api.call(
                "POST",
                f"/orgs/{ORG}/teams",
                {
                    "name": name,
                    "description": description,
                    "permission": permission,
                    "units": units,
                    "includes_all_repositories": True,
                },
            )["id"]
        for user in members:
            api.call("PUT", f"/teams/{teams[name]}/members/{user}")

    if not api.call("GET", f"/repos/{ORG}/{REPO}", ok=(200, 404)).get("id"):
        api.call(
            "POST",
            f"/orgs/{ORG}/repos",
            {
                "name": REPO,
                "description": "Northwind's finance application (supplier payments)",
                "private": True,
                "default_branch": "main",
                "auto_init": False,
            },
            sudo="james.carter",
        )
    api.call(
        "PATCH",
        f"/repos/{ORG}/{REPO}",
        {
            "allow_fast_forward_only_merge": True,
            "allow_merge_commits": False,
            "allow_rebase": False,
            "allow_rebase_explicit": False,
            "allow_squash_merge": False,
            "default_merge_style": "fast-forward-only",
            "default_delete_branch_after_merge": True,
            "has_wiki": False,
            "has_projects": False,
            "has_actions": False,
        },
        sudo="james.carter",
    )
    return passwords


def user_tokens(gitea_cmd: list[str], users: list[str]) -> dict[str, str]:
    tokens = {}
    for user in users:
        name = f"history-build-{int(time.time())}"
        out = subprocess.run(
            [
                *gitea_cmd,
                "admin",
                "user",
                "generate-access-token",
                "--username",
                user,
                "--token-name",
                name,
                "--scopes",
                "write:repository",
                "--raw",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        tokens[user] = out.stdout.strip().splitlines()[-1]
    return tokens


def push(repo: Path, url: str, user: str, token: str, refspec: str) -> None:
    auth = base64.b64encode(f"{user}:{token}".encode()).decode()
    git(
        repo, "-c", f"http.extraHeader=Authorization: Basic {auth}", "push", "--quiet", url, refspec
    )


def write_change(repo: Path, change: dict, version: str) -> None:
    (repo / "VERSION").write_text(version + "\n")
    ref = change["id"] or "no ticket"
    with (repo / "CHANGELOG.md").open("a") as f:
        f.write(f"\n## {version}\n\n* {change['title']} ({ref})\n")


def next_version(current: str, change: dict) -> str:
    major, minor, patch = (int(x) for x in current.split("."))
    if change["kind"] == "direct" or change["title"].startswith(("Emergency", "Fix")):
        return f"{major}.{minor}.{patch + 1}"
    return f"{major}.{minor + 1}.0"


def build(args: argparse.Namespace) -> int:
    history = load_changes()
    api = Gitea(args.gitea, Path(args.token_file).read_text().strip())
    db_path = Path(args.db)
    state_path = Path(args.state)
    if state_path.exists():
        print(f"{state_path} exists, so the history has already been built")
        return 0

    build_started = int(time.time())
    setup_accounts(api, Path(args.passwords))
    gitea_cmd = args.gitea_cmd.split()
    authors = sorted({c["author"] for c in history["changes"]} | {"ryan.patel"})
    tokens = user_tokens(gitea_cmd, authors)
    remote = f"{args.gitea}/{ORG}/{REPO}.git"

    work = Path(tempfile.mkdtemp(prefix="northwind-history-"))
    repo = work / "finance-app"
    repo.mkdir()
    git(repo, "init", "--quiet", "--initial-branch=main")
    git(repo, "config", "commit.gpgsign", "false")

    initial = history["initial_commit"]
    (repo / "app.py").write_text((APP_FILES / "app.py").read_text())
    (repo / "VERSION").write_text("1.0.0\n")
    (repo / "README.md").write_text(
        "# Northwind finance app\n\nLists supplier payments from the finance database.\n\n"
        "Changes reach production only through a pull request and a change ticket. "
        "Deploy with `sudo northwind-deploy <ticket>` on the app server.\n"
    )
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0\n\n* First release\n")
    git(repo, "add", "-A")
    git(
        repo,
        "commit",
        "--quiet",
        "-m",
        initial["title"],
        env=identity(initial["author"], initial["authored_at"]),
    )
    push(repo, remote, initial["author"], tokens[initial["author"]], "HEAD:refs/heads/main")
    initial_sha = git(repo, "rev-parse", "HEAD")
    wait_for(api, f"/repos/{ORG}/{REPO}", lambda r: r.get("empty") is False, "the first push")

    version, records = "1.0.0", []
    order = sorted(history["changes"], key=lambda c: c.get("merged_at") or c["authored_at"])
    for change in order:
        version = next_version(version, change)
        write_change(repo, change, version)
        git(repo, "add", "-A")
        author = change["author"]
        record = {"title": change["title"], "id": change["id"], "kind": change["kind"]}
        if change["kind"] == "direct":
            git(
                repo,
                "commit",
                "--quiet",
                "-m",
                change["title"],
                env=identity(author, change["authored_at"]),
            )
            push(repo, remote, author, tokens[author], "HEAD:refs/heads/main")
            record.update(pushed_at=iso(change["authored_at"], 8))
        else:
            # The author rebased the branch onto main just before it was merged.
            commit_time = iso(change["merged_at"], -40)
            message = f"{change['title']}\n\nChange ticket: {change['id']}"
            git(
                repo,
                "commit",
                "--quiet",
                "-m",
                message,
                env=identity(author, change["authored_at"], commit_time=commit_time),
            )
            push(repo, remote, author, tokens[author], f"HEAD:refs/heads/{change['branch']}")
            sha = git(repo, "rev-parse", "HEAD")
            wait_for(
                api,
                f"/repos/{ORG}/{REPO}/branches/{quote(change['branch'], safe='')}",
                lambda r, sha=sha: r.get("commit", {}).get("id") == sha,
                f"branch {change['branch']}",
            )
            body = (
                f"Change ticket: {change['id']}\n\n{change['title']}."
                if change["id"]
                else change["title"]
            )
            pr = api.call(
                "POST",
                f"/repos/{ORG}/{REPO}/pulls",
                {"title": change["title"], "head": change["branch"], "base": "main", "body": body},
                sudo=author,
            )
            if pr["number"] != change["pr"]:
                raise RuntimeError(f"expected pull request #{change['pr']}, got #{pr['number']}")
            if change["reviewer"]:
                api.call(
                    "POST",
                    f"/repos/{ORG}/{REPO}/pulls/{pr['number']}/reviews",
                    {"event": "APPROVED", "body": "Reviewed the change and the tests."},
                    sudo=change["reviewer"],
                )
            merge(api, pr["number"], change["merged_by"])
            merged = wait_for_merge(api, pr["number"])
            record.update(
                pr=pr["number"],
                branch=change["branch"],
                opened_at=iso(change["authored_at"], 30),
                reviewed_at=iso(change["merged_at"], -25) if change["reviewer"] else None,
                merged_at=change["merged_at"],
                merge_commit=merged["merge_commit_sha"],
            )
        record["commit"] = git(repo, "rev-parse", "HEAD")
        records.append(record)
        print(f"  {change['id'] or 'no ticket':14} {record.get('pr', ''):>3} {change['title']}")

    last_activity = max(r.get("merged_at") or r["pushed_at"] for r in records)
    api.call(
        "POST",
        f"/repos/{ORG}/{REPO}/branch_protections",
        {
            "rule_name": "main",
            "enable_push": True,
            "enable_push_whitelist": True,
            "push_whitelist_usernames": ["ryan.patel"],
            "required_approvals": 1,
            "enable_approvals_whitelist": False,
            "block_on_rejected_reviews": True,
            "dismiss_stale_approvals": False,
            "block_admin_merge_override": False,
            "enable_status_check": False,
        },
        sudo="james.carter",
    )
    wait_until_quiet(db_path)

    state = {
        "initial_commit": initial_sha,
        "initial": initial,
        "records": records,
        "last_activity": last_activity,
        "built_at": datetime.now().astimezone().isoformat(),
        "build_started": build_started,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(f"loaded {len(records)} changes into {ORG}/{REPO}")
    return 0


def backdate(args: argparse.Namespace) -> int:
    state = json.loads(Path(args.state).read_text())
    history = {c["title"]: c for c in load_changes()["changes"]}
    db = sqlite3.connect(args.db)
    repo_id = db.execute(
        "SELECT r.id FROM repository r JOIN user u ON u.id = r.owner_id "
        "WHERE u.lower_name = ? AND r.lower_name = ?",
        (ORG, REPO),
    ).fetchone()[0]
    uid = dict(db.execute("SELECT lower_name, id FROM user").fetchall())
    last_seen: dict[str, str] = {}

    def seen(user: str | None, when: str | None) -> None:
        if user and when and when > last_seen.get(user, ""):
            last_seen[user] = when

    initial = state["initial"]
    for rec in state["records"]:
        change = history[rec["title"]]
        if rec["kind"] == "direct":
            seen(change["author"], rec["pushed_at"])
            continue
        opened, merged = ts(rec["opened_at"]), ts(rec["merged_at"])
        reviewed = ts(rec["reviewed_at"]) if rec["reviewed_at"] else merged
        issue_id = db.execute(
            'SELECT id FROM issue WHERE repo_id = ? AND "index" = ?', (repo_id, rec["pr"])
        ).fetchone()[0]
        db.execute(
            "UPDATE issue SET created_unix = ?, updated_unix = ?, closed_unix = ? WHERE id = ?",
            (opened, merged, merged, issue_id),
        )
        db.execute("UPDATE pull_request SET merged_unix = ? WHERE issue_id = ?", (merged, issue_id))
        db.execute(
            "UPDATE review SET created_unix = ?, updated_unix = ? WHERE issue_id = ?",
            (reviewed, reviewed, issue_id),
        )
        db.execute(
            "UPDATE comment SET created_unix = CASE WHEN type = ? THEN ? ELSE ? END, "
            "updated_unix = CASE WHEN type = ? THEN ? ELSE ? END WHERE issue_id = ?",
            (COMMENT_REVIEW, reviewed, merged, COMMENT_REVIEW, reviewed, merged, issue_id),
        )
        db.execute(
            "UPDATE branch SET created_unix = ?, updated_unix = ?, deleted_unix = "
            "CASE WHEN is_deleted THEN ? ELSE deleted_unix END "
            "WHERE repo_id = ? AND name = ?",
            (opened - 300, merged, merged, repo_id, rec["branch"]),
        )
        seen(change["author"], rec["opened_at"])
        seen(change["reviewer"], rec["reviewed_at"])
        seen(change["merged_by"], rec["merged_at"])

    # The default branch row, the repository and the organisation.
    last = ts(state["last_activity"])
    first = ts(initial["authored_at"])
    db.execute(
        "UPDATE branch SET created_unix = ?, updated_unix = ? WHERE repo_id = ? AND name = 'main'",
        (first, last, repo_id),
    )
    db.execute(
        "UPDATE repository SET created_unix = ?, updated_unix = ? WHERE id = ?",
        (first - 600, last, repo_id),
    )
    db.execute("UPDATE repo_unit SET created_unix = ? WHERE repo_id = ?", (first - 600, repo_id))
    db.execute(
        "UPDATE protected_branch SET created_unix = ?, updated_unix = ? WHERE repo_id = ?",
        (ts(PROTECTION_SET), ts(PROTECTION_SET), repo_id),
    )
    backdate_activity(db, repo_id, state, first)

    # The accounts: when each was created and when each person last signed in.
    seen("svc-deploy", max(c["deployed_at"] for c in history.values()))
    seen(
        "james.carter", max(c["ticket"]["approved_at"] for c in history.values() if c.get("ticket"))
    )
    for user, info in PEOPLE.items():
        db.execute(
            "UPDATE user SET created_unix = ?, updated_unix = ?, last_login_unix = ? WHERE id = ?",
            (
                ts(info["created"]),
                ts(info["created"]),
                ts(last_seen.get(user, info["created"])),
                uid[user],
            ),
        )
    db.execute(
        "UPDATE user SET created_unix = ?, updated_unix = ? WHERE lower_name = ?",
        (ts(ORG_CREATED), ts(ORG_CREATED), ORG),
    )
    db.execute(
        "UPDATE user SET created_unix = ?, updated_unix = ?, last_login_unix = ? "
        "WHERE lower_name = 'gitea-admin'",
        (ts(ADMIN_CREATED),) * 3,
    )
    for table in ("team_user", "org_user"):
        cols = [c[1] for c in db.execute(f"PRAGMA table_info({table})")]
        if "created_unix" in cols:
            db.execute(f"UPDATE {table} SET created_unix = ?", (ts(ORG_CREATED),))

    # Rows Gitea updates as a side effect: who watches the repository, notification read
    # times, the language statistics and Gitea's built in OAuth applications.
    since = state["build_started"]
    for user, info in PEOPLE.items():
        db.execute(
            "UPDATE watch SET created_unix = ?, updated_unix = ? WHERE user_id = ?",
            (max(first, ts(info["created"])),) * 2 + (uid[user],),
        )
    db.execute(
        "UPDATE watch SET created_unix = ?, updated_unix = ? WHERE created_unix >= ?",
        (first, first, since),
    )
    db.execute(
        "UPDATE notification SET created_unix = (SELECT created_unix FROM issue i "
        "WHERE i.id = notification.issue_id), updated_unix = (SELECT updated_unix "
        "FROM issue i WHERE i.id = notification.issue_id) WHERE repo_id = ?",
        (repo_id,),
    )
    db.execute("UPDATE language_stat SET created_unix = ? WHERE repo_id = ?", (last, repo_id))
    db.execute(
        "UPDATE oauth2_application SET created_unix = ?, updated_unix = ? WHERE created_unix >= ?",
        (ts(ADMIN_CREATED), ts(ADMIN_CREATED), since),
    )

    # The tokens used to load the history are no longer needed.
    db.execute("DELETE FROM access_token WHERE name LIKE 'history-build-%'")
    db.commit()

    leftover = remaining_build_times(db, state["build_started"])
    db.close()
    if leftover:
        print("Records still carrying the build date:")
        for line in leftover:
            print("  " + line)
    print("history dates applied")
    return 0


def backdate_activity(db: sqlite3.Connection, repo_id: int, state: dict, first: int) -> None:
    """Dates each entry in the activity feed from the change it belongs to.

    Gitea writes these from a background queue, so their order does not follow the order
    of the changes. Each is matched on its content instead: the commit pushed, the branch
    deleted, or the pull request number.
    """
    by_commit = {r["commit"]: r for r in state["records"]}
    by_branch = {r["branch"]: r for r in state["records"] if r.get("branch")}
    by_pr = {r["pr"]: r for r in state["records"] if r.get("pr")}
    rows = db.execute(
        "SELECT id, op_type, ref_name, content FROM action WHERE repo_id = ?", (repo_id,)
    ).fetchall()
    for action_id, op, ref, content in rows:
        when = first
        ref = (ref or "").removeprefix("refs/heads/")
        if op == ACT_COMMIT:
            try:
                sha = json.loads(content)["Commits"][0]["Sha1"]
            except (ValueError, KeyError, IndexError, TypeError):
                sha = ""
            if ref == "main" and sha in by_commit:
                rec = by_commit[sha]
                when = ts(rec.get("merged_at") or rec["pushed_at"])
            elif ref in by_branch:
                when = ts(by_branch[ref]["opened_at"]) - 300
        elif op == ACT_DELETE_BRANCH and ref in by_branch:
            when = ts(by_branch[ref]["merged_at"])
        elif op in (ACT_CREATE_PR, ACT_MERGE_PR, ACT_APPROVE) and content:
            number = int(content.split("|", 1)[0]) if content.split("|", 1)[0].isdigit() else 0
            rec = by_pr.get(number)
            if rec:
                when = ts(
                    {
                        ACT_CREATE_PR: rec["opened_at"],
                        ACT_APPROVE: rec["reviewed_at"] or rec["merged_at"],
                    }.get(op, rec["merged_at"])
                )
        db.execute("UPDATE action SET created_unix = ? WHERE id = ?", (when, action_id))


def remaining_build_times(db: sqlite3.Connection, since: int) -> list[str]:
    """Lists columns that still hold a time from the build, as a check on the step above."""
    ignore = {
        "session",
        "access_token",
        "system_setting",
        "app_state",
        "version",
        "notice",
        "task",
        "user_setting",
        "email_hash",
    }
    found = []
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        if table in ignore:
            continue
        for col in [c[1] for c in db.execute(f'PRAGMA table_info("{table}")')]:
            if not col.endswith("_unix") and col != "commit_time":
                continue
            sql = f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" >= ?'
            n = db.execute(sql, (since,)).fetchone()[0]
            if n:
                found.append(f"{table}.{col}: {n}")
    return found


def deploylog(args: argparse.Namespace) -> int:
    state = json.loads(Path(args.state).read_text())
    commits = {r["title"]: r["commit"] for r in state["records"]}
    lines = []
    for change in load_changes()["changes"]:
        lines.append(
            f"{change['deployed_at']} deploy commit={commits[change['title']]} "
            f"ticket={change['id'] or 'none'} by={change['deployed_by']} result=success"
        )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sorted(lines)) + "\n")
    last = max(load_changes()["changes"], key=lambda c: c["deployed_at"])
    print(commits[last["title"]])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("step", choices=["build", "backdate", "deploylog"])
    parser.add_argument("--gitea", default="http://127.0.0.1:3000")
    parser.add_argument("--token-file", default="/root/northwind-lab/gitea-admin-token")
    parser.add_argument(
        "--gitea-cmd",
        default="sudo -u git gitea --config /etc/gitea/app.ini",
        help="how to run the gitea command line as the git user",
    )
    parser.add_argument("--db", default="/var/lib/gitea/data/gitea.db")
    parser.add_argument("--state", default="/root/northwind-lab/build-state.json")
    parser.add_argument("--passwords", default="/root/northwind-lab/gitea-passwords.csv")
    parser.add_argument("--out", default="/var/log/northwind/deployments.log")
    args = parser.parse_args()
    return {"build": build, "backdate": backdate, "deploylog": deploylog}[args.step](args)


if __name__ == "__main__":
    sys.exit(main())
