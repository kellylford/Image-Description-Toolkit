# -*- mode: python ; coding: utf-8 -*-
"""
IDT CLI v4.5 - PyInstaller Spec File

Builds the new unified CLI (cli/main.py) with all 13 commands powered by idt_core.

Directory structure (relative to idt/ where this spec lives):
  ../cli/         - New CLI entry point and guide wizard
  ../idt_core/    - Core engine (pipeline, providers, metadata, embed, etc.)
  ../scripts/     - Legacy scripts (still needed for some embed/convert paths)
  ../models/      - Model registry
  ../analysis/    - Analysis scripts

PyInstaller is run from the idt/ directory by build_idt.bat.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules
import sys as _sys

# BeautifulSoup4 — used by idt_core.downloader
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')

# OpenCV — used by idt_core.video for frame extraction
try:
    cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')
except Exception:
    cv2_datas, cv2_binaries, cv2_hiddenimports = [], [], []

# macOS Apple Silicon only — no-op on Windows
if _sys.platform == 'darwin':
    try:
        mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = collect_all('mlx_vlm')
    except Exception:
        mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = [], [], []
    try:
        mlx_datas, mlx_binaries, mlx_hiddenimports = collect_all('mlx')
    except Exception:
        mlx_datas, mlx_binaries, mlx_hiddenimports = [], [], []
else:
    mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = [], [], []
    mlx_datas, mlx_binaries, mlx_hiddenimports = [], [], []

a = Analysis(
    ['../cli/main.py'],
    pathex=['..'],          # project root — makes idt_core, cli, models, scripts all importable
    binaries=bs4_binaries + cv2_binaries + mlx_vlm_binaries + mlx_binaries,
    datas=[
        # idt_core configuration defaults
        ('../scripts/image_describer_config.json', 'scripts'),
        ('../scripts/workflow_config.json', 'scripts'),
        # Legacy scripts still called by embed/convert paths
        ('../scripts/embed_descriptions.py', 'scripts'),
        ('../scripts/exif_embedder.py', 'scripts'),
        ('../scripts/ConvertImage.py', 'scripts'),
        ('../scripts/descriptions_to_html.py', 'scripts'),
        # Analysis
        ('../analysis', 'analysis'),
        # Models
        ('../models', 'models'),
        # Version
        ('../VERSION', '.'),
    ] + bs4_datas + cv2_datas + mlx_vlm_datas + mlx_datas,
    hiddenimports=[
        # ---- New CLI ----
        'cli',
        'cli.main',
        'cli.guide',

        # ---- idt_core engine ----
        'idt_core',
        'idt_core.project',
        'idt_core.pipeline',
        'idt_core.image_item',
        'idt_core.scanner',
        'idt_core.metadata',
        'idt_core.embedder',
        'idt_core.exporter',
        'idt_core.config',
        'idt_core.converter',
        'idt_core.progress',
        'idt_core.watcher',
        'idt_core.downloader',
        'idt_core.video',
        'idt_core.providers',
        'idt_core.providers.base',
        'idt_core.providers.claude',
        'idt_core.providers.ollama',
        'idt_core.providers.openai_provider',
        'idt_core.providers.florence',

        # ---- scripts still used by idt_core helpers ----
        'scripts.embed_descriptions',
        'scripts.exif_embedder',
        'scripts.ConvertImage',
        'scripts.descriptions_to_html',
        'embed_descriptions',   # frozen bare-name import
        'exif_embedder',        # frozen bare-name import

        # ---- models / analysis ----
        'models.claude_models',
        'models.openai_models',
        'models.provider_configs',
        'analysis.combine_workflow_descriptions',

        # ---- jaraco (required by pkg_resources / setuptools >= 75) ----
        'jaraco', 'jaraco.text', 'jaraco.functools',
        'jaraco.context', 'jaraco.collections',

        # ---- image / EXIF ----
        'PIL', 'PIL.Image', 'PIL.ImageOps', 'PIL.PngImagePlugin',
        'pillow_heif',
        'piexif', 'piexif.helper',

        # ---- AI providers ----
        'anthropic',
        'anthropic._client',
        'anthropic._base_client',
        'anthropic._models',
        'anthropic._types',
        'anthropic._utils',
        'anthropic._constants',
        'anthropic._exceptions',
        'anthropic.types',
        'anthropic.resources',
        'openai',
        'openai._client',
        'openai._base_client',
        'openai._models',
        'openai._types',
        'openai._utils',
        'openai._constants',
        'openai._exceptions',
        'openai.types',
        'openai.resources',
        'ollama',

        # ---- HTTP / network ----
        'requests', 'requests.adapters', 'requests.packages',
        'urllib3', 'charset_normalizer', 'certifi', 'idna',

        # ---- web scraping (downloader) ----
        'bs4', 'bs4.builder', 'bs4.builder._htmlparser',
        'bs4.builder._lxml', 'soupsieve',

        # ---- video (OpenCV) ----
        'cv2',

        # ---- HuggingFace / Florence (local model) ----
        'transformers', 'transformers.models.auto',
        'huggingface_hub', 'safetensors', 'sentencepiece', 'tokenizers',
        'torch',

        # ---- macOS MLX (no-op on Windows) ----
        'mlx_vlm', 'mlx', 'mlx.core', 'mlx.nn', 'mlx.nn.layers',
    ] + bs4_hiddenimports + cv2_hiddenimports + mlx_vlm_hiddenimports + mlx_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hooks/rthooks/pyi_rth_pkgres.py'],
    excludes=['setuptools', 'pip'],
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
