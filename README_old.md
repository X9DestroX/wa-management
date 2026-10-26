# W-A Systeme de Gestion — Desktop Edition

The UI is redesigned to closely match the supplied reference: light background, white left sidebar, WA brand block, blue active navigation, compact top-right user badge, date selector, four metric cards, sales overview, daily position, and recent sales/deposits panels.

## Run
Install Python 3.11+ on Windows, then double-click `start_wa_manager.bat` or run `python wa_manager.py`.

## Build EXE
Double-click `build_exe.bat`. It creates `dist\\W-A Systeme de Gestion\\W-A Systeme de Gestion.exe`.

## LAN
The server computer uses `config-server.json`. Other PCs use a `config.json` under `%USERPROFILE%\\WA_Manager_System` with the server computer's LAN IP and `server_mode: false`.

## Default accounts
Manager: `admin / admin123`
HR: `hr / hr123`

Change these before production use.
