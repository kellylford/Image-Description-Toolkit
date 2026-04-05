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

# Conditionally collect mlx-vlm and mlx (macOS Apple Silicon only)
# mlx-vlm must be installed in the build venv: pip install mlx-vlm
import sys as _sys
if _sys.platform == 'darwin':
    try:
        mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = collect_all('mlx_vlm')
    except Exception:
        mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = [], [], []
    try:
        # collect_all('mlx') includes libmlx.dylib (Metal framework) and all mlx submodules
        mlx_datas, mlx_binaries, mlx_hiddenimports = collect_all('mlx')
    except Exception:
        mlx_datas, mlx_binaries, mlx_hiddenimports = [], [], []
else:
    mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = [], [], []
    mlx_datas, mlx_binaries, mlx_hiddenimports = [], [], []

a = Analysis(
    ['idt_cli.py'],
    pathex=['..'],  # Add parent directory to import path
    binaries=bs4_binaries + mlx_vlm_binaries + mlx_binaries,
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
        ('../scripts/video_describer.py', 'scripts'),
        ('../scripts/enhanced_scene_detector.py', 'scripts'),
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
        ('../imagedescriber/__init__.py', 'imagedescriber'),
        ('../imagedescriber/ai_providers.py', 'imagedescriber'),
        ('../imagedescriber/data_models.py', 'imagedescriber'),
        # Include VERSION file
        ('../VERSION', '.'),
    ] + bs4_datas + mlx_vlm_datas + mlx_datas,
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
        'scripts.video_describer',
        'scripts.enhanced_scene_detector',
        'scripts.web_image_downloader',
        'scripts.config_loader',
        'scripts.list_prompts',
        'scripts.list_results',
        # Person identification
        'scripts.persons_manager',
        'scripts.persons_cli',
        'scripts.person_identifier',
        'scripts.face_db',
        'scripts.face_engine',
        'scripts.install_persons_engine',
        # Models and analysis
        'models.check_models',
        'models.claude_models',  # Central Claude model configuration
        'models.openai_models',  # Central OpenAI model configuration
        'analysis.stats_analysis',  # Fixed: was analyze_workflow_stats (wrong module name)
        'analysis.content_analysis',  # Fixed: was analyze_description_content (wrong module name)
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
        # MLX / Apple Metal (macOS Apple Silicon only — no-op on Windows)
        'mlx_vlm',
        'mlx',
        'mlx.core',
        'mlx.nn',
        'mlx.nn.layers',
        'transformers',
        'transformers.models.auto',
        # Qwen2-VL modules (for mlx-community/Qwen2-VL-2B model)
        'transformers.models.qwen2_vl',
        'transformers.models.qwen2_vl.configuration_qwen2_vl',
        'transformers.models.qwen2_vl.image_processing_qwen2_vl',
        'transformers.models.qwen2_vl.image_processing_qwen2_vl_fast',
        'transformers.models.qwen2_vl.modeling_qwen2_vl',
        'transformers.models.qwen2_vl.processing_qwen2_vl',
        'transformers.models.qwen2_vl.video_processing_qwen2_vl',
        # Qwen2.5-VL modules (for mlx-community/Qwen2.5-VL-3B and 7B models)
        'transformers.models.qwen2_5_vl',
        'transformers.models.qwen2_5_vl.configuration_qwen2_5_vl',
        'transformers.models.qwen2_5_vl.modeling_qwen2_5_vl',
        'transformers.models.qwen2_5_vl.processing_qwen2_5_vl',
        'huggingface_hub',
        'safetensors',
        'sentencepiece',
        'tokenizers',
        # stdlib modules torch/torchvision/facenet/sklearn need at import time.
        # face_engine_packages is loaded at runtime so PyInstaller can't auto-detect these.
        # Full list derived from exhaustive import-trace of all four packages together.
        'timeit', 'modulefinder', 'colorsys', 'fractions', 'statistics', 'numbers',
        'dis', 'opcode', 'profile', 'pstats', 'cProfile', 'pickletools',
        'nturl2path', 'quopri', 'stringprep',
        # ctypes submodules (ctypes itself is included but submodules are not auto-bundled)
        'ctypes._endian', 'ctypes.util', 'ctypes.wintypes',
        # unittest (all submodules needed by torch._dynamo)
        'unittest', 'unittest.case', 'unittest.loader', 'unittest.main',
        'unittest.mock', 'unittest.result', 'unittest.runner', 'unittest.signals',
        'unittest.suite', 'unittest.util',
        # re submodules (re is a PY3_BASE_MODULE but submodules need explicit listing)
        're._casefix', 're._compiler', 're._constants', 're._parser',
        # asyncio full package
        'asyncio', 'asyncio.base_events', 'asyncio.base_futures',
        'asyncio.base_subprocess', 'asyncio.base_tasks', 'asyncio.constants',
        'asyncio.coroutines', 'asyncio.events', 'asyncio.exceptions',
        'asyncio.format_helpers', 'asyncio.futures', 'asyncio.locks',
        'asyncio.log', 'asyncio.mixins', 'asyncio.proactor_events',
        'asyncio.protocols', 'asyncio.queues', 'asyncio.runners',
        'asyncio.selector_events', 'asyncio.sslproto', 'asyncio.staggered',
        'asyncio.streams', 'asyncio.subprocess', 'asyncio.taskgroups',
        'asyncio.tasks', 'asyncio.threads', 'asyncio.timeouts',
        'asyncio.transports', 'asyncio.trsock',
        'asyncio.windows_events', 'asyncio.windows_utils',
        # collections submodule
        'collections.abc',
        # concurrent.futures full package
        'concurrent.futures', 'concurrent.futures._base',
        'concurrent.futures.process', 'concurrent.futures.thread',
        # email full package
        'email', 'email._encoded_words', 'email._parseaddr', 'email._policybase',
        'email.base64mime', 'email.charset', 'email.encoders', 'email.errors',
        'email.feedparser', 'email.header', 'email.iterators', 'email.message',
        'email.parser', 'email.quoprimime', 'email.utils',
        # html
        'html', 'html.entities', 'html.parser',
        # http full package
        'http', 'http.client', 'http.cookiejar', 'http.cookies',
        # importlib submodules
        'importlib._abc', 'importlib.abc',
        'importlib.metadata', 'importlib.metadata._adapters',
        'importlib.metadata._collections', 'importlib.metadata._functools',
        'importlib.metadata._itertools', 'importlib.metadata._meta',
        'importlib.metadata._text',
        'importlib.readers', 'importlib.resources', 'importlib.resources._adapters',
        'importlib.resources._common', 'importlib.resources._itertools',
        'importlib.resources._legacy', 'importlib.resources.abc',
        'importlib.resources.readers',
        # json submodules
        'json', 'json.decoder', 'json.encoder', 'json.scanner',
        # multiprocessing full package
        'multiprocessing', 'multiprocessing.connection', 'multiprocessing.context',
        'multiprocessing.pool', 'multiprocessing.process', 'multiprocessing.queues',
        'multiprocessing.reduction', 'multiprocessing.resource_sharer',
        'multiprocessing.resource_tracker', 'multiprocessing.spawn',
        'multiprocessing.synchronize', 'multiprocessing.util',
        # urllib full package
        'urllib', 'urllib.error', 'urllib.parse', 'urllib.request', 'urllib.response',
        # xml.etree
        'xml', 'xml.etree', 'xml.etree.ElementPath', 'xml.etree.ElementTree',
        # zipfile submodule
        'zipfile._path',
    ] + bs4_hiddenimports + mlx_vlm_hiddenimports + mlx_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['workflow', 'setuptools', 'pip'],  # Exclude conflicting/problematic packages
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

