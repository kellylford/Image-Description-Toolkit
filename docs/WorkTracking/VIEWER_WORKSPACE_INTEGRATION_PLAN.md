# Viewer-to-Workspace Integration Plan

**Date:** 2026-02-10  
**Status:** Planning  
**Priority:** High (Data Loss Risk)

## Problem Statement

Opening a workflow directory in Results Viewer mode creates a disconnected viewing session that cannot be converted into an editable workspace without manual steps. This causes several UX and data integrity issues:

### Critical Issues

1. **Data Loss Risk**: User views workflow results, clicks "Save Workspace", but saves an empty/unrelated workspace instead of what they're viewing
2. **Disconnected State**: Viewer mode has no relationship to the workspace system - they're parallel universes
3. **Awkward Conversion**: To edit viewed results, user must:
   - Switch to Editor mode (losing viewer context)
   - File → Import Workflow
   - Re-select the same directory they just viewed
4. **Menu Ambiguity**: All menus remain enabled in viewer mode, including "Process Current Image" which has no context
5. **Live Mode Limbo**: User watches descriptions appear in real-time but can't transition to editing without starting over

### Current Architecture Gaps

**From Research:**
- `ViewerPanel` loads data from `image_descriptions.txt` (text parsing)
- `ImageWorkspace` stores data in memory (object graph)
- No bridge between these representations
- Viewer mode doesn't create/populate `self.workspace`
- Save operations act on `self.workspace`, ignoring viewer state
- Menu state doesn't change based on mode

## Phased Solution

### Phase 1: Safety & Clarity (Immediate - v4.1.1)

**Goal:** Prevent data loss and user confusion

**Changes:**

1. **Disable Save Operations in Viewer Mode**
   - Disable `File → Save Workspace` when `current_mode == 'viewer'`
   - Disable `File → Save Workspace As...` in viewer mode
   - Reason: No workspace to save, prevents accidental empty workspace creation

2. **Mode Indicators**
   - Status bar shows: `"Viewing: {workflow_name}"` or `"Viewing: {workflow_name} (Live)"` in viewer mode
   - Status bar shows: `"Editing: {workspace_file}"` or `"Editing: Untitled"` in editor mode
   - Window title includes mode: `"{title} - Viewer"` vs `"{title} - Editor"`

3. **Warning on Mode Switch**
   - If switching from viewer to editor mode:
     - Show dialog: "Switching to Editor mode will close the current workflow view. Continue?"
     - Options: Continue / Cancel
   - If editor has unsaved changes when switching to viewer:
     - Use existing `confirm_unsaved_changes()` logic

4. **Menu State Management**
   - **Disable in Viewer Mode:**
     - `Process → Process Current Image`
     - `Process → Batch Process All Images`
     - `Process → Stop Processing`
     - `Descriptions → Add Description`
     - `Descriptions → Delete Selected Description`
   - **Enable in Viewer Mode:**
     - `Descriptions → Export to HTML` (if useful for workflow)
     - `File → Import Workflow` (to add to current view - see Phase 2)
   - Tooltip/status text explains why disabled when hovered

**Implementation Files:**
- `imagedescriber/imagedescriber_wx.py` (menu state, mode switching)
- `imagedescriber/viewer_components.py` (mode indicator updates)

**Testing:**
- Open workflow in viewer mode → verify Save disabled
- Try to switch modes → verify warnings appear
- Check status bar updates correctly
- Verify disabled menus show appropriate tooltips

**Risk:** Low - Pure UI safety improvements

---

### Phase 2: Viewer-to-Workspace Conversion (Short-Term - v4.2.0)

**Goal:** Provide seamless conversion from viewed workflow to editable workspace

**New Feature: "Convert to Workspace"**

#### User Experience

**Menu Location:** `File → Convert Workflow to Workspace` (enabled only in viewer mode)

**Workflow:**

