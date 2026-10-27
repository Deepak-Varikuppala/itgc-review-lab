#!/usr/bin/env python3
"""Generates Northwind's Q3 2026 change and backup history for the app server lab.

The app server is built in October, but the review covers 1 July to 30 September 2026,
so the history of that quarter has to be created when the lab is built. This script
defines that history in one place and writes:

    lab/app/data/changes.json       code changes and deployments, used by install.sh
    lab/app/data/backup-history.log the backup job's log for the quarter
    scenario/change-tickets.csv     the service desk's change records
    scenario/incidents.csv          the service desk's incident records
    scenario/restore-tests.csv      the record of backup restore tests

The history is deliberately imperfect: some changes break the change management and
operations controls, as a real quarter might. It is deterministic, so running it again
produces identical files.

    python3 lab/app/history.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "lab" / "app" / "data"
SCENARIO = ROOT / "scenario"
START, END = date(2026, 7, 1), date(2026, 9, 30)
BANK_HOLIDAYS = {date(2026, 8, 31)}

NORMAL_TITLES = [
    "Add supplier VAT number validation",
    "Show payment due date on the payments list",
    "Reject payments to suppliers with no bank details",
    "Log every payment approval with the approver's username",
    "Round payment amounts to two decimal places on import",
    "Add search by supplier name",
    "Upgrade the HTTP server dependency",
    "Paginate the payments list",
    "Add a health check endpoint for monitoring",
    "Store the time each payment was approved",
    "Warn when a supplier's bank details change",
    "Export approved payments to the bank file format",
    "Rotate application logs daily",
    "Add currency code to each payment",
    "Validate sort codes before saving supplier details",
    "Show who created each payment",
    "Fix timezone on payment dates",
    "Add a daily total of approved payments",
    "Reduce database lock time during imports",
    "Add unit tests for payment validation",
    "Highlight payments over the approval limit",
    "Mask bank account numbers on screen",
    "Read configuration from environment variables",
    "Add supplier status (active or blocked)",
    "Block payments to blocked suppliers",
    "Record the IP address of each approval",
    "Improve error message for duplicate invoices",
    "Detect duplicate invoice numbers",
    "Add a weekly supplier report",
    "Move the database path to configuration",
    "Tidy up unused payment fields",
    "Add a dry run option to the bank export",
    "Speed up the supplier lookup",
    "Show the last login time on the admin page",
    "Prepare quarter end payment summary",
]


# Changes before the audit period: (deployment date, title, author, ticket number).
# They are part of the repository's history but outside the period under review, so
# the service desk extract given to the auditor does not include their tickets.
BEFORE_PERIOD = [
    (date(2026, 1, 15), "Add supplier list page", "ryan.patel", 4),
    (date(2026, 1, 29), "Add payments table", "aisha.khan", 11),
    (date(2026, 2, 12), "Add supplier bank details form", "leo.martin", 19),
    (date(2026, 2, 26), "Add approval status to payments", "ryan.patel", 27),
    (date(2026, 3, 12), "Add sort code to suppliers", "leo.martin", 34),
    (date(2026, 3, 26), "Block negative payment amounts", "aisha.khan", 42),
    (date(2026, 4, 16), "Add invoice number to payments", "ryan.patel", 53),
    (date(2026, 4, 30), "Add basic request logging", "leo.martin", 61),
    (date(2026, 5, 14), "Open the database read only for the payments page", "aisha.khan", 70),
    (date(2026, 5, 28), "Move page templates into one module", "leo.martin", 79),
    (date(2026, 6, 18), "Prepare for Q3 payment runs", "ryan.patel", 88),
]
INITIAL_COMMIT = {
    "title": "Initial version of the payments app",
    "author": "ryan.patel",
    "authored_at": "2025-11-03T14:20:00+00:00",
}


def branch_name(title: str) -> str:
    words = "".join(ch if ch.isalnum() or ch == " " else "" for ch in title.lower()).split()
    return "feature/" + "-".join(words[:4])


def before_period_changes() -> list[dict]:
    changes = []
    for pr, (d, title, author, ticket) in enumerate(BEFORE_PERIOD, start=1):
        other = "ryan.patel" if author != "ryan.patel" else "aisha.khan"
        changes.append(
            {
                "id": f"CHG-2026-{ticket:04d}",
                "kind": "pull_request",
                "pr": pr,
                "title": title,
                "branch": branch_name(title),
                "author": author,
                "authored_at": at(previous_working_day(previous_working_day(d)), 10, 20),
                "reviewer": other,
                "merged_by": other,
                "merged_at": at(previous_working_day(d), 15, 40),
                "deployed_at": at(d, 18, 20),
                "deployed_by": "aisha.khan" if author != "aisha.khan" else "ryan.patel",
                "ticket": None,
                "before_period": True,
            }
        )
    return changes


def deployment_days() -> list[date]:
    """Mondays, Tuesdays and Thursdays in Q3, except the bank holiday and three quiet days."""
    days, d = [], START
    quiet = {date(2026, 7, 6), date(2026, 8, 3), date(2026, 9, 7)}
    while d <= END:
        if d.weekday() in (0, 1, 3) and d not in BANK_HOLIDAYS and d not in quiet:
            days.append(d)
        d += timedelta(days=1)
    return days


def at(d: date, hh: int, mm: int) -> str:
    return datetime.combine(d, time(hh, mm), tzinfo=timezone.utc).isoformat()


def previous_working_day(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5 or d in BANK_HOLIDAYS:
        d -= timedelta(days=1)
    return d


def build_changes() -> list[dict]:
    days = deployment_days()
    assert len(days) == len(NORMAL_TITLES) == 35, len(days)

    # Deliberate control failures, keyed by deployment date.
    self_deploy = {date(2026, 7, 14), date(2026, 8, 6), date(2026, 9, 1), date(2026, 9, 22)}
    approved_late = {date(2026, 7, 23): 1, date(2026, 9, 15): 2}  # days after deployment
    no_test_evidence = {date(2026, 8, 25), date(2026, 9, 8)}
    unreviewed_merge = {date(2026, 7, 30)}
    contractor_change = date(2026, 8, 13)

    changes = []
    ticket = 101
    for i, (d, title) in enumerate(zip(days, NORMAL_TITLES, strict=True)):
        author = "aisha.khan" if i % 3 == 2 else "ryan.patel"
        if d == contractor_change:
            author = "leo.martin"
        reviewer = "ryan.patel" if author == "aisha.khan" else "aisha.khan"
        if author == "leo.martin":
            reviewer = "ryan.patel"
        deployer = "ryan.patel" if author == "aisha.khan" else "aisha.khan"
        if d in self_deploy:
            author, reviewer, deployer = "ryan.patel", "aisha.khan", "ryan.patel"
        deployed = at(d, 18, 10 + (i % 4) * 10)
        approved_day = previous_working_day(d)
        if d in approved_late:
            approved_day = d + timedelta(days=approved_late[d])
        changes.append(
            {
                "id": f"CHG-2026-{ticket:04d}",
                "kind": "pull_request",
                "title": title,
                "branch": branch_name(title),
                "author": author,
                "authored_at": at(previous_working_day(previous_working_day(d)), 10, 15 + i % 40),
                "reviewer": None if d in unreviewed_merge else reviewer,
                "merged_by": author if d in unreviewed_merge else reviewer,
                "merged_at": at(previous_working_day(d), 15, 30 + i % 25),
                "deployed_at": deployed,
                "deployed_by": deployer,
                "ticket": {
                    "type": "Normal",
                    "requested_by": author,
                    "approved_by": "james.carter",
                    "approved_at": at(approved_day, 11 if d not in approved_late else 9, 0),
                    "test_evidence": ""
                    if d in no_test_evidence
                    else "Unit tests passed in pull request #{pr}; checked in test copy by "
                    + reviewer,
                    "implemented_by": deployer,
                    "implemented_at": deployed,
                    "pir_completed": "",
                    "status": "Closed",
                },
            }
        )
        ticket += 1

    # Two emergency changes. The first follows the emergency procedure; the second does not.
    changes.append(
        {
            "id": f"CHG-2026-{ticket:04d}",
            "kind": "pull_request",
            "title": "Emergency: bank rejected payment file, fix field order",
            "branch": "hotfix/bank-file-field-order",
            "author": "ryan.patel",
            "authored_at": at(date(2026, 8, 19), 21, 5),
            "reviewer": "aisha.khan",
            "merged_by": "aisha.khan",
            "merged_at": at(date(2026, 8, 19), 22, 20),
            "deployed_at": at(date(2026, 8, 19), 22, 40),
            "deployed_by": "aisha.khan",
            "ticket": {
                "type": "Emergency",
                "requested_by": "ryan.patel",
                "approved_by": "james.carter",
                "approved_at": at(date(2026, 8, 20), 9, 30),
                "test_evidence": "Payment file validated against the bank's test service",
                "implemented_by": "aisha.khan",
                "implemented_at": at(date(2026, 8, 19), 22, 40),
                "pir_completed": "2026-08-21",
                "status": "Closed",
            },
        }
    )
    ticket += 1
    changes.append(
        {
            "id": f"CHG-2026-{ticket:04d}",
            "kind": "direct",
            "title": "Emergency: approvals page timing out",
            "branch": "main",
            "author": "ryan.patel",
            "authored_at": at(date(2026, 9, 23), 20, 50),
            "deployed_at": at(date(2026, 9, 23), 21, 15),
            "deployed_by": "ryan.patel",
            "ticket": {
                "type": "Emergency",
                "requested_by": "ryan.patel",
                "approved_by": "james.carter",
                "approved_at": at(date(2026, 10, 6), 10, 0),
                "test_evidence": "",
                "implemented_by": "ryan.patel",
                "implemented_at": at(date(2026, 9, 23), 21, 15),
                "pir_completed": "",
                "status": "Closed",
            },
        }
    )

    # Three changes pushed straight to main and deployed with no ticket at all.
    for d, title in [
        (date(2026, 7, 17), "Quick fix: payment list sort order"),
        (date(2026, 8, 21), "Quick fix: typo on approval screen"),
        (date(2026, 9, 11), "Quick fix: increase export timeout"),
    ]:
        changes.append(
            {
                "id": None,
                "kind": "direct",
                "title": title,
                "branch": "main",
                "author": "ryan.patel",
                "authored_at": at(d, 16, 40),
                "deployed_at": at(d, 17, 5),
                "deployed_by": "ryan.patel",
                "ticket": None,
            }
        )

    # Gitea numbers pull requests in the order they are opened, and each is opened and
    # merged in turn, so numbers follow the merge order. Numbers 1 to 11 are before Q3.
    changes.sort(key=lambda c: c["deployed_at"])
    prs = sorted((c for c in changes if c["kind"] == "pull_request"), key=lambda c: c["merged_at"])
    for number, c in enumerate(prs, start=len(BEFORE_PERIOD) + 1):
        c["pr"] = number
        c["ticket"]["test_evidence"] = c["ticket"]["test_evidence"].replace("{pr}", str(number))
    return before_period_changes() + changes


def backup_log() -> list[str]:
    """The nightly backup job's log. It runs at 01:30 UTC and backs up the finance database."""
    failures = {
        date(2026, 8, 8): "No space left on device",
        date(2026, 8, 9): "No space left on device",
        date(2026, 8, 10): "No space left on device",
        date(2026, 8, 11): "No space left on device",
        date(2026, 9, 20): "database is locked",
    }
    did_not_run = {date(2026, 7, 19)}
    lines, d, size = [], START, 1_880
    while d <= END:
        if d in did_not_run:
            d += timedelta(days=1)
            continue
        stamp = at(d, 1, 30)
        name = f"finance-{d:%Y%m%d}.db.gz"
        if d in failures:
            lines.append(f'{stamp} backup FAILED file={name} error="{failures[d]}"')
        else:
            size += 1 + d.toordinal() % 3
            digest = hashlib.sha256(f"northwind-finance-{d}".encode()).hexdigest()
            lines.append(f"{stamp} backup OK file={name} bytes={size} sha256={digest}")
        d += timedelta(days=1)
    return lines


