"""
Base provider interface.
All providers receive image bytes and a prompt, return a DescriptionResult.
No file paths, no temp copies — just bytes in, text out.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class DescriptionResult:
    text: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class BaseProvider(ABC):
    @abstractmethod
    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        """
        Send image_bytes to the AI and return a description.
        mime_type: e.g. "image/jpeg", "image/png"
        prompt: the user's instruction text
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name!r})"
