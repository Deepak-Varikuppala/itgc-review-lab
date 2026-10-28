# Lab build

| Machine | Address | Built by |
|---|---|---|
| Domain controller `linux` | 192.168.64.10 | `dc/build-directory.sh` |
| Application server `linux2` | 192.168.64.11 | `app/join-domain.sh`, then `app/install.sh` |
| Office PC `NW-PC01` | DHCP on 192.168.64.0/24 | `pc/setup-pc.ps1` |

The servers are Ubuntu Server 26.04 virtual machines in UTM. The PC is a Windows 11 Pro (ARM64) virtual machine in UTM.

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

## Application server

An Ubuntu Server 26.04 virtual machine at 192.168.64.11, joined to the domain. It runs:

* **Gitea 1.27.3**, where Northwind's developers keep the finance application's code and review each other's changes through pull requests (port 3000).
* **The finance application** (port 8080), deployed with `sudo northwind-deploy <ticket>`, which records every deployment in `/var/log/northwind/deployments.log`.
* **A nightly backup** of the finance database at 01:30 UTC, logged to `/var/log/northwind/backup.log`.

Run from your Mac, with both servers switched on:

```bash
scp -r lab labadmin@192.168.64.11:~/
ssh -t labadmin@192.168.64.11 'sudo bash ~/lab/app/join-domain.sh'
ssh -t labadmin@192.168.64.11 'sudo bash ~/lab/app/install.sh'
```

`join-domain.sh` points the server at the domain controller for DNS, joins `northwind.internal` with realmd and SSSD (it asks for the domain Administrator password), and lets only GG-IT members sign in. Server rights then follow domain groups: IT-Server-Admins get full administrator rights and Change-Deployers may run the deployment tool.

`install.sh` installs Gitea and the finance application and loads Northwind's history for Q3 2026. The server is built after the quarter it is audited for, so the history is recreated from `app/history.py`, which defines every change, deployment and backup run in the quarter. `app/build_repo.py` puts each change through Gitea as it would really happen: the author pushes a branch and opens a pull request, the reviewer approves it and the merger merges it, each acting as themselves through the Gitea API. It then moves the dates Gitea recorded to the dates in the history. Both scripts are safe to run again.

The history includes the kinds of things a real quarter can contain: changes pushed straight to `main`, a change merged without review, developers deploying their own changes, approvals given after the event, an emergency change that skipped its review, and missed and failed backups. The server is also left with changes made outside the change process, such as a supplier's support account and a scheduled job nobody approved. Finding these is the job of the review.

Generated passwords are kept in `/root/northwind-lab/gitea-passwords.csv` on the server, readable by root only.

## Office PC

A Windows 11 Pro virtual machine, created in UTM with **Virtualize > Windows**, with "Install drivers and SPICE tools" ticked, 4 GB of memory, 4 cores, a 64 GB disk and **Shared Network**. Home cannot join a domain, so choose Pro during installation. During first setup, a local account called `pcadmin` is created (Shift+F10, then `start ms-cxh:localonly`), and the UTM guest tools are installed from the CD drive for the network driver.

To manage it from the Mac, OpenSSH Server is switched on in an administrator PowerShell window, with the Mac's lab key authorised for administrators:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service sshd -StartupType Automatic; Start-Service sshd
New-ItemProperty -Path HKLM:\SOFTWARE\OpenSSH -Name DefaultShell -PropertyType String -Force `
  -Value C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
Set-Content C:\ProgramData\ssh\administrators_authorized_keys '<contents of northwind_lab.pub>' -Encoding ascii
icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant 'Administrators:F' /grant 'SYSTEM:F'
```

Then, from the Mac, with the domain controller switched on:

```bash
scp lab/pc/setup-pc.ps1 pcadmin@<pc address>:
ssh pcadmin@<pc address> 'powershell -NoProfile -ExecutionPolicy Bypass -File setup-pc.ps1 -DomainPassword <password>'
# the PC joins northwind.internal as NW-PC01 and restarts; then run the same command again
```

The first run points the PC at the domain controller for DNS, renames it NW-PC01 and joins the domain. The second run leaves it as it stood at the end of Q3, with a member of IT support in its local Administrators group.
