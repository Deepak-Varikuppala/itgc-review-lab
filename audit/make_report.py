#!/usr/bin/env python3
"""Write the review report and the testing programme from the test results and findings.

    python3 audit/make_report.py

Reads workpapers/results.json (written by run_tests.py) and findings.py, and writes
report/logical-access-review.md and docs/testing-programme.md, so the report, the
programme and the workpaper always agree.
"""

from __future__ import annotations

import json
from pathlib import Path

from findings import FINDINGS, OBSERVATIONS

ROOT = Path(__file__).resolve().parents[1]


def words(n: int) -> str:
    names = [
        "None",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
    ]
    return names[n] if n < len(names) else str(n)


def tested(test: dict) -> int:
    return sum(1 for i in test["items"] if i["result"] != "Not applicable")


def exceptions(test: dict) -> int:
    return sum(1 for i in test["items"] if i["result"] == "Exception")


def report(results: dict) -> str:
    tests = results["tests"]
    counts = {r: sum(1 for f in FINDINGS if f.rating == r) for r in ("High", "Medium", "Low")}
    effective = [t for t in tests if not exceptions(t)]
    design = sum(1 for t in tests if t["test_type"] == "Design")
    out = [
        "# Northwind Retail: Logical Access Review",
        "",
        "| | |",
        "|---|---|",
        "| Entity | Northwind Retail (fictional company, lab environment) |",
        "| System | Active Directory domain `northwind.internal` |",
        "| Audit period | 1 July 2026 to 30 September 2026 |",
        f"| Evidence extracted | {results['as_at']} |",
        "| Criteria | Northwind Retail Access Control Policy v2.1 |",
        "| Prepared by | Deepak Kumar Varikuppala |",
        "| Status | Issued for management response |",
        "",
        "## 1. Summary",
        "",
        "**Overall conclusion: logical access controls over the Northwind domain were not "
        "operating effectively during the period.**",
        "",
        f"Of {len(tests)} controls tested, {len(effective)} operated without exception and "
        f"{len(tests) - len(effective)} had exceptions. The review raised {len(FINDINGS)} "
        f"findings: {counts['High']} high, {counts['Medium']} medium and {counts['Low']} low.",
        "",
        "Three themes explain most of the findings:",
        "",
        "1. **Access is added reliably but rarely taken away.** New starters were set up "
        "correctly, but a leaver, a mover and a contractor all kept access they should have "
        "lost (F1, F4, F5).",
        "2. **The payments process can be bypassed by one person.** A Senior Accountant "
        "approved her own request to become a payment approver, and a shared login can "
        "create payments without anyone being accountable (F8, F3).",
        "3. **Privileged access and the domain settings have drifted from policy.** Two "
        "accounts hold full domain administrator rights without approval, and accounts can "
        "be attacked by unlimited password guessing (F2, F6).",
        "",
        "The quarterly access review, which should have caught most of these, could not be "
        "evidenced (F10).",
        "",
        "The most urgent actions are to disable the leaver's account and investigate its use "
        "after he left, remove the conflicting payment access, disable the shared finance "
        "login, and enable account lockout.",
        "",
        "## 2. Scope and approach",
        "",
        "The review covered logical access to the `northwind.internal` Active Directory "
        "domain, which controls sign in to Northwind's systems and access to the finance "
        "application's payment roles. Change management, IT operations and access to the "
        "servers are reported separately, for the same period, in "
        "[change-and-operations-review.md](change-and-operations-review.md).",
        "",
        "Directory data was extracted read only by the system administrator using a scripted "
        "extraction (`audit/collect_evidence.py`). Before testing, the extraction was checked "
        "for **completeness**, by confirming the record counts in the raw directory output "
        "matched the processed listing, and for **integrity**, by verifying SHA-256 hashes "
        "of every evidence file.",
        "",
        "Each control was tested against the clause of the policy it implements. Tests "
        "examined the **whole population** rather than a sample, so there is no sampling "
        f"risk. {words(design)} tests assess **design** (whether the configuration can "
        f"achieve the policy at all) and {words(len(tests) - design).lower()} assess "
        "**operating effectiveness** (whether the control worked in practice). The full "
        "procedures are in "
        "[docs/testing-programme.md](../docs/testing-programme.md), and every item tested "
        "is in [the workpaper](../workpapers/logical-access-workpaper.xlsx).",
        "",
        "Each test is also mapped to ISO/IEC 27001:2022 Annex A and CIS Controls v8.1, so "
        "the results can be read against either framework. The mapping is in the testing "
        "programme.",
        "",
        "## 3. Results by control",
        "",
        "| Test | Control | Policy | Tested | Exceptions | Conclusion |",
        "|---|---|---|---|---|---|",
    ]
    for t in tests:
        out.append(
            f"| {t['test_id']} | {t['title']} | {t['policy_ref']} | {tested(t)} | "
            f"{exceptions(t)} | {t['conclusion']} |"
        )
    out += ["", "## 4. Findings", ""]
    out += ["| ID | Finding | Rating | Tests |", "|---|---|---|---|"]
    out += [
        f"| [{f.finding_id}](#{f.finding_id.lower()}) | {f.title} | **{f.rating}** | "
        f"{', '.join(f.tests)} |"
        for f in FINDINGS
    ]
    for f in FINDINGS:
        out += [
            "",
            f"### {f.finding_id}",
            "",
            f"**{f.title}**  ",
            f"Rating: **{f.rating}** | Policy clause {f.policy} | Tests {', '.join(f.tests)}",
            "",
            f"**Condition.** {f.condition}",
            "",
            f"**Criteria.** {f.criteria}",
            "",
            f"**Cause.** {f.cause}",
            "",
            f"**Effect.** {f.effect}",
            "",
            f"**Recommendation.** {f.recommendation}",
            "",
            "**Management response.** Pending.",
        ]
    out += ["", "## 5. Observations", ""]
    for oid, title, text in OBSERVATIONS:
        out += [f"**{oid}: {title}.** {text}", ""]
    out += [
        "## 6. Ratings",
        "",
        "| Rating | Meaning |",
        "|---|---|",
        "| High | Could directly allow fraud, loss of control of the domain, or unauthorised "
        "access to financial processes. Fix immediately. |",
        "| Medium | Weakens a control so that misuse is more likely or less likely to be "
        "detected. Fix within 30 days. |",
        "| Low | Good practice improvement with limited direct risk. Fix within 90 days. |",
        "",
        "## 7. Limitations",
        "",
        "* This is a lab environment. The company and its records are fictional, and the "
        "weaknesses were seeded deliberately to be found.",
        "* Account creation dates in the directory are the date the lab was built, so HR "
        "start dates were relied on instead.",
        "* Last logon dates were recorded when the lab was built. At that time the domain "
        "controller's clock was about 38 minutes slow; it was corrected before the evidence "
        "was extracted. Time synchronisation was tested as an IT operations control (OP-06, "
        "finding F22).",
        "* No evidence of the quarterly access review was provided, so that control could "
        "not be tested beyond confirming its absence.",
        "",
    ]
    out += retest_section()
    out += [
        "## 9. Next steps",
        "",
        "1. Complete the open follow ups from the retest, and test the first quarterly "
        "access review when it is performed.",
        "2. Change management, IT operations and server access are reported in "
        "[change-and-operations-review.md](change-and-operations-review.md), and both "
        "reviews are brought together in [itgc-summary.md](itgc-summary.md).",
        "",
    ]
    return "\n".join(out)


