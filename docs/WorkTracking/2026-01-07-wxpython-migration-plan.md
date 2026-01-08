# wxPython Migration Plan
**Date:** January 7, 2026
**Objective:** Migrate all 4 GUI applications from PyQt6 to wxPython for better macOS VoiceOver accessibility

## Migration Scope

### Applications to Migrate
1. **viewer** (2146 lines) - ✅ COMPLETE (viewer_wx_full.py)
2. **prompteditor** (1119 lines) - Simplest remaining
3. **idtconfigure** (859 lines) - Medium complexity
4. **imagedescriber** (10,524 lines) - Most complex

### Total Lines: 14,648 lines of PyQt6 code

## Phase 1: Discovery & Analysis (IN PROGRESS)

### Files Read Completely
- ✅ idtconfigure/idtconfigure.py (859 lines)
- ✅ prompt_editor/prompt_editor.py (1119 lines) 
- ⏳ imagedescriber/imagedescriber.py (10,524 lines) - Reading in progress
- ⏳ viewer/viewer.py (2146 lines) - Will re-read for shared pattern extraction

### Key Findings from IDTConfigure

**File:** idtconfigure/idtconfigure.py (859 lines)

**Purpose:** GUI for editing three JSON config files:
- `image_describer_config.json`
- `video_frame_extractor_config.json`
- `workflow_config.json`

**Structure:**
- `SettingEditDialog` - Modal dialog for editing individual settings with type-specific editors (bool, int, float, choice, string)
- `IDTConfigureApp` - Main window with:
  - Menu bar (File, Settings categories, Help)
  - Settings list (QListWidget) - LEFT PANEL
  - Explanation text (QTextEdit read-only) - RIGHT PANEL
  - Change button to open edit dialog

**Key Components:**
1. **Settings Metadata** - Hardcoded dictionary defining all editable settings organized by category:
   - AI Model Settings
   - Prompt Styles
   - Video Extraction
   - Processing Options
   - Metadata Settings
   - Workflow Settings
   - Output Format

2. **Path Resolution** - Uses `find_scripts_directory()`:
   - Checks frozen (PyInstaller) vs script mode
   - Looks for `scripts/` subdirectory
   - Fallback to current directory

3. **Settings Navigation:**
   - Each setting has: file, path (nested JSON keys), type, description, optional range/choices
   - Get/Set methods navigate nested JSON using path array
   - Updates are in-memory until explicit Save

**File Paths Referenced:**
- `scripts/image_describer_config.json`
- `scripts/video_frame_extractor_config.json`
- `scripts/workflow_config.json`

**Key UX Patterns:**
- Menu-driven category selection
- Arrow key navigation of settings list
- Single-click focus changes (no manual refresh)
- Modal dialog for editing
- Export/Import full config
- Backup/Restore functionality

**NO External Dependencies on Scripts:**
- Pure config file editor
- No imports from `scripts/` or `imagedescriber/` packages
- Self-contained logic

### Key Findings from Prompt Editor

**File:** prompt_editor/prompt_editor.py (1119 lines)

**Purpose:** Visual editor for prompt templates in `image_describer_config.json`

**Structure:**
- `PromptEditorMainWindow` - Single main window with:
  - LEFT PANEL: Prompt list, Add/Delete/Duplicate buttons, Default settings, Actions
  - RIGHT PANEL: Name editor, Text editor with character count

**Key Components:**
1. **Prompt Management:**
   - List all prompt variations
   - Add new prompts with default template
   - Delete prompts (with default update logic)
   - Duplicate prompts (auto-numbered copies)
   - Edit prompt name and text independently

2. **AI Provider Support:**
   - Provider combo: ollama, openai, claude
   - Model discovery (different logic per provider)
   - API key field (hidden for ollama)
   - Toggle show/hide API key

