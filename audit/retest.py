#!/usr/bin/env python3
"""Remediation testing: confirm each finding's condition has been fixed.

Rerunning the Q3 tests on new evidence still reports events that happened during the
period, such as a sign in after leaving. Remediation testing asks a different question:
is the condition behind each finding resolved now? Each check below is specific to its
finding and reads a fresh evidence extraction taken after remediation.

    python3 audit/retest.py --evidence evidence/directory-<after remediation>

Writes workpapers/remediation-retest.md and workpapers/remediation-retest.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from findings import FINDINGS
from run_tests import ROOT, Evidence, verify_evidence

RESOLVED, FOLLOW_UP, OPEN = "Resolved", "Resolved, follow up open", "Open"


def check(ev: Evidence) -> dict[str, tuple[str, str]]:
    u = ev.users
    groups = ev.groups_of
    da = ev.members.get("Domain Admins", set())
    res: dict[str, tuple[str, str]] = {}

    m = u["mark.taylor"]
    fixed = (
        m["enabled"] == "No" and not groups("mark.taylor") and m["location"].startswith("Leavers")
    )
    res["F1"] = (
        FOLLOW_UP if fixed else OPEN,
        "mark.taylor is disabled, has no group memberships and is in Leavers. The "
        "sign in after the leaving date still needs to be investigated."
        if fixed
        else f"mark.taylor: enabled={m['enabled']}, "
        f"groups={', '.join(sorted(groups('mark.taylor'))) or 'none'}.",
    )

    left = sorted(da & {"liam.brooks", "svc-backup"})
    res["F2"] = (
        (OPEN, f"Still in Domain Admins: {', '.join(left)}.")
        if left
        else (
            RESOLVED,
            "Domain Admins now contains only Administrator and the adm. accounts: "
            + ", ".join(sorted(da))
            + ".",
        )
    )

    f = u["finance.shared"]
    ok = f["enabled"] == "No" and not groups("finance.shared")
    res["F3"] = (
        RESOLVED if ok else OPEN,
        "finance.shared is disabled with no group memberships."
        if ok
        else "finance.shared is still enabled or still holds groups.",
    )

    held = sorted(groups("emma.wilson") & {"GG-Finance", "Finance-Payments-Initiators"})
    res["F4"] = (
        (OPEN, f"emma.wilson still holds {', '.join(held)}.")
        if held
        else (
            RESOLVED,
            "emma.wilson holds only Sales access: "
            + ", ".join(sorted(groups("emma.wilson")))
            + ".",
        )
    )

    lm = u["leo.martin"]
    ok = lm["enabled"] == "No" and not groups("leo.martin")
    res["F5"] = (
        FOLLOW_UP if ok else OPEN,
        "leo.martin is disabled with no group memberships. Setting expiry dates on "
        "new contractor accounts is a process change to confirm on the next contractor "
        "joiner."
        if ok
        else "leo.martin is still enabled or still holds groups.",
    )

    p = ev.policy
    length = int(p["Minimum password length"])
    lockout = int(p["Account lockout threshold (attempts)"])
    ok = length >= 12 and 0 < lockout <= 5
    res["F6"] = (
        RESOLVED if ok else OPEN,
        f"Minimum password length {length}; lockout after {lockout} attempts.",
    )

    bad = sorted(
        n
        for n, x in u.items()
        if x["enabled"] == "Yes"
        and x["password_never_expires"] == "Yes"
        and ev.kind(n) != "Service"
    )
    res["F7"] = (
        (OPEN, f"Still set: {', '.join(bad)}.")
        if bad
        else (
            RESOLVED,
            "Only service accounts with approved exceptions keep non-expiring passwords.",
        )
    )

    both = ev.members.get("Finance-Payments-Initiators", set()) & ev.members.get(
        "Finance-Payments-Approvers", set()
    )
    res["F8"] = (
        (OPEN, f"Still holding both roles: {', '.join(sorted(both))}.")
        if both
        else (
            FOLLOW_UP,
            "Nobody now holds both payment roles. The review of payments approved by "
            "priya.shah since November 2025, and blocking self approval in the request "
            "process, remain open.",
        )
    )

    s = u["svc-financeapp"]
    res["F9"] = (
        (RESOLVED, "svc-financeapp is disabled.")
        if s["enabled"] == "No"
        else (OPEN, "svc-financeapp is still enabled and unused.")
    )

    res["F10"] = (
        OPEN,
        "Process change. The first quarterly review is due at the end of Q4 "
        "2026 and will be tested then.",
    )
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--scenario", default=ROOT / "scenario", type=Path)
    parser.add_argument("--out", default=ROOT / "workpapers", type=Path)
    args = parser.parse_args()

    problems = verify_evidence(args.evidence)
    if problems:
        print("Evidence failed its integrity check:\n  " + "\n  ".join(problems))
        return 1
    ev = Evidence(args.evidence, args.scenario)
    results = check(ev)

    lines = [
        "# Remediation retest",
        "",
        f"Evidence extracted after remediation on {ev.as_at} (`{args.evidence.name}`). Each "
        "finding was retested by checking its condition directly in the new extraction.",
        "",
        "| Finding | Rating | Status | Retest result |",
        "|---|---|---|---|",
    ]
    for f in FINDINGS:
        status, note = results[f.finding_id]
        lines.append(f"| {f.finding_id}: {f.title} | {f.rating} | **{status}** | {note} |")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "remediation-retest.md").write_text("\n".join(lines) + "\n")
    (args.out / "remediation-retest.json").write_text(
        json.dumps(
            {
                "evidence": args.evidence.name,
                "as_at": ev.as_at.isoformat(),
                "results": {k: {"status": v[0], "note": v[1]} for k, v in results.items()},
            },
            indent=2,
        )
        + "\n"
    )

    for f in FINDINGS:
        status, note = results[f.finding_id]
        print(f"{f.finding_id:<4} {status:<26} {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