def retest_section() -> list[str]:
    path = ROOT / "workpapers" / "remediation-retest.json"
    out = ["## 8. Remediation and retest", ""]
    if not path.exists():
        return out + ["Remediation has not yet been retested.", ""]
    retest = json.loads(path.read_text())
    out += [
        f"After remediation, a fresh extraction was taken on {retest['as_at']} "
        f"(`{retest['evidence']}`) and each finding's condition was checked directly. Full "
        "detail is in [workpapers/remediation-retest.md](../workpapers/remediation-retest.md).",
        "",
        "| Finding | Rating | Status | Retest result |",
        "|---|---|---|---|",
    ]
    for f in FINDINGS:
        r = retest["results"][f.finding_id]
        out.append(f"| {f.finding_id} | {f.rating} | **{r['status']}** | {r['note']} |")
    return out + [""]


def programme(results: dict) -> str:
    out = [
        "# Testing programme: logical access",
        "",
        "Generated from the test definitions in `audit/run_tests.py`. Each test was designed "
        "before testing began, against the clause of the Northwind Access Control Policy it "
        "covers. Each test is also mapped to ISO/IEC 27001:2022 Annex A and to CIS Controls "
        "v8.1 safeguards. The policy remains the criteria; the mapping shows where each test "
        "sits in those frameworks.",
        "",
        "| Test | Control | Policy | Type | ISO/IEC 27001:2022 | CIS Controls v8.1 |",
        "|---|---|---|---|---|---|",
    ]
    out += [
        f"| {t['test_id']} | {t['title']} | {t['policy_ref']} | {t['test_type']} | "
        f"{t['iso27001']} | {t['cis_controls']} |"
        for t in results["tests"]
    ]
    for t in results["tests"]:
        out += [
            "",
            f"## {t['test_id']}: {t['title']}",
            "",
            f"**Policy clause:** {t['policy_ref']}  ",
            f"**ISO/IEC 27001:2022:** {t['iso27001']}  ",
            f"**CIS Controls v8.1:** {t['cis_controls']}  ",
            f"**Test type:** {t['test_type']}",
            "",
            f"**Control objective.** {t['objective']}",
            "",
            f"**Procedure.** {t['procedure']}",
            "",
            f"**Population.** {t['population']}. Every item was tested.",
            "",
            "**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, "
            "`password-policy.txt`) and the relevant company records in `scenario/`.",
        ]
    return "\n".join(out) + "\n"


