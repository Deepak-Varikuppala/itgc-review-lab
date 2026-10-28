# Testing programme: change management, IT operations and server access

Generated from the test definitions in `audit/run_change_ops_tests.py`, which implement the [test plan](test-plan-change-and-operations.md) written before testing began. The criteria are the Change Management and IT Operations Standard (Standard) and the Access Control Policy (Policy).

| Test | Control | Criteria | Type | Sample | ISO/IEC 27001:2022 | CIS Controls v8.1 |
|---|---|---|---|---|---|---|
| AC-15 | Only authorised people can sign in to the servers | Standard 5.1 | Design and operating effectiveness | Whole population | A.5.15 Access control; A.5.16 Identity management | 5.1 Inventory of accounts; 6.7 Centralise access control |
| AC-16 | Administrator rights on the servers are limited to IT-Server-Admins | Standard 5.2 | Operating effectiveness | Whole population | A.8.2 Privileged access rights | 5.4 Restrict administrator privileges; 6.8 Role based access |
| AC-17 | SSH settings on the servers meet the Standard | Standard 5.3 | Design | Whole population | A.8.9 Configuration management; A.8.5 Secure authentication | 4.1 Secure configuration process |
| AC-18 | Each person's access matches their job (sample) | Policy 3.1, 6.1, 6.3; Standard 3.8 | Operating effectiveness | 15 of 22, selected with random.Random(20261001).sample() | A.5.18 Access rights; A.5.3 Segregation of duties | 6.8 Role based access |
| CM-01 | Every deployment to production has a change ticket | Standard 3.1 | Operating effectiveness | Whole population | A.8.32 Change management | 16.1 Secure application development process |
| CM-02 | Code reaches main only through an approved pull request | Standard 3.4 | Operating effectiveness | Whole population | A.8.32 Change management; A.8.4 Access to source code | 16.1 Secure application development process |
| CM-03 | Nobody deploys their own change | Standard 3.5; Policy 6.3 | Operating effectiveness | Whole population | A.5.3 Segregation of duties; A.8.31 Separation of environments | 16.1 Secure application development process |
| CM-04 | Changes are approved and tested before deployment (sample) | Standard 3.2, 3.3 | Operating effectiveness | 15 of 40, selected with random.Random(20261001).sample() | A.8.32 Change management; A.8.29 Security testing | 16.1 Secure application development process |
| CM-05 | Emergency changes follow the emergency procedure | Standard 3.6 | Operating effectiveness | Whole population | A.8.32 Change management | 16.1 Secure application development process |
| CM-06 | Branch protection and the deployment tool are set up as required | Standard 3.7 | Design | Whole population | A.8.32 Change management; A.8.9 Configuration management | 16.1 Secure application development process; 4.1 Secure configuration process |
| CM-07 | Only current developers can change code, and only non developers can deploy | Standard 3.8 | Operating effectiveness | Whole population | A.8.4 Access to source code; A.5.18 Access rights | 6.2 Access revoking process; 6.8 Role based access |
| OP-01 | The finance database was backed up every night | Standard 4.1 | Operating effectiveness | Whole population | A.8.13 Information backup | 11.2 Automated backups |
| OP-02 | Failed and missed backups were followed up | Standard 4.2 | Operating effectiveness | Whole population | A.8.13 Information backup; A.8.16 Monitoring activities | 11.2 Automated backups |
| OP-03 | Restores were tested in the quarter | Standard 4.3 | Operating effectiveness | Whole population | A.8.13 Information backup | 11.5 Test data recovery |
| OP-04 | The backup job is designed as required | Standard 4.1, 4.2, 4.4 | Design | Whole population | A.8.13 Information backup | 11.1 Data recovery process |
| OP-05 | Only approved jobs are scheduled on the servers | Standard 4.5 | Operating effectiveness | Whole population | A.8.9 Configuration management; A.8.19 Software on operational systems | 4.1 Secure configuration process |
| OP-06 | Server clocks are synchronised | Standard 4.6 | Operating effectiveness | Whole population | A.8.17 Clock synchronisation | 8.4 Standardise time synchronisation |
| OP-07 | Security updates are installed | Standard 4.7 | Design and operating effectiveness | Whole population | A.8.8 Management of technical vulnerabilities | 7.3 Automated operating system patch management |

