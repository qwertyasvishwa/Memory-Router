param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [string]$Reload = "true"
)

$reloadFlag = [System.Convert]::ToBoolean($Reload)

# Start the development uvicorn server with optional --reload and write PID to server.pid.
# Usage: .\start_dev_server.ps1 -Host 127.0.0.1 -Port 8000 -Reload

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir\..  # project root

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Error "Python executable not found in PATH. Please ensure Python is installed and on PATH."
    exit 1
}

 $args = @('-m', 'uvicorn', 'app.main:app', '--host', $BindHost, '--port', $Port.ToString())
if ($reloadFlag) { $args += '--reload' }

# Prepare log files
$stdout = Join-Path $scriptDir "..\server-out.log"
$stderr = Join-Path $scriptDir "..\server-err.log"
$pidFile = Join-Path $scriptDir "..\server.pid"

# Start process detached
$startInfo = @{
    FilePath = $python
    ArgumentList = $args
    WorkingDirectory = (Get-Location).Path
    RedirectStandardOutput = $stdout
    RedirectStandardError = $stderr
    NoNewWindow = $false
    PassThru = $true
}

$proc = Start-Process @startInfo

# Save PID (parent/reloader PID) to server.pid
$procId = $proc.Id
"$procId" | Out-File -FilePath $pidFile -Encoding ascii -Force

Write-Host "Started uvicorn (reloader parent) PID=$procId; logs: server-out.log, server-err.log"
Write-Host "To stop: .\scripts\stop_dev_server.ps1"
