# -*- mode: python ; coding: utf-8 -*-
"""
ImageDescriber.app for macOS - PyInstaller Spec File

ACCESSIBILITY NOTES:
- Full WCAG 2.2 AA compliance through PyQt6
- VoiceOver support via NSAccessibility
- Keyboard-only navigation enabled
- All interactive elements have accessible names/descriptions
"""

a = Analysis(
    ['imagedescriber.py'],
    pathex=['..'],  # Add parent directory to path for scripts import
    binaries=[],
    datas=[
        ('../scripts/*.py', 'scripts'),  # Bundle all Python files from scripts
        ('../scripts/image_describer_config.json', 'scripts'),
        ('../scripts/workflow_config.json', 'scripts'),
        ('../models/*.py', 'models'),  # Bundle models directory
        ('ai_providers.py', '.'),
        ('data_models.py', '.'),
        ('worker_threads.py', '.'),
        ('ui_components.py', '.'),
        ('dialogs.py', '.'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'ollama',
        'pillow_heif',
        'cv2',
        'ai_providers',
        'data_models',
        'worker_threads',
        'ui_components',
        'dialogs',
        # All scripts modules
        'scripts',
        'scripts.ConvertImage',
        'scripts.config_loader',
        'scripts.resource_manager',
        'scripts.image_describer',
        'scripts.workflow_utils',
        'scripts.metadata_extractor',
        'scripts.video_metadata_extractor',
        'scripts.exif_embedder',
        'scripts.video_frame_extractor',
        'scripts.descriptions_to_html',
        'scripts.list_results',
        'scripts.guided_workflow',
        # Models directory
        'models',
        'models.model_registry',
        'models.provider_configs',
        'models.check_models',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'onnx.reference',
        'onnx.reference.ops',
        'torch.testing',
        'pytest',
        'polars',
        'thop',
        'scipy.signal',
        'workflow',  # Exclude conflicting workflow package (not our scripts.workflow)
    ],
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
    name='imagedescriber',
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
    name='imagedescriber.app',
    icon=None,
    bundle_identifier='com.idt.imagedescriber',
    info_plist={
        'CFBundleName': 'Image Describer',
        'CFBundleDisplayName': 'Image Describer',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 IDT Project',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # Accessibility
        'NSAccessibilityDescription': 'Batch process images with AI descriptions',
        # Camera/Photos access (for image files)
        'NSCameraUsageDescription': 'Access camera to describe images',
        'NSPhotoLibraryUsageDescription': 'Access photos to describe images',
        # Required for GUI apps
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
)
