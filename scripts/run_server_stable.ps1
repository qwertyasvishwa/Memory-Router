param(
    [string]$HostAddress = '127.0.0.1',
    [int]$Port = 8000,
    [string]$LogFile = 'server.log'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot '.venv\bin\python'
if (-not (Test-Path $venvPython)) {
    throw "Expected venv python at '$venvPython' but it was not found. Check your .venv layout."
}

Write-Host "Starting server on http://${HostAddress}:${Port} (no reload)" -ForegroundColor Cyan
Write-Host "Logging to: $LogFile" -ForegroundColor Cyan

# Run uvicorn and tee output to a log file for post-mortem debugging.
# NOTE: In Windows PowerShell 5.1, you can't invoke a "document" (non-.exe) in the middle
# of a pipeline. This venv appears to be WSL-created and contains a POSIX python shim
# at .venv\bin\python. We invoke it via the system Python as a fallback.

$invoked = $false

if ($venvPython.ToLower().EndsWith('.exe')) {
    $cmd = "& `"$venvPython`" -m uvicorn app.main:app --host $HostAddress --port $Port --log-level info"
    Invoke-Expression $cmd 2>&1 | Tee-Object -FilePath $LogFile
    $invoked = $true
}

if (-not $invoked) {
    Write-Host "Detected non-Windows venv python shim at '$venvPython'. Falling back to system python." -ForegroundColor DarkYellow
    $cmd = "python -m uvicorn app.main:app --host $HostAddress --port $Port --log-level info"
    Invoke-Expression $cmd 2>&1 | Tee-Object -FilePath $LogFile
}
