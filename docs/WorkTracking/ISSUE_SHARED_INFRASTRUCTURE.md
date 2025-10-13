# Issue: Resolve Shared Infrastructure in IDT Apps

**Created**: October 12, 2025  
**Priority**: Medium  
**Target**: Post v1.0 Release (v1.1 or v2.0)  
**Status**: Investigation Complete, Solution Pending

---

## Problem Statement

The Image Description Toolkit has evolved into four separate applications (IDT, Viewer, Prompt Editor, ImageDescriber), but the original design assumed shared configuration and prompt files. With PyInstaller creating standalone executables, each app now has isolated, frozen copies of resources, breaking the intended cross-app integration.

### What Works vs. What Doesn't

| Scenario | Works? | Why/Why Not |
|----------|--------|-------------|
| Edit prompts in source, rebuild all apps | ✅ Yes | Changes baked into new builds |
| Run Prompt Editor.exe, edit prompts | ⚠️ Partial | Edits external files, but... |
| Other .exe files see prompt changes | ❌ No | They use bundled copies |
| Run apps from source (python) | ✅ Yes | All share actual `models/` and `scripts/` |
| IDT standalone | ✅ Yes | Complete, self-contained |
| Viewer standalone | ✅ Yes | Can view workflows, redescribe with bundled scripts |
| ImageDescriber standalone | ✅ Yes | Can process images with bundled prompts |
| Prompt Editor affects other apps | ❌ No | Edits external files that executables can't see |
| Shared configuration between apps | ❌ No | Each app has bundled configs from build time |
| Dynamic prompt updates | ❌ No | Would need to rebuild executables |

---

## Technical Analysis

### Shared Resources

#### 1. Prompt Files (`models/*_prompts.json`)
**Location**: `models/claude_prompts.json`, `models/openai_prompts.json`, `models/ollama_prompts.json`

**Used by**:
- IDT (idt.exe) - bundled in executable via `final_working.spec`
- ImageDescriber - bundled in executable
- Viewer (redescribe feature) - bundled with `--add-data`
- Prompt Editor - edits these files

**Current Problem**:
- Each executable has its OWN copy of prompts bundled at build time
- Prompt Editor edits files in the USER'S repository/installation
- Those edits won't affect already-built executables (they have frozen copies)

#### 2. Scripts Directory
**Location**: `scripts/` with `image_describer.py`, `workflow.py`, etc.

**Used by**:
- IDT - bundled
- Viewer (redescribe feature) - bundled with `--add-data "../scripts;scripts"`
- ImageDescriber - bundled with `--add-data`

**Current Problem**: Each has a frozen copy from build time

#### 3. Configuration Files
**Location**:
- `scripts/workflow_config.json`
- `scripts/image_describer_config.json`
- `scripts/video_frame_extractor_config.json`

**Current Problem**: Each executable has bundled copies from build time

### How Prompt Editor Currently Works

From `prompt_editor/prompt_editor.py`:

```python
def find_config_file(self):
    """Find the image_describer_config.json file"""
    # Look in scripts directory relative to current location
    possible_paths = [
        Path("scripts/image_describer_config.json"),
        Path("../scripts/image_describer_config.json"),
        Path("./image_describer_config.json"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path.resolve()
    
    # If not found, default to scripts directory
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    return scripts_dir / "image_describer_config.json"
```

**Problem**: Looks for files relative to CWD, not in bundled resources of other apps.

### The Architectural Conflict

**Original Design Assumption**:
- **Source mode**: All apps share `models/` and `scripts/` directories
- **Prompt Editor**: Edits shared files, all apps see changes immediately
- **Dynamic system**: Change prompts once, affects all tools

**PyInstaller Reality**:
- **Executable mode**: Each app is isolated with frozen resources at `sys._MEIPASS`
- **Prompt Editor**: Edits files that executables can't see
- **Static system**: Changes require rebuilding executables

---

## Proposed Solutions

### Option 1: External Resource Directory ⭐ RECOMMENDED FOR FUTURE

Make executables look for prompts/configs in external locations:

```python
# Check external location first, fall back to bundled
EXTERNAL_PROMPTS = Path.home() / "AppData/Local/ImageDescriptionToolkit/prompts"
EXTERNAL_CONFIGS = Path.home() / "AppData/Local/ImageDescriptionToolkit/configs"

if EXTERNAL_PROMPTS.exists():
    load_from(EXTERNAL_PROMPTS)
else:
    # First run: copy bundled defaults to external location
    initialize_external_resources()
    load_from(EXTERNAL_PROMPTS)
```

