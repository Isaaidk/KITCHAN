@echo off
setlocal
rem ============================================================
rem  Inicia todo lo necesario para la demo de KITCHAN:
rem  Docker (Postgres + Redis), APIs falsas de Rappi y PedidosYa,
rem  backend, frontend, el tunel de ngrok (webhooks de Uber) y el menu de
rem  pedidos de la demo.
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

echo [1/6] Iniciando Docker (Postgres y Redis)...
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

rem Aplica las migraciones pendientes (alembic upgrade head). Sin esto, una base
rem desactualizada hace fallar el dashboard, la cola y el historial. Si Postgres
rem acaba de encenderse tarda unos segundos en aceptar conexiones: se reintenta.
echo     Aplicando migraciones de la base de datos...
set "INTENTOS=0"
:migrar
set /a INTENTOS+=1
pushd "%BACKEND%"
set PYTHONUTF8=1
"%PYTHON%" -m alembic upgrade head >"%TEMP%\kitchan_migracion.log" 2>&1
set "RESULTADO=%errorlevel%"
popd
if "%RESULTADO%"=="0" goto migraciones_listas
if %INTENTOS% GEQ 10 goto migracion_fallida
timeout /t 3 /nobreak >nul
goto migrar
:migracion_fallida
type "%TEMP%\kitchan_migracion.log"
echo.
echo No se pudieron aplicar las migraciones de la base de datos.
echo Revisa el mensaje de arriba y ejecuta a mano: alembic upgrade head
pause
exit /b 1
:migraciones_listas

echo [2/6] API falsa de Rappi (puerto 8010)...
start "KITCHAN - API Rappi falsa" /min cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& "%PYTHON%" -m uvicorn scripts.simulador_rappi.api_rappi_falsa:app --port 8010"

echo [3/6] API falsa de PedidosYa (puerto 8011)...
start "KITCHAN - API PedidosYa falsa" /min cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& "%PYTHON%" -m uvicorn scripts.simulador_pedidosya.api_pedidosya_falsa:app --port 8011"

echo [4/6] Backend de KITCHAN (puerto 8000)...
start "KITCHAN - Backend" /min cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& "%PYTHON%" -m uvicorn src.kitchan.main:app --host 127.0.0.1 --port 8000"

echo [5/6] Frontend (puerto 5173)...
start "KITCHAN - Frontend" /min cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo [6/6] Tunel publico de ngrok para los webhooks de Uber...
rem Dominio fijo de ngrok: es la URL que esta registrada como webhook en la
rem app KITCHAN de Uber Developers. Si cambia, hay que actualizarla alli.
set "NGROK_DOMINIO=able-gap-saddling.ngrok-free.dev"
where ngrok >nul 2>&1
if errorlevel 1 (
    echo     ngrok no esta instalado: Uber NO recibira pedidos en esta demo.
) else (
    start "KITCHAN - ngrok" /min cmd /k "ngrok http 8000 --url=https://%NGROK_DOMINIO%"
)

echo.
echo Esperando a que todo arranque...
timeout /t 12 /nobreak >nul
start "" http://localhost:5173/
start "KITCHAN - Menu de la demo" cmd /k "cd /d "%BACKEND%" && set PYTHONUTF8=1&& "%PYTHON%" scripts\demo\demo_pedidos.py"

echo.
echo Listo. Inicia sesion en KITCHAN en el navegador y usa la ventana
echo "KITCHAN - Menu de la demo" para enviar pedidos.
timeout /t 8 >nul
