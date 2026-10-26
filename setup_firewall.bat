@echo off
chcp 65001 >nul
echo ================================================
echo   W-A Systeme de Gestion - Pare-feu LAN
 echo   A executer en tant qu'administrateur
 echo ================================================
echo.
netsh advfirewall firewall delete rule name="W-A Systeme de Gestion TCP 8765" >nul 2>&1
netsh advfirewall firewall delete rule name="W-A Systeme de Gestion UDP 8766" >nul 2>&1
netsh advfirewall firewall add rule name="W-A Systeme de Gestion TCP 8765" dir=in action=allow protocol=TCP localport=8765 profile=private
netsh advfirewall firewall add rule name="W-A Systeme de Gestion UDP 8766" dir=in action=allow protocol=UDP localport=8766 profile=private
if errorlevel 1 (
 echo.
 echo ERREUR : lancez ce fichier avec "Executer en tant qu'administrateur".
) else (
 echo.
 echo Pare-feu configure pour le reseau prive.
 echo La limitation aux PC autorises est geree par lan_access.json.
)
pause
