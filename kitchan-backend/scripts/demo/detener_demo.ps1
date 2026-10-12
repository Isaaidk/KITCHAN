# Detiene la demo de KITCHAN que inicio iniciar_demo.cmd.
#
# Cierra solo los procesos de la demo, identificados por su comando (no por
# el titulo de la ventana): asi no se cierran el navegador (cuya pestana
# tambien se llama "KITCHAN") ni Windows Terminal con otras pestanas abiertas.
# Despues detiene Postgres y Redis sin borrar datos.

$patron = '(?i)kitchan.*(api_rappi_falsa|api_pedidosya_falsa|src\.kitchan\.main:app|demo_pedidos\.py|npm run dev)'

Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" |
    Where-Object { $_.CommandLine -match $patron } |
    ForEach-Object { taskkill /PID $_.ProcessId /T /F | Out-Null }

# Por si algun servidor quedo vivo fuera de su ventana: se libera por puerto,
# solo si es un proceso de Python o Node (los de la demo).
foreach ($puerto in 8000, 8010, 8011, 5173) {
    Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            $proceso = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
            if ($proceso -and $proceso.ProcessName -match '^(python|node)$') {
                Stop-Process -Id $proceso.Id -Force
            }
        }
}

docker stop kitchan_postgres kitchan_redis 2>$null | Out-Null
Write-Host "Demo detenida."
