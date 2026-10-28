<#
.SYNOPSIS
Collect ITGC evidence from a Northwind Windows PC.

.DESCRIPTION
Read only. Exports the PC's local accounts, the members of its local Administrators
group, the password policy, time synchronisation and Windows Update status into a dated
evidence folder, with an extraction log and SHA-256 hashes of every file.

Run as an administrator on the PC:

  powershell -NoProfile -ExecutionPolicy Bypass -File collect_pc_evidence.ps1 -Out $HOME\evidence

Files are written as UTF-8 with Unix line endings, so the hashes can be checked on any
machine with: shasum -a 256 -c SHA256SUMS
#>
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$TimeSource = '192.168.64.10'
)

$ErrorActionPreference = 'Stop'
$Log = New-Object System.Collections.Generic.List[string]
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function Clean([string]$Text) {
    # Windows output can contain typographic dashes; they are written as hyphens.
    if ($null -eq $Text) { return '' }
    return $Text.Replace([string][char]0x2013, '-').Replace([string][char]0x2014, '-')
}

function Save([string]$Name, [string[]]$Lines) {
    $text = (Clean (($Lines | ForEach-Object { $_ }) -join "`n")).TrimEnd() + "`n"
    [System.IO.File]::WriteAllText((Join-Path $Folder $Name), $text, $Utf8)
}

function SaveCsv([string]$Name, $Rows, [string[]]$Columns) {
    $lines = @('"' + ($Columns -join '","') + '"')
    foreach ($row in $Rows) {
        $values = foreach ($c in $Columns) { '"' + ([string]$row.$c).Replace('"', '""') + '"' }
        $lines += ($values -join ',')
    }
    Save $Name $lines
    return @($Rows).Count
}

function Run([string]$Command, [scriptblock]$Block) {
    # Native commands write some messages to the error stream; keep them with the output.
    $Log.Add("> $Command")
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { return @(& $Block 2>&1 | ForEach-Object { [string]$_ }) }
    catch { return @("(failed: $($_.Exception.Message))") }
    finally { $ErrorActionPreference = $previous }
}

function IsoTime($Value) {
    if ($null -eq $Value -or $Value -eq '') { return '' }
    return ([datetime]$Value).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss') + '+00:00'
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run as an administrator: Windows Update history and some settings need it.'
}

$Now = (Get-Date).ToUniversalTime()
$Stamp = $Now.ToString('yyyyMMddTHHmmssZ')
$Folder = Join-Path $Out "pc-$($env:COMPUTERNAME.ToLower())-$Stamp"
New-Item -ItemType Directory -Path $Folder -Force | Out-Null
$Operator = [Security.Principal.WindowsIdentity]::GetCurrent().Name

# 1. The PC itself.
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$Log.Add('> Get-CimInstance Win32_OperatingSystem, Win32_ComputerSystem')
$ips = Run 'Get-NetIPAddress -AddressFamily IPv4' {
    Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } |
        ForEach-Object { "$($_.InterfaceAlias): $($_.IPAddress)" }
}
Save 'host.txt' (@(
    "Computer name: $($env:COMPUTERNAME)",
    "Domain member: $($cs.PartOfDomain)",
    "Domain: $($cs.Domain)",
    "Windows: $($os.Caption) $($os.Version) (build $($os.BuildNumber))",
    "Architecture: $($os.OSArchitecture)",
    "Installed (UTC): $(IsoTime $os.InstallDate)",
    "Last started (UTC): $(IsoTime $os.LastBootUpTime)",
    '', '# IPv4 addresses') + $ips)

# 2. Local accounts.
$Log.Add('> Get-LocalUser')
$users = Get-LocalUser | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{
        username = $_.Name; enabled = $(if ($_.Enabled) { 'Yes' } else { 'No' })
        description = $_.Description; password_required = $(if ($_.PasswordRequired) { 'Yes' } else { 'No' })
        password_last_set = IsoTime $_.PasswordLastSet
        password_expires = $(if ($_.PasswordExpires) { IsoTime $_.PasswordExpires } else { 'Never' })
        last_logon = IsoTime $_.LastLogon; sid = $_.SID.Value
    }
}
$nUsers = SaveCsv 'local-accounts.csv' $users @('username', 'enabled', 'description',
    'password_required', 'password_last_set', 'password_expires', 'last_logon', 'sid')

# 3. Members of the local Administrators group, by two methods that should agree.
$Log.Add("> Get-LocalGroupMember -Group 'Administrators'")
$admins = Get-LocalGroupMember -Group 'Administrators' | Sort-Object Name | ForEach-Object {
    $enabled = ''
    if ($_.PrincipalSource -eq 'Local' -and $_.ObjectClass -eq 'User') {
        $local = Get-LocalUser -SID $_.SID
        $enabled = $(if ($local.Enabled) { 'Yes' } else { 'No' })
    }
    [pscustomobject]@{
        member = $_.Name; type = $_.ObjectClass; source = [string]$_.PrincipalSource
        enabled = $enabled; sid = $_.SID.Value
    }
}
$nAdmins = SaveCsv 'local-administrators.csv' $admins @('member', 'type', 'source', 'enabled', 'sid')
$netAdmins = Run 'net localgroup Administrators' { net localgroup Administrators }
Save 'local-administrators.txt' $netAdmins
$start = [array]::IndexOf($netAdmins, ($netAdmins | Where-Object { $_ -match '^-{5,}' } | Select-Object -First 1))
$nNet = @($netAdmins[($start + 1)..($netAdmins.Count - 1)] |
    Where-Object { $_.Trim() -and $_ -notmatch 'command completed' }).Count

