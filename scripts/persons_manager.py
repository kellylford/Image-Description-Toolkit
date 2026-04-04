"""
Persons Manager — CRUD operations for the known persons database and image tagging.

Supports both workspace-level persistence (via ImageWorkspace) and per-workflow
export/import so that person tags travel with workflow result directories.

Usage (from Python):
    from persons_manager import add_person, tag_image, get_images_for_person, export_to_workflow

All functions operate on an ImageWorkspace instance; the caller is responsible
for saving the workspace after making changes.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import path resolution: supports both frozen exe and dev mode
# ---------------------------------------------------------------------------
try:
    from data_models import ImageWorkspace, PersonRecord, PersonGroup
except ImportError:
    # Dev mode: data_models is in imagedescriber/
    _project_root = Path(__file__).parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    _imagedescriber_path = _project_root / "imagedescriber"
    if str(_imagedescriber_path) not in sys.path:
        sys.path.insert(0, str(_imagedescriber_path))
    from data_models import ImageWorkspace, PersonRecord, PersonGroup

PERSONS_EXPORT_FILENAME = "persons_export.json"


# ---------------------------------------------------------------------------
# Known Persons CRUD
# ---------------------------------------------------------------------------

def add_person(workspace: ImageWorkspace, name: str,
               description_traits: str = "", notes: str = "") -> PersonRecord:
    """Add a new known person to the workspace persons database.

    Args:
        workspace: The active ImageWorkspace.
        name: Display name for the person (e.g. "Alice Smith").
        description_traits: Free-text physical description for AI matching
                            (e.g. "tall woman, auburn hair, glasses").
        notes: Optional miscellaneous notes.

    Returns:
        The newly created PersonRecord.
    """
    record = PersonRecord(name=name, description_traits=description_traits, notes=notes)
    workspace.persons[record.id] = record
    workspace.mark_modified()
    logger.info("Added person '%s' (id=%s)", name, record.id)
    return record


def update_person(workspace: ImageWorkspace, person_id: str,
                  name: Optional[str] = None,
                  description_traits: Optional[str] = None,
                  notes: Optional[str] = None) -> bool:
    """Update fields on an existing PersonRecord.

    Returns True if the record was found and updated, False otherwise.
    """
    record = workspace.persons.get(person_id)
    if record is None:
        logger.warning("update_person: person_id '%s' not found", person_id)
        return False
    if name is not None:
        record.name = name
    if description_traits is not None:
        record.description_traits = description_traits
    if notes is not None:
        record.notes = notes
    workspace.mark_modified()
    return True


def remove_person(workspace: ImageWorkspace, person_id: str) -> bool:
    """Remove a person record and all their tags from images.

    Returns True if the record existed and was removed.
    """
    if person_id not in workspace.persons:
        return False

    # Untag all images
    for item in workspace.items.values():
        if person_id in item.person_tags:
            item.person_tags.remove(person_id)

    del workspace.persons[person_id]
    workspace.mark_modified()
    logger.info("Removed person id=%s", person_id)
    return True


def find_person_by_name(workspace: ImageWorkspace, name: str) -> Optional[PersonRecord]:
    """Look up a person by exact name (case-insensitive). Returns first match or None."""
    name_lower = name.strip().lower()
    for record in workspace.persons.values():
        if record.name.strip().lower() == name_lower:
            return record
    return None


def get_or_create_person(workspace: ImageWorkspace, name: str,
                         description_traits: str = "", notes: str = "") -> PersonRecord:
    """Return an existing PersonRecord by name, or create one if not found."""
    existing = find_person_by_name(workspace, name)
    if existing:
        return existing
    return add_person(workspace, name, description_traits, notes)


# ---------------------------------------------------------------------------
# Image Tagging
# ---------------------------------------------------------------------------

def tag_image(workspace: ImageWorkspace, file_path: str,
              person_id_or_name: str) -> Optional[PersonRecord]:
    """Tag an image with a known person.

    Accepts either a PersonRecord.id (UUID string) or a person's display name.
    If a name is given and no matching record exists, a new record is created.

    Returns the PersonRecord that was applied, or None if the image was not
    found in the workspace.
    """
    item = workspace.items.get(file_path)
    if item is None:
        logger.warning("tag_image: file_path '%s' not in workspace", file_path)
        return None

    # Resolve to a PersonRecord
    if person_id_or_name in workspace.persons:
        record = workspace.persons[person_id_or_name]
    else:
        record = get_or_create_person(workspace, person_id_or_name)

    if record.id not in item.person_tags:
        item.person_tags.append(record.id)
        workspace.mark_modified()

    if file_path not in record.tagged_images:
        record.tagged_images.append(file_path)
        workspace.mark_modified()

    return record


def untag_image(workspace: ImageWorkspace, file_path: str, person_id: str) -> bool:
    """Remove a person tag from an image.

    Returns True if the tag was present and removed.
    """
    item = workspace.items.get(file_path)
    if item is None or person_id not in item.person_tags:
        return False

    item.person_tags.remove(person_id)
    workspace.mark_modified()

    record = workspace.persons.get(person_id)
    if record and file_path in record.tagged_images:
        record.tagged_images.remove(file_path)
    return True


def get_images_for_person(workspace: ImageWorkspace, person_id: str) -> List[str]:
    """Return all file paths tagged with the given person_id."""
    record = workspace.persons.get(person_id)
    if record is None:
        return []
    # Return the canonical list from the record, filtering to paths still in workspace
    return [p for p in record.tagged_images if p in workspace.items]


def get_persons_for_image(workspace: ImageWorkspace, file_path: str) -> List[PersonRecord]:
    """Return all PersonRecords tagged on a given image."""
    item = workspace.items.get(file_path)
    if item is None:
        return []
    return [workspace.persons[pid] for pid in item.person_tags if pid in workspace.persons]


def get_persons_display(workspace: ImageWorkspace, file_path: str) -> str:
    """Return a comma-separated string of person names tagged on an image, or '' if none."""
    persons = get_persons_for_image(workspace, file_path)
    return ", ".join(p.name for p in persons)


# ---------------------------------------------------------------------------
# Person Groups
# ---------------------------------------------------------------------------

def create_group(workspace: ImageWorkspace, display_label: str,
                 images: List[str], description_summary: str = "",
                 method: str = "manual") -> PersonGroup:
    """Create a new PersonGroup in the workspace."""
    group = PersonGroup(
        display_label=display_label,
        description_summary=description_summary,
        method=method,
    )
    group.images = [p for p in images if p in workspace.items]
    workspace.person_groups[group.id] = group

    # Set group_id on each image
    for path in group.images:
        item = workspace.items.get(path)
        if item:
            item.person_group_id = group.id
    workspace.mark_modified()
    return group


def resolve_group_to_person(workspace: ImageWorkspace, group_id: str,
                             person_id_or_name: str) -> bool:
    """Link a PersonGroup to a known PersonRecord and tag all group images.

    Returns True on success.
    """
    group = workspace.person_groups.get(group_id)
    if group is None:
        return False

    if person_id_or_name in workspace.persons:
        record = workspace.persons[person_id_or_name]
    else:
        record = get_or_create_person(workspace, person_id_or_name)

    group.resolved_person_id = record.id
    group.display_label = record.name

    for path in group.images:
        tag_image(workspace, path, record.id)

    workspace.mark_modified()
    return True


def remove_group(workspace: ImageWorkspace, group_id: str) -> bool:
    """Remove a PersonGroup and clear group_id from images. Does not remove person tags."""
    group = workspace.person_groups.get(group_id)
    if group is None:
        return False

    for path in group.images:
        item = workspace.items.get(path)
        if item and item.person_group_id == group_id:
            item.person_group_id = None

    del workspace.person_groups[group_id]
    workspace.mark_modified()
    return True


# ---------------------------------------------------------------------------
# Export / Import (per-workflow)
# ---------------------------------------------------------------------------

def export_to_workflow(workspace: ImageWorkspace, workflow_dir: str) -> Path:
    """Export person tags relevant to a workflow directory to persons_export.json.

    Only images that live inside workflow_dir (or its descriptions/ subdirectory)
    are included. The export also includes the full persons and person_groups
    databases so the file is self-contained.

    Returns the Path to the written file.
    """
    wf_path = Path(workflow_dir)
    descriptions_dir = wf_path / "descriptions"
    descriptions_dir.mkdir(parents=True, exist_ok=True)
    export_path = descriptions_dir / PERSONS_EXPORT_FILENAME

    # Collect images relevant to this workflow
    image_data = {}
    for file_path, item in workspace.items.items():
        if item.person_tags or item.person_group_id:
            fp = Path(file_path)
            # Include if the file is inside the workflow dir
            try:
                fp.relative_to(wf_path)
                relevant = True
            except ValueError:
                relevant = False
            if relevant:
                image_data[fp.name] = {
                    "file_path": file_path,
                    "person_tags": item.person_tags,
                    "person_group_id": item.person_group_id,
                    "person_names": [
                        workspace.persons[pid].name
                        for pid in item.person_tags
                        if pid in workspace.persons
                    ],
                }

    export = {
        "workflow": wf_path.name,
        "exported": datetime.now().isoformat(),
        "images": image_data,
        "persons": {pid: p.to_dict() for pid, p in workspace.persons.items()},
        "person_groups": {gid: g.to_dict() for gid, g in workspace.person_groups.items()},
    }

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)

    logger.info("Exported person data to %s", export_path)
    return export_path


def import_from_workflow(workspace: ImageWorkspace, workflow_dir: str) -> Tuple[int, int]:
    """Import person tags from a workflow's persons_export.json back into the workspace.

    Merges persons and groups (no duplicates by id). Re-applies image tags.

    Returns:
        (persons_imported, images_tagged) counts.
    """
    export_path = Path(workflow_dir) / "descriptions" / PERSONS_EXPORT_FILENAME
    if not export_path.exists():
        logger.warning("import_from_workflow: no export file at %s", export_path)
        return 0, 0

    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    persons_imported = 0
    for pid, pdata in data.get("persons", {}).items():
        if pid not in workspace.persons:
            workspace.persons[pid] = PersonRecord.from_dict(pdata)
            persons_imported += 1

    for gid, gdata in data.get("person_groups", {}).items():
        if gid not in workspace.person_groups:
            workspace.person_groups[gid] = PersonGroup.from_dict(gdata)

    images_tagged = 0
    for filename, idata in data.get("images", {}).items():
        file_path = idata.get("file_path", "")
        item = workspace.items.get(file_path)
        if item is None:
            continue
        for pid in idata.get("person_tags", []):
            if pid not in item.person_tags:
                item.person_tags.append(pid)
                images_tagged += 1
        if idata.get("person_group_id"):
            item.person_group_id = idata["person_group_id"]

    workspace.mark_modified()
    logger.info("Imported %d persons, tagged %d images from %s",
                persons_imported, images_tagged, export_path)
    return persons_imported, images_tagged


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def build_report_lines(workspace: ImageWorkspace, workflow_dir: Optional[str] = None) -> List[str]:
    """Build a human-readable report of all person data.

    If workflow_dir is given, only images inside that directory are included.
    """
    lines: List[str] = []
    lines.append(f"Person Identification Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    if not workspace.persons and not workspace.person_groups:
        lines.append("No person data found in this workspace.")
        return lines

    # Known persons section
    if workspace.persons:
        lines.append(f"\nKnown Persons ({len(workspace.persons)}):")
        lines.append("-" * 40)
        for record in sorted(workspace.persons.values(), key=lambda r: r.name.lower()):
            images = get_images_for_person(workspace, record.id)
            if workflow_dir:
                wf_path = Path(workflow_dir)
                images = [p for p in images if _is_inside(Path(p), wf_path)]
            lines.append(f"  {record.name}")
            if record.description_traits:
                lines.append(f"    Traits: {record.description_traits}")
            lines.append(f"    Images: {len(images)}")
            for img in images:
                lines.append(f"      - {Path(img).name}")

    # Unresolved groups section
    unresolved = [g for g in workspace.person_groups.values() if g.resolved_person_id is None]
    if unresolved:
        lines.append(f"\nUnresolved Groups ({len(unresolved)}):")
        lines.append("-" * 40)
        for group in unresolved:
            imgs = group.images
            if workflow_dir:
                wf_path = Path(workflow_dir)
                imgs = [p for p in imgs if _is_inside(Path(p), wf_path)]
            lines.append(f"  {group.display_label} [{group.method}] — {len(imgs)} images")
            if group.description_summary:
                lines.append(f"    Summary: {group.description_summary}")
            for img in imgs:
                lines.append(f"      - {Path(img).name}")

    return lines


def _is_inside(path: Path, parent: Path) -> bool:
    """Return True if path is inside parent directory."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
