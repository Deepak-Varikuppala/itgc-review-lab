# Test plan: change management, IT operations and server access

Written before any evidence was collected from the application server or the office PC, and before testing began. It sets out, for each control, the procedure and the evidence needed, how the population is confirmed as complete, and whether every item is tested or a sample is taken.

The criteria are Northwind's [Change Management and IT Operations Standard](../scenario/northwind-change-and-operations-standard.md) (the Standard) and, where stated, its [Access Control Policy](../scenario/northwind-access-control-policy.md) (the Policy). The audit period is 1 July to 30 September 2026, as for the logical access tests AC-01 to AC-14.

> **Scope change, 28 October 2026.** The office PC had not been put into service when fieldwork took place, so AC-15, AC-16, OP-06 and OP-07 were performed on the two Linux servers only. The PC will be reviewed once it is in service. See the [fieldwork notes](fieldwork-notes.md).

## Scope

| System | Where | What is tested |
|---|---|---|
| Finance application code repository (Gitea) | Application server `linux2`, 192.168.64.11 | Pull requests, reviews, branch protection, accounts and access |
| Finance application in production | Application server | Deployments, deployment tool, who can deploy |
| Finance database backups | Application server | Backup log, backup job, restore tests |
| Linux servers | `linux` (domain controller) and `linux2` | Sign in, administrator rights, SSH, scheduled jobs, time, patching |
| Office PC (Windows 11) | `NW-PC01`, joined to the domain | Local administrators, local accounts, time, patching |

## Evidence

| Evidence | Collected by | Notes |
|---|---|---|
| Gitea accounts, repository access, pull requests, reviews, branch protection, updates to `main` | `audit/collect_app_evidence.py` on the app server | Gitea's database opened read only |
| Commits on `main` | the same | `git log --first-parent main` on the repository Gitea serves |
| Deployment log, deployment tool, production release | the same | The deployment log is the population of production changes |
| Backup log, backup job, backup files | the same | |
| Local accounts, sudo rules, SSH settings, sign in restrictions, scheduled jobs, time, patch status | `audit/collect_host_evidence.py` on each Linux server | |
| Local administrators, local accounts, time, patch status | `audit/collect_pc_evidence.ps1` on the PC | |
| Change tickets, incidents, restore tests, job schedule, role access matrix, exception register | Provided by Northwind (`scenario/`) | Service desk and IT records |

Every extraction records who ran it, when, on which host, each command or query, and record counts, and is hashed with SHA-256. Tests do not run on evidence whose hashes do not match.

## Whole populations and samples

Where a test compares system records with each other or with a rule, and the comparison can be done by a script without judgement, every item in the population is tested. Examples are matching deployments to tickets, or checking the deployer is not the author.

Where each item needs a person to read a document and judge it, a sample is taken. These are CM-04, where each sampled change ticket is read to confirm it describes the change, was approved by an authorised person in time and records testing; and AC-18, where each sampled person's access across every system is compared with what their job needs.

**Sample size.** These controls operate when needed rather than on a fixed schedule, so the sample size depends on how many times the control operated in the period:

| Items in the population | Sample size |
|---|---|
| 1 to 4 | All of them |
| 5 to 12 | 5 |
| 13 to 52 | 15 |
| 53 to 250 | 25 |
| More than 250 | 40 |

**Selection.** Items are selected at random, without replacement, using Python's `random.Random(20261001).sample()` over the population sorted by a stable key (deployment time, or username). The seed is recorded so anyone can repeat the selection and get the same items. The full population and the selected items are both listed in the workpaper.

**Evaluating a sample.** These are key controls, so no exceptions are tolerated. One exception in a sample means the control is not relied on for the period, and its cause is investigated. Sample results are not projected to the population as a number.

## Server and PC access

### AC-15: Only authorised people can sign in to servers and the PC

**Criteria:** Standard 5.1. **Type:** design and operating effectiveness. **Population:** every local account on both Linux servers and on the PC (all tested), and the domain sign in restriction on the app server.

**Procedure.** Confirm the app server only lets members of GG-IT sign in with domain accounts. List every local account that can sign in (a login shell and a usable password or SSH key). Each must be the built in emergency administrator account with an exception in the register, or a system account that cannot sign in. Any other account is an exception, with its creation or last password change date as the date it appeared.

**Evidence.** `local-accounts.csv`, `domain-sign-in.txt`, PC `local-accounts.csv`, exception register.

### AC-16: Administrator rights on servers and the PC are limited to IT-Server-Admins

**Criteria:** Standard 5.2 and 5.4; Policy 5.4. **Type:** operating effectiveness. **Population:** every sudo rule on both Linux servers and every account it covers, and every member of the PC's local Administrators group (all tested).

**Procedure.** For each sudo rule, record who it covers and what it allows. Full rights are allowed only through IT-Server-Admins. Limited rights (the deployment tool for Change-Deployers) are allowed if limited to that command. A rule granted to a person directly, or one that does not ask for a password, is an exception unless the exception register covers it. On the PC, any member of local Administrators other than Domain Admins and the disabled built in Administrator is an exception.

