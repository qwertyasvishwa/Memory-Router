param(
    [string]$PidFile = "server.pid"
)

# Stop the development uvicorn server started by start_dev_server.ps1
# This will attempt to kill the parent PID and any child processes recursively.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir\..

$pidPath = Join-Path (Get-Location) $PidFile
if (-not (Test-Path $pidPath)) {
    Write-Host "PID file not found: $pidPath"
    exit 1
}

$raw = Get-Content $pidPath | Where-Object { $_ -match '\d+' }
$pids = $raw -replace '[^0-9]', '' | Where-Object { $_ -ne '' } | ForEach-Object { [int]$_ }

function Get-ChildPids($parentPid) {
    $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $parentPid } | Select-Object -ExpandProperty ProcessId
    $all = @()
    foreach ($c in $children) {
        $all += $c
        $all += Get-ChildPids -parentPid $c
    }
    return $all
}

$toKill = @()
foreach ($rootPid in $pids) {
    if (Get-Process -Id $rootPid -ErrorAction SilentlyContinue) {
        $toKill += $rootPid
        $toKill += Get-ChildPids -parentPid $rootPid
    }
}

$toKill = $toKill | Where-Object { $_ -and ($_ -is [int]) } | Select-Object -Unique
if (-not $toKill) {
    Write-Host "No running processes found for PIDs in $pidPath"
    Remove-Item $pidPath -ErrorAction SilentlyContinue
    exit 0
}

foreach ($k in $toKill) {
    try {
        Stop-Process -Id $k -Force -ErrorAction Stop
        Write-Host "Stopped PID $k"
    } catch {
        $msg = $_.Exception.Message
        Write-Host ("Failed to stop PID {0}: {1}" -f $k, $msg)
    }
}

# Clean up pid file
Remove-Item $pidPath -ErrorAction SilentlyContinue
Write-Host "Stopped server and cleaned up PID file."
