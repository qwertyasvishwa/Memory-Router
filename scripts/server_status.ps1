param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

Write-Host "Checking port $Port..." -ForegroundColor Cyan

try {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    if (-not $conns) {
        Write-Host "NO_LISTENER on port $Port" -ForegroundColor Yellow
        exit 2
    }

    $conns | Select-Object LocalAddress, LocalPort, OwningProcess, State | Format-Table -AutoSize

    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            Write-Host "PID $pid: $($proc.ProcessName)" -ForegroundColor Green
        } catch {
            Write-Host "PID $pid: (process not found)" -ForegroundColor DarkYellow
        }
    }
} catch {
    Write-Host "Get-NetTCPConnection failed. Falling back to netstat." -ForegroundColor DarkYellow
    netstat -ano | findstr (":" + $Port)
}
