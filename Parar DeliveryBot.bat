@echo off
chcp 65001 >nul
title DeliveryBot - Parando tudo
cd /d "%~dp0"

echo Parando o DeliveryBot...
echo.

taskkill /FI "WINDOWTITLE eq DeliveryBot - ngrok*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DeliveryBot - Sistema*" /T /F >nul 2>&1

where docker >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Parando o Docker (WAHA)...
    docker compose down
) else (
    echo Docker nao encontrado -- pulando essa parte.
)

echo.
echo Tudo parado.
echo.
pause