3. **Configuration:**
   - `default_prompt_style` - Which prompt to use
   - `default_provider` - Which AI service
   - `default_model` - Which model within provider
   - `api_key` - Optional API key storage
   - `prompt_variations` - Dictionary of name→text

**File Paths Referenced:**
- `scripts/image_describer_config.json` (primary)
- Supports opening any JSON file via dialog

**External Dependencies:**
- `ollama` package (optional, for model discovery)
- `imagedescriber.ai_providers` - OllamaProvider, OpenAIProvider, ClaudeProvider (optional)
- `scripts.versioning` - log_build_banner, get_full_version (optional)

**Key UX Patterns:**
- Auto-save removed (was causing unwanted saves)
- Explicit Save/Save As only
- Modified state tracking with `*` in title
- Real-time character count
- Case-insensitive prompt name lookup
- Tab order set explicitly for accessibility
- Keyboard shortcuts: Ctrl+N, Ctrl+S, Ctrl+Shift+S, Ctrl+O, F5, Ctrl+D, Delete

**Accessibility Features:**
- `setAccessibleName()` and `setAccessibleDescription()` on all inputs
- `setTabChangesFocus(True)` on text editor
- Focus visibility styling (blue border on focus)

### Key Findings from ImageDescriber (Preliminary)

**File:** imagedescriber/imagedescriber.py (10,524 lines!)

**Classes Identified (20+):**
1. `AccessibleTreeWidget` - Custom tree with accessibility
2. `AccessibleNumericInput` - Numeric input with validation
3. `AccessibleTextEdit` - Text editor with accessibility
4. `ImageDescription` - Data class for description metadata
5. `ImageItem` - Data class for image with path/description
6. `ImageWorkspace` - Manages collection of images
7. `ProcessingWorker` - QThread for batch AI processing
8. `WorkflowProcessWorker` - QThread for workflow orchestration
9. `ConversionWorker` - QThread for HEIC→JPG conversion
10. `VideoProcessingWorker` - QThread for video frame extraction
11. `ChatProcessingWorker` - QThread for interactive chat mode
12. `DirectorySelectionDialog` - File/folder picker
13. `WorkspaceDirectoryManager` - Workspace directory management
14. `ProcessingDialog` - Main batch processing UI
15. `ChatDialog` - Interactive chat with AI
16. `ChatWindow` - Extended chat interface
17. `VideoProcessingDialog` - Video frame extraction UI
18. `AllDescriptionsDialog` - View all descriptions
19. `ModelManagerDialog` - Manage AI models
20. More classes likely...

**Architecture Pattern:**
- Main application window (likely `ImageDescriberApp` or similar)
- Multiple QThread workers for async operations
- Custom accessible widgets (TreeWidget, NumericInput, TextEdit)
- Multiple modal dialogs for different features

**Concerns:**
- 10k+ lines suggests significant duplication potential
- Many specialized dialogs (opportunity for shared components)
- Multiple worker threads (need careful wxPython thread handling)
- Complex UI likely has duplicate layout code

## Known File Paths & Constants to Document

### From IDTConfigure:
- `scripts/image_describer_config.json`
- `scripts/video_frame_extractor_config.json`
- `scripts/workflow_config.json`

### From PromptEditor:
- `scripts/image_describer_config.json`
- Backup suffix: `.bak`
- Backup naming: `image_describer_config_backup_{timestamp}.json`

### From Viewer (Already Migrated):
- `descriptions/image_descriptions.txt` ✅ FIXED
- `workflow_metadata.json`

## Shared Component Opportunities

### Common Dialogs (All Apps):
1. **File/Directory Pickers** - Open/Save dialogs with filters
2. **Message Boxes** - Info, Warning, Error, Question
3. **About Dialog** - Application info
4. **Help Dialog** - User guidance
5. **Confirmation Dialogs** - Save changes? Delete? Overwrite?