RATINGS = [
    "## 6. Ratings",
    "",
    "| Rating | Meaning |",
    "|---|---|",
    "| High | Could directly allow fraud, loss of control of a system, loss of data, or "
    "unauthorised access to financial processes. Fix immediately. |",
    "| Medium | Weakens a control so that misuse is more likely or less likely to be "
    "detected. Fix within 30 days. |",
    "| Low | Good practice improvement with limited direct risk. Fix within 90 days. |",
    "",
]


def findings_detail(findings) -> list[str]:
    out = ["| ID | Finding | Rating | Tests |", "|---|---|---|---|"]
    out += [
        f"| [{f.finding_id}](#{f.finding_id.lower()}) | {f.title} | **{f.rating}** | "
        f"{', '.join(f.tests)} |"
        for f in findings
    ]
    for f in findings:
        out += [
            "",
            f"### {f.finding_id}",
            "",
            f"**{f.title}**  ",
            f"Rating: **{f.rating}** | Criteria: {f.policy} | Tests {', '.join(f.tests)}",
            "",
            f"**Condition.** {f.condition}",
            "",
            f"**Criteria.** {f.criteria}",
            "",
            f"**Cause.** {f.cause}",
            "",
            f"**Effect.** {f.effect}",
            "",
            f"**Recommendation.** {f.recommendation}",
            "",
            "**Management response.** Pending.",
        ]
    return out


