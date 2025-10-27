# -*- mode: python ; coding: utf-8 -*-
"""
FINAL WORKING SPEC FILE - INCLUDES EVERYTHING EXPLICITLY

MAINTENANCE NOTES:
- This spec file is optimized for executable-first usage
- When adding new modules, update hiddenimports list
- Test with test_executable.py after building
- Keep excludes list updated to avoid conflicts
- Use build_executable.sh for automated builds
"""

a = Analysis(
    ['../idt_cli.py'],
    pathex=['..', '../scripts'],
    binaries=[],
    datas=[
        # Include ALL scripts files individually
        ('../scripts/workflow.py', 'scripts'),
        ('../scripts/workflow_utils.py', 'scripts'), 
        ('../scripts/image_describer.py', 'scripts'),
        ('../scripts/metadata_extractor.py', 'scripts'),
        ('../scripts/ConvertImage.py', 'scripts'),
        ('../scripts/descriptions_to_html.py', 'scripts'),
        ('../scripts/video_frame_extractor.py', 'scripts'),
        ('../scripts/config_loader.py', 'scripts'),
        ('../scripts/guided_workflow.py', 'scripts'),
        ('../scripts/list_prompts.py', 'scripts'),
        ('../scripts/list_results.py', 'scripts'),
        ('../scripts/workflow_config.json', 'scripts'),
        ('../scripts/image_describer_config.json', 'scripts'),
        # Include essential directories
        ('../models', 'models'),
        ('../analysis', 'analysis'),
        ('../VERSION', '.'),
    ],
    hiddenimports=[
        # EXPLICITLY include every module we need
        'scripts',
        'scripts.workflow',
        'scripts.workflow_utils',
        'scripts.image_describer', 
        'metadata_extractor',
        'scripts.ConvertImage',
        'scripts.descriptions_to_html',
        'scripts.video_frame_extractor',
        'scripts.config_loader',
        'scripts.list_prompts',
        'scripts.list_results',
        'models.check_models',
        'analysis.analyze_workflow_stats',
        'analysis.analyze_description_content',
        'analysis.combine_workflow_descriptions',
        # imagedescriber package
        'imagedescriber',
        'imagedescriber.ai_providers',
        # Standard library imports
        'json', 'pathlib', 'subprocess', 'logging', 'datetime', 'argparse',
        # Image processing
        'PIL', 'PIL.Image', 'PIL.ImageOps', 'pillow_heif',
        # AI providers - CRITICAL for executable
        'requests', 'anthropic', 'openai',
        # Anthropic dependencies
        'anthropic._client',
        'anthropic._base_client',
        'anthropic._models',
        'anthropic._types',
        'anthropic._utils',
        'anthropic._constants',
        'anthropic._exceptions',
        'anthropic.types',
        'anthropic.resources',
        # OpenAI dependencies
        'openai._client',
        'openai._base_client',
        'openai._models',
        'openai._types',
        'openai._utils',
        'openai._constants',
        'openai._exceptions',
        'openai.types',
        'openai.resources',
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)