# 4. Password and lockout policy.
Save 'password-policy.txt' (@('# net accounts (this PC)') + (Run 'net accounts' { net accounts }) +
    @('', '# net accounts /domain') + (Run 'net accounts /domain' { net accounts /domain }))

# 5. Time synchronisation.
Save 'time-sync.txt' (@('# w32tm /query /status /verbose') +
    (Run 'w32tm /query /status /verbose' { w32tm /query /status /verbose }) +
    @('', '# w32tm /query /source') + (Run 'w32tm /query /source' { w32tm /query /source }) +
    @('', "# w32tm /stripchart /computer:$TimeSource /samples:3 /dataonly") +
    (Run "w32tm /stripchart /computer:$TimeSource /samples:3 /dataonly" {
        w32tm /stripchart /computer:$TimeSource /samples:3 /dataonly }))

# 6. Windows Update: settings, updates waiting, and what was installed.
$Log.Add('> Windows Update agent: search for updates not yet installed, and update history')
$session = New-Object -ComObject Microsoft.Update.Session
$searcher = $session.CreateUpdateSearcher()
$pending = @()
$searchNote = 'completed'
try {
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
    foreach ($u in $result.Updates) {
        $categories = @($u.Categories | ForEach-Object { $_.Name }) -join '; '
        $pending += [pscustomobject]@{
            title = $u.Title; kb = (@($u.KBArticleIDs) -join ';'); severity = [string]$u.MsrcSeverity
            categories = $categories; released = IsoTime $u.LastDeploymentChangeTime
            security = $(if ($categories -match 'Security' -or $u.MsrcSeverity) { 'Yes' } else { 'No' })
        }
    }
} catch { $searchNote = "failed: $($_.Exception.Message)" }
$nPending = SaveCsv 'updates-pending.csv' $pending @('title', 'kb', 'security', 'severity',
    'categories', 'released')
$history = @()
$total = $searcher.GetTotalHistoryCount()
if ($total -gt 0) {
    foreach ($h in $searcher.QueryHistory(0, [Math]::Min($total, 100))) {
        $history += [pscustomobject]@{
            date = IsoTime $h.Date; title = $h.Title
            result = @{ 1 = 'In progress'; 2 = 'Succeeded'; 3 = 'Succeeded with errors'; 4 = 'Failed'; 5 = 'Aborted' }[[int]$h.ResultCode]
        }
    }
}
$nHistory = SaveCsv 'updates-installed.csv' $history @('date', 'title', 'result')
$au = Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -ErrorAction SilentlyContinue
$service = Get-Service wuauserv
Save 'update-settings.txt' @(
    "Update search: $searchNote",
    "Windows Update service: $($service.Status), start type $($service.StartType)",
    "Policy NoAutoUpdate: $(if ($au -and $null -ne $au.NoAutoUpdate) { $au.NoAutoUpdate } else { 'not set (automatic updates on)' })",
    "Policy AUOptions: $(if ($au -and $null -ne $au.AUOptions) { $au.AUOptions } else { 'not set' })",
    "Hotfixes listed by Get-HotFix: $(@(Get-HotFix).Count)")
$Log.Add('> Get-ItemProperty HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU; Get-Service wuauserv; Get-HotFix')

# 7. Extraction log, then hashes of every file.
Save 'extraction-log.txt' (@(
    'Northwind Retail: PC evidence extraction',
    "Extracted at (UTC):  $($Now.ToString('yyyy-MM-ddTHH:mm:ss'))+00:00",
    "Performed by:        $Operator (as an administrator on the PC)",
    "Host:                $($env:COMPUTERNAME)",
    'Method:              read only commands; nothing on the PC was changed',
    '',
    'Record counts (completeness checks: each pair must match)',
    "  local accounts (Get-LocalUser): $(@(Get-LocalUser).Count)",
    "  rows in local-accounts.csv: $nUsers",
    "  members listed by net localgroup Administrators: $nNet",
    "  rows in local-administrators.csv: $nAdmins",
    "  rows in updates-pending.csv: $nPending",
    "  rows in updates-installed.csv: $nHistory",
    '',
    'Commands run') + ($Log | ForEach-Object { "  $_" }))

$sums = Get-ChildItem -Path $Folder -File | Sort-Object Name | ForEach-Object {
    "$((Get-FileHash -Algorithm SHA256 -Path $_.FullName).Hash.ToLower())  $($_.Name)"
}
[System.IO.File]::WriteAllText((Join-Path $Folder 'SHA256SUMS'), (($sums -join "`n") + "`n"), $Utf8)
Write-Output "Evidence written to $Folder"