## AC-15: Only authorised people can sign in to the servers

**Criteria:** Standard 5.1  
**ISO/IEC 27001:2022:** A.5.15 Access control; A.5.16 Identity management  
**CIS Controls v8.1:** 5.1 Inventory of accounts; 6.7 Centralise access control  
**Test type:** Design and operating effectiveness

**Control objective.** Nobody can sign in to a server except IT staff with their own domain account, and the emergency administrator account.

**Procedure.** Confirm the app server only lets members of GG-IT sign in with domain accounts. List every local account on each server that can sign in (a login shell and a usable password or SSH key). Each must be the emergency administrator account with an exception in the register, or an account that cannot sign in.

**Population.** Every local account on both Linux servers, and the domain sign in setting on the app server.

**Sample.** None: every item was tested.

## AC-16: Administrator rights on the servers are limited to IT-Server-Admins

**Criteria:** Standard 5.2  
**ISO/IEC 27001:2022:** A.8.2 Privileged access rights  
**CIS Controls v8.1:** 5.4 Restrict administrator privileges; 6.8 Role based access  
**Test type:** Operating effectiveness

**Control objective.** Full control of a server is held only by approved IT administrators, and every use of it asks for a password.

**Procedure.** For every sudo rule on each server, record who it covers and what it allows. Full rights are allowed only through IT-Server-Admins. Rights limited to the deployment tool are allowed for Change-Deployers. A rule granted to a person directly, or one that does not ask for a password, is an exception unless the exception register covers it.

**Population.** Every sudo rule on both Linux servers and every account it covers.

**Sample.** None: every item was tested.

## AC-17: SSH settings on the servers meet the Standard

**Criteria:** Standard 5.3  
**ISO/IEC 27001:2022:** A.8.9 Configuration management; A.8.5 Secure authentication  
**CIS Controls v8.1:** 4.1 Secure configuration process  
**Test type:** Design

**Control objective.** Remote access to the servers resists password guessing and misuse of idle or forwarded sessions.

**Procedure.** Compare each setting in the table in Standard 5.3 with the effective SSH configuration reported by sshd -T, which includes defaults and every included file.

**Population.** Both Linux servers, eight settings each.

**Sample.** None: every item was tested.

## AC-18: Each person's access matches their job (sample)

**Criteria:** Policy 3.1, 6.1, 6.3; Standard 3.8  
**ISO/IEC 27001:2022:** A.5.18 Access rights; A.5.3 Segregation of duties  
**CIS Controls v8.1:** 6.8 Role based access  
**Test type:** Operating effectiveness

**Control objective.** People hold only the access their job needs, across every system, and no one holds a combination of access that lets them complete a sensitive process alone.

**Procedure.** For each sampled person, gather their directory groups, their access to the code repository and their rights on the app server, and compare them with the role access matrix for their job. For anything beyond the matrix, look for an approved request and judge whether it is still needed and whether it combines duties that should be kept apart. Confirm the person is still employed.

**Population.** 22 enabled personal accounts in the directory at the end of the period.

**Sample.** 15 of 22, selected with random.Random(20261001).sample().

## CM-01: Every deployment to production has a change ticket

**Criteria:** Standard 3.1  
**ISO/IEC 27001:2022:** A.8.32 Change management  
**CIS Controls v8.1:** 16.1 Secure application development process  
**Test type:** Operating effectiveness

**Control objective.** Every change to production is recorded and can be traced to a request and approval.

**Procedure.** Match each deployment's ticket number to the service desk extract. A deployment with no ticket, or a ticket number that does not exist, is an exception.

**Population.** All 40 deployments between 1 July and 30 September 2026. Completeness: 40 commits were added to main in the period; 40 were deployed in the period, and every deployed commit is on main.

**Sample.** None: every item was tested.

## CM-02: Code reaches main only through an approved pull request

**Criteria:** Standard 3.4  
**ISO/IEC 27001:2022:** A.8.32 Change management; A.8.4 Access to source code  
**CIS Controls v8.1:** 16.1 Secure application development process  
**Test type:** Operating effectiveness

