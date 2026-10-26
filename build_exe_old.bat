@echo off
setlocal
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --windowed --name "W-A Systeme de Gestion" --icon "app.ico" --add-data "ui.html;." wa_manager.py
echo.
echo Build complete: dist\W-A Systeme de Gestion\W-A Systeme de Gestion.exe
pause
