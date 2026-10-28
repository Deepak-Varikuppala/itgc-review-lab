# Northwind Retail: Change Management, IT Operations and Server Access Review

| | |
|---|---|
| Entity | Northwind Retail (fictional company, lab environment) |
| Systems | Finance application and its code repository (Gitea) on `linux2`; Linux servers `linux` (domain controller) and `linux2` (application server) |
| Audit period | 1 July 2026 to 30 September 2026 |
| Evidence extracted | 2026-10-28 |
| Criteria | Northwind Retail Change Management and IT Operations Standard v1.4; Access Control Policy v2.1 |
| Prepared by | Deepak Kumar Varikuppala |
| Status | Issued for management response |

## 1. Summary

**Overall conclusion: change management, IT operations and server access controls were not operating effectively during the period.**

Of 18 controls tested, 1 operated without exception and 17 had exceptions. The review raised 12 findings: 7 high and 5 medium. They are numbered on from the ten findings of the logical access review ([report](logical-access-review.md)), which covers the same period.

Four themes explain the findings:

1. **The change process can be skipped, and was.** Branch protection lets one developer push straight to the main branch and lets administrators merge without approval, and the deployment tool does not need a ticket. Five of 40 changes went live without review, three of them with no ticket (F11, F15, F14).
2. **The people who write the code also put it live.** A developer deployed his own changes 8 times, and both people who write code can deploy. A contractor whose contract had ended still had access and changed the code (F12, F16).
3. **Administrator access on the production server was given in a hurry and never taken back.** A supplier's account and a developer both have full control, and an unapproved job gives the same developer a hidden route to it (F17, F21).
4. **Backups failed without anyone noticing, and restores were not tested.** The finance database went four days without a backup in August (F19, F20).

Some controls worked. Most sampled changes were approved and tested before going live, one of the two emergency changes followed the procedure in full, security updates were up to date on both servers, and sign in to the app server is limited to IT staff.

The most urgent actions are to remove the support account and the developer's administrator rights from the app server, remove the unapproved scheduled job, block direct changes to the main branch, disable the former contractor's Gitea account, and alert on backup failures.

## 2. Scope and approach

The review covered three areas over the finance application and the servers it depends on: change management (how code changes are reviewed, approved and deployed), IT operations (backups, restore testing, scheduled jobs, time and patching), and access to the servers themselves. The procedures, the evidence required and the sampling method were set out in the [test plan](../docs/test-plan-change-and-operations.md) before any evidence was collected.

Evidence was extracted read only by scripted collectors: from Gitea's database and repository and the app server's logs (`audit/collect_app_evidence.py`), and from each Linux server (`audit/collect_host_evidence.py`). Each extraction was checked for **completeness**, for example the number of pull requests in the database against the rows exported, and the commits on main against both Gitea's records and the deployment log, and for **integrity** by SHA-256 hashes. Evidence folders: `evidence/app-20261028T015418Z`, `evidence/host-linux-20261028T015420Z`, `evidence/host-linux2-20261028T015418Z`, `evidence/directory-20261027T030229Z`.

Where a test compares system records with each other or with a rule, every item in the population was tested. Where each item had to be read and judged, a random sample was taken: AC-18, CM-04. The sample size comes from the table in the test plan, and the items were selected with `random.Random(20261001).sample()` so the selection can be repeated. Because these are key controls, one exception in a sample means the control is not relied on. The population and the selected items are on the Samples sheet of [the workpaper](../workpapers/change-operations-workpaper.xlsx), and the full procedures are in [docs/testing-programme-change-and-operations.md](../docs/testing-programme-change-and-operations.md).

Each test is mapped to ISO/IEC 27001:2022 Annex A and CIS Controls v8.1.

## 3. Results by control