def change_ops_report(results: dict) -> str:
    from change_ops_findings import FINDINGS as CO_FINDINGS
    from change_ops_findings import OBSERVATIONS as CO_OBSERVATIONS

    tests = results["tests"]
    counts = {r: sum(1 for f in CO_FINDINGS if f.rating == r) for r in ("High", "Medium", "Low")}
    effective = [t for t in tests if not exceptions(t)]
    sampled = [t for t in tests if t["sample"]]
    ev = results["evidence"]
    out = [
        "# Northwind Retail: Change Management, IT Operations and Server Access Review",
        "",
        "| | |",
        "|---|---|",
        "| Entity | Northwind Retail (fictional company, lab environment) |",
        "| Systems | Finance application and its code repository (Gitea) on `linux2`; Linux "
        "servers `linux` (domain controller) and `linux2` (application server) |",
        "| Audit period | 1 July 2026 to 30 September 2026 |",
        f"| Evidence extracted | {results['as_at']} |",
        "| Criteria | Northwind Retail Change Management and IT Operations Standard v1.4; "
        "Access Control Policy v2.1 |",
        "| Prepared by | Deepak Kumar Varikuppala |",
        "| Status | Issued for management response |",
        "",
        "## 1. Summary",
        "",
        "**Overall conclusion: change management, IT operations and server access controls "
        "were not operating effectively during the period.**",
        "",
        f"Of {len(tests)} controls tested, {len(effective)} operated without exception and "
        f"{len(tests) - len(effective)} had exceptions. The review raised {len(CO_FINDINGS)} "
        "findings: "
        + " and ".join(
            ", ".join(
                f"{counts[r]} {r.lower()}" for r in ("High", "Medium", "Low") if counts[r]
            ).rsplit(", ", 1)
        )
        + ". They are numbered on from the ten findings of the logical access review "
        "([report](logical-access-review.md)), which covers the same period.",
        "",
        "Four themes explain the findings:",
        "",
        "1. **The change process can be skipped, and was.** Branch protection lets one "
        "developer push straight to the main branch and lets administrators merge without "
        "approval, and the deployment tool does not need a ticket. Five of 40 changes went "
        "live without review, three of them with no ticket (F11, F15, F14).",
        "2. **The people who write the code also put it live.** A developer deployed his own "
        "changes 8 times, and both people who write code can deploy. A contractor whose "
        "contract had ended still had access and changed the code (F12, F16).",
        "3. **Administrator access on the production server was given in a hurry and never "
        "taken back.** A supplier's account and a developer both have full control, and an "
        "unapproved job gives the same developer a hidden route to it (F17, F21).",
        "4. **Backups failed without anyone noticing, and restores were not tested.** The "
        "finance database went four days without a backup in August (F19, F20).",
        "",
        "Some controls worked. Most sampled changes were approved and tested before going "
        "live, one of the two emergency changes followed the procedure in full, security "
        "updates were up to date on both servers, and sign in to the app server is limited "
        "to IT staff.",
        "",
        "The most urgent actions are to remove the support account and the developer's "
        "administrator rights from the app server, remove the unapproved scheduled job, "
        "block direct changes to the main branch, disable the former contractor's Gitea "
        "account, and alert on backup failures.",
        "",
        "## 2. Scope and approach",
        "",
        "The review covered three areas over the finance application and the servers it "
        "depends on: change management (how code changes are reviewed, approved and "
        "deployed), IT operations (backups, restore testing, scheduled jobs, time and "
        "patching), and access to the servers themselves. The procedures, the evidence "
        "required and the sampling method were set out in the "
        "[test plan](../docs/test-plan-change-and-operations.md) before any evidence was "
        "collected.",
        "",
        "Evidence was extracted read only by scripted collectors: from Gitea's database and "
        "repository and the app server's logs (`audit/collect_app_evidence.py`), and from "
        "each Linux server (`audit/collect_host_evidence.py`). Each extraction was checked "
        "for **completeness**, for example the number of pull requests in the database "
        "against the rows exported, and the commits on main against both Gitea's records "
        "and the deployment log, and for **integrity** by SHA-256 hashes. Evidence folders: "
        + ", ".join(f"`{x}`" for x in [ev["app"], *ev["hosts"], ev["directory"]])
        + ".",
        "",
        "Where a test compares system records with each other or with a rule, every item in "
        "the population was tested. Where each item had to be read and judged, a random "
        f"sample was taken: {', '.join(t['test_id'] for t in sampled)}. The sample size comes "
        "from the table in the test plan, and the items were selected with "
        f"`random.Random({results['seed']}).sample()` so the selection can be repeated. "
        "Because these are key controls, one exception in a sample means the control is not "
        "relied on. The population and the selected items are on the Samples sheet of "
        "[the workpaper](../workpapers/change-operations-workpaper.xlsx), and the full "
        "procedures are in "
        "[docs/testing-programme-change-and-operations.md]"
        "(../docs/testing-programme-change-and-operations.md).",
        "",
        "Each test is mapped to ISO/IEC 27001:2022 Annex A and CIS Controls v8.1.",
        "",
        "## 3. Results by control",
        "",
        "| Test | Control | Criteria | Tested | Exceptions | Conclusion |",
        "|---|---|---|---|---|---|",
    ]
    for t in tests:
        how = f"{tested(t)} (sample)" if t["sample"] else str(tested(t))
        out.append(
            f"| {t['test_id']} | {t['title']} | {t['policy_ref']} | {how} | "
            f"{exceptions(t)} | {t['conclusion']} |"
        )
    out += [
        "",
        "AC-18 also found access already reported in the logical access review: Domain "
        "Admins rights without approval (F2), an ended contractor's enabled account (F5) "
        "and conflicting payment roles (F8).",
        "",
        "## 4. Findings",
        "",
    ]
    out += findings_detail(CO_FINDINGS)
    out += ["", "## 5. Observations", ""]
    for oid, title, text in CO_OBSERVATIONS:
        out += [f"**{oid}: {title}.** {text}", ""]
    out += RATINGS
    out += [
        "## 7. Limitations",
        "",
        "* This is a lab environment. The company and its records are fictional, and the "
        "weaknesses were seeded deliberately to be found.",
        "* The application server was built after the audit period. Its Q3 history (pull "
        "requests, reviews, merges, deployments and backup runs) was recreated through Gitea "
        "itself when it was built and dated to when each event happened. See "
        "[lab/README.md](../lab/README.md).",
        "* Server settings (sudo rules, SSH, scheduled jobs, time and patching) were "
        f"extracted on {results['as_at']}, after the period. File dates and password dates "
        "were used to establish when each exception began; settings with no date are "
        "reported as found.",
        "* The servers keep no sign in history (O4), so the use of the access in F17 could "
        "not be tested.",
        "* The office PC was not available during fieldwork, so the PC items in the test "
        "plan were not tested. See [the fieldwork notes](../docs/fieldwork-notes.md).",
        "",
        "## 8. Next steps",
        "",
        "1. Management responses, owners and dates for each finding.",
        "2. Remediation, followed by a retest of each finding's condition on fresh evidence, "
        "as was done for the logical access findings.",
        "3. Review of the office PC once it is in service.",
        "",
    ]
    return "\n".join(out)


