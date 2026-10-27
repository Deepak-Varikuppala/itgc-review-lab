# Testing programme: logical access

Generated from the test definitions in `audit/run_tests.py`. Each test was designed before testing began, against the clause of the Northwind Access Control Policy it covers. Each test is also mapped to ISO/IEC 27001:2022 Annex A and to CIS Controls v8.1 safeguards. The policy remains the criteria; the mapping shows where each test sits in those frameworks.

| Test | Control | Policy | Type | ISO/IEC 27001:2022 | CIS Controls v8.1 |
|---|---|---|---|---|---|
| AC-01 | Leavers' accounts are disabled promptly | 3.3 | Operating effectiveness | A.5.18 Access rights | 6.2 Access revoking process |
| AC-02 | Access is updated when staff change role | 3.2 | Operating effectiveness | A.5.18 Access rights | 6.2 Access revoking process; 6.8 Role based access |
| AC-03 | New starters' access is approved by their line manager | 3.1 | Operating effectiveness | A.5.18 Access rights | 6.1 Access granting process |
| AC-04 | Every enabled personal account belongs to a current employee or contractor | 3.3, 3.4 | Operating effectiveness | A.5.16 Identity management; A.5.18 Access rights | 5.1 Inventory of accounts; 6.2 Access revoking process |
| AC-05 | Contractor accounts expire at the end of the contract | 3.4 | Design | A.5.18 Access rights | 6.2 Access revoking process |
| AC-06 | Unused accounts are disabled | 3.5 | Operating effectiveness | A.5.18 Access rights | 5.3 Disable dormant accounts |
| AC-07 | Domain password and lockout settings meet policy | 4.1, 4.2 | Design | A.5.17 Authentication information; A.8.5 Secure authentication | 5.2 Use unique passwords |
| AC-08 | Only approved service accounts have non-expiring passwords | 4.3 | Operating effectiveness | A.5.17 Authentication information | 5.2 Use unique passwords; 5.5 Inventory of service accounts |
| AC-09 | There are no shared accounts | 4.4 | Operating effectiveness | A.5.16 Identity management | 5.1 Inventory of accounts |
| AC-10 | Domain Admins is limited to approved, named administrator accounts | 5.1, 5.2, 5.3 | Operating effectiveness | A.8.2 Privileged access rights | 5.4 Dedicated administrator accounts; 5.5 Inventory of service accounts |
| AC-11 | No one can both create and approve supplier payments | 6.1 | Operating effectiveness | A.5.3 Segregation of duties | 6.8 Role based access |
| AC-12 | Nobody approves their own access | 6.2 | Operating effectiveness | A.5.3 Segregation of duties; A.5.18 Access rights | 6.1 Access granting process |
| AC-13 | Every member of a sensitive group has approved access | 3.1, 5.1 | Operating effectiveness | A.5.18 Access rights; A.8.2 Privileged access rights | 6.1 Access granting process; 6.8 Role based access |
| AC-14 | Quarterly access reviews are performed | 7.1 | Operating effectiveness | A.5.18 Access rights | 6.8 Role based access (recurring access reviews) |

## AC-01: Leavers' accounts are disabled promptly

**Policy clause:** 3.3  
**ISO/IEC 27001:2022:** A.5.18 Access rights  
**CIS Controls v8.1:** 6.2 Access revoking process  
**Test type:** Operating effectiveness

**Control objective.** Former employees cannot use their access after they leave.

**Procedure.** From the HR extract, select every employee with a leaving date in the audit period. Find each one's account by employee ID. Check the account is disabled, removed from all groups and moved to the Leavers area, and compare any last logon date with the leaving date. Deadline: 1 working day after the leaving date.

**Population.** All employees who left between 1 July and 30 September 2026. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-02: Access is updated when staff change role

**Policy clause:** 3.2  
**ISO/IEC 27001:2022:** A.5.18 Access rights  
**CIS Controls v8.1:** 6.2 Access revoking process; 6.8 Role based access  
**Test type:** Operating effectiveness

**Control objective.** People do not keep access from a previous role that they no longer need.

**Procedure.** From the HR extract, select every employee who transferred department in the audit period. Compare their current group memberships with their new department. Any group belonging to the previous department still held 5 working days after the transfer is an exception.

**Population.** All transfers between 1 July and 30 September 2026. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-03: New starters' access is approved by their line manager

**Policy clause:** 3.1  
**ISO/IEC 27001:2022:** A.5.18 Access rights  
**CIS Controls v8.1:** 6.1 Access granting process  
**Test type:** Operating effectiveness

**Control objective.** Access is only given when the business has asked for it.

**Procedure.** From the HR extract, select every employee who started in the audit period. For each, find the access request, and check it was approved by the line manager recorded in HR, on or before the start date, and that the groups granted match the request.

**Population.** All starters between 1 July and 30 September 2026. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-04: Every enabled personal account belongs to a current employee or contractor

**Policy clause:** 3.3, 3.4  
**ISO/IEC 27001:2022:** A.5.16 Identity management; A.5.18 Access rights  
**CIS Controls v8.1:** 5.1 Inventory of accounts; 6.2 Access revoking process  
**Test type:** Operating effectiveness

**Control objective.** No active account exists for someone who no longer works for the company.

**Procedure.** List every enabled personal account in the directory. Match each one by employee or contractor ID to the HR extract and contractor list. An account with no match, or whose match has left or whose contract has ended, is an exception. Generic, administrator, service and built in accounts are tested in AC-08 to AC-10.

