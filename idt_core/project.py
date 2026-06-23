"""
Project — the pairing of a source directory with its .idt/ mirror.

Opening a project on ~/Pictures/Vacation/ creates (if absent) ~/Pictures/Vacation.idt/
and a project.json inside it. The mirror directory structure is created on demand as
images are described; nothing is written until there is something to write.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from .image_item import ImageItem
from .scanner import scan_images


@dataclass
class ProjectConfig:
    """Per-project settings, stored in project.json alongside source/model/prompt history."""
    default_provider: str = "anthropic"
    default_model: str = "claude-opus-4-6"
    default_prompt_name: str = "detailed"
    default_prompt_text: str = ""  # empty means use the built-in text for default_prompt_name


@dataclass
class Project:
    source_dir: Path
    idt_dir: Path
    config: ProjectConfig = field(default_factory=ProjectConfig)
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Open / create                                                        #
    # ------------------------------------------------------------------ #

    @classmethod
    def open(cls, source_dir: Path) -> Project:
        """
        Open an existing project or create a new one.
        source_dir must exist and be a directory.
        The .idt/ mirror is created next to source_dir (not inside it).
        """
        source_dir = source_dir.resolve()
        if not source_dir.is_dir():
            raise NotADirectoryError(f"Source directory does not exist: {source_dir}")

        idt_dir = source_dir.parent / (source_dir.name + ".idt")
        project_file = idt_dir / "project.json"

        if project_file.exists():
            return cls._load(source_dir, idt_dir, project_file)

        idt_dir.mkdir(parents=True, exist_ok=True)
        project = cls(source_dir=source_dir, idt_dir=idt_dir)
        project.save()
        return project

    @classmethod
    def _load(cls, source_dir: Path, idt_dir: Path, project_file: Path) -> Project:
        data = json.loads(project_file.read_text(encoding="utf-8"))
        cfg_data = data.get("config", {})
        config = ProjectConfig(
            default_provider=cfg_data.get("default_provider", "anthropic"),
            default_model=cfg_data.get("default_model", "claude-opus-4-6"),
            default_prompt_name=cfg_data.get("default_prompt_name", "detailed"),
            default_prompt_text=cfg_data.get("default_prompt_text", ""),
        )
        return cls(
            source_dir=source_dir,
            idt_dir=idt_dir,
            config=config,
            created=data.get("created", datetime.now(timezone.utc).isoformat()),
            last_run=data.get("last_run"),
        )

    def save(self) -> None:
        self.idt_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "source": str(self.source_dir),
            "created": self.created,
            "last_run": self.last_run,
            "config": {
                "default_provider": self.config.default_provider,
                "default_model": self.config.default_model,
                "default_prompt_name": self.config.default_prompt_name,
                "default_prompt_text": self.config.default_prompt_text,
            },
        }
        (self.idt_dir / "project.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ------------------------------------------------------------------ #
    # Sidecar path resolution                                              #
    # ------------------------------------------------------------------ #

    def sidecar_path(self, source_path: Path) -> Path:
        """
        Return the .json sidecar path in .idt/ that mirrors a given source file.
        Example: source_dir/Day1/photo.jpg  →  idt_dir/Day1/photo.jpg.json
        """
        rel = source_path.relative_to(self.source_dir)
        return self.idt_dir / (str(rel) + ".json")

    # ------------------------------------------------------------------ #
    # Image iteration                                                      #
    # ------------------------------------------------------------------ #

    def items(self, include_videos: bool = False) -> Iterator[ImageItem]:
        """Yield an ImageItem for every image in the source directory."""
        for img_path in scan_images(self.source_dir, include_videos=include_videos):
            sidecar = self.sidecar_path(img_path)
            if sidecar.exists():
                yield ImageItem.load(sidecar)
            else:
                yield ImageItem(source_path=img_path, sidecar_path=sidecar)

    def undescribed(self, include_videos: bool = False) -> Iterator[ImageItem]:
        for item in self.items(include_videos=include_videos):
            if not item.described:
                yield item

    def described(self, include_videos: bool = False) -> Iterator[ImageItem]:
        for item in self.items(include_videos=include_videos):
            if item.described:
                yield item

    # ------------------------------------------------------------------ #
    # Status                                                               #
    # ------------------------------------------------------------------ #

    def status(self) -> dict:
        all_items = list(self.items())
        n_described = sum(1 for i in all_items if i.described)
        return {
            "total": len(all_items),
            "described": n_described,
            "undescribed": len(all_items) - n_described,
            "source": str(self.source_dir),
            "idt_dir": str(self.idt_dir),
            "last_run": self.last_run,
        }
