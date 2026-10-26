@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================
echo W-A Systeme de Gestion - Windows EXE Builder
echo ================================================
echo.

set "PY312="
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PY312=%%P"
if not defined PY312 if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY312=%LocalAppData%\Programs\Python\Python312\python.exe"

if not defined PY312 (
    echo Python 3.12 x64 was not found.
    echo.
    echo Please install Python 3.12.10 x64 from python.org and run this file again.
    echo The builder deliberately does not silently install software.
    pause
    exit /b 1
)

echo Using Python:
echo %PY312%
"%PY312%" --version
if errorlevel 1 goto :fail

if exist .venv312 rmdir /s /q .venv312
"%PY312%" -m venv .venv312
if errorlevel 1 goto :fail

set "VENV=.venv312\Scripts\python.exe"
"%VENV%" build.py
if errorlevel 1 goto :fail

echo.
echo ================================================
echo BUILD SUCCESSFUL
echo ================================================
echo.
echo Open:
echo   dist\W-A Systeme de Gestion\W-A Systeme de Gestion.exe
echo.
echo Keep the complete W-A Systeme de Gestion folder together.
pause
exit /b 0

:fail
echo.
echo ================================================
echo BUILD FAILED
echo ================================================
echo Review the error above.
pause
exit /b 1
