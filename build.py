import os, sys, shutil, subprocess, glob, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / '.venv312' / 'Scripts' / 'python.exe'
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'

print('=' * 55)
print('W-A Systeme de Gestion - robust Windows EXE builder')
print('=' * 55)
print('Build Python:', sys.executable)
print('Python version:', sys.version)

if sys.version_info[:2] != (3, 12):
    raise SystemExit('ERROR: This build script must run with Python 3.12 x64.')

# Verify the environment is 64-bit.
if sys.maxsize <= 2**32:
    raise SystemExit('ERROR: A 64-bit Python 3.12 installation is required.')

# Install build dependencies in the isolated venv.
subprocess.check_call([str(VENV_PY), '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])
subprocess.check_call([str(VENV_PY), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements-build.txt')])

# If the previously built EXE is still running, Windows keeps DLLs inside
# dist\W-A Systeme de Gestion\_internal locked. Build into another folder instead.
def process_is_running(image_name):
    if os.name != 'nt':
        return False
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'IMAGENAME eq {image_name}'],
            capture_output=True, text=True, timeout=10
        )
        return image_name.lower() in (result.stdout or '').lower()
    except Exception:
        return False

stamp = time.strftime('%Y%m%d_%H%M%S')
app_running = process_is_running('W-A Systeme de Gestion.exe')

# Choose paths without deleting an output folder that Windows may have locked.
def prepare_path(path, label, skip_clean=False):
    if skip_clean and path.exists():
        alternate = ROOT / f'{label}_{stamp}'
        print(f'\nWARNING: Existing {path.name} is being used by Windows.')
        print(f'The old folder will be preserved; the new build will go to: {alternate}')
        return alternate
    if path.exists():
        try:
            shutil.rmtree(path)
        except OSError as exc:
            alternate = ROOT / f'{label}_{stamp}'
            print(f'\nWARNING: Could not remove {path}: {exc}')
            print('This can happen when the app is open or a DLL is locked by Windows.')
            print(f'The new build will use a separate folder: {alternate}')
            return alternate
    return path

BUILD_OUTPUT = prepare_path(BUILD, 'build_retry')
DIST_OUTPUT = prepare_path(DIST, 'dist_retry', skip_clean=app_running)

# Locate Microsoft runtime DLLs that can be shipped with the application.
# Python's python312.dll can fail to load when these are absent from a clean PC.
dll_names = [
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'msvcp140.dll',
    'msvcp140_1.dll',
    'concrt140.dll',
]
search_dirs = [
    Path(sys.base_prefix),
    Path(sys.base_prefix) / 'DLLs',
    Path(os.environ.get('WINDIR', r'C:\Windows')) / 'System32',
]

binaries = []
for name in dll_names:
    found = None
    for d in search_dirs:
        candidate = d / name
        if candidate.exists():
            found = candidate
            break
    if found:
        print(f'Bundling runtime: {found}')
        binaries.append((str(found), '_internal'))
    else:
        print(f'Runtime not found (will rely on Windows): {name}')

# Let PyInstaller collect webview, but explicitly bundle the Python runtime dependencies above.
cmd = [
    str(VENV_PY), '-m', 'PyInstaller',
    '--noconfirm', '--clean', '--windowed', '--onedir',
    '--distpath', str(DIST_OUTPUT),
    '--workpath', str(BUILD_OUTPUT),
    '--name', 'W-A Systeme de Gestion',
    '--icon', str(ROOT / 'app.ico'),
    '--contents-directory', '_internal',
    '--add-data', 'ui.html;.',
    '--collect-all', 'webview',
    '--collect-all', 'reportlab',
    '--hidden-import', 'webview.platforms.winforms',
    '--hidden-import', 'webview.platforms.edgechromium',
]
for src, dest in binaries:
    cmd += ['--add-binary', f'{src};{dest}']
cmd.append('wa_manager.py')

print('\nRunning PyInstaller...')
print(' '.join(f'"{x}"' if ' ' in x else x for x in cmd))
subprocess.check_call(cmd, cwd=ROOT)

exe = DIST_OUTPUT / 'W-A Systeme de Gestion' / 'W-A Systeme de Gestion.exe'
internal = DIST_OUTPUT / 'W-A Systeme de Gestion' / '_internal'
if not exe.exists():
    raise SystemExit('BUILD FAILED: executable was not created.')

# Copy first-run Cloud setup guides/scripts beside the packaged application.
for setup_name in ('configure_cloud.bat', 'configure_cloud.ps1', 'CLOUD_SETUP_FR.md'):
    source = ROOT / setup_name
    if source.exists():
        shutil.copy2(source, DIST_OUTPUT / 'W-A Systeme de Gestion' / setup_name)

# Make a tiny launcher beside the EXE for users who prefer double-clicking a batch file.
launcher = DIST_OUTPUT / 'START W-A SYSTEME DE GESTION.bat'
launcher.write_text(
    '@echo off\n'
    'cd /d "%~dp0W-A Systeme de Gestion"\n'
    'start "W-A Systeme de Gestion" "W-A Systeme de Gestion.exe"\n',
    encoding='utf-8'
)

print('\n' + '=' * 55)
print('BUILD SUCCESSFUL')
print('=' * 55)
print('EXE:', exe)
print('Keep the complete "W-A Systeme de Gestion" folder together.')
print('Output folder:', DIST_OUTPUT)
print('Optional launcher:', launcher)
