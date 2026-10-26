@echo off
setlocal
chcp 65001 >nul

echo ================================================
echo   W-A Systeme de Gestion - Configuration LAN
 echo   1 serveur + 1 ou 2 PC clients maximum
echo ================================================
echo.
echo Cette operation doit etre faite sur le PC SERVEUR.
echo Utilisez les adresses IP fixes des PC clients.
echo Exemple : 192.168.50.2 et 192.168.50.3
 echo.
set /p IP1=IP du PC client 1 : 
set /p IP2=IP du PC client 2 (laisser vide si 1 seul client) : 

if "%IP1%"=="" (
  echo Vous devez saisir au moins une IP client.
  pause
  exit /b 1
)

set "WA_DIR=%USERPROFILE%\WA_Manager_System"
if not exist "%WA_DIR%" mkdir "%WA_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ips=@('%IP1%'); if('%IP2%' -ne ''){$ips += '%IP2%'}; $o=[ordered]@{enabled=$true;max_clients=2;allowed_ips=$ips}; $o | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 '%WA_DIR%\lan_access.json'"

if errorlevel 1 (
  echo.
  echo ERREUR : impossible de creer la configuration.
  pause
  exit /b 1
)

echo.
echo Configuration creee :
echo %WA_DIR%\lan_access.json
echo.
echo Les seuls PC autorises sont :
echo   %IP1%
if not "%IP2%"=="" echo   %IP2%
echo.
echo Redemarrez W-A Systeme de Gestion sur le serveur apres cette configuration.
echo.
pause
