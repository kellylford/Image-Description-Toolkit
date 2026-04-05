"""
Person identification dialogs for Image Describer (wxPython)

Provides accessible dialogs for:
  - TagPersonDialog       — tag a specific image with a known person
  - PersonDatabaseDialog  — manage the known persons database
  - GroupingResultsDialog — review auto-detected person groups
  - MatchResultsDialog    — confirm AI match suggestions

All dialogs comply with WCAG 2.2 AA: single-tab-stop list boxes, descriptive
name= parameters on all controls, no multi-column list controls.
"""

import re
import sys
import logging
from pathlib import Path
from typing import List, Optional

import wx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import path resolution (frozen exe + dev mode)
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    _project_root = Path(sys.executable).parent
else:
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from shared.wx_common import show_error, show_info, ask_yes_no
except ImportError:
    def show_error(parent, msg, title="Error"):
        wx.MessageBox(msg, title, wx.OK | wx.ICON_ERROR, parent)

    def show_info(parent, msg, title="Information"):
        wx.MessageBox(msg, title, wx.OK | wx.ICON_INFORMATION, parent)

    def ask_yes_no(parent, msg, title="Confirm"):
        dlg = wx.MessageDialog(parent, msg, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result

try:
    from .data_models import ImageWorkspace, PersonRecord, PersonGroup
except ImportError:
    from data_models import ImageWorkspace, PersonRecord, PersonGroup

try:
    from .persons_manager import (
        add_person, update_person, remove_person, find_person_by_name,
        tag_image, untag_image, get_persons_for_image, get_images_for_person,
        create_group, resolve_group_to_person, remove_group,
    )
except ImportError:
    try:
        from persons_manager import (
            add_person, update_person, remove_person, find_person_by_name,
            tag_image, untag_image, get_persons_for_image, get_images_for_person,
            create_group, resolve_group_to_person, remove_group,
        )
    except ImportError:
        # persons_manager is in scripts/; add that path
        _scripts_path = _project_root / "scripts"
        if str(_scripts_path) not in sys.path:
            sys.path.insert(0, str(_scripts_path))
        from persons_manager import (
            add_person, update_person, remove_person, find_person_by_name,
            tag_image, untag_image, get_persons_for_image, get_images_for_person,
            create_group, resolve_group_to_person, remove_group,
        )


# ---------------------------------------------------------------------------
# Description parsing — positional person extraction
# ---------------------------------------------------------------------------

def _extract_person_from_description(description: str, person_number: int) -> str:
    """Extract the text for person N from a left-to-right numbered description.

    The AI generates descriptions like:
        1. **Man in maroon** - Wearing a maroon polo...
        2. **Woman with dark hair** - Wearing a white blouse...

    Given person_number=2 this returns:
        "Woman with dark hair - Wearing a white blouse..."

    Returns empty string if the person number is not found.
    """
    # Match "N. text until next numbered item or end-of-string"
    pattern = rf'(?:^|\n)\s*{person_number}\.\s+(.*?)(?=\n\s*\d+\.|\Z)'
    match = re.search(pattern, description, re.DOTALL)
    if not match:
        return ""
    text = match.group(1).strip()
    # Strip markdown bold markers (**word**)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:400]


# ---------------------------------------------------------------------------
# TagPersonDialog
# ---------------------------------------------------------------------------

class TagPersonDialog(wx.Dialog):
    """Dialog for tagging an image with a known person.

    Shows the current image path and its description text (read-only) so the
    user can review physical trait details before assigning a name.

    Usage:
        dlg = TagPersonDialog(parent, workspace, file_path, description_text)
        if dlg.ShowModal() == wx.ID_OK:
            person_name = dlg.get_person_name()
            # then call tag_image(workspace, file_path, person_name)
        dlg.Destroy()
    """

    def __init__(self, parent, workspace: ImageWorkspace, file_path: str,
                 description_text: str = ""):
        super().__init__(parent, title="Tag Person in Image",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._workspace = workspace
        self._file_path = file_path
        self._description_text = description_text
        self._build_ui()
        self.SetMinSize(wx.Size(500, 400))
        self.Fit()
        self.CentreOnParent()

    def _build_ui(self):
        outer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Image filename label
        filename = Path(self._file_path).name
        img_label = wx.StaticText(panel, label=f"Image: {filename}",
                                  name="Image filename")
        img_label.SetFont(img_label.GetFont().Bold())
        sizer.Add(img_label, flag=wx.ALL, border=8)

        # Description text (read-only, scrollable)
        desc_label = wx.StaticText(panel, label="Description (read-only):",
                                   name="Description label")
        sizer.Add(desc_label, flag=wx.LEFT | wx.RIGHT, border=8)

        desc_ctrl = wx.TextCtrl(
            panel,
            value=self._description_text or "(no description)",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=wx.Size(-1, 120),
            name="Image description",
        )
        sizer.Add(desc_ctrl, proportion=1,
                  flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        # Person name input with autocomplete from known persons
        name_label = wx.StaticText(panel, label="Person name:",
                                   name="Person name label")
        sizer.Add(name_label, flag=wx.LEFT | wx.RIGHT, border=8)

        known_names = sorted(
            r.name for r in self._workspace.persons.values()
        )

        self._name_ctrl = wx.ComboBox(
            panel,
            choices=known_names,
            style=wx.CB_DROPDOWN,
            name="Person name — type a name or choose from known persons",
        )
        sizer.Add(self._name_ctrl, flag=wx.EXPAND | wx.ALL, border=8)

        # Currently tagged persons
        current = get_persons_for_image(self._workspace, self._file_path)
        if current:
            current_label = wx.StaticText(
                panel,
                label="Already tagged: " + ", ".join(p.name for p in current),
                name="Currently tagged persons",
            )
            sizer.Add(current_label, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        panel.SetSizer(sizer)
        outer.Add(panel, proportion=1, flag=wx.EXPAND)

        # Button row
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        ok_btn = self.FindWindowById(wx.ID_OK)
        if ok_btn:
            ok_btn.SetLabel("Tag Person")
        outer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        self.SetSizer(outer)

        # Bind OK to validate
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, _event):
        name = self._name_ctrl.GetValue().strip()
        if not name:
            show_error(self, "Please enter a person name.", "Name Required")
            self._name_ctrl.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_person_name(self) -> str:
        """Return the person name entered by the user."""
        return self._name_ctrl.GetValue().strip()


# ---------------------------------------------------------------------------
# AddEditPersonDialog  (helper used inside PersonDatabaseDialog)
# ---------------------------------------------------------------------------

class _AddEditPersonDialog(wx.Dialog):
    """Internal dialog for adding or editing a PersonRecord."""

    def __init__(self, parent, title="Add Person", record: Optional[PersonRecord] = None):
        super().__init__(parent, title=title,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._record = record
        self._build_ui()
        self.Fit()
        self.SetMinSize(wx.Size(420, 300))
        self.CentreOnParent()

    def _build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(rows=3, cols=2, hgap=8, vgap=6)
        grid.AddGrowableCol(1)

        # Name
        grid.Add(wx.StaticText(self, label="Name:", name="Name label"),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        self._name = wx.TextCtrl(self, name="Person name",
                                  value=self._record.name if self._record else "")
        grid.Add(self._name, flag=wx.EXPAND)

        # Traits
        grid.Add(wx.StaticText(self, label="Physical traits:", name="Traits label"),
                 flag=wx.ALIGN_TOP | wx.TOP, border=2)
        self._traits = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
            size=wx.Size(-1, 80),
            name="Physical description traits for AI matching",
            value=self._record.description_traits if self._record else "",
        )
        grid.Add(self._traits, flag=wx.EXPAND)

        # Notes
        grid.Add(wx.StaticText(self, label="Notes:", name="Notes label"),
                 flag=wx.ALIGN_TOP | wx.TOP, border=2)
        self._notes = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
            size=wx.Size(-1, 60),
            name="Optional notes about this person",
            value=self._record.notes if self._record else "",
        )
        grid.Add(self._notes, flag=wx.EXPAND)

        sizer.Add(grid, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)
        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL),
                  flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, _event):
        if not self._name.GetValue().strip():
            show_error(self, "Please enter a name.", "Name Required")
            self._name.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_values(self):
        return (
            self._name.GetValue().strip(),
            self._traits.GetValue().strip(),
            self._notes.GetValue().strip(),
        )


# ---------------------------------------------------------------------------
# PersonDatabaseDialog
# ---------------------------------------------------------------------------

class PersonDatabaseDialog(wx.Dialog):
    """Dialog for managing the known persons database.

    Lists all PersonRecords; supports Add, Edit, Remove, and Export.
    Accessible: single-tab-stop ListBox, all controls named.
    """

    def __init__(self, parent, workspace: ImageWorkspace):
        super().__init__(parent, title="Known Persons Database",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._workspace = workspace
        self._modified = False
        self._build_ui()
        self.SetMinSize(wx.Size(560, 400))
        self.Fit()
        self.CentreOnParent()
        self._refresh_list()

    def _build_ui(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        # Split: list on left, detail panel on right
        content = wx.BoxSizer(wx.HORIZONTAL)

        # Left: persons list + buttons
        left = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(self, label="Known persons:",
                                   name="Known persons list label")
        left.Add(list_label, flag=wx.LEFT | wx.TOP, border=8)

        self._list = wx.ListBox(self, style=wx.LB_SINGLE,
                                name="Known persons — select to view details")
        self._list.SetMinSize(wx.Size(200, 200))
        left.Add(self._list, proportion=1,
                 flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_add = wx.Button(self, label="Add", name="Add new person")
        self._btn_edit = wx.Button(self, label="Edit", name="Edit selected person")
        self._btn_remove = wx.Button(self, label="Remove", name="Remove selected person")
        btn_row.Add(self._btn_add)
        btn_row.AddSpacer(4)
        btn_row.Add(self._btn_edit)
        btn_row.AddSpacer(4)
        btn_row.Add(self._btn_remove)
        left.Add(btn_row, flag=wx.LEFT | wx.BOTTOM, border=8)
        content.Add(left, proportion=1, flag=wx.EXPAND)

        content.AddSpacer(8)

        # Right: detail panel
        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self, label="Details:", name="Person details label"),
                  flag=wx.TOP, border=8)

        self._detail = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=wx.Size(260, 200),
            name="Person details — traits, notes, tagged images",
        )
        right.Add(self._detail, proportion=1,
                  flag=wx.EXPAND | wx.RIGHT | wx.BOTTOM, border=8)
        content.Add(right, proportion=1, flag=wx.EXPAND)

        outer.Add(content, proportion=1, flag=wx.EXPAND | wx.ALL, border=4)

        # Close button
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_export = wx.Button(self, label="Export to JSON…",
                                      name="Export persons database to JSON file")
        close_btn = wx.Button(self, wx.ID_CLOSE, label="Close")
        btn_sizer.Add(self._btn_export)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(close_btn)
        outer.Add(btn_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        self.SetSizer(outer)

        # Events
        self._list.Bind(wx.EVT_LISTBOX, self._on_select)
        self._btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        self._btn_edit.Bind(wx.EVT_BUTTON, self._on_edit)
        self._btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self._btn_export.Bind(wx.EVT_BUTTON, self._on_export)
        close_btn.Bind(wx.EVT_BUTTON, lambda _: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CLOSE, lambda _: self.EndModal(wx.ID_CLOSE))

    def _refresh_list(self):
        self._list.Clear()
        self._records: List[PersonRecord] = sorted(
            self._workspace.persons.values(), key=lambda r: r.name.lower()
        )
        for record in self._records:
            images = get_images_for_person(self._workspace, record.id)
            self._list.Append(f"{record.name} ({len(images)} image(s))")
        self._detail.SetValue("")
        self._update_buttons()

    def _update_buttons(self):
        has_sel = self._list.GetSelection() != wx.NOT_FOUND
        self._btn_edit.Enable(has_sel)
        self._btn_remove.Enable(has_sel)

    def _on_select(self, _event):
        idx = self._list.GetSelection()
        if idx == wx.NOT_FOUND:
            self._detail.SetValue("")
            self._update_buttons()
            return
        record = self._records[idx]
        images = get_images_for_person(self._workspace, record.id)
        lines = [
            f"Name: {record.name}",
            f"Traits: {record.description_traits or '(none)'}",
            f"Notes: {record.notes or '(none)'}",
            f"Tagged images ({len(images)}):",
        ]
        for path in images:
            lines.append(f"  {Path(path).name}")
        self._detail.SetValue("\n".join(lines))
        self._update_buttons()

    def _on_add(self, _event):
        dlg = _AddEditPersonDialog(self, title="Add Person")
        if dlg.ShowModal() == wx.ID_OK:
            name, traits, notes = dlg.get_values()
            add_person(self._workspace, name, traits, notes)
            self._modified = True
            self._refresh_list()
        dlg.Destroy()

    def _on_edit(self, _event):
        idx = self._list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        record = self._records[idx]
        dlg = _AddEditPersonDialog(self, title="Edit Person", record=record)
        if dlg.ShowModal() == wx.ID_OK:
            name, traits, notes = dlg.get_values()
            update_person(self._workspace, record.id,
                          name=name, description_traits=traits, notes=notes)
            self._modified = True
            self._refresh_list()
        dlg.Destroy()

    def _on_remove(self, _event):
        idx = self._list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        record = self._records[idx]
        images = get_images_for_person(self._workspace, record.id)
        msg = f"Remove '{record.name}'?"
        if images:
            msg += f"\nThis will also remove their tag from {len(images)} image(s)."
        if ask_yes_no(self, msg, "Confirm Remove"):
            remove_person(self._workspace, record.id)
            self._modified = True
            self._refresh_list()

    def _on_export(self, _event):
        import json
        dlg = wx.FileDialog(
            self,
            message="Export persons database",
            wildcard="JSON files (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            defaultFile="persons_database.json",
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                data = {
                    pid: r.to_dict()
                    for pid, r in self._workspace.persons.items()
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                show_info(self, f"Exported {len(data)} person(s) to:\n{path}")
            except Exception as e:
                show_error(self, f"Export failed: {e}")
        dlg.Destroy()

    def was_modified(self) -> bool:
        """Return True if any changes were made to the workspace persons data."""
        return self._modified


# ---------------------------------------------------------------------------
# GroupingResultsDialog
# ---------------------------------------------------------------------------

class GroupingResultsDialog(wx.Dialog):
    """Dialog for reviewing auto-detected person groups.

    Shows each candidate PersonGroup with the images it contains along with
    their description excerpts, so a blind user can confirm identity by
    reading the descriptions.

    Buttons per group: Accept (save as group), Skip, Mark as Same Person
    (link to existing known person).
    """

    def __init__(self, parent, workspace: ImageWorkspace,
                 candidate_groups: List[PersonGroup],
                 image_descriptions: dict,
                 workspace_dir: Optional[str] = None):
        """
        Args:
            parent: Parent window.
            workspace: Active ImageWorkspace.
            candidate_groups: Groups produced by person_identifier.py.
            image_descriptions: Dict of {file_path: description_text} for display.
            workspace_dir: Path to the workspace directory (enables per-face description).
        """
        super().__init__(parent, title="Person Grouping Results",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._workspace = workspace
        self._candidates = list(candidate_groups)
        self._descriptions = image_descriptions
        self._workspace_dir = workspace_dir
        self._face_db = None  # Lazily opened when workspace_dir is set
        self._accepted: List[PersonGroup] = []
        self._current_idx = 0
        self._modified = False
        self._build_ui()
        self.SetMinSize(wx.Size(600, 500))
        self.Fit()
        self.CentreOnParent()
        self._show_group(0)

    def _build_ui(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        # Header: progress
        self._progress_label = wx.StaticText(
            self, label="", name="Group review progress"
        )
        outer.Add(self._progress_label, flag=wx.ALL, border=8)

        # Group label + method
        self._group_label = wx.StaticText(
            self, label="", name="Candidate group label"
        )
        self._group_label.SetFont(self._group_label.GetFont().Bold())
        outer.Add(self._group_label, flag=wx.LEFT | wx.RIGHT, border=8)

        self._summary_label = wx.StaticText(
            self, label="", name="Group description summary"
        )
        outer.Add(self._summary_label, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        # Images in this group with descriptions
        outer.Add(
            wx.StaticText(self, label="Images in this group:",
                          name="Images in group label"),
            flag=wx.LEFT, border=8
        )
        self._image_list = wx.ListBox(
            self,
            style=wx.LB_SINGLE,
            name="Images in candidate group — select to read description",
        )
        self._image_list.SetMinSize(wx.Size(-1, 120))
        outer.Add(self._image_list, flag=wx.EXPAND | wx.ALL, border=8)

        # Description of selected image
        outer.Add(
            wx.StaticText(self, label="Description of selected image:",
                          name="Selected image description label"),
            flag=wx.LEFT, border=8
        )
        self._desc_ctrl = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=wx.Size(-1, 100),
            name="Description text of selected image",
        )
        outer.Add(self._desc_ctrl, flag=wx.EXPAND | wx.ALL, border=8)

        # Action buttons
        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_accept = wx.Button(
            self, label="Accept Group", name="Accept this candidate group"
        )
        self._btn_name = wx.Button(
            self, label="Accept & Name…", name="Accept group and assign a known person name"
        )
        self._btn_skip = wx.Button(
            self, label="Skip", name="Skip this candidate group"
        )
        action_row.Add(self._btn_accept)
        action_row.AddSpacer(4)
        action_row.Add(self._btn_name)
        action_row.AddSpacer(4)
        action_row.Add(self._btn_skip)
        outer.Add(action_row, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        # Close button
        close_btn = wx.Button(self, wx.ID_CLOSE, label="Done")
        outer.Add(close_btn, flag=wx.ALIGN_RIGHT | wx.ALL, border=8)

        self.SetSizer(outer)

        self._image_list.Bind(wx.EVT_LISTBOX, self._on_image_select)
        self._btn_accept.Bind(wx.EVT_BUTTON, self._on_accept)
        self._btn_name.Bind(wx.EVT_BUTTON, self._on_accept_and_name)
        self._btn_skip.Bind(wx.EVT_BUTTON, self._on_skip)
        close_btn.Bind(wx.EVT_BUTTON, lambda _: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CLOSE, lambda _: self.EndModal(wx.ID_CLOSE))

    def _show_group(self, idx: int):
        total = len(self._candidates)
        if idx >= total:
            self.SetTitle(f"Person Grouping Results — Done")
            self._group_label.SetLabel("All groups reviewed.")
            self._summary_label.SetLabel("")
            self._progress_label.SetLabel(f"Done — {len(self._accepted)} group(s) accepted.")
            self._image_list.Clear()
            self._desc_ctrl.SetValue("")
            self._btn_accept.Enable(False)
            self._btn_name.Enable(False)
            self._btn_skip.Enable(False)
            return

        self._current_idx = idx
        group = self._candidates[idx]
        self.SetTitle(f"Person Grouping Results — {idx + 1} of {total}")
        self._progress_label.SetLabel(
            f"Group {idx + 1} of {total}  —  method: {group.method}"
        )
        self._group_label.SetLabel(f"Candidate: {group.display_label}")
        self._summary_label.SetLabel(
            group.description_summary or "(no summary available)"
        )

        self._image_list.Clear()
        for path in group.images:
            self._image_list.Append(Path(path).name)

        if group.images:
            self._image_list.SetSelection(0)
            self._show_description_for(group.images[0])

    def _show_description_for(self, file_path: str):
        full_text = self._descriptions.get(file_path, "(no description)")
        if self._workspace_dir is not None:
            focused = self._get_focused_person_description(file_path, full_text)
            if focused:
                self._desc_ctrl.SetValue(focused)
                return
        self._desc_ctrl.SetValue(full_text)

    def _get_focused_person_description(self, filename: str, full_text: str) -> str:
        """Return a focused per-face description using bounding box position matching.

        Looks up which x-position this cluster's face occupies in *filename*,
        then ranks that position among all faces in the image (left to right) to
        determine the person number, and extracts just that person's text.

        Returns empty string when the lookup fails or no match is found.
        """
        group = self._candidates[self._current_idx]
        cluster_label = self._parse_cluster_label(group.display_label)
        if cluster_label is None:
            return ""

        # Lazy-init the face DB connection for this session
        if self._face_db is None:
            try:
                _scripts_path = str(_project_root / "scripts")
                if _scripts_path not in sys.path:
                    sys.path.insert(0, _scripts_path)
                from face_db import FaceDatabase
                self._face_db = FaceDatabase(Path(self._workspace_dir))
            except Exception as exc:
                logger.warning("GroupingResultsDialog: could not open face DB: %s", exc)
                return ""

        try:
            x1 = self._face_db.get_cluster_face_x_for_image(cluster_label, filename)
            if x1 is None:
                return ""
            rank = self._face_db.get_x_rank_in_image(filename, x1)
            person_text = _extract_person_from_description(full_text, rank)
            if person_text:
                return f"Person {rank} (from left in image):\n{person_text}"
            # rank exists but AI didn't number that person — show position note + full text
            return f"Person {rank} (from left in image) — not individually described by AI.\n\nFull image description:\n{full_text}"
        except Exception as exc:
            logger.warning("GroupingResultsDialog: position lookup failed: %s", exc)
        return ""

    def _parse_cluster_label(self, display_label: str) -> Optional[int]:
        """Parse the integer cluster label from a 'Face cluster N' display label."""
        m = re.search(r'Face cluster\s+(\d+)', display_label, re.IGNORECASE)
        return int(m.group(1)) if m else None

    def _resolve_image_paths(self, filenames: list) -> list:
        """Resolve short filenames from the face DB to full workspace paths.

        The face DB stores filenames only (e.g. 'img_0022.jpg'), but
        workspace.items is keyed by full path. Build a name→path map and
        return full paths where possible, falling back to the original string.
        """
        name_to_path = {Path(fp).name: fp for fp in self._workspace.items}
        return [name_to_path.get(Path(p).name, p) for p in filenames]

    def _on_image_select(self, _event):
        idx = self._image_list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        group = self._candidates[self._current_idx]
        if idx < len(group.images):
            self._show_description_for(group.images[idx])

    def _on_accept(self, _event):
        group = self._candidates[self._current_idx]
        resolved = self._resolve_image_paths(group.images)
        saved = create_group(
            self._workspace,
            display_label=group.display_label,
            images=resolved,
            description_summary=group.description_summary,
            method=group.method,
        )
        self._accepted.append(saved)
        self._modified = True
        self._show_group(self._current_idx + 1)

    def _on_accept_and_name(self, _event):
        dlg = wx.TextEntryDialog(
            self,
            "Enter a name to assign to this group (or leave blank to save unnamed):",
            "Name This Group",
        )
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            group = self._candidates[self._current_idx]
            resolved = self._resolve_image_paths(group.images)
            saved = create_group(
                self._workspace,
                display_label=name or group.display_label,
                images=resolved,
                description_summary=group.description_summary,
                method=group.method,
            )
            if name:
                resolve_group_to_person(self._workspace, saved.id, name)
            self._accepted.append(saved)
            self._modified = True
        dlg.Destroy()
        self._show_group(self._current_idx + 1)

    def _on_skip(self, _event):
        self._show_group(self._current_idx + 1)

    def get_accepted_groups(self) -> List[PersonGroup]:
        return list(self._accepted)

    def was_modified(self) -> bool:
        return self._modified


# ---------------------------------------------------------------------------
# MatchResultsDialog
# ---------------------------------------------------------------------------

class MatchResultsDialog(wx.Dialog):
    """Dialog for reviewing AI-generated person match suggestions.

    Shows each suggested (image, person_name, confidence) triple; the user
    confirms or rejects each match.
    """

    def __init__(self, parent, workspace: ImageWorkspace,
                 matches: List[dict], image_descriptions: dict):
        """
        Args:
            matches: List of dicts with keys:
                       file_path, person_name, confidence (0-1 float),
                       description_excerpt (optional)
            image_descriptions: Dict of {file_path: description_text}
        """
        super().__init__(parent, title="Person Match Results",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._workspace = workspace
        self._matches = list(matches)
        self._descriptions = image_descriptions
        self._confirmed: List[dict] = []
        self._current_idx = 0
        self._modified = False
        self._build_ui()
        self.SetMinSize(wx.Size(580, 480))
        self.Fit()
        self.CentreOnParent()
        self._show_match(0)

    def _build_ui(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        self._progress_label = wx.StaticText(
            self, label="", name="Match review progress"
        )
        outer.Add(self._progress_label, flag=wx.ALL, border=8)

        # Image info
        self._image_label = wx.StaticText(
            self, label="", name="Image filename"
        )
        self._image_label.SetFont(self._image_label.GetFont().Bold())
        outer.Add(self._image_label, flag=wx.LEFT | wx.RIGHT, border=8)

        # Description
        outer.Add(
            wx.StaticText(self, label="Image description:",
                          name="Image description label"),
            flag=wx.LEFT | wx.TOP, border=8
        )
        self._desc_ctrl = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=wx.Size(-1, 110),
            name="Description text of the image being matched",
        )
        outer.Add(self._desc_ctrl, flag=wx.EXPAND | wx.ALL, border=8)

        # Proposed match
        self._match_label = wx.StaticText(
            self, label="", name="Proposed person match"
        )
        outer.Add(self._match_label, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        # Action buttons
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_confirm = wx.Button(
            self, label="Confirm Match", name="Confirm this person match"
        )
        self._btn_reject = wx.Button(
            self, label="Reject", name="Reject this person match"
        )
        row.Add(self._btn_confirm)
        row.AddSpacer(4)
        row.Add(self._btn_reject)
        outer.Add(row, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        close_btn = wx.Button(self, wx.ID_CLOSE, label="Done")
        outer.Add(close_btn, flag=wx.ALIGN_RIGHT | wx.ALL, border=8)

        self.SetSizer(outer)

        self._btn_confirm.Bind(wx.EVT_BUTTON, self._on_confirm)
        self._btn_reject.Bind(wx.EVT_BUTTON, self._on_reject)
        close_btn.Bind(wx.EVT_BUTTON, lambda _: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CLOSE, lambda _: self.EndModal(wx.ID_CLOSE))

    def _show_match(self, idx: int):
        total = len(self._matches)
        if idx >= total:
            self._progress_label.SetLabel(
                f"Done — {len(self._confirmed)} match(es) confirmed."
            )
            self._image_label.SetLabel("")
            self._desc_ctrl.SetValue("")
            self._match_label.SetLabel("")
            self._btn_confirm.Enable(False)
            self._btn_reject.Enable(False)
            return

        self._current_idx = idx
        m = self._matches[idx]
        self._progress_label.SetLabel(f"Match {idx + 1} of {total}")
        self._image_label.SetLabel(Path(m["file_path"]).name)
        self._desc_ctrl.SetValue(
            self._descriptions.get(m["file_path"], "(no description)")
        )
        confidence_pct = int(m.get("confidence", 0) * 100)
        self._match_label.SetLabel(
            f"Proposed match: {m['person_name']}  (confidence: {confidence_pct}%)"
        )

    def _on_confirm(self, _event):
        m = self._matches[self._current_idx]
        tag_image(self._workspace, m["file_path"], m["person_name"])
        self._confirmed.append(m)
        self._modified = True
        self._show_match(self._current_idx + 1)

    def _on_reject(self, _event):
        self._show_match(self._current_idx + 1)

    def get_confirmed_matches(self) -> List[dict]:
        return list(self._confirmed)

    def was_modified(self) -> bool:
        return self._modified
