# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_all

block_cipher = None

# 1. Base project assets & folders
datas = [
    ('head.glb', '.'),
    ('index.html', '.'),
    ('Nexus_logo.png', '.'),
    ('assets', 'assets'),
    ('config', 'config'),
    ('core/prompt.txt', 'core'),
    ('dashboard/static', 'dashboard/static'),
    ('memory', 'memory'),
    ('model', 'model'),
    ('actions', 'actions'),
    ('plugins', 'plugins'),
]

binaries = []
hidden_imports = [
    'ui',
    'nexus_splash',
    'nexus_main_integration',
    'core',
    'core.installer',
    'core.llm_client',
    'core.plugin_loader',
    'core.stt',
    'core.tts',
    'dashboard',
    'dashboard.server',
    'memory',
    'memory.config_manager',
    'memory.memory_manager',
]

hidden_imports += collect_submodules('actions')
hidden_imports += collect_submodules('plugins')

# 2. Master sweep of ALL C/C++ compiled packages (avoids missing DLLs forever)
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
    'playwright',
    'pygame',
]

for pkg in heavy_packages:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hidden_imports += pkg_hidden
    except Exception:
        pass

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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nexus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # STRICTLY OFF: prevents "%1 is not a valid Win32 application"
    console=True,
    icon='config/nexus.ico' if os.path.exists('config/nexus.ico') else None,
    contents_directory='.',
)

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