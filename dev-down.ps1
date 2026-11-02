# Apaga todo lo que levantó dev-up.ps1.  Uso: .\dev-down.ps1
$Root = $PSScriptRoot
$Services = Join-Path $env:USERPROFILE "kitchan-dev-services"

# Bot + túnel (script propio del bot)
& (Join-Path $Root "Whatsapp\kitchan-wa-local\scripts\stop-public.ps1")

# Backend (8000) y frontend (5173)
foreach ($port in 8000, 5173) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

# Redis y Postgres
Get-Process redis-server -ErrorAction SilentlyContinue | Stop-Process -Force
$pgctl = Join-Path $Services "pg-extract\pgsql\bin\pg_ctl.exe"
if (Test-Path "$Services\pgdata") { & $pgctl stop -D "$Services\pgdata" -m fast 2>$null | Out-Null }

Write-Host "Todo apagado." -ForegroundColor Green