**Control objective.** Every change to the finance application's code is checked by a second person before it can be deployed.

**Procedure.** Match each commit added to main to the merged pull request that added it. Confirm the pull request had an approving review that counts towards approval, from someone other than its author, before it was merged. A commit with no pull request, or a pull request merged without such an approval, is an exception.

**Population.** All 40 commits added to main between 1 July and 30 September 2026.

**Sample.** None: every item was tested.

## CM-03: Nobody deploys their own change

**Criteria:** Standard 3.5; Policy 6.3  
**ISO/IEC 27001:2022:** A.5.3 Segregation of duties; A.8.31 Separation of environments  
**CIS Controls v8.1:** 16.1 Secure application development process  
**Test type:** Operating effectiveness

**Control objective.** No one can write a change and put it into production without another person being involved.

**Procedure.** Compare the person who ran each deployment with the author of the deployed commit. The same person is an exception.

**Population.** All 40 deployments between 1 July and 30 September 2026.

**Sample.** None: every item was tested.

## CM-04: Changes are approved and tested before deployment (sample)

**Criteria:** Standard 3.2, 3.3  
**ISO/IEC 27001:2022:** A.8.32 Change management; A.8.29 Security testing  
**CIS Controls v8.1:** 16.1 Secure application development process  
**Test type:** Operating effectiveness

**Control objective.** Only changes that the business has approved, and that have been tested, reach production.

**Procedure.** For each sampled deployment, inspect its change ticket and confirm: (a) the ticket exists and describes the change deployed; (b) it was approved by a member of Change-Approvers; (c) the approval came before the deployment; (d) testing is recorded on the ticket. Emergency changes are assessed against the emergency procedure in CM-05 instead of (c).

**Population.** All 40 deployments between 1 July and 30 September 2026.

**Sample.** 15 of 40, selected with random.Random(20261001).sample().

## CM-05: Emergency changes follow the emergency procedure

**Criteria:** Standard 3.6  
**ISO/IEC 27001:2022:** A.8.32 Change management  
**CIS Controls v8.1:** 16.1 Secure application development process  
**Test type:** Operating effectiveness

**Control objective.** Changes deployed in a hurry are still checked by a second person and approved and reviewed soon afterwards.

**Procedure.** For each emergency change, confirm a second person approved the code before it was deployed, the ticket was approved within 2 working days of deployment, and a post implementation review was recorded within 5 working days.

**Population.** All 2 emergency changes in the period.

**Sample.** None: every item was tested.

## CM-06: Branch protection and the deployment tool are set up as required

**Criteria:** Standard 3.7  
**ISO/IEC 27001:2022:** A.8.32 Change management; A.8.9 Configuration management  
**CIS Controls v8.1:** 16.1 Secure application development process; 4.1 Secure configuration process  
**Test type:** Design

**Control objective.** The tools enforce the change process, so it cannot be skipped by mistake or on purpose.

**Procedure.** Inspect the branch protection rule on main: one approval required, direct pushes blocked for everyone, administrators unable to override. Inspect the deployment tool: every deployment logged with commit, ticket and person, and whether it checks the ticket exists and is approved.

**Population.** The branch protection rule on main and the deployment tool.

**Sample.** None: every item was tested.

## CM-07: Only current developers can change code, and only non developers can deploy

**Criteria:** Standard 3.8  
**ISO/IEC 27001:2022:** A.8.4 Access to source code; A.5.18 Access rights  
**CIS Controls v8.1:** 6.2 Access revoking process; 6.8 Role based access  
**Test type:** Operating effectiveness

**Control objective.** Code and production can only be changed by people who should, and no one can both write code and deploy it.

**Procedure.** Match every account with write access or more to the code repository, and every account that can run the deployment tool, to the HR extract and contractor list. Compare each person's access with the role access matrix. A leaver or ended contractor with active access, a developer who can deploy, or a developer with administrator rights over the repository is an exception.

**Population.** Every Gitea account with write access or more, and every account that can run the deployment tool on the app server.

**Sample.** None: every item was tested.

## OP-01: The finance database was backed up every night

