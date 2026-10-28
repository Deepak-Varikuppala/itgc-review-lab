# Northwind Retail: Logical Access Review

| | |
|---|---|
| Entity | Northwind Retail (fictional company, lab environment) |
| System | Active Directory domain `northwind.internal` |
| Audit period | 1 July 2026 to 30 September 2026 |
| Evidence extracted | 2026-10-27 |
| Criteria | Northwind Retail Access Control Policy v2.1 |
| Prepared by | Deepak Kumar Varikuppala |
| Status | Issued for management response |

## 1. Summary

**Overall conclusion: logical access controls over the Northwind domain were not operating effectively during the period.**

Of 14 controls tested, 1 operated without exception and 13 had exceptions. The review raised 10 findings: 5 high, 4 medium and 1 low.

Three themes explain most of the findings:

1. **Access is added reliably but rarely taken away.** New starters were set up correctly, but a leaver, a mover and a contractor all kept access they should have lost (F1, F4, F5).
2. **The payments process can be bypassed by one person.** A Senior Accountant approved her own request to become a payment approver, and a shared login can create payments without anyone being accountable (F8, F3).
3. **Privileged access and the domain settings have drifted from policy.** Two accounts hold full domain administrator rights without approval, and accounts can be attacked by unlimited password guessing (F2, F6).

The quarterly access review, which should have caught most of these, could not be evidenced (F10).

The most urgent actions are to disable the leaver's account and investigate its use after he left, remove the conflicting payment access, disable the shared finance login, and enable account lockout.

## 2. Scope and approach

The review covered logical access to the `northwind.internal` Active Directory domain, which controls sign in to Northwind's systems and access to the finance application's payment roles. Change management, IT operations and access to the servers are reported separately, for the same period, in [change-and-operations-review.md](change-and-operations-review.md).

Directory data was extracted read only by the system administrator using a scripted extraction (`audit/collect_evidence.py`). Before testing, the extraction was checked for **completeness**, by confirming the record counts in the raw directory output matched the processed listing, and for **integrity**, by verifying SHA-256 hashes of every evidence file.

Each control was tested against the clause of the policy it implements. Tests examined the **whole population** rather than a sample, so there is no sampling risk. Two tests assess **design** (whether the configuration can achieve the policy at all) and twelve assess **operating effectiveness** (whether the control worked in practice). The full procedures are in [docs/testing-programme.md](../docs/testing-programme.md), and every item tested is in [the workpaper](../workpapers/logical-access-workpaper.xlsx).

Each test is also mapped to ISO/IEC 27001:2022 Annex A and CIS Controls v8.1, so the results can be read against either framework. The mapping is in the testing programme.

## 3. Results by control

| Test | Control | Policy | Tested | Exceptions | Conclusion |
|---|---|---|---|---|---|
| AC-01 | Leavers' accounts are disabled promptly | 3.3 | 3 | 1 | Not operating effectively (1 exception in 3 tested) |
| AC-02 | Access is updated when staff change role | 3.2 | 1 | 1 | Not operating effectively (1 exception in 1 tested) |
| AC-03 | New starters' access is approved by their line manager | 3.1 | 2 | 0 | Effective (no exceptions) |
| AC-04 | Every enabled personal account belongs to a current employee or contractor | 3.3, 3.4 | 22 | 2 | Not operating effectively (2 exceptions in 22 tested) |
| AC-05 | Contractor accounts expire at the end of the contract | 3.4 | 1 | 1 | Design deficiency (1 exception in 1 tested) |
| AC-06 | Unused accounts are disabled | 3.5 | 28 | 2 | Not operating effectively (2 exceptions in 28 tested) |
| AC-07 | Domain password and lockout settings meet policy | 4.1, 4.2 | 6 | 2 | Design deficiency (2 exceptions in 6 tested) |
| AC-08 | Only approved service accounts have non-expiring passwords | 4.3 | 4 | 2 | Not operating effectively (2 exceptions in 4 tested) |
| AC-09 | There are no shared accounts | 4.4 | 1 | 1 | Not operating effectively (1 exception in 1 tested) |
| AC-10 | Domain Admins is limited to approved, named administrator accounts | 5.1, 5.2, 5.3 | 5 | 2 | Not operating effectively (2 exceptions in 5 tested) |
| AC-11 | No one can both create and approve supplier payments | 6.1 | 7 | 1 | Not operating effectively (1 exception in 7 tested) |
| AC-12 | Nobody approves their own access | 6.2 | 18 | 1 | Not operating effectively (1 exception in 18 tested) |
| AC-13 | Every member of a sensitive group has approved access | 3.1, 5.1 | 17 | 3 | Not operating effectively (3 exceptions in 17 tested) |
| AC-14 | Quarterly access reviews are performed | 7.1 | 1 | 1 | Not operating effectively (1 exception in 1 tested) |

