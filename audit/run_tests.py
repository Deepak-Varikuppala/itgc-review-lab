#!/usr/bin/env python3
"""Run the Northwind logical access ITGC tests against an evidence folder.

Each test compares the directory evidence with the company's own records (HR extract,
contractor list, access requests, exception register) and its access control policy.
Every item in each population is tested, so there is no sampling risk; each item's
result and the reason for it are recorded so the work can be re-performed.

    python3 audit/run_tests.py --evidence evidence/directory-<timestamp>

Outputs workpapers/logical-access-workpaper.xlsx and workpapers/results.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIOD_START = date(2026, 7, 1)
PERIOD_END = date(2026, 9, 30)

# England and Wales bank holidays, used to count working days.
BANK_HOLIDAYS_2026 = {
    date(2026, 1, 1),
    date(2026, 4, 3),
    date(2026, 4, 6),
    date(2026, 5, 4),
    date(2026, 5, 25),
    date(2026, 8, 31),
    date(2026, 12, 25),
    date(2026, 12, 28),
}

SENSITIVE_GROUPS = [
    "Domain Admins",
    "IT-Server-Admins",
    "Finance-Payments-Initiators",
    "Finance-Payments-Approvers",
    "Change-Approvers",
    "Change-Deployers",
]
BUILT_IN = {"Administrator", "Guest", "krbtgt"}


def working_days_after(start: date, days: int) -> date:
    current, added = start, 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in BANK_HOLIDAYS_2026:
            added += 1
    return current


def sentence(text: str) -> str:
    """Capitalise the first letter only, leaving names and group names as they are."""
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def iso_date(value: str) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def account_type(username: str, employee_id: str = "") -> str:
    """Classify an account. Personal accounts carry an HR employee or contractor ID."""
    if username in BUILT_IN:
        return "Built in"
    if username.startswith("adm."):
        return "Administrator"
    if username.startswith("svc-"):
        return "Service"
    return "Personal" if employee_id else "Generic"


@dataclass
class Item:
    item: str
    detail: str
    result: str  # Pass, Exception, Not applicable
    comment: str


@dataclass
class Test:
    test_id: str
    title: str
    policy_ref: str
    test_type: str  # Design, Operating effectiveness
    objective: str
    procedure: str
    population: str
    items: list[Item] = field(default_factory=list)
    conclusion: str = ""
    findings: list[str] = field(default_factory=list)
    iso27001: str = ""
    cis_controls: str = ""

    def exceptions(self) -> list[Item]:
        return [i for i in self.items if i.result == "Exception"]

    def conclude(self, findings: list[str] | None = None, untested: str | None = None) -> None:
        if untested:
            self.conclusion = f"Not tested: {untested}"
        elif self.exceptions():
            n, total = (
                len(self.exceptions()),
                len([i for i in self.items if i.result != "Not applicable"]),
            )
            kind = (
                "Design deficiency" if self.test_type == "Design" else "Not operating effectively"
            )
            self.conclusion = f"{kind} ({n} exception{'s' if n > 1 else ''} in {total} tested)"
        else:
            self.conclusion = "Effective (no exceptions)"
        self.findings = findings or []


class Evidence:
    def __init__(self, evidence_dir: Path, scenario_dir: Path):
        self.dir = evidence_dir
        self.users = {u["username"]: u for u in read_csv(evidence_dir / "users.csv")}
        self.members: dict[str, set[str]] = {}
        for row in read_csv(evidence_dir / "group-members.csv"):
            self.members.setdefault(row["group"], set()).add(row["member"])
        self.policy = {}
        for line in (evidence_dir / "password-policy.txt").read_text().splitlines():
            key, sep, value = line.partition(":")
            if sep:
                self.policy[key.strip()] = value.strip()
        log = (evidence_dir / "extraction-log.txt").read_text()
        stamp = next(line for line in log.splitlines() if line.startswith("Extracted at"))
        self.as_at = datetime.fromisoformat(stamp.split(":", 1)[1].strip()).date()

        self.hr = read_csv(scenario_dir / "hr-extract-2026-10-01.csv")
        self.contractors = read_csv(scenario_dir / "contractors-2026-10-01.csv")
        self.requests = read_csv(scenario_dir / "access-requests.csv")
        self.exceptions = read_csv(scenario_dir / "exception-register.csv")
        self.by_employee_id = {u["employee_id"]: u for u in self.users.values() if u["employee_id"]}

    def groups_of(self, username: str) -> set[str]:
        """Groups an account was added to. Domain Users, which every account gets
        automatically, is left out."""
        return {g for g, m in self.members.items() if username in m and g != "Domain Users"}

    def kind(self, username: str) -> str:
        return account_type(username, self.users.get(username, {}).get("employee_id", ""))

    def approved_request(self, username: str, group: str) -> dict | None:
        for r in self.requests:
            if (
                r["account"] == username
                and r["access_requested"] == group
                and r["status"] == "Approved"
            ):
                return r
        return None

    def has_exception(self, username: str, clause: str) -> dict | None:
        for e in self.exceptions:
            if e["account"] == username and e["policy_clause"] == clause:
                return e
        return None


def test_leavers(ev: Evidence) -> Test:
    t = Test(
        "AC-01",
        "Leavers' accounts are disabled promptly",
        "3.3",
        "Operating effectiveness",
        "Former employees cannot use their access after they leave.",
        "From the HR extract, select every employee with a leaving date in the audit period. "
        "Find each one's account by employee ID. Check the account is disabled, removed from "
        "all groups and moved to the Leavers area, and compare any last logon date with the "
        "leaving date. Deadline: 1 working day after the leaving date.",
        "All employees who left between 1 July and 30 September 2026",
    )
    for p in ev.hr:
        end = iso_date(p["end_date"])
        if not end or not (PERIOD_START <= end <= PERIOD_END):
            continue
        name = f"{p['first_name']} {p['last_name']} ({p['employee_id']})"
        deadline = working_days_after(end, 1)
        acct = ev.by_employee_id.get(p["employee_id"])
        if not acct:
            t.items.append(Item(name, f"Left {end}", "Pass", "No account found in the directory."))
            continue
        problems = []
        if acct["enabled"] == "Yes":
            problems.append(
                f"account still enabled at {ev.as_at}, "
                f"{(ev.as_at - deadline).days} days after the {deadline} deadline"
            )
        if acct["groups"]:
            problems.append(f"still a member of {acct['groups'].replace(';', ', ')}")
        if not acct["location"].startswith("Leavers"):
            problems.append(f"not moved to Leavers (located in {acct['location']})")
        last = iso_date(acct["last_logon"])
        if last and last > end:
            problems.append(f"account signed in on {last}, after the leaving date")
        t.items.append(
            Item(
                f"{acct['username']}: {name}",
                f"Left {end}; deadline {deadline}",
                "Exception" if problems else "Pass",
                sentence("; ".join(problems))
                if problems
                else "Disabled, no group memberships, in Leavers.",
            )
        )
    t.conclude(["F1"] if t.exceptions() else None)
    return t


def test_movers(ev: Evidence) -> Test:
    t = Test(
        "AC-02",
        "Access is updated when staff change role",
        "3.2",
        "Operating effectiveness",
        "People do not keep access from a previous role that they no longer need.",
        "From the HR extract, select every employee who transferred department in the audit "
        "period. Compare their current group memberships with their new department. Any "
        "group belonging to the previous department still held 5 working days after the "
        "transfer is an exception.",
        "All transfers between 1 July and 30 September 2026",
    )
    for p in ev.hr:
        changed = iso_date(p["last_change_date"])
        if (
            not changed
            or not (PERIOD_START <= changed <= PERIOD_END)
            or not p["last_change"].startswith("Transferred from")
        ):
            continue
        acct = ev.by_employee_id[p["employee_id"]]
        old_dept = p["last_change"].split("from ", 1)[1].split(" (")[0]
        deadline = working_days_after(changed, 5)
        leftover = sorted(
            g
            for g in ev.groups_of(acct["username"])
            if old_dept in g or (old_dept == "Finance" and g.startswith("Finance-"))
        )
        t.items.append(
            Item(
                acct["username"],
                f"{old_dept} to {p['department']} on {changed}; deadline {deadline}",
                "Exception" if leftover else "Pass",
                (
                    f"Still holds {', '.join(leftover)} at {ev.as_at}, "
                    f"{(ev.as_at - deadline).days} days after the deadline."
                )
                if leftover
                else "No access from the previous role remains.",
            )
        )
    t.conclude(["F4"] if t.exceptions() else None)
    return t


def test_joiners(ev: Evidence) -> Test:
    t = Test(
        "AC-03",
        "New starters' access is approved by their line manager",
        "3.1",
        "Operating effectiveness",
        "Access is only given when the business has asked for it.",
        "From the HR extract, select every employee who started in the audit period. For "
        "each, find the access request, and check it was approved by the line manager "
        "recorded in HR, on or before the start date, and that the groups granted match "
        "the request.",
        "All starters between 1 July and 30 September 2026",
    )
    for p in ev.hr:
        start = iso_date(p["start_date"])
        if not (PERIOD_START <= start <= PERIOD_END):
            continue
        acct = ev.by_employee_id[p["employee_id"]]
        manager = ev.by_employee_id.get(p["line_manager_id"], {}).get("username", "")
        groups = ev.groups_of(acct["username"])
        problems, notes = [], []
        for g in sorted(groups):
            r = ev.approved_request(acct["username"], g)
            if not r:
                problems.append(f"no approved request for {g}")
                continue
            if r["approved_by"] != manager:
                problems.append(f"{g} approved by {r['approved_by']}, not line manager {manager}")
            if date.fromisoformat(r["approved_date"]) > start:
                problems.append(f"{g} approved {r['approved_date']}, after start date {start}")
            notes.append(
                f"{g}: {r['request_id']} approved by {r['approved_by']} on {r['approved_date']}"
            )
        t.items.append(
            Item(
                acct["username"],
                f"Started {start}; line manager {manager}",
                "Exception" if problems else "Pass",
                "; ".join(problems) if problems else "; ".join(notes),
            )
        )
    t.conclude()
    return t


def test_reconciliation(ev: Evidence) -> Test:
    t = Test(
        "AC-04",
        "Every enabled personal account belongs to a current employee or contractor",
        "3.3, 3.4",
        "Operating effectiveness",
        "No active account exists for someone who no longer works for the company.",
        "List every enabled personal account in the directory. Match each one by employee "
        "or contractor ID to the HR extract and contractor list. An account with no match, "
        "or whose match has left or whose contract has ended, is an exception. Generic, "
        "administrator, service and built in accounts are tested in AC-08 to AC-10.",
        "All enabled personal accounts at the extraction date",
    )
    contractors = {c["contractor_id"]: c for c in ev.contractors}
    hr = {p["employee_id"]: p for p in ev.hr}
    for u in sorted(ev.users.values(), key=lambda x: x["username"]):
        if u["enabled"] != "Yes" or ev.kind(u["username"]) != "Personal":
            continue
        ident = u["employee_id"]
        if ident in hr:
            p = hr[ident]
            ok = p["employment_status"] == "Active"
            comment = (
                f"Matches active employee {p['first_name']} {p['last_name']}."
                if ok
                else f"Employee left on {p['end_date']} but the account is enabled."
            )
        elif ident in contractors:
            c = contractors[ident]
            ok = c["status"] == "Active"
            comment = (
                "Matches active contractor."
                if ok
                else f"Contract with {c['agency']} ended on {c['contract_end']} "
                f"but the account is enabled."
            )
        else:
            ok, comment = False, "No matching employee or contractor record."
        t.items.append(
            Item(u["username"], ident or "no ID", "Pass" if ok else "Exception", comment)
        )
    t.conclude(["F1", "F5"] if t.exceptions() else None)
    return t


def test_contractors(ev: Evidence) -> Test:
    t = Test(
        "AC-05",
        "Contractor accounts expire at the end of the contract",
        "3.4",
        "Design",
        "A contractor's access stops automatically when their contract ends, even if "
        "nobody remembers to remove it.",
        "For every contractor on the contractor list, find their account and check its "
        "expiry date is set to the contract end date.",
        "All contractors on the contractor list",
    )
    for c in ev.contractors:
        acct = ev.by_employee_id.get(c["contractor_id"])
        if not acct:
            t.items.append(Item(c["contractor_id"], "", "Pass", "No account found."))
            continue
        expires = acct["account_expires"]
        ok = expires != "Never" and expires[:10] <= c["contract_end"]
        t.items.append(
            Item(
                acct["username"],
                f"Contract ended {c['contract_end']}",
                "Pass" if ok else "Exception",
                f"Account expiry: {expires}."
                + (
                    ""
                    if ok
                    else " No expiry was set, so the account stayed usable after the "
                    "contract ended."
                ),
            )
        )
    t.conclude(["F5"] if t.exceptions() else None)
    return t


def test_dormant(ev: Evidence) -> Test:
    t = Test(
        "AC-06",
        "Unused accounts are disabled",
        "3.5",
        "Operating effectiveness",
        "Accounts nobody uses are removed before they can be misused unnoticed.",
        "List every enabled account. Flag any account that has never signed in, or whose "
        "last sign in was 45 days or more before the extraction date, unless an approved "
        "exception exists.",
        "All enabled accounts at the extraction date",
    )
    for u in sorted(ev.users.values(), key=lambda x: x["username"]):
        if u["enabled"] != "Yes":
            continue
        last = iso_date(u["last_logon"])
        if last and (ev.as_at - last).days < 45:
            t.items.append(
                Item(u["username"], ev.kind(u["username"]), "Pass", f"Last signed in {last}.")
            )
            continue
        t.items.append(
            Item(
                u["username"],
                ev.kind(u["username"]),
                "Exception",
                "Never signed in."
                if not last
                else f"Last signed in {last}, {(ev.as_at - last).days} days ago.",
            )
        )
    t.conclude(["F5", "F9"] if t.exceptions() else None)
    return t


def test_password_policy(ev: Evidence) -> Test:
    t = Test(
        "AC-07",
        "Domain password and lockout settings meet policy",
        "4.1, 4.2",
        "Design",
        "Passwords are hard to guess and accounts cannot be attacked by repeated guessing.",
        "Read the live domain password settings and compare each with the policy.",
        "The domain password policy (one configuration)",
    )
    p = ev.policy
    checks = [
        ("Minimum password length", int(p["Minimum password length"]), ">= 12", lambda v: v >= 12),
        ("Password complexity", p["Password complexity"], "on", lambda v: v == "on"),
        ("Password history length", int(p["Password history length"]), ">= 24", lambda v: v >= 24),
        (
            "Maximum password age (days)",
            int(p["Maximum password age (days)"]),
            "1 to 90",
            lambda v: 0 < v <= 90,
        ),
        (
            "Account lockout threshold (attempts)",
            int(p["Account lockout threshold (attempts)"]),
            "1 to 5",
            lambda v: 0 < v <= 5,
        ),
        (
            "Account lockout duration (mins)",
            int(p["Account lockout duration (mins)"]),
            ">= 15",
            lambda v: v >= 15,
        ),
    ]
    for name, value, required, ok in checks:
        passed = ok(value)
        comment = f"Configured {value}; policy requires {required}."
        if name.startswith("Account lockout threshold") and value == 0:
            comment += " A threshold of 0 means accounts never lock."
        if (
            name.startswith("Account lockout duration")
            and int(p["Account lockout threshold (attempts)"]) == 0
        ):
            passed, comment = True, comment + " Has no effect while lockout is disabled."
        t.items.append(Item(name, str(value), "Pass" if passed else "Exception", comment))
    t.conclude(["F6"] if t.exceptions() else None)
    return t


def test_non_expiring(ev: Evidence) -> Test:
    t = Test(
        "AC-08",
        "Only approved service accounts have non-expiring passwords",
        "4.3",
        "Operating effectiveness",
        "Every person's password is changed regularly.",
        "List every enabled account whose password is set never to expire. Each must be a "
        "service account with an approved, in date entry in the exception register.",
        "All enabled accounts with non-expiring passwords",
    )
    for u in sorted(ev.users.values(), key=lambda x: x["username"]):
        if u["enabled"] != "Yes" or u["password_never_expires"] != "Yes":
            continue
        kind = ev.kind(u["username"])
        exc = ev.has_exception(u["username"], "4.3")
        if kind == "Service" and exc and date.fromisoformat(exc["review_date"]) >= ev.as_at:
            t.items.append(
                Item(
                    u["username"],
                    kind,
                    "Pass",
                    f"Approved exception {exc['exception_id']} by "
                    f"{exc['approved_by']}, review due {exc['review_date']}.",
                )
            )
        else:
            t.items.append(
                Item(
                    u["username"],
                    kind,
                    "Exception",
                    f"{kind} account; no approved exception."
                    if kind != "Service"
                    else "Service account without an approved exception.",
                )
            )
    t.conclude(["F7"] if t.exceptions() else None)
    return t


def test_shared(ev: Evidence) -> Test:
    t = Test(
        "AC-09",
        "There are no shared accounts",
        "4.4",
        "Operating effectiveness",
        "Every action can be traced to one person.",
        "List every enabled account that is not personal, administrator, service or built "
        "in, and confirm its purpose from its description.",
        "All enabled generic accounts",
    )
    for u in sorted(ev.users.values(), key=lambda x: x["username"]):
        if u["enabled"] == "Yes" and ev.kind(u["username"]) == "Generic":
            t.items.append(
                Item(
                    u["username"],
                    u["description"],
                    "Exception",
                    f"Shared login used by more than one person. Member of "
                    f"{u['groups'].replace(';', ', ')}.",
                )
            )
    if not t.items:
        t.items.append(Item("Directory", "", "Pass", "No generic accounts found."))
    t.conclude(["F3"] if t.exceptions() else None)
    return t


def test_privileged(ev: Evidence) -> Test:
    t = Test(
        "AC-10",
        "Domain Admins is limited to approved, named administrator accounts",
        "5.1, 5.2, 5.3",
        "Operating effectiveness",
        "Full control of the domain is held only by people who need it, through separate "
        "accounts that are not used for everyday work.",
        "List every member of Domain Admins. Each must be a separate adm. account with an "
        "approved request, or the built in Administrator account. Day to day accounts and "
        "service accounts are exceptions unless an approved exception exists.",
        "All members of Domain Admins",
    )
    for m in sorted(ev.members.get("Domain Admins", set())):
        kind = ev.kind(m)
        if kind == "Built in":
            t.items.append(
                Item(
                    m,
                    kind,
                    "Pass",
                    "Built in break glass account. Its use should be "
                    "monitored; see observation O1.",
                )
            )
            continue
        req = ev.approved_request(m, "Domain Admins")
        if kind == "Administrator" and req:
            t.items.append(
                Item(
                    m,
                    kind,
                    "Pass",
                    f"Separate admin account; {req['request_id']} "
                    f"approved by {req['approved_by']}.",
                )
            )
        elif kind == "Service":
            exc = ev.has_exception(m, "5.3")
            t.items.append(
                Item(
                    m,
                    kind,
                    "Pass" if exc else "Exception",
                    "Approved exception."
                    if exc
                    else "Service account in Domain Admins with no exception recorded "
                    "under clause 5.3 (its exception covers only clause 4.3).",
                )
            )
        else:
            other = [
                r["request_id"] + " " + r["access_requested"]
                for r in ev.requests
                if r["account"] == m
            ]
            t.items.append(
                Item(
                    m,
                    kind,
                    "Exception",
                    "Everyday personal account with full domain admin rights and no "
                    "approved request. Approved access: " + (", ".join(other) or "none") + ".",
                )
            )
    t.conclude(["F2"] if t.exceptions() else None)
    return t


def test_sod(ev: Evidence) -> Test:
    t = Test(
        "AC-11",
        "No one can both create and approve supplier payments",
        "6.1",
        "Operating effectiveness",
        "A single person cannot make and approve a fraudulent payment.",
        "Compare the members of Finance-Payments-Initiators with the members of "
        "Finance-Payments-Approvers. Anyone in both is an exception.",
        "All members of either payments group",
    )
    init = ev.members.get("Finance-Payments-Initiators", set())
    appr = ev.members.get("Finance-Payments-Approvers", set())
    for m in sorted(init | appr):
        both = m in init and m in appr
        t.items.append(
            Item(
                m,
                ("Initiator and Approver" if both else "Initiator" if m in init else "Approver"),
                "Exception" if both else "Pass",
                "Holds both conflicting roles." if both else "One role only.",
            )
        )
    t.conclude(["F8"] if t.exceptions() else None)
    return t


def test_self_approval(ev: Evidence) -> Test:
    t = Test(
        "AC-12",
        "Nobody approves their own access",
        "6.2",
        "Operating effectiveness",
        "Access is always checked by someone other than the person receiving it.",
        "Inspect every access request. Any request approved by the person it gives access "
        "to is an exception.",
        f"All {len(ev.requests)} access requests in the access request log",
    )
    for r in ev.requests:
        own = r["approved_by"] == r["account"]
        t.items.append(
            Item(
                r["request_id"],
                f"{r['account']}: {r['access_requested']}",
                "Exception" if own else "Pass",
                f"Requested and approved by {r['approved_by']}, for their own account."
                if own
                else f"Approved by {r['approved_by']}.",
            )
        )
    t.conclude(["F8"] if t.exceptions() else None)
    return t


def test_authorisation(ev: Evidence) -> Test:
    t = Test(
        "AC-13",
        "Every member of a sensitive group has approved access",
        "3.1, 5.1",
        "Operating effectiveness",
        "Nobody holds powerful access that the business did not approve.",
        "For every member of each sensitive group, find an approved access request for "
        "that group. Requests approved by the person themselves are dealt with in AC-12.",
        "All members of: " + ", ".join(SENSITIVE_GROUPS),
    )
    for g in SENSITIVE_GROUPS:
        for m in sorted(ev.members.get(g, set())):
            if m in BUILT_IN:
                t.items.append(
                    Item(
                        f"{g}: {m}",
                        "Built in",
                        "Not applicable",
                        "Built in account, created with the domain.",
                    )
                )
                continue
            r = ev.approved_request(m, g)
            t.items.append(
                Item(
                    f"{g}: {m}",
                    ev.kind(m),
                    "Pass" if r else "Exception",
                    f"{r['request_id']} approved by {r['approved_by']} on {r['approved_date']}."
                    if r
                    else "No approved request.",
                )
            )
    t.conclude(["F2", "F3"] if t.exceptions() else None)
    return t


def test_access_review(ev: Evidence) -> Test:
    t = Test(
        "AC-14",
        "Quarterly access reviews are performed",
        "7.1",
        "Operating effectiveness",
        "Access that is no longer needed is found and removed even when other controls miss it.",
        "Request the signed off Q3 2026 review of Domain Admins, IT-Server-Admins and the "
        "two payments groups, and re-perform a sample of the review's conclusions.",
        "The Q3 2026 quarterly access review",
    )
    t.items.append(
        Item(
            "Q3 2026 access review",
            "Requested from the Head of IT",
            "Exception",
            "No evidence of a review was provided. Several exceptions found in this "
            "testing (AC-01, AC-02, AC-10, AC-11) would have been caught by an "
            "effective review.",
        )
    )
    t.conclude(["F10"])
    return t


ALL_TESTS = [
    test_leavers,
    test_movers,
    test_joiners,
    test_reconciliation,
    test_contractors,
    test_dormant,
    test_password_policy,
    test_non_expiring,
    test_shared,
    test_privileged,
    test_sod,
    test_self_approval,
    test_authorisation,
    test_access_review,
]


# Each test mapped to ISO/IEC 27001:2022 Annex A controls and CIS Controls v8.1 safeguards.
# The company policy is the criteria the tests are judged against; this mapping shows how
# each test relates to the two frameworks most often used to structure IT controls.
FRAMEWORKS = {
    "AC-01": ("A.5.18 Access rights", "6.2 Access revoking process"),
    "AC-02": ("A.5.18 Access rights", "6.2 Access revoking process; 6.8 Role based access"),
    "AC-03": ("A.5.18 Access rights", "6.1 Access granting process"),
    "AC-04": (
        "A.5.16 Identity management; A.5.18 Access rights",
        "5.1 Inventory of accounts; 6.2 Access revoking process",
    ),
    "AC-05": ("A.5.18 Access rights", "6.2 Access revoking process"),
    "AC-06": ("A.5.18 Access rights", "5.3 Disable dormant accounts"),
    "AC-07": (
        "A.5.17 Authentication information; A.8.5 Secure authentication",
        "5.2 Use unique passwords",
    ),
    "AC-08": (
        "A.5.17 Authentication information",
        "5.2 Use unique passwords; 5.5 Inventory of service accounts",
    ),
    "AC-09": ("A.5.16 Identity management", "5.1 Inventory of accounts"),
    "AC-10": (
        "A.8.2 Privileged access rights",
        "5.4 Dedicated administrator accounts; 5.5 Inventory of service accounts",
    ),
    "AC-11": ("A.5.3 Segregation of duties", "6.8 Role based access"),
    "AC-12": ("A.5.3 Segregation of duties; A.5.18 Access rights", "6.1 Access granting process"),
    "AC-13": (
        "A.5.18 Access rights; A.8.2 Privileged access rights",
        "6.1 Access granting process; 6.8 Role based access",
    ),
    "AC-14": ("A.5.18 Access rights", "6.8 Role based access (recurring access reviews)"),
}


def run_all(evidence_dir: Path, scenario_dir: Path) -> tuple[Evidence, list[Test]]:
    ev = Evidence(evidence_dir, scenario_dir)
    tests = [fn(ev) for fn in ALL_TESTS]
    for t in tests:
        t.iso27001, t.cis_controls = FRAMEWORKS[t.test_id]
    return ev, tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--scenario", default=ROOT / "scenario", type=Path)
    parser.add_argument("--out", default=ROOT / "workpapers", type=Path)
    args = parser.parse_args()

    problems = verify_evidence(args.evidence)
    if problems:
        print("Evidence failed its integrity check, so it cannot be relied on:")
        print("\n".join(f"  {p}" for p in problems))
        return 1

    ev, tests = run_all(args.evidence, args.scenario)
    args.out.mkdir(parents=True, exist_ok=True)
    from workpaper import build_workpaper  # local module, imported late to keep tests light

    build_workpaper(ev, tests, args.out / "logical-access-workpaper.xlsx")
    (args.out / "results.json").write_text(
        json.dumps(
            {
                "evidence": str(
                    args.evidence.relative_to(ROOT)
                    if args.evidence.is_relative_to(ROOT)
                    else args.evidence
                ),
                "as_at": ev.as_at.isoformat(),
                "period": [PERIOD_START.isoformat(), PERIOD_END.isoformat()],
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
    print(f"\nWorkpaper: {args.out / 'logical-access-workpaper.xlsx'}")
    return 0


def verify_evidence(folder: Path) -> list[str]:
    problems = []
    sums = folder / "SHA256SUMS"
    if not sums.exists():
        return ["SHA256SUMS is missing"]
    for line in sums.read_text().splitlines():
        digest, _, name = line.partition("  ")
        path = folder / name
        if not path.exists():
            problems.append(f"{name}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"{name}: modified since extraction")
    return problems


if __name__ == "__main__":
    raise SystemExit(main())
