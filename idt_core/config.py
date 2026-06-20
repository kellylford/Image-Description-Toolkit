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


def _load_prompt_library() -> tuple[dict[str, str], str]:
    """Load the canonical prompt set from image_describer_config.json.

    Returns (prompts, default_prompt_name). This is the shared, researched
    prompt library used everywhere; the GUI reads the same file directly.
    """
    try:
        from config_loader import load_json_config          # frozen mode
    except ImportError:
        try:
            from scripts.config_loader import load_json_config  # dev mode
        except ImportError:
            return dict(_FALLBACK_PROMPTS), _FALLBACK_DEFAULT_PROMPT

    config, _path, _src = load_json_config('image_describer_config.json')
    variations = dict(config.get("prompt_variations") or {}) if config else {}
    if not variations:
        return dict(_FALLBACK_PROMPTS), _FALLBACK_DEFAULT_PROMPT
    default = (config.get("default_prompt_style") or "").strip()
    if default not in variations:
        default = "narrative" if "narrative" in variations else next(iter(variations))
    return variations, default


# Built-in prompts available by name on the CLI (--prompt <name>), loaded from
# the shared config at import time.
BUILT_IN_PROMPTS, DEFAULT_PROMPT_NAME = _load_prompt_library()

_CONFIG_FILE = Path.home() / ".idt" / "config.json"


@dataclass
class UserConfig:
    default_provider: str = "ollama"
    default_model: str = "moondream"
    default_prompt_name: str = DEFAULT_PROMPT_NAME
    custom_prompts: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls) -> UserConfig:
        if not _CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return cls()
        obj = cls()
        for key in ("default_provider", "default_model", "default_prompt_name"):
            if key in data:
                setattr(obj, key, data[key])
        obj.custom_prompts = data.get("custom_prompts", {})
        return obj

    def save(self) -> None:
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "default_provider": self.default_provider,
            "default_model": self.default_model,
            "default_prompt_name": self.default_prompt_name,
            "custom_prompts": self.custom_prompts,
        }
        _CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_prompt_text(self, name: str) -> Optional[str]:
        """Look up a prompt by name — custom prompts override built-ins."""
        return self.custom_prompts.get(name) or BUILT_IN_PROMPTS.get(name)

    def list_prompts(self) -> dict[str, str]:
        """All available prompts: built-ins plus any user-defined ones."""
        return {**BUILT_IN_PROMPTS, **self.custom_prompts}
