"""
gui_bridge — convert between the ImageDescriber GUI workspace document and a
unified `.idtw` bundle.

The GUI's in-memory model (imagedescriber/data_models.py) serializes to a single
dict via ImageWorkspace.to_dict(); historically that dict was written to a `.idw`
file. These functions map that dict to and from a Workspace bundle so the GUI can
open and save the same bundles the CLI produces.

Goals:
  - Lossless round-trip: GUI fields with no place in the core schema are stashed
    in per-item / per-description `extra` dicts and restored exactly.
  - Originals untouched: images are COPIED into the bundle.
  - Chat items (file_path "chat:<id>") map to the bundle's chats/ store.

These are pure functions — no wx — so they are unit-testable headlessly.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .workspace import Workspace, WorkspaceItem, WorkspaceDescription

logger = logging.getLogger(__name__)

# GUI item_type marker for chat sessions
_CHAT_TYPE = "chat"

# Core description fields owned by WorkspaceDescription; everything else in a GUI
# description dict is preserved in description.extra.
_DESC_CORE_GUI_KEYS = {
    "id", "text", "model", "prompt_style", "created", "custom_prompt",
    "provider", "detection_data", "finish_reason", "response_id",
}
# Core item fields owned by WorkspaceItem; everything else goes to item.extra.
_ITEM_CORE_GUI_KEYS = {
    "file_path", "item_type", "descriptions", "subfolder", "parent_video",
    "video_metadata", "download_url", "download_timestamp", "alt_text",
    "exif_datetime", "file_mtime", "is_missing",
}


# --------------------------------------------------------------------------- #
# GUI description <-> WorkspaceDescription                                      #
# --------------------------------------------------------------------------- #

def _gui_desc_to_ws(d: dict) -> WorkspaceDescription:
    token_usage = d.get("token_usage") or {}
    input_tokens = token_usage.get("prompt_tokens")
    output_tokens = token_usage.get("completion_tokens")
    if output_tokens is None:
        output_tokens = d.get("completion_tokens") or None

    metadata = d.get("metadata") or {}
    metadata_context = metadata.get("prompt_context")

    # Everything GUI-specific not represented above is preserved verbatim.
    extra = {k: v for k, v in d.items() if k not in _DESC_CORE_GUI_KEYS}
    # token_usage/completion_tokens/metadata are restored explicitly below, so
    # keep them in extra to guarantee an exact round-trip.

    return WorkspaceDescription(
        id=d.get("id") or "",
        text=d.get("text", ""),
        provider=d.get("provider", ""),
        model=d.get("model", ""),
        prompt_name=d.get("prompt_style", ""),
        prompt_text=d.get("custom_prompt", ""),
        created=d.get("created", ""),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        metadata_context=metadata_context,
        detection_data=d.get("detection_data", []),
        finish_reason=d.get("finish_reason", ""),
        response_id=d.get("response_id", ""),
        extra=extra,
    )


def _ws_desc_to_gui(w: WorkspaceDescription) -> dict:
    out = {
        "id": w.id,
        "text": w.text,
        "model": w.model,
        "prompt_style": w.prompt_name,
        "created": w.created,
        "custom_prompt": w.prompt_text,
        "provider": w.provider,
        "detection_data": w.detection_data,
        "metadata": {},
        "finish_reason": w.finish_reason,
        "response_id": w.response_id,
    }
    # Restore GUI-only fields stashed in extra (metadata, token_usage,
    # completion_tokens, etc.).
    out.update(w.extra)
    # Make sure prompt_context lands back in metadata if that's where it came from
    if w.metadata_context and "prompt_context" not in out.get("metadata", {}):
        out.setdefault("metadata", {})
        out["metadata"]["prompt_context"] = w.metadata_context
    # If extra didn't carry token_usage but we have token counts, synthesize it
    if "token_usage" not in out and (w.input_tokens or w.output_tokens):
        out["token_usage"] = {
            "prompt_tokens": w.input_tokens or 0,
            "completion_tokens": w.output_tokens or 0,
            "total_tokens": (w.input_tokens or 0) + (w.output_tokens or 0),
        }
    return out


# --------------------------------------------------------------------------- #
# GUI workspace dict  ->  bundle                                                #
# --------------------------------------------------------------------------- #

def gui_workspace_to_bundle(workspace_dict: dict, dest: Path,
                            copy_images: bool = True,
                            progress: Optional[Callable[[int, int, str], None]] = None) -> Workspace:
    """
    Build (or update) a .idtw bundle from a GUI ImageWorkspace.to_dict() document.
    Images referenced by each item are copied into the bundle; originals untouched.
    Chat items are written to the bundle's chats/ store.

    Args:
        progress: Optional callback invoked as progress(done, total, name) after
            each item is written.  Lets the GUI drive a progress dialog through
            what is otherwise a long silent loop.  Never called with total == 0.
    """
    ws = Workspace.open(dest)

    # Record this bundle's copy character so it round-trips and matches the CLI.
    ws.copy_originals = bool(copy_images)

    # Top-level manifest mapping
    dir_paths = workspace_dict.get("directory_paths") or []
    scan_recursive = workspace_dict.get("directory_scan_recursive") or {}
    ws.sources = [
        {"path": p, "recursive": bool(scan_recursive.get(p, True))}
        for p in dir_paths
    ]
    ws.batch_state = workspace_dict.get("batch_state")
    ws.cached_ollama_models = workspace_dict.get("cached_ollama_models")
    ws.save_manifest()

    items = workspace_dict.get("items") or {}
    total = len(items)
    for done, (key, item) in enumerate(items.items(), start=1):
        item_type = item.get("item_type", "image")
        if item_type == _CHAT_TYPE or str(key).startswith("chat:"):
            _gui_chat_item_to_bundle(ws, key, item)
        else:
            _gui_image_item_to_bundle(ws, key, item, copy_images)
        if progress:
            progress(done, total, Path(str(key)).name)

    return ws


def _gui_image_item_to_bundle(ws: Workspace, file_path: str, item: dict,
                              copy_images: bool) -> None:
    src = Path(file_path)

    # If the image is already inside this bundle's images/ directory, update the
    # existing sidecar in-place so we preserve the original source_path and storage
    # type that the CLI recorded (avoids overwriting provenance on re-save).
    try:
        src.relative_to(ws.images_dir)
        existing = ws.get_item(src.name)
        if existing is not None:
            existing.is_missing = item.get("is_missing", False)
            existing.descriptions = [_gui_desc_to_ws(d) for d in item.get("descriptions", [])]
            if existing.descriptions:
                existing.active_description_id = existing.descriptions[-1].id
            existing.extra.update({k: v for k, v in item.items() if k not in _ITEM_CORE_GUI_KEYS})
            ws.save_item(existing)
            return
    except ValueError:
        pass  # src is not inside this bundle's images/ dir — proceed normally

    is_missing = item.get("is_missing", False) or not src.exists()

    if copy_images and src.exists():
        wi = ws.add_image(src, subfolder=item.get("subfolder"), copy=True)
    elif src.exists():
        # Reference mode: record source path in a sidecar, don't copy the file.
        wi = WorkspaceItem(
            image=src.name,
            source_path=str(src),
            storage="reference",
            subfolder=item.get("subfolder"),
        )
    else:
        # File not on disk: register a missing sidecar.
        wi = WorkspaceItem(
            image=src.name,
            source_path=str(src),
            subfolder=item.get("subfolder"),
        )

    wi.item_type = item.get("item_type", "image")
    wi.parent_video = item.get("parent_video")
    wi.video_metadata = item.get("video_metadata")
    wi.download_url = item.get("download_url")
    wi.download_timestamp = item.get("download_timestamp")
    wi.alt_text = item.get("alt_text")
    wi.exif_datetime = item.get("exif_datetime")
    wi.file_mtime = item.get("file_mtime")
    wi.is_missing = is_missing
    wi.descriptions = [_gui_desc_to_ws(d) for d in item.get("descriptions", [])]
    if wi.descriptions:
        wi.active_description_id = wi.descriptions[-1].id
    # Preserve GUI-only item fields (batch state, extracted_frames, display_name…)
    wi.extra = {k: v for k, v in item.items() if k not in _ITEM_CORE_GUI_KEYS}
    ws.save_item(wi)


def _gui_chat_item_to_bundle(ws: Workspace, key: str, item: dict) -> None:
    chat_id = key.split("chat:", 1)[-1] if str(key).startswith("chat:") else key
    messages = [_ws_desc_to_gui(_gui_desc_to_ws(d)) for d in item.get("descriptions", [])]
    provider = model = ""
    if item.get("descriptions"):
        provider = item["descriptions"][0].get("provider", "")
        model = item["descriptions"][0].get("model", "")
    ws.save_chat({
        "id": chat_id,
        "name": item.get("display_name", "Chat"),
        "image": None,
        "provider": provider,
        "model": model,
        "messages": messages,
        "extra": {k: v for k, v in item.items() if k not in _ITEM_CORE_GUI_KEYS},
    })


# --------------------------------------------------------------------------- #
# bundle  ->  GUI workspace dict                                                #
# --------------------------------------------------------------------------- #

def bundle_to_gui_workspace_dict(ws: Workspace) -> dict:
    """
    Build a GUI ImageWorkspace.to_dict()-shaped document from a bundle so the GUI
    can load it. Item file paths point at the bundle's image copies so the GUI
    displays the workspace's own images.
    """
    items: dict = {}

    for wi in ws.items():
        # For reference-mode items, point the GUI at the original file so it
        # can display the image without requiring a copy inside the bundle.
        gui_path = str(ws.image_path(wi))
        gui_item = {
            "file_path": gui_path,
            "item_type": wi.item_type,
            "descriptions": [_ws_desc_to_gui(d) for d in wi.descriptions],
            "subfolder": wi.subfolder,
            "parent_video": wi.parent_video,
            "video_metadata": wi.video_metadata,
            "download_url": wi.download_url,
            "download_timestamp": wi.download_timestamp,
            "alt_text": wi.alt_text,
            "exif_datetime": wi.exif_datetime,
            "file_mtime": wi.file_mtime,
            "is_missing": wi.is_missing,
        }
        gui_item.update(wi.extra)  # restore batch state, extracted_frames, etc.
        items[gui_path] = gui_item

    # Chats become chat items keyed "chat:<id>"
    for chat in ws.chats():
        cid = chat.get("id", "")
        key = f"chat:{cid}"
        descs = []
        for m in chat.get("messages", []):
            # messages are already GUI-shaped description dicts
            descs.append(m)
        chat_item = {
            "file_path": key,
            "item_type": _CHAT_TYPE,
            "display_name": chat.get("name", "Chat"),
            "descriptions": descs,
        }
        chat_item.update(chat.get("extra", {}))
        items[key] = chat_item

    # Reconstruct video→frame links for bundles created before the CLI recorded
    # parent_video / item_type="extracted_frame" in each sidecar.
    _reconstruct_video_frame_links(ws, items)

    return {
        "version": "3.0",
        "directory_path": ws.sources[0]["path"] if ws.sources else "",
        "directory_paths": [s["path"] for s in ws.sources],
        "directory_scan_recursive": {s["path"]: s.get("recursive", True) for s in ws.sources},
        "items": items,
        "chat_sessions": {},
        "imported_workflow_dir": None,
        "cached_ollama_models": ws.cached_ollama_models,
        "batch_state": ws.batch_state,
        "created": ws.created,
        "modified": ws.modified,
    }


def _reconstruct_video_frame_links(ws: Workspace, items: dict) -> None:
    """
    Detect extracted frames stored as item_type="image" with subfolder="frames/<Stem>"
    and no parent_video — produced by older CLI runs — and synthesize the proper
    video→frame relationship so the GUI tree can nest them correctly.

    For each unique video stem found, if no video item already exists, a placeholder
    video entry is inserted (is_missing=True, no image copy in the bundle).
    The frame items are updated to item_type="extracted_frame" with parent_video set.
    """
    import re
    _frame_sub = re.compile(r'^frames/(.+)$')

    # Collect unlinked frames grouped by video stem.
    unlinked: dict = {}  # stem -> [gui_path, ...]
    for gui_path, item in items.items():
        if (item.get("item_type", "image") == "image"
                and item.get("parent_video") is None
                and item.get("subfolder")):
            m = _frame_sub.match(item["subfolder"])
            if m:
                stem = m.group(1)
                unlinked.setdefault(stem, []).append(gui_path)

    if not unlinked:
        return

    for stem, frame_paths in unlinked.items():
        # Look for a video item already present (added by CLI after the fix).
        video_key = next(
            (k for k, v in items.items()
             if v.get("item_type") == "video" and Path(k).stem == stem),
            None,
        )
        if video_key is None:
            # Synthesize a placeholder video node.  Use the would-be bundle path as
            # a stable, unique key; is_missing=True since no file was copied.
            video_key = str(ws.images_dir / stem)
            items[video_key] = {
                "file_path": video_key,
                "item_type": "video",
                "descriptions": [],
                "subfolder": None,
                "parent_video": None,
                "video_metadata": None,
                "download_url": None,
                "download_timestamp": None,
                "alt_text": None,
                "exif_datetime": None,
                "file_mtime": None,
                "is_missing": True,
                "extracted_frames": sorted(frame_paths),
            }
        elif not items[video_key].get("extracted_frames"):
            items[video_key]["extracted_frames"] = sorted(frame_paths)

        for fp in frame_paths:
            items[fp]["item_type"] = "extracted_frame"
            items[fp]["parent_video"] = video_key


# --------------------------------------------------------------------------- #
# Writing one GUI item into an open bundle                                     #
# --------------------------------------------------------------------------- #

def _same_file(a, b) -> bool:
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def _find_ws_item(ws: Workspace, p: Path, subfolder: Optional[str]) -> Optional[WorkspaceItem]:
    """The bundle's sidecar for the GUI item at ``p``, or None if it has none yet.

    The sidecar at the item's own (subfolder, name) is taken as is. Failing
    that, the descriptions/ tree is searched by name, but a match is accepted
    only if it is the same image: two folders can each hold an ``IMG_0001.jpg``,
    and taking the first name match wrote one image's description into the
    other's sidecar, replacing its description.
    """
    direct = ws._sidecar_path(p.name, subfolder)
    if direct.exists():
        return ws.get_item(p.name, subfolder)
    if not ws.descriptions_dir.is_dir():
        return None
    for sidecar in ws.descriptions_dir.glob(f"**/{p.name}.json"):
        try:
            wi = WorkspaceItem.from_dict(json.loads(sidecar.read_text(encoding="utf-8")))
        except Exception:
            continue
        if _same_file(ws.image_path(wi), p) or (
                wi.source_path and _same_file(wi.source_path, p)):
            return wi
    return None


def gui_item_to_ws_item(ws: Workspace, file_path: str, gui_item: dict) -> WorkspaceItem:
    """Merge one GUI item dict into the bundle's sidecar for it (not yet saved).

    Updates the existing sidecar's descriptions and GUI extras when the bundle
    already holds the image, otherwise builds a reference item. The caller
    writes the result with ``ws.save_item``.
    """
    p = Path(file_path)
    subfolder = gui_item.get("subfolder")
    existing = _find_ws_item(ws, p, subfolder)
    extra = {k: v for k, v in gui_item.items() if k not in _ITEM_CORE_GUI_KEYS}
    descs = [_gui_desc_to_ws(d) for d in gui_item.get("descriptions", [])]

    if existing is not None:
        existing.item_type = gui_item.get("item_type", existing.item_type)
        existing.parent_video = gui_item.get("parent_video", existing.parent_video)
        if gui_item.get("video_metadata") is not None:
            existing.video_metadata = gui_item["video_metadata"]
        existing.descriptions = descs
        if existing.descriptions:
            existing.active_description_id = existing.descriptions[-1].id
        existing.is_missing = gui_item.get("is_missing", False)
        existing.extra.update(extra)
        return existing

    wi = WorkspaceItem(
        image=p.name,
        source_path=str(p),
        storage="reference",
        subfolder=subfolder,
    )
    wi.item_type = gui_item.get("item_type", "image")
    wi.parent_video = gui_item.get("parent_video")
    wi.video_metadata = gui_item.get("video_metadata")
    wi.download_url = gui_item.get("download_url")
    wi.download_timestamp = gui_item.get("download_timestamp")
    wi.alt_text = gui_item.get("alt_text")
    wi.exif_datetime = gui_item.get("exif_datetime")
    wi.file_mtime = gui_item.get("file_mtime")
    wi.is_missing = gui_item.get("is_missing", False) or not p.exists()
    wi.descriptions = descs
    if wi.descriptions:
        wi.active_description_id = wi.descriptions[-1].id
    wi.extra = extra
    return wi


# --------------------------------------------------------------------------- #
# Saving descriptions as a batch produces them                                 #
# --------------------------------------------------------------------------- #

class BundleCheckpointWriter:
    """Writes each finished item to its bundle while a batch runs.

    A batch used to keep every description in memory until the whole run ended,
    so a crash hours into a 10,000-image run lost all of it. A full save
    rewrites one sidecar per item and takes minutes on a large workspace, far
    too slow to run per image. This writes only the item that just finished,
    on one background thread, and refreshes the manifest (batch_state, which
    resume reads) every ``manifest_every`` items or ``manifest_secs`` seconds.

    Ordering against a full save: every snapshot of GUI state — a checkpoint or
    a full save's ``to_dict()`` — takes a number from ``snapshot_seq()`` on the
    main thread when it is taken. A sidecar is written only when its snapshot
    is newer than the last one written for that item, checked under ``lock``,
    so a slow full save cannot put back an older copy of an item the writer
    has already saved, and the writer cannot overwrite a newer full save.
    """

    def __init__(self, manifest_every: int = 25, manifest_secs: float = 30.0):
        self.lock = threading.Lock()
        self.manifest_every = manifest_every
        self.manifest_secs = manifest_secs
        self._queue: queue.Queue = queue.Queue()
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._written: dict = {}
        self._thread: Optional[threading.Thread] = None
        self._since_manifest = 0
        self._last_manifest = time.monotonic()
        self.items_written = 0
        self.last_error: Optional[str] = None

    # ----- snapshot ordering ----- #
    def snapshot_seq(self) -> int:
        """Number a snapshot of GUI state. Strictly increasing."""
        with self._seq_lock:
            self._seq += 1
            return self._seq

    def claim(self, bundle_path, file_path: str, seq: int) -> bool:
        """Call holding ``lock``: may a snapshot numbered ``seq`` write this item?

        A True answer is recorded, so call it only right before writing.
        """
        key = (str(Path(bundle_path)), str(file_path))
        if seq <= self._written.get(key, 0):
            return False
        self._written[key] = seq
        return True

    # ----- queueing ----- #
    def enqueue_item(self, bundle_path, file_path: str, gui_item: dict,
                     batch_state: Optional[dict], seq: int) -> None:
        """Queue one item. ``gui_item`` and ``batch_state`` must be main-thread copies."""
        self._queue.put((Path(bundle_path), str(file_path), gui_item,
                         batch_state, seq))
        self._ensure_thread()

    def flush(self, timeout: Optional[float] = None) -> bool:
        """Wait until every queued write has finished. False on timeout."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while self._queue.unfinished_tasks:
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.02)
        return True

    def _ensure_thread(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run, name="BundleCheckpointWriter", daemon=True)
            self._thread.start()

    # ----- writer thread ----- #
    def _run(self) -> None:
        while True:
            job = self._queue.get()
            try:
                self._handle(*job)
            except Exception as exc:  # one bad item must not stop the writer
                self.last_error = str(exc)
                logger.error(f"Checkpoint write failed: {exc}", exc_info=True)
            finally:
                self._queue.task_done()

    def _handle(self, bundle_path: Path, file_path, gui_item,
                batch_state, seq) -> None:
        # Never recreate a bundle that was moved or deleted mid-run:
        # Workspace.open() would silently make a fresh empty one.
        if not Workspace.is_bundle(bundle_path):
            return
        with self.lock:
            ws = Workspace(bundle_path)
            if self.claim(bundle_path, file_path, seq):
                ws.save_item(gui_item_to_ws_item(ws, file_path, gui_item))
                self.items_written += 1
            self._since_manifest += 1
            due = (self._since_manifest >= self.manifest_every
                   or time.monotonic() - self._last_manifest >= self.manifest_secs)
            if not due:
                return
            # Re-read so settings a full save just wrote (defaults, models)
            # survive; _save_bundle holds this lock for its manifest write too.
            ws = Workspace.open(bundle_path)
            ws.batch_state = batch_state
            ws.has_any_descriptions = (ws.has_any_descriptions
                                       or bool(gui_item.get("descriptions")))
            ws.save_manifest()
            self._since_manifest = 0
            self._last_manifest = time.monotonic()