**Evidence.** `sudo-rules.csv`, `sudoers.txt` (with file dates), `local-groups.csv`, PC `local-administrators.csv`, exception register.

### AC-17: SSH settings meet the Standard

**Criteria:** Standard 5.3 (CIS Ubuntu Linux Benchmark settings). **Type:** design. **Population:** both Linux servers.

**Procedure.** Compare each setting in the table in Standard 5.3 with the effective SSH configuration reported by `sshd -T`, which includes defaults and every included file.

**Evidence.** `sshd-effective.txt` from each server.

### AC-18: Each person's access matches their job (sample)

**Criteria:** Policy 3.1, 6.1 and 6.3; Standard 3.8; role access matrix. **Type:** operating effectiveness. **Population:** every enabled personal account in the directory at the end of the period (22 accounts). **Sample:** 15, selected as above.

**Procedure.** For each sampled person, gather all their access: directory groups, Gitea access, and server administrator or deployment rights. Compare it with the role access matrix for their job title. For anything beyond the matrix, look for an approved access request and judge whether the access is still needed (least privilege), and whether it combines duties that should be kept apart (segregation of duties). Record the evidence behind each conclusion.

**Evidence.** Directory extract (`users.csv`, `group-members.csv`), `gitea-repo-access.csv`, `sudo-rules.csv`, `role-access-matrix.csv`, `access-requests.csv`, HR extract.

## Change management

The population for change management is every deployment to production in the period, from the deployment log. Its completeness is checked against the repository: every commit added to `main` in the period must appear in a deployment or still be waiting for one, and every deployed commit must be on `main`.

### CM-01: Every deployment to production has a change ticket

**Criteria:** Standard 3.1. **Type:** operating effectiveness. **Population:** every deployment in the period (all tested).

**Procedure.** Match each deployment's ticket number to the service desk extract. A deployment with no ticket, or with a ticket number that does not exist, is an exception.

**Evidence.** `deployments.log`, `change-tickets.csv`.

### CM-02: Code reaches main only through an approved pull request

**Criteria:** Standard 3.4. **Type:** operating effectiveness. **Population:** every commit added to `main` in the period (all tested).

**Procedure.** Match each commit to the merged pull request that added it. Confirm the pull request had an approving review that counts towards approval, from someone other than its author, submitted before the merge. A commit with no pull request (pushed directly), or a pull request merged without such an approval, is an exception. Record who pushed or merged.

**Evidence.** `git-main-commits.csv`, `gitea-pull-requests.csv`, `gitea-reviews.csv`, `gitea-main-updates.csv`.

### CM-03: Nobody deploys their own change

**Criteria:** Standard 3.5; Policy 6.3. **Type:** operating effectiveness. **Population:** every deployment in the period (all tested).

**Procedure.** Compare the person who ran each deployment with the author of the deployed commit. The same person is an exception.

**Evidence.** `deployments.log`, `git-main-commits.csv`.

### CM-04: Changes are approved and tested before deployment (sample)

**Criteria:** Standard 3.2 and 3.3. **Type:** operating effectiveness. **Population:** every deployment in the period. **Sample:** 15, selected as above.

**Procedure.** For each sampled deployment, inspect its change ticket and confirm: (a) the ticket exists and describes the change that was deployed; (b) it was approved by a member of Change-Approvers; (c) the approval came before the deployment; (d) testing is recorded on the ticket. Emergency changes in the sample are assessed against the emergency procedure in CM-05 instead of attribute (c).

**Evidence.** `change-tickets.csv`, `deployments.log`, `gitea-pull-requests.csv`, directory `group-members.csv` (Change-Approvers).

### CM-05: Emergency changes follow the emergency procedure

**Criteria:** Standard 3.6. **Type:** operating effectiveness. **Population:** every emergency change in the period (all tested).

**Procedure.** For each emergency change: confirm a second person approved the code before deployment; the ticket was approved within 2 working days of deployment; and a post implementation review was recorded within 5 working days.

**Evidence.** `change-tickets.csv`, `gitea-pull-requests.csv`, `gitea-reviews.csv`, `deployments.log`.

### CM-06: Branch protection and the deployment tool are set up as required

**Criteria:** Standard 3.7. **Type:** design.

**Procedure.** Inspect the branch protection rule on `main`: one approval required, direct pushes blocked for everyone, administrators unable to override. Inspect the deployment tool: every deployment logged with commit, ticket and person; and whether it checks the ticket exists and is approved.

**Evidence.** `gitea-branch-protection.json`, `deploy-tool.txt`.

### CM-07: Only current developers can change code, and only non developers can deploy

**Criteria:** Standard 3.8. **Type:** operating effectiveness. **Population:** every Gitea account with write access or more, and every account that can run the deployment tool (all tested).

