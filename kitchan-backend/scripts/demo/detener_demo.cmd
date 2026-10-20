@echo off
rem Detiene la demo de KITCHAN (ver detener_demo.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0detener_demo.ps1"
timeout /t 3 >nul
