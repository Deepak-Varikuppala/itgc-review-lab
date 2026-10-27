# Northwind Retail: Access Control Policy

| | |
|---|---|
| Version | 2.1 |
| Owner | Head of IT (James Carter) |
| Approved by | Chief Executive |
| Approved on | 15 January 2026 |
| Next review | January 2027 |

## 1. Purpose and scope

This policy sets the rules for giving, changing and removing access to Northwind Retail's IT systems. It applies to every account in the `northwind.internal` directory and to every application that uses it, including the finance application. It covers employees, contractors, shared accounts and service accounts.

## 2. Responsibilities

| Role | Responsibility |
|---|---|
| Line manager | Requests access for their staff and confirms it matches the job |
| HR | Tells IT about every joiner, mover and leaver on or before the effective date |
| Head of IT | Approves all privileged access and all exceptions to this policy |
| IT administrators | Set up, change and remove access only when an approved request exists |
| System owners | Review who has access to their system every quarter |

## 3. User access management

**3.1 Joiners.** Access is given only after an access request has been approved by the person's line manager. Privileged access also needs approval from the Head of IT. Access must match the person's job.

**3.2 Movers.** When someone changes job, access they no longer need must be removed within 5 working days of the change.

**3.3 Leavers.** A leaver's account must be disabled within 1 working day of their last day. It is then removed from all groups and moved to the Leavers area of the directory.

**3.4 Contractors.** Every contractor has a named Northwind sponsor. Their account must be set to expire on the contract end date.

**3.5 Dormant accounts.** An account that has not been used for 45 days must be disabled unless the Head of IT approves an exception.

## 4. Authentication

**4.1 Passwords.** Passwords must be at least 12 characters long and meet complexity rules. The last 24 passwords cannot be reused. Passwords expire after at most 90 days.

**4.2 Lockout.** An account must lock for at least 15 minutes after 5 failed sign-in attempts.

**4.3 Non-expiring passwords.** Only service accounts may have passwords that never expire, and only with an approved entry in the exception register.

**4.4 Individual accountability.** Every account belongs to one named person or one named system. Shared accounts used by more than one person are not allowed.

## 5. Privileged access

**5.1** Membership of Domain Admins is limited to separate administrator accounts named `adm.<name>`, belonging to IT staff whose job needs it.

**5.2** Accounts used for day to day work, such as email and browsing, must never hold administrator rights.

**5.3** Service accounts must not be members of Domain Admins unless an exception approved by the Head of IT is recorded in the exception register.

**5.4** IT support staff are given the Helpdesk role, which allows password resets only.

## 6. Segregation of duties

**6.1** No one may hold both the ability to create supplier payments (Finance-Payments-Initiators) and the ability to approve them (Finance-Payments-Approvers).

**6.2** Nobody may approve their own access request.

**6.3** Developers must not deploy their own changes to production. A different person must approve and deploy each change.

## 7. Access reviews

**7.1** Every quarter, system owners review who belongs to Domain Admins, IT-Server-Admins, Finance-Payments-Initiators and Finance-Payments-Approvers. Any access that is no longer needed is removed. The review is signed off, and the evidence is kept for 3 years.

## 8. Exceptions

Any exception to this policy must be recorded in the exception register with a business reason, approval by the Head of IT, and a review date no more than 12 months away.
