# Scenario: Northwind Retail

Northwind Retail is a fictional retailer with about 25 staff. Its IT environment is a small lab built on two virtual machines, and an ITGC review is carried out against it.

## Audit period

**1 July 2026 to 30 September 2026** (Q3). Evidence was provided by the company on 1 October 2026.

## Evidence provided by the company

| File | What it is |
|---|---|
| [northwind-access-control-policy.md](northwind-access-control-policy.md) | The policy each control is tested against |
| [hr-extract-2026-10-01.csv](hr-extract-2026-10-01.csv) | Every employee from the HR system, with start, leave and transfer dates |
| [contractors-2026-10-01.csv](contractors-2026-10-01.csv) | Contractors and their contract dates |
| [access-requests.csv](access-requests.csv) | Approved requests for access to sensitive groups |
| [exception-register.csv](exception-register.csv) | Approved exceptions to the policy |

The live directory on the domain controller is the system under review. Read only extracts are taken from it during testing.

## Environment

| Host | Address | Role |
|---|---|---|
| `linux.northwind.internal` | 192.168.64.10 | Samba Active Directory domain controller for `northwind.internal` |
| `app01` | to be built | Finance application, change management (Gitea) and backups |

The company, its people and its data are fictional.

## Lab limitations

* Accounts were created when the lab was built, so the creation date shown in the directory is the build date, not the HR start date. HR start dates are the reliable record.
* Last logon dates come from sign-ins made when the lab was built.
