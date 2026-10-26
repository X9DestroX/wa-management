@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%TEMP%\python-3.12.10-amd64.exe'"
if errorlevel 1 (
  echo Failed to download Python 3.12.10.
  pause
  exit /b 1
)
"%TEMP%\python-3.12.10-amd64.exe" InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1
pause