**Directory Structure**:
```
C:/Users/<user>/AppData/Local/ImageDescriptionToolkit/
├── prompts/
│   ├── claude_prompts.json
│   ├── openai_prompts.json
│   └── ollama_prompts.json
├── configs/
│   ├── workflow_config.json
│   └── image_describer_config.json
└── logs/
```

**Pros**:
- ✅ Prompt Editor edits shared location
- ✅ All executables read from same place
- ✅ User can customize without rebuilding
- ✅ Matches user expectations
- ✅ Follows enterprise software patterns
- ✅ Centralized, predictable location

**Cons**:
- ❌ Code changes needed in all apps
- ❌ More complex resource loading
- ❌ Need first-run initialization logic
- ❌ Need to handle missing/corrupted external files

**Implementation Checklist**:
- [ ] Define shared resource paths (AppData location)
- [ ] Create resource initialization on first run
- [ ] Update all apps to check external location first
- [ ] Add fallback to bundled resources
- [ ] Update Prompt Editor to save to shared location
- [ ] Add validation/recovery for corrupted external files
- [ ] Update documentation
- [ ] Test cross-app integration

---

### Option 2: Rebuild Workflow

Keep current architecture, document that changes require rebuilds.

**Documentation**:
```markdown
## Customizing Prompts

After editing prompts with Prompt Editor, rebuild applications to use new prompts:
1. Edit prompts with Prompt Editor
2. Run releaseitall.bat to rebuild all apps
3. Distribute new executables

Note: Prompts are frozen into executables at build time.
```

**Pros**:
- ✅ No code changes required
- ✅ Simple to understand
- ✅ Works with current design

**Cons**:
- ❌ Not user-friendly
- ❌ Can't distribute Prompt Editor to end users
- ❌ Defeats purpose of having a Prompt Editor
- ❌ High friction for customization

---

### Option 3: Hybrid Approach (CURRENT PLAN FOR v1.0)

**Strategy**:
- IDT, Viewer, ImageDescriber: Standalone with bundled resources
- Prompt Editor: Developer tool only (not distributed to end users)
- Document: "Prompt Editor is for developers creating custom builds"

**Pros**:
- ✅ Clear separation of concerns
- ✅ Developers can customize, rebuild, distribute
- ✅ End users get pre-configured executables
- ✅ No code changes needed for v1.0
- ✅ Gets us to release faster

**Cons**:
- ⚠️ Limits Prompt Editor usefulness for end users
- ⚠️ Can't let end users customize prompts easily
- ⚠️ Temporary solution

