# Levanta TODO KITCHAN en local (sin admin): Postgres, Redis, migraciones,
# backend, frontend, bot de WhatsApp y túnel público para Meta.
# Uso:  .\dev-up.ps1        (apagar: .\dev-down.ps1)
# Es idempotente: lo que ya esté corriendo se deja como está.
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Services = Join-Path $env:USERPROFILE "kitchan-dev-services"   # Postgres/Redis portables
$Logs = Join-Path $Services "logs"
$Pg = Join-Path $Services "pg-extract\pgsql\bin"
$Redis = Join-Path $Services "redis"
$Backend = Join-Path $Root "kitchan-backend"
$Frontend = Join-Path $Root "frontend"
$Bot = Join-Path $Root "Whatsapp\kitchan-wa-local"
$BackendPy = Join-Path $Backend ".venv\Scripts\python.exe"
New-Item -ItemType Directory -Force $Logs | Out-Null

function Test-Port([int]$Port) {
    [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}
function Wait-Port([int]$Port, [string]$Name, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $Port) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name no levantó en el puerto $Port. Revisa los logs en $Logs"
}
function Step($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }

# --- Requisitos ---
if (-not (Test-Path "$Pg\pg_ctl.exe") -or -not (Test-Path "$Redis\redis-server.exe")) {
    throw "Faltan Postgres/Redis portables en $Services (pg-extract\pgsql y redis). Descárgalos de nuevo (ver README)."
}
if (-not (Test-Path $BackendPy)) {
    throw "No existe kitchan-backend\.venv. Crea el entorno: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
}
if (-not (Test-Path (Join-Path $Backend ".env"))) { throw "Falta kitchan-backend\.env (copia .env.example)." }

# --- Postgres ---
Step "Postgres (5432)"
if (-not (Test-Path "$Services\pgdata")) {
    Set-Content "$Services\pwfile" "kitchan_password" -NoNewline
    & "$Pg\initdb.exe" -D "$Services\pgdata" -U kitchan_user --pwfile="$Services\pwfile" -A scram-sha-256 -E UTF8 | Out-Null
}
if (-not (Test-Port 5432)) {
    Start-Process "$Pg\pg_ctl.exe" -ArgumentList "start", "-D", "$Services\pgdata", "-l", "$Logs\postgres.log" -WindowStyle Hidden
    Wait-Port 5432 "Postgres"
}
$env:PGPASSWORD = "kitchan_password"
$existe = & "$Pg\psql.exe" -U kitchan_user -h 127.0.0.1 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='kitchan_db'"
if ($existe -ne "1") { & "$Pg\createdb.exe" -U kitchan_user -h 127.0.0.1 kitchan_db }

# --- Redis ---
Step "Redis (6379)"
if (-not (Test-Port 6379)) {
    Start-Process "$Redis\redis-server.exe" -ArgumentList "--port", "6379" -WorkingDirectory $Redis -WindowStyle Hidden
    Wait-Port 6379 "Redis"
}

# --- Backend ---
Step "Backend KITCHAN (8000)"
Push-Location $Backend
$ErrorActionPreference = "Continue"   # alembic escribe su log por stderr
& $BackendPy -m alembic upgrade head *> "$Logs\alembic.log"
$alembicOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
Pop-Location
if (-not $alembicOk) { throw "Falló alembic upgrade head. Revisa $Logs\alembic.log" }
if (-not (Test-Port 8000)) {
    Start-Process $BackendPy -ArgumentList "-m", "uvicorn", "src.kitchan.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $Backend -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\backend.out.log" -RedirectStandardError "$Logs\backend.err.log"
    Wait-Port 8000 "Backend"
}

# --- Frontend ---
Step "Frontend (5173)"
if (-not (Test-Path "$Frontend\node_modules")) {
    Push-Location $Frontend; npm install --no-audit --no-fund | Out-Null; Pop-Location
}
if (-not (Test-Port 5173)) {
    Start-Process cmd -ArgumentList "/c", "npm run dev" -WorkingDirectory $Frontend -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\frontend.out.log" -RedirectStandardError "$Logs\frontend.err.log"
    Wait-Port 5173 "Frontend"
}

# --- Bot de WhatsApp + túnel (servicio independiente) ---
Step "Bot de WhatsApp (8001) + túnel público"
& (Join-Path $Bot "scripts\start-public.ps1")
$webhook = (Get-Content (Join-Path $Bot "data\public-url.txt") -Raw | ConvertFrom-Json).webhook_url

Write-Host "`n================ KITCHAN LISTO ================" -ForegroundColor Green
Write-Host "Frontend:        http://localhost:5173"
Write-Host "Backend (docs):  http://127.0.0.1:8000/docs"
Write-Host "Bot (panel):     http://127.0.0.1:8001"
Write-Host "Webhook en Meta: $webhook" -ForegroundColor Yellow
Write-Host "Verify token:    WHATSAPP_VERIFY_TOKEN (Whatsapp\kitchan-wa-local\.env)"
Write-Host "Logs:            $Logs"
