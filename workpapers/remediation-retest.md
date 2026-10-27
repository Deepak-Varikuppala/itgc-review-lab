# Remediation retest

Evidence extracted after remediation on 2026-10-27 (`directory-20261027T033513Z`). Each finding was retested by checking its condition directly in the new extraction.

| Finding | Rating | Status | Retest result |
|---|---|---|---|
| F1: A leaver's account was still active and able to approve payments | High | **Resolved, follow up open** | mark.taylor is disabled, has no group memberships and is in Leavers. The sign in after the leaving date still needs to be investigated. |
| F2: Full domain administrator rights were held without approval | High | **Resolved** | Domain Admins now contains only Administrator and the adm. accounts: Administrator, adm.akhan, adm.jcarter. |
| F3: A shared account can create supplier payments | High | **Resolved** | finance.shared is disabled with no group memberships. |
| F4: A member of staff kept payment access after moving to Sales | Medium | **Resolved** | emma.wilson holds only Sales access: GG-Sales. |
| F5: A contractor's account stayed active after the contract ended | Medium | **Resolved, follow up open** | leo.martin is disabled with no group memberships. Setting expiry dates on new contractor accounts is a process change to confirm on the next contractor joiner. |
| F6: The password and lockout settings are weaker than policy | High | **Resolved** | Minimum password length 12; lockout after 5 attempts. |
| F7: Passwords set never to expire without approval | Medium | **Resolved** | Only service accounts with approved exceptions keep non-expiring passwords. |
| F8: One person can create and approve payments, and approved that access herself | High | **Resolved, follow up open** | Nobody now holds both payment roles. The review of payments approved by priya.shah since November 2025, and blocking self approval in the request process, remain open. |
| F9: An unused service account | Low | **Resolved** | svc-financeapp is disabled. |
| F10: Quarterly access reviews could not be evidenced | Medium | **Open** | Process change. The first quarterly review is due at the end of Q4 2026 and will be tested then. |
