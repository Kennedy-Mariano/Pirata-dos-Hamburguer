@echo off
chcp 65001 >nul
title DeliveryBot - Configurar IA
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "iniciar.ps1" -ConfigurarIA
echo.
pause
