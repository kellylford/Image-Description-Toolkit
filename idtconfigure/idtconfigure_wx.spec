# -*- mode: python ; coding: utf-8 -*-
"""
IDTConfigure wxPython - macOS Build Spec

Builds the IDTConfigure GUI application using wxPython for macOS VoiceOver accessibility.
"""

from PyInstaller.utils.hooks import collect_all

# Collect all wxPython files
wx_datas, wx_binaries, wx_hiddenimports = collect_all('wx')

a = Analysis(
    ['idtconfigure_wx.py'],
    pathex=[],
    binaries=wx_binaries,
    datas=[
        ('../scripts', 'scripts'),
        ('../shared', 'shared'),
    ] + wx_datas,
    hiddenimports=[
        'wx',
        'wx.adv',
        'wx.lib.masked',
        'wx.lib.newevent',
        'shared.wx_common',
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
    [],
    exclude_binaries=True,
    name='IDTConfigure',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='IDTConfigure',
)

app = BUNDLE(
    coll,
    name='IDTConfigure.app',
    icon=None,
    bundle_identifier='com.idt.idtconfigure',
)
