"""
Workspace — the unified `.idtw` bundle shared by the CLI and the GUI.

A workspace is a single self-contained directory the user names. It holds copies
of the images, their descriptions, chat sessions, and derived artifacts. Both
tools open and write the SAME bundle. The user's originals are never moved or
modified — they are copied in, and the source path is kept only as provenance.

See docs/design/unified-workspace.md for the full format reference.

Layout:
    MyTrip.idtw/
        manifest.json
        images/           copies of source images (collision-safe names)
        descriptions/     one <imagename>.json sidecar per image
        chats/            chat sessions not tied to a single image
        derived/          frames/, converted/, ... generated artifacts
        logs/
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .scanner import scan_images, is_image, is_video

BUNDLE_EXT = ".idtw"
FORMAT_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text to path crash-safely (temp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------- #
# Description — unified shape (superset of idt_core.Description and GUI's       #
# ImageDescription). See design doc §4.1.                                       #
# --------------------------------------------------------------------------- #

@dataclass
class WorkspaceDescription:
    id: str
    text: str
    provider: str = ""
    model: str = ""
    prompt_name: str = ""
    prompt_text: str = ""
    created: str = field(default_factory=_now)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    metadata_context: Optional[str] = None
    detection_data: list = field(default_factory=list)
    finish_reason: str = ""
    response_id: str = ""
    # Tool-specific fields preserved verbatim for lossless round-trips
    # (e.g. the GUI's per-description EXIF metadata dict and token_usage).
    extra: dict = field(default_factory=dict)

    @classmethod
    def create(cls, text: str, *, provider: str = "", model: str = "",
               prompt_name: str = "", prompt_text: str = "",
               input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
               metadata_context: Optional[str] = None) -> "WorkspaceDescription":
        return cls(
            id=str(uuid.uuid4()),
            text=text,
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata_context=metadata_context,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.id,
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "prompt_name": self.prompt_name,
            "prompt_text": self.prompt_text,
            "created": self.created,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
        if self.metadata_context:
            d["metadata_context"] = self.metadata_context
        if self.detection_data:
            d["detection_data"] = self.detection_data
        if self.finish_reason:
            d["finish_reason"] = self.finish_reason
        if self.response_id:
            d["response_id"] = self.response_id
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WorkspaceDescription":
        return cls(
            id=d.get("id") or str(uuid.uuid4()),
            text=d.get("text", ""),
            provider=d.get("provider", ""),
            model=d.get("model", ""),
            prompt_name=d.get("prompt_name", d.get("prompt_style", "")),
            prompt_text=d.get("prompt_text", d.get("custom_prompt", "")),
            created=d.get("created", d.get("timestamp", _now())),
            input_tokens=d.get("input_tokens"),
            output_tokens=d.get("output_tokens"),
            metadata_context=d.get("metadata_context"),
            detection_data=d.get("detection_data", []),
            finish_reason=d.get("finish_reason", ""),
            response_id=d.get("response_id", ""),
            extra=d.get("extra", {}),
        )


# --------------------------------------------------------------------------- #
# WorkspaceItem — one image in the bundle and all its descriptions.            #
# --------------------------------------------------------------------------- #

@dataclass
class WorkspaceItem:
    image: str                 # bundle-internal filename in images/ (the KEY)
    source_path: str = ""      # original absolute path, provenance only
    storage: str = "copy"      # "copy" (v4.5) | "reference" (future)
    item_type: str = "image"   # image | video | extracted_frame | downloaded_image
    subfolder: Optional[str] = None

    converted: Optional[str] = None      # derived/ path used for AI (HEIC->JPEG)
    parent_video: Optional[str] = None
    video_metadata: Optional[dict] = None

    download_url: Optional[str] = None
    download_timestamp: Optional[str] = None
    alt_text: Optional[str] = None

    metadata: dict = field(default_factory=dict)
    exif_datetime: Optional[str] = None
    file_mtime: Optional[float] = None

    active_description_id: Optional[str] = None
    embedded_at: Optional[str] = None
    tags: list = field(default_factory=list)
    notes: str = ""
    is_missing: bool = False

    # Tool-specific fields not part of the core schema (e.g. GUI batch state),
    # preserved verbatim so a GUI<->bundle round-trip is lossless.
    extra: dict = field(default_factory=dict)

    descriptions: list = field(default_factory=list)  # list[WorkspaceDescription]

    # ----- properties ----- #
    @property
    def display_name(self) -> str:
        if self.source_path:
            return Path(self.source_path).name
        return self.image

    @property
    def described(self) -> bool:
        return len(self.descriptions) > 0

    @property
    def active_description(self) -> Optional[WorkspaceDescription]:
        if not self.descriptions:
            return None
        if self.active_description_id:
            for d in self.descriptions:
                if d.id == self.active_description_id:
                    return d
        return self.descriptions[-1]

    def add_description(self, desc: WorkspaceDescription) -> None:
        self.descriptions.append(desc)
        self.active_description_id = desc.id
        self.embedded_at = None  # a new description makes any prior embed stale

    # ----- serialization ----- #
    def to_dict(self) -> dict:
        d: dict = {
            "image": self.image,
            "source_path": self.source_path,
            "storage": self.storage,
            "item_type": self.item_type,
            "subfolder": self.subfolder,
            "converted": self.converted,
            "parent_video": self.parent_video,
            "video_metadata": self.video_metadata,
            "download_url": self.download_url,
            "download_timestamp": self.download_timestamp,
            "alt_text": self.alt_text,
            "metadata": self.metadata,
            "exif_datetime": self.exif_datetime,
            "file_mtime": self.file_mtime,
            "active_description_id": self.active_description_id,
            "embedded_at": self.embedded_at,
            "tags": self.tags,
            "notes": self.notes,
            "is_missing": self.is_missing,
            "descriptions": [d.to_dict() for d in self.descriptions],
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WorkspaceItem":
        return cls(
            image=d["image"],
            source_path=d.get("source_path", ""),
            storage=d.get("storage", "copy"),
            item_type=d.get("item_type", "image"),
            subfolder=d.get("subfolder"),
            converted=d.get("converted"),
            parent_video=d.get("parent_video"),
            video_metadata=d.get("video_metadata"),
            download_url=d.get("download_url"),
            download_timestamp=d.get("download_timestamp"),
            alt_text=d.get("alt_text"),
            metadata=d.get("metadata", {}),
            exif_datetime=d.get("exif_datetime"),
            file_mtime=d.get("file_mtime"),
            active_description_id=d.get("active_description_id"),
            embedded_at=d.get("embedded_at"),
            tags=d.get("tags", []),
            notes=d.get("notes", ""),
            is_missing=d.get("is_missing", False),
            extra=d.get("extra", {}),
            descriptions=[WorkspaceDescription.from_dict(x) for x in d.get("descriptions", [])],
        )


# --------------------------------------------------------------------------- #
# Workspace — the bundle itself.                                              #
# --------------------------------------------------------------------------- #

@dataclass
class WorkspaceDefaults:
    provider: str = "ollama"
    model: str = "moondream"
    prompt_name: str = "detailed"
    prompt_text: str = ""


class Workspace:
    """A `.idtw` bundle on disk. Open or create one, then add images and descriptions."""

    def __init__(self, path: Path):
        self.path = Path(os.path.abspath(path))
        self.name: str = self.path.stem
        self.created: str = _now()
        self.modified: str = self.created
        self.sources: list[dict] = []
        self.defaults = WorkspaceDefaults()
        self.batch_state: Optional[dict] = None
        self.cached_ollama_models: Optional[list] = None
        self.geocode_enabled: bool = False
        # True once at least one image has been successfully described.
        # Guards provider/model resolution so a failed run can't poison the defaults
        # for the next run (workspace provider is only honored when there ARE descriptions).
        self.has_any_descriptions: bool = False
        # lazy index of source_path -> bundle image name, for idempotent adds
        self._source_index: Optional[dict] = None

    # ----- directory accessors ----- #
    @property
    def manifest_path(self) -> Path:
        return self.path / "manifest.json"

    @property
    def images_dir(self) -> Path:
        return self.path / "images"

    @property
    def descriptions_dir(self) -> Path:
        return self.path / "descriptions"

    @property
    def chats_dir(self) -> Path:
        return self.path / "chats"

    @property
    def logs_dir(self) -> Path:
        return self.path / "logs"

    def derived_dir(self, kind: str = "") -> Path:
        d = self.path / "derived"
        if kind:
            d = d / kind
        return d

    # ----- create / open ----- #
    @staticmethod
    def is_bundle(path: Path) -> bool:
        path = Path(path)
        return path.is_dir() and (path / "manifest.json").is_file()

    @classmethod
    def create(cls, path: Path, name: Optional[str] = None) -> "Workspace":
        """Create a new bundle at path. Appends .idtw if missing."""
        path = Path(path)
        if path.suffix.lower() != BUNDLE_EXT:
            path = path.with_name(path.name + BUNDLE_EXT)
        path = Path(os.path.abspath(path))
        ws = cls(path)
        if name:
            ws.name = name
        path.mkdir(parents=True, exist_ok=True)
        for d in (ws.images_dir, ws.descriptions_dir, ws.chats_dir):
            d.mkdir(parents=True, exist_ok=True)
        ws._source_index = {}
        ws.save_manifest()
        return ws

    @classmethod
    def open(cls, path: Path) -> "Workspace":
        """Open an existing bundle, or create one if it does not exist yet."""
        path = Path(path)
        if path.suffix.lower() != BUNDLE_EXT and not cls.is_bundle(path):
            path = path.with_name(path.name + BUNDLE_EXT)
        path = Path(os.path.abspath(path))
        if not cls.is_bundle(path):
            return cls.create(path)
        ws = cls(path)
        data = json.loads(ws.manifest_path.read_text(encoding="utf-8"))
        ws.name = data.get("name", path.stem)
        ws.created = data.get("created", _now())
        ws.modified = data.get("modified", ws.created)
        ws.sources = data.get("sources", [])
        defs = data.get("defaults", {})
        ws.defaults = WorkspaceDefaults(
            provider=defs.get("provider", "ollama"),
            model=defs.get("model", "moondream"),
            prompt_name=defs.get("prompt_name", "detailed"),
            prompt_text=defs.get("prompt_text", ""),
        )
        ws.has_any_descriptions = data.get("has_any_descriptions", False)
        ws.batch_state = data.get("batch_state")
        ws.cached_ollama_models = data.get("cached_ollama_models")
        ws.geocode_enabled = data.get("geocode_enabled", False)
        return ws

    # ----- manifest ----- #
    def save_manifest(self) -> None:
        self.modified = _now()
        data = {
            "format": "idtw",
            "version": FORMAT_VERSION,
            "name": self.name,
            "created": self.created,
            "modified": self.modified,
            "sources": self.sources,
            "defaults": {
                "provider": self.defaults.provider,
                "model": self.defaults.model,
                "prompt_name": self.defaults.prompt_name,
                "prompt_text": self.defaults.prompt_text,
            },
            "has_any_descriptions": self.has_any_descriptions,
            "batch_state": self.batch_state,
            "cached_ollama_models": self.cached_ollama_models,
            "geocode_enabled": self.geocode_enabled,
        }
        _atomic_write_text(self.manifest_path, json.dumps(data, indent=2, ensure_ascii=False))

    # ----- image add ----- #
    def _build_source_index(self) -> dict:
        idx: dict = {}
        for item in self.items():
            if item.source_path:
                idx[item.source_path] = item.image
        return idx

    def _bundle_name_for(self, source_path: Path, subfolder: Optional[str]) -> str:
        """Pick a collision-safe filename inside images/ for a new source file."""
        base = source_path.name
        if not (self.images_dir / base).exists():
            return base
        # collision: prefix with flattened subfolder
        if subfolder:
            flat = subfolder.replace("/", "__").replace("\\", "__")
            candidate = f"{flat}__{base}"
            if not (self.images_dir / candidate).exists():
                return candidate
        # still colliding: append a counter before the extension
        stem, suffix = source_path.stem, source_path.suffix
        n = 1
        while (self.images_dir / f"{stem}_{n}{suffix}").exists():
            n += 1
        return f"{stem}_{n}{suffix}"

    def add_image(self, source_path: Path, subfolder: Optional[str] = None) -> WorkspaceItem:
        """
        Copy a source image into the bundle (if not already present) and return its item.
        Idempotent: adding the same source path twice returns the existing item.
        The original file is never modified.
        """
        source_path = Path(os.path.abspath(source_path))
        if self._source_index is None:
            self._source_index = self._build_source_index()

        existing = self._source_index.get(str(source_path))
        if existing:
            return self.get_item(existing)

        self.images_dir.mkdir(parents=True, exist_ok=True)
        bundle_name = self._bundle_name_for(source_path, subfolder)
        dest = self.images_dir / bundle_name
        shutil.copy2(source_path, dest)  # copy2 preserves mtime; original untouched

        item = WorkspaceItem(
            image=bundle_name,
            source_path=str(source_path),
            item_type="video" if is_video(source_path) else "image",
            subfolder=subfolder,
        )
        self.save_item(item)
        self._source_index[str(source_path)] = bundle_name
        return item

    def add_source_folder(self, folder: Path, recursive: bool = True,
                          include_videos: bool = False) -> list[WorkspaceItem]:
        """Scan a folder and add every image. Records the folder in manifest.sources."""
        folder = Path(os.path.abspath(folder))
        added: list[WorkspaceItem] = []
        if recursive:
            paths = list(scan_images(folder, include_videos=include_videos))
        else:
            paths = sorted(
                p for p in folder.iterdir()
                if p.is_file() and (is_image(p) or (include_videos and is_video(p)))
            )
        for p in paths:
            try:
                sub = str(p.parent.relative_to(folder)) if p.parent != folder else None
            except ValueError:
                sub = None
            if sub == ".":
                sub = None
            added.append(self.add_image(p, subfolder=sub))

        entry = {"path": str(folder), "recursive": recursive, "added": _now()}
        if not any(s.get("path") == str(folder) for s in self.sources):
            self.sources.append(entry)
        self.save_manifest()
        return added

    # ----- item persistence ----- #
    def _sidecar_path(self, image_name: str) -> Path:
        return self.descriptions_dir / (image_name + ".json")

    def save_item(self, item: WorkspaceItem) -> None:
        _atomic_write_text(
            self._sidecar_path(item.image),
            json.dumps(item.to_dict(), indent=2, ensure_ascii=False),
        )

    def get_item(self, image_name: str) -> Optional[WorkspaceItem]:
        p = self._sidecar_path(image_name)
        if not p.exists():
            return None
        return WorkspaceItem.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def items(self) -> list[WorkspaceItem]:
        if not self.descriptions_dir.is_dir():
            return []
        out: list[WorkspaceItem] = []
        for p in sorted(self.descriptions_dir.glob("*.json")):
            try:
                out.append(WorkspaceItem.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return out

    def image_path(self, item: WorkspaceItem) -> Path:
        """Absolute path to the item's image (bundle copy or original reference)."""
        if item.storage == "reference" and item.source_path:
            return Path(item.source_path)
        return self.images_dir / item.image

    # ----- chats ----- #
    def save_chat(self, chat: dict) -> None:
        chat_id = chat.get("id") or f"chat_{uuid.uuid4().hex}"
        chat["id"] = chat_id
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(
            self.chats_dir / (chat_id + ".json"),
            json.dumps(chat, indent=2, ensure_ascii=False),
        )

    def chats(self) -> list[dict]:
        if not self.chats_dir.is_dir():
            return []
        out = []
        for p in sorted(self.chats_dir.glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out

    def delete_chat(self, chat_id: str) -> None:
        p = self.chats_dir / (chat_id + ".json")
        if p.exists():
            p.unlink()

    # ----- status ----- #
    def status(self) -> dict:
        all_items = self.items()
        n_described = sum(1 for i in all_items if i.described)
        return {
            "name": self.name,
            "path": str(self.path),
            "total": len(all_items),
            "described": n_described,
            "undescribed": len(all_items) - n_described,
            "sources": [s.get("path") for s in self.sources],
        }
