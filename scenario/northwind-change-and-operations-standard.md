# Northwind Retail: Change Management and IT Operations Standard

| | |
|---|---|
| Version | 1.4 |
| Owner | Head of IT (James Carter) |
| Approved by | Chief Executive |
| Approved on | 15 January 2026 |
| Next review | January 2027 |

## 1. Purpose and scope

This standard sets the rules for changing Northwind Retail's production systems and for running them day to day. It applies to the finance application and its code repository, to the servers that run the business (the domain controller and the application server) and to the office PC. It sits alongside the Access Control Policy, which covers access to the `northwind.internal` directory.

## 2. Responsibilities

| Role | Responsibility |
|---|---|
| Head of IT | Approves every change to production and every exception to this standard. Owns the job schedule |
| Systems Administrator | Runs the servers, the backups and patching, and deploys changes |
| Developers | Write and test changes to the finance application. Do not deploy their own changes |
| Reviewer | A developer or administrator other than the author who checks each change before it is merged |

## 3. Change management

**3.1 Change tickets.** Every change to production, whether to the finance application or to a server's configuration, needs a change ticket in the service desk before it is made. The ticket says what is changing, who asked for it, how it was tested and who approved it.

**3.2 Approval.** A member of the Change-Approvers group approves each normal change before it is deployed.

**3.3 Testing.** The ticket records the testing done, and this is in place before the change is approved.

**3.4 Code review.** Code reaches the `main` branch of the repository only through a pull request approved by someone other than its author. Nobody pushes directly to `main`.

**3.5 Segregation.** The person who deploys a change to production is never its author. This is the same rule as clause 6.3 of the Access Control Policy.

**3.6 Emergency changes.** When a fix cannot wait for approval it may be deployed first, but only if all of the following happen:

* a second person reviews the code before it is deployed;
* the change ticket is approved within 2 working days of the deployment; and
* a post implementation review is recorded on the ticket within 5 working days.

**3.7 Change tools.** Branch protection on `main` requires one approval, blocks direct pushes, and does not let administrators override it. The deployment tool records every deployment with the commit, the change ticket and the person who ran it.

**3.8 Access to change and deploy.** Write access to the code repository is limited to current developers, and administrator rights over it to the Head of IT. Rights to deploy to production are limited to members of Change-Deployers who do not write code. Access of leavers, and of contractors whose contract has ended, is removed within 1 working day, as in clauses 3.3 and 3.4 of the Access Control Policy.

## 4. IT operations

**4.1 Backups.** The finance database is backed up every night. Every run writes a line to the backup log, whether it succeeds or fails.

**4.2 Backup monitoring.** A failed or missing backup is followed up: an incident is raised in the service desk by the end of the next working day and the backup is run again successfully.

**4.3 Restore testing.** A restore from backup is tested at least once a quarter, and the result recorded in the restore test log.

**4.4 Backup design.** Backups are kept for 30 days, and each backup file has a recorded checksum so a restore can confirm it is complete.

**4.5 Scheduled jobs.** Only jobs on the job schedule may run on servers. Each job on the schedule has an owner and the Head of IT's approval. A job that runs as root may only run programs that only root can change. Jobs installed by Ubuntu packages as part of the standard server build are covered by that build and are not listed one by one.

**4.6 Time.** Every server and PC keeps its clock synchronised with a reliable time source, and stays within 5 seconds of it.

**4.7 Patching.** Security updates are installed on servers and PCs within 14 days of release. Automatic security updates are switched on.

## 5. Server and PC access

**5.1 Sign in.** Only IT staff may sign in to servers, using their own domain account. The only local account allowed to sign in is the built in administrator account kept for emergencies, which needs an entry in the exception register.

**5.2 Administrator rights.** Administrator rights on Linux servers are given only through membership of the IT-Server-Admins group. Rights given to a person directly, and rights that do not ask for a password, are not allowed without an exception.

**5.3 Remote access.** SSH on servers follows the settings below, taken from the CIS Ubuntu Linux Benchmark:

| Setting | Required value |
|---|---|
| `PermitRootLogin` | `no` |
| `PermitEmptyPasswords` | `no` |
| `MaxAuthTries` | 4 or fewer |
| `X11Forwarding` | `no` |
| `IgnoreRhosts` | `yes` |
| `HostbasedAuthentication` | `no` |
| `LoginGraceTime` | 60 seconds or less |
| `ClientAliveInterval` | between 1 and 900 seconds |

**5.4 PCs.** The local Administrators group on a PC holds only Domain Admins and the PC's built in Administrator account, which is disabled. IT support staff do not have administrator rights on PCs.

## 6. Exceptions

Exceptions to this standard are recorded in the same exception register as exceptions to the Access Control Policy, with a business reason, the Head of IT's approval, and a review date no more than 12 months away.
