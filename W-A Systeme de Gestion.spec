# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('ui.html', '.')]
binaries = [('C:/Users/Destrox/AppData/Local/Programs/Python/Python312/vcruntime140.dll', '_internal'), ('C:/Users/Destrox/AppData/Local/Programs/Python/Python312/vcruntime140_1.dll', '_internal'), ('C:/Windows/System32/msvcp140.dll', '_internal'), ('C:/Windows/System32/msvcp140_1.dll', '_internal'), ('C:/Windows/System32/concrt140.dll', '_internal')]
hiddenimports = ['webview.platforms.winforms', 'webview.platforms.edgechromium']
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['wa_manager.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='W-A Systeme de Gestion',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/DESTROX/Projects/wa-management/app.ico'],
    contents_directory='_internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='W-A Systeme de Gestion',
)
