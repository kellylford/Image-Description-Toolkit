"""Layered configuration loader for Image Description Toolkit.

Non-breaking helper used to allow external overrides of bundled JSON config
files without requiring a rebuild. If a higher-precedence source is not
present, existing bundled behavior is preserved.

Resolution order (first existing file wins):
 1. Explicit path (passed by caller)
 2. File env var (e.g. IDT_IMAGE_DESCRIBER_CONFIG)
 3. Directory env var IDT_CONFIG_DIR/<filename>
 4. Frozen exe dir /scripts/<filename>
 5. Frozen exe dir /<filename>
 6. User config dir (platform-specific, writable):
      macOS  : ~/Library/Application Support/IDT/<filename>
      Windows: %APPDATA%\\IDT\\<filename>
      Linux  : ~/.config/IDT/<filename>
 7. Bundled data dir (sys._MEIPASS/scripts/ in onefile mode)
 8. Current working directory ./<filename>
 9. Bundled script directory (where this module lives)

Each resolver returns (path, source_label) so callers can optionally log
which layer provided the config.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

__all__ = [
    'get_user_config_dir',
    'resolve_config',
    'load_json_config',
]


def get_user_config_dir() -> Path:
    """Return the platform-appropriate writable user config directory for IDT.

    macOS  : ~/Library/Application Support/IDT/
    Windows: %APPDATA%/IDT/   (C:/Users/<user>/AppData/Roaming/IDT/)
    Linux  : ~/.config/IDT/

    The directory is NOT created by this function — call .mkdir() at the
    write site so read paths never create the directory unnecessarily.
    """
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'IDT'
    elif sys.platform == 'win32':
        appdata = os.environ.get('APPDATA') or str(Path.home() / 'AppData' / 'Roaming')
        return Path(appdata) / 'IDT'
    else:
        # Linux / other POSIX
        xdg = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
        return Path(xdg) / 'IDT'

def _exists_file(p: Optional[Path]) -> bool:
    return bool(p and p.exists() and p.is_file())


def resolve_config(
    filename: str,
    explicit: Optional[str] = None,
    env_var_file: Optional[str] = None,
) -> Tuple[Path, str]:
    # 1 explicit
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = Path.cwd() / p
        if _exists_file(p):
            return p, 'explicit'

    # 2 file env var
    if env_var_file:
        env_val = os.getenv(env_var_file)
        if env_val:
            p = Path(env_val)
            if _exists_file(p):
                return p, env_var_file.lower()

    # 3 directory env var
    cfg_dir = os.getenv('IDT_CONFIG_DIR')
    if cfg_dir:
        p = Path(cfg_dir) / filename
        if _exists_file(p):
            # Log when using IDT_CONFIG_DIR to help with troubleshooting
            print(f"INFO: Using config from IDT_CONFIG_DIR environment variable", file=sys.stderr)
            print(f"      Location: {p}", file=sys.stderr)
            print(f"      To change: Windows: setx IDT_CONFIG_DIR \"\"", file=sys.stderr)
            print(f"                 macOS: unset IDT_CONFIG_DIR (in ~/.zshrc or ~/.bash_profile)", file=sys.stderr)
            return p, 'idt_config_dir'

    exe_dir: Optional[Path] = None
    meipass_dir: Optional[Path] = None
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        # In onefile mode, bundled data files land in sys._MEIPASS (temp extract dir)
        _meipass = getattr(sys, '_MEIPASS', None)
        if _meipass:
            meipass_dir = Path(_meipass)

    script_dir = Path(__file__).parent

    candidates = []
    if exe_dir:
        candidates.append(exe_dir / 'scripts' / filename)
        candidates.append(exe_dir / filename)
    # User config dir (writable, platform-specific) — takes priority over bundled defaults
    user_config_dir = get_user_config_dir()
    candidates.append(user_config_dir / filename)
    # onefile bundle: data files extracted to _MEIPASS/scripts/ (per spec datas dest)
    if meipass_dir:
        candidates.append(meipass_dir / 'scripts' / filename)
        candidates.append(meipass_dir / filename)
    candidates.append(Path.cwd() / filename)
    candidates.append(script_dir / filename)

    for c in candidates:
        if _exists_file(c):
            if exe_dir and c.is_relative_to(exe_dir):
                if 'scripts' in c.parts:
                    return c, 'exe_scripts'
                return c, 'exe_dir'
            if meipass_dir and c.is_relative_to(meipass_dir):
                return c, 'bundled'
            if c.parent == user_config_dir:
                return c, 'user_config'
            if c.parent == Path.cwd():
                return c, 'cwd'
            if c.parent == script_dir:
                return c, 'bundled'
            return c, 'found'

    # fallback path (likely non-existent) for logging
    return script_dir / filename, 'missing_fallback'


def load_json_config(
    filename: str,
    explicit: Optional[str] = None,
    env_var_file: Optional[str] = None,
):
    import json
    path, source = resolve_config(filename, explicit=explicit, env_var_file=env_var_file)
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f), path, source
    except Exception:
        return {}, path, source
