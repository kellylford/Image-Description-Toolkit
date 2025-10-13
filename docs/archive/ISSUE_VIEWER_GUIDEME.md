# Issue: Support Viewer with GuideMe Runs

## Status
🔴 **OPEN** - Enhancement to integrate viewer into guideme workflow

## Priority
**MEDIUM** - Quality of life improvement for guideme users

## Description
The GuideMe interactive wizard should offer to create a batch file to view workflow results after completion. This provides a convenient way for users to launch the viewer and browse their descriptions.

## Current State

### GuideMe Workflow Steps
Currently, guideme helps users:
1. Choose AI provider (Ollama, OpenAI, Claude)
2. Select model
3. Configure API key (if needed)
4. Choose input directory
5. Set workflow name (optional)
6. Select prompt style
7. **Launch workflow**

**Missing**: No easy way to view results after workflow completes

### Viewer Capabilities
The viewer (`viewer/viewer.py`) supports:
- Opening directories via command line: `viewer.exe <directory_path>`
- Browsing completed workflows in HTML mode
- Monitoring in-progress workflows in Live mode
- Redescribing images with Ollama

**Location**: `viewer\viewer.exe` (once built per Issue #45)

## Proposed Enhancement

### New GuideMe Step: "View Results"

After workflow launches (or completes), offer to create a batch file:

```
Workflow started successfully!

Would you like to create a batch file to view results? (Y/n): _
```

If user chooses **Yes**:
1. Create batch file in `analysis\viewResults\` directory
2. Name it based on workflow: `view_<workflow_name>.bat`
3. Contents launch viewer with the workflow output directory
4. Display instructions for using the batch file

### Batch File Template

```batch
@echo off
REM View results for workflow: <workflow_name>
REM Created: <timestamp>
REM Output directory: <output_dir>

cd /d "%~dp0\..\.."
start "" "viewer\viewer.exe" "<output_dir_path>"

REM Note: Viewer will open in Live mode if workflow is in progress,
REM or HTML mode if workflow is complete.
```

### Example

**Workflow**: `wf_vacation_ollama_llava_artistic_20251012_143022`

**Generated file**: `analysis\viewResults\view_vacation.bat`

**Contents**:
```batch
@echo off
REM View results for workflow: vacation
REM Created: 2025-10-12 14:30:22
REM Output directory: Descriptions\wf_vacation_ollama_llava_artistic_20251012_143022

cd /d "%~dp0\..\.."
start "" "viewer\viewer.exe" "Descriptions\wf_vacation_ollama_llava_artistic_20251012_143022"
```

**User experience**:
1. User runs guideme, creates workflow named "vacation"
2. Guideme asks: "Create batch file to view results?"
3. User answers "Y"
4. File created: `analysis\viewResults\view_vacation.bat`
5. User can double-click this file anytime to view results

## Implementation Details

### Directory Structure
```
idt/
├── analysis/
│   └── viewResults/          ← New directory
│       ├── view_vacation.bat
│       ├── view_europe.bat
│       └── README.txt        ← Explains how to use these files
├── viewer/
│   └── viewer.exe            ← Built viewer executable
└── Descriptions/             ← Workflow output directories
    ├── wf_vacation_ollama_llava_artistic_20251012_143022/
    └── wf_europe_ollama_gemma_narrative_20251011_162608/
```

### Changes Needed in guided_workflow.py

**Add after workflow launch (around line 450+):**

```python
def create_viewer_batch_file(workflow_name: str, output_dir: Path) -> Optional[Path]:
    """Create a batch file to launch viewer for this workflow"""
    
    # Create viewResults directory if it doesn't exist
    view_results_dir = Path("analysis") / "viewResults"
    view_results_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate batch file name from workflow name
    batch_filename = f"view_{workflow_name}.bat"
    batch_path = view_results_dir / batch_filename
    
    # Get relative path from batch file to output directory
    # batch_path is in analysis/viewResults/
    # output_dir is in Descriptions/
    # Both are relative to project root
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    batch_content = f"""@echo off
REM View results for workflow: {workflow_name}
REM Created: {timestamp}
REM Output directory: {output_dir}

cd /d "%~dp0\\..\\.."

REM Check if viewer exists
if not exist "viewer\\viewer.exe" (
    echo ERROR: Viewer not found at viewer\\viewer.exe
    echo Please build the viewer first using viewer\\build_viewer.bat
    echo.
    pause
    exit /b 1
)

REM Launch viewer
echo Launching viewer for workflow: {workflow_name}
echo Output directory: {output_dir}
echo.
start "" "viewer\\viewer.exe" "{output_dir}"
"""
    
    try:
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        return batch_path
    except Exception as e:
        print(f"Warning: Could not create viewer batch file: {e}")
        return None


def offer_viewer_batch_file(workflow_name: str, output_dir: Path):
    """Offer to create a batch file to view results"""
    
    print("\n" + "="*60)
    print("View Results")
    print("="*60)
    print("Would you like to create a batch file to view workflow results?")
    print(f"This will create: analysis\\viewResults\\view_{workflow_name}.bat")
    print()
    
    choice = get_choice("Create viewer batch file?", ["Yes", "No"], allow_exit=False)
    
    if choice == "Yes":
        batch_path = create_viewer_batch_file(workflow_name, output_dir)
        if batch_path:
            print(f"\n✓ Created viewer batch file: {batch_path}")
            print(f"\nTo view results, double-click: {batch_path}")
            print("Or run from command line:")
            print(f"  {batch_path}")
            print("\nNote: Viewer will open in:")
            print("  - Live mode if workflow is still running")
            print("  - HTML mode when workflow is complete")
        else:
            print("\n✗ Failed to create viewer batch file")
    else:
        print("\nSkipping viewer batch file creation")
        print(f"\nYou can still view results manually:")
        print(f"  viewer\\viewer.exe {output_dir}")
```

**Integration point in main guideme flow:**

After launching the workflow (currently around lines 455-465), add:

```python
# Launch workflow
print("\nLaunching workflow...")
# ... existing workflow launch code ...

# Offer to create viewer batch file
if workflow_launched_successfully:
    offer_viewer_batch_file(workflow_name, output_dir)
```

### Create README for viewResults Directory

**File**: `analysis/viewResults/README.txt`

```
View Results Batch Files
========================

This directory contains batch files created by the GuideMe wizard to
conveniently view workflow results using the Image Description Viewer.

How to Use:
-----------
1. Double-click any .bat file to launch the viewer for that workflow
2. Or run from command line: view_<name>.bat

What the Batch Files Do:
------------------------
- Navigate to the project root directory
- Check if viewer.exe exists
- Launch the viewer with the workflow output directory

Viewer Modes:
-------------
- Live Mode: If workflow is still running, see real-time progress
- HTML Mode: If workflow is complete, browse final results

Requirements:
-------------
- Viewer must be built: viewer\viewer.exe
- Build using: cd viewer && build_viewer.bat

Manual Viewing:
---------------
You can also launch the viewer manually:
  viewer\viewer.exe <path_to_workflow_directory>

Example:
  viewer\viewer.exe Descriptions\wf_vacation_ollama_llava_artistic_20251012_143022
```

## User Experience Flow

### Scenario 1: Create Batch File After Launch

```
$ idt guideme

[... user goes through guideme steps ...]

Launching workflow...
✓ Workflow started successfully!

============================================================
View Results
============================================================
Would you like to create a batch file to view workflow results?
This will create: analysis\viewResults\view_vacation.bat

Create viewer batch file?
  1. Yes
  2. No
> 1

✓ Created viewer batch file: analysis\viewResults\view_vacation.bat

To view results, double-click: analysis\viewResults\view_vacation.bat
Or run from command line:
  analysis\viewResults\view_vacation.bat

Note: Viewer will open in:
  - Live mode if workflow is still running
  - HTML mode when workflow is complete
```

### Scenario 2: User Skips Batch File Creation

```
Create viewer batch file?
  1. Yes
  2. No
> 2

Skipping viewer batch file creation

You can still view results manually:
  viewer\viewer.exe Descriptions\wf_vacation_ollama_llava_artistic_20251012_143022
```

### Scenario 3: User Runs Batch File

```
C:\idt> analysis\viewResults\view_vacation.bat

Launching viewer for workflow: vacation
Output directory: Descriptions\wf_vacation_ollama_llava_artistic_20251012_143022

[Viewer window opens showing workflow results]
```

## Benefits

1. **Convenience**: One-click access to view results
2. **Discoverability**: Users learn about the viewer feature
3. **Organized**: All view scripts in one place
4. **Reusable**: Batch files can be used multiple times
5. **Educational**: Shows users the viewer command syntax
6. **Persistent**: Batch files remain after workflow completes

## Edge Cases to Handle

### Viewer Not Built
```batch
if not exist "viewer\viewer.exe" (
    echo ERROR: Viewer not found at viewer\viewer.exe
    echo Please build the viewer first using viewer\build_viewer.bat
    pause
    exit /b 1
)
```

### Invalid Characters in Workflow Name
Sanitize workflow name for batch filename:
```python
safe_name = re.sub(r'[<>:"/\\|?*]', '_', workflow_name)
batch_filename = f"view_{safe_name}.bat"
```

### Duplicate Batch Files
If `view_vacation.bat` already exists:
- Option A: Overwrite with timestamp comment
- Option B: Create `view_vacation_2.bat`
- Option C: Ask user to confirm overwrite

### Viewer in Different Location
Make batch file robust to viewer location:
```batch
REM Try multiple viewer locations
if exist "viewer\viewer.exe" (
    set VIEWER=viewer\viewer.exe
) else if exist "dist\viewer.exe" (
    set VIEWER=dist\viewer.exe
) else (
    echo ERROR: Viewer not found
    exit /b 1
)

start "" "%VIEWER%" "<output_dir>"
```

## Testing Checklist

- [ ] Create new workflow via guideme
- [ ] Accept viewer batch file creation
- [ ] Verify batch file created in analysis\viewResults\
- [ ] Verify batch file name matches workflow name
- [ ] Run batch file - viewer launches correctly
- [ ] Run batch file during workflow - opens in Live mode
- [ ] Run batch file after completion - opens in HTML mode
- [ ] Test with workflow name containing special characters
- [ ] Test when viewer.exe doesn't exist - shows error
- [ ] Test declining batch file creation - workflow proceeds
- [ ] Verify README.txt is helpful

## Implementation Plan

### Phase 1: Basic Implementation
- [ ] Create `analysis/viewResults/` directory structure
- [ ] Add `create_viewer_batch_file()` function to guided_workflow.py
- [ ] Add `offer_viewer_batch_file()` function to guided_workflow.py
- [ ] Integrate into guideme workflow (after launch)
- [ ] Create README.txt in viewResults directory

### Phase 2: Polish
- [ ] Handle special characters in workflow names
- [ ] Add viewer existence check in batch file
- [ ] Test on workflows in progress (Live mode)
- [ ] Test on completed workflows (HTML mode)
- [ ] Add color/formatting to batch file output

### Phase 3: Documentation
- [ ] Update guideme documentation
- [ ] Add screenshots to README
- [ ] Document batch file format
- [ ] Add to user guide

## Related Files
- `scripts/guided_workflow.py` - Main guideme implementation
- `viewer/viewer.py` - Viewer application (supports directory argument)
- `analysis/viewResults/` - New directory for batch files (to be created)
- `viewer/viewer.exe` - Built viewer executable (from Issue #45)

## Dependencies
- **Issue #45**: Viewer must be built and available at `viewer/viewer.exe`
- Viewer already supports directory argument (implemented)
- GuideMe wizard already captures workflow name and output directory

## Future Enhancements
- Add "View Results" option to main IDT menu (not just guideme)
- Create viewer shortcuts for all existing workflows
- Add option to auto-launch viewer after workflow completes
- Create PowerShell version for better cross-platform support
- Add viewer batch files to workflow metadata

---
**Created:** October 12, 2025
**Priority:** Medium
**Category:** Enhancement, User Experience
**Dependencies:** Issue #45 (Viewer build)
**Estimated Effort:** 2-4 hours
