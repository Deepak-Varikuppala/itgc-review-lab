# Audit scripts

| Script | Runs on | What it does |
|---|---|---|
| `collect_evidence.py` | Domain controller | Read only extraction of users, groups, privileged groups and password policy, with an extraction log and SHA-256 hashes |
| `run_tests.py` | Anywhere | Runs the 14 logical access tests and builds the workpaper |
| `make_report.py` | Anywhere | Writes the report and the testing programme from the results |
| `retest.py` | Anywhere | Checks each finding's condition in an extraction taken after remediation |
| `findings.py` | | The findings: condition, criteria, cause, effect and recommendation |
| `workpaper.py` | | Builds the Excel workpaper |

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

## 2. Test and report

```bash
python3 audit/run_tests.py --evidence evidence/directory-<timestamp>
python3 audit/make_report.py
```

## 3. Remediate and retest

```bash
scp lab/dc/remediate.sh labadmin@192.168.64.10:~/
ssh -t labadmin@192.168.64.10 'sudo bash ~/remediate.sh'
# collect a fresh extraction as in step 1, then:
python3 audit/retest.py --evidence evidence/directory-<new timestamp>
python3 audit/make_report.py
```
