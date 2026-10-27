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
        "application's payment roles. Change management and IT operations controls are out "
        "of scope and will be reviewed separately.",
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
        "was extracted. Time synchronisation will be tested as an IT operations control.",
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
        "2. Phase 2: change management and IT operations (backups and time "
        "synchronisation) on the application server.",
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


def main() -> int:
    results = json.loads((ROOT / "workpapers" / "results.json").read_text())
    (ROOT / "report").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "report" / "logical-access-review.md").write_text(report(results))
    (ROOT / "docs" / "testing-programme.md").write_text(programme(results))
    print("Wrote report/logical-access-review.md and docs/testing-programme.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
