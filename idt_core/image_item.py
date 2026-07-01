"""
ImageItem — one image and all its descriptions.
The sidecar .json file in the .idt/ mirror is the single source of truth.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Description:
    id: str
    text: str
    model: str
    provider: str
    prompt_name: str
    prompt_text: str
    timestamp: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    # The metadata context string that was prepended to the prompt ("Munich, Germany  Sep 12, 2025")
    metadata_context: Optional[str] = None

    @classmethod
    def create(
        cls,
        text: str,
        model: str,
        provider: str,
        prompt_name: str,
        prompt_text: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        metadata_context: Optional[str] = None,
    ) -> Description:
        return cls(
            id=str(uuid.uuid4()),
            text=text,
            model=model,
            provider=provider,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata_context=metadata_context,
        )

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "prompt_name": self.prompt_name,
            "prompt_text": self.prompt_text,
            "timestamp": self.timestamp,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
        if self.metadata_context:
            d["metadata_context"] = self.metadata_context
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Description:
        return cls(
            id=d["id"],
            text=d["text"],
            model=d["model"],
            provider=d["provider"],
            prompt_name=d.get("prompt_name", ""),
            prompt_text=d.get("prompt_text", ""),
            timestamp=d["timestamp"],
            input_tokens=d.get("input_tokens"),
            output_tokens=d.get("output_tokens"),
            metadata_context=d.get("metadata_context"),
        )


@dataclass
class ImageItem:
    source_path: Path        # absolute path to the original, never modified
    sidecar_path: Path       # .json in the .idt/ mirror directory

    # For HEIC originals, the converted JPEG lives in the .idt/ mirror too
    converted_path: Optional[Path] = None

    descriptions: list[Description] = field(default_factory=list)
    active_description_id: Optional[str] = None

    # Set when the active description has been embedded into a copy
    embedded_at: Optional[str] = None
    embedded_path: Optional[Path] = None

    tags: list[str] = field(default_factory=list)
    notes: str = ""

    # Extracted EXIF metadata (serialized dict from ImageMetadata.to_dict())
    metadata: dict = field(default_factory=dict)

    # Alt text from website when image was downloaded via `idt download`
    alt_text: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def described(self) -> bool:
        return len(self.descriptions) > 0

    @property
    def active_description(self) -> Optional[Description]:
        if not self.descriptions:
            return None
        if self.active_description_id:
            for d in self.descriptions:
                if d.id == self.active_description_id:
                    return d
        return self.descriptions[-1]

    @property
    def processable_path(self) -> Path:
        """Path we actually read for AI — converted JPEG for HEIC, original otherwise."""
        return self.converted_path or self.source_path

    @property
    def display_name(self) -> str:
        return self.source_path.name

    # ------------------------------------------------------------------ #
    # Mutations                                                            #
    # ------------------------------------------------------------------ #

    def add_description(self, description: Description) -> None:
        self.descriptions.append(description)
        self.active_description_id = description.id
        # A new description means any prior embed is stale
        self.embedded_at = None
        self.embedded_path = None

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        self.sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {
            "source": str(self.source_path),
            "converted_path": str(self.converted_path) if self.converted_path else None,
            "descriptions": [d.to_dict() for d in self.descriptions],
            "active_description_id": self.active_description_id,
            "embedded_at": self.embedded_at,
            "embedded_path": str(self.embedded_path) if self.embedded_path else None,
            "tags": self.tags,
            "notes": self.notes,
        }
        if self.metadata:
            data["metadata"] = self.metadata
        if self.alt_text:
            data["alt_text"] = self.alt_text
        self.sidecar_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def load(cls, sidecar_path: Path) -> ImageItem:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        return cls(
            source_path=Path(data["source"]),
            sidecar_path=sidecar_path,
            converted_path=Path(data["converted_path"]) if data.get("converted_path") else None,
            descriptions=[Description.from_dict(d) for d in data.get("descriptions", [])],
            active_description_id=data.get("active_description_id"),
            embedded_at=data.get("embedded_at"),
            embedded_path=Path(data["embedded_path"]) if data.get("embedded_path") else None,
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
            alt_text=data.get("alt_text"),
        )
