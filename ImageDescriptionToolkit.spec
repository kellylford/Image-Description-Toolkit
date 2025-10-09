# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Image Description Toolkit
Builds a single-file executable that bundles all dependencies.

To build:
    pyinstaller ImageDescriptionToolkit.spec

Output:
    dist/ImageDescriptionToolkit.exe
"""

block_cipher = None

# Analysis - what to include
# NOTE: Using noarchive and module-level excludes to avoid workflow hook conflict
import sys
sys.setrecursionlimit(5000)  # Prevent deep recursion issues

a = Analysis(
    ['idt_cli.py'],                    # Entry point
    pathex=[],
    binaries=[],
    datas=[
        # Include all Python scripts from scripts directory
        ('scripts/*.py', 'scripts'),
        
        # Include configuration files from scripts directory
        ('scripts/*.json', 'scripts'),
        
        # Include imagedescriber Python modules
        ('imagedescriber/*.py', 'imagedescriber'),
        
        # Include VERSION file
        ('VERSION', '.'),
        
        # Include model Python files
        ('models/*.py', 'models'),
        
        # Include analysis scripts
        ('analysis/*.py', 'analysis'),
    ],
    hiddenimports=[
        # Core dependencies
        'PIL',
        'PIL._tkinter_finder',
        'requests',
        'ollama',
        'openai',
        'anthropic',
        'pillow_heif',
        
        # Standard library modules that might be missed
        'subprocess',
        'pathlib',
        'json',
        'csv',
        'argparse',
        'logging',
        're',
        
        # Analysis modules
        'statistics',
        'datetime',
        
        # Video processing (optional)
        'cv2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unrelated workflow package (we have our own workflow.py)
        'workflow',
        'apache-airflow',  # Another workflow package to exclude
        
        # Exclude GUI frameworks we don't use
        'PyQt5',
        'PyQt6',
        'tkinter',
        'matplotlib',
        'numpy',  # Exclude unless needed for video processing
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        
        # Exclude test frameworks
        'pytest',
        'unittest',
        'nose',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    module_collection_mode={
        'workflow': 'py',  # Treat workflow as python-only, skip hooks
    },
)

# Pack into PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create single-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ImageDescriptionToolkit',
    debug=False,                        # Set to True for debugging
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                          # Compress with UPX (reduces size 30-50%)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,                      # Keep console window (CLI tool)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',                 # Optional: add icon file if available
)
