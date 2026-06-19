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

# Built-in prompts available by name on the CLI (--prompt <name>)
BUILT_IN_PROMPTS: dict[str, str] = {
    "detailed": (
        "Describe this image in detail for someone who cannot see it. "
        "Include the main subjects, their positions and appearance, the setting, "
        "colors, lighting, any visible text, and the overall mood or context."
    ),
    "brief": (
        "In one or two sentences, describe the main subject and setting of this image "
        "for someone who cannot see it."
    ),
    "technical": (
        "Describe this image with technical precision. Cover subjects, composition, "
        "camera angle, lighting, color palette, depth of field, and notable qualities."
    ),
    "social": (
        "Write a 2–3 sentence description of this image suitable for use as alt text "
        "when sharing on social media. Be specific and engaging."
    ),
    "document": (
        "This image may contain text, charts, or structured data. "
        "Transcribe all visible text. Describe any charts, diagrams, tables, or "
        "illustrations with enough detail that someone could understand the content."
    ),
    "news": (
        "Describe this image as you would for a news article caption. "
        "Include who or what is shown, what is happening, where it appears to be, "
        "and any contextual details visible in the image."
    ),
}

_CONFIG_FILE = Path.home() / ".idt" / "config.json"


@dataclass
class UserConfig:
    default_provider: str = "anthropic"
    default_model: str = "claude-opus-4-6"
    default_prompt_name: str = "detailed"
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
