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
    pathex=[],
    binaries=wx_binaries,
    datas=[
        (str(project_root / 'scripts'), 'scripts'),
        (str(project_root / 'shared'), 'shared'),
        (str(project_root / 'models'), 'models'),
        (str(project_root / 'imagedescriber' / 'ai_providers.py'), 'imagedescriber'),
        (str(project_root / 'imagedescriber' / 'data_models.py'), 'imagedescriber'),
        (str(project_root / 'imagedescriber' / 'dialogs_wx.py'), 'imagedescriber'),
        (str(project_root / 'imagedescriber' / 'workers_wx.py'), 'imagedescriber'),
    ] + wx_datas,
    hiddenimports=[
        'wx.adv',
        'wx.lib.newevent',
        'shared.wx_common',
        'imagedescriber.ai_providers',
        'imagedescriber.data_models',
        'imagedescriber.dialogs_wx',
        'imagedescriber.workers_wx',
        'scripts.metadata_extractor',
        'scripts.versioning',
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
    target_arch='arm64' if sys.platform == 'darwin' else None,
    codesign_identity=None,
    entitlements_file=None,
)

# macOS-specific bundle (only created on macOS)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='ImageDescriber.app',
        icon=None,
        bundle_identifier='com.imagedescriber.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
