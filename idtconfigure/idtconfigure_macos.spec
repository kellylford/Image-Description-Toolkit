# -*- mode: python ; coding: utf-8 -*-
"""
IDTConfigure.app for macOS - PyInstaller Spec File

ACCESSIBILITY NOTES:
- Configuration management with full keyboard access
- VoiceOver support for all settings
- Clear accessible labels for form fields
"""

a = Analysis(
    ['idtconfigure.py'],
    pathex=[],
    binaries=[],
    datas=[('../scripts', 'scripts')],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
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
    name='idtconfigure',
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
    icon=None,
)

app = BUNDLE(
    exe,
    name='idtconfigure.app',
    icon=None,
    bundle_identifier='com.idt.configure',
    info_plist={
        'CFBundleName': 'IDT Configure',
        'CFBundleDisplayName': 'IDT Configure',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 IDT Project',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # Accessibility
        'NSAccessibilityDescription': 'Configure Image Description Toolkit settings',
        # Required for GUI apps
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
)
