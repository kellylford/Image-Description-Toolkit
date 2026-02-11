# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Get the project root (parent of imagedescriber/)
project_root = Path(SPECPATH).parent

# Collect all wxPython files
wx_datas, wx_binaries, wx_hiddenimports = collect_all('wx')

a = Analysis(
    [str(project_root / 'imagedescriber' / 'imagedescriber_wx.py')],
    pathex=[
        str(project_root),
        str(project_root / 'imagedescriber'),
        str(project_root / 'scripts'),
        str(project_root / 'shared'),
        str(project_root / 'models'),
    ],
    binaries=wx_binaries,
    datas=[
        (str(project_root / 'scripts' / '*.json'), 'scripts'),
        (str(project_root / 'VERSION'), '.'),
    ] + wx_datas,
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
        'ai_providers',
        'data_models',
        'dialogs_wx',
        'workers_wx',
        'chat_window_wx',  # Chat with Image feature
        'prompt_editor_dialog',  # Integrated PromptEditor
        'configure_dialog',  # Integrated IDTConfigure
        'download_dialog',  # URL download dialog (frozen mode)
        'batch_progress_dialog',  # Phase 3: Batch progress dialog (frozen mode)
        'scripts.metadata_extractor',
        'scripts.versioning',
        'scripts.config_loader',
        'scripts.descriptions_to_html',  # HTML export functionality
        'scripts.web_image_downloader',  # URL image downloader
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

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
