# Workflow Helper Batch Files

## Overview
When a workflow starts (via `idt workflow` or `idt guideme`), three convenience batch files are automatically created in the workflow directory. These files provide easy access to common workflow operations.

## Created Files

### 1. view_results.bat
**Purpose:** Launch the viewer to see workflow results in real-time

**Usage:**
```bash
cd wf\wf_identifier_20250113_143022
view_results.bat
```

**What it does:**
- Opens the viewer application pointing to the workflow directory
- Works even while workflow is still running
- Shows descriptions as they are generated

**When to use:**
- Monitor progress during long workflows
- Review completed descriptions
- Check results after workflow interruption

---

### 2. resume_workflow.bat
**Purpose:** Resume an interrupted workflow from the last completed step

**Usage:**
```bash
cd wf\wf_identifier_20250113_143022
resume_workflow.bat
```

**What it does:**
- Calls `idt workflow --resume` with the current workflow directory
- Reads workflow metadata to determine last completed step
- Continues processing from where it left off
- Includes pause at end so you can see results

**When to use:**
- Workflow was interrupted (Ctrl+C, system crash, etc.)
- Want to complete partial workflow
- System ran out of resources mid-workflow

---

### 3. run_stats.bat
**Purpose:** Run statistics analysis on this specific workflow

**Usage:**
```bash
cd wf\wf_identifier_20250113_143022
run_stats.bat
```

**What it does:**
1. Creates `stats\` subdirectory in the workflow folder
2. Runs `idt stats --input-dir` on the parent directory (all workflows)
3. Copies output files to the local `stats\` subdirectory
4. Saves these files:
   - `stats\workflow_timing_stats.csv` - Timing data in CSV format
   - `stats\workflow_statistics.json` - Complete stats in JSON format

**Output Location:**
```
wf\wf_identifier_20250113_143022\
├── view_results.bat
├── resume_workflow.bat
├── run_stats.bat
└── stats\                                    ← Created when you run run_stats.bat
    ├── workflow_timing_stats.csv
    └── workflow_statistics.json
```

**What's in the stats files:**

**workflow_timing_stats.csv** (spreadsheet-friendly):
- Workflow identifier
- Total duration
- Steps completed
- Items processed
- Average time per item
- Start/end timestamps

**workflow_statistics.json** (complete data):
- All timing information
- Step-by-step breakdown
- Model used
- Prompt style
- Configuration details
- File paths

**When to use:**
- Analyzing workflow performance
- Comparing different workflows
- Debugging slow processing
- Documenting workflow metrics
- Quality analysis of results

**Why stats are only saved if you run the bat file:**
- Avoids cluttering workflow directories with automatic files
- Stats are optional - only generated when needed
- Keeps workflow directory clean for primary outputs (descriptions, images, etc.)
- User has control over when stats are generated

---

## Technical Details

### File Creation Timing
All three batch files are created **immediately** when the workflow starts, right after the directory structure is created. This ensures they're available even if the workflow is interrupted early.

### Cross-Platform Considerations
- These are Windows batch files (`.bat`)
- Created by `create_workflow_helper_files()` in `scripts/workflow_utils.py`
- Work in both development mode (Python scripts) and executable mode (idt.exe)

### Development vs. Executable Mode

**Executable Mode** (idt.exe):
```batch
# view_results.bat calls:
"C:\IDT\viewer\viewer.exe" "C:\path\to\workflow"

# resume_workflow.bat calls:
"C:\IDT\idt.exe" workflow --resume "C:\path\to\workflow"

# run_stats.bat calls:
"C:\IDT\idt.exe" stats --input-dir "C:\path\to\Descriptions" --csv-output "..." --json-output "..."
```

**Development Mode** (Python scripts):
```batch
# view_results.bat calls:
"C:\Python\python.exe" "C:\repo\viewer\viewer.py" "C:\path\to\workflow"

# resume_workflow.bat calls:
"C:\Python\python.exe" "C:\repo\scripts\workflow.py" --resume "C:\path\to\workflow"

# run_stats.bat calls:
"C:\Python\python.exe" "C:\repo\analysis\stats_analysis.py" --input-dir "..." --csv-output "..." --json-output "..."
```

### Error Handling
If batch file creation fails for any reason:
- Error is silently caught (these are convenience features)
- Workflow continues normally
- No impact on core functionality

## Examples

### Example 1: Monitor Long Workflow
```bash
# Terminal 1: Start workflow
idt workflow --input testimages --provider ollama --model llama32-vision

# Terminal 2: View results as they generate
cd wf\wf_testimages_20250113_143022
view_results.bat
```

### Example 2: Resume After Interruption
```bash
# Workflow was interrupted with Ctrl+C
cd wf\wf_testimages_20250113_143022
resume_workflow.bat
# Workflow continues from last completed step
```

### Example 3: Analyze Workflow Performance
```bash
# After workflow completes
cd wf\wf_testimages_20250113_143022
run_stats.bat

# Review stats
type stats\workflow_timing_stats.csv
# Or open in Excel/spreadsheet application
```

### Example 4: Compare Multiple Workflows
```bash
# Run stats for each workflow
cd wf\wf_test1_20250113_100000
run_stats.bat

cd ..\wf_test2_20250113_110000
run_stats.bat

# Stats are isolated in each workflow's stats\ subdirectory
# Compare the CSV files side by side
```

## Related Documentation
- **Workflow Resume:** See `docs/workflow_resume.md` for details on resume functionality
- **Stats Analysis:** See `analysis/README.md` for stats output format details
- **Viewer:** See `viewer/README.md` for viewer features

## Implementation
See `scripts/workflow_utils.py` - `create_workflow_helper_files()` function for implementation details.