**Procedure.** Match each account to the HR extract and contractor list. A leaver, or a contractor whose contract has ended, with active access is an exception; record their last sign in. Compare each person's level of access with the role access matrix. A developer who can deploy, or who has administrator rights over the repository, is an exception.

**Evidence.** `gitea-users.csv`, `gitea-repo-access.csv`, `sudo-rules.csv`, HR extract, contractor list, role access matrix.

## IT operations

### OP-01: The finance database was backed up every night

**Criteria:** Standard 4.1. **Type:** operating effectiveness. **Population:** every night in the period, 92 nights (all tested).

**Procedure.** For each night, find the backup log entry. A night with a failed run, or with no entry at all, is an exception.

**Evidence.** `backup.log`.

### OP-02: Failed and missed backups were followed up

**Criteria:** Standard 4.2. **Type:** operating effectiveness. **Population:** every exception from OP-01 (all tested).

**Procedure.** For each failed or missed night, look for an incident raised by the end of the next working day, and a later successful backup.

**Evidence.** `backup.log`, `incidents.csv`.

### OP-03: Restores were tested in the quarter

**Criteria:** Standard 4.3. **Type:** operating effectiveness.

**Procedure.** Look for a restore test in the period in the restore test log, and inspect its result.

**Evidence.** `restore-tests.csv`.

### OP-04: The backup job is designed as required

**Criteria:** Standard 4.1, 4.2 and 4.4. **Type:** design.

**Procedure.** Inspect the scheduled job and the backup program: it runs nightly, writes a log line for success and for failure, records a checksum for each file, and removes files older than 30 days. Note whether anything alerts a person when a run fails.

**Evidence.** `backup-job.txt`.

### OP-05: Only approved jobs are scheduled on servers

**Criteria:** Standard 4.5. **Type:** operating effectiveness. **Population:** every scheduled job on both Linux servers that was not installed by an Ubuntu package (all tested).

**Procedure.** Match each job to the job schedule. A job not on the schedule is an exception. For any job that runs as root, check that the program it runs can only be changed by root.

**Evidence.** `scheduled-jobs.csv` from each server, `job-schedule.csv`.

### OP-06: Clocks are synchronised

**Criteria:** Standard 4.6. **Type:** operating effectiveness. **Population:** both Linux servers and the PC.

**Procedure.** Confirm each machine synchronises with a time source and was within 5 seconds of it when the evidence was collected.

**Evidence.** `time-sync.txt` from each server, PC `time-sync.txt`.

### OP-07: Security updates are installed

**Criteria:** Standard 4.7. **Type:** design and operating effectiveness. **Population:** both Linux servers and the PC.

**Procedure.** Confirm automatic security updates are switched on. List security updates still waiting to be installed when the evidence was collected, and when updates were last installed. Any security update waiting for more than 14 days is an exception.

**Evidence.** `patching.txt` from each server, PC `patching.txt`.

## Framework mapping

| Test | ISO/IEC 27001:2022 Annex A | CIS Controls v8.1 |
|---|---|---|
| AC-15 | A.5.15 Access control; A.5.16 Identity management | 5.1 Inventory of accounts; 6.7 Centralise access control |
| AC-16 | A.8.2 Privileged access rights | 5.4 Restrict administrator privileges; 6.8 Role based access |
| AC-17 | A.8.9 Configuration management; A.8.5 Secure authentication | 4.1 Secure configuration process |
| AC-18 | A.5.18 Access rights; A.5.3 Segregation of duties | 6.8 Role based access |
| CM-01 | A.8.32 Change management | 16.1 Secure application development process |
| CM-02 | A.8.32 Change management; A.8.4 Access to source code | 16.1 Secure application development process |
| CM-03 | A.5.3 Segregation of duties; A.8.31 Separation of environments | 16.1 Secure application development process |
| CM-04 | A.8.32 Change management; A.8.29 Security testing | 16.1 Secure application development process |
| CM-05 | A.8.32 Change management | 16.1 Secure application development process |
| CM-06 | A.8.32 Change management; A.8.9 Configuration management | 16.1 Secure application development process; 4.1 Secure configuration process |
| CM-07 | A.8.4 Access to source code; A.5.18 Access rights | 6.2 Access revoking process; 6.8 Role based access |
| OP-01 | A.8.13 Information backup | 11.2 Automated backups |
| OP-02 | A.8.13 Information backup; A.8.16 Monitoring activities | 11.2 Automated backups |
| OP-03 | A.8.13 Information backup | 11.5 Test data recovery |
| OP-04 | A.8.13 Information backup | 11.1 Data recovery process |
| OP-05 | A.8.9 Configuration management; A.8.19 Software on operational systems | 4.1 Secure configuration process |
| OP-06 | A.8.17 Clock synchronisation | 8.4 Standardise time synchronisation |
| OP-07 | A.8.8 Management of technical vulnerabilities | 7.3 Automated operating system patch management |
