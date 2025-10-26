# GitHub Issue: Handle Proper Install on Windows

**Title:** Handle proper install on Windows - Support standard file locations

**Labels:** enhancement, windows, architecture

---

## Problem

The current v3.0.1 installer installs everything to `C:\idt\`, which works but doesn't follow Windows best practices for file organization. This leads to several issues:

### Current Issues

1. **Configuration Files in Install Directory**
   - Prompts and configs are in `C:\idt\scripts\`
   - Users need write access to edit prompts via Prompt Editor
   - Works now (C:\idt is writable), but fragile

2. **Workflow/Description Folders Scattered**
   - `idt` creates workflow directories wherever the user runs it
   - Results in description folders scattered across user's filesystem
   - No central location to find all previous workflows
   - Makes backup/sync difficult

3. **No User Data Separation**
   - Program files mixed with user data
   - Updates might overwrite user customizations
   - Uninstall unclear about what data to keep

4. **PATH Dependency**
   - CLI requires adding to PATH to be useful
   - Otherwise users must run from `C:\idt\` or specify full path

## Windows Best Practices

According to Microsoft guidelines, applications should use:

### Program Files
- **Location:** `C:\Program Files\ImageDescriptionToolkit\`
- **Contents:** Executables, DLLs, read-only resources
- **Permissions:** Read-only for users, write for admin/installer
- **Purpose:** Application binaries only

### AppData\Roaming
- **Location:** `%APPDATA%\ImageDescriptionToolkit\`
- **Full Path:** `C:\Users\<username>\AppData\Roaming\ImageDescriptionToolkit\`
- **Contents:** User settings, custom prompts, configuration files
- **Permissions:** Full read/write for user
- **Purpose:** User-specific settings that should roam with user profile
- **Synced:** Yes (in domain environments)

### AppData\Local
- **Location:** `%LOCALAPPDATA%\ImageDescriptionToolkit\`
- **Full Path:** `C:\Users\<username>\AppData\Local\ImageDescriptionToolkit\`
- **Contents:** Cache, temp files, logs
- **Permissions:** Full read/write for user
- **Purpose:** Machine-specific data
- **Synced:** No

### Documents
- **Location:** `%USERPROFILE%\Documents\ImageDescriptionToolkit\`
- **Full Path:** `C:\Users\<username>\Documents\ImageDescriptionToolkit\`
- **Contents:** User-created workflows, description outputs
- **Permissions:** Full read/write for user
- **Purpose:** User's actual work product
- **Synced:** Often (via OneDrive, etc.)

## Proposed Architecture

### File Organization

```
C:\Program Files\ImageDescriptionToolkit\
├── idt.exe                      (main CLI)
├── LICENSE
├── docs\                        (read-only documentation)
├── Viewer\
│   └── viewer.exe
├── ImageDescriber\
│   └── imagedescriber.exe
└── PromptEditor\
    └── prompteditor.exe

%APPDATA%\ImageDescriptionToolkit\
├── settings.json                (user preferences)
├── prompts\                     (custom prompts)
│   ├── default.txt
│   ├── detailed.txt
│   └── custom\
└── api_keys\                    (encrypted API keys)
    ├── openai.key
    └── anthropic.key

%LOCALAPPDATA%\ImageDescriptionToolkit\
├── cache\                       (model cache, temp files)
├── logs\                        (application logs)
└── tmp\                         (temporary processing)

%USERPROFILE%\Documents\ImageDescriptionToolkit\
└── workflows\                   (default workflow location)
    ├── 2025-10-24_ProjectA\
    ├── 2025-10-23_Vacation\
    └── ...
