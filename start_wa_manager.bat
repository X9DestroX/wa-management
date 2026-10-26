@echo off
setlocal
cd /d "%~dp0"
if exist "dist\W-A Systeme de Gestion\W-A Systeme de Gestion.exe" (
  start "W-A Systeme de Gestion" "dist\W-A Systeme de Gestion\W-A Systeme de Gestion.exe"
  exit /b 0
)
call run_source.bat