**Implementation for v1.0**:
- [x] Keep Prompt Editor as development tool
- [x] Document in developer guide
- [ ] Update README to clarify tool purpose
- [ ] Consider removing from packageitall.bat (don't distribute yet)

---

### Option 4: Config File Editing Instructions

For v1.0, provide clear instructions for manual config editing:

**Documentation**:
```markdown
## Customizing AI Prompts (Advanced Users)

You can edit prompts by modifying configuration files in your IDT installation:

### Location
- `scripts/image_describer_config.json`

### Steps
1. Open the file in a text editor (Notepad, VS Code, etc.)
2. Find the "prompts" section
3. Edit prompt text while maintaining JSON structure
4. Save the file
5. Restart IDT/Viewer to use new prompts

### Example
{
  "prompts": {
    "default": "Describe this image in detail.",
    "technical": "Provide a technical analysis of this image.",
    "custom": "Your custom prompt here."
  }
}

Note: Be careful with JSON syntax. Invalid JSON will prevent the application from starting.
```

**Pros**:
- ✅ Works with current architecture
- ✅ No code changes
- ✅ Power users can customize
- ✅ Simple documentation

**Cons**:
- ⚠️ Requires technical knowledge
- ⚠️ Risk of JSON syntax errors
- ⚠️ Not beginner-friendly

---

## Decision for v1.0 Release

**Chosen Approach**: **Option 3 (Hybrid) + Option 4 (Manual Editing)**

**Reasoning**:
- Focus on releasing IDT and Viewer (they work well together)
- Users can manually edit config files if needed
- Prompt Editor and ImageDescriber need more work anyway
- Buys time to implement Option 1 properly in v2.0

**v1.0 Distribution Plan**:
1. ✅ Distribute: IDT (main CLI toolkit)
2. ✅ Distribute: Viewer (workflow browser)
3. ❌ Don't distribute yet: Prompt Editor (developer tool, needs external resource implementation)
4. ❌ Don't distribute yet: ImageDescriber (needs more work + external resource implementation)

**Documentation Updates Needed**:
- [ ] Add "Advanced: Editing Config Files" section to USER_GUIDE.md
- [ ] Mark Prompt Editor as "Developer Tool (v2.0 Coming Soon)" in README
- [ ] Add note in Viewer docs: "Prompts are frozen at build time, can be edited manually"
- [ ] Create developer guide for customizing and rebuilding

---

## Roadmap for v2.0

**Goal**: Implement **Option 1 (External Resource Directory)**

### Phase 1: Design
- [ ] Define exact AppData structure
- [ ] Design first-run initialization flow
- [ ] Design resource validation/recovery
- [ ] Create migration plan from v1.0 to v2.0

### Phase 2: Implementation
- [ ] Implement shared resource loader utility
- [ ] Update IDT to use external resources
- [ ] Update Viewer to use external resources
- [ ] Update ImageDescriber to use external resources
- [ ] Update Prompt Editor to edit shared location

### Phase 3: Testing
- [ ] Test first-run initialization
- [ ] Test cross-app integration
- [ ] Test prompt changes affecting all apps
- [ ] Test corrupted file recovery
- [ ] Test migration from v1.0

### Phase 4: Documentation
- [ ] Update user guide with shared resources
- [ ] Update developer guide
- [ ] Create migration guide for v1.0 users

---

## Alternative: Per-App Customization

**Another approach**: Accept that apps are independent, allow per-app customization

**Strategy**:
- Each app has its own config in AppData
- Prompt Editor becomes "multi-app editor" that can edit configs for any app
- User chooses which app's config to edit

**Example**:
```
C:/Users/<user>/AppData/Local/ImageDescriptionToolkit/
├── IDT/
│   ├── prompts.json
│   └── config.json
├── Viewer/
│   ├── prompts.json
│   └── config.json
└── ImageDescriber/
    ├── prompts.json
    └── config.json
```

**Pros**:
- ✅ Each app fully independent
- ✅ Can customize per-app without affecting others
- ✅ Clearer separation of concerns

**Cons**:
- ❌ More redundancy
- ❌ Must edit prompts in multiple places for consistency
- ❌ More disk space

---

## Testing Checklist (For Chosen Solution)

When implementing Option 1:

**Initialization Tests**:
- [ ] First run creates AppData directory
- [ ] Bundled defaults copied to AppData
- [ ] Permissions are correct

**Integration Tests**:
- [ ] IDT reads from external prompts
- [ ] Viewer reads from external prompts
- [ ] ImageDescriber reads from external prompts
- [ ] Prompt Editor saves to external location
- [ ] All apps see same prompt changes

**Fallback Tests**:
- [ ] Missing external file falls back to bundled
- [ ] Corrupted external file falls back to bundled
- [ ] Invalid JSON handled gracefully

**Migration Tests**:
- [ ] v1.0 users can migrate to v2.0
- [ ] Manual edits preserved during migration

---

## Related Issues

- None yet (this is the first comprehensive investigation)

## Related Documentation

- `tools/INVENTORY.md` - Tools documentation
- `BUILD_AND_PACKAGE_GUIDE.md` - Build system documentation
- `docs/archive/AI_AGENT_REFERENCE.md` - Technical reference

---

## Discussion Notes

**Kelly (October 12, 2025)**:
> "The way this project has come together, we might have painted ourselves into a bit of a corner. Some of the configuration files and maybe scripts work between apps. For example, the prompteditor was intended to make new prompts that would appear in imagedescriber, viewer and be supported by idt. But is any of that going to work with these built versions?"

**Analysis Result**: No, cross-app configuration sharing does not work with current PyInstaller-based builds. Each executable has frozen, isolated copies of all resources.

**Kelly (October 12, 2025)**:
> "For now I'm focusing on releasing the scripts and viewer. Those work well together and if a user wants a new prompt for now, they can edit the config file. PromptEditor and ImageDescriber are close but need some more work. So this is a good time to figure this all out."

**Decision**: Ship v1.0 with IDT + Viewer. Document manual config editing. Implement proper shared infrastructure in v2.0.

---

## Next Steps

**Immediate (v1.0)**:
1. Update packageitall.bat to skip Prompt Editor
2. Document manual config editing in USER_GUIDE.md
3. Add developer note about Prompt Editor
4. Ship IDT + Viewer as planned

**Post-Release (v1.1/v2.0)**:
1. Implement Option 1 (External Resource Directory)
2. Full cross-app integration testing
3. Distribute all four applications

---

**Issue Author**: AI Assistant  
**Reporter**: Kelly Ford  
**Last Updated**: October 12, 2025
