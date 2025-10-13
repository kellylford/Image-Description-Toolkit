# Issue: Workflow Resume Overwrites Existing Descriptions (Data Loss)

## Status
🔴 **CRITICAL** - Data loss bug affecting production use

## Priority
**CRITICAL** - User lost 141 descriptions when testing resume feature

## Description
When using `--resume` on a partially completed workflow, the describe step **overwrites all existing descriptions** instead of preserving them and continuing from where it left off.

**Expected Behavior:**
- Resume should skip already-described images
- Existing descriptions should be preserved
- Only remaining images should be processed

**Actual Behavior:**
- All images are re-described from scratch
- Existing descriptions are lost/overwritten
- User reported losing 141 descriptions on resume

## Environment
- **Version**: Built executable (`idt.exe`)
- **Platform**: Windows
- **Command**: `idt workflow --resume <workflow_dir>`
- **Affected Workflow**: `C:\idtexternal\idt\Descriptions\wf_europe_ollama_gemma3_artistic_20251011_162608`

## Reproduction Steps
1. Start a workflow: `idt workflow <input_dir> --provider ollama --model gemma`
2. Let it process some images (e.g., 141 descriptions created)
3. Interrupt or let it fail partway through
4. Resume: `idt workflow --resume <workflow_dir>`
5. **BUG**: All 141 descriptions lost, workflow starts over from ~14 images

## User Report
> "Something is wrong with --resume. I used it on... it had 141 descriptions but resume caused it to start over"

## Root Cause Analysis

### How Resume is SUPPOSED to Work

**image_describer.py has skip logic** (lines 608-698):
```python
# Lines 608-626: Load progress file
already_described = set()
progress_file = Path(self.log_dir) / "image_describer_progress.txt"

if progress_file.exists():
    logger.info(f"Found progress file: {progress_file}")
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            for line in f:
                image_path_str = line.strip()
                if image_path_str:
                    already_described.add(image_path_str)
        logger.info(f"Found {len(already_described)} already-described images, will skip them")

# Lines 695-698: Skip already-described images
for i, image_path in enumerate(image_files, 1):
    if str(image_path) in already_described:
        skip_count += 1
        logger.info(f"Skipping already-described image {i} of {len(image_files)}: {image_path.name}")
        continue
```

This skip logic **should work** - but it doesn't on resume. Why?

### Why Resume Breaks the Skip Logic

**The temp_combined_images directory issue:**

1. **Original run** (`workflow.py` lines 494-590):
   - Creates `temp_combined_images` directory
   - Copies all images to temp with structured paths
   - Example path: `wf_europe_.../temp_combined_images/europe/folder/image1.jpg`
   - Calls image_describer.py with temp directory
   - image_describer writes progress file with these temp paths
   - **Temp directory is deleted after completion** (line 731)

2. **Resume run**:
   - Creates `temp_combined_images` directory AGAIN
   - Copies all images to temp with SAME structured paths ✅
   - Example path: `wf_europe_.../temp_combined_images/europe/folder/image1.jpg` ✅
   - Progress file exists with same paths ✅
   - **Should work!** Paths match, skip logic should engage

### So Why Does It Fail?

**Investigation revealed:**
- Temp directory cleanup happens at line 731: `shutil.rmtree(temp_combined_dir)`
- On resume, temp directory recreated with same paths
- Progress file still exists in `logs/image_describer_progress.txt`
- Paths in progress file SHOULD match new temp paths

**Possible causes:**
1. Progress file gets cleared/reset on resume
2. Temp directory paths are slightly different between runs
3. Working directory changes affect path resolution
4. --preserve-descriptions flag exists but was never implemented

### The --preserve-descriptions Flag (Never Implemented)

**Flag defined** (line 1271):
```python
parser.add_argument(
    "--preserve-descriptions",
    action="store_true",
    help="Skip describe step if descriptions already exist (for resume)"
)
```

**But never used!** The flag is defined but:
- `describe_images()` method doesn't check it (lines 448-750)
- No logic to skip describe step when flag is set
- Flag is passed to orchestrator but ignored