```

### Configuration Search Order

Applications should search for configs in this order:
1. Current working directory (for workflow-specific overrides)
2. `%APPDATA%\ImageDescriptionToolkit\` (user customizations)
3. `C:\Program Files\ImageDescriptionToolkit\` (defaults)

### Workflow Directory Options

Users should be able to specify where workflows are created:

**Option 1: Current Directory (Current Behavior)**
```bash
cd C:\Users\kelly\Pictures\Vacation
idt guideme
# Creates: C:\Users\kelly\Pictures\Vacation\<workflow_timestamp>\
```

**Option 2: Central Workflows Directory (New)**
```bash
idt guideme --workflow-dir default
# Creates: %USERPROFILE%\Documents\ImageDescriptionToolkit\workflows\<timestamp>\
```

**Option 3: Explicit Path**
```bash
idt guideme --workflow-dir "D:\Projects\MyImages"
# Creates: D:\Projects\MyImages\<workflow_timestamp>\
```

## Implementation Plan

### Phase 1: Configuration Migration (v3.1)

1. **Config File Discovery**
   - Add function to search multiple locations
   - Migrate hardcoded `scripts/` references
   - Test with both development and installed environments

2. **First-Run Setup**
   - On first launch, copy default prompts to `%APPDATA%\ImageDescriptionToolkit\prompts\`
   - Create default settings file
   - Show welcome dialog explaining file locations

3. **Prompt Editor Updates**
   - Update to read/write from `%APPDATA%\ImageDescriptionToolkit\prompts\`
   - Keep fallback to read-only defaults in Program Files

### Phase 2: Workflow Directory Management (v3.2)

1. **Add Workflow Settings**
   - New setting: `default_workflow_location`
   - Options: `current`, `documents`, `custom`
   - Store in `%APPDATA%\ImageDescriptionToolkit\settings.json`

2. **Update CLI Commands**
   - Add `--workflow-dir` flag to all commands
   - Respect `default_workflow_location` setting
   - Maintain backward compatibility (current dir if not specified)

3. **Workflow Browser**
   - Add to Viewer: "Recent Workflows" from Documents folder
   - Track workflow history in settings

### Phase 3: Installation Improvements (v3.3)

1. **Update Installer**
   - Install to `Program Files` (proper location)
   - Create `%APPDATA%` structure on first run
   - Add PATH during install
   - Create Start Menu shortcuts

2. **Update Handling**
   - Preserve user data in `%APPDATA%` and `Documents`
   - Only update Program Files
   - Migrate old configs if updating from v3.0

3. **Uninstall Handling**
   - Remove Program Files
   - Option to keep or remove user data
   - Clear documentation about data locations

## Affected Components

- ✅ **idt.exe** - Config search paths, workflow location logic
- ✅ **ImageDescriber** - Workspace management, config loading
- ✅ **Viewer** - Workflow discovery, recent files
- ✅ **Prompt Editor** - Read/write to AppData, not install dir
- ✅ **Installer** - New directory structure, migration logic
- ✅ **Documentation** - Update file location references

## Testing Checklist

- [ ] Fresh install to Program Files works
- [ ] First-run setup creates AppData structure
- [ ] Prompts editable without admin rights
- [ ] Workflows can be created in Documents
- [ ] Workflows can be created in current directory
- [ ] Config search finds files in correct order
- [ ] Update preserves user data
- [ ] Uninstall offers to keep/remove user data
- [ ] Works for non-admin users
- [ ] Works with OneDrive-synced Documents folder

## Breaking Changes

**Potentially breaking:**
- Hardcoded paths to `scripts/` directory will break
- Applications assuming install dir is writable will fail

**Mitigation:**
- Keep `C:\idt\` as valid install location option
- Provide migration tool for existing users
- Update docs with new locations

## References

- [Microsoft: Application Data Locations](https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid)
- [Microsoft: User Data and Settings](https://learn.microsoft.com/en-us/windows/apps/design/app-settings/store-and-retrieve-app-data)
- [Windows App Certification Kit: File System Rules](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)

## Notes for v3.0.1

For the current release (v3.0.1), we're keeping the simpler `C:\idt\` installation:
- ✅ Fully writable location
- ✅ Simple, clean path
- ✅ No complexity around data migration
- ✅ Works well enough for initial release
- ⚠️ Not following Windows best practices (acceptable for now)
- ⚠️ Will require migration in future versions

This issue tracks the proper implementation for future releases.
