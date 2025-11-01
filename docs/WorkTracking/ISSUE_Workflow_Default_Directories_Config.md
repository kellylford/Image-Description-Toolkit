# Issue: Add Default Input/Output Directory Support to workflow_config.json

**Created**: October 31, 2025  
**Status**: Proposed  
**Priority**: Medium  
**Related Branch**: feature/explicit-config-arguments  
**Related Issues**: ISSUE_ImageDescriber_Custom_Config_Support.md

## Summary

Add configuration settings for default input and output directories in `workflow_config.json`, allowing users to set preferred locations without specifying them on every command line. This complements the existing explicit config file support (`--config-workflow`, `--config-id`, `--config-video`).

## Current Behavior

### Input Directory
- **Required**: Positional argument `input_source` (except when using `--resume`)
- **No default**: User must specify on every workflow run
- **No config option**: Cannot be set in `workflow_config.json`

```bash
# Current: Always required
idt workflow C:/Users/kelly/Photos
idt workflow //qnap/home/media/photos
```

### Output Directory
- **Optional**: `--output-dir` or `-o` command-line flag
- **Hardcoded default**: `"workflow_output"` in current working directory
- **No config option**: Cannot be set in `workflow_config.json`

```bash
# Current: Defaults to ./workflow_output
idt workflow photos

# Current: Override with command line
idt workflow photos --output-dir //qnap/home/idt/descriptions
```

### Existing base_output_dir Setting
The current `workflow_config.json` has `base_output_dir`, but this is NOT the same:

```json
{
  "workflow": {
    "base_output_dir": "workflow_output"  // ← Used WITHIN workflow directories
  }
}
```

**What it does**: Controls subdirectory structure INSIDE a workflow directory  
**Example**: In `wf_2025_09_ollama_test_20251031_132241/`, creates `workflow_output/extracted_frames/`, `workflow_output/converted_images/`, etc.

**What it does NOT do**: Control WHERE workflow directories themselves are created

## Proposed Behavior

### Add Config Settings

```json
{
  "workflow": {
    "default_input_directory": null,  // ← NEW: Default input when not specified
    "default_output_directory": null, // ← NEW: Default for --output-dir
    "base_output_dir": "workflow_output",  // Existing: subdirs within workflow
    "preserve_structure": true,
    "cleanup_intermediate": false,
    // ... rest of config
  }
}
```

### Priority Resolution

1. **Command-line arguments** (highest priority)
2. **Config file settings** (if command-line not provided)
3. **Hardcoded defaults** (fallback)

### Input Directory Resolution
```python
# Pseudocode
if args.input_source:
    input_dir = args.input_source
elif config.get("workflow", {}).get("default_input_directory"):
    input_dir = config["workflow"]["default_input_directory"]
else:
    if not args.resume:
        error: "input_source is required"
```

### Output Directory Resolution
```python
# Pseudocode
if args.output_dir:
    output_dir = args.output_dir
elif config.get("workflow", {}).get("default_output_directory"):
    output_dir = config["workflow"]["default_output_directory"]
else:
    output_dir = "workflow_output"  # Hardcoded fallback
```

## Use Cases

### Use Case 1: Consistent Photo Source
User always processes photos from a specific directory:

**Config:**
```json
{
  "workflow": {
    "default_input_directory": "C:/Users/kelly/Photos/ToProcess"
  }
}
```

**Usage:**
```bash
# No input_source needed - uses default from config
idt workflow --config-workflow my_config.json

# Still allow override
idt workflow special_photos --config-workflow my_config.json
```

### Use Case 2: Network Storage Default
User stores all results on NAS:

**Config:**
```json
{
  "workflow": {
    "default_output_directory": "//qnap/home/idt/descriptions"
  }
}
```

**Usage:**
```bash
# Results go to NAS automatically
idt workflow photos --config-workflow nas_config.json

# Still allow override for local testing
idt workflow photos --output-dir ./test_results --config-workflow nas_config.json
```

### Use Case 3: Desktop Shortcuts
Create multiple workflow "profiles" with different defaults:

**config_vacation_photos.json:**
```json
{
  "workflow": {
    "default_input_directory": "D:/Vacation Photos",
    "default_output_directory": "D:/Vacation Descriptions"
  }
}
```

**config_work_images.json:**
```json
{
  "workflow": {
    "default_input_directory": "//company-server/images",
    "default_output_directory": "//company-server/descriptions"
  }
}
```

**Desktop shortcuts:**
```bash
# Vacation shortcut
"C:\IDT\idt.exe" workflow --config-workflow config_vacation_photos.json

# Work shortcut
"C:\IDT\idt.exe" workflow --config-workflow config_work_images.json
```

## Implementation Considerations

### 1. Argument Parsing Changes

**Current (workflow.py ~line 2305):**
```python
parser.add_argument(
    "input_source",
    nargs='?',  # Optional when using --resume
    help="Input directory containing media files, or URL to download images from"
)
```

**Proposed:**
```python
parser.add_argument(
    "input_source",
    nargs='?',  # Optional when using --resume OR when config has default
    help="Input directory containing media files, or URL to download images from (uses config default if not specified)"
)
```

### 2. Config Loading Order

Must load config BEFORE validating positional arguments:

