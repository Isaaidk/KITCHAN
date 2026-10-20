@echo off
setlocal
rem ============================================================
rem  Inicia todo lo necesario para la demo de KITCHAN:
rem  Docker (Postgres + Redis), APIs falsas de Rappi y PedidosYa,
rem  backend, frontend y el menu de pedidos de la demo.
rem  Cada servicio abre su propia ventana; para cerrar todo usa
rem  detener_demo.cmd.
rem ============================================================

set "BACKEND=%~dp0..\.."
for %%I in ("%BACKEND%") do set "BACKEND=%%~fI"
set "FRONTEND=%BACKEND%\..\frontend"
for %%I in ("%FRONTEND%") do set "FRONTEND=%%~fI"

set "PYTHON=%BACKEND%\venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%BACKEND%\..\..\KITCHAN\kitchan-backend\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo No se encontro el venv del backend. Crea kitchan-backend\venv antes de la demo.
    pause
    exit /b 1
)
if not exist "%BACKEND%\.env" (
    echo Falta kitchan-backend\.env con la configuracion de la demo.
    pause
    exit /b 1
)

echo [1/5] Iniciando Docker (Postgres y Redis)...
docker info >nul 2>&1
if not errorlevel 1 goto docker_listo
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo     Esperando a que Docker termine de arrancar...
:esperar_docker
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto esperar_docker
:docker_listo
docker start kitchan_postgres kitchan_redis >nul
timeout /t 3 /nobreak >nul

echo [2/5] API falsa de Rappi (puerto 8010)...
start "KITCHAN - API Rappi falsa" /min cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& "%PYTHON%" -m uvicorn scripts.simulador_rappi.api_rappi_falsa:app --port 8010"

echo [3/5] API falsa de PedidosYa (puerto 8011)...
start "KITCHAN - API PedidosYa falsa" /min cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& "%PYTHON%" -m uvicorn scripts.simulador_pedidosya.api_pedidosya_falsa:app --port 8011"

echo [4/5] Backend de KITCHAN (puerto 8000)...
start "KITCHAN - Backend" /min cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& "%PYTHON%" -m uvicorn src.kitchan.main:app --host 127.0.0.1 --port 8000"

echo [5/5] Frontend (puerto 5173)...
start "KITCHAN - Frontend" /min cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo.
echo Esperando a que todo arranque...
timeout /t 12 /nobreak >nul
start "" http://localhost:5173/
start "KITCHAN - Menu de la demo" cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& "%PYTHON%" scripts\demo\demo_pedidos.py"

echo.
echo Listo. Inicia sesion en KITCHAN en el navegador y usa la ventana
echo "KITCHAN - Menu de la demo" para enviar pedidos.
timeout /t 8 >nul
