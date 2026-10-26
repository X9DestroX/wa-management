@echo off
setlocal
cd /d "%~dp0"
echo W-A Systeme de Gestion runtime diagnostic
echo.
if exist "dist\W-A Systeme de Gestion\_internal\python312.dll" (
  echo [OK] python312.dll exists in _internal
) else (
  echo [FAIL] python312.dll is missing
)
for %%D in (vcruntime140.dll vcruntime140_1.dll msvcp140.dll msvcp140_1.dll) do (
  if exist "dist\W-A Systeme de Gestion\_internal\%%D" (echo [OK] %%D bundled) else (echo [WARN] %%D not bundled)
)
echo.
echo If Windows reports a missing DLL, install the Microsoft Visual C++ 2015-2022 x64 Redistributable.
pause
