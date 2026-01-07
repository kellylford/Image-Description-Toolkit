# -*- mode: python ; coding: utf-8 -*-
"""
FINAL WORKING SPEC FILE FOR macOS - INCLUDES EVERYTHING EXPLICITLY

MAINTENANCE NOTES:
- This spec file is optimized for macOS executable-first usage
- When adding new modules, update hiddenimports list
- Test with test_executable.py after building
- Keep excludes list updated to avoid conflicts
- Use build_idt_macos.sh for automated builds

MACOS-SPECIFIC NOTES:
- Creates standalone binary (not .app bundle) for CLI tool
- Uses POSIX paths instead of Windows paths
- No console window parameter needed (always console on macOS)
- Accessibility handled automatically by macOS for CLI tools

RECENT UPDATES:
- January 2026: Created macOS version from Windows spec
- October 2025: Added video metadata extraction modules (video_metadata_extractor.py, exif_embedder.py)
- October 2025: Added piexif for EXIF embedding in extracted video frames
- October 2025: Added web image download support (web_image_downloader.py, beautifulsoup4)
"""

# Web download dependencies - use PyInstaller's collect_all for BeautifulSoup4
from PyInstaller.utils.hooks import collect_all
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')

a = Analysis(
    ['../../idt_cli.py'],
    pathex=['../..', '../../scripts'],
    binaries=bs4_binaries,
    datas=[
        # Include ALL scripts files individually
        ('../../scripts/workflow.py', 'scripts'),
        ('../../scripts/workflow_utils.py', 'scripts'), 
        ('../../scripts/versioning.py', 'scripts'),
        ('../../scripts/image_describer.py', 'scripts'),
        ('../../scripts/metadata_extractor.py', 'scripts'),
        ('../../scripts/video_metadata_extractor.py', 'scripts'),
        ('../../scripts/exif_embedder.py', 'scripts'),
        ('../../scripts/ConvertImage.py', 'scripts'),
        ('../../scripts/descriptions_to_html.py', 'scripts'),
        ('../../scripts/video_frame_extractor.py', 'scripts'),
        ('../../scripts/web_image_downloader.py', 'scripts'),
        ('../../scripts/config_loader.py', 'scripts'),
        ('../../scripts/resource_manager.py', 'scripts'),
        ('../../scripts/guided_workflow.py', 'scripts'),
        ('../../scripts/list_prompts.py', 'scripts'),
        ('../../scripts/list_results.py', 'scripts'),
        ('../../scripts/workflow_config.json', 'scripts'),
        ('../../scripts/image_describer_config.json', 'scripts'),
        # Include essential directories
        ('../../models', 'models'),
        ('../../analysis', 'analysis'),
        ('../../VERSION', '.'),
    ] + bs4_datas,
    hiddenimports=[
        # EXPLICITLY include every module we need
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
        # EXIF handling for video frame metadata
        'piexif', 'piexif.helper',
        # Web image download support - using PyInstaller's collect_all
        'html.parser', 'urllib3', 'urllib.parse', 'urllib.request',
        'hashlib', 'requests.adapters', 'requests.packages',
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
    ] + bs4_hiddenimports,
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
    console=True,  # CLI tool always uses console
    disable_windowed_traceback=False,
    # macOS-specific settings
    argv_emulation=False,  # Not needed for CLI
    target_arch=None,  # Auto-detect (supports both Intel and Apple Silicon)
    codesign_identity=None,  # Optional: Add code signing identity for distribution
    entitlements_file=None,  # Optional: Add entitlements for sandboxing/notarization
)
