"""
User-level configuration stored in ~/.idt/config.json.
Project-level overrides live in the .idt/project.json beside each source directory.
API keys are never stored here — read from environment variables by providers.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Prompt library — SINGLE SOURCE OF TRUTH.
#
# IDT's researched prompt set lives in scripts/image_describer_config.json
# (key "prompt_variations"). The GUI, the legacy CLI, and idt_core all read
# that one file so every surface offers the exact same named prompts. Do NOT
# hardcode a prompt list here — that is what caused the CLI and GUI to drift
# apart in v4.5. The fallback below is an emergency net only, used solely if
# the shared config cannot be loaded (missing/corrupt); it is intentionally
# tiny so a silent fallback is obvious rather than masquerading as the real set.
# ---------------------------------------------------------------------------
_FALLBACK_PROMPTS: dict[str, str] = {
    "narrative": (
        "Describe this image in a narrative style. Start with the overall scene, "
        "then describe specific objects and people from left to right. Include colors, "
        "clothing details, and spatial relationships. Use concrete, specific language."
    ),
}
_FALLBACK_DEFAULT_PROMPT = "narrative"


def _load_shared_config() -> tuple[dict[str, str], str, str]:
    """Load prompts and defaults from image_describer_config.json.

    Returns (prompts, default_prompt_name, default_ollama_model).
    Single source of truth for all surfaces: CLI, GUI, and idt_core.
    To change the default Ollama model, edit image_describer_config.json
    → "default_model". All Python code reads from there at import time.
    """
    try:
        from idt_core.config_loader import load_json_config
    except ImportError:
        try:
            from config_loader import load_json_config          # frozen mode
        except ImportError:
            return dict(_FALLBACK_PROMPTS), _FALLBACK_DEFAULT_PROMPT, "llama3.2-vision"

    config, _path, _src = load_json_config('image_describer_config.json')
    variations = dict(config.get("prompt_variations") or {}) if config else {}
    if not variations:
        return dict(_FALLBACK_PROMPTS), _FALLBACK_DEFAULT_PROMPT, "llama3.2-vision"
    default_prompt = (config.get("default_prompt_style") or "").strip()
    if default_prompt not in variations:
        default_prompt = "narrative" if "narrative" in variations else next(iter(variations))
    # Strip tag suffix (e.g. "llama3.2-vision:latest" → "llama3.2-vision") for
    # consistency with how the CLI and workspace record model names.
    raw_model = (config.get("default_model") or "llama3.2-vision").strip()
    default_model = raw_model.split(":")[0] if ":" in raw_model else raw_model
    return variations, default_prompt, default_model


# Loaded once at import time from the shared config JSON.
# To change defaults project-wide, edit scripts/image_describer_config.json.
BUILT_IN_PROMPTS, DEFAULT_PROMPT_NAME, DEFAULT_OLLAMA_MODEL = _load_shared_config()

_CONFIG_FILE = Path.home() / ".idt" / "config.json"


@dataclass
class UserConfig:
    default_provider: str = "ollama"
    default_model: str = DEFAULT_OLLAMA_MODEL
    default_prompt_name: str = DEFAULT_PROMPT_NAME
    custom_prompts: dict[str, str] = field(default_factory=dict)
    workspace_root: Optional[str] = None  # None → ~/Documents/idt
    # Whether new workspaces copy the user's originals into images/ (self-contained,
    # portable) or reference them in place. Default off. See
    # docs/design/image-handling-lifecycle.md.
    copy_originals: bool = False
    # Whether `idt download` (CLI) and the ImageDescriber download dialog (GUI) save
    # a downloaded image's HTML alt text as its own description (model "Website Alt
    # Text"), in addition to any AI-generated one. Default on.
    preserve_alt_text: bool = True
    # Whether ImageDescriber checks GitHub for a newer release at startup. The
    # manual Help > Check for Updates always runs regardless. See idt_core/updater.py.
    auto_check_updates: bool = True
    # A version the user chose "Skip This Version" on; the startup check never
    # offers that exact version again. Manual checks ignore it.
    skipped_update_version: Optional[str] = None
    # ISO timestamp of the last startup check, used to throttle to once a day so
    # every launch does not hit the GitHub API.
    last_update_check: Optional[str] = None

    def workspace_root_path(self) -> Path:
        """Resolved workspace root. Defaults to ~/Documents/idt."""
        if self.workspace_root:
            return Path(self.workspace_root).expanduser().resolve()
        return Path.home() / "Documents" / "idt"

    @classmethod
    def load(cls) -> "UserConfig":
        if not _CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return cls()
        obj = cls()
        for key in ("default_provider", "default_model", "default_prompt_name", "workspace_root",
                    "skipped_update_version", "last_update_check"):
            if key in data:
                setattr(obj, key, data[key])
        obj.custom_prompts = data.get("custom_prompts", {})
        obj.copy_originals = bool(data.get("copy_originals", False))
        obj.preserve_alt_text = bool(data.get("preserve_alt_text", True))
        obj.auto_check_updates = bool(data.get("auto_check_updates", True))
        return obj

    def save(self) -> None:
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "default_provider": self.default_provider,
            "default_model": self.default_model,
            "default_prompt_name": self.default_prompt_name,
            "custom_prompts": self.custom_prompts,
            "copy_originals": self.copy_originals,
            "preserve_alt_text": self.preserve_alt_text,
            "auto_check_updates": self.auto_check_updates,
        }
        if self.workspace_root:
            data["workspace_root"] = self.workspace_root
        if self.skipped_update_version:
            data["skipped_update_version"] = self.skipped_update_version
        if self.last_update_check:
            data["last_update_check"] = self.last_update_check
        _CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_prompt_text(self, name: str) -> Optional[str]:
        """Look up a prompt by name — custom prompts override built-ins."""
        return self.custom_prompts.get(name) or BUILT_IN_PROMPTS.get(name)

    def list_prompts(self) -> dict[str, str]:
        """All available prompts: built-ins plus any user-defined ones."""
        return {**BUILT_IN_PROMPTS, **self.custom_prompts}
