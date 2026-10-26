# Levanta Uvicorn + túnel HTTPS en una sola acción (Windows).
# Uso: .\scripts\start-public.ps1
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Cloudflared = Join-Path $ProjectRoot "cloudflared.exe"
$DataDir = Join-Path $ProjectRoot "data"
$TunnelLog = Join-Path $DataDir "tunnel.log"
$UrlFile = Join-Path $DataDir "public-url.txt"
$PidFile = Join-Path $DataDir "dev.pids.json"
# Puerto del bot (8001): el backend de KITCHAN usa el 8000. Se lee de PORT en .env.
$Port = 8001
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    $m = Select-String -Path $envFile -Pattern "^\s*PORT\s*=\s*(\d+)" | Select-Object -First 1
    if ($m) { $Port = [int]$m.Matches[0].Groups[1].Value }
}

if (-not (Test-Path $Python)) {
    Write-Host "No existe .venv. Crea el entorno e instala requirements (ver README)." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Cloudflared)) {
    Write-Host "Descargando cloudflared..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $Cloudflared
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

function Test-ServerUp {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 3
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

$uvicornPid = $null
if (-not (Test-ServerUp)) {
    Write-Host "Iniciando servidor en http://127.0.0.1:$Port ..." -ForegroundColor Cyan
    $uvicorn = Start-Process -FilePath $Python `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
        -WorkingDirectory $ProjectRoot `
        -PassThru `
        -WindowStyle Hidden
    $uvicornPid = $uvicorn.Id

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-ServerUp)) {
        Start-Sleep -Milliseconds 400
    }
    if (-not (Test-ServerUp)) {
        Write-Host "El servidor no respondió en /health." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Servidor ya activo en puerto $Port." -ForegroundColor Green
}

Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*127.0.0.1:$Port*" -or $_.CommandLine -like "*localhost:$Port*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (Test-Path $TunnelLog) { Remove-Item $TunnelLog -Force }

Write-Host "Iniciando túnel HTTPS (http2)..." -ForegroundColor Cyan
$tunnel = Start-Process -FilePath $Cloudflared `
    -ArgumentList @("tunnel", "--protocol", "http2", "--url", "http://127.0.0.1:$Port") `
    -RedirectStandardError $TunnelLog `
    -PassThru `
    -WindowStyle Hidden

$publicUrl = $null
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $deadline -and -not $publicUrl) {
    if (Test-Path $TunnelLog) {
        $line = Select-String -Path $TunnelLog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches |
            Select-Object -First 1
        if ($line -and $line.Matches.Count -gt 0) {
            $publicUrl = $line.Matches[0].Value
        }
    }
    Start-Sleep -Milliseconds 500
}

if (-not $publicUrl) {
    Write-Host "No se pudo obtener la URL pública. Revisa $TunnelLog" -ForegroundColor Red
    if ($uvicornPid) { Stop-Process -Id $uvicornPid -Force -ErrorAction SilentlyContinue }
    Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

$webhookUrl = "$publicUrl/webhook"
@{
    base_url    = $publicUrl
    webhook_url = $webhookUrl
    started_at  = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -Path $UrlFile -Encoding UTF8

@{
    uvicorn_pid = $uvicornPid
    tunnel_pid  = $tunnel.Id
} | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

Write-Host ""
Write-Host "=== KITCHAN listo ===" -ForegroundColor Green
Write-Host "Local:    http://127.0.0.1:$Port"
Write-Host "Público:  $publicUrl"
Write-Host "Webhook:  $webhookUrl  (pega esto en Meta)"
Write-Host ""
Write-Host "Verify token (.env): WHATSAPP_VERIFY_TOKEN"
Write-Host "Para apagar: .\scripts\stop-public.ps1"
Write-Host "Guardado en: $UrlFile"

