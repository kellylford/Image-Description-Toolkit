# Workflow Naming Analysis - Experimental Results

## Overview

Analyzed **168 existing workflows** from `idtexternal/idt/descriptions/hold/` to evaluate automatic naming proposals that include input directory information.

**Key Finding**: Only **19 unique input directories** were used across 168 workflows, with heavy reuse of test image directories.

## Naming Proposal Examples

### iPhone Photo Batches (2025/07, 08, 09)

**Current naming** (no way to distinguish):
```
wf_claude_claude-3-haiku-20240307_narrative_20251011_103631
wf_claude_claude-3-haiku-20240307_narrative_20251011_100046
wf_claude_claude-3-haiku-20240307_narrative_20251010_210405
```

**Proposed naming options**:

#### Option 1: Single component (rightmost directory)
```
wf_07_claude_claude-3-haiku-20240307_narrative_20251011_103631
wf_08_claude_claude-3-haiku-20240307_narrative_20251011_100046
wf_09_claude_claude-3-haiku-20240307_narrative_20251010_210405
```
**Pros**: Very short, shows month  
**Cons**: Doesn't show year, could be ambiguous

#### Option 2: Two components
```
wf_2025_07_claude_claude-3-haiku-20240307_narrative_20251011_103631
wf_2025_08_claude_claude-3-haiku-20240307_narrative_20251011_100046
wf_2025_09_claude_claude-3-haiku-20240307_narrative_20251010_210405
```
**Pros**: Clear year/month identifier  
**Cons**: Still doesn't show it's iPhone photos

#### Option 3: Three components
```
wf_iphone_2025_07_claude_claude-3-haiku-20240307_narrative_20251011_103631
wf_iphone_2025_08_claude_claude-3-haiku-20240307_narrative_20251011_100046
wf_iphone_2025_09_claude_claude-3-haiku-20240307_narrative_20251010_210405
```
**Pros**: Very clear what the source is (iPhone/2025/07)  
**Cons**: Longest names

### Test Image Directories

**Current naming** (multiple different test directories):
```
wf_claude_claude-3-5-haiku-20241022_narrative_20251010_211438
wf_claude_claude-3-5-haiku-20241022_narrative_20251011_004240
wf_claude_claude-3-7-sonnet-20250219_detailed_20251009_163048
```

**Input directories**:
- `C:\Users\kelly\GitHub\idt\idtexternal\testimages`
- `C:\Users\kelly\GitHub\idt\idtexternal\idt\bat\testimages`
- `c:\idt\testimages`

**Proposed with 2 components**:
```
wf_idtexternal_testimages_claude_claude-3-5-haiku-20241022_narrative_20251010_211438
wf_bat_testimages_claude_claude-3-5-haiku-20241022_narrative_20251011_004240
wf_idt_testimages_claude_claude-3-7-sonnet-20250219_detailed_20251009_163048
```

Shows different test image locations clearly.

## Statistics

### Input Directory Reuse

**Top 5 Most-Used Directories**:
1. `C:\Users\kelly\GitHub\idt\idtexternal\testimages` - **50 workflows** (30%)
2. `C:\idt\testimages` - **32 workflows** (19%)
3. `C:\Users\kelly\GitHub\idt\test_images` - **19 workflows** (11%)
4. `c:\users\kelly\github\testimages` - **13 workflows** (8%)
5. `C:\Users\kelly\GitHub\idt\idtexternal\idt\bat\testimages` - **10 workflows** (6%)

**Observation**: Heavy concentration in test directories. This is exactly why Issue #27's de-duplication problem occurs - same images processed many times with same settings.

### Real Photo Directories
- `\\ford\home\photos\MobileBackup\iPhone\2025\09` - 10 workflows
- `\\ford\home\photos\MobileBackup\iPhone\2025\07` - 1 workflow  
- `\\ford\home\photos\MobileBackup\iPhone\2025\08` - 1 workflow

These benefit most from path-based naming since they're actual production photo batches.

## Analysis & Recommendations

### What Works Well

**Path-based auto-naming is GOOD for**:
- Production photo batches (iPhone/2025/XX clearly identifies month)
- Different test image sets (shows which test directory)
- Automatic differentiation without user input

### What Doesn't Work Well

**Path-based auto-naming is NOT ENOUGH for**:
- Same directory used multiple times (50 workflows on `testimages`)
- Distinguishing test purposes ("initial test" vs "improved prompts")
- Semantic meaning ("family vacation" vs "product shots")

### Recommendation: Hybrid Approach

The analysis supports Issue #27's **Option C - Hybrid Approach**:

1. **Auto-generated base**: Include path identifier (2-3 components recommended)
   - Format: `wf_{path_id}_{provider}_{model}_{prompt}_{timestamp}`
   - Example: `wf_iphone_2025_07_claude_haiku_narrative_20251011_103631`

2. **Optional user override**: `--workflow-name` for semantic meaning
   - Format: `wf_{user_name}_{provider}_{model}_{prompt}_{timestamp}`
   - Example: `wf_family_vacation_claude_haiku_narrative_20251011_103631`
   - Or even: `wf_family_vacation_batch1_claude_haiku_narrative_20251011_103631`

3. **For CSV/analysis**: Use BOTH path and user name if provided
   - Column: `workflow_name` = `{user_name}` or `{path_id}` if no user name
   - Allows grouping by user-provided name across multiple runs

## Readability Assessment

### Directory Name Length Comparison

**Current**:
```
wf_claude_claude-3-haiku-20240307_narrative_20251011_103631 (59 chars)
```

**With 2-component path**:
```
wf_2025_07_claude_claude-3-haiku-20240307_narrative_20251011_103631 (67 chars)
```

**With 3-component path**:
```
wf_iphone_2025_07_claude_claude-3-haiku-20240307_narrative_20251011_103631 (74 chars)
```

**With user name**:
```
wf_july_iphone_claude_claude-3-haiku-20240307_narrative_20251011_103631 (71 chars)
```

**Assessment**: 
- 2-component adds +8 chars (reasonable)
- 3-component adds +15 chars (getting long but still manageable)
- User names can be shorter than paths (more control)

## Next Steps

1. **Review this CSV**: See if the proposed naming patterns make sense
2. **Decide on default components**: 1, 2, or 3 path components?
3. **Test user naming**: Would you want to override with custom names?
4. **Consider metadata approach**: Store name in file rather than directory name?

## Files

- **Analysis script**: `tools/analyze_workflow_naming.py`
- **Results CSV**: `workflow_naming_analysis.csv` (168 rows, 5 columns)
- **Command to re-run**: `python tools/analyze_workflow_naming.py`

## Questions for Review

1. **Readability**: Do the 2-component names (`wf_2025_07_...`) work for you?
2. **Length**: Are 3-component names too long?
3. **User override**: How often would you want to provide custom names?
4. **Metadata vs directory**: Store name in metadata file instead of directory name?
5. **Backwards compatibility**: How to handle the 168 existing workflows?
