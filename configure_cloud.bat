@echo off
setlocal
title Configuration Cloud - W-A Systeme de Gestion
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0configure_cloud.ps1"
if errorlevel 1 (
  echo.
  echo Configuration non terminee. Verifiez les messages ci-dessus.
  pause
)
endlocal