1. User is viewing workflow results (possibly in live mode)
2. Clicks `File → Convert Workflow to Workspace`
3. If live mode active:
   - Dialog: "Live monitoring is active. Stop monitoring and convert current results to workspace?"
   - Options: Convert Now / Cancel
   - If Convert: Stop monitoring thread cleanly
4. Conversion dialog appears:
   - "Converting workflow to editable workspace..."
   - Progress bar (if many images)
   - Shows:
     - Images found: X
     - Descriptions loaded: Y
     - Path resolution: Z/Y successful
5. On completion:
   - Auto-switch to Editor mode
   - Workspace marked as modified (*Untitled)
   - Status message: "Workspace created from {workflow_name} with {n} images"
   - Ask: "Save workspace now?" → Opens Save As dialog if Yes
6. If errors (missing images):
   - Show summary: "X images could not be located"
   - Option to save anyway or review missing files
   - Still creates workspace with available images

#### Technical Implementation

**New Method:** `on_convert_to_workspace()` in `ImageDescriberFrame`

```python
def on_convert_to_workspace(self, event):
    """Convert currently viewed workflow to editable workspace"""
    # Verify we're in viewer mode with a workflow directory
    if self.current_mode != 'viewer' or not self.viewer_panel.current_dir:
        show_error(self, "Must be viewing a workflow to convert")
        return
    
    # Check for live monitoring
    if self.viewer_panel.is_live:
        if not ask_yes_no(self, 
            "Live monitoring is active. Stop monitoring and convert current results?",
            "Convert Workflow"):
            return
        self.viewer_panel.is_live = False
        if self.viewer_panel.monitor_thread:
            self.viewer_panel.monitor_thread.stop()
            self.viewer_panel.monitor_thread = None
    
    # Show progress dialog
    progress_dlg = wx.ProgressDialog(
        "Converting Workflow",
        "Preparing to convert workflow to workspace...",
        maximum=100,
        parent=self,
        style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE
    )
    
    try:
        # Create new workspace
        new_workspace = ImageWorkspace(new_workspace=True)
        
        # Get workflow directory and metadata
        workflow_dir = self.viewer_panel.current_dir
        workflow_metadata = load_workflow_metadata(workflow_dir)
        
        # Track conversion source for potential re-sync
        new_workspace.imported_workflow_dir = str(workflow_dir)
        
        # Add source directory from workflow metadata
        if workflow_metadata and 'input_directory' in workflow_metadata:
            source_dir = workflow_metadata['input_directory']
            if Path(source_dir).exists():
                new_workspace.add_directory(source_dir)
        
        # Also check input_images directory in workflow
        input_images_dir = workflow_dir / "input_images"
        if input_images_dir.exists():
            # Count total for progress
            total_items = len(self.viewer_panel.entries)
            
        # Convert each entry from viewer to workspace
        images_found = 0
        images_missing = 0
        descriptions_loaded = 0
        missing_paths = []
        
        for i, entry in enumerate(self.viewer_panel.entries):
            # Update progress
            progress = int((i / total_items) * 100) if total_items > 0 else 0
            progress_dlg.Update(progress, 
                f"Processing {i+1}/{total_items}: {entry.get('relative_path', 'image')}")
            
            # Resolve image path
            image_path = self._resolve_workflow_image_path(
                entry, workflow_dir, new_workspace.directory_paths
            )
            
            if not image_path or not Path(image_path).exists():
                images_missing += 1
                missing_paths.append(entry.get('relative_path', entry.get('file_path', 'unknown')))
                continue
            
            images_found += 1
            
            # Create or get ImageItem
            image_path_str = str(image_path)
            if image_path_str not in new_workspace.items:
                # Determine item type
                parent_name = Path(image_path).parent.name
                if parent_name == 'extracted_frames':
                    item_type = 'extracted_frame'
                else:
                    item_type = 'image'
                
                item = ImageItem(image_path_str, item_type)
                new_workspace.add_item(item)
            else:
                item = new_workspace.items[image_path_str]
            
            # Create ImageDescription from entry
            desc = ImageDescription(
                text=entry.get('description', ''),
                model=entry.get('model', ''),
                prompt_style=entry.get('prompt_style', ''),
                custom_prompt='',  # Not stored in workflow text
                provider=entry.get('provider', ''),
                metadata={}  # Will be re-extracted from EXIF if needed
            )
            # Preserve timestamp if available
            if entry.get('created'):
                desc.created = entry['created']
            
            # Add description (checks for duplicates internally)
            if item.add_description(desc):
                descriptions_loaded += 1
        
        progress_dlg.Update(100, "Conversion complete")
        
        # Show results
        summary = f"Workspace created:\n\n"
        summary += f"  Images found: {images_found}\n"
        summary += f"  Descriptions loaded: {descriptions_loaded}\n"
        
        if images_missing > 0:
            summary += f"\n  ⚠ {images_missing} images could not be located\n"
            if len(missing_paths) <= 10:
                summary += "\nMissing files:\n" + "\n".join(f"  • {p}" for p in missing_paths)
            else:
                summary += f"\nMissing files: {len(missing_paths)} (showing first 10):\n"
                summary += "\n".join(f"  • {p}" for p in missing_paths[:10])
        
        # Ask about missing files
        if images_missing > 0:
            if not ask_yes_no(self, 
                f"{summary}\n\nCreate workspace anyway?",
                "Conversion Complete with Warnings"):
                return
        else:
            show_info(self, summary, "Conversion Complete")
        
        # Switch to editor mode with new workspace
        self.workspace = new_workspace
        self.switch_mode('editor')
        self.refresh_image_list()
        self.mark_modified()  # Unsaved changes
        
        # Offer to save immediately
        if ask_yes_no(self, "Save workspace now?", "Save Workspace"):
            self.on_save_workspace_as(None)
        
    except Exception as e:
        show_error(self, f"Error converting workflow:\n{str(e)}")
        import traceback
        self.logger.error(f"Conversion error: {traceback.format_exc()}")
    finally:
        progress_dlg.Destroy()


def _resolve_workflow_image_path(self, entry, workflow_dir, additional_search_dirs):
    """
    Resolve image path from workflow entry.
    
    Tries in order:
    1. entry['file_path'] if absolute and exists
    2. workflow_dir/input_images/{relative_path}
    3. workflow_dir/input_images/{filename}
    4. Search in additional_search_dirs
    5. Recursive search in converted_images, extracted_frames
    
    Returns Path object or None if not found
    """
    from pathlib import Path
    
    # Try direct path
    if 'file_path' in entry and Path(entry['file_path']).exists():
        return Path(entry['file_path'])
    
    # Get filename/relative path
    relative = entry.get('relative_path', '')
    if not relative and 'file_path' in entry:
        relative = Path(entry['file_path']).name
    
    if not relative:
        return None
    
    # Try input_images directory
    input_images = workflow_dir / "input_images" / relative
    if input_images.exists():
        return input_images
    
    # Try just filename in input_images
    input_images_flat = workflow_dir / "input_images" / Path(relative).name
    if input_images_flat.exists():
        return input_images_flat
    
    # Search in additional directories
    for search_dir in additional_search_dirs:
        candidate = Path(search_dir) / relative
        if candidate.exists():
            return candidate
        candidate = Path(search_dir) / Path(relative).name
        if candidate.exists():
            return candidate
    
    # Recursive search in workflow subdirectories
    for subdir_name in ['converted_images', 'extracted_frames', 'input_images']:
        subdir = workflow_dir / subdir_name
        if subdir.exists():
            # Recursive search
            try:
                matches = list(subdir.rglob(Path(relative).name))
                if matches:
                    return matches[0]  # Return first match
            except Exception:
                pass
    
    return None
```

