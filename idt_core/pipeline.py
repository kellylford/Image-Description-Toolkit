"""
Pipeline — orchestrates scanning, conversion, and description for a project.

Design:
  - Reads source images directly into memory; never copies them to a temp location
  - HEIC → JPEG conversion happens in memory for the API call; if a persistent copy
    is needed (stored in .idt/), it is saved there and tracked in the sidecar
  - Extracts EXIF metadata before the API call; injects context into the prompt
    so the AI knows when/where the photo was taken (dramatic quality improvement)
  - Yields PipelineEvent objects so the caller (CLI or GUI) controls output
  - Stateless: create a new Pipeline per run; the Project holds all state
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from .converter import load_for_api, save_heic_copy
from .image_item import Description, ImageItem
from .metadata import ImageMetadata, MetadataExtractor, NominatimGeocoder
from .project import Project
from .providers.base import BaseProvider
from .scanner import is_heic
from .workspace import Workspace, WorkspaceItem, WorkspaceDescription


@dataclass
class RunOptions:
    prompt_name: str = "detailed"
    prompt_text: str = ""         # if empty, provider uses the project/config default
    redescribe: bool = False      # re-run images that already have descriptions
    limit: Optional[int] = None   # stop after N images (useful for testing)
    extract_metadata: bool = True  # extract EXIF and inject context into prompt
    geocode: bool = False          # reverse-geocode GPS → city/state (requires internet)
    geocode_cache: Optional[Path] = None  # path to geocoding cache JSON


@dataclass
class PipelineEvent:
    item: ImageItem
    index: int                    # 1-based position in this run
    total: int                    # total images in this run
    error: Optional[str] = None
    metadata: Optional[ImageMetadata] = None

    @property
    def success(self) -> bool:
        return self.error is None


class Pipeline:
    def __init__(self, project: Project, provider: BaseProvider):
        self.project = project
        self.provider = provider
        self._extractor: Optional[MetadataExtractor] = None
        self._geocoder: Optional[NominatimGeocoder] = None

    def run(self, options: RunOptions) -> Iterator[PipelineEvent]:
        """
        Yield a PipelineEvent for each image processed.
        Updates the project's last_run timestamp when the run completes.
        """
        # Lazy-init metadata extractor once per run
        if options.extract_metadata:
            self._extractor = MetadataExtractor()
            if options.geocode:
                cache = options.geocode_cache or (
                    Path.home() / ".idt" / "geocode_cache.json"
                )
                self._geocoder = NominatimGeocoder(cache_path=cache)

        queue = list(
            self.project.items() if options.redescribe
            else self.project.undescribed()
        )
        if options.limit is not None:
            queue = queue[: options.limit]

        total = len(queue)
        for index, item in enumerate(queue, start=1):
            yield self._process(item, index, total, options)

        self.project.last_run = datetime.now(timezone.utc).isoformat()
        self.project.save()

    def _process(
        self, item: ImageItem, index: int, total: int, options: RunOptions
    ) -> PipelineEvent:
        try:
            # HEIC: save a JPEG copy in the .idt/ mirror if we don't have one yet
            if is_heic(item.source_path) and item.converted_path is None:
                item.converted_path = save_heic_copy(
                    item.source_path, item.sidecar_path.parent
                )

            # Extract EXIF metadata from the original source file
            meta: Optional[ImageMetadata] = None
            meta_context = ""
            if self._extractor:
                meta = self._extractor.extract(item.source_path)
                if self._geocoder and meta:
                    meta = self._geocoder.enrich(meta)
                if meta:
                    meta_context = meta.prompt_context()
                    item.metadata = meta.to_dict()

            # Build enriched prompt: context line first, then the actual prompt
            prompt = options.prompt_text
            if meta_context and prompt:
                prompt = f"Context: {meta_context}\n\n{prompt}"
            elif meta_context:
                prompt = f"Context: {meta_context}\n\n{prompt}"

            image_bytes, mime_type = load_for_api(item.processable_path)
            result = self.provider.describe(image_bytes, mime_type, prompt)

            desc = Description.create(
                text=result.text,
                model=result.model,
                provider=result.provider,
                prompt_name=options.prompt_name,
                prompt_text=options.prompt_text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                metadata_context=meta_context or None,
            )
            item.add_description(desc)
            item.save()
            return PipelineEvent(item=item, index=index, total=total, metadata=meta)

        except Exception as exc:
            return PipelineEvent(item=item, index=index, total=total, error=str(exc))


# --------------------------------------------------------------------------- #
# Shared per-image describe helper (used by both pipelines)                     #
# --------------------------------------------------------------------------- #

def _extract_and_build_prompt(extractor, geocoder, exif_path, prompt_text):
    """
    Extract EXIF (optionally geocode) and prepend a context line to the prompt.
    Returns (ImageMetadata|None, context_str, enriched_prompt).
    """
    meta: Optional[ImageMetadata] = None
    meta_context = ""
    if extractor:
        meta = extractor.extract(exif_path)
        if geocoder and meta:
            meta = geocoder.enrich(meta)
        if meta:
            meta_context = meta.prompt_context()
    prompt = prompt_text
    if meta_context:
        prompt = f"Context: {meta_context}\n\n{prompt_text}"
    return meta, meta_context, prompt


# --------------------------------------------------------------------------- #
# WorkspacePipeline — same logic, but runs over a unified .idtw bundle          #
# --------------------------------------------------------------------------- #

@dataclass
class WorkspaceEvent:
    item: WorkspaceItem
    index: int
    total: int
    error: Optional[str] = None
    metadata: Optional[ImageMetadata] = None

    @property
    def success(self) -> bool:
        return self.error is None


class WorkspacePipeline:
    """Describe the images inside a `.idtw` bundle. Reads the bundle's image copies."""

    def __init__(self, workspace: Workspace, provider: BaseProvider):
        self.workspace = workspace
        self.provider = provider
        self._extractor: Optional[MetadataExtractor] = None
        self._geocoder: Optional[NominatimGeocoder] = None

    def run(self, options: RunOptions) -> Iterator[WorkspaceEvent]:
        from .logger import open_run_log, close_run_log

        if options.extract_metadata:
            self._extractor = MetadataExtractor()
            if options.geocode:
                cache = options.geocode_cache or (Path.home() / ".idt" / "geocode_cache.json")
                self._geocoder = NominatimGeocoder(cache_path=cache)

        all_items = self.workspace.items()
        queue = all_items if options.redescribe else [i for i in all_items if not i.described]
        if options.limit is not None:
            queue = queue[: options.limit]

        total = len(queue)
        log = open_run_log(self.workspace.logs_dir)
        log.info(
            f"provider={self.provider.provider_name}  model={self.provider.model_name}"
            f"  prompt={options.prompt_name}  images={total}"
        )
        t0 = time.monotonic()
        described = errors = 0

        try:
            for index, item in enumerate(queue, start=1):
                event = self._process(item, index, total, options)
                if event.success:
                    described += 1
                    tokens = ""
                    if item.descriptions:
                        last = item.descriptions[-1]
                        if last.input_tokens or last.output_tokens:
                            tokens = f"  ({last.input_tokens} in, {last.output_tokens} out)"
                    log.info(f"{index}/{total}  {item.image}: described{tokens}")
                else:
                    errors += 1
                    log.error(f"{index}/{total}  {item.image}: ERROR — {event.error}")
                yield event

            elapsed = time.monotonic() - t0
            log.info(f"done  described={described}  errors={errors}  elapsed={elapsed:.1f}s")
            self.workspace.save_manifest()
        except BaseException:
            log.exception("run aborted")
            raise
        finally:
            close_run_log(log)

    def _process(self, item: WorkspaceItem, index: int, total: int,
                 options: RunOptions) -> WorkspaceEvent:
        try:
            bundle_image = self.workspace.image_path(item)
            read_path = bundle_image

            # HEIC: convert into derived/converted (inside the bundle) and read that
            if is_heic(bundle_image):
                if item.converted:
                    read_path = self.workspace.path / item.converted
                else:
                    conv = save_heic_copy(bundle_image, self.workspace.derived_dir("converted"))
                    item.converted = str(conv.relative_to(self.workspace.path))
                    read_path = conv

            # EXIF is read from the bundle copy (copy2 preserved it)
            meta, meta_context, prompt = _extract_and_build_prompt(
                self._extractor, self._geocoder, bundle_image, options.prompt_text
            )
            if meta:
                item.metadata = meta.to_dict()

            image_bytes, mime_type = load_for_api(read_path)
            result = self.provider.describe(image_bytes, mime_type, prompt)

            desc = WorkspaceDescription.create(
                text=result.text,
                provider=result.provider,
                model=result.model,
                prompt_name=options.prompt_name,
                prompt_text=options.prompt_text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                metadata_context=meta_context or None,
            )
            item.add_description(desc)
            self.workspace.save_item(item)
            return WorkspaceEvent(item=item, index=index, total=total, metadata=meta)

        except Exception as exc:
            return WorkspaceEvent(item=item, index=index, total=total, error=str(exc))
