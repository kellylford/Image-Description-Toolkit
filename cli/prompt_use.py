"""Whether a run's provider takes a prompt, and how a run reports the prompt it uses.

Shared by cli.main and cli.guide. It lives apart from cli.main so guideme can use it without
importing cli.main, which imports guideme.
"""
from __future__ import annotations

from typing import Optional


def uses_prompt(provider: Optional[str]) -> bool:
    """False for a provider that takes no prompt (Windows AI, whose models are fixed kinds of
    description). Its runs record no prompt and must not change a workspace's saved one."""
    from idt_core.providers.registry import uses_prompt as _registry_uses_prompt

    return provider is None or _registry_uses_prompt(provider)


def prompt_label(provider: Optional[str], model: Optional[str], prompt_name: str) -> str:
    """The prompt as a run reports it before starting."""
    if not uses_prompt(provider):
        return f"not used (Windows AI describes with its {model} kind)"
    return prompt_name
