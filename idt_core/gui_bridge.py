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

from pathlib import Path
from typing import Optional

from .workspace import Workspace, WorkspaceItem, WorkspaceDescription

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
                            copy_images: bool = True) -> Workspace:
    """
    Build (or update) a .idtw bundle from a GUI ImageWorkspace.to_dict() document.
    Images referenced by each item are copied into the bundle; originals untouched.
    Chat items are written to the bundle's chats/ store.
    """
    ws = Workspace.open(dest)

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
    for key, item in items.items():
        item_type = item.get("item_type", "image")
        if item_type == _CHAT_TYPE or str(key).startswith("chat:"):
            _gui_chat_item_to_bundle(ws, key, item)
            continue
        _gui_image_item_to_bundle(ws, key, item, copy_images)

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
        wi = ws.add_image(src, subfolder=item.get("subfolder"))
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