AREAS = [
    ("Logical access: directory", ("AC-01", "AC-14")),
    ("Logical access: servers", ("AC-15", "AC-18")),
    ("Change management", ("CM-01", "CM-07")),
    ("IT operations", ("OP-01", "OP-07")),
]


def in_area(test_id: str, bounds: tuple[str, str]) -> bool:
    prefix, low, high = test_id[:2], int(bounds[0][3:]), int(bounds[1][3:])
    return prefix == bounds[0][:2] and low <= int(test_id[3:]) <= high


def summary(results: dict, co_results: dict) -> str:
    from change_ops_findings import FINDINGS as CO_FINDINGS

    tests = results["tests"] + co_results["tests"]
    findings = list(FINDINGS) + list(CO_FINDINGS)
    retest_path = ROOT / "workpapers" / "remediation-retest.json"
    retest = json.loads(retest_path.read_text())["results"] if retest_path.exists() else {}
    out = [
        "# Northwind Retail: IT General Controls Review, Q3 2026",
        "",
        "A summary of the two reports that make up the review of Northwind Retail's IT "
        "general controls for 1 July to 30 September 2026:",
        "",
        "* [Logical access review](logical-access-review.md): the Active Directory domain "
        "(AC-01 to AC-14), with a remediation retest.",
        "* [Change management, IT operations and server access review]"
        "(change-and-operations-review.md): the finance application, its code repository "
        "and the two Linux servers (AC-15 to AC-18, CM-01 to CM-07, OP-01 to OP-07).",
        "",
        "## Results by area",
        "",
        "| Area | Tests | Effective | With exceptions | Findings | Conclusion |",
        "|---|---|---|---|---|---|",
    ]
    for name, bounds in AREAS:
        area = [t for t in tests if in_area(t["test_id"], bounds)]
        ok = sum(1 for t in area if not exceptions(t))
        raised = sorted({f for t in area for f in t["findings"]}, key=lambda x: int(x[1:]))
        verdict = "Effective" if ok == len(area) else "Not effective"
        out.append(
            f"| {name} ({bounds[0]} to {bounds[1]}) | {len(area)} | {ok} | "
            f"{len(area) - ok} | {', '.join(raised) or 'None'} | **{verdict}** |"
        )
    counts = {r: sum(1 for f in findings if f.rating == r) for r in ("High", "Medium", "Low")}
    out += [
        "",
        f"**{len(tests)} controls were tested and {len(findings)} findings raised: "
        f"{counts['High']} high, {counts['Medium']} medium and {counts['Low']} low.** IT "
        "general controls over the finance application and the systems it depends on were "
        "not operating effectively in the period, so they cannot be relied on to support the "
        "accuracy of the finance application's records without further work.",
        "",
        "## All findings",
        "",
        "| ID | Finding | Rating | Status |",
        "|---|---|---|---|",
    ]
    for f in findings:
        report_file = (
            "logical-access-review.md" if f in FINDINGS else "change-and-operations-review.md"
        )
        status = retest.get(f.finding_id, {}).get("status", "Open, awaiting remediation")
        out.append(
            f"| [{f.finding_id}]({report_file}#{f.finding_id.lower()}) | {f.title} | "
            f"{f.rating} | {status} |"
        )
    out += [
        "",
        "Statuses for F1 to F10 come from the remediation retest. F11 to F22 are awaiting "
        "management responses and remediation.",
        "",
    ]
    return "\n".join(out)