**Partial fix added** (lines 1424-1427):
```python
# Auto-enable preserve-descriptions for partial resumes
if not args.preserve_descriptions:
    print(f"INFO: Auto-enabling --preserve-descriptions to protect existing work")
    args.preserve_descriptions = True
```

**But this doesn't help!** The flag is set but `describe_images()` never checks it.

### Recent Changes (Workflow Naming)

**Question**: Did workflow naming feature break resume?

**Answer**: NO - Resume uses the same output directory:
- Line 1407: `output_dir = resume_dir` (uses existing workflow dir)
- Line 1547: `orchestrator = WorkflowOrchestrator(..., base_output_dir=output_dir)`
- Temp dir path: `{base_output_dir}/temp_combined_images` - same location ✅
- Progress file: `{base_output_dir}/logs/image_describer_progress.txt` - same location ✅

**Conclusion**: Workflow naming didn't break resume. This was a pre-existing bug.

## Current State

### Partial Fix Implemented (INCOMPLETE ⚠️)
**Commit**: "Fix workflow resume to handle workflow naming metadata"

**Changes made:**
1. Lines 1376-1407: Load workflow_metadata on resume ✅
2. Lines 1424-1427: Auto-enable args.preserve_descriptions flag ⚠️

**What's missing:**
- `describe_images()` doesn't check `self.preserve_descriptions` flag
- No logic to skip describe step when preserve flag is set
- Temp directory still recreated regardless of flag

**Current code** (lines 1511-1520):
```python
orchestrator = WorkflowOrchestrator(
    args.config, 
    base_output_dir=output_dir, 
    model=args.model, 
    prompt_style=args.prompt_style, 
    provider=args.provider, 
    api_key_file=args.api_key_file,
    preserve_descriptions=args.preserve_descriptions  # ✅ Passed to orchestrator
)
```

**Orchestrator stores it** (line 208):
```python
self.preserve_descriptions = preserve_descriptions  # ✅ Stored
```

**But describe_images() doesn't use it** (lines 448-750):
```python
def describe_images(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:
    # ❌ No check for self.preserve_descriptions
    # ❌ No logic to skip if descriptions exist
    # ❌ Always creates temp_combined_dir and re-describes
```

## Solutions

### Solution A: Skip Describe Step When Preserve Flag Set (RECOMMENDED)

Add check at start of `describe_images()` method (after line 458):

```python
def describe_images(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """Generate AI descriptions for images using image_describer.py"""
    self.logger.info("Starting image description...")
    
    # Check if preserve_descriptions flag is set and descriptions already exist
    if self.preserve_descriptions:
        desc_output_dir = self.config.get_step_output_dir("image_description")
        existing_desc_file = desc_output_dir / "descriptions.csv"
        
        if existing_desc_file.exists():
            # Count existing descriptions
            try:
                import csv
                with open(existing_desc_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    desc_count = sum(1 for row in reader)
                
                self.logger.info(f"Preserve flag set - {desc_count} descriptions exist")
                print(f"INFO: Skipping describe step ({desc_count} existing descriptions)")
                
                # Return success with existing file
                return {
                    "success": True,
                    "processed": desc_count,
                    "output_dir": desc_output_dir,
                    "description_file": str(existing_desc_file),
                    "skipped": True,
                    "reason": "preserve_descriptions flag enabled"
                }
            except Exception as e:
                self.logger.warning(f"Could not read existing descriptions: {e}")
                # Continue with normal processing
    
    # Build list of directories to search for images
    search_dirs = [input_dir]
    # ... rest of method
```

**Pros:**
- Simple and safe
- Preserves ALL existing work
- Clear user feedback
- No complex path mapping needed

**Cons:**
- Doesn't allow partial resume (can't add more images and describe only new ones)
- All-or-nothing approach

### Solution B: Don't Delete Temp Directory on Partial Completion

Modify cleanup logic (line 731):

