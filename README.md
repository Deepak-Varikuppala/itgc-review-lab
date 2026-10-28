# ITGC Review Lab: Northwind Retail

[![CI](https://github.com/Deepak-Varikuppala/itgc-review-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/Deepak-Varikuppala/itgc-review-lab/actions/workflows/ci.yml)

An IT general controls review of a small company, carried out the way an IT auditor would. It covers the three ITGC areas: logical access, change management and IT operations. For each area, the controls are scoped against the company's own policies and the test procedures are written before testing begins. Each control is tested on evidence that can be re-performed, using the whole population or a documented sample, and the findings are reported with risk ratings and followed through to a remediation retest.

The company, Northwind Retail, is fictional. Its systems are real, running in a virtual machine lab with deliberate control weaknesses for the review to find:

* a Samba Active Directory domain controller for `northwind.internal`
* an Ubuntu application server joined to that domain. It runs Gitea, where developers review and merge code; the finance application that pays suppliers; and its nightly backups.

## Results

**IT general controls were not operating effectively in Q3 2026.** Of 32 controls tested, 2 operated without exception. The review raised 22 findings: 12 high, 9 medium and 1 low.

| Area | Tests | Effective | Findings |
|---|---|---|---|
| Logical access: directory | AC-01 to AC-14 | 1 of 14 | F1 to F10 |
| Logical access: servers | AC-15 to AC-18 | 0 of 4 | F17, F18, and confirms F2, F5, F8 |
| Change management | CM-01 to CM-07 | 0 of 7 | F11 to F16 |
| IT operations | OP-01 to OP-07 | 1 of 7 | F19 to F22 |

A few of the findings:

* A leaver's account could still approve supplier payments (F1).
* Five changes went live without a code review, and a developer deployed his own changes eight times (F11, F12).
* A contractor changed the payments code six weeks after his contract ended (F16).
* A supplier's account and a developer both have full administrator rights on the production server, outside every change control (F17).
* The finance database went four days without a backup, and nobody noticed (F19).

**Read the reports:**

* [report/itgc-summary.md](report/itgc-summary.md): all 22 findings and their status
* [report/logical-access-review.md](report/logical-access-review.md): the directory, with a remediation retest
* [report/change-and-operations-review.md](report/change-and-operations-review.md): change management, IT operations and server access

**Every item tested:** [logical access workpaper](workpapers/logical-access-workpaper.xlsx) and [change and operations workpaper](workpapers/change-operations-workpaper.xlsx).

## How the review was done

1. **Criteria.** Northwind's [Access Control Policy](scenario/northwind-access-control-policy.md) and [Change Management and IT Operations Standard](scenario/northwind-change-and-operations-standard.md) set the rules. Examples: leavers are disabled within 1 working day; code reaches the main branch only through a reviewed pull request; developers never deploy their own changes; a restore is tested every quarter. Every test traces back to a clause.
2. **Test plan first.** The procedures, the evidence needed and the sampling method were written down before any evidence was collected: [docs/test-plan-change-and-operations.md](docs/test-plan-change-and-operations.md). The commit history shows the order.
3. **Evidence.** Read only collectors extracted the evidence from each system: [`collect_evidence.py`](audit/collect_evidence.py) for the directory, [`collect_app_evidence.py`](audit/collect_app_evidence.py) for Gitea, deployments and backups, and [`collect_host_evidence.py`](audit/collect_host_evidence.py) for each Linux server. Each extraction is checked for completeness, with record counts reconciled to the source (for example, commits on main against both Gitea's records and the deployment log). It is also checked for integrity with SHA-256 hashes, which you can verify with `shasum -a 256 -c SHA256SUMS`.
4. **Whole populations and samples.** Where a test compares system records without judgement, every item is tested: every deployment, every commit, every night's backup, every sudo rule. Where each item has to be read and judged, a random sample is taken instead. For change tickets (CM-04) and the user access review against the role matrix (AC-18), 15 items were selected with a recorded seed, so anyone can repeat the selection. Sample sizes follow a stated table, and one exception means the control is not relied on.
5. **Design and operating effectiveness.** These are assessed separately. For example, branch protection requires an approval on paper (design), but in practice it let changes through without one.
6. **Reporting.** Each finding sets out condition, criteria, cause, effect and recommendation, in plain language for a reader outside IT. Each test is mapped to ISO/IEC 27001:2022 Annex A and CIS Controls v8.1. The reports and testing programmes are generated from the same results as the workpapers, so they cannot disagree.
7. **Remediation and retest.** The logical access findings were fixed on the domain controller and then retested on a fresh extraction ([workpapers/remediation-retest.md](workpapers/remediation-retest.md)). The retest checks each finding's condition directly. That is a different question from rerunning the period tests, which would still report events that happened during the period.

## Repository layout

```
scenario/     the company's policies and records given to the auditor
lab/dc/       builds the domain controller's directory, and applies remediation
lab/app/      builds the application server and recreates its Q3 history
audit/        evidence collectors, tests, findings, workpapers, reports and retest
evidence/     extractions from each system, each with SHA256SUMS
workpapers/   the Excel workpapers and machine readable results
report/       the review reports
docs/         the test plan, testing programmes and fieldwork notes
tests/        tests for the audit scripts themselves
```

## Reproducing it

The tests and reports run from the committed evidence, without the lab:

```bash
pip install openpyxl
python3 audit/run_tests.py --evidence evidence/directory-20261027T030229Z
python3 audit/run_change_ops_tests.py --app evidence/app-20261028T015418Z \
    --host evidence/host-linux-20261028T015420Z --host evidence/host-linux2-20261028T015418Z \
    --directory evidence/directory-20261027T030229Z
python3 audit/make_report.py
```

To build the lab, follow [lab/README.md](lab/README.md), then [audit/README.md](audit/README.md) to collect evidence.

## Limitations

This is a lab. The weaknesses were seeded deliberately, and the application server's Q3 history was recreated when it was built, through Gitea itself, and dated to when each event happened. Directory creation and last logon dates reflect when the lab was built. The office PC was not in service during fieldwork, so the review covers the directory and the two Linux servers. Each report sets out its limitations in full, and [docs/fieldwork-notes.md](docs/fieldwork-notes.md) records what happened during fieldwork.
