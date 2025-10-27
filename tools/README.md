# Tools Directory

This directory contains utility scripts for managing and analyzing the Image Description Toolkit workflows.

## Available Tools

### 1. show_metadata.py (NEW)

**Purpose**: Extract and display EXIF metadata from images without running AI descriptions.

**What it does**:
- Shows what metadata will be extracted during workflows
- Displays both the detailed EXIF block and the compact Meta suffix
- Tests metadata extraction on your images before running full workflows
- Identifies images with/without EXIF data

**Usage**:
```bash
# Show metadata for all images in a directory
python tools/show_metadata.py images/

# Process subdirectories recursively
python tools/show_metadata.py images/ --recursive

# Hide the Meta suffix line (show only detailed metadata)
python tools/show_metadata.py images/ --no-meta-suffix
```

**Output Example**:
```
[1/3] IMG_1234.JPG
  File size: 2458.3 KB
  File modified: 3/25/2025 7:35P

  EXIF Metadata:
  Photo Date: 3/25/2025 7:35P
  Location: GPS: 30.267200, -97.743100, Altitude: 165.0m, Location: Austin, TX
  Camera: Apple iPhone 14 Pro, Lens: iPhone 14 Pro back triple camera
  Settings: Iso: 100, Aperture: f/1.8, Shutter Speed: 1/120s, Focal Length: 7mm

  Meta: date=3/25/2025 7:35P; location=Austin, TX; coords=30.267200,-97.743100
```

**Use Cases**:
- Test which images have EXIF metadata before running workflows
- Verify date/time formatting matches project standards
- Check GPS coordinates and location data availability
- Preview what the Meta suffix will contain

---

### 2. analyze_workflow_naming.py

**Purpose**: Analyze existing workflow directories and propose enhanced naming schemes with path identifiers.

**What it does**:
- Scans all workflow directories in the `hold` folder
- Extracts input directory paths from workflow log files
- Generates proposed names with 1, 2, or 3 path components
- Outputs CSV with old names vs. proposed new names
- Provides statistics on directory usage and duplicates

**Usage**:
```bash
# Analyze workflows (defaults to descriptions/hold directory)
python tools/analyze_workflow_naming.py

# Analyze a different directory
python tools/analyze_workflow_naming.py C:\path\to\workflows
```

**Output**:
- `workflow_naming_analysis.csv` - CSV with old and proposed names
- Console statistics and summary

**Related**: See `WORKFLOW_NAMING_ANALYSIS.md` for full analysis results and recommendations.

---

### 3. rename_workflows_with_paths.py

**Purpose**: Rename existing workflow directories to include 2-component path identifiers.

**What it does**:
- Renames workflow directories from old format to new format
- Old: `wf_PROVIDER_MODEL_PROMPT_TIMESTAMP`
- New: `wf_PATH1_PATH2_PROVIDER_MODEL_PROMPT_TIMESTAMP`
- Example: `wf_claude_haiku_narrative_20251011_103631` → `wf_2025_07_claude_haiku_narrative_20251011_103631`

**⚠️ WARNING**: This script modifies directory names. Make sure you have backups before running!

**Usage**:
```bash
# DRY RUN FIRST (recommended) - see what would be renamed
python tools/rename_workflows_with_paths.py --dry-run

# Actually perform the rename
python tools/rename_workflows_with_paths.py

# Rename workflows in a different directory
python tools/rename_workflows_with_paths.py C:\path\to\hold --dry-run
```

**Features**:
- **Dry-run mode**: See proposed changes without actually renaming
- **Safety checks**: Won't overwrite existing directories
- **Detailed output**: Shows old name, new name, and input directory for each workflow
- **Summary report**: Counts of renamed, skipped, and any errors
- **Error handling**: Continues processing even if individual renames fail

**Workflow**:
1. Run with `--dry-run` to review all proposed changes
2. Review the output carefully
3. Run without `--dry-run` to perform actual rename
4. Review summary to confirm all renames succeeded

**Default directory**: `~/idt/descriptions/hold` (or `C:\Users\<USERNAME>\idt\descriptions\hold` on Windows)

---

## Workflow Naming Background

**Problem**: Workflow directories are hard to identify without opening log files. When you have 168 workflows like:
- `wf_claude_haiku_narrative_20251011_103631`
- `wf_claude_haiku_narrative_20251012_094512`
- `wf_claude_haiku_narrative_20251013_151234`

You can't tell which images were processed without diving into the logs.

**Solution**: Include path identifiers in directory names:
- `wf_2025_07_claude_haiku_narrative_20251011_103631` (iPhone photos from July 2025)
- `wf_2025_08_claude_haiku_narrative_20251012_094512` (iPhone photos from August 2025)
- `wf_testimages_claude_haiku_narrative_20251013_151234` (Test images)

**Implementation**: The 2-component approach (e.g., `2025_07` or `testimages`) provides a good balance:
- Readable: Year/month for dated photos, meaningful names for project directories
- Concise: Adds only ~8 characters vs. original names
- Useful: Immediately identifies which photos were processed

**Related Issues**: GitHub Issue #27 - "Add Workflow Names/Identifiers to Support Multiple Runs"

---

## Future Enhancements

These tools support Issue #27 implementation, which will add:
- `--workflow-name` parameter to `workflow.py` for user-provided names
- Automatic path-based naming when `--workflow-name` not provided
- Updated `combine_workflow_descriptions.py` to use workflow names as row keys
- Metadata file to store workflow name alongside other workflow information

---

## Development Notes

**Path Identifier Extraction**:
- Extracts from workflow log files: `Input directory: C:\path\to\images`
- Takes rightmost N components: `images\2025\07` → `2025_07` (2 components)
- Cleans for filesystem: Removes special chars, limits length to 50 chars
- Normalizes: Lowercase, underscores instead of spaces/slashes

**Workflow Directory Parsing**:
- Expected format: `wf_PROVIDER_MODEL_PROMPT_TIMESTAMP`
- Timestamp pattern: `YYYYMMDD_HHMMSS` (e.g., `20251011_103631`)
- Middle components: Everything between `wf_` prefix and timestamp
- Robust parsing: Handles various provider/model name formats

**Safety**:
- Both scripts use read-only operations by default (dry-run)
- Won't overwrite existing directories
- Detailed logging of all operations
- Error handling to prevent partial failures

---

## See Also

- `WORKFLOW_NAMING_ANALYSIS.md` - Comprehensive analysis of 168 existing workflows
- `workflow_naming_analysis.csv` - Raw data with all naming proposals
- GitHub Issue #27 - Original feature request and discussion
- `docs/AI_AGENT_REFERENCE.md` - Overall project architecture and design decisions