### Common Widgets (From ImageDescriber):
1. **Accessible Widgets** - Custom focus/screen reader support
2. **Progress Indicators** - For background tasks
3. **Status Bar** - Bottom status messages
4. **Settings Editors** - Different types (bool, int, float, choice, string)

### Common Patterns:
1. **Config File Loading** - JSON read/write with error handling
2. **Path Resolution** - Frozen vs dev mode, scripts/ directory finding
3. **Modified State Tracking** - Unsaved changes detection
4. **Window Title Updates** - Show filename and modified state
5. **Threading** - Background workers for long operations

## Migration Strategy

### Shared Library Design (wx_shared.py):

```python
# Dialogs
class WxFileDialog - Enhanced file/directory selection
class WxMessageBox - Standardized message dialogs  
class WxAboutDialog - Reusable about box
class WxConfirmDialog - Save/Delete/Overwrite confirmations

# Widgets
class WxAccessibleList - List with proper VoiceOver support
class WxAccessibleText - Text field with accessibility
class WxSettingEditor - Generic setting editor (type-aware)
class WxStatusBar - Standard status bar with messages

# Utilities
def find_scripts_dir() - Unified path resolution
def load_json_config(filename) - Config loading with error handling
def save_json_config(filename, data) - Config saving with backup
def format_timestamp() - Consistent date formatting
class ModifiedStateTracker - Mixin for unsaved changes

# Threading
class WxWorkerThread - Base class for background tasks
def run_in_background(func) - Decorator for async operations
```

### Migration Order Rationale:

1. **Viewer** - ✅ DONE - Established wxPython patterns
2. **PromptEditor** - NEXT - Simpler, good for testing shared library
3. **IDTConfigure** - AFTER - Medium complexity, tests setting editors
4. **ImageDescriber** - LAST - Most complex, benefits from all learned patterns

## Next Steps

1. ✅ Finish reading imagedescriber.py completely
2. ✅ Document all file paths and constants via grep
3. ✅ Identify duplicate code patterns in imagedescriber
4. Create wx_shared.py with common components
5. Migrate prompteditor (test shared library)
6. Migrate idtconfigure (test setting editors)
7. Migrate imagedescriber (apply all patterns)
8. Refactor viewer to use wx_shared.py
9. Build and test all 4 apps
10. Create documentation

## Success Criteria

- All 4 apps launch and function identically to PyQt6 versions
- VoiceOver works perfectly on macOS (Tab navigation, item announcement)
- No regressions in functionality
- Shared library eliminates code duplication
- Build scripts work for all 4 apps
- Comprehensive test coverage

## Risks & Mitigations

**Risk:** Breaking existing functionality during migration
**Mitigation:** Keep PyQt6 versions, thorough testing, feature checklist

**Risk:** wxPython threading model different from PyQt6
**Mitigation:** Review wxPython threading docs, test all background operations

**Risk:** 10k+ line imagedescriber too complex to migrate accurately
**Mitigation:** Break into smaller tasks, comprehensive testing, find/eliminate duplicates first

**Risk:** Missing subtle behaviors or edge cases
**Mitigation:** READ COMPLETE FILES, no assumptions, grep for all paths

## Notes for AI Agent

### Critical Reminders:
- ✅ Read COMPLETE files - no skimming
- ✅ Grep for ALL file paths before coding
- ✅ Check for existing patterns in scripts/
- ✅ Test builds after each app
- ✅ No assumptions about filenames (learned lesson: `image_descriptions.txt` not `descriptions.txt`)
- ✅ Find duplicate code patterns
- ✅ Extract to shared library when possible
- ✅ Preserve ALL functionality

### Lessons from Viewer Migration:
1. Wrong filename (`descriptions.txt` vs `image_descriptions.txt`) - GREP FIRST!
2. PyQt6 has poor VoiceOver support - wxPython superior
3. Tab navigation critical for accessibility
4. Build and test immediately after coding
5. Directory listing in error messages helps debugging
