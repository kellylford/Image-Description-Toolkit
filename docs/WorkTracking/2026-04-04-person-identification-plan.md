# Person Identification Plan
**Date:** 2026-04-04  
**Status:** Implementation complete (Phases 1–5)

---

## Problem Statement

IDT excels at describing *what* is in images but cannot identify *who* the people are. Users need a way to tell the system who is in their pictures so that person identities can be preserved across workflow runs, exported to HTML, and queried via CLI.

---

## Approach Overview

Three complementary methods feed the same underlying data model:

| Method | Accuracy | Dependencies | When to use |
|--------|----------|--------------|-------------|
| **Text-mining** (Phase 3) | Low–Medium | None | Quick pass; no GPU needed |
| **AI-assisted** (Phase 4) | Medium–High | Provider API key | Any existing AI subscription |
| **CV face recognition** (Phase 5) | High | facenet-pytorch (~1 GB) | Best for large collections |

---

## Data Model

### New classes in `imagedescriber/data_models.py`

```python
class PersonRecord:
    id: str                             # uuid4
    name: str
    description_traits: str            # physical traits for AI matching
    notes: str
    tagged_images: List[str]           # file_path strings
    face_embedding: Optional[List[float]]  # reserved for Phase 5

class PersonGroup:
    id: str                            # uuid4
    display_label: str
    resolved_person_id: Optional[str]
    images: List[str]
    description_summary: str
    method: str                        # "manual"/"text"/"ai"/"cv"
```

### Extensions to `ImageItem`:
- `person_tags: List[str]`     — PersonRecord.id list
- `person_group_id: Optional[str]`

### Extensions to `ImageWorkspace`:
- `persons: Dict[str, PersonRecord]`
- `person_groups: Dict[str, PersonGroup]`

---

## Storage

| Where | What |
|-------|------|
| `.idtworkspace` (existing) | `persons` + `person_groups` dicts |
| `wf_*/descriptions/persons_export.json` | Per-workflow snapshot for sharing |
| `.idt_faces.db` (new, SQLite) | Face embeddings + DBSCAN clusters |

### `persons_export.json` schema:
```json
{
  "workflow": "wf_2025-01-01_120000_gpt4o_default",
  "exported": "2025-01-01T12:00:00",
  "images": {
    "IMG_001.jpg": {
      "file_path": "/abs/path/IMG_001.jpg",
      "person_tags": ["uuid1", "uuid2"],
      "person_group_id": null,
      "person_names": ["Alice", "Bob"]
    }
  },
  "persons": { ... },
  "person_groups": { ... }
}
```

---

## Phases

### Phase 1 — Prompt ✅
**File:** `scripts/image_describer_config.json`  
Added `people_focused` prompt that instructs the AI to describe each person's age, gender expression, build, hair, clothing, and distinctive features — framed for re-identification by someone who cannot see the image.

### Phase 2 — Core infrastructure ✅

**2a. Data models** (`imagedescriber/data_models.py`)  
`PersonRecord`, `PersonGroup`, `ImageItem.person_tags`, `ImageWorkspace.persons`.

**2b. Persons Manager** (`scripts/persons_manager.py`)  
Full CRUD: add/update/remove persons, tag/untag images, group management, export/import.

**2c. CLI** (`scripts/persons_cli.py` + `idt/idt_cli.py`)  
`idt persons add|tag|untag|list|report|export|import|install-engine`

**2d. GUI** (`imagedescriber/person_dialogs_wx.py`, `imagedescriber_wx.py`)  
- `TagPersonDialog` — assign person to current image
- `PersonDatabaseDialog` — manage known persons DB
- `GroupingResultsDialog` — review auto-grouped clusters
- `MatchResultsDialog` — review AI match suggestions
- `Descriptions → Tag Person in Image`
- `Tools → Manage Known Persons`

**2d. HTML** (`scripts/descriptions_to_html.py`)  
`DescriptionEntry.person_tags` field; rendered as green badge `<p class="person-tags">People identified: Alice, Bob</p>`; loaded from `persons_export.json` during parse.

