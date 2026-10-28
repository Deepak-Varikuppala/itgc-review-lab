<#
.SYNOPSIS
Sets up Northwind's office PC and joins it to the northwind.internal domain.

.DESCRIPTION
Run as an administrator on a fresh Windows 11 Pro installation, in two stages:

  1. Points the PC at the domain controller for DNS, names it NW-PC01 and joins the
     domain. The PC then restarts.
  2. Run again after the restart. Leaves the PC as it stood at the end of Q3 2026,
     including a change made outside Northwind's procedures.

  powershell -NoProfile -ExecutionPolicy Bypass -File setup-pc.ps1 -DomainPassword <password>

The password is for the domain's built in Administrator account and is used only to
join the domain.
#>
param(
    [string]$DomainPassword
)

$ErrorActionPreference = 'Stop'
$DcIp = '192.168.64.10'
$Domain = 'northwind.internal'
$NetBios = 'NORTHWIND'
$Name = 'NW-PC01'

function Step([string]$Text) { Write-Output ''; Write-Output "== $Text" }

$os = Get-CimInstance Win32_OperatingSystem
if ($os.Caption -notmatch 'Pro|Enterprise|Education') {
    throw "$($os.Caption) cannot join a domain. Install Windows 11 Pro."
}
$computer = Get-CimInstance Win32_ComputerSystem

if (-not $computer.PartOfDomain) {
    if (-not $DomainPassword) { throw 'Give the domain Administrator password with -DomainPassword.' }

    Step 'Using the domain controller for DNS'
    $address = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -like '192.168.64.*' } | Select-Object -First 1
    if (-not $address) { throw 'No address on the lab network (192.168.64.x). Check the VM uses Shared Network.' }
    Set-DnsClientServerAddress -InterfaceIndex $address.InterfaceIndex -ServerAddresses $DcIp
    Clear-DnsClientCache
    $srv = Resolve-DnsName "_ldap._tcp.$Domain" -Type SRV -ErrorAction SilentlyContinue
    if (-not $srv) { throw "The domain controller at $DcIp is not answering DNS for $Domain." }
    Write-Output "   PC address $($address.IPAddress); domain controller found: $(($srv | Where-Object Type -eq 'SRV' | Select-Object -First 1).NameTarget)"

    Step 'Checking the clocks agree (Kerberos needs them within 5 minutes)'
    $chart = w32tm /stripchart /computer:$DcIp /samples:1 /dataonly 2>&1 | Select-Object -Last 1
    Write-Output "   offset from the domain controller: $chart"

    Step "Joining $Domain as $Name"
    $secure = ConvertTo-SecureString $DomainPassword -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential("$NetBios\Administrator", $secure)
    if ($env:COMPUTERNAME -ne $Name) {
        Add-Computer -DomainName $Domain -NewName $Name -Credential $credential -Force
    } else {
        Add-Computer -DomainName $Domain -Credential $credential -Force
    }
    Write-Output "== JOINED $Domain. The PC restarts now; run this script again afterwards."
    Restart-Computer -Force
    return
}

Step "Joined to $($computer.Domain) as $env:COMPUTERNAME"

# IT support added Liam Brooks to the PC's administrators in August so he could install a
# printer driver, and the access was never taken away.
Step 'Settings as at the end of Q3 2026'
$member = "$NetBios\liam.brooks"
$current = Get-LocalGroupMember -Group 'Administrators' | Select-Object -ExpandProperty Name
if ($current -notcontains $member) {
    Add-LocalGroupMember -Group 'Administrators' -Member $member
    Write-Output "   added $member to Administrators"
}

Step 'Local Administrators group'
Get-LocalGroupMember -Group 'Administrators' | ForEach-Object { Write-Output "   $($_.Name) ($($_.ObjectClass))" }

Step 'PC READY'
