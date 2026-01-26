# -*- mode: python ; coding: utf-8 -*-
"""
Prompt Editor wxPython - macOS Build Spec

Builds the Prompt Editor GUI application using wxPython for macOS VoiceOver accessibility.
"""

from PyInstaller.utils.hooks import collect_all

# Collect all wxPython files
wx_datas, wx_binaries, wx_hiddenimports = collect_all('wx')

a = Analysis(
    ['prompt_editor_wx.py'],
    pathex=[],
    binaries=wx_binaries,
    datas=[
        ('../scripts', 'scripts'),
        ('../shared', 'shared'),
    ] + wx_datas,
    hiddenimports=[
        'wx',
        'wx.adv',
        'wx.lib.newevent',
        'shared.wx_common',
        'ollama',
        'imagedescriber.ai_providers',
        'scripts.versioning',
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
    name='PromptEditor',
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
