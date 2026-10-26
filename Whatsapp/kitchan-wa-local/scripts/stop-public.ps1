# Detiene servidor y túnel iniciados con start-public.ps1
$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "data\dev.pids.json"

if (Test-Path $PidFile) {
    $pids = Get-Content $PidFile -Raw | ConvertFrom-Json
    foreach ($name in @("uvicorn_pid", "tunnel_pid")) {
        $id = $pids.$name
        if ($id) { Stop-Process -Id $id -Force }
    }
    Remove-Item $PidFile -Force
}

Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { if ($_ -and $_ -ne 0) { Stop-Process -Id $_ -Force } }

Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
    Where-Object { $_.CommandLine -like "*$ProjectRoot*" -or $_.CommandLine -match "(:8001|:8000)" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host "Servidor y túnel detenidos." -ForegroundColor Green