| Test | Control | Criteria | Tested | Exceptions | Conclusion |
|---|---|---|---|---|---|
| AC-15 | Only authorised people can sign in to the servers and the PC | Standard 5.1, 5.4 | 4 | 1 | Not operating effectively (1 exception in 4 tested) |
| AC-16 | Administrator rights on the servers and the PC are limited as required | Standard 5.2, 5.4 | 12 | 2 | Not operating effectively (2 exceptions in 12 tested) |
| AC-17 | SSH settings on the servers meet the Standard | Standard 5.3 | 16 | 10 | Design deficiency (10 exceptions in 16 tested) |
| AC-18 | Each person's access matches their job (sample) | Policy 3.1, 6.1, 6.3; Standard 3.8 | 15 (sample) | 4 | Not operating effectively (4 exceptions in 15 tested) |
| CM-01 | Every deployment to production has a change ticket | Standard 3.1 | 40 | 3 | Not operating effectively (3 exceptions in 40 tested) |
| CM-02 | Code reaches main only through an approved pull request | Standard 3.4 | 40 | 5 | Not operating effectively (5 exceptions in 40 tested) |
| CM-03 | Nobody deploys their own change | Standard 3.5; Policy 6.3 | 40 | 8 | Not operating effectively (8 exceptions in 40 tested) |
| CM-04 | Changes are approved and tested before deployment (sample) | Standard 3.2, 3.3 | 15 (sample) | 2 | Not operating effectively (2 exceptions in 15 tested) |
| CM-05 | Emergency changes follow the emergency procedure | Standard 3.6 | 2 | 1 | Not operating effectively (1 exception in 2 tested) |
| CM-06 | Branch protection and the deployment tool are set up as required | Standard 3.7 | 6 | 4 | Design deficiency (4 exceptions in 6 tested) |
| CM-07 | Only current developers can change code, and only non developers can deploy | Standard 3.8 | 7 | 4 | Not operating effectively (4 exceptions in 7 tested) |
| OP-01 | The finance database was backed up every night | Standard 4.1 | 92 | 6 | Not operating effectively (6 exceptions in 92 tested) |
| OP-02 | Failed and missed backups were followed up | Standard 4.2 | 6 | 5 | Not operating effectively (5 exceptions in 6 tested) |
| OP-03 | Restores were tested in the quarter | Standard 4.3 | 1 | 1 | Not operating effectively (1 exception in 1 tested) |
| OP-04 | The backup job is designed as required | Standard 4.1, 4.2, 4.4 | 5 | 1 | Design deficiency (1 exception in 5 tested) |
| OP-05 | Only approved jobs are scheduled on the servers | Standard 4.5 | 2 | 1 | Not operating effectively (1 exception in 2 tested) |
| OP-06 | Server and PC clocks are synchronised | Standard 4.6 | 2 | 1 | Not operating effectively (1 exception in 2 tested) |
| OP-07 | Security updates are installed | Standard 4.7 | 2 | 0 | Effective (no exceptions) |

AC-18 also found access already reported in the logical access review: Domain Admins rights without approval (F2), an ended contractor's enabled account (F5) and conflicting payment roles (F8).

## 4. Findings

