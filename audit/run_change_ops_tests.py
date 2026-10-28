#!/usr/bin/env python3
"""Run the Northwind change management, IT operations and server access ITGC tests.

Follows the test plan in docs/test-plan-change-and-operations.md. Tests that compare
system records without judgement cover the whole population. CM-04 and AC-18 need each
item to be read and judged, so they use a random sample drawn with a recorded seed.

    python3 audit/run_change_ops_tests.py \\
        --app evidence/app-<timestamp> \\
        --host evidence/host-linux-<timestamp> --host evidence/host-linux2-<timestamp> \\
        --directory evidence/directory-<timestamp>

Outputs workpapers/change-operations-workpaper.xlsx and
workpapers/change-operations-results.json.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from run_tests import (
    BANK_HOLIDAYS_2026,
    PERIOD_END,
    PERIOD_START,
    ROOT,
    Item,
    Test,
    iso_date,
    read_csv,
    sentence,
    verify_evidence,
    working_days_after,
)

SEED = 20261001
# Findings already raised for access that should not be held, by the group concerned.
GROUP_FINDINGS = {
    "Domain Admins": ["F2"],
    "Finance-Payments-Approvers": ["F8"],
    "Finance-Payments-Initiators": ["F4"],
    "GG-Finance": ["F4"],
    "Change-Deployers": ["F12"],
}
APP_SERVER = "linux2"
DEPLOY_TOOL = "/usr/local/sbin/northwind-deploy"
ACCESS_ORDER = ["none", "read", "write", "admin", "owner"]
MATRIX_CODE_ACCESS = {
    "none": "none",
    "write": "write",
    "owner": "owner",
    "site administrator": "admin",
}
SSH_RULES = [
    ("permitrootlogin", "no", lambda v: v == "no"),
    ("permitemptypasswords", "no", lambda v: v == "no"),
    ("maxauthtries", "4 or fewer", lambda v: v.isdigit() and int(v) <= 4),
    ("x11forwarding", "no", lambda v: v == "no"),
    ("ignorerhosts", "yes", lambda v: v == "yes"),
    ("hostbasedauthentication", "no", lambda v: v == "no"),
    ("logingracetime", "60 seconds or less", lambda v: v.isdigit() and 0 < int(v) <= 60),
    ("clientaliveinterval", "1 to 900 seconds", lambda v: v.isdigit() and 1 <= int(v) <= 900),
]
# Observations of the domain controller's clock made during fieldwork, recorded in
# docs/fieldwork-notes.md.
CLOCK_OBSERVATIONS = {
    "linux": [
        "27 October 2026: the clock was about 38 minutes slow and was corrected by hand "
        "(chronyc makestep) before the directory evidence was extracted",
        "28 October 2026: the clock was about 22 hours behind, which stopped the app server "
        "joining the domain (Kerberos rejects clocks more than 5 minutes apart); it was "
        "corrected by restarting chrony",
    ]
}


def sample_size(population: int) -> int:
    """The sample size table in the test plan, for controls that operate when needed."""
    if population <= 4:
        return population
    if population <= 12:
        return 5
    if population <= 52:
        return 15
    if population <= 250:
        return 25
    return 40


def select_sample(keys: list[str]) -> list[str]:
    """Random selection without replacement, reproducible from the recorded seed."""
    return sorted(random.Random(SEED).sample(sorted(keys), sample_size(len(keys))))


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def in_period(value: str) -> bool:
    return PERIOD_START <= ts(value).date() <= PERIOD_END


def working_days_between(start: date, end: date) -> int:
    """Working days after start up to and including end."""
    days, d = 0, start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in BANK_HOLIDAYS_2026:
            days += 1
    return days


def user_of(email: str) -> str:
    return email.split("@", 1)[0]


class HostEvidence:
    def __init__(self, folder: Path):
        self.dir = folder
        self.host = folder.name.split("-")[1]
        self.accounts = read_csv(folder / "local-accounts.csv")
        self.sudo = read_csv(folder / "sudo-rules.csv")
        self.jobs = read_csv(folder / "scheduled-jobs.csv")
        self.sshd = {}
        for line in (folder / "sshd-effective.txt").read_text().splitlines():
            key, _, value = line.partition(" ")
            self.sshd.setdefault(key.lower(), value.strip())
        self.time_sync = (folder / "time-sync.txt").read_text()
        self.patching = (folder / "patching.txt").read_text()
        self.sign_in = (folder / "domain-sign-in.txt").read_text()
        log = (folder / "extraction-log.txt").read_text()
        stamp = next(line for line in log.splitlines() if line.startswith("Extracted at"))
        self.as_at = datetime.fromisoformat(stamp.split(":", 1)[1].strip())


class Evidence:
    def __init__(self, app: Path, hosts: list[Path], directory: Path, scenario: Path):
        self.app_dir, self.directory_dir = app, directory
        self.hosts = {h.host: h for h in (HostEvidence(p) for p in hosts)}
        self.gitea_users = {u["username"]: u for u in read_csv(app / "gitea-users.csv")}
        self.repo_access = read_csv(app / "gitea-repo-access.csv")
        self.prs = {int(p["number"]): p for p in read_csv(app / "gitea-pull-requests.csv")}
        self.reviews: dict[int, list[dict]] = {}
        for r in read_csv(app / "gitea-reviews.csv"):
            self.reviews.setdefault(int(r["pull_request"]), []).append(r)
        self.protection = json.loads((app / "gitea-branch-protection.json").read_text())
        self.commits = {c["commit"]: c for c in read_csv(app / "git-main-commits.csv")}
        self.pushes = {}
        for p in read_csv(app / "gitea-main-updates.csv"):
            for sha in p["commits"].split(";"):
                self.pushes[sha] = p
        self.pr_by_commit = {
            p["merge_commit"]: p for p in self.prs.values() if p["merged"] == "Yes"
        }
        self.deployments = []
        pattern = re.compile(r"^(\S+) deploy commit=(\w+) ticket=(\S+) by=(\S+) result=(\w+)$")
        for line in (app / "deployments.log").read_text().splitlines():
            m = pattern.match(line)
            if m:
                self.deployments.append(
                    dict(zip(["at", "commit", "ticket", "by", "result"], m.groups(), strict=True))
                )
        self.backup_log = (app / "backup.log").read_text().splitlines()
        self.deploy_tool = (app / "deploy-tool.txt").read_text()
        self.backup_job = (app / "backup-job.txt").read_text()
        log = (app / "extraction-log.txt").read_text()
        stamp = next(line for line in log.splitlines() if line.startswith("Extracted at"))
        self.as_at = datetime.fromisoformat(stamp.split(":", 1)[1].strip()).date()

        self.users = {u["username"]: u for u in read_csv(directory / "users.csv")}
        self.members: dict[str, set[str]] = {}
        for row in read_csv(directory / "group-members.csv"):
            self.members.setdefault(row["group"], set()).add(row["member"])

        self.tickets = {t["ticket_id"]: t for t in read_csv(scenario / "change-tickets.csv")}
        self.incidents = read_csv(scenario / "incidents.csv")
        self.restores = read_csv(scenario / "restore-tests.csv")
        self.job_schedule = read_csv(scenario / "job-schedule.csv")
        self.matrix = {r["job_title"]: r for r in read_csv(scenario / "role-access-matrix.csv")}
        self.exceptions = read_csv(scenario / "exception-register.csv")
        self.requests = read_csv(scenario / "access-requests.csv")
        self.hr = {p["employee_id"]: p for p in read_csv(scenario / "hr-extract-2026-10-01.csv")}
        self.contractors = {
            c["contractor_id"]: c for c in read_csv(scenario / "contractors-2026-10-01.csv")
        }

    def period_deployments(self) -> list[dict]:
        return [d for d in self.deployments if in_period(d["at"])]

    def period_commits(self) -> list[dict]:
        return sorted(
            (c for c in self.commits.values() if in_period(c["committed"])),
            key=lambda c: c["committed"],
        )

    def author(self, commit: str) -> str:
        return user_of(self.commits[commit]["author_email"])

    def groups_of(self, username: str) -> set[str]:
        return {g for g, m in self.members.items() if username in m and g != "Domain Users"}

    def exception_for(self, account: str, clause_text: str) -> dict | None:
        for e in self.exceptions:
            if e["account"] == account and clause_text in e["policy_clause"]:
                return e
        return None

    def person(self, username: str) -> tuple[str, str]:
        """Status and description of a person, from HR or the contractor list."""
        employee_id = self.users.get(username, {}).get("employee_id", "")
        if employee_id in self.hr:
            p = self.hr[employee_id]
            if p["employment_status"] == "Leaver":
                return "Leaver", f"left on {p['end_date']}"
            return "Current", p["job_title"]
        if employee_id in self.contractors:
            c = self.contractors[employee_id]
            end = iso_date(c["contract_end"])
            if end and end < self.as_at:
                return "Contract ended", f"contract ended on {end}"
            return "Current", c["role"]
        return "Unknown", "not in the HR extract or contractor list"

    def code_access(self, username: str) -> tuple[str, list[str]]:
        rows = [r for r in self.repo_access if r["account"] == username]
        if not rows:
            return "none", []
        best = max(rows, key=lambda r: ACCESS_ORDER.index(r["access"]))
        return best["access"], [f"{r['access']} ({r['granted_through']})" for r in rows]

    def server_rights(self, username: str, host: str = APP_SERVER) -> list[dict]:
        return [r for r in self.hosts[host].sudo if r["account"] == username]


def test_server_sign_in(ev: Evidence) -> Test:
    t = Test(
        "AC-15",
        "Only authorised people can sign in to the servers",
        "Standard 5.1",
        "Design and operating effectiveness",
        "Nobody can sign in to a server except IT staff with their own domain account, and "
        "the emergency administrator account.",
        "Confirm the app server only lets members of GG-IT sign in with domain accounts. List "
        "every local account on each server that can sign in (a login shell and a usable "
        "password or SSH key). Each must be the emergency administrator account with an "
        "exception in the register, or an account that cannot sign in.",
        "Every local account on both Linux servers, and the domain sign in setting on the "
        "app server",
    )
    app = ev.hosts[APP_SERVER]
    allowed = re.search(r"^simple_allow_groups\s*=\s*(.+)$", app.sign_in, re.M)
    restricted = "access_provider = simple" in app.sign_in and allowed
    t.items.append(
        Item(
            f"{APP_SERVER}: domain sign in",
            "SSSD access settings",
            "Pass" if restricted else "Exception",
            f"Only members of {allowed.group(1).strip()} may sign in with a domain account "
            "(access_provider = simple)."
            if restricted
            else "Domain sign in is not restricted.",
        )
    )
    for host in sorted(ev.hosts):
        h = ev.hosts[host]
        for a in h.accounts:
            if a["can_sign_in"] != "Yes":
                continue
            detail = (
                f"uid {a['uid']}; password {a['password'].lower()}; "
                f"{a['ssh_keys']} SSH key(s); groups {a['groups'] or 'none'}"
            )
            exc = ev.exception_for(a["username"], "5.1")
            if exc:
                t.items.append(
                    Item(
                        f"{host}: {a['username']}",
                        detail,
                        "Pass",
                        f"Emergency administrator account covered by "
                        f"{exc['exception_id']}, review due {exc['review_date']}.",
                    )
                )
            else:
                t.items.append(
                    Item(
                        f"{host}: {a['username']}",
                        detail,
                        "Exception",
                        f'Local account "{a["description"]}" can sign in and is not in the '
                        f"exception register. Password last set {a['password_last_changed']}, and "
                        "neither the password nor the account ever expires.",
                    )
                )
    t.conclude(["F17"] if t.exceptions() else None)
    return t


def test_server_admin(ev: Evidence) -> Test:
    t = Test(
        "AC-16",
        "Administrator rights on the servers are limited to IT-Server-Admins",
        "Standard 5.2",
        "Operating effectiveness",
        "Full control of a server is held only by approved IT administrators, and every use "
        "of it asks for a password.",
        "For every sudo rule on each server, record who it covers and what it allows. Full "
        "rights are allowed only through IT-Server-Admins. Rights limited to the deployment "
        "tool are allowed for Change-Deployers. A rule granted to a person directly, or one "
        "that does not ask for a password, is an exception unless the exception register "
        "covers it.",
        "Every sudo rule on both Linux servers and every account it covers",
    )
    for host in sorted(ev.hosts):
        for r in ev.hosts[host].sudo:
            who = r["account"]
            item = f"{host}: {who} via {r['granted_to']}"
            detail = (
                f"{r['run_as']} {r['commands']}; password asked: "
                f"{'no' if r['no_password'] == 'Yes' else 'yes'}; "
                f"{r['file']} (modified {r['file_modified'][:10]})"
            )
            if who == "(no members)":
                t.items.append(Item(item, detail, "Not applicable", "The group has no members."))
            elif who == "root":
                t.items.append(Item(item, detail, "Pass", "The root account itself."))
            elif ev.exception_for(who, "5.2"):
                e = ev.exception_for(who, "5.2")
                t.items.append(Item(item, detail, "Pass", f"Covered by {e['exception_id']}."))
            elif r["granted_to"] == "%it-server-admins":
                t.items.append(
                    Item(item, detail, "Pass", "Granted through IT-Server-Admins, with a password.")
                )
            elif r["granted_to"] == "%change-deployers" and r["commands"] == DEPLOY_TOOL:
                t.items.append(
                    Item(item, detail, "Pass", "Limited to the deployment tool, with a password.")
                )
            else:
                problems = []
                if r["granted_to_type"] == "user":
                    problems.append("granted to the person directly")
                else:
                    problems.append(f"granted through {r['granted_to']}, not IT-Server-Admins")
                if r["no_password"] == "Yes":
                    problems.append("does not ask for a password")
                t.items.append(
                    Item(
                        item,
                        detail,
                        "Exception",
                        sentence(
                            f"Full administrator rights {', '.join(problems)}, "
                            "with no exception recorded"
                        ),
                    )
                )
    t.conclude(["F17"] if t.exceptions() else None)
    return t


def test_ssh(ev: Evidence) -> Test:
    t = Test(
        "AC-17",
        "SSH settings on the servers meet the Standard",
        "Standard 5.3",
        "Design",
        "Remote access to the servers resists password guessing and misuse of idle or "
        "forwarded sessions.",
        "Compare each setting in the table in Standard 5.3 with the effective SSH "
        "configuration reported by sshd -T, which includes defaults and every included file.",
        "Both Linux servers, eight settings each",
    )
    for host in sorted(ev.hosts):
        for key, required, ok in SSH_RULES:
            value = ev.hosts[host].sshd.get(key, "(not reported)")
            t.items.append(
                Item(
                    f"{host}: {key}",
                    f"Required: {required}",
                    "Pass" if ok(value) else "Exception",
                    f"Effective value: {value}.",
                )
            )
    t.conclude(["F18"] if t.exceptions() else None)
    return t


def test_user_access_sample(ev: Evidence) -> tuple[Test, dict]:
    population = sorted(
        u for u, r in ev.users.items() if r["enabled"] == "Yes" and r["employee_id"]
    )
    sample = select_sample(population)
    t = Test(
        "AC-18",
        "Each person's access matches their job (sample)",
        "Policy 3.1, 6.1, 6.3; Standard 3.8",
        "Operating effectiveness",
        "People hold only the access their job needs, across every system, and no one holds "
        "a combination of access that lets them complete a sensitive process alone.",
        "For each sampled person, gather their directory groups, their access to the code "
        "repository and their rights on the app server, and compare them with the role "
        "access matrix for their job. For anything beyond the matrix, look for an approved "
        "request and judge whether it is still needed and whether it combines duties that "
        "should be kept apart. Confirm the person is still employed.",
        f"{len(population)} enabled personal accounts in the directory at the end of the period",
        sample=f"{len(sample)} of {len(population)}, selected with random.Random({SEED}).sample()",
    )
    tags: set[str] = set()
    for username in sample:
        user = ev.users[username]
        status, about = ev.person(username)
        role = ev.matrix.get(user["job_title"], {})
        expected = set(filter(None, role.get("directory_groups", "").split(";")))
        actual = ev.groups_of(username)
        code, code_detail = ev.code_access(username)
        rights = ev.server_rights(username)
        full_admin = [r for r in rights if r["commands"] == "ALL"]
        problems = []
        if status != "Current":
            problems.append(
                f"no longer works for Northwind ({about}) but the account is "
                "enabled"
                + (f" and has {code} access to the code repository" if code != "none" else "")
            )
            tags.update({"Leaver": ["F1"], "Contract ended": ["F5"]}.get(status, []))
            if code != "none":
                tags.add("F16")
        for g in sorted(actual - expected):
            req = next(
                (
                    r
                    for r in ev.requests
                    if r["account"] == username
                    and r["access_requested"] == g
                    and r["status"] == "Approved"
                ),
                None,
            )
            why = (
                f"approved in {req['request_id']} by {req['approved_by']}"
                + (" (their own approval)" if req["approved_by"] == username else "")
                if req
                else "no approved request"
            )
            problems.append(f"{g} is not needed for the job of {user['job_title']} ({why})")
            tags.update(GROUP_FINDINGS.get(g, []))
        allowed_code = MATRIX_CODE_ACCESS.get(role.get("code_repository", "none"), "none")
        if ACCESS_ORDER.index(code) > ACCESS_ORDER.index(allowed_code):
            problems.append(
                f"code repository access is {code}, but the job needs "
                f"{role.get('code_repository', 'none')}"
            )
            tags.add("F12")
        if full_admin and role.get("server_rights") != "administrator":
            nopw = any(r["no_password"] == "Yes" for r in full_admin)
            problems.append(
                "has full administrator rights on the app server"
                + (" without a password" if nopw else "")
            )
            tags.add("F17")
        if {"Finance-Payments-Initiators", "Finance-Payments-Approvers"} <= actual:
            problems.append("can both create and approve supplier payments")
        if "Developers" in actual and "Change-Deployers" in actual:
            problems.append("writes code and can deploy it to production")
            tags.add("F12")
        held = ", ".join(sorted(actual)) or "none"
        detail = (
            f"{user['job_title']}, {status.lower()}. Directory: {held}. Code: "
            f"{', '.join(code_detail) or 'none'}. App server: "
            f"{'; '.join(r['commands'] + ' via ' + r['granted_to'] for r in rights) or 'none'}"
        )
        t.items.append(
            Item(
                username,
                detail,
                "Exception" if problems else "Pass",
                sentence("; ".join(problems))
                if problems
                else "Access matches the role access matrix.",
            )
        )
    t.conclude(sorted(tags, key=lambda f: int(f[1:])))
    return t, {"population": population, "sample": sample}


def test_deployment_tickets(ev: Evidence) -> Test:
    deps = ev.period_deployments()
    commits = ev.period_commits()
    deployed = {d["commit"] for d in deps}
    undeployed = [c["commit"][:7] for c in commits if c["commit"] not in deployed]
    off_main = [d["commit"][:7] for d in deps if d["commit"] not in ev.commits]
    t = Test(
        "CM-01",
        "Every deployment to production has a change ticket",
        "Standard 3.1",
        "Operating effectiveness",
        "Every change to production is recorded and can be traced to a request and approval.",
        "Match each deployment's ticket number to the service desk extract. A deployment with "
        "no ticket, or a ticket number that does not exist, is an exception.",
        f"All {len(deps)} deployments between 1 July and 30 September 2026. Completeness: "
        f"{len(commits)} commits were added to main in the period; "
        f"{len(commits) - len(undeployed)} were deployed in the period"
        + (f" ({', '.join(undeployed)} not yet deployed)" if undeployed else "")
        + ", and "
        + (
            "every deployed commit is on main"
            if not off_main
            else f"{len(off_main)} deployed commits are not on main"
        ),
    )
    for d in deps:
        ticket = ev.tickets.get(d["ticket"])
        subject = ev.commits.get(d["commit"], {}).get("subject", "")
        item = f"{d['at'][:16].replace('T', ' ')} {d['commit'][:7]}"
        if ticket:
            t.items.append(
                Item(
                    item,
                    f"{subject}; deployed by {d['by']}",
                    "Pass",
                    f"{ticket['ticket_id']}: {ticket['title']}.",
                )
            )
        else:
            t.items.append(
                Item(
                    item,
                    f"{subject}; deployed by {d['by']}",
                    "Exception",
                    f'Deployed with no change ticket (ticket recorded as "{d["ticket"]}").',
                )
            )
    t.conclude(["F11"] if t.exceptions() else None)
    return t


def test_code_review(ev: Evidence) -> Test:
    commits = ev.period_commits()
    t = Test(
        "CM-02",
        "Code reaches main only through an approved pull request",
        "Standard 3.4",
        "Operating effectiveness",
        "Every change to the finance application's code is checked by a second person before "
        "it can be deployed.",
        "Match each commit added to main to the merged pull request that added it. Confirm "
        "the pull request had an approving review that counts towards approval, from "
        "someone other than its author, before it was merged. A commit with no pull request, "
        "or a pull request merged without such an approval, is an exception.",
        f"All {len(commits)} commits added to main between 1 July and 30 September 2026",
    )
    for c in commits:
        author = user_of(c["author_email"])
        item = f"{c['commit'][:7]} {c['subject']}"
        pr = ev.pr_by_commit.get(c["commit"])
        if not pr:
            push = ev.pushes.get(c["commit"], {})
            t.items.append(
                Item(
                    item,
                    f"Author {author}",
                    "Exception",
                    f"Pushed directly to main by {push.get('account', 'unknown')} "
                    f"at {push.get('time', '')[:16].replace('T', ' ')}, with no pull "
                    "request or review.",
                )
            )
            continue
        number = int(pr["number"])
        approvals = [
            r
            for r in ev.reviews.get(number, [])
            if r["decision"] == "approved"
            and r["counts_towards_approval"] == "Yes"
            and r["reviewer"] != pr["author"]
            and r["submitted"] <= pr["merged_at"]
        ]
        detail = f"Pull request #{number} by {pr['author']}, merged by {pr['merged_by']}"
        if approvals:
            a = approvals[0]
            t.items.append(
                Item(
                    item,
                    detail,
                    "Pass",
                    f"Approved by {a['reviewer']} at "
                    f"{a['submitted'][:16].replace('T', ' ')}, before the merge.",
                )
            )
        else:
            t.items.append(
                Item(
                    item,
                    detail,
                    "Exception",
                    f"Merged by its author {pr['merged_by']} with no approving "
                    "review, although branch protection requires one approval.",
                )
            )
    t.conclude(["F11", "F15"] if t.exceptions() else None)
    return t


def test_deployer_not_author(ev: Evidence) -> Test:
    deps = ev.period_deployments()
    t = Test(
        "CM-03",
        "Nobody deploys their own change",
        "Standard 3.5; Policy 6.3",
        "Operating effectiveness",
        "No one can write a change and put it into production without another person being "
        "involved.",
        "Compare the person who ran each deployment with the author of the deployed commit. "
        "The same person is an exception.",
        f"All {len(deps)} deployments between 1 July and 30 September 2026",
    )
    for d in deps:
        author = ev.author(d["commit"])
        same = author == d["by"]
        t.items.append(
            Item(
                f"{d['at'][:16].replace('T', ' ')} {d['commit'][:7]}",
                f"{ev.commits[d['commit']]['subject']}; ticket {d['ticket']}",
                "Exception" if same else "Pass",
                f"Written and deployed by {author}."
                if same
                else f"Written by {author}, deployed by {d['by']}.",
            )
        )
    t.conclude(["F12"] if t.exceptions() else None)
    return t


def test_change_approval_sample(ev: Evidence) -> tuple[Test, dict]:
    deps = {f"{d['at']} {d['commit'][:7]}": d for d in ev.period_deployments()}
    sample = select_sample(list(deps))
    approvers = ev.members.get("Change-Approvers", set())
    t = Test(
        "CM-04",
        "Changes are approved and tested before deployment (sample)",
        "Standard 3.2, 3.3",
        "Operating effectiveness",
        "Only changes that the business has approved, and that have been tested, reach production.",
        "For each sampled deployment, inspect its change ticket and confirm: (a) the ticket "
        "exists and describes the change deployed; (b) it was approved by a member of "
        "Change-Approvers; (c) the approval came before the deployment; (d) testing is "
        "recorded on the ticket. Emergency changes are assessed against the emergency "
        "procedure in CM-05 instead of (c).",
        f"All {len(deps)} deployments between 1 July and 30 September 2026",
        sample=f"{len(sample)} of {len(deps)}, selected with random.Random({SEED}).sample()",
    )
    for key in sample:
        d = deps[key]
        subject = ev.commits[d["commit"]]["subject"]
        ticket = ev.tickets.get(d["ticket"])
        item = f"{d['at'][:16].replace('T', ' ')} {d['commit'][:7]}"
        if not ticket:
            t.items.append(
                Item(
                    item, subject, "Exception", "(a) No change ticket, so (b) to (d) cannot be met."
                )
            )
            continue
        problems, notes = [], []
        if ticket["title"] != subject:
            problems.append(
                f'(a) the ticket describes "{ticket["title"]}", not the deployed change'
            )
        if ticket["approved_by"] not in approvers:
            problems.append(
                f"(b) approved by {ticket['approved_by']}, who is not in Change-Approvers"
            )
        if ticket["type"] == "Emergency":
            notes.append("(c) emergency change, see CM-05")
        elif ticket["approved_at"] > d["at"]:
            late = (ts(ticket["approved_at"]).date() - ts(d["at"]).date()).days
            problems.append(
                f"(c) approved {ticket['approved_at'][:16].replace('T', ' ')}, "
                f"{late} day{'s' if late != 1 else ''} after deployment"
            )
        if not ticket["test_evidence"].strip():
            problems.append("(d) no testing recorded on the ticket")
        detail = (
            f"{ticket['ticket_id']} ({ticket['type']}): {subject}; approved by "
            f"{ticket['approved_by']} {ticket['approved_at'][:16].replace('T', ' ')}"
        )
        if problems:
            t.items.append(Item(item, detail, "Exception", sentence("; ".join(problems))))
        else:
            t.items.append(
                Item(
                    item,
                    detail,
                    "Pass",
                    sentence("(a) to (d) met" + (": " + "; ".join(notes) if notes else "")),
                )
            )
    t.conclude(["F13"] if t.exceptions() else None)
    return t, {"population": list(deps), "sample": sample}


def test_emergency(ev: Evidence) -> Test:
    emergencies = [
        t
        for t in ev.tickets.values()
        if t["type"] == "Emergency" and in_period(t["implemented_at"])
    ]
    t = Test(
        "CM-05",
        "Emergency changes follow the emergency procedure",
        "Standard 3.6",
        "Operating effectiveness",
        "Changes deployed in a hurry are still checked by a second person and approved and "
        "reviewed soon afterwards.",
        "For each emergency change, confirm a second person approved the code before it was "
        "deployed, the ticket was approved within 2 working days of deployment, and a post "
        "implementation review was recorded within 5 working days.",
        f"All {len(emergencies)} emergency changes in the period",
    )
    for tk in sorted(emergencies, key=lambda x: x["ticket_id"]):
        dep = next(d for d in ev.period_deployments() if d["ticket"] == tk["ticket_id"])
        deployed = ts(dep["at"])
        pr = ev.pr_by_commit.get(dep["commit"])
        reviewed = pr and any(
            r["decision"] == "approved"
            and r["reviewer"] != pr["author"]
            and r["submitted"] <= dep["at"]
            for r in ev.reviews.get(int(pr["number"]), [])
        )
        approval_days = working_days_between(deployed.date(), ts(tk["approved_at"]).date())
        pir = iso_date(tk["pir_completed"])
        pir_days = working_days_between(deployed.date(), pir) if pir else None
        problems = []
        if not reviewed:
            problems.append(
                "no second person reviewed the code before deployment ("
                + ("pushed directly to main" if not pr else "no approval")
                + ")"
            )
        if approval_days > 2:
            problems.append(
                f"approved {tk['approved_at'][:10]}, {approval_days} working days after deployment"
            )
        if pir_days is None:
            problems.append("no post implementation review recorded")
        elif pir_days > 5:
            problems.append(f"post implementation review {pir_days} working days after")
        detail = f"{tk['title']}; deployed {dep['at'][:16].replace('T', ' ')} by {dep['by']}"
        t.items.append(
            Item(
                tk["ticket_id"],
                detail,
                "Exception" if problems else "Pass",
                sentence("; ".join(problems))
                if problems
                else f"Reviewed by a second person in pull request #{pr['number']}, approved "
                f"{approval_days} working day(s) later, review completed {tk['pir_completed']}.",
            )
        )
    t.conclude(["F14"] if t.exceptions() else None)
    return t


def test_change_tools(ev: Evidence) -> Test:
    t = Test(
        "CM-06",
        "Branch protection and the deployment tool are set up as required",
        "Standard 3.7",
        "Design",
        "The tools enforce the change process, so it cannot be skipped by mistake or on purpose.",
        "Inspect the branch protection rule on main: one approval required, direct pushes "
        "blocked for everyone, administrators unable to override. Inspect the deployment "
        "tool: every deployment logged with commit, ticket and person, and whether it checks "
        "the ticket exists and is approved.",
        "The branch protection rule on main and the deployment tool",
    )
    rule = next((r for r in ev.protection if r["rule"] == "main"), None)
    if not rule:
        t.items.append(Item("main", "Branch protection", "Exception", "No protection rule."))
    else:
        since = f"Rule last changed {rule['updated'][:10]}"
        t.items.append(
            Item(
                "Branch protection: approvals",
                since,
                "Pass" if rule["required_approvals"] >= 1 else "Exception",
                f"{rule['required_approvals']} approval required before merging.",
            )
        )
        pushers = rule["accounts_allowed_to_push"]
        blocked = not rule["direct_push_allowed"]
        t.items.append(
            Item(
                "Branch protection: direct pushes",
                since,
                "Pass" if blocked else "Exception",
                "Direct pushes are blocked."
                if blocked
                else f"Direct pushes to main are allowed for {pushers or 'everyone'}, "
                "so changes can skip the pull request and review.",
            )
        )
        t.items.append(
            Item(
                "Branch protection: administrator override",
                since,
                "Pass" if rule["administrators_cannot_override"] else "Exception",
                "Administrators cannot override the rule."
                if rule["administrators_cannot_override"]
                else "Repository administrators (organisation owners and Gitea site "
                "administrators) can merge without the required approval.",
            )
        )
        t.items.append(
            Item(
                "Branch protection: new commits after approval",
                since,
                "Pass" if rule["approvals_dismissed_when_new_commits_pushed"] else "Exception",
                "Approvals are dismissed when new commits are pushed."
                if rule["approvals_dismissed_when_new_commits_pushed"]
                else "An approval stays valid if more commits are pushed after it, so "
                "unreviewed code can be merged under an earlier approval.",
            )
        )
    logs_all = all(k in ev.deploy_tool for k in ("commit=$COMMIT", "ticket=$TICKET", "by=$WHO"))
    t.items.append(
        Item(
            "Deployment tool: logging",
            DEPLOY_TOOL,
            "Pass" if logs_all else "Exception",
            "Every deployment is logged with its commit, ticket and the person who ran it."
            if logs_all
            else "Deployments are not fully logged.",
        )
    )
    checks_ticket = 'TICKET="${1:-none}"' not in ev.deploy_tool
    t.items.append(
        Item(
            "Deployment tool: ticket check",
            DEPLOY_TOOL,
            "Pass" if checks_ticket else "Exception",
            "The ticket is checked before deploying."
            if checks_ticket
            else 'The ticket is optional (it defaults to "none") and is never '
            "checked against the service desk, so anything can be deployed "
            "without an approved ticket.",
        )
    )
    t.conclude(["F15"] if t.exceptions() else None)
    return t


def test_change_access(ev: Evidence) -> Test:
    t = Test(
        "CM-07",
        "Only current developers can change code, and only non developers can deploy",
        "Standard 3.8",
        "Operating effectiveness",
        "Code and production can only be changed by people who should, and no one can both "
        "write code and deploy it.",
        "Match every account with write access or more to the code repository, and every "
        "account that can run the deployment tool, to the HR extract and contractor list. "
        "Compare each person's access with the role access matrix. A leaver or ended "
        "contractor with active access, a developer who can deploy, or a developer with "
        "administrator rights over the repository is an exception.",
        "Every Gitea account with write access or more, and every account that can run the "
        "deployment tool on the app server",
    )
    writers = {
        r["account"]
        for r in ev.repo_access
        if ACCESS_ORDER.index(r["access"]) >= ACCESS_ORDER.index("write")
    }
    deployers = {
        r["account"]
        for r in ev.hosts[APP_SERVER].sudo
        if r["commands"] in ("ALL", DEPLOY_TOOL) and r["account"] not in ("root", "(no members)")
    }
    authored = {}
    for c in ev.period_commits():
        authored[user_of(c["author_email"])] = authored.get(user_of(c["author_email"]), 0) + 1
    for account in sorted(writers | deployers):
        code, code_detail = ev.code_access(account)
        can_deploy = account in deployers
        gitea = ev.gitea_users.get(account, {})
        detail = (
            f"Code: {', '.join(code_detail) or 'none'}. Can deploy: "
            f"{'yes' if can_deploy else 'no'}. Commits in the period: "
            f"{authored.get(account, 0)}"
        )
        if account == "gitea-admin":
            t.items.append(
                Item(
                    account,
                    detail,
                    "Pass",
                    "Gitea's built in administrator account, last used "
                    f"{gitea.get('last_sign_in', '')[:10]}; see observation O2.",
                )
            )
            continue
        if account not in ev.users:
            exc = ev.exception_for(account, "5.2")
            t.items.append(
                Item(
                    account,
                    detail,
                    "Pass" if exc else "Exception",
                    f"Local emergency account covered by {exc['exception_id']}."
                    if exc
                    else "Local server account, not a named person, that "
                    "can deploy to production and is not in the exception "
                    "register.",
                )
            )
            continue
        status, about = ev.person(account)
        role = ev.matrix.get(ev.users[account]["job_title"], {})
        problems = []
        if status != "Current":
            last = gitea.get("last_sign_in", "")[:10]
            problems.append(
                f"{about} but the Gitea account is still active"
                + (f"; last signed in {last}" if last else "")
                + (
                    f"; wrote {authored[account]} commit(s) in the period"
                    if authored.get(account)
                    else ""
                )
            )
        allowed = MATRIX_CODE_ACCESS.get(role.get("code_repository", "none"), "none")
        if ACCESS_ORDER.index(code) > ACCESS_ORDER.index(allowed):
            problems.append(
                f"{code} access to the repository, more than the "
                f"{role.get('code_repository', 'none')} the job needs, so they "
                "can change branch protection and push to main"
            )
        if can_deploy and authored.get(account):
            problems.append(
                f"can deploy to production and wrote {authored[account]} of the "
                "commits deployed in the period"
            )
        t.items.append(
            Item(
                account,
                detail,
                "Exception" if problems else "Pass",
                sentence("; ".join(problems))
                if problems
                else "Access matches the role and the person is current.",
            )
        )
    t.conclude(["F12", "F16"] if t.exceptions() else None)
    return t


def backup_nights(ev: Evidence) -> dict[date, str]:
    nights = {}
    for line in ev.backup_log:
        m = re.match(r"^(\S+) backup (OK|FAILED)(.*)$", line)
        if m:
            nights.setdefault(ts(m.group(1)).date(), f"{m.group(2)}{m.group(3)}")
    return nights


def test_backups(ev: Evidence) -> Test:
    nights = backup_nights(ev)
    t = Test(
        "OP-01",
        "The finance database was backed up every night",
        "Standard 4.1",
        "Operating effectiveness",
        "A recent copy of the finance database is always available to restore from.",
        "For each night in the period, find the backup log entry. A failed run, or no entry "
        "at all, is an exception.",
        f"All {(PERIOD_END - PERIOD_START).days + 1} nights between 1 July and 30 September 2026",
    )
    d = PERIOD_START
    while d <= PERIOD_END:
        entry = nights.get(d)
        if entry and entry.startswith("OK"):
            size = re.search(r"bytes=(\d+)", entry)
            t.items.append(
                Item(
                    d.isoformat(),
                    "Backup at 01:30",
                    "Pass",
                    f"Completed ({size.group(1)} bytes)." if size else "Completed.",
                )
            )
        elif entry:
            err = re.search(r'error="([^"]+)"', entry)
            t.items.append(
                Item(
                    d.isoformat(),
                    "Backup at 01:30",
                    "Exception",
                    f"Failed: {err.group(1) if err else entry}.",
                )
            )
        else:
            t.items.append(
                Item(
                    d.isoformat(),
                    "Backup at 01:30",
                    "Exception",
                    "No log entry: the backup did not run.",
                )
            )
        d += timedelta(days=1)
    t.conclude(["F19"] if t.exceptions() else None)
    return t


def test_backup_follow_up(ev: Evidence) -> Test:
    nights = backup_nights(ev)
    failed = []
    d = PERIOD_START
    while d <= PERIOD_END:
        if not nights.get(d, "").startswith("OK"):
            failed.append(d)
        d += timedelta(days=1)
    t = Test(
        "OP-02",
        "Failed and missed backups were followed up",
        "Standard 4.2",
        "Operating effectiveness",
        "Backup problems are noticed and fixed before the business needs a restore.",
        "For each failed or missed night, look for an incident raised by the end of the next "
        "working day, and a later successful backup.",
        f"All {len(failed)} failed or missed nights from OP-01",
    )
    backup_incidents = [i for i in ev.incidents if i["system"] == "Backups"]
    for night in failed:
        deadline = working_days_after(night, 1)
        raised = [i for i in backup_incidents if night <= ts(i["raised_at"]).date() <= deadline]
        next_ok = next(
            (n for n in sorted(nights) if n > night and nights[n].startswith("OK")), None
        )
        detail = ("Missed" if night not in nights else "Failed") + f"; incident due by {deadline}"
        if raised:
            i = raised[0]
            t.items.append(
                Item(
                    night.isoformat(),
                    detail,
                    "Pass",
                    f"{i['incident_id']} raised {i['raised_at'][:10]} by "
                    f"{i['raised_by']}; next successful backup {next_ok}.",
                )
            )
        else:
            t.items.append(
                Item(
                    night.isoformat(),
                    detail,
                    "Exception",
                    f"No incident was raised. The next successful backup was on {next_ok}.",
                )
            )
    t.conclude(["F19"] if t.exceptions() else None)
    return t


def test_restores(ev: Evidence) -> Test:
    t = Test(
        "OP-03",
        "Restores were tested in the quarter",
        "Standard 4.3",
        "Operating effectiveness",
        "The backups are known to work, because a restore from them has been tried.",
        "Look for a restore test in the period in the restore test log, and inspect its result.",
        "The restore test log, for 1 July to 30 September 2026",
    )
    in_q3 = [r for r in ev.restores if PERIOD_START <= iso_date(r["performed_at"]) <= PERIOD_END]
    last = max(ev.restores, key=lambda r: r["performed_at"]) if ev.restores else None
    if in_q3:
        for r in in_q3:
            t.items.append(
                Item(
                    r["test_id"],
                    f"{r['performed_at']} by {r['performed_by']}",
                    "Pass" if r["result"] == "Success" else "Exception",
                    f"{r['result']}: {r['notes']}.",
                )
            )
    else:
        t.items.append(
            Item(
                "Q3 2026 restore test",
                "Restore test log",
                "Exception",
                "No restore was tested in the quarter. The last test was "
                + (
                    f"{last['test_id']} on {last['performed_at']}, "
                    f"{(PERIOD_END - iso_date(last['performed_at'])).days} days "
                    "before the end of the period."
                    if last
                    else "never."
                ),
            )
        )
    t.conclude(["F20"] if t.exceptions() else None)
    return t


def test_backup_design(ev: Evidence) -> Test:
    job = ev.backup_job
    t = Test(
        "OP-04",
        "The backup job is designed as required",
        "Standard 4.1, 4.2, 4.4",
        "Design",
        "The backup job can produce, check and keep the backups the business needs, and "
        "makes failures visible.",
        "Inspect the scheduled job and the backup program: it runs nightly, writes a log line "
        "for success and for failure, records a checksum for each file, and removes files "
        "older than 30 days. Note whether anything alerts a person when a run fails.",
        "The backup job and program on the app server",
    )
    checks = [
        (
            "Schedule",
            re.search(r"^30 1 \* \* \* root /usr/local/sbin/northwind-backup", job, re.M),
            "Runs every night at 01:30 UTC as root.",
            "Not scheduled nightly.",
        ),
        (
            "Logging",
            "backup OK" in job and "backup FAILED" in job,
            "Writes a log line for every run, successful or not.",
            "Not every run is logged.",
        ),
        (
            "Checksum",
            "sha256sum" in job,
            "Records a SHA-256 checksum for each backup file.",
            "No checksum is recorded.",
        ),
        (
            "Retention",
            "-mtime +30 -delete" in job,
            "Removes backups older than 30 days.",
            "Retention does not match the Standard.",
        ),
        (
            "Alerting",
            any(k in job for k in ("mail ", "sendmail", "notify", "curl ")),
            "Failures are sent to a person.",
            "Nothing tells anyone when a backup fails or does not run: the only record is a line "
            "in a log file on the same server. This is why the failures in OP-01 went unnoticed.",
        ),
    ]
    for name, ok, good, bad in checks:
        t.items.append(
            Item(name, "northwind-backup", "Pass" if ok else "Exception", good if ok else bad)
        )
    t.conclude(["F19"] if t.exceptions() else None)
    return t


def system_job(job: dict) -> bool:
    """Jobs installed with Ubuntu. Units under /usr/lib and /lib are installed by packages;
    dpkg records them under /lib, so its lookup misses the merged /usr/lib path."""
    return job["package"] != "not from a package" or job["source"].startswith(
        ("/usr/lib/", "/lib/")
    )


def test_scheduled_jobs(ev: Evidence) -> Test:
    t = Test(
        "OP-05",
        "Only approved jobs are scheduled on the servers",
        "Standard 4.5",
        "Operating effectiveness",
        "Nothing runs on a schedule on the servers that IT has not approved, and jobs that "
        "run as root cannot be changed by someone without root rights.",
        "Match every scheduled job not installed by an Ubuntu package to the job schedule. A "
        "job not on the schedule is an exception. For a job that runs as root, check the "
        "program it runs can only be changed by root.",
        "Every scheduled job on both Linux servers not installed with Ubuntu",
    )
    approved = {(j["server"], j["program"]): j for j in ev.job_schedule}
    for host in sorted(ev.hosts):
        jobs = [j for j in ev.hosts[host].jobs if not system_job(j)]
        system = len(ev.hosts[host].jobs) - len(jobs)
        if not jobs:
            t.items.append(
                Item(
                    f"{host}",
                    f"{system} jobs installed with Ubuntu",
                    "Not applicable",
                    "No other scheduled jobs.",
                )
            )
        for j in jobs:
            program = j["command"].split()[0]
            entry = approved.get((host, program))
            detail = (
                f"{j['schedule']} as {j['runs_as']}: {j['command']} ({j['source']}, "
                f"modified {j['file_modified'][:10]})"
            )
            problems = []
            if not entry:
                problems.append("not on the job schedule, so it was never approved")
            if j["runs_as"] == "root" and program.startswith("/home/"):
                owner = program.split("/")[2]
                problems.append(
                    f"runs as root a script in {owner}'s home folder, which "
                    f"{owner} can change, so it gives {owner} a way to run any "
                    "command as root"
                )
            if problems:
                t.items.append(
                    Item(
                        f"{host}: {Path(j['source']).name}",
                        detail,
                        "Exception",
                        sentence("; ".join(problems)),
                    )
                )
            else:
                t.items.append(
                    Item(
                        f"{host}: {Path(j['source']).name}",
                        detail,
                        "Pass",
                        f"{entry['job_id']}, owner {entry['owner']}, approved by "
                        f"{entry['approved_by']} on {entry['approved_date']}.",
                    )
                )
    t.conclude(["F21"] if t.exceptions() else None)
    return t


def test_time(ev: Evidence) -> Test:
    t = Test(
        "OP-06",
        "Server clocks are synchronised",
        "Standard 4.6",
        "Operating effectiveness",
        "Every server keeps the correct time, so logs can be relied on and Kerberos sign in works.",
        "Confirm each server synchronises with a time source and was within 5 seconds of it "
        "when the evidence was collected. Consider anything seen during fieldwork that shows "
        "the clock was wrong at other times.",
        "Both Linux servers",
    )
    for host in sorted(ev.hosts):
        text = ev.hosts[host].time_sync
        ref = re.search(r"Reference ID\s*:\s*\S+ \(([^)]+)\)", text)
        off = re.search(r"System time\s*:\s*([\d.]+) seconds (slow|fast)", text)
        synced = bool(ref and off and float(off.group(1)) <= 5 and ref.group(1) != "0.0.0.0")
        detail = (
            f"Source {ref.group(1) if ref else 'none'}; "
            f"{off.group(1) + ' seconds ' + off.group(2) if off else 'offset unknown'} "
            f"at {ev.hosts[host].as_at:%Y-%m-%d %H:%M} UTC"
        )
        seen = CLOCK_OBSERVATIONS.get(host, [])
        if synced and not seen:
            t.items.append(Item(host, detail, "Pass", "Synchronised and within 5 seconds."))
        elif synced:
            t.items.append(
                Item(
                    host,
                    detail,
                    "Exception",
                    "Synchronised when the evidence was collected, but found badly "
                    "wrong twice during fieldwork: " + "; ".join(seen) + ".",
                )
            )
        else:
            t.items.append(Item(host, detail, "Exception", "Not synchronised within 5 seconds."))
    t.conclude(["F22"] if t.exceptions() else None)
    return t


def test_patching(ev: Evidence) -> Test:
    t = Test(
        "OP-07",
        "Security updates are installed",
        "Standard 4.7",
        "Design and operating effectiveness",
        "Known security weaknesses in the servers' software are fixed promptly.",
        "Confirm automatic security updates are switched on. List security updates still "
        "waiting to be installed when the evidence was collected. Any security update "
        "waiting for more than 14 days is an exception.",
        "Both Linux servers",
    )
    for host in sorted(ev.hosts):
        text = ev.hosts[host].patching
        auto = 'APT::Periodic::Unattended-Upgrade "1"' in text and re.search(
            r"# unattended-upgrades service\n\s*enabled", text
        )
        pending = int(re.search(r"from the security archive: (\d+)", text).group(1))
        refreshed = re.search(r"refreshed \(UTC\): (\S+)", text).group(1)
        ok = auto and pending == 0
        t.items.append(
            Item(
                host,
                f"Package lists refreshed {refreshed[:16].replace('T', ' ')}",
                "Pass" if ok else "Exception",
                (
                    "Automatic security updates are on"
                    if auto
                    else "Automatic security updates are off"
                )
                + f"; {pending} security update(s) waiting.",
            )
        )
    t.conclude(["F23"] if t.exceptions() else None)
    return t


ALL_TESTS = [
    test_server_sign_in,
    test_server_admin,
    test_ssh,
    test_user_access_sample,
    test_deployment_tickets,
    test_code_review,
    test_deployer_not_author,
    test_change_approval_sample,
    test_emergency,
    test_change_tools,
    test_change_access,
    test_backups,
    test_backup_follow_up,
    test_restores,
    test_backup_design,
    test_scheduled_jobs,
    test_time,
    test_patching,
]

FRAMEWORKS = {
    "AC-15": (
        "A.5.15 Access control; A.5.16 Identity management",
        "5.1 Inventory of accounts; 6.7 Centralise access control",
    ),
    "AC-16": (
        "A.8.2 Privileged access rights",
        "5.4 Restrict administrator privileges; 6.8 Role based access",
    ),
    "AC-17": (
        "A.8.9 Configuration management; A.8.5 Secure authentication",
        "4.1 Secure configuration process",
    ),
    "AC-18": ("A.5.18 Access rights; A.5.3 Segregation of duties", "6.8 Role based access"),
    "CM-01": ("A.8.32 Change management", "16.1 Secure application development process"),
    "CM-02": (
        "A.8.32 Change management; A.8.4 Access to source code",
        "16.1 Secure application development process",
    ),
    "CM-03": (
        "A.5.3 Segregation of duties; A.8.31 Separation of environments",
        "16.1 Secure application development process",
    ),
    "CM-04": (
        "A.8.32 Change management; A.8.29 Security testing",
        "16.1 Secure application development process",
    ),
    "CM-05": ("A.8.32 Change management", "16.1 Secure application development process"),
    "CM-06": (
        "A.8.32 Change management; A.8.9 Configuration management",
        "16.1 Secure application development process; 4.1 Secure configuration process",
    ),
    "CM-07": (
        "A.8.4 Access to source code; A.5.18 Access rights",
        "6.2 Access revoking process; 6.8 Role based access",
    ),
    "OP-01": ("A.8.13 Information backup", "11.2 Automated backups"),
    "OP-02": ("A.8.13 Information backup; A.8.16 Monitoring activities", "11.2 Automated backups"),
    "OP-03": ("A.8.13 Information backup", "11.5 Test data recovery"),
    "OP-04": ("A.8.13 Information backup", "11.1 Data recovery process"),
    "OP-05": (
        "A.8.9 Configuration management; A.8.19 Software on operational systems",
        "4.1 Secure configuration process",
    ),
    "OP-06": ("A.8.17 Clock synchronisation", "8.4 Standardise time synchronisation"),
    "OP-07": (
        "A.8.8 Management of technical vulnerabilities",
        "7.3 Automated operating system patch management",
    ),
}


def run_all(
    app: Path, hosts: list[Path], directory: Path, scenario: Path
) -> tuple[Evidence, list[Test], dict]:
    ev = Evidence(app, hosts, directory, scenario)
    tests, samples = [], {}
    for fn in ALL_TESTS:
        result = fn(ev)
        if isinstance(result, tuple):
            result, samples[result.test_id] = result
        result.iso27001, result.cis_controls = FRAMEWORKS[result.test_id]
        tests.append(result)
    return ev, tests, samples


def relative(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--host", required=True, type=Path, action="append")
    parser.add_argument(
        "--directory",
        required=True,
        type=Path,
        help="directory extraction for the end of the period",
    )
    parser.add_argument("--scenario", default=ROOT / "scenario", type=Path)
    parser.add_argument("--out", default=ROOT / "workpapers", type=Path)
    args = parser.parse_args()

    for folder in [args.app, *args.host, args.directory]:
        problems = verify_evidence(folder)
        if problems:
            print(f"{folder} failed its integrity check, so it cannot be relied on:")
            print("\n".join(f"  {p}" for p in problems))
            return 1

    ev, tests, samples = run_all(args.app, args.host, args.directory, args.scenario)
    args.out.mkdir(parents=True, exist_ok=True)
    from workpaper import build_change_ops_workpaper

    build_change_ops_workpaper(
        ev, tests, samples, args.out / "change-operations-workpaper.xlsx", SEED
    )
    (args.out / "change-operations-results.json").write_text(
        json.dumps(
            {
                "evidence": {
                    "app": relative(args.app),
                    "hosts": [relative(h) for h in args.host],
                    "directory": relative(args.directory),
                },
                "as_at": ev.as_at.isoformat(),
                "period": [PERIOD_START.isoformat(), PERIOD_END.isoformat()],
                "seed": SEED,
                "samples": samples,
                "tests": [asdict(t) for t in tests],
            },
            indent=2,
        )
        + "\n"
    )

    for t in tests:
        print(f"{t.test_id}  {t.title:<72} {t.conclusion}")
        for i in t.exceptions():
            print(f"         - {i.item}: {i.comment}")
    print(f"\nWorkpaper: {args.out / 'change-operations-workpaper.xlsx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
