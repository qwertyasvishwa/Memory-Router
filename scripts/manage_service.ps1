<#
manage_service.ps1 - simple wrapper to control the dev server
Usage:
  .\manage_service.ps1 start
  .\manage_service.ps1 stop
  .\manage_service.ps1 restart
  .\manage_service.ps1 status

This script delegates to start_dev_server.ps1 and stop_dev_server.ps1 and reports status using server.pid.
#>
param(
    [Parameter(Mandatory=$true)][ValidateSet('start','stop','restart','status','install-nssm','uninstall-nssm')] [string]$Action,
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8000,
    [switch]$Reload = $true,
    [string]$NssmPath = ''
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir\..  # project root
$pidFile = Join-Path (Get-Location) 'server.pid'

function Get-ServerPids() {
    if (-not (Test-Path $pidFile)) { return @() }
    $raw = Get-Content $pidFile | Where-Object { $_ -match '\d+' }
    $pids = $raw -replace '[^0-9]', '' | Where-Object { $_ -ne '' } | ForEach-Object { [int]$_ }
    return $pids
}

switch ($Action) {
    'start' {
        if (Get-ServerPids) {
            Write-Host "Server already has PID(s): $(Get-ServerPids -join ',') - stop it first or use restart."
            break
        }
        $startScript = Join-Path $scriptDir 'start_dev_server.ps1'
        if (-not (Test-Path $startScript)) { Write-Error "Start script not found: $startScript"; break }
        $args = @()
        $args += '-BindHost'; $args += $BindHost
        $args += '-Port'; $args += $Port
        if ($Reload) { $args += '-Reload' }
        Start-Process -FilePath powershell -ArgumentList ('-NoProfile','-ExecutionPolicy','Bypass','-File', $startScript) -WorkingDirectory (Get-Location).Path -PassThru | Out-Null
        Start-Sleep -Seconds 2
        if (Get-ServerPids) { Write-Host "Started server with PID(s): $(Get-ServerPids -join ',')" } else { Write-Error "Failed to start server - check server-out.log and server-err.log" }
    }
    'stop' {
        $stopScript = Join-Path $scriptDir 'stop_dev_server.ps1'
        if (-not (Test-Path $stopScript)) { Write-Error "Stop script not found: $stopScript"; break }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
    }
    'restart' {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir 'stop_dev_server.ps1')
        Start-Sleep -Seconds 1
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir 'start_dev_server.ps1') -BindHost $BindHost -Port $Port -Reload:$Reload
        Start-Sleep -Seconds 2
        if (Get-ServerPids) { Write-Host "Restarted server with PID(s): $(Get-ServerPids -join ',')" } else { Write-Error "Failed to restart server" }
    }
    'status' {
        $pids = Get-ServerPids
        if ($pids) {
            foreach ($pid in $pids) {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($proc) { Write-Host "PID $pid - Running - StartTime: $($proc.StartTime)" } else { Write-Host "PID $pid - Not running" }
            }
        } else {
            Write-Host "No server PID file found or server not running (no server.pid)"
        }
    }
    'install-nssm' {
        if (-not $NssmPath) { Write-Error 'Please provide path to nssm.exe via -NssmPath'; break }
        if (-not (Test-Path $NssmPath)) { Write-Error "nssm.exe not found at $NssmPath"; break }
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $python) { Write-Error 'Python not found in PATH'; break }
        $serviceName = 'MemoryRouter'
        $wd = (Get-Location).Path
        & $NssmPath install $serviceName $python "-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info"
        & $NssmPath set $serviceName AppDirectory $wd
        & $NssmPath set $serviceName AppStdout "$wd\server-out.log"
        & $NssmPath set $serviceName AppStderr "$wd\server-err.log"
        Write-Host "NSSM service $serviceName installed. Start it with: Start-Service $serviceName"
    }
    'uninstall-nssm' {
        if (-not $NssmPath) { Write-Error 'Please provide path to nssm.exe via -NssmPath'; break }
        $serviceName = 'MemoryRouter'
        & $NssmPath remove $serviceName confirm
        Write-Host "NSSM service $serviceName removed"
    }
}
