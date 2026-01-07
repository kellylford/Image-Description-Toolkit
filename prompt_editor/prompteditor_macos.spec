# -*- mode: python ; coding: utf-8 -*-
"""
PromptEditor.app for macOS - PyInstaller Spec File

ACCESSIBILITY NOTES:
- Text editing with full VoiceOver support
- Keyboard shortcuts for all operations
- Form controls with accessible labels
"""

a = Analysis(
    ['prompt_editor.py'],
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
    name='prompteditor',
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
    name='prompteditor.app',
    icon=None,
    bundle_identifier='com.idt.prompteditor',
    info_plist={
        'CFBundleName': 'Prompt Editor',
        'CFBundleDisplayName': 'Prompt Editor',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 IDT Project',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # Accessibility
        'NSAccessibilityDescription': 'Edit AI prompt templates for image descriptions',
        # Required for GUI apps
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
)
