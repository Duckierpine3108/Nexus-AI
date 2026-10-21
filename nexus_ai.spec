# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_all

# Raise recursion limit to prevent crashes during Google GenAI & Pydantic v2 AST analysis
sys.setrecursionlimit(50000)

block_cipher = None

# ── Helper: Clean Harvester (Strips __pycache__ and stale .pyc files) ─────────
def get_clean_datas(folder_name):
    clean_entries = []
    if not os.path.exists(folder_name):
        return clean_entries
    for root, dirs, files in os.walk(folder_name):
        # Exclude pycache and version control directories
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.svn', '.vscode')]
        for f in files:
            # Exclude compiled bytecode and temporary lockfiles
            if f.endswith(('.pyc', '.pyo', '.lock')):
                continue
            src_path = os.path.join(root, f)
            rel_path = os.path.relpath(root, folder_name)
            dst_folder = folder_name if rel_path == '.' else os.path.join(folder_name, rel_path)
            clean_entries.append((src_path, dst_folder))
    return clean_entries

# ── 1. Static Assets & Core Runtime Trees ─────────────────────────────────────
datas = [
    ('head.glb', '.'),
    ('index.html', '.'),
    ('Nexus_logo.png', '.'),
    ('core/prompt.txt', 'core'),
]

# Cleanly collect folders while eliminating stale Python 3.11 / 3.13 pycache artifacts
datas += get_clean_datas('actions')
datas += get_clean_datas('assets')
datas += get_clean_datas('config')
datas += get_clean_datas('dashboard')
datas += get_clean_datas('memory')
datas += get_clean_datas('model')
datas += get_clean_datas('plugins')

binaries = []

# ── 2. Explicit Hidden Imports ───────────────────────────────────────────────
hidden_imports = [
    'ui',
    'nexus_splash',
    'nexus_main_integration',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtNetwork',
    'PyQt6.QtSvg',
    'PyQt6.QtWebChannel',
    'PyQt6.QtQuick',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtQml',
    'win32api',
    'win32con',
    'win32gui',
    'win32process',
    'win32clipboard',
    'win32event',
    'win32file',
    'win32ts',
]

# Automatically sweep all internal package submodules
for mod in ['core', 'dashboard', 'memory', 'actions', 'plugins', 'config']:
    hidden_imports.append(mod)
    try:
        hidden_imports += collect_submodules(mod)
    except Exception:
        pass

# ── 3. Master Sweep for Compiled C/C++/Rust Packages ─────────────────────────
heavy_packages = [
    'vosk',
    'pydantic',
    'pydantic_core',
    'google.genai',
    'psutil',
    'cv2',
    'numpy',
    'PIL',
    'matplotlib',
    'sounddevice',
    'cryptography',
    'websockets',
    'uvicorn',
    'fastapi',
    'starlette',
    'qrcode',
    'pyautogui',
    'playwright',
    'pygame',
    'primp',
    'lxml',
    'pptx',
    'watchfiles',
]

for pkg in heavy_packages:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hidden_imports += pkg_hidden
    except Exception:
        pass

# ── 4. Analysis ──────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['__pycache__'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── 5. Executable Target ─────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nexus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # STRICTLY OFF: Prevents DLL and node.exe corruption
    console=True,                   # Required for live server output and terminal status
    icon='config/nexus.ico' if os.path.exists('config/nexus.ico') else None,
    contents_directory='.',         # Keeps files at root of output folder for Inno Setup
)

# ── 6. Directory Collection (For Inno Setup) ─────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='nexus',
)