## 4. Findings

| ID | Finding | Rating | Tests |
|---|---|---|---|
| [F1](#f1) | A leaver's account was still active and able to approve payments | **High** | AC-01, AC-04 |
| [F2](#f2) | Full domain administrator rights were held without approval | **High** | AC-10, AC-13 |
| [F3](#f3) | A shared account can create supplier payments | **High** | AC-09, AC-13, AC-08 |
| [F4](#f4) | A member of staff kept payment access after moving to Sales | **Medium** | AC-02 |
| [F5](#f5) | A contractor's account stayed active after the contract ended | **Medium** | AC-04, AC-05, AC-06 |
| [F6](#f6) | The password and lockout settings are weaker than policy | **High** | AC-07 |
| [F7](#f7) | Passwords set never to expire without approval | **Medium** | AC-08 |
| [F8](#f8) | One person can create and approve payments, and approved that access herself | **High** | AC-11, AC-12 |
| [F9](#f9) | An unused service account | **Low** | AC-06 |
| [F10](#f10) | Quarterly access reviews could not be evidenced | **Medium** | AC-14 |

### F1

**A leaver's account was still active and able to approve payments**  
Rating: **High** | Policy clause 3.3 | Tests AC-01, AC-04

**Condition.** Mark Taylor (Financial Controller) left on 29 August 2026. On 27 October 2026, 56 days after the deadline for disabling his account, the account mark.taylor was still enabled, still in Finance-Payments-Approvers and GG-Finance, and had not been moved to Leavers. The directory records a sign in on 27 October 2026, after his leaving date. The other two leavers in the period were handled correctly.

**Criteria.** Policy clause 3.3: a leaver's account must be disabled within 1 working day of their last day, removed from all groups and moved to Leavers.

**Cause.** Leavers are removed only when HR tells IT. There is no regular check of the directory against the HR leavers list, so a missed notification is not picked up.

**Effect.** A former employee, or anyone who knows the password, could approve supplier payments after leaving. The recorded sign in after the leaving date needs to be investigated to establish who used the account.

**Recommendation.** Disable mark.taylor now, remove its group memberships and review what the account did after 29 August 2026. Reconcile the directory against the HR leavers list every week, and make IT acknowledge each HR leaver notification.

**Management response.** Pending.

### F2

**Full domain administrator rights were held without approval**  
Rating: **High** | Policy clause 5.1, 5.2, 5.3 | Tests AC-10, AC-13

**Condition.** Two of the five members of Domain Admins are not allowed by policy. liam.brooks is an everyday personal account belonging to an IT Support Analyst whose approved access (REQ-2023-047) is the Helpdesk role for password resets only. svc-backup is a service account; its exception EX-2024-02 covers its non-expiring password, not Domain Admins membership.

**Criteria.** Policy clauses 5.1 to 5.3: Domain Admins is limited to separate adm. accounts with approved access; everyday accounts must not hold administrator rights; service accounts need a recorded exception to be Domain Admins.

**Cause.** Privileged access appears to be granted directly by IT without a matching approved request, and nothing compares Domain Admins membership with approvals.

**Effect.** Domain Admins can change any account, password or setting in the domain. An everyday account is exposed to phishing and web browsing, and a compromised service account with these rights would give an attacker full control.

**Recommendation.** Remove liam.brooks from Domain Admins; delegate password reset rights to Helpdesk only. Give svc-backup only the rights the backup job needs, or record and approve an exception. Review Domain Admins membership every month.

**Management response.** Pending.

### F3

**A shared account can create supplier payments**  
Rating: **High** | Policy clause 4.4 | Tests AC-09, AC-13, AC-08

**Condition.** finance.shared is a login used by the finance team. It is a member of Finance-Payments-Initiators, has no approved access request, and its password is set never to expire without an exception.

**Criteria.** Policy clause 4.4: every account belongs to one named person or system, and shared accounts are not allowed. Clause 4.3: only approved service accounts may have non-expiring passwords.

**Cause.** The account appears to have been set up for convenience and was never put through the access request process.

**Effect.** Payments created with this account cannot be traced to a person, so a fraudulent or mistaken payment could not be attributed. The password is likely known to several people, including any who have since left, and is never changed.

**Recommendation.** Disable finance.shared. Give each finance team member who needs to create payments their own approved access. If a shared mailbox is needed, use mailbox delegation rather than a shared login.

**Management response.** Pending.

### F4

**A member of staff kept payment access after moving to Sales**  
Rating: **Medium** | Policy clause 3.2 | Tests AC-02

**Condition.** Emma Wilson transferred from Finance (Accounts Payable Clerk) to Sales (Account Manager) on 14 September 2026. On 27 October 2026, 36 days after the deadline, her account still had Finance-Payments-Initiators and GG-Finance. Her new Sales access was approved promptly (REQ-2026-084), but nothing was removed.

**Criteria.** Policy clause 3.2: access no longer needed must be removed within 5 working days of a change of role.

**Cause.** The transfer was treated as a request for new access only. There is no step to remove the previous role's access.

**Effect.** Staff build up access they do not need. Here a Sales employee can still create supplier payments.

**Recommendation.** Remove Finance-Payments-Initiators and GG-Finance from emma.wilson. Change the mover process so the old line manager confirms which access to remove.

**Management response.** Pending.

### F5

**A contractor's account stayed active after the contract ended**  
Rating: **Medium** | Policy clause 3.4, 3.5 | Tests AC-04, AC-05, AC-06

**Condition.** Leo Martin's contract with DevPartners Ltd ended on 30 June 2026. The account leo.martin was still enabled on 27 October 2026, with no expiry date set and membership of Developers and GG-IT. It has never been used.

**Criteria.** Policy clause 3.4: contractor accounts must expire on the contract end date. Clause 3.5: accounts unused for 45 days must be disabled.

**Cause.** Expiry dates are not set when contractor accounts are created, and contractors are not covered by the HR leaver process.

**Effect.** An unused, forgotten account is an easy target, because misuse is unlikely to be noticed.

**Recommendation.** Disable leo.martin. Make an expiry date mandatory when creating contractor accounts, and include the contractor list in the weekly leaver reconciliation.

**Management response.** Pending.

### F6

**The password and lockout settings are weaker than policy**  
Rating: **High** | Policy clause 4.1, 4.2 | Tests AC-07

**Condition.** The domain allows passwords of 8 characters against a policy minimum of 12, and the account lockout threshold is 0, so accounts never lock however many wrong passwords are tried. Complexity, history and maximum age meet the policy.

**Criteria.** Policy clause 4.1: passwords of at least 12 characters. Clause 4.2: accounts lock for at least 15 minutes after 5 failed attempts.

**Cause.** The domain settings were not updated when the policy was revised to version 2.1 in January 2026.

**Effect.** Every account in the domain can be attacked by unlimited password guessing, and shorter passwords make that guessing far quicker.

**Recommendation.** Set the minimum password length to 12 and the lockout threshold to 5. Check the domain settings against the policy whenever the policy changes.

**Management response.** Pending.

### F7

**Passwords set never to expire without approval**  
Rating: **Medium** | Policy clause 4.3 | Tests AC-08

**Condition.** Two accounts have non-expiring passwords without an approved exception: sarah.mitchell, a personal account, and finance.shared (see F3). The two service accounts with this setting have approved exceptions.

**Criteria.** Policy clause 4.3: only service accounts with an approved exception may have passwords that never expire.

**Cause.** The setting can be applied by any administrator without an exception being recorded.

**Effect.** A password that never changes stays useful to anyone who has learned it.

**Recommendation.** Remove the setting from sarah.mitchell and finance.shared. Report every account with this setting monthly and compare it with the exception register.

**Management response.** Pending.

### F8

**One person can create and approve payments, and approved that access herself**  
Rating: **High** | Policy clause 6.1, 6.2 | Tests AC-11, AC-12

**Condition.** Priya Shah (Senior Accountant) is in both Finance-Payments-Initiators and Finance-Payments-Approvers. The approver access was requested and approved by Priya Shah herself on 3 November 2025 (REQ-2025-118), described as cover during a busy period. The access was never removed.

**Criteria.** Policy clause 6.1: no one may hold both payment roles. Clause 6.2: nobody may approve their own access request.

**Cause.** The access request process does not stop a requester from approving their own request, and temporary access is not given an end date.

**Effect.** One person can create and approve a supplier payment with no second check, which is the classic route to payment fraud. Payments approved by Priya Shah should be reviewed to confirm none were also created by her.

**Recommendation.** Remove Finance-Payments-Approvers from priya.shah. Review all payments she has approved since November 2025. Block self-approval in the request process, and give temporary access an end date.

**Management response.** Pending.

### F9

**An unused service account**  
Rating: **Low** | Policy clause 3.5 | Tests AC-06

**Condition.** svc-financeapp has never signed in, although it has an exception for a non-expiring password.

**Criteria.** Policy clause 3.5: accounts unused for 45 days must be disabled unless an exception is approved.

**Cause.** The account may have been created for an integration that was not used, or the application may authenticate in another way.

**Effect.** An unused account with a long lived password adds risk without benefit.

**Recommendation.** Confirm with the finance application owner whether the account is needed. Disable it if not; if it is, record the dormancy in its exception.

**Management response.** Pending.

### F10

**Quarterly access reviews could not be evidenced**  
Rating: **Medium** | Policy clause 7.1 | Tests AC-14

**Condition.** No evidence of a Q3 2026 review of the privileged and payments groups was provided.

**Criteria.** Policy clause 7.1: system owners review these groups every quarter and keep signed off evidence.

**Cause.** Reviews do not appear to be scheduled or assigned to named owners.

**Effect.** The review is the control that catches failures in the joiner, mover and leaver processes. F1, F2, F4 and F8 would all have been visible to an effective review.

**Recommendation.** Assign an owner to each group, schedule the reviews, and keep the signed off list with the changes made as a result.

**Management response.** Pending.

## 5. Observations

**O1: The built in Administrator account is in use.** The built in Administrator account signed in on 27 October 2026. Named adm. accounts exist for administrative work. The built in account should be kept as a break glass account with a vaulted password, and every use of it reviewed.

## 6. Ratings

| Rating | Meaning |
|---|---|
| High | Could directly allow fraud, loss of control of the domain, or unauthorised access to financial processes. Fix immediately. |
| Medium | Weakens a control so that misuse is more likely or less likely to be detected. Fix within 30 days. |
| Low | Good practice improvement with limited direct risk. Fix within 90 days. |

## 7. Limitations

* This is a lab environment. The company and its records are fictional, and the weaknesses were seeded deliberately to be found.
* Account creation dates in the directory are the date the lab was built, so HR start dates were relied on instead.
* Last logon dates were recorded when the lab was built. At that time the domain controller's clock was about 38 minutes slow; it was corrected before the evidence was extracted. Time synchronisation was tested as an IT operations control (OP-06, finding F22).
* No evidence of the quarterly access review was provided, so that control could not be tested beyond confirming its absence.

## 8. Remediation and retest

After remediation, a fresh extraction was taken on 2026-10-27 (`directory-20261027T033513Z`) and each finding's condition was checked directly. Full detail is in [workpapers/remediation-retest.md](../workpapers/remediation-retest.md).

| Finding | Rating | Status | Retest result |
|---|---|---|---|
| F1 | High | **Resolved, follow up open** | mark.taylor is disabled, has no group memberships and is in Leavers. The sign in after the leaving date still needs to be investigated. |
| F2 | High | **Resolved** | Domain Admins now contains only Administrator and the adm. accounts: Administrator, adm.akhan, adm.jcarter. |
| F3 | High | **Resolved** | finance.shared is disabled with no group memberships. |
| F4 | Medium | **Resolved** | emma.wilson holds only Sales access: GG-Sales. |
| F5 | Medium | **Resolved, follow up open** | leo.martin is disabled with no group memberships. Setting expiry dates on new contractor accounts is a process change to confirm on the next contractor joiner. |
| F6 | High | **Resolved** | Minimum password length 12; lockout after 5 attempts. |
| F7 | Medium | **Resolved** | Only service accounts with approved exceptions keep non-expiring passwords. |
| F8 | High | **Resolved, follow up open** | Nobody now holds both payment roles. The review of payments approved by priya.shah since November 2025, and blocking self approval in the request process, remain open. |
| F9 | Low | **Resolved** | svc-financeapp is disabled. |
| F10 | Medium | **Open** | Process change. The first quarterly review is due at the end of Q4 2026 and will be tested then. |

## 9. Next steps

1. Complete the open follow ups from the retest, and test the first quarterly access review when it is performed.
2. Change management, IT operations and server access are reported in [change-and-operations-review.md](change-and-operations-review.md), and both reviews are brought together in [itgc-summary.md](itgc-summary.md).
