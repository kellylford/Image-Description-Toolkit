# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Get the project root (parent of imagedescriber/)
project_root = Path(SPECPATH).parent

# Collect all wxPython files
wx_datas, wx_binaries, wx_hiddenimports = collect_all('wx')

# Collect all OpenCV files (needed for macOS .dylib dependencies)
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')

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
    try:
        # torch (CPU-only) is required by transformers processor layer for some
        # models (e.g. Phi-3.5-Vision) even though inference runs on Metal via MLX.
        torch_datas, torch_binaries, torch_hiddenimports = collect_all('torch')
    except Exception:
        torch_datas, torch_binaries, torch_hiddenimports = [], [], []
else:
    mlx_vlm_datas, mlx_vlm_binaries, mlx_vlm_hiddenimports = [], [], []
    mlx_datas, mlx_binaries, mlx_hiddenimports = [], [], []
    torch_datas, torch_binaries, torch_hiddenimports = [], [], []

a = Analysis(
    [str(project_root / 'imagedescriber' / 'imagedescriber_wx.py')],
    pathex=[
        str(project_root),
        str(project_root / 'imagedescriber'),
        str(project_root / 'scripts'),
        str(project_root / 'shared'),
        str(project_root / 'models'),
    ],
    binaries=wx_binaries + cv2_binaries + mlx_vlm_binaries + mlx_binaries + torch_binaries,
    datas=[
        (str(project_root / 'scripts' / '*.json'), 'scripts'),
        (str(project_root / 'scripts' / 'video_describer.py'), 'scripts'),
        (str(project_root / 'scripts' / 'enhanced_scene_detector.py'), 'scripts'),
        (str(project_root / 'VERSION'), '.'),
    ] + wx_datas + cv2_datas + mlx_vlm_datas + mlx_datas + torch_datas,
    hiddenimports=[
        'wx.adv',
        'wx.lib.newevent',
        'shared.wx_common',
        'shared',
        'imagedescriber.ai_providers',
        'imagedescriber.data_models',
        'imagedescriber.dialogs_wx',
        'imagedescriber.workers_wx',
        'imagedescriber.chat_window_wx',  # Chat with Image feature
        'imagedescriber.viewer_components', # Viewer components
        'imagedescriber.prompt_editor_dialog',
        'imagedescriber.configure_dialog',
        'imagedescriber.download_dialog',  # URL download dialog
        'imagedescriber.batch_progress_dialog',  # Phase 3: Batch progress dialog
        'imagedescriber.workspace_stats_dialog',  # Workspace Statistics dialog
        'ai_providers',
        'data_models',
        'dialogs_wx',
        'workers_wx',
        'chat_window_wx',  # Chat with Image feature
        'prompt_editor_dialog',  # Integrated PromptEditor
        'configure_dialog',  # Integrated IDTConfigure
        'download_dialog',  # URL download dialog (frozen mode)
        'batch_progress_dialog',  # Phase 3: Batch progress dialog (frozen mode)
        'workspace_stats_dialog',  # Workspace Statistics dialog (frozen mode)
        'scripts.metadata_extractor',
        'scripts.versioning',
        'scripts.config_loader',
        'scripts.descriptions_to_html',  # HTML export functionality
        'scripts.web_image_downloader',  # URL image downloader
        # Person identification
        'scripts.persons_manager',
        'scripts.person_identifier',
        'scripts.face_db',
        'scripts.face_engine',
        'scripts.install_persons_engine',
        'imagedescriber.person_dialogs_wx',
        'person_dialogs_wx',
        'persons_manager',
        'person_identifier',
        'face_db',
        'face_engine',
        'install_persons_engine',
        'scripts.video_describer',       # Video description feature
        'scripts.enhanced_scene_detector',  # Enhanced scene detection
        'video_describer',               # Frozen mode: bare module name
        'enhanced_scene_detector',       # Frozen mode: bare module name
        'models.provider_configs',
        'models.claude_models',  # Central Claude model configuration
        'models.openai_models',  # Central OpenAI model configuration
        'models.model_options',
        'metadata_extractor',
        'web_image_downloader',  # URL image downloader (frozen mode)
        'ollama',
        'openai',
        'anthropic',
        'cv2',
        'PIL',
        'pillow_heif',
        'requests',  # Required for geocoding and URL downloads
        'urllib3',  # Dependency of requests
        'charset_normalizer',  # Dependency of requests
        'certifi',  # Dependency of requests
        'idna',  # Dependency of requests
        'bs4',  # BeautifulSoup4 for URL downloads
        'bs4.builder',
        'bs4.builder._htmlparser',
        'bs4.builder._lxml',
        'soupsieve',  # BeautifulSoup dependency
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
        # LLaVA modules — kept for potential future use, currently broken with
        # transformers 5.x (patch_size NoneType in LLaVA processor)
        'transformers.models.llava',
        'transformers.models.llava.configuration_llava',
        'transformers.models.llava.modeling_llava',
        'transformers.models.llava.processing_llava',
        # Phi-3 modules (for mlx-community/phi-3.5-vision-instruct-4bit)
        'transformers.models.phi3',
        'transformers.models.phi3.configuration_phi3',
        'transformers.models.phi3.modeling_phi3',
        # Gemma3 modules (for mlx-community/gemma-3-4b-it-qat-4bit)
        'transformers.models.gemma3',
        'transformers.models.gemma3.configuration_gemma3',
        'transformers.models.gemma3.modeling_gemma3',
        'transformers.models.gemma3.processing_gemma3',
        'transformers.models.gemma3.image_processing_gemma3',
        'transformers.models.gemma3.image_processing_gemma3_fast',
        # Idefics3 / SmolVLM modules (for mlx-community/SmolVLM-Instruct-4bit)
        'transformers.models.idefics3',
        'transformers.models.idefics3.configuration_idefics3',
        'transformers.models.idefics3.modeling_idefics3',
        'transformers.models.idefics3.processing_idefics3',
        'transformers.models.idefics3.image_processing_idefics3',
        'transformers.models.idefics3.image_processing_idefics3_fast',
        # MLLama modules (for mlx-community/Llama-3.2-11B-Vision-Instruct-4bit)
        'transformers.models.mllama',
        'transformers.models.mllama.configuration_mllama',
        'transformers.models.mllama.modeling_mllama',
        'transformers.models.mllama.processing_mllama',
        'transformers.models.mllama.image_processing_mllama',
        'transformers.models.mllama.image_processing_mllama_fast',
        # PyTorch — CPU-only, required by transformers processor layer for LLaVA/Phi models
        'torch',
        'torchvision',
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
        'huggingface_hub',
        'safetensors',
        'sentencepiece',
        'tokenizers',
    ] + wx_hiddenimports + cv2_hiddenimports + mlx_vlm_hiddenimports + mlx_hiddenimports + torch_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['setuptools', 'pip'],  # Prevent pyi_rth_setuptools bootstrap crash
    noarchive=False,
)

pyz = PYZ(a.pure)

# onefile mode (PyInstaller warns it's deprecated with .app bundles, but it works)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ImageDescriber',
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
)

# Read version from VERSION file
version_file = project_root / 'VERSION'
version = '4.0.0'  # Fallback
if version_file.exists():
    version_text = version_file.read_text().strip()
    # Extract just the version number (e.g., "4.0.0Beta1 bld050" -> "4.0.0")
    version = version_text.split()[0].rstrip('Beta1234567890')
    if not version:
        version = '4.0.0'

# macOS .app bundle
app = BUNDLE(
    exe,
    name='ImageDescriber.app',
    icon=None,
    bundle_identifier='com.imagedescriber.app',
    version=version,
    info_plist={
        'CFBundleShortVersionString': version,
        'CFBundleVersion': version_text if version_file.exists() else version,
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
    },
)