| ID | Finding | Rating | Tests |
|---|---|---|---|
| [F11](#f11) | Changes reached production without a ticket or a code review | **High** | CM-01, CM-02 |
| [F12](#f12) | Developers deployed their own changes | **High** | CM-03, CM-07, AC-18 |
| [F13](#f13) | Changes were approved only after they were deployed | **Medium** | CM-04 |
| [F14](#f14) | An emergency change skipped the emergency procedure | **Medium** | CM-05 |
| [F15](#f15) | The change tools do not enforce the change process | **High** | CM-06, CM-02 |
| [F16](#f16) | A contractor changed the code after his contract ended | **High** | CM-07, AC-18 |
| [F17](#f17) | Unapproved administrator rights on the application server | **High** | AC-15, AC-16, AC-18 |
| [F18](#f18) | SSH settings on the servers are weaker than the Standard | **Medium** | AC-17 |
| [F19](#f19) | Backups failed or did not run on 6 nights, and 5 went unnoticed | **High** | OP-01, OP-02, OP-04 |
| [F20](#f20) | No restore was tested in the quarter | **Medium** | OP-03 |
| [F21](#f21) | An unapproved job runs a developer's script as root | **High** | OP-05 |
| [F22](#f22) | The domain controller's clock was found badly wrong twice | **Medium** | OP-06 |

### F11

**Changes reached production without a ticket or a code review**  
Rating: **High** | Criteria: Standard 3.1, 3.4 | Tests CM-01, CM-02

**Condition.** Five of the 40 changes added to the finance application in the period skipped part of the change process. Ryan Patel pushed four straight to main, with no pull request and no review: three quick fixes on 17 July, 21 August and 11 September, and the emergency fix on 23 September. He deployed each himself within 25 minutes, and the three quick fixes were deployed with no change ticket at all. Aisha Khan merged her own pull request #23 (Export approved payments to the bank file format, CHG-2026-0112) on 29 July without anyone approving it.

**Criteria.** Standard 3.1: every change to production needs a change ticket before it is made. Standard 3.4: code reaches main only through a pull request approved by someone other than its author, and nobody pushes directly to main.

**Cause.** The tools allow it (F15). Branch protection lets Ryan Patel push to main, and lets repository administrators merge without an approval. The deployment tool accepts a deployment with no ticket.

**Effect.** Code that nobody else has looked at is running in the application that pays suppliers, including a change to the bank payment file. An error or a deliberate change to payments in that code could go unnoticed.

**Recommendation.** Have someone other than the authors review the five changes now and record the review. Fix the tools as set out in F15 so the process cannot be skipped. Report any change deployed without a ticket to the Head of IT each week from the deployment log.

**Management response.** Pending.

### F12

**Developers deployed their own changes**  
Rating: **High** | Criteria: Standard 3.5, 3.8; Policy 6.3 | Tests CM-03, CM-07, AC-18

**Condition.** In 8 of the 40 deployments in the period, the person who deployed the change also wrote it. All eight were Ryan Patel's: four normal changes (14 July, 6 August, 1 September and 22 September), the three quick fixes and the 23 September emergency fix. Both people who write the finance application's code can deploy it: Ryan Patel, a Software Developer, is in Change-Deployers (REQ-2022-052) and owns the repository; Aisha Khan, the Systems Administrator, wrote 10 of the 40 changes and deploys.

**Criteria.** Standard 3.5 and Policy 6.3: the person who deploys a change is never its author. Standard 3.8: rights to deploy are limited to members of Change-Deployers who do not write code.

**Cause.** With two technical staff, deployment rights were given to both, and nothing stops an author deploying their own change or flags it afterwards. Ryan Patel's request for deployment rights was approved even though the role access matrix does not give them to developers.

**Effect.** One person can write a change to the payments application and put it live without anyone else being involved, which removes the main protection against unauthorised or mistaken changes.

**Recommendation.** Remove Ryan Patel from Change-Deployers. Make the deployment tool refuse to deploy a commit written by the person running it. While the team is too small for full separation, have the Head of IT review the deployment log against commit authors every week and sign off the review.

**Management response.** Pending.

### F13

**Changes were approved only after they were deployed**  
Rating: **Medium** | Criteria: Standard 3.2 | Tests CM-04

**Condition.** In the sample of 15 deployments, 2 were approved after they had gone live: CHG-2026-0109 (Add a health check endpoint for monitoring), deployed on 23 July and approved the next morning, and CHG-2026-0129 (Add a weekly supplier report), deployed on 15 September and approved two days later. The other 13 sampled changes met all four checks; one of them was an emergency change, assessed in CM-05.

**Criteria.** Standard 3.2: a member of Change-Approvers approves each normal change before it is deployed.

**Cause.** The deployment tool does not check the ticket is approved (F15), so a change can be deployed while its approval is still pending.

**Effect.** Changes can reach production before the business has agreed to them. Because the sample found exceptions, the approval control cannot be relied on for the period.

**Recommendation.** Make the deployment tool check that the ticket is approved before deploying. Have management check all 40 Q3 changes for approval after deployment and report the result.

**Management response.** Pending.

### F14

**An emergency change skipped the emergency procedure**  
Rating: **Medium** | Criteria: Standard 3.6 | Tests CM-05

**Condition.** Emergency change CHG-2026-0137 (approvals page timing out) was pushed straight to main and deployed by Ryan Patel on 23 September at 21:15, with no second person reviewing the code. The ticket was approved on 6 October, 9 working days later, has no testing recorded and has no post implementation review. The same evening Ryan Patel was given full administrator rights on the app server (F17). The other emergency change in the period, CHG-2026-0136 on 19 August, followed the procedure.

**Criteria.** Standard 3.6: an emergency change may be deployed first only if a second person reviews the code before deployment, the ticket is approved within 2 working days, and a post implementation review is recorded within 5 working days.

**Cause.** The fix was made late in the evening by one person, and nothing tracks emergency changes to make sure the approval and review follow.

**Effect.** An urgent change, made under pressure and without review, was never checked afterwards. Emergency changes carry the most risk of a mistake.

**Recommendation.** Complete the post implementation review of CHG-2026-0137 now. Keep a list of open emergency changes that the Head of IT checks at least weekly until each has its approval and review.

**Management response.** Pending.

### F15

**The change tools do not enforce the change process**  
Rating: **High** | Criteria: Standard 3.7 | Tests CM-06, CM-02

**Condition.** Branch protection on main requires one approval but allows Ryan Patel to push directly, lets repository administrators (the two organisation owners and the Gitea site administrators) merge without the approval, and keeps an approval valid when new commits are added after it. The rule was last changed on 2 February 2026, so these settings applied for the whole period. The deployment tool records every deployment correctly, but the ticket is optional and is never checked.

**Criteria.** Standard 3.7: branch protection on main requires one approval, blocks direct pushes, and does not let administrators override it.

**Cause.** Exceptions were added to the protection rule so urgent fixes could be made quickly, and the deployment tool was not connected to the service desk.

**Effect.** The change process depends on people choosing to follow it. F11 and F12 show that it was not followed when it was inconvenient.

**Recommendation.** Block direct pushes to main for everyone, stop administrators overriding the rule, and dismiss approvals when new commits are pushed. Make the deployment tool refuse a deployment unless the ticket exists, is approved and names the commit.

**Management response.** Pending.

### F16

**A contractor changed the code after his contract ended**  
Rating: **High** | Criteria: Standard 3.8; Policy 3.4 | Tests CM-07, AC-18

**Condition.** Leo Martin's contract with DevPartners Ltd ended on 30 June 2026. His Gitea account is still active with write access to the finance application. He signed in on 11 August, opened pull request #28 (Fix timezone on payment dates), and it was approved by Ryan Patel, merged on 12 August and deployed on 13 August under CHG-2026-0117. His directory account was also still enabled (F5).

**Criteria.** Standard 3.8 and Policy 3.4: access of contractors whose contract has ended is removed within 1 working day.

**Cause.** Gitea has its own accounts, separate from the directory, and it is not part of the process for removing access at the end of a contract.

**Effect.** Someone with no contract, and so no obligations to Northwind, changed the code of the payments application. The change was reviewed, which reduces the risk, but the access should not have existed.

**Recommendation.** Disable leo.martin in Gitea now and confirm with DevPartners whether the work was requested. Add Gitea to the leaver and contract end checklist, and connect Gitea to the directory so that disabling a directory account also blocks Gitea.

**Management response.** Pending.

### F17

**Unapproved administrator rights on the application server**  
Rating: **High** | Criteria: Standard 5.1, 5.2 | Tests AC-15, AC-16, AC-18

**Condition.** Two grants of full administrator rights on the app server have no approval. A local account called support, described as the DevPartners support engineer, had its password set on 12 August 2026. It can sign in with a password that never expires, and is in the sudo group, which gives full rights. Ryan Patel was given full rights that do not ask for a password, in /etc/sudoers.d/ryan-emergency, dated 23 September 2026 20:41 and labelled as temporary for the approvals page fix. Both were still in place when the evidence was collected on 28 October.

**Criteria.** Standard 5.1: the only local account allowed to sign in is the emergency administrator account, with an exception. Standard 5.2: administrator rights are given only through IT-Server-Admins, and rights that do not ask for a password need an exception.

**Cause.** Access given in a hurry, for a supplier's visit and for an emergency, was never recorded and never taken away. Nothing reviews who has administrator rights on the servers.

**Effect.** A supplier and a developer each have full control of the production server, including the finance database and the deployment tool, outside every change control. Because the server keeps no sign in history (O4), it cannot be shown whether either was used.

**Recommendation.** Remove the support account and the ryan-emergency rule now. Give temporary access only through IT-Server-Admins with an exception that has an end date. Review the sudo rules on every server each quarter as part of the access review (F10).

**Management response.** Pending.

### F18

**SSH settings on the servers are weaker than the Standard**  
Rating: **Medium** | Criteria: Standard 5.3 | Tests AC-17

**Condition.** On both servers, five of the eight required SSH settings are not met. Root can sign in with a key (PermitRootLogin is prohibit-password, not no); six password attempts are allowed per connection (MaxAuthTries 6, not 4 or fewer); X11 forwarding is on; an unauthenticated connection is kept open for 120 seconds (LoginGraceTime, not 60 or less); and idle sessions never time out (ClientAliveInterval 0).

**Criteria.** Standard 5.3: SSH follows the listed CIS Ubuntu Linux Benchmark settings.

**Cause.** The servers were built with Ubuntu's default SSH settings, and the build does not apply the Standard.

**Effect.** Password guessing is easier, a forgotten session stays open indefinitely, and root sign in is possible if a key is ever placed on the root account.

**Recommendation.** Add the settings in a file in /etc/ssh/sshd_config.d/ on both servers, include it in the server build, and check it with sshd -T after each change.

**Management response.** Pending.

### F19

**Backups failed or did not run on 6 nights, and 5 went unnoticed**  
Rating: **High** | Criteria: Standard 4.1, 4.2 | Tests OP-01, OP-02, OP-04

**Condition.** Of the 92 nightly backups in the period, 5 failed and 1 did not run. On four nights in a row, 8 to 11 August, the backup failed because the disk was full, leaving no new backup for four days. On 19 July there is no log entry at all. On 20 September the backup failed because the database was locked. Only the 20 September failure was followed up, with incident INC-2026-0193 the next day; nothing was raised for the other five. The backup job writes a log line for every run but does not tell anyone when a run fails or does not happen.

**Criteria.** Standard 4.1: the finance database is backed up every night. Standard 4.2: a failed or missing backup is followed up with an incident by the end of the next working day and a successful rerun.

**Cause.** Nothing alerts a person to a failure (OP-04), and nobody checks the backup log, so failures are found only by chance. The full disk was not monitored either.

**Effect.** Had the database been lost during 8 to 11 August, up to four days of supplier payments data could not have been recovered.

**Recommendation.** Send an alert to the Systems Administrator when a backup fails or has not run by 03:00. Monitor free disk space on the app server. Find out why the job did not run on 19 July.

**Management response.** Pending.

### F20

**No restore was tested in the quarter**  
Rating: **Medium** | Criteria: Standard 4.3 | Tests OP-03

**Condition.** The restore test log has no test in Q3 2026. The last restore was tested on 14 April 2026 (RT-2026-02), 169 days before the end of the period.

**Criteria.** Standard 4.3: a restore from backup is tested at least once a quarter, and the result recorded.

**Cause.** Restore tests are not scheduled, and the missed test was not noticed.

**Effect.** Without a recent restore there is no assurance that the backups, including those taken after the failures in F19, can be used to recover the finance database.

**Recommendation.** Test a restore of the latest backup now, comparing record counts with the live database, and record it. Put a quarterly restore test in the IT calendar, owned by the Systems Administrator.

**Management response.** Pending.

### F21

**An unapproved job runs a developer's script as root**  
Rating: **High** | Criteria: Standard 4.5 | Tests OP-05

**Condition.** /etc/cron.d/finance-tidy, dated 2 July 2026, runs /home/ryan.patel/bin/tidy-exports.sh as root at 02:15 every night. The job is not on the job schedule, and the script is in Ryan Patel's home folder, where he can change it.

**Criteria.** Standard 4.5: only jobs on the job schedule may run, and a job that runs as root may only run programs that only root can change.

**Cause.** The job was set up directly on the server to tidy old payment exports, outside the change process.

**Effect.** Anyone who can change the script, which means Ryan Patel or anyone using his account, can run any command as root on the production server the next night, without sudo and without it being logged. This would still be true after his other rights are removed (F17).

**Recommendation.** Move the script to a root owned location such as /usr/local/sbin, review it, and add the job to the schedule with the Head of IT's approval; or remove it. Check every server's scheduled jobs against the schedule each quarter.

**Management response.** Pending.

### F22

**The domain controller's clock was found badly wrong twice**  
Rating: **Medium** | Criteria: Standard 4.6 | Tests OP-06

**Condition.** Both servers were synchronised when the evidence was collected. During fieldwork, however, the domain controller's clock was found about 38 minutes slow on 27 October and about 22 hours behind on 28 October. Each time it was corrected by hand. The second time it stopped the app server joining the domain, because Kerberos rejects clocks more than 5 minutes apart.

**Criteria.** Standard 4.6: every server keeps its clock synchronised with a reliable time source, within 5 seconds of it.

**Cause.** Not confirmed. The pattern fits the virtual machine being paused and resumed, after which chrony, as configured, corrects a large error only slowly.

**Effect.** While the clock is wrong, sign in to the domain can fail and the times recorded in the directory and in logs cannot be trusted, which weakens every control that relies on them, including the dates used in this review.

**Recommendation.** Allow chrony to step the clock whenever it is more than a second out (makestep 1 -1) on both servers, and alert when the offset is above 5 seconds.

**Management response.** Pending.

## 5. Observations

**O2: Gitea's built in administrator account.** The gitea-admin account has full control of Gitea and was last used when Gitea was set up on 3 November 2025. It should be kept as an emergency account with its password in the vault, and each use of it reviewed.

**O3: Backups are kept on the same server.** Backups of the finance database are written to /var/backups/northwind on the app server itself. If the server is lost, the database and its backups are lost together. A copy should be kept on another machine.

**O4: The servers keep no sign in history.** Neither Linux server has a sign in history (last and wtmpdb are not installed), so it could not be checked whether the support account or Ryan Patel's administrator rights were used. Sign in history should be kept and the authentication logs sent to a central place.

## 6. Ratings

| Rating | Meaning |
|---|---|
| High | Could directly allow fraud, loss of control of a system, loss of data, or unauthorised access to financial processes. Fix immediately. |
| Medium | Weakens a control so that misuse is more likely or less likely to be detected. Fix within 30 days. |
| Low | Good practice improvement with limited direct risk. Fix within 90 days. |

## 7. Limitations

* This is a lab environment. The company and its records are fictional, and the weaknesses were seeded deliberately to be found.
* The application server was built after the audit period. Its Q3 history (pull requests, reviews, merges, deployments and backup runs) was recreated through Gitea itself when it was built and dated to when each event happened. See [lab/README.md](../lab/README.md).
* Server settings (sudo rules, SSH, scheduled jobs, time and patching) were extracted on 2026-10-28, after the period. File dates and password dates were used to establish when each exception began; settings with no date are reported as found.
* The servers keep no sign in history (O4), so the use of the access in F17 could not be tested.
* The office PC was not available during fieldwork, so the PC items in the test plan were not tested. See [the fieldwork notes](../docs/fieldwork-notes.md).

## 8. Next steps

1. Management responses, owners and dates for each finding.
2. Remediation, followed by a retest of each finding's condition on fresh evidence, as was done for the logical access findings.
3. Review of the office PC once it is in service.
