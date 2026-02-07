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
        'imagedescriber.ai_providers',
        'imagedescriber.data_models',
        'imagedescriber.dialogs_wx',
        'imagedescriber.workers_wx',
        'imagedescriber.prompt_editor_dialog',
        'imagedescriber.configure_dialog',
        'ai_providers',
        'data_models',
        'dialogs_wx',
        'workers_wx',
        'prompt_editor_dialog',  # Integrated PromptEditor
        'configure_dialog',  # Integrated IDTConfigure
        'scripts.metadata_extractor',
        'scripts.versioning',
        'scripts.config_loader',
        'models.provider_configs',
        'models.model_options',
        'metadata_extractor',
        'ollama',
        'openai',
        'anthropic',
        'cv2',
        'PIL',
        'pillow_heif',
        'requests',  # Required for geocoding
        'urllib3',  # Dependency of requests
        'charset_normalizer',  # Dependency of requests
        'certifi',  # Dependency of requests
        'idna',  # Dependency of requests
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
    console=True,  # Temporarily enabled for geocoding debug
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
