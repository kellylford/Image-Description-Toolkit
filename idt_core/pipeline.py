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

import re
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

# Label for the EXIF context line prepended to describe prompts.
#
# A bare "Context:" gave the model no way to tell capture metadata from scene
# content — with the camera in that line, a Ray-Ban Meta capture was described
# as a photo *of* Ray-Ban glasses. The camera is gone from prompt_context() now,
# but the label still states plainly that this is not visible in the image, so
# a place name is used to ground the description rather than described as if
# printed on it. Shared by the CLI pipeline and the GUI worker so the two
# cannot drift.
META_PREFIX = "Capture metadata (not visible in the image): "


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
            if meta_context:
                prompt = f"{META_PREFIX}{meta_context}\n\n{prompt}"

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
        prompt = f"{META_PREFIX}{meta_context}\n\n{prompt_text}"
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
    #: For a failure, what the run's stop rules need to know about it (see _failure_event).
    #: Not the exception itself: its traceback would keep the image's bytes alive.
    signature: Optional[str] = None
    per_image: bool = False
    setup: bool = False

    @property
    def success(self) -> bool:
        return self.error is None


#: Consecutive images failing with the identical error that stop a run: a provider that has
#: stopped working fails every remaining image the same way (Ollama not running, a used-up
#: plan, a stuck Windows AI that timed out on picture after picture, three minutes each, with
#: 10,700 still to go, 10/7/2026). Large enough that a few bad files in a row don't trip it.
#: ImageDescriber's batches use the same rules (imagedescriber/workers_wx.py).
SAME_FAILURE_STREAK = 10

#: Consecutive images the provider declined (per-image refusals, which neither count toward
#: nor break the identical-failure streak). A few dozen similar photos can each be refused;
#: this many in a row is the prompt itself being refused on every image (#352).
REFUSAL_STREAK = 25

_HEX_ADDRESS = re.compile(r"\b0x[0-9a-fA-F]+\b")
#: Per-request identifiers that API error bodies embed (Anthropic puts
#: 'request_id': 'req_…' in str(exc)); with them, no two failures matched.
#: A bare req_ only when id-length, so a file called req_0001.jpg in a
#: "file not found" message stays distinct; "request ID" in any spelling.
_REQUEST_ID = re.compile(
    r"\breq_[A-Za-z0-9]{16,}|"
    r"""(request[\s_-]?id['"]?\s*[:=]?\s*['"]?)[A-Za-z0-9_-]{6,}""",
    re.IGNORECASE)


def normalise_failure_text(text: str) -> str:
    """An error message without the object addresses and request IDs that would make two
    identical failures look different."""
    text = _HEX_ADDRESS.sub("0x", text)
    return _REQUEST_ID.sub(lambda m: (m.group(1) or "") + "<id>", text)


def failure_source(path, parent_video: Optional[str] = None) -> str:
    """What a failure counts against for the identical-failure stop: the video, for a
    frame extracted from one; otherwise the picture itself.

    Frames of one video look alike, and a provider can fail on all of them: Windows AI
    failed with InternalError at every size on every frame of one iPhone screen
    recording while describing the frames on either side (10/8/2026). Counted as ten
    failures, that one video stopped the run, and stopped it again at the same place
    on every run after. A frame's video comes from ``parent_video`` when the caller
    knows it, else from where frames are kept: each video's own folder under the
    workspace's derived/frames.
    """
    if parent_video:
        return str(parent_video)
    p = Path(path)
    lowered = [part.lower() for part in p.parts]
    for i in range(len(lowered) - 1):
        if lowered[i] == "derived" and lowered[i + 1] == "frames":
            return str(p.parent)
    return str(p)


def _chain_says(exc: Optional[BaseException], attribute: str) -> bool:
    """True if `exc`, or anything it was raised from, has `attribute` set to True."""
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if getattr(exc, attribute, False) is True:
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def is_per_image_failure(exc: BaseException) -> bool:
    """True if the provider declined this one image (``per_image``) rather than failed."""
    return _chain_says(exc, "per_image")


def is_setup_failure(exc: BaseException) -> bool:
    """True if nothing will work until the user changes something (``setup``: the Windows AI
    helper isn't installed, Apple Intelligence isn't licensed), so a run stops at once."""
    return _chain_says(exc, "setup")