**Criteria:** Standard 4.1  
**ISO/IEC 27001:2022:** A.8.13 Information backup  
**CIS Controls v8.1:** 11.2 Automated backups  
**Test type:** Operating effectiveness

**Control objective.** A recent copy of the finance database is always available to restore from.

**Procedure.** For each night in the period, find the backup log entry. A failed run, or no entry at all, is an exception.

**Population.** All 92 nights between 1 July and 30 September 2026.

**Sample.** None: every item was tested.

## OP-02: Failed and missed backups were followed up

**Criteria:** Standard 4.2  
**ISO/IEC 27001:2022:** A.8.13 Information backup; A.8.16 Monitoring activities  
**CIS Controls v8.1:** 11.2 Automated backups  
**Test type:** Operating effectiveness

**Control objective.** Backup problems are noticed and fixed before the business needs a restore.

**Procedure.** For each failed or missed night, look for an incident raised by the end of the next working day, and a later successful backup.

**Population.** All 6 failed or missed nights from OP-01.

**Sample.** None: every item was tested.

## OP-03: Restores were tested in the quarter

**Criteria:** Standard 4.3  
**ISO/IEC 27001:2022:** A.8.13 Information backup  
**CIS Controls v8.1:** 11.5 Test data recovery  
**Test type:** Operating effectiveness

**Control objective.** The backups are known to work, because a restore from them has been tried.

**Procedure.** Look for a restore test in the period in the restore test log, and inspect its result.

**Population.** The restore test log, for 1 July to 30 September 2026.

**Sample.** None: every item was tested.

## OP-04: The backup job is designed as required

**Criteria:** Standard 4.1, 4.2, 4.4  
**ISO/IEC 27001:2022:** A.8.13 Information backup  
**CIS Controls v8.1:** 11.1 Data recovery process  
**Test type:** Design

**Control objective.** The backup job can produce, check and keep the backups the business needs, and makes failures visible.

**Procedure.** Inspect the scheduled job and the backup program: it runs nightly, writes a log line for success and for failure, records a checksum for each file, and removes files older than 30 days. Note whether anything alerts a person when a run fails.

**Population.** The backup job and program on the app server.

**Sample.** None: every item was tested.

## OP-05: Only approved jobs are scheduled on the servers

**Criteria:** Standard 4.5  
**ISO/IEC 27001:2022:** A.8.9 Configuration management; A.8.19 Software on operational systems  
**CIS Controls v8.1:** 4.1 Secure configuration process  
**Test type:** Operating effectiveness

**Control objective.** Nothing runs on a schedule on the servers that IT has not approved, and jobs that run as root cannot be changed by someone without root rights.

**Procedure.** Match every scheduled job not installed by an Ubuntu package to the job schedule. A job not on the schedule is an exception. For a job that runs as root, check the program it runs can only be changed by root.

**Population.** Every scheduled job on both Linux servers not installed with Ubuntu.

**Sample.** None: every item was tested.

## OP-06: Server clocks are synchronised

**Criteria:** Standard 4.6  
**ISO/IEC 27001:2022:** A.8.17 Clock synchronisation  
**CIS Controls v8.1:** 8.4 Standardise time synchronisation  
**Test type:** Operating effectiveness

**Control objective.** Every server keeps the correct time, so logs can be relied on and Kerberos sign in works.

**Procedure.** Confirm each server synchronises with a time source and was within 5 seconds of it when the evidence was collected. Consider anything seen during fieldwork that shows the clock was wrong at other times.

**Population.** Both Linux servers.

**Sample.** None: every item was tested.

## OP-07: Security updates are installed

**Criteria:** Standard 4.7  
**ISO/IEC 27001:2022:** A.8.8 Management of technical vulnerabilities  
**CIS Controls v8.1:** 7.3 Automated operating system patch management  
**Test type:** Design and operating effectiveness

**Control objective.** Known security weaknesses in the servers' software are fixed promptly.

**Procedure.** Confirm automatic security updates are switched on. List security updates still waiting to be installed when the evidence was collected. Any security update waiting for more than 14 days is an exception.

**Population.** Both Linux servers.

**Sample.** None: every item was tested.
