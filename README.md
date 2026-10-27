# ITGC Review Lab: Northwind Retail

[![CI](https://github.com/Deepak-Varikuppala/itgc-review-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/Deepak-Varikuppala/itgc-review-lab/actions/workflows/ci.yml)

An IT general controls review of a small company's Active Directory, carried out the way an IT auditor would: scoped against the company's own policy, tested on the whole population with evidence that can be re-performed, reported as findings with risk ratings, and followed through to a remediation retest.

The company, Northwind Retail, is fictional. Its domain runs on a real Samba Active Directory domain controller in a virtual machine lab, with deliberate control weaknesses for the review to find.

## Results

**Logical access controls were not operating effectively in Q3 2026.** Of 14 controls tested, 1 operated without exception. The review raised 10 findings: 5 high, 4 medium and 1 low.

| | Finding | Rating |
|---|---|---|
| F1 | A leaver's account was still active and able to approve payments | High |
| F2 | Full domain administrator rights were held without approval | High |
| F3 | A shared account can create supplier payments | High |
| F4 | A member of staff kept payment access after moving to Sales | Medium |
| F5 | A contractor's account stayed active after the contract ended | Medium |
| F6 | The password and lockout settings are weaker than policy | High |
| F7 | Passwords set never to expire without approval | Medium |
| F8 | One person can create and approve payments, and approved that access herself | High |
| F9 | An unused service account | Low |
| F10 | Quarterly access reviews could not be evidenced | Medium |

**Read the report:** [report/logical-access-review.md](report/logical-access-review.md)
**Every item tested:** [workpapers/logical-access-workpaper.xlsx](workpapers/logical-access-workpaper.xlsx)

## How the review was done

1. **Criteria.** Northwind's [access control policy](scenario/northwind-access-control-policy.md) sets the rules: leavers disabled within 1 working day, 12 character passwords, no shared accounts, segregation of payment duties and so on. Every test traces back to a clause.
2. **Evidence.** Directory data was extracted read only by [`audit/collect_evidence.py`](audit/collect_evidence.py), then checked for completeness (record counts in the raw output match the processed listing) and integrity (SHA-256 hashes, verifiable with `shasum -a 256 -c SHA256SUMS`).
3. **Testing.** [`audit/run_tests.py`](audit/run_tests.py) runs 14 tests against the evidence and the company's HR extract, contractor list, access request log and exception register. Each test covers its whole population, and records why every item passed or failed. Two tests assess design; twelve assess operating effectiveness. Each test is mapped to ISO/IEC 27001:2022 Annex A and CIS Controls v8.1. Procedures and mapping: [docs/testing-programme.md](docs/testing-programme.md).
4. **Reporting.** Each finding sets out condition, criteria, cause, effect and recommendation ([`audit/findings.py`](audit/findings.py)). The report and testing programme are generated from the same data as the workpaper, so they cannot disagree.
5. **Remediation and retest.** [`lab/dc/remediate.sh`](lab/dc/remediate.sh) applies the agreed fixes. [`audit/retest.py`](audit/retest.py) then checks each finding's condition directly in a fresh extraction. That is a different question from rerunning the period tests, which would still report events that happened during the period.

## Repository layout

```
scenario/     the company's policy and records given to the auditor
lab/dc/       builds the domain controller's directory, and applies remediation
audit/        evidence collection, tests, findings, workpaper, report and retest
evidence/     extractions from the domain controller, each with SHA256SUMS
workpapers/   the Excel workpaper and machine readable results
report/       the review report
docs/         the testing programme
tests/        tests for the audit scripts themselves
```

## Reproducing it

The tests and report run from the committed evidence, without the lab:

```bash
pip install openpyxl
python3 audit/run_tests.py --evidence evidence/directory-20261027T030229Z
python3 audit/make_report.py
```

To build the lab, create an Ubuntu Server VM, set it up as a Samba AD domain controller for `northwind.internal`, then follow [lab/README.md](lab/README.md) and [audit/README.md](audit/README.md).

## Limitations

This is a lab. The weaknesses were seeded deliberately, account creation dates reflect when the lab was built, and last logon dates come from sign ins made during the build. These are set out in section 7 of the report.

## Next phase

Change management (pull request approval and segregation between developers and deployers) and IT operations (backups, restore testing and time synchronisation) on an application server joined to the domain.
