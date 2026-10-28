# Northwind Retail: IT General Controls Review, Q3 2026

A summary of the two reports that make up the review of Northwind Retail's IT general controls for 1 July to 30 September 2026:

* [Logical access review](logical-access-review.md): the Active Directory domain (AC-01 to AC-14), with a remediation retest.
* [Change management, IT operations and server access review](change-and-operations-review.md): the finance application, its code repository and the two Linux servers (AC-15 to AC-18, CM-01 to CM-07, OP-01 to OP-07).

## Results by area

| Area | Tests | Effective | With exceptions | Findings | Conclusion |
|---|---|---|---|---|---|
| Logical access: directory (AC-01 to AC-14) | 14 | 1 | 13 | F1, F2, F3, F4, F5, F6, F7, F8, F9, F10 | **Not effective** |
| Logical access: servers (AC-15 to AC-18) | 4 | 0 | 4 | F2, F5, F8, F12, F16, F17, F18 | **Not effective** |
| Change management (CM-01 to CM-07) | 7 | 0 | 7 | F11, F12, F13, F14, F15, F16 | **Not effective** |
| IT operations (OP-01 to OP-07) | 7 | 1 | 6 | F19, F20, F21, F22 | **Not effective** |

**32 controls were tested and 22 findings raised: 12 high, 9 medium and 1 low.** IT general controls over the finance application and the systems it depends on were not operating effectively in the period, so they cannot be relied on to support the accuracy of the finance application's records without further work.

## All findings

| ID | Finding | Rating | Status |
|---|---|---|---|
| [F1](logical-access-review.md#f1) | A leaver's account was still active and able to approve payments | High | Resolved, follow up open |
| [F2](logical-access-review.md#f2) | Full domain administrator rights were held without approval | High | Resolved |
| [F3](logical-access-review.md#f3) | A shared account can create supplier payments | High | Resolved |
| [F4](logical-access-review.md#f4) | A member of staff kept payment access after moving to Sales | Medium | Resolved |
| [F5](logical-access-review.md#f5) | A contractor's account stayed active after the contract ended | Medium | Resolved, follow up open |
| [F6](logical-access-review.md#f6) | The password and lockout settings are weaker than policy | High | Resolved |
| [F7](logical-access-review.md#f7) | Passwords set never to expire without approval | Medium | Resolved |
| [F8](logical-access-review.md#f8) | One person can create and approve payments, and approved that access herself | High | Resolved, follow up open |
| [F9](logical-access-review.md#f9) | An unused service account | Low | Resolved |
| [F10](logical-access-review.md#f10) | Quarterly access reviews could not be evidenced | Medium | Open |
| [F11](change-and-operations-review.md#f11) | Changes reached production without a ticket or a code review | High | Open, awaiting remediation |
| [F12](change-and-operations-review.md#f12) | Developers deployed their own changes | High | Open, awaiting remediation |
| [F13](change-and-operations-review.md#f13) | Changes were approved only after they were deployed | Medium | Open, awaiting remediation |
| [F14](change-and-operations-review.md#f14) | An emergency change skipped the emergency procedure | Medium | Open, awaiting remediation |
| [F15](change-and-operations-review.md#f15) | The change tools do not enforce the change process | High | Open, awaiting remediation |
| [F16](change-and-operations-review.md#f16) | A contractor changed the code after his contract ended | High | Open, awaiting remediation |
| [F17](change-and-operations-review.md#f17) | Unapproved administrator rights on the application server | High | Open, awaiting remediation |
| [F18](change-and-operations-review.md#f18) | SSH settings on the servers are weaker than the Standard | Medium | Open, awaiting remediation |
| [F19](change-and-operations-review.md#f19) | Backups failed or did not run on 6 nights, and 5 went unnoticed | High | Open, awaiting remediation |
| [F20](change-and-operations-review.md#f20) | No restore was tested in the quarter | Medium | Open, awaiting remediation |
| [F21](change-and-operations-review.md#f21) | An unapproved job runs a developer's script as root | High | Open, awaiting remediation |
| [F22](change-and-operations-review.md#f22) | The domain controller's clock was found badly wrong twice | Medium | Open, awaiting remediation |

Statuses for F1 to F10 come from the remediation retest. F11 to F22 are awaiting management responses and remediation.
