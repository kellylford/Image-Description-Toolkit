# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Get the project root (parent of imagedescriber/)
project_root = Path(SPECPATH).parent

# Collect all wxPython files
wx_datas, wx_binaries, wx_hiddenimports = collect_all('wx')

a = Analysis(
    [str(project_root / 'imagedescriber' / 'imagedescriber_wx.py')],
    pathex=[
        str(project_root),
        str(project_root / 'imagedescriber'),
        str(project_root / 'scripts'),
        str(project_root / 'shared'),
        str(project_root / 'models'),
    ],
    binaries=wx_binaries,
    datas=[
        (str(project_root / 'scripts' / '*.json'), 'scripts'),
        (str(project_root / 'VERSION'), '.'),
    ] + wx_datas,
    hiddenimports=[
        'wx.adv',
        'wx.lib.newevent',
        'shared.wx_common',
        'shared',
        'ai_providers',
        'data_models',
        'dialogs_wx',
        'workers_wx',
        'scripts.metadata_extractor',
        'scripts.versioning',
        'scripts.config_loader',
        'models.provider_configs',
        'models.model_options',
        'ollama',
        'openai',
        'anthropic',
        'cv2',
        'PIL',
        'pillow_heif',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ImageDescriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