**Menu Item:**
```python
convert_item = file_menu.Append(wx.ID_ANY, "Convert Workflow to &Workspace...")
self.Bind(wx.EVT_MENU, self.on_convert_to_workspace, convert_item)
# Enable only in viewer mode - update in switch_mode()
```

**Files Modified:**
- `imagedescriber/imagedescriber_wx.py` - Add conversion method and menu
- `imagedescriber/data_models.py` - Ensure `add_description()` handles duplicate checking

**Advanced Feature: Smart Path Mapping**

Read `descriptions/file_path_mapping.json` if it exists (created by some workflow tools):
```json
{
  "/tmp/converted_abc.jpg": "/original/path/image.heic",
  "/tmp/frame_001.jpg": "/videos/movie.mp4#frame001"
}
```

Use this to resolve original source files rather than workflow temp paths.

**Testing:**
- Convert simple workflow → verify all images found
- Convert with missing images → verify warning and partial success
- Convert in live mode → verify monitoring stops
- Convert with complex paths (extracted frames, converted HEIC) → verify resolution
- Cancel at various stages → verify no corruption

**Risk:** Medium - Complex path resolution, must handle edge cases gracefully

---

### Phase 3: Workspace-Aware Viewing (Medium-Term - v4.3.0)

**Goal:** Allow workspaces to remember viewer state and support re-synchronization

