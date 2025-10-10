# -*- mode: python ; coding: utf-8 -*-
"""
FINAL WORKING SPEC FILE - INCLUDES EVERYTHING EXPLICITLY
"""

a = Analysis(
    ['idt_cli.py'],
    pathex=['.', 'scripts'],
    binaries=[],
    datas=[
        # Include ALL scripts files individually
        ('scripts/workflow.py', 'scripts'),
        ('scripts/workflow_utils.py', 'scripts'), 
        ('scripts/image_describer.py', 'scripts'),
        ('scripts/ConvertImage.py', 'scripts'),
        ('scripts/descriptions_to_html.py', 'scripts'),
        ('scripts/video_frame_extractor.py', 'scripts'),
        ('scripts/config_loader.py', 'scripts'),
        ('scripts/workflow_config.json', 'scripts'),
        ('scripts/image_describer_config.json', 'scripts'),
        # Include essential directories
        ('models', 'models'),
        ('analysis', 'analysis'),
        ('VERSION', '.'),
    ],
    hiddenimports=[
        # EXPLICITLY include every module we need
        'scripts',
        'scripts.workflow',
        'scripts.workflow_utils',
        'scripts.image_describer', 
        'scripts.ConvertImage',
        'scripts.descriptions_to_html',
        'scripts.video_frame_extractor',
        'scripts.config_loader',
        'models.check_models',
        'analysis.analyze_workflow_stats',
        'analysis.analyze_description_content',
        'analysis.combine_workflow_descriptions',
        # Standard library imports
        'json', 'pathlib', 'subprocess', 'logging', 'datetime', 'argparse',
        # Image processing
        'PIL', 'PIL.Image', 'PIL.ImageOps', 'pillow_heif',
        # AI providers  
        'requests', 'anthropic', 'openai',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['workflow'],  # Exclude the problematic external workflow package
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
    name='idt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)