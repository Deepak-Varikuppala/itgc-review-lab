"""Findings from the Q3 2026 logical access review.

Each finding follows the standard structure: condition (what was found), criteria (what
should be the case), cause, effect (the risk) and recommendation. Causes are based on
the evidence and are to be confirmed with management.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    finding_id: str
    title: str
    rating: str  # High, Medium, Low
    tests: tuple[str, ...]
    policy: str
    condition: str
    criteria: str
    cause: str
    effect: str
    recommendation: str


FINDINGS = [
    Finding(
        "F1",
        "A leaver's account was still active and able to approve payments",
        "High",
        ("AC-01", "AC-04"),
        "3.3",
        "Mark Taylor (Financial Controller) left on 29 August 2026. On 27 October 2026, 56 days "
        "after the deadline for disabling his account, the account mark.taylor was still "
        "enabled, still in Finance-Payments-Approvers and GG-Finance, and had not been moved to "
        "Leavers. The directory records a sign in on 27 October 2026, after his leaving date. "
        "The other two leavers in the period were handled correctly.",
        "Policy clause 3.3: a leaver's account must be disabled within 1 working day of their "
        "last day, removed from all groups and moved to Leavers.",
        "Leavers are removed only when HR tells IT. There is no regular check of the directory "
        "against the HR leavers list, so a missed notification is not picked up.",
        "A former employee, or anyone who knows the password, could approve supplier payments "
        "after leaving. The recorded sign in after the leaving date needs to be investigated "
        "to establish who used the account.",
        "Disable mark.taylor now, remove its group memberships and review what the account did "
        "after 29 August 2026. Reconcile the directory against the HR leavers list every week, "
        "and make IT acknowledge each HR leaver notification.",
    ),
    Finding(
        "F2",
        "Full domain administrator rights were held without approval",
        "High",
        ("AC-10", "AC-13"),
        "5.1, 5.2, 5.3",
        "Two of the five members of Domain Admins are not allowed by policy. liam.brooks is an "
        "everyday personal account belonging to an IT Support Analyst whose approved access "
        "(REQ-2023-047) is the Helpdesk role for password resets only. svc-backup is a service "
        "account; its exception EX-2024-02 covers its non-expiring password, not Domain Admins "
        "membership.",
        "Policy clauses 5.1 to 5.3: Domain Admins is limited to separate adm. accounts with "
        "approved access; everyday accounts must not hold administrator rights; service "
        "accounts need a recorded exception to be Domain Admins.",
        "Privileged access appears to be granted directly by IT without a matching approved "
        "request, and nothing compares Domain Admins membership with approvals.",
        "Domain Admins can change any account, password or setting in the domain. An everyday "
        "account is exposed to phishing and web browsing, and a compromised service account "
        "with these rights would give an attacker full control.",
        "Remove liam.brooks from Domain Admins; delegate password reset rights to Helpdesk "
        "only. Give svc-backup only the rights the backup job needs, or record and approve an "
        "exception. Review Domain Admins membership every month.",
    ),
    Finding(
        "F3",
        "A shared account can create supplier payments",
        "High",
        ("AC-09", "AC-13", "AC-08"),
        "4.4",
        "finance.shared is a login used by the finance team. It is a member of "
        "Finance-Payments-Initiators, has no approved access request, and its password is set "
        "never to expire without an exception.",
        "Policy clause 4.4: every account belongs to one named person or system, and shared "
        "accounts are not allowed. Clause 4.3: only approved service accounts may have "
        "non-expiring passwords.",
        "The account appears to have been set up for convenience and was never put through "
        "the access request process.",
        "Payments created with this account cannot be traced to a person, so a fraudulent or "
        "mistaken payment could not be attributed. The password is likely known to several "
        "people, including any who have since left, and is never changed.",
        "Disable finance.shared. Give each finance team member who needs to create payments "
        "their own approved access. If a shared mailbox is needed, use mailbox delegation "
        "rather than a shared login.",
    ),
    Finding(
        "F4",
        "A member of staff kept payment access after moving to Sales",
        "Medium",
        ("AC-02",),
        "3.2",
        "Emma Wilson transferred from Finance (Accounts Payable Clerk) to Sales (Account "
        "Manager) on 14 September 2026. On 27 October 2026, 36 days after the deadline, her "
        "account still had Finance-Payments-Initiators and GG-Finance. Her new Sales access was "
        "approved promptly (REQ-2026-084), but nothing was removed.",
        "Policy clause 3.2: access no longer needed must be removed within 5 working days of a "
        "change of role.",
        "The transfer was treated as a request for new access only. There is no step to "
        "remove the previous role's access.",
        "Staff build up access they do not need. Here a Sales employee can still create "
        "supplier payments.",
        "Remove Finance-Payments-Initiators and GG-Finance from emma.wilson. Change the mover "
        "process so the old line manager confirms which access to remove.",
    ),
    Finding(
        "F5",
        "A contractor's account stayed active after the contract ended",
        "Medium",
        ("AC-04", "AC-05", "AC-06"),
        "3.4, 3.5",
        "Leo Martin's contract with DevPartners Ltd ended on 30 June 2026. The account "
        "leo.martin was still enabled on 27 October 2026, with no expiry date set and "
        "membership of Developers and GG-IT. It has never been used.",
        "Policy clause 3.4: contractor accounts must expire on the contract end date. Clause "
        "3.5: accounts unused for 45 days must be disabled.",
        "Expiry dates are not set when contractor accounts are created, and contractors are "
        "not covered by the HR leaver process.",
        "An unused, forgotten account is an easy target, because misuse is unlikely to be noticed.",
        "Disable leo.martin. Make an expiry date mandatory when creating contractor accounts, "
        "and include the contractor list in the weekly leaver reconciliation.",
    ),
    Finding(
        "F6",
        "The password and lockout settings are weaker than policy",
        "High",
        ("AC-07",),
        "4.1, 4.2",
        "The domain allows passwords of 8 characters against a policy minimum of 12, and the "
        "account lockout threshold is 0, so accounts never lock however many wrong passwords "
        "are tried. Complexity, history and maximum age meet the policy.",
        "Policy clause 4.1: passwords of at least 12 characters. Clause 4.2: accounts lock "
        "for at least 15 minutes after 5 failed attempts.",
        "The domain settings were not updated when the policy was revised to version 2.1 in "
        "January 2026.",
        "Every account in the domain can be attacked by unlimited password guessing, and "
        "shorter passwords make that guessing far quicker.",
        "Set the minimum password length to 12 and the lockout threshold to 5. Check the "
        "domain settings against the policy whenever the policy changes.",
    ),
    Finding(
        "F7",
        "Passwords set never to expire without approval",
        "Medium",
        ("AC-08",),
        "4.3",
        "Two accounts have non-expiring passwords without an approved exception: "
        "sarah.mitchell, a personal account, and finance.shared (see F3). The two service "
        "accounts with this setting have approved exceptions.",
        "Policy clause 4.3: only service accounts with an approved exception may have "
        "passwords that never expire.",
        "The setting can be applied by any administrator without an exception being recorded.",
        "A password that never changes stays useful to anyone who has learned it.",
        "Remove the setting from sarah.mitchell and finance.shared. Report every account with "
        "this setting monthly and compare it with the exception register.",
    ),
    Finding(
        "F8",
        "One person can create and approve payments, and approved that access herself",
        "High",
        ("AC-11", "AC-12"),
        "6.1, 6.2",
        "Priya Shah (Senior Accountant) is in both Finance-Payments-Initiators and "
        "Finance-Payments-Approvers. The approver access was requested and approved by Priya "
        "Shah herself on 3 November 2025 (REQ-2025-118), described as cover during a busy "
        "period. The access was never removed.",
        "Policy clause 6.1: no one may hold both payment roles. Clause 6.2: nobody may approve "
        "their own access request.",
        "The access request process does not stop a requester from approving their own "
        "request, and temporary access is not given an end date.",
        "One person can create and approve a supplier payment with no second check, which is "
        "the classic route to payment fraud. Payments approved by Priya Shah should be "
        "reviewed to confirm none were also created by her.",
        "Remove Finance-Payments-Approvers from priya.shah. Review all payments she has "
        "approved since November 2025. Block self-approval in the request process, and give "
        "temporary access an end date.",
    ),
    Finding(
        "F9",
        "An unused service account",
        "Low",
        ("AC-06",),
        "3.5",
        "svc-financeapp has never signed in, although it has an exception for a "
        "non-expiring password.",
        "Policy clause 3.5: accounts unused for 45 days must be disabled unless an exception "
        "is approved.",
        "The account may have been created for an integration that was not used, or the "
        "application may authenticate in another way.",
        "An unused account with a long lived password adds risk without benefit.",
        "Confirm with the finance application owner whether the account is needed. Disable it "
        "if not; if it is, record the dormancy in its exception.",
    ),
    Finding(
        "F10",
        "Quarterly access reviews could not be evidenced",
        "Medium",
        ("AC-14",),
        "7.1",
        "No evidence of a Q3 2026 review of the privileged and payments groups was provided.",
        "Policy clause 7.1: system owners review these groups every quarter and keep signed "
        "off evidence.",
        "Reviews do not appear to be scheduled or assigned to named owners.",
        "The review is the control that catches failures in the joiner, mover and leaver "
        "processes. F1, F2, F4 and F8 would all have been visible to an effective review.",
        "Assign an owner to each group, schedule the reviews, and keep the signed off list "
        "with the changes made as a result.",
    ),
]

OBSERVATIONS = [
    (
        "O1",
        "The built in Administrator account is in use",
        "The built in Administrator account signed in on 27 October 2026. Named adm. accounts "
        "exist for administrative work. The built in account should be kept as a break glass "
        "account with a vaulted password, and every use of it reviewed.",
    ),
]


def by_id(finding_id: str) -> Finding:
    return next(f for f in FINDINGS if f.finding_id == finding_id)