```python
# Clean up temporary directory only if fully complete
# Keep it for resume if describe step was interrupted
try:
    if completed_successfully and not partial_completion:
        shutil.rmtree(temp_combined_dir)
        self.logger.debug(f"Cleaned up temporary directory: {temp_combined_dir}")
    else:
        self.logger.info(f"Keeping temp directory for resume: {temp_combined_dir}")
except Exception as e:
    self.logger.warning(f"Failed to clean up temporary directory: {e}")
```

**Pros:**
- Allows true resume with skip logic working
- Existing image_describer skip logic works as designed

**Cons:**
- Leaves temp directories around
- Wastes disk space
- What if user manually deletes temp dir?

### Solution C: Use Original Paths Instead of Temp Directory

Major refactor - don't copy to temp, pass original directories:

**Pros:**
- No temp directory needed
- No cleanup issues
- Resume naturally works

**Cons:**
- Large refactor required
- Multiple directories complicate image_describer
- Risk of breaking current functionality

### Solution D: Implement Path Mapping for Resume

Store mapping of temp→original paths, reconstruct on resume:

**Pros:**
- Most robust solution
- Handles all edge cases

**Cons:**
- Complex implementation
- Multiple failure points
- Over-engineered for the problem

## Recommended Solution

**Use Solution A** for immediate fix:
1. Simple and safe
2. Prevents data loss (critical requirement)
3. Can be implemented in 20 lines
4. Provides clear user feedback
5. Can enhance later if partial resume needed

**Later enhancement** (if needed):
- Implement Solution B for true partial resume
- Or add flag to force re-describe all vs preserve all

## Implementation Plan

### Phase 1: Immediate Fix (Solution A) ✅ READY TO IMPLEMENT
1. Add preserve check to `describe_images()` method
2. Test with user's workflow (141 descriptions)
3. Verify no data loss on resume
4. Commit and deploy

### Phase 2: Testing
1. Test resume with 0 descriptions (should process all)
2. Test resume with partial descriptions (should skip)
3. Test resume with complete descriptions (should skip)
4. Test normal workflow (should ignore preserve flag)

### Phase 3: Enhancement (Optional)
1. Add `--force-redescribe` flag to override preserve
2. Implement partial resume (Solution B)
3. Add progress indicator showing X/Y descriptions exist

## Related Files
- `scripts/workflow.py`:
  - Lines 448-750: `describe_images()` method (needs preserve check)
  - Line 527: temp_combined_dir creation
  - Line 731: temp_combined_dir cleanup
  - Lines 1376-1407: Resume workflow metadata loading
  - Lines 1424-1427: Auto-enable preserve flag (partial fix)
  - Line 1271: --preserve-descriptions argument definition
  - Line 208: Orchestrator stores preserve_descriptions

- `scripts/image_describer.py`:
  - Lines 608-626: Progress file loading (skip logic)
  - Lines 695-698: Skip already-described images

## Test Case
**Workflow**: `C:\idtexternal\idt\Descriptions\wf_europe_ollama_gemma3_artistic_20251011_162608`
- Original: 141 descriptions
- After resume: Lost all, restarted with ~14
- Expected: Keep 141, continue with remaining

## Resolution Checklist
- [ ] Implement Solution A (preserve check in describe_images)
- [ ] Test with user's 141-description workflow
- [ ] Verify existing descriptions preserved
- [ ] Test normal workflow (no regression)
- [ ] Update documentation
- [ ] Add integration test for resume
- [ ] Consider adding --force-redescribe flag
- [ ] Update this issue with resolution details

## Additional Context
- User was testing resume after workflow naming feature
- Workflow naming did NOT cause this bug
- Bug appears to be pre-existing
- --preserve-descriptions flag was defined but never implemented
- Critical for production use - prevents data loss

---
**Created:** October 11, 2025
**Severity:** CRITICAL - Data Loss
**Impact:** Production workflows lose hours of AI processing on resume
**User Impact:** Lost 141 descriptions in real workflow