#### Extended .idw Format

Add optional `viewer_state` to workspace:

```json
{
  "version": "3.1",
  "items": { /* ... */ },
  "viewer_state": {
    "workflow_dir": "/path/to/wf_2026-02-10_...",
    "last_viewed": "2026-02-10T14:30:00",
    "live_mode_was_active": false,
    "import_timestamp": "2026-02-10T14:25:00"
  }
}
```

#### Features

1. **Restore Viewer Mode on Load** (Optional)
   - When loading .idw with `viewer_state`:
     - Show dialog: "This workspace was created from a workflow. Open in Viewer mode or Editor mode?"
     - Options: Viewer / Editor / Ask Each Time (preference)
   - If Viewer selected: Switch to viewer mode and load workflow directory
   - Preserves viewing context across sessions

2. **Re-sync from Workflow**
   - New menu: `File → Sync from Workflow...` (enabled when workspace has `imported_workflow_dir`)
   - Checks if workflow directory still exists
   - Compares timestamps:
     - Workflow `image_describer_progress.txt` modification time
     - Workspace `import_timestamp`
   - If workflow newer:
     - Parse descriptions again
     - Merge new descriptions (don't overwrite edited ones)
     - Add new images not yet in workspace
     - Update `import_timestamp`
   - Shows diff: "+5 new descriptions, +2 new images"

3. **Track Edit History**
   - Mark descriptions as "imported" vs "user-edited"
   - On re-sync, preserve user edits
   - Offer to review conflicts if workflow regenerated with different model

#### Implementation

**Update `data_models.py`:**

```python
class ImageWorkspace:
    def __init__(self, new_workspace=False):
        # ... existing fields ...
        self.viewer_state = None  # Optional dict with viewer context
    
    def set_viewer_state(self, workflow_dir, live_mode=False):
        """Store viewer state for restoration"""
        from datetime import datetime
        self.viewer_state = {
            'workflow_dir': str(workflow_dir),
            'last_viewed': datetime.now().isoformat(),
            'live_mode_was_active': live_mode,
            'import_timestamp': datetime.now().isoformat()
        }
        self.mark_modified()
    
    def to_dict(self):
        data = {
            # ... existing fields ...
        }
        if self.viewer_state:
            data['viewer_state'] = self.viewer_state
        return data
    
    @staticmethod
    def from_dict(data):
        workspace = ImageWorkspace(new_workspace=True)
        # ... existing field restoration ...
        workspace.viewer_state = data.get('viewer_state')
        return workspace
```

**Add to `imagedescriber_wx.py`:**

```python
def on_sync_from_workflow(self, event):
    """Re-import descriptions from original workflow directory"""
    if not self.workspace or not self.workspace.imported_workflow_dir:
        show_info(self, "No workflow source to sync from", "Sync from Workflow")
        return
    
    workflow_dir = Path(self.workspace.imported_workflow_dir)
    if not workflow_dir.exists():
        show_error(self, f"Workflow directory not found:\n{workflow_dir}")
        return
    
    # Check if workflow has been updated
    progress_file = workflow_dir / "logs" / "image_describer_progress.txt"
    if progress_file.exists():
        workflow_mtime = datetime.fromtimestamp(progress_file.stat().st_mtime)
        
        if self.workspace.viewer_state and 'import_timestamp' in self.workspace.viewer_state:
            import_time = datetime.fromisoformat(self.workspace.viewer_state['import_timestamp'])
            if workflow_mtime <= import_time:
                if not ask_yes_no(self, 
                    "Workflow doesn't appear to have new descriptions. Sync anyway?",
                    "Sync from Workflow"):
                    return
    
    # Perform sync (similar to Import Workflow but with merge logic)
    # ... implementation details ...
    
    show_info(self, f"Sync complete:\n  New descriptions: {n}\n  New images: {m}")
```

**Files Modified:**
- `imagedescriber/data_models.py` - Extend ImageWorkspace
- `imagedescriber/imagedescriber_wx.py` - Add sync method and menu

**Testing:**
- Save workspace with viewer state → reload → verify restoration prompt
- Re-sync from workflow → verify new descriptions merged
- Edit description → re-sync → verify edit preserved
- Workflow directory moved/deleted → verify graceful handling

**Risk:** Medium - Merge logic must preserve user edits carefully

---

### Phase 4: idt Integration (Long-Term - v5.0.0)

**Goal:** Native .idw workspace creation from idt workflow command

#### Design Principles

1. **Backward Compatibility**: Text output remains default and primary
2. **Opt-In**: Workspace creation is optional via flag
3. **No Behavior Change**: Existing idt workflows unchanged
4. **Dual Output**: Can generate both text and workspace

#### Command-Line Interface

**New Flag:** `--create-workspace` or `-w`

```bash
# Traditional (text only)
idt workflow /path/to/images --model gpt-4o --prompt detailed

# With workspace creation
idt workflow /path/to/images --model gpt-4o --prompt detailed --create-workspace

# Workspace only (no text file)
idt workflow /path/to/images --model gpt-4o --prompt detailed --create-workspace --no-text-output
```

**Output Structure:**

```
wf_2026-02-10_143000_gpt4o_detailed/
  ├── input_images/          # Hardlinked or copied source images
  ├── descriptions/
  │   ├── image_descriptions.txt        # Traditional text output
  │   └── file_path_mapping.json        # Path resolution helper
  ├── logs/
  │   └── image_describer_progress.txt  # Progress tracking
  ├── html_reports/          # HTML output (if --steps includes html)
  ├── workspace.idw          # NEW: Native workspace file
  └── workflow_metadata.json # Existing metadata
```

#### workspace.idw Contents

Generated workspace includes:

```json
{
  "version": "3.1",
  "directory_paths": ["/path/to/original/images"],
  "items": {
    "/path/to/original/image.jpg": {
      "file_path": "/path/to/original/image.jpg",
      "item_type": "image",
      "descriptions": [{
        "text": "Generated description...",
        "model": "gpt-4o",
        "prompt_style": "detailed",
        "provider": "openai",
        "created": "2026-02-10T14:30:00",
        "metadata": {
          "exif": { /* extracted metadata */ },
          "location": { /* geocoded data */ }
        }
      }]
    }
  },
  "viewer_state": {
    "workflow_dir": "/path/to/wf_2026-02-10_...",
    "import_timestamp": "2026-02-10T14:30:05",
    "live_mode_was_active": false
  },
  "created": "2026-02-10T14:30:05",
  "modified": "2026-02-10T14:30:05"
}
```

**Key Features:**

1. **Source Paths**: Uses original image paths, not workflow temp copies
2. **Full Metadata**: Includes EXIF, GPS, tokens, costs, timing
3. **Immediately Editable**: Can be opened in ImageDescriber GUI
4. **Viewer State**: Tracks workflow directory for potential re-runs
5. **Multi-Directory**: Supports multiple source directories correctly

#### Implementation in idt/workflow.py

**Add to argument parser:**

```python
parser.add_argument(
    '--create-workspace', '-w',
    action='store_true',
    help='Create .idw workspace file in addition to text descriptions'
)

parser.add_argument(
    '--no-text-output',
    action='store_true',
    help='Skip creating text description file (requires --create-workspace)'
)
```

**Add to WorkflowOrchestrator:**

```python
def _generate_workspace_file(self, output_dir: Path, metadata: dict) -> None:
    """
    Generate .idw workspace file from workflow results.
    
    Reads descriptions from text file or progress tracking,
    resolves paths to original source images,
    creates fully-formed ImageDescriber workspace.
    """
    from data_models import ImageWorkspace, ImageItem, ImageDescription
    import json
    
    workspace = ImageWorkspace(new_workspace=True)
    
    # Add source directory
    source_dir = metadata.get('input_directory')
    if source_dir:
        workspace.add_directory(source_dir)
    
    # Parse descriptions file
    desc_file = output_dir / "descriptions" / "image_descriptions.txt"
    if not desc_file.exists():
        self.logger.warning("No descriptions file found, creating empty workspace")
        workspace_path = output_dir / "workspace.idw"
        workspace.save_to_file(str(workspace_path))
        return
    
    # Load path mapping if available
    mapping_file = output_dir / "descriptions" / "file_path_mapping.json"
    path_mapping = {}
    if mapping_file.exists():
        with open(mapping_file, 'r') as f:
            path_mapping = json.load(f)
    
    # Parse descriptions (reuse existing parser)
    from viewer_components import WorkflowParser
    entries = WorkflowParser.parse_file(desc_file)
    
    for entry in entries:
        # Resolve to original path
        temp_path = entry.get('file_path', '')
        original_path = path_mapping.get(temp_path, temp_path)
        
        if not Path(original_path).exists():
            self.logger.warning(f"Image not found: {original_path}")
            continue
        
        # Create ImageItem
        item = ImageItem(original_path, 'image')
        
        # Create ImageDescription with full metadata
        desc = ImageDescription(
            text=entry.get('description', ''),
            model=entry.get('model', metadata.get('model', '')),
            prompt_style=entry.get('prompt_style', metadata.get('prompt_style', '')),
            provider=entry.get('provider', metadata.get('provider', '')),
            metadata=entry.get('metadata', {})
        )
        
        item.add_description(desc)
        workspace.add_item(item)
    
    # Set viewer state for future reference
    workspace.set_viewer_state(output_dir, live_mode=False)
    
    # Save workspace
    workspace_path = output_dir / "workspace.idw"
    workspace.save_to_file(str(workspace_path))
    
    self.logger.info(f"Workspace created: {workspace_path}")
    self.logger.info(f"  Images: {len(workspace.items)}")
    self.logger.info(f"  Total descriptions: {sum(len(item.descriptions) for item in workspace.items.values())}")
```

**Call in run_workflow():**

```python
# After description step completes
if args.create_workspace:
    self._generate_workspace_file(output_dir, workflow_metadata)
```

**Files Modified:**
- `scripts/workflow.py` - Add workspace generation
- `idt/idt_cli.py` - Add arguments
- May need to import from imagedescriber (carefully, respecting frozen mode)

**Testing:**
- Run workflow with -w → verify both text and .idw created
- Open .idw in ImageDescriber → verify all images and descriptions present
- Verify paths resolve to original images, not temp copies
- Test with multi-directory workflows
- Test --no-text-output mode

**Risk:** Medium-High
- Need to handle imports carefully in frozen mode
- Path resolution must be robust
- Additional output increases workflow disk usage
- Must not break existing workflows

---

## Migration Path

### For Users

**Immediate (Phase 1):**
- Existing workflows: No change in behavior
- Viewer mode: More predictable (can't accidentally save wrong thing)

**Phase 2:**
- Can convert viewed workflows to workspaces easily
- Workflow: View → Convert → Edit → Save (3 steps vs many)

**Phase 3:**
- Workspaces remember their workflow source
- Can re-sync if workflow re-run with more images

**Phase 4:**
- New workflows auto-create .idw files (if --create-workspace used)
- Immediately editable without conversion

### For Developers

**Phase 1:** UI/menu changes only, no data model impact

**Phase 2:** 
- New conversion logic, reuses existing path resolution
- Extends viewer functionality, no breaking changes

**Phase 3:**
- Extends .idw format (backward compatible via optional field)
- Old workspaces load normally, just don't have viewer_state

**Phase 4:**
- idt workflow extended, but existing behavior unchanged
- May need refactoring to share code between CLI and GUI

---

## Implementation Order

### Priority 1 (v4.1.1 - Next Sprint)
- Phase 1: Safety improvements
- Estimated: 2-3 days

### Priority 2 (v4.2.0 - Following Sprint)  
- Phase 2: Convert to Workspace
- Estimated: 5-7 days (path resolution is complex)

### Priority 3 (v4.3.0 - Future)
- Phase 3: Workspace-aware viewing
- Estimated: 4-5 days

### Priority 4 (v5.0.0 - Long-term)
- Phase 4: idt integration
- Estimated: 7-10 days (testing in frozen mode, cross-platform)

---

## Open Questions

1. **Viewer State Persistence**: Should we always save viewer_state when using Convert to Workspace, or make it optional?

2. **Path Resolution Conflicts**: If multiple images have same filename in different directories, how to disambiguate in conversion?

3. **Live Mode Sync**: Should live mode conversion poll periodically and auto-update workspace? Or require manual refresh?

4. **Workspace Merge Strategy**: If workspace already has descriptions and you sync from workflow, how to handle conflicts?
   - Keep both (multiple descriptions per image)
   - Prefer user edits
   - Prefer workflow (fresher data)
   - Ask user per conflict

5. **Performance**: For workflows with 1000+ images, conversion could be slow. Need progress dialog? Background thread?

6. **CLI Flag Naming**: `--create-workspace` vs `--workspace` vs `-w` - which is clearest?

7. **Memory Usage**: Having both viewer entries and workspace items in memory could be wasteful. Should viewer mode clear workspace when loading directory?

---

## Success Metrics

**Phase 1:**
- Zero reports of "saved workspace but it's empty"
- User feedback: clearer mode distinctions

**Phase 2:**
- Conversion success rate > 95% (path resolution works)
- User workflow time reduced: View → Edit from 5+ steps to 2 steps
- Positive feedback on feature discoverability

**Phase 3:**
- Users re-sync from workflows (feature usage tracked)
- No reports of lost edits during sync

**Phase 4:**
- Adoption rate of --create-workspace flag
- File size comparison (text vs .idw)
- No regression in idt workflow performance or reliability

---

## Documentation Updates

**Phase 1:**
- Update USER_GUIDE.md: Explain viewer vs editor modes
- Add troubleshooting: "Why is Save disabled?"

**Phase 2:**
- Document Convert to Workspace feature
- Add workflow: "Editing workflow results"
- Screenshots/demo

**Phase 3:**
- Document sync feature
- Explain viewer state in .idw format

**Phase 4:**
- Update CLI_REFERENCE.md with new flags
- Document workspace creation in workflow guide
- Compare text vs .idw outputs

---

## Related Issues

- Will be linked when issue is created

---

## Changelog

- 2026-02-10: Initial plan created