```python
def main():
    args = parser.parse_args()
    
    # Load config (which might have defaults)
    config_file = args.config_workflow if args.config_workflow else "workflow_config.json"
    config = WorkflowConfig(config_file)
    
    # Resolve input_source
    if not args.input_source and not args.resume:
        default_input = config.config.get("workflow", {}).get("default_input_directory")
        if default_input:
            args.input_source = default_input
        else:
            parser.error("input_source is required when not using --resume")
    
    # Resolve output_dir
    if not args.output_dir:
        default_output = config.config.get("workflow", {}).get("default_output_directory")
        if default_output:
            args.output_dir = default_output
        else:
            args.output_dir = "workflow_output"
```

### 3. Path Validation

Both settings need validation:
- Check if paths exist (or are creatable for output)
- Handle relative vs absolute paths
- Handle UNC network paths
- Handle URL input sources (for input only)

```python
def resolve_input_directory(path_or_url: str) -> Path:
    """Resolve and validate input directory or URL"""
    if path_or_url.startswith(('http://', 'https://')):
        return path_or_url  # URL, no validation needed
    
    path = Path(path_or_url).resolve()
    if not path.exists():
        raise ValueError(f"Input directory does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Input path is not a directory: {path}")
    
    return path

def resolve_output_directory(path: str, create: bool = True) -> Path:
    """Resolve and validate output directory"""
    path = Path(path).resolve()
    
    if create:
        path.mkdir(parents=True, exist_ok=True)
    elif not path.exists():
        raise ValueError(f"Output directory does not exist: {path}")
    
    return path
```

### 4. Resume Compatibility

When resuming, don't override directories from metadata:

```python
if args.resume:
    # Load metadata from resume directory
    metadata = load_workflow_metadata(resume_dir)
    
    # Use original directories, ignore config defaults
    input_source = metadata.get('input_source')
    output_dir = metadata.get('output_directory')
else:
    # New workflow: apply config defaults
    input_source = resolve_input_source(args, config)
    output_dir = resolve_output_directory(args, config)
```

### 5. Help Text Updates

Update help text to reflect new behavior:

```python
parser.add_argument(
    "input_source",
    nargs='?',
    help=(
        "Input directory containing media files, or URL to download images from. "
        "Optional if workflow_config.json has 'default_input_directory' set, "
        "or when using --resume."
    )
)

parser.add_argument(
    "--output-dir", "-o",
    help=(
        "Output directory for workflow results. "
        "Uses 'default_output_directory' from workflow_config.json if set, "
        "otherwise defaults to 'workflow_output' in current directory."
    )
)
```

### 6. Metadata Storage

Save resolved directories to workflow_metadata.json for debugging:

```json
{
  "input_source": "C:/Users/kelly/Photos",
  "input_source_origin": "config_default",  // or "command_line" or "hardcoded"
  "output_directory": "//qnap/home/idt/descriptions",
  "output_directory_origin": "command_line",
  // ... rest of metadata
}
```

## Differences from ImageDescriber GUI Issue

**This issue (workflow CLI)**:
- Users CAN use command-line options (`--output-dir`, positional `input_source`)
- Adding config-based DEFAULTS to complement existing CLI args
- Priority: CLI args > config defaults > hardcoded defaults

**ImageDescriber GUI issue**:
- Users CANNOT use command-line options (no argparse in GUI)
- Adding ANY way to specify custom configs (currently impossible)
- Priority: Need to add missing capability

## Testing Requirements

1. **Config with input default only**
   - Verify input uses default, output uses hardcoded default
   
2. **Config with output default only**
   - Verify input still required, output uses config default

3. **Config with both defaults**
   - Verify both use config defaults

4. **Command-line override**
   - Verify CLI args take precedence over config defaults

5. **Resume behavior**
   - Verify resume uses original directories, ignores config defaults

6. **Missing directory handling**
   - Verify error if input doesn't exist
   - Verify output creates directories if needed

7. **UNC path support**
   - Verify network paths work for both input and output

8. **URL input**
   - Verify URLs still work for input_source

9. **Relative paths**
   - Verify relative paths resolve correctly

10. **Empty/null config values**
    - Verify null/missing settings fall back to hardcoded defaults

## Documentation Updates Needed

1. **workflow_config.json** - Add new settings with examples
2. **docs/CONFIG_FILES.md** - Document new settings
3. **docs/WORKFLOW_CLI.md** - Update usage examples
4. **README.md** - Update workflow examples if relevant

## Related Context

- **Feature branch**: `feature/explicit-config-arguments` already adds `--config-workflow` support
- **Existing work**: Config loading infrastructure already in place via `config_loader.py`
- **User workflow**: User runs workflows from UNC paths regularly (e.g., `//qnap/home/idt/descriptions`)
- **Priority**: Lower than stabilizing current explicit config arguments feature

## Recommendation

**Defer until after feature/explicit-config-arguments is merged and stabilized.**

This feature complements the explicit config work but is not critical for the current branch goals:
- Users can already specify directories via CLI args
- Explicit config file support is the priority
- This is a convenience enhancement, not a missing capability

Once the config file loading system is validated and merged, this will be a straightforward addition following the same patterns.

## Notes

- Consider adding validation warnings if config defaults point to nonexistent paths
- Consider adding `--show-config` debug flag to display resolved settings
- May want to add similar defaults to `image_describer_config.json` for standalone image_describer.py usage
