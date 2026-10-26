@echo off
setlocal
cd /d "%~dp0"
set "PY312="
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PY312=%%P"
if not defined PY312 if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY312=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY312 (
  echo Python 3.12 is required. Run install_python_312.bat first.
  pause
  exit /b 1
)
"%PY312%" -m pip install -r requirements-build.txt
"%PY312%" wa_manager.py
