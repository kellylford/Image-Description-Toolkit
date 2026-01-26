# -*- mode: python ; coding: utf-8 -*-
"""
Viewer wxPython - Cross-Platform Build Spec

Builds the Viewer GUI application using wxPython for accessibility.
Supports both Windows (.exe) and macOS (.app) builds.
"""

import sys
from PyInstaller.utils.hooks import collect_all

# Collect all wxPython files
wx_datas, wx_binaries, wx_hiddenimports = collect_all('wx')

a = Analysis(
    ['viewer_wx.py'],
    pathex=[],
    binaries=wx_binaries,
    datas=[
        ('../scripts', 'scripts'),  # Bundle scripts for config files
        ('../shared', 'shared'),     # Bundle shared utilities
    ] + wx_datas,
    hiddenimports=[
        'wx',
        'wx.adv',
        'wx.lib.newevent',
        'shared.wx_common',
        'shared.exif_utils',
        'models.model_registry',
        'config_loader',  # Note: no scripts. prefix for frozen mode
        'list_results',   # Note: no scripts. prefix for frozen mode
        'ollama',
    ] + wx_hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='Viewer',
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
