# -*- mode: python ; coding: utf-8 -*-
"""
Viewer.app for macOS - PyInstaller Spec File

ACCESSIBILITY NOTES:
- macOS .app bundles automatically support VoiceOver
- PyQt6 provides native NSAccessibility support
- Info.plist includes accessibility metadata
- Keyboard navigation handled by Qt framework
"""

a = Analysis(
    ['viewer.py'],
    pathex=[],
    binaries=[],
    datas=[('../scripts', 'scripts')],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'ollama',
        'models.provider_configs',
        'models.model_registry',
        'workflow_utils'
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
    name='viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # Auto-detect architecture
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Optional: Add .icns file for macOS icon
)

app = BUNDLE(
    exe,
    name='viewer.app',
    icon=None,  # Optional: Add .icns file
    bundle_identifier='com.idt.viewer',  # Unique bundle ID
    info_plist={
        'CFBundleName': 'Image Description Viewer',
        'CFBundleDisplayName': 'Image Description Viewer',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 IDT Project',
        'LSMinimumSystemVersion': '10.13.0',  # macOS High Sierra or later
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # Accessibility
        'NSAccessibilityDescription': 'View and monitor image description workflows',
        # Document types (if opening workflow directories)
        'CFBundleDocumentTypes': [],
        # Required for GUI apps
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
)