def change_ops_programme(results: dict) -> str:
    out = [
        "# Testing programme: change management, IT operations and server access",
        "",
        "Generated from the test definitions in `audit/run_change_ops_tests.py`, which "
        "implement the [test plan](test-plan-change-and-operations.md) written before "
        "testing began. The criteria are the Change Management and IT Operations Standard "
        "(Standard) and the Access Control Policy (Policy).",
        "",
        "| Test | Control | Criteria | Type | Sample | ISO/IEC 27001:2022 | CIS Controls v8.1 |",
        "|---|---|---|---|---|---|---|",
    ]
    out += [
        f"| {t['test_id']} | {t['title']} | {t['policy_ref']} | {t['test_type']} | "
        f"{t['sample'] or 'Whole population'} | {t['iso27001']} | {t['cis_controls']} |"
        for t in results["tests"]
    ]
    for t in results["tests"]:
        sample = (
            f"**Sample.** {t['sample']}."
            if t["sample"]
            else "**Sample.** None: every item was tested."
        )
        out += [
            "",
            f"## {t['test_id']}: {t['title']}",
            "",
            f"**Criteria:** {t['policy_ref']}  ",
            f"**ISO/IEC 27001:2022:** {t['iso27001']}  ",
            f"**CIS Controls v8.1:** {t['cis_controls']}  ",
            f"**Test type:** {t['test_type']}",
            "",
            f"**Control objective.** {t['objective']}",
            "",
            f"**Procedure.** {t['procedure']}",
            "",
            f"**Population.** {t['population']}.",
            "",
            sample,
        ]
    return "\n".join(out) + "\n"


def main() -> int:
    results = json.loads((ROOT / "workpapers" / "results.json").read_text())
    (ROOT / "report").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "report" / "logical-access-review.md").write_text(report(results))
    (ROOT / "docs" / "testing-programme.md").write_text(programme(results))
    print("Wrote report/logical-access-review.md and docs/testing-programme.md")
    co = ROOT / "workpapers" / "change-operations-results.json"
    if co.exists():
        co_results = json.loads(co.read_text())
        (ROOT / "report" / "change-and-operations-review.md").write_text(
            change_ops_report(co_results)
        )
        (ROOT / "docs" / "testing-programme-change-and-operations.md").write_text(
            change_ops_programme(co_results)
        )
        (ROOT / "report" / "itgc-summary.md").write_text(summary(results, co_results))
        print(
            "Wrote report/change-and-operations-review.md, "
            "docs/testing-programme-change-and-operations.md and report/itgc-summary.md"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
