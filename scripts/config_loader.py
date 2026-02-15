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
 6. Current working directory ./<filename>
 7. Bundled script directory (where this module lives)

Each resolver returns (path, source_label) so callers can optionally log
which layer provided the config.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

__all__ = [
    'resolve_config',
    'load_json_config',
]

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
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent

    script_dir = Path(__file__).parent

    candidates = []
    if exe_dir:
        candidates.append(exe_dir / 'scripts' / filename)
        candidates.append(exe_dir / filename)
    candidates.append(Path.cwd() / filename)
    candidates.append(script_dir / filename)

    for c in candidates:
        if _exists_file(c):
            if exe_dir and c.is_relative_to(exe_dir):
                if 'scripts' in c.parts:
                    return c, 'exe_scripts'
                return c, 'exe_dir'
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
