@echo off
chcp 65001 >nul
title DeliveryBot - Trocar senha da cozinha
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "iniciar.ps1" -SoTrocarSenha
echo.
pause