### Phase 3 — Text-mining clustering ✅
**File:** `scripts/person_identifier.py`

- `extract_person_descriptors(text)` — regex extraction of age/gender/hair/clothing/distinctive features
- `cluster_by_text(images_dict, threshold=0.35)` — greedy Jaccard-similarity clustering (no external dependencies)
- `generate_grouping_report(groups, output_path=None)` — text report

### Phase 4 — AI-assisted clustering ✅
**File:** `scripts/person_identifier.py` (continued)

- `cluster_by_ai(images_dict, provider, model, ...)` — batched LLM grouping
- `match_known_persons_ai(images_dict, workspace, provider, model, ...)` — match against known persons DB
- Supports: Ollama (local), OpenAI, Anthropic

### Phase 5 — CV face recognition ✅
**Files:** `scripts/face_db.py`, `scripts/face_engine.py`, `scripts/install_persons_engine.py`

**Technology stack (selected):**
- `facenet-pytorch` (MIT licence) — MTCNN detection + InceptionResnetV1 embeddings
- `scikit-learn` — DBSCAN clustering on L2-normalised embeddings
- `sqlite3` — stdlib, no extra dependency

**Why facenet-pytorch:**
- MIT licence (commercial-friendly)
- torch already in imagedescriber spec
- Cross-platform without cmake
- State-of-the-art accuracy on VGGFace2

**Rejected alternatives:**
- `face_recognition`/dlib — requires cmake on Windows, unmaintained since 2020
- `deepface` — TensorFlow ≈500 MB, too large for PyInstaller
- `insightface` — non-commercial licence on pretrained models

**GUI integration (`imagedescriber_wx.py`):**
- `Tools → Install Face Recognition Engine` — progress dialog pip installer
- `Process → Scan Faces` — MTCNN detect + InceptionResnetV1 embed, stored to SQLite
- `Process → Cluster Faces` — DBSCAN on stored embeddings → GroupingResultsDialog
- `Process → Find Similar Faces` — cosine nearest-neighbour for selected image

---

## Testing Notes

All new `.py` files pass `python -m py_compile` syntax validation:
- `scripts/persons_manager.py` ✅
- `scripts/persons_cli.py` ✅
- `scripts/person_identifier.py` ✅
- `scripts/face_db.py` ✅
- `scripts/face_engine.py` ✅
- `scripts/install_persons_engine.py` ✅
- `imagedescriber/data_models.py` ✅
- `imagedescriber/person_dialogs_wx.py` ✅
- `imagedescriber/imagedescriber_wx.py` ✅
- `idt/idt_cli.py` ✅
- `scripts/descriptions_to_html.py` ✅

**Note on Phase 5 runtime testing:** Full runtime test of face detection requires
facenet-pytorch installed in the venv. The engine is optional and guarded by
`is_engine_available()` throughout — the rest of the app works without it.

---

## Files Modified / Created

| File | Change |
|------|--------|
| `scripts/image_describer_config.json` | Added `people_focused` prompt |
| `imagedescriber/data_models.py` | Added `PersonRecord`, `PersonGroup`; extended `ImageItem`, `ImageWorkspace` |
| `scripts/persons_manager.py` | **NEW** — full CRUD |
| `scripts/persons_cli.py` | **NEW** — CLI commands |
| `scripts/person_identifier.py` | **NEW** — text-mining + AI clustering |
| `scripts/face_db.py` | **NEW** — SQLite face embedding store |
| `scripts/face_engine.py` | **NEW** — facenet-pytorch wrapper (optional) |
| `scripts/install_persons_engine.py` | **NEW** — pip installer |
| `imagedescriber/person_dialogs_wx.py` | **NEW** — all person-related dialogs |
| `imagedescriber/imagedescriber_wx.py` | Added menus, handlers, person_tags_label |
| `idt/idt_cli.py` | Added `persons` command routing |
| `scripts/descriptions_to_html.py` | Added `person_tags` field, CSS, HTML rendering, JSON injection |