def tickets(changes: list[dict]) -> list[list[str]]:
    rows = []
    for c in changes:
        t = c["ticket"]
        if not t:
            continue
        rows.append(
            [
                c["id"],
                c["title"],
                t["type"],
                t["requested_by"],
                t["approved_by"],
                t["approved_at"],
                t["test_evidence"],
                t["implemented_by"],
                t["implemented_at"],
                t["pir_completed"],
                t["status"],
            ]
        )
    return sorted(rows)


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    changes = build_changes()
    (DATA / "changes.json").write_text(
        json.dumps({"initial_commit": INITIAL_COMMIT, "changes": changes}, indent=2) + "\n"
    )
    (DATA / "backup-history.log").write_text("\n".join(backup_log()) + "\n")

    write_csv(
        SCENARIO / "change-tickets.csv",
        [
            "ticket_id",
            "title",
            "type",
            "requested_by",
            "approved_by",
            "approved_at",
            "test_evidence",
            "implemented_by",
            "implemented_at",
            "pir_completed",
            "status",
        ],
        tickets(changes),
    )
    write_csv(
        SCENARIO / "incidents.csv",
        ["incident_id", "raised_at", "raised_by", "system", "summary", "resolved_at", "status"],
        [
            [
                "INC-2026-0158",
                "2026-07-08T09:12:00+00:00",
                "sophie.turner",
                "Email",
                "Cannot open attachment from supplier",
                "2026-07-08T10:02:00+00:00",
                "Closed",
            ],
            [
                "INC-2026-0171",
                "2026-08-20T08:05:00+00:00",
                "daniel.hughes",
                "Finance app",
                "Bank rejected last night's payment file",
                "2026-08-20T09:40:00+00:00",
                "Closed",
            ],
            [
                "INC-2026-0193",
                "2026-09-21T08:30:00+00:00",
                "aisha.khan",
                "Backups",
                "Nightly finance backup failed: database is locked",
                "2026-09-21T11:15:00+00:00",
                "Closed",
            ],
        ],
    )
    write_csv(
        SCENARIO / "restore-tests.csv",
        ["test_id", "performed_at", "performed_by", "backup_file", "result", "notes"],
        [
            [
                "RT-2026-01",
                "2026-01-12",
                "aisha.khan",
                "finance-20260111.db.gz",
                "Success",
                "Restored to test server; row counts matched",
            ],
            [
                "RT-2026-02",
                "2026-04-14",
                "aisha.khan",
                "finance-20260413.db.gz",
                "Success",
                "Restored to test server; row counts matched",
            ],
        ],
    )
    in_period = [c for c in changes if not c.get("before_period")]
    print(
        f"{len(changes)} deployments ({len(in_period)} in the period), "
        f"{sum(1 for c in changes if c['ticket'])} change tickets, "
        f"{len(backup_log())} backup log lines"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
