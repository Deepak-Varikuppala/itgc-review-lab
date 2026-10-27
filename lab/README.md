# Lab build

## Domain controller

An Ubuntu Server 26.04 virtual machine at 192.168.64.10, set up as a Samba Active Directory domain controller for `northwind.internal`.

Run from your Mac, with the domain controller switched on:

```bash
scp -r lab labadmin@192.168.64.10:~/
ssh -t labadmin@192.168.64.10 'sudo bash ~/lab/dc/build-directory.sh'
```

`build-directory.sh` reads `dc/staff.csv` and creates the organisational units, groups and accounts, sets the domain password policy, and signs in as the active accounts so they have last logon dates. It is safe to run again: anything that already exists is left alone.

Generated passwords are kept on the domain controller in `/root/northwind-lab/account-passwords.csv`, readable by root only.

## Remediation

`dc/remediate.sh` applies the fixes agreed for the findings, each labelled with its finding number. It is also safe to run again. See [audit/README.md](../audit/README.md) for the retest.
