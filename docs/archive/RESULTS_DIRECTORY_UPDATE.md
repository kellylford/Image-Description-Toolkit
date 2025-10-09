# Results Directory Organization - October 8, 2025

## Summary

Updated all analysis scripts to write output files to a dedicated `analysis/results/` directory instead of the main `analysis/` directory. This keeps the workspace clean and organized.

## Changes Made

### 1. Created New Directory Structure
- **New Directory:** `analysis/results/`
- **Purpose:** Centralized location for all analysis output files
- **Git Tracking:** Directory includes `.gitignore` to exclude output files from version control

### 2. Updated Scripts

#### combine_workflow_descriptions.py
- **Output location changed:** `analysis/` → `analysis/results/`
- **Default output:** `results/combineddescriptions.csv`
- **Help text updated:** Now mentions `analysis/results/` directory
- **Line changes:**
  - Line 285: Updated help text to mention `results/` directory
  - Line 369: Changed output directory from `Path(__file__).parent` to `Path(__file__).parent / "results"`

#### content_analysis.py
- **Output location changed:** `analysis/` → `analysis/results/`
- **Input location priority:** Checks `results/` first, falls back to `analysis/` for backward compatibility
- **Default input:** Looks in `results/combineddescriptions.csv` first
- **Default output:** `results/description_content_analysis.csv`
- **Help text updated:** Now mentions `results/` directory
- **Line changes:**
  - Line 363: Updated help text for input to mention `results/` directory
  - Line 370: Updated help text for output to mention `results/` directory
  - Lines 375-380: Added backward compatibility check (looks in `results/` first, then `analysis/`)
  - Line 413: Changed output directory from `Path(__file__).parent` to `Path(__file__).parent / "results"`

#### stats_analysis.py
- **Output location changed:** `analysis/` → `analysis/results/`
- **Default CSV output:** `results/workflow_timing_stats.csv`
- **Default JSON output:** `results/workflow_statistics.json`
- **Help text updated:** Both arguments now mention `results/` directory
- **Line changes:**
  - Line 763: Updated CSV help text to mention `results/` directory
  - Line 770: Updated JSON help text to mention `results/` directory
  - Line 827: Changed output directory from `Path(__file__).parent` to `Path(__file__).parent / "results"`

### 3. Migrated Existing Files
Moved existing output files from `analysis/` to `analysis/results/`:
- ✅ `workflow_statistics.json`
- ✅ `workflow_timing_stats.csv`
- ✅ `combineddescriptions.csv`

### 4. Created Documentation

#### results/.gitignore
Excludes all output files from git:
```gitignore
# Ignore all analysis output files
*.csv
*.json
*.txt

# But keep this directory in git
!.gitignore
```

**Note:** The results directory contains only `.gitignore` - all output files are ignored by git and can be safely deleted by users at any time.

### 5. Updated Main Documentation

#### analysis/README.md
Updated sections:
- **Default Output Locations table:** All paths now show `results/` prefix
- **Arguments tables:** Updated help text for all three scripts
- **Output Files section:** Added explanation of why results directory is used
- **Note about backward compatibility:** Mentioned in content_analysis.py section

## Benefits

✅ **Cleaner Directory Structure**
- Analysis scripts (`.py`) separated from output files (`.csv`, `.json`)
- Easy to see what's code vs what's generated data

✅ **Easier Navigation**
- All results in one place - no hunting through directories
- Quick to find latest analysis output

✅ **Better Git Hygiene**
- Single `.gitignore` in results directory handles all output files
- No accidental commits of large CSV files
- Repository stays focused on code, not data

✅ **Backward Compatibility**
- `content_analysis.py` checks both locations for input files
- Existing workflows continue to work
- Old files still accessible if needed

## File Organization

### Before
```
analysis/
├── combine_workflow_descriptions.py
├── stats_analysis.py
├── content_analysis.py
├── analysis_utils.py
├── combineddescriptions.csv          ❌ Mixed with code
├── workflow_timing_stats.csv         ❌ Mixed with code
├── workflow_statistics.json          ❌ Mixed with code
├── README.md
└── __pycache__/
```

### After
```
analysis/
├── combine_workflow_descriptions.py
├── stats_analysis.py
├── content_analysis.py
├── analysis_utils.py
├── README.md
├── CSV_FORMAT_UPGRADE.md
├── PROMPT_TRACKING_UPDATE.md
├── __pycache__/
└── results/                          ✅ Organized!
    └── .gitignore                    ✅ Auto-ignore all outputs (directory is otherwise empty)
```

**Note:** Output files (`.csv`, `.json`, `.txt`) will be created here when scripts run, but are not tracked in git.

## Testing Recommendations

1. **Test each script with default arguments:**
   ```bash
   cd analysis
   python combine_workflow_descriptions.py
   python stats_analysis.py
   python content_analysis.py
   ```
   - Verify files are created in `results/` directory
   - Check that file numbering works (creates `_1`, `_2`, etc. if files exist)

2. **Test backward compatibility:**
   ```bash
   # Move an old combineddescriptions.csv to analysis/ directory
   mv results/combineddescriptions.csv .
   
   # This should still find and read the file
   python content_analysis.py
   ```

3. **Test custom output paths:**
   ```bash
   python combine_workflow_descriptions.py --output /tmp/test.csv
   python stats_analysis.py --csv-output /tmp/stats.csv
   ```

4. **Verify directory is created if missing:**
   ```bash
   rm -rf results
   python combine_workflow_descriptions.py
   # Should auto-create results/ directory
   ```

## Migration Notes

### For Users
- **No action required** - Scripts automatically create and use `results/` directory
- Existing files in `analysis/` directory can be moved to `results/` manually if desired
- Scripts will continue to work exactly as before, just with cleaner organization

### For Developers
- All scripts use `ensure_directory()` from `analysis_utils.py` to create results directory
- Output paths constructed as: `Path(__file__).parent / "results" / args.output`
- Input paths in `content_analysis.py` check both locations for compatibility

## Related Updates

This change complements recent improvements:
- **Prompt Tracking** (PROMPT_TRACKING_UPDATE.md) - Added prompt column to all analysis outputs
- **CSV Format Upgrade** (CSV_FORMAT_UPGRADE.md) - Added CSV/TSV/ATSV format support

All three major improvements maintain backward compatibility while adding new capabilities.
