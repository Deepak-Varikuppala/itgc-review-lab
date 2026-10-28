# Audit scripts

| Script | Runs on | What it does |
|---|---|---|
| `collect_evidence.py` | Domain controller | Read only extraction of users, groups, privileged groups and password policy, with an extraction log and SHA-256 hashes |
| `collect_app_evidence.py` | App server | Read only extraction from Gitea's database and repository (accounts, access, pull requests, reviews, branch protection, commits on main) and the server (deployment log, deployment tool, backup log and job) |
| `collect_host_evidence.py` | Each Linux server | Read only extraction of local accounts, sudo rules, effective SSH settings, domain sign in settings, scheduled jobs, time synchronisation and patch status |
| `collect_pc_evidence.ps1` | The office PC | Read only extraction of local accounts, local Administrators members, password policy, time synchronisation and Windows Update status |
| `run_tests.py` | Anywhere | Runs the 14 logical access tests on the directory and builds its workpaper |
| `run_change_ops_tests.py` | Anywhere | Runs the 18 change management, IT operations and server access tests, including the two sampled tests, and builds their workpaper |
| `make_report.py` | Anywhere | Writes both reports, both testing programmes and the overall summary from the results |
| `retest.py` | Anywhere | Checks each logical access finding's condition in an extraction taken after remediation |
| `findings.py`, `change_ops_findings.py` | | The findings: condition, criteria, cause, effect and recommendation |
| `workpaper.py` | | Builds the Excel workpapers |

## 1. Collect evidence

Run from your Mac, with the domain controller switched on:

```bash
scp -r audit labadmin@192.168.64.10:~/
ssh -t labadmin@192.168.64.10 'sudo python3 ~/audit/collect_evidence.py --out ~/evidence'
scp -r labadmin@192.168.64.10:~/evidence ./
```

The extraction creates `evidence/directory-<timestamp>/`:

| File | Contents |
|---|---|
| `users.csv` | Every account: department, manager, location, enabled, password settings, last logon, groups |
| `group-members.csv` | Every group and its members |
| `privileged-groups.txt` | Members of Domain Admins, Enterprise Admins, Schema Admins and Administrators |
| `password-policy.txt` | The domain password and lockout settings |
| `raw-users.ldif` | The raw directory output the CSV was built from, so the extraction can be re-performed |
| `extraction-log.txt` | Who ran it, when, on which host, every command run, and record counts |
| `SHA256SUMS` | Hashes of every file |

Before relying on it, check the record counts in `extraction-log.txt` match, and that `shasum -a 256 -c SHA256SUMS` passes. `run_tests.py` and `retest.py` refuse to run on evidence whose hashes do not match.

### App server and Linux servers

Run from your Mac, with both servers switched on:

```bash
scp -r audit labadmin@192.168.64.11:~/ && scp -r audit labadmin@192.168.64.10:~/
ssh -t labadmin@192.168.64.11 'sudo python3 ~/audit/collect_app_evidence.py --out ~/evidence && sudo python3 ~/audit/collect_host_evidence.py --out ~/evidence'
ssh -t labadmin@192.168.64.10 'sudo python3 ~/audit/collect_host_evidence.py --out ~/evidence'
```

For the office PC:

```bash
scp audit/collect_pc_evidence.ps1 pcadmin@<pc address>:
ssh pcadmin@<pc address> 'powershell -NoProfile -ExecutionPolicy Bypass -File collect_pc_evidence.ps1 -Out C:\Users\pcadmin\evidence'
scp -r 'pcadmin@<pc address>:evidence/pc-*' evidence/
```

This creates `evidence/app-<timestamp>/` on the app server and `evidence/host-<hostname>-<timestamp>/` on each server. Copy them back with `scp -r`. Each has its own `extraction-log.txt` with record counts and a `SHA256SUMS` file.

## 2. Test and report

```bash
python3 audit/run_tests.py --evidence evidence/directory-<timestamp>
python3 audit/run_change_ops_tests.py --app evidence/app-<timestamp> \
    --host evidence/host-linux-<timestamp> --host evidence/host-linux2-<timestamp> \
    --directory evidence/directory-<timestamp>
python3 audit/make_report.py
```

`run_change_ops_tests.py` uses the directory extraction for the end of the period (for Change-Approvers and the AC-18 population). The two sampled tests, CM-04 and AC-18, select their items with `random.Random(20261001)`, so the same evidence always gives the same sample.

## 3. Remediate and retest (logical access)

```bash
scp lab/dc/remediate.sh labadmin@192.168.64.10:~/
ssh -t labadmin@192.168.64.10 'sudo bash ~/remediate.sh'
# collect a fresh extraction as in step 1, then:
python3 audit/retest.py --evidence evidence/directory-<new timestamp>
python3 audit/make_report.py
```
