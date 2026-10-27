# Scenario: Northwind Retail

Northwind Retail is a fictional retailer with about 25 staff. Its IT environment is a small lab of virtual machines: two Linux servers and a Windows PC. An ITGC review is carried out against it.

## Audit period

**1 July 2026 to 30 September 2026** (Q3). Evidence was provided by the company on 1 October 2026.

## Evidence provided by the company

| File | What it is |
|---|---|
| [northwind-access-control-policy.md](northwind-access-control-policy.md) | The policy each control is tested against |
| [hr-extract-2026-10-01.csv](hr-extract-2026-10-01.csv) | Every employee from the HR system, with start, leave and transfer dates |
| [contractors-2026-10-01.csv](contractors-2026-10-01.csv) | Contractors and their contract dates |
| [access-requests.csv](access-requests.csv) | Approved requests for access to sensitive groups |
| [exception-register.csv](exception-register.csv) | Approved exceptions to the policy and the standard |
| [northwind-change-and-operations-standard.md](northwind-change-and-operations-standard.md) | The standard for change management, IT operations and server access |
| [change-tickets.csv](change-tickets.csv) | Change tickets raised in the service desk for changes in the period |
| [incidents.csv](incidents.csv) | Incidents raised in the service desk in the period |
| [restore-tests.csv](restore-tests.csv) | The log of backup restore tests |
| [job-schedule.csv](job-schedule.csv) | Scheduled jobs approved to run on the servers |
| [role-access-matrix.csv](role-access-matrix.csv) | The access each job needs |

The live systems are the domain controller's directory, Gitea and the application server, the two Linux servers and the office PC. Read only extracts are taken from them during testing.

## Environment

| Host | Address | Role |
|---|---|---|
| `linux.northwind.internal` | 192.168.64.10 | Samba Active Directory domain controller for `northwind.internal` |
| `linux2.northwind.internal` | 192.168.64.11 | Finance application, its code repository (Gitea) and backups |
| `NW-PC01` | to be built | Windows 11 office PC joined to the domain |

The company, its people and its data are fictional.

## Lab limitations

* Accounts were created when the lab was built, so the creation date shown in the directory is the build date, not the HR start date. HR start dates are the reliable record.
* Last logon dates come from sign-ins made when the lab was built.
* The application server was built after the audit period. Its Q3 history (pull requests, reviews, merges, deployments and backup runs) was recreated when it was built, from `lab/app/history.py`, and dated to when each event happened. See [lab/README.md](../lab/README.md).
