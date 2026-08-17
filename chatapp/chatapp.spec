# -*- mode: python ; coding: utf-8 -*-
"""
IDT Chat - PyInstaller Spec File

Builds the standalone accessible chat client (chatapp/chat_app_wx.py).

Directory structure (relative to chatapp/ where this spec lives):
  ../idt_core/    - Chat engine, providers, config (no wx)
  ../shared/      - Shared wx helpers
  ../scripts/     - JSON config files only

PyInstaller is run from the chatapp/ directory by build_chatapp.bat.

Deliberately lean compared with imagedescriber_wx.spec: this app never touches
OpenCV, Pillow-HEIF, MLX or the description pipeline, so none of that is
bundled. Chat needs the three provider SDKs and wx, nothing more.
"""

import re
import sys as _sys
from pathlib import Path as _Path

from PyInstaller.utils.hooks import collect_all

a = Analysis(
    ['chat_app_wx.py'],
    pathex=['..', '.'],     # project root for idt_core; '.' for flat imports
    binaries=[],
    datas=[
        ('../scripts/image_describer_config.json', 'scripts'),
        ('../shared/*.py', 'shared'),
        # ClaudeSpeak speech routers (JAWS/NVDA/OneCore/SAPI on Windows,
        # VoiceOver/say on macOS), run as detached processes by
        # shared/speech_engine.py.
        ('../shared/speech/*', 'shared/speech'),
        ('../VERSION', '.'),
    ],
    hiddenimports=[
        # ---- this app ----
        'chatapp',
        'chatapp.chat_app_wx',

        # ---- shared wx helpers ----
        # The chat worker lives in shared/ so ImageDescriber's chat window and
        # this app use the same one.
        'shared',
        'shared.chat_worker_wx',
        'shared.speech_engine',
        # Names controls for VoiceOver through NSAccessibility. ctypes only,
        # no PyObjC, but it still has to be in the bundle: without it every
        # text box and list in the macOS build goes back to being unlabelled.
        'shared.mac_accessibility',

        # ---- idt_core chat engine ----
        'idt_core',
        'idt_core.chat',
        'idt_core.chat.attachments',
        'idt_core.chat.mlx',
        'idt_core.chat.engine',
        'idt_core.chat.errors',
        'idt_core.chat.events',
        'idt_core.chat.messages',
        'idt_core.chat.providers',
        'idt_core.chat.store',
        'idt_core.chat.tokens',
        'idt_core.chat.tools',

        # ---- idt_core support ----
        'idt_core.config',
        'idt_core.config_loader',
        'idt_core.keys',
        'idt_core.logger',
        'idt_core.updater',
        'idt_core.workspace',
        'idt_core.providers',
        'idt_core.providers.base',
        'idt_core.providers.claude',
        'idt_core.providers.ollama',
        'idt_core.providers.openai_provider',
        'idt_core.providers.registry',
        # Model catalog + its disk cache. Reached only through function-level
        # imports (registry.model_limits, ProviderDialog), which is exactly the
        # shape hiddenimports exists for.
        'idt_core.providers.catalog',
        'idt_core.providers.model_cache',

        # ---- wxPython ----
        'wx', 'wx.adv', 'wx.lib', 'wx.lib.newevent',

        # ---- AI provider SDKs ----
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

        # ---- HTTP ----
        'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna',
        'httpx', 'httpcore', 'anyio', 'sniffio', 'h11',

        # ---- image resize for OpenAI attachments ----
        'PIL', 'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'setuptools', 'pip',
        # Not used by chat, and each is large.
        'cv2', 'numpy.f2py', 'matplotlib', 'scipy',
        'torch', 'transformers', 'mlx', 'mlx_vlm',
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
    name='IDTChat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---------------------------------------------------------------------------
# macOS .app bundle
#
# Mirrors imagedescriber_wx.spec. The version is parsed rather than taken
# whole: VERSION can read "4.5.0Beta1 bld050", and CFBundleShortVersionString
# must be numeric or the bundle is rejected.
# ---------------------------------------------------------------------------
if _sys.platform == 'darwin':
    _version_file = _Path(SPECPATH).parent / 'VERSION'
    _version_text = _version_file.read_text().strip() if _version_file.exists() else ''
    _match = re.match(r'\d+(?:\.\d+)*', _version_text)
    _version = _match.group(0) if _match else '4.0.0'

    app = BUNDLE(
        exe,
        name='IDTChat.app',
        icon=None,
        bundle_identifier='com.imagedescriptiontoolkit.chat',
        version=_version,
        info_plist={
            'CFBundleShortVersionString': _version,
            'CFBundleVersion': _version_text or _version,
            'CFBundleName': 'IDT Chat',
            'CFBundleDisplayName': 'IDT Chat',
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
        },
    )