def _failure_event(item: WorkspaceItem, index: int, total: int, exc: BaseException) -> WorkspaceEvent:
    return WorkspaceEvent(
        item=item, index=index, total=total, error=str(exc),
        signature=f"{type(exc).__name__}: {normalise_failure_text(str(exc))}",
        per_image=is_per_image_failure(exc), setup=is_setup_failure(exc),
    )


class WorkspacePipeline:
    """Describe the images inside a `.idtw` bundle. Reads the bundle's image copies."""

    def __init__(self, workspace: Workspace, provider: BaseProvider):
        self.workspace = workspace
        self.provider = provider
        self._extractor: Optional[MetadataExtractor] = None
        self._geocoder: Optional[NominatimGeocoder] = None
        #: Why the last run stopped before its last image (None if it didn't), whether that was
        #: for refusals, and how many images it didn't try.
        self.halted: Optional[str] = None
        self.halted_by_refusals = False
        self.not_tried = 0

    def run(self, options: RunOptions) -> Iterator[WorkspaceEvent]:
        all_items = self.workspace.media_items()
        # Skip items whose image is missing on disk (e.g. a moved/deleted reference
        # original). Mark them so the state is durable, and never queue them — this
        # is the single place that decides what gets processed.
        live_items = []
        for i in all_items:
            if not self.workspace.image_path(i).exists():
                if not i.is_missing:
                    i.is_missing = True
                    self.workspace.save_item(i)
                continue
            live_items.append(i)
        queue = live_items if options.redescribe else [i for i in live_items if not i.described]
        if options.limit is not None:
            queue = queue[: options.limit]

        yield from self._run_queue(queue, options)

    def run_items(self, items: list[WorkspaceItem], options: RunOptions) -> Iterator[WorkspaceEvent]:
        """
        Process an explicit list of items (e.g. a batch just downloaded via
        `idt download`) instead of deriving the queue from the whole workspace.
        `options.redescribe` still controls whether already-described items among
        *items* are skipped, but the rest of the workspace is never touched — this
        is what lets a freshly downloaded, alt-text-seeded batch get an AI
        description without reprocessing every previously-described image in a
        shared workspace.
        """
        queue = list(items) if options.redescribe else [i for i in items if not i.described]
        if options.limit is not None:
            queue = queue[: options.limit]

        yield from self._run_queue(queue, options)

    def _run_queue(self, queue: list[WorkspaceItem], options: RunOptions) -> Iterator[WorkspaceEvent]:
        from .logger import open_run_log, close_run_log

        if options.extract_metadata:
            self._extractor = MetadataExtractor()
            if options.geocode:
                cache = options.geocode_cache or (Path.home() / ".idt" / "geocode_cache.json")
                self._geocoder = NominatimGeocoder(cache_path=cache)

        total = len(queue)
        log = open_run_log(self.workspace.logs_dir)
        log.info(
            f"provider={self.provider.provider_name}  model={self.provider.model_name}"
            f"  prompt={options.prompt_name}  images={total}"
        )
        t0 = time.monotonic()
        described = errors = 0
        self.halted = None
        self.halted_by_refusals = False
        self.not_tried = 0
        # The identical failures in a row, by what each counts against (failure_source).
        last_signature, failed_sources, refusals = None, set(), 0

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

                if event.success:
                    last_signature, failed_sources, refusals = None, set(), 0
                elif event.per_image:
                    refusals += 1
                else:
                    if event.signature != last_signature:
                        failed_sources = set()
                    failed_sources.add(failure_source(item.source_path or item.image, item.parent_video))
                    last_signature, refusals = event.signature, 0
                if index < total:
                    if event.setup:
                        self.halted = event.error
                    elif len(failed_sources) >= SAME_FAILURE_STREAK:
                        self.halted = (f"{len(failed_sources)} pictures or videos in a row failed "
                                       f"with the same error: {event.error}")
                    elif refusals >= REFUSAL_STREAK:
                        self.halted_by_refusals = True
                        self.halted = (f"{self.provider.provider_name} declined {refusals} images in "
                                       "a row, which usually means it is declining the prompt itself.")
                if self.halted:
                    self.not_tried = total - index
                    log.warning(f"run halted after {index} of {total} images: {self.halted}")
                    break

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
            return _failure_event(item, index, total, exc)
