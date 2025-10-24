# Bug Fix: Unknown Prompt in Combined Descriptions and Stats

**Date:** October 18, 2025  
**Severity:** Medium - New prompts appeared as "unknown" in analysis outputs  
**Status:** FIXED ✅

## Summary

When a new prompt style was added to `image_describer_config.json` and used in a workflow run, both the `combine_workflow_descriptions.py` and `stats_analysis.py` scripts showed the prompt as "unknown" in their output files. This made it difficult to track and compare results from new prompts.

## Root Cause

Both analysis scripts had hardcoded lists of prompt styles instead of reading them dynamically from `image_describer_config.json`:

### combine_workflow_descriptions.py

**Location:** Line 167  
**Issue:** Hardcoded list missing prompts or with case mismatches

```python
# Old Code ❌
prompt_styles = ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic', 'simple']
```

**Problems:**
1. Had "simple" (lowercase) but config has "Simple" (capital S)
2. Would not detect any newly added prompts
3. Any prompt not in this list would show as "unknown"

### stats_analysis.py

**Location:** Line 201  
**Issue:** Similar hardcoded list, also missing "simple" entirely

```python
# Old Code ❌
prompt_styles = ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic']
```

**Problems:**
1. Missing "simple" completely
2. Would not detect newly added prompts
3. Inconsistent with combine_workflow_descriptions.py

### Why This Was a Problem

1. **Maintenance Burden:** Every time a user added a new prompt to the config, they would also need to:
   - Update combine_workflow_descriptions.py
   - Update stats_analysis.py
   - Hope they didn't miss any other scripts

2. **Case Sensitivity:** The config has "Simple" with capital S, but the hardcoded lists had "simple" lowercase. The comparison used `.lower()` in combine but not in stats.

3. **User Experience:** Workflows with new prompts showed as "unknown" in analysis files, making comparisons difficult.

## Solution

Created a centralized function to load prompt styles dynamically from the configuration file:

### New Function in analysis_utils.py

```python
def load_prompt_styles_from_config():
    """
    Load prompt styles dynamically from image_describer_config.json.
    
    Returns:
        List of lowercase prompt style names from the config file.
        Falls back to a default list if config cannot be loaded.
    """
    try:
        from scripts.config_loader import load_json_config
        
        # Load the image describer config
        config, config_path, source = load_json_config('image_describer_config.json')
        
        # Extract prompt styles from prompt_variations
        if config and 'prompt_variations' in config:
            # Convert all keys to lowercase for case-insensitive matching
            prompt_styles = [key.lower() for key in config['prompt_variations'].keys()]
            return prompt_styles
    except Exception as e:
        print(f"Warning: Could not load prompt styles from config: {e}")
    
    # Fallback list
    return ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic', 'simple']
```

### Updated combine_workflow_descriptions.py

```python
# New Code ✅
from analysis_utils import get_safe_filename, ensure_directory, load_prompt_styles_from_config

# In get_workflow_label function:
# Load prompt styles dynamically from config
prompt_styles = load_prompt_styles_from_config()

# Find the prompt style (it's the part before the datetime)
prompt_style = 'unknown'
for i, part in enumerate(parts):
    if part.lower() in prompt_styles:
        prompt_style = part
        break
```

### Updated stats_analysis.py

```python
# New Code ✅
from analysis_utils import get_safe_filename, ensure_directory, load_prompt_styles_from_config

# In parse_workflow_log function:
# Load prompt styles dynamically from config
prompt_styles = load_prompt_styles_from_config()
for i in range(3, len(parts)):
    if parts[i].lower() in prompt_styles:
        stats['prompt_style'] = parts[i]
        break
```

## Benefits

1. **Automatic Detection:** New prompts are automatically detected without code changes
2. **Single Source of Truth:** Config file is the only place to add prompts
3. **Case Insensitive:** Works regardless of capitalization in directory names
4. **Consistent:** Both scripts use the same function and behavior
5. **Robust Fallback:** If config can't be loaded, falls back to common prompts

## Testing

### Test 1: Existing "simple" Prompt

Created test workflow: `wf_ollama_moondream_simple_20241018_1234`

**Before Fix:**
- combine_workflow_descriptions.py: Detected "simple" (happened to match)
- stats_analysis.py: Showed as "unknown" (missing from hardcoded list)

**After Fix:**
- Both scripts correctly detect "simple"
- CSV output shows "simple" in Prompt column

### Test 2: New Custom "testprompt"

1. Added "testprompt" to image_describer_config.json
2. Created test workflow: `wf_ollama_moondream_testprompt_20241018_5678`

**Before Fix:**
- Both scripts showed "unknown"

**After Fix:**
- Both scripts correctly detect "testprompt"
- CSV outputs show "testprompt" in Prompt column
- No code changes needed in analysis scripts

### Test 3: Verification Commands

```bash
# Test combine script
python3 analysis/combine_workflow_descriptions.py --input-dir /tmp/test_workflows2 --output /tmp/test.csv

# Output shows:
# Prompts found:
#   testprompt: 1 descriptions  ✅

# Test stats script
python3 analysis/stats_analysis.py --input-dir /tmp/test_workflows2

# Output shows:
# Prompt: testprompt  ✅
```

## Files Changed

1. **analysis/analysis_utils.py**
   - Added `load_prompt_styles_from_config()` function
   - Added `sys` import

2. **analysis/combine_workflow_descriptions.py**
   - Updated import to include `load_prompt_styles_from_config`
   - Replaced hardcoded list with dynamic loading (line 167)

3. **analysis/stats_analysis.py**
   - Updated import to include `load_prompt_styles_from_config`
   - Replaced hardcoded list with dynamic loading (line 201)
   - Fixed case-sensitive comparison to use `.lower()`

## Related Issues

A similar bug was previously fixed in the stats command, as mentioned in the original issue. This fix completes the work by addressing the remaining analysis scripts.

## Future Improvements

1. Consider adding validation to ensure workflow directory names match expected format
2. Add logging when prompt style cannot be determined
3. Consider creating a shared workflow directory name parser utility

## Verification Steps for Users

To verify this fix works in your environment:

1. Add a new prompt to `scripts/image_describer_config.json`:
   ```json
   "prompt_variations": {
     "myprompt": "Your custom prompt description here",
     ...
   }
   ```

2. Run a workflow with the new prompt:
   ```bash
   idt.exe --prompt-style myprompt
   ```

3. Generate combined descriptions:
   ```bash
   python analysis/combine_workflow_descriptions.py
   ```

4. Verify the CSV shows "myprompt" in the Prompt column, not "unknown"

5. Generate stats:
   ```bash
   python analysis/stats_analysis.py
   ```

6. Verify the output shows "Prompt: myprompt", not "unknown"
