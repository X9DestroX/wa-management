@echo off
setlocal
set "CFG=%USERPROFILE%\WA_Manager_System\config.json"
if exist "%CFG%" del /q "%CFG%"
echo W-A Systeme de Gestion network configuration reset.
echo The next launch will automatically search the local LAN for a server.
pause
