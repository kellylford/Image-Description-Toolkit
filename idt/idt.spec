# -*- mode: python ; coding: utf-8 -*-
"""
IDT CLI - PyInstaller Spec File

This builds the unified CLI tool that routes commands to all IDT scripts.

Directory structure:
- idt/ - This directory (contains idt_cli.py, idt_runner.py)
- ../scripts/ - Workflow scripts
- ../analysis/ - Analysis scripts
- ../models/ - Model registry

All paths use ../ prefix since we're building from idt/ subdirectory.
"""

# Web download dependencies - use PyInstaller's collect_all for BeautifulSoup4
from PyInstaller.utils.hooks import collect_all
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')

a = Analysis(
    ['idt_cli.py'],
    pathex=[],
    binaries=bs4_binaries,
    datas=[
        # Include ALL scripts files
        ('../scripts/workflow.py', 'scripts'),
        ('../scripts/workflow_utils.py', 'scripts'),
        ('../scripts/versioning.py', 'scripts'),
        ('../scripts/image_describer.py', 'scripts'),
        ('../scripts/metadata_extractor.py', 'scripts'),
        ('../scripts/video_metadata_extractor.py', 'scripts'),
        ('../scripts/exif_embedder.py', 'scripts'),
        ('../scripts/ConvertImage.py', 'scripts'),
        ('../scripts/descriptions_to_html.py', 'scripts'),
        ('../scripts/video_frame_extractor.py', 'scripts'),
        ('../scripts/web_image_downloader.py', 'scripts'),
        ('../scripts/config_loader.py', 'scripts'),
        ('../scripts/resource_manager.py', 'scripts'),
        ('../scripts/guided_workflow.py', 'scripts'),
        ('../scripts/list_prompts.py', 'scripts'),
        ('../scripts/list_results.py', 'scripts'),
        ('../scripts/workflow_config.json', 'scripts'),
        ('../scripts/image_describer_config.json', 'scripts'),
        ('../scripts/video_frame_extractor_config.json', 'scripts'),
        # Include models and analysis directories
        ('../models', 'models'),
        ('../analysis', 'analysis'),
        # Include imagedescriber package for ai_providers
        ('../imagedescriber/ai_providers.py', 'imagedescriber'),
        ('../imagedescriber/data_models.py', 'imagedescriber'),
        # Include VERSION file
        ('../VERSION', '.'),
    ] + bs4_datas,
    hiddenimports=[
        # Scripts modules
        'scripts',
        'scripts.workflow',
        'scripts.workflow_utils',
        'scripts.versioning',
        'scripts.image_describer',
        'scripts.metadata_extractor',
        'scripts.guided_workflow',
        'scripts.resource_manager',
        'scripts.video_metadata_extractor',
        'scripts.exif_embedder',
        'scripts.ConvertImage',
        'scripts.descriptions_to_html',
        'scripts.video_frame_extractor',
        'scripts.web_image_downloader',
        'scripts.config_loader',
        'scripts.list_prompts',
        'scripts.list_results',
        # Models and analysis
        'models.check_models',
        'analysis.analyze_workflow_stats',
        'analysis.analyze_description_content',
        'analysis.combine_workflow_descriptions',
        # imagedescriber package
        'imagedescriber',
        'imagedescriber.ai_providers',
        # Standard library
        'json', 'pathlib', 'subprocess', 'logging', 'datetime', 'argparse',
        # Image processing
        'PIL', 'PIL.Image', 'PIL.ImageOps', 'pillow_heif',
        # EXIF handling
        'piexif', 'piexif.helper',
        # Web support
        'html.parser', 'urllib3', 'urllib.parse', 'urllib.request',
        'hashlib', 'requests.adapters', 'requests.packages',
        # AI providers
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
    ] + bs4_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['workflow'],  # Exclude conflicting external workflow package
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