**Population.** All enabled personal accounts at the extraction date. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-05: Contractor accounts expire at the end of the contract

**Policy clause:** 3.4  
**ISO/IEC 27001:2022:** A.5.18 Access rights  
**CIS Controls v8.1:** 6.2 Access revoking process  
**Test type:** Design

**Control objective.** A contractor's access stops automatically when their contract ends, even if nobody remembers to remove it.

**Procedure.** For every contractor on the contractor list, find their account and check its expiry date is set to the contract end date.

**Population.** All contractors on the contractor list. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-06: Unused accounts are disabled

**Policy clause:** 3.5  
**ISO/IEC 27001:2022:** A.5.18 Access rights  
**CIS Controls v8.1:** 5.3 Disable dormant accounts  
**Test type:** Operating effectiveness

**Control objective.** Accounts nobody uses are removed before they can be misused unnoticed.

**Procedure.** List every enabled account. Flag any account that has never signed in, or whose last sign in was 45 days or more before the extraction date, unless an approved exception exists.

**Population.** All enabled accounts at the extraction date. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-07: Domain password and lockout settings meet policy

**Policy clause:** 4.1, 4.2  
**ISO/IEC 27001:2022:** A.5.17 Authentication information; A.8.5 Secure authentication  
**CIS Controls v8.1:** 5.2 Use unique passwords  
**Test type:** Design

**Control objective.** Passwords are hard to guess and accounts cannot be attacked by repeated guessing.

**Procedure.** Read the live domain password settings and compare each with the policy.

**Population.** The domain password policy (one configuration). Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-08: Only approved service accounts have non-expiring passwords

**Policy clause:** 4.3  
**ISO/IEC 27001:2022:** A.5.17 Authentication information  
**CIS Controls v8.1:** 5.2 Use unique passwords; 5.5 Inventory of service accounts  
**Test type:** Operating effectiveness

**Control objective.** Every person's password is changed regularly.

**Procedure.** List every enabled account whose password is set never to expire. Each must be a service account with an approved, in date entry in the exception register.

**Population.** All enabled accounts with non-expiring passwords. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-09: There are no shared accounts

**Policy clause:** 4.4  
**ISO/IEC 27001:2022:** A.5.16 Identity management  
**CIS Controls v8.1:** 5.1 Inventory of accounts  
**Test type:** Operating effectiveness

**Control objective.** Every action can be traced to one person.

**Procedure.** List every enabled account that is not personal, administrator, service or built in, and confirm its purpose from its description.

**Population.** All enabled generic accounts. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-10: Domain Admins is limited to approved, named administrator accounts

**Policy clause:** 5.1, 5.2, 5.3  
**ISO/IEC 27001:2022:** A.8.2 Privileged access rights  
**CIS Controls v8.1:** 5.4 Dedicated administrator accounts; 5.5 Inventory of service accounts  
**Test type:** Operating effectiveness

**Control objective.** Full control of the domain is held only by people who need it, through separate accounts that are not used for everyday work.

**Procedure.** List every member of Domain Admins. Each must be a separate adm. account with an approved request, or the built in Administrator account. Day to day accounts and service accounts are exceptions unless an approved exception exists.

**Population.** All members of Domain Admins. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-11: No one can both create and approve supplier payments

**Policy clause:** 6.1  
**ISO/IEC 27001:2022:** A.5.3 Segregation of duties  
**CIS Controls v8.1:** 6.8 Role based access  
**Test type:** Operating effectiveness

**Control objective.** A single person cannot make and approve a fraudulent payment.

**Procedure.** Compare the members of Finance-Payments-Initiators with the members of Finance-Payments-Approvers. Anyone in both is an exception.

**Population.** All members of either payments group. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-12: Nobody approves their own access

**Policy clause:** 6.2  
**ISO/IEC 27001:2022:** A.5.3 Segregation of duties; A.5.18 Access rights  
**CIS Controls v8.1:** 6.1 Access granting process  
**Test type:** Operating effectiveness

**Control objective.** Access is always checked by someone other than the person receiving it.

**Procedure.** Inspect every access request. Any request approved by the person it gives access to is an exception.

**Population.** All 18 access requests in the access request log. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-13: Every member of a sensitive group has approved access

**Policy clause:** 3.1, 5.1  
**ISO/IEC 27001:2022:** A.5.18 Access rights; A.8.2 Privileged access rights  
**CIS Controls v8.1:** 6.1 Access granting process; 6.8 Role based access  
**Test type:** Operating effectiveness

**Control objective.** Nobody holds powerful access that the business did not approve.

**Procedure.** For every member of each sensitive group, find an approved access request for that group. Requests approved by the person themselves are dealt with in AC-12.

**Population.** All members of: Domain Admins, IT-Server-Admins, Finance-Payments-Initiators, Finance-Payments-Approvers, Change-Approvers, Change-Deployers. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.

## AC-14: Quarterly access reviews are performed

**Policy clause:** 7.1  
**ISO/IEC 27001:2022:** A.5.18 Access rights  
**CIS Controls v8.1:** 6.8 Role based access (recurring access reviews)  
**Test type:** Operating effectiveness

**Control objective.** Access that is no longer needed is found and removed even when other controls miss it.

**Procedure.** Request the signed off Q3 2026 review of Domain Admins, IT-Server-Admins and the two payments groups, and re-perform a sample of the review's conclusions.

**Population.** The Q3 2026 quarterly access review. Every item was tested.

**Evidence used.** Directory extract (`users.csv`, `group-members.csv`, `password-policy.txt`) and the relevant company records in `scenario/`.
