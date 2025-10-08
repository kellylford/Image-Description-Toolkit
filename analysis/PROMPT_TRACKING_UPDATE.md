# Prompt Tracking Update for analyze_workflow_stats.py

**Date:** 2025-01-XX  
**Updated File:** `analyze_workflow_stats.py`  
**Purpose:** Add prompt style tracking to timing and statistics analysis

## Summary

The workflow statistics analysis script has been updated to extract, track, and display the prompt style used in each workflow run. This enables comparison of model performance across different prompt styles (narrative, detailed, concise, technical, creative, colorful, artistic).

## Changes Made

### 1. Prompt Extraction from Directory Name
**Location:** `parse_workflow_log()` function (lines 56-77)

- Added `prompt_style` field to stats dictionary
- Extracts prompt from workflow directory name format: `wf_PROVIDER_MODEL_[VARIANT]_PROMPTSTYLE_DATETIME`
- Searches for known prompt styles in directory name parts
- Handles models with and without variant specifications

**Known Prompt Styles:**
- narrative
- detailed
- concise
- technical
- creative
- colorful
- artistic

**Example Extraction:**
```
wf_ollama_llava_7b_artistic_20251007_223811
→ Provider: ollama, Model: llava, Variant: 7b, Prompt: artistic

wf_claude_claude-opus-4-1_colorful_20251008_024912
→ Provider: claude, Model: claude-opus-4-1, Prompt: colorful
```

### 2. CSV Output Enhancement
**Location:** `save_stats_csv()` function (lines 628-715)

**Added Column:**
- "Prompt" column inserted after "Model" column (4th column)
- Shows prompt style for each workflow
- Empty string if prompt not detected

**New CSV Structure:**
```csv
Workflow,Provider,Model,Prompt,Total Files in Workflow,...
Claude Opus 4.1,claude,claude-opus-4-1,artistic,42,...
OpenAI GPT-4o,openai,gpt-4o,colorful,42,...
```

### 3. Comparison Table Display
**Location:** `print_comparison_table()` function (lines 505-533)

**Updates:**
- Added "Prompt" column between "Workflow" and "Files" columns
- Increased table width from 100 to 115 characters
- Shows "N/A" if prompt not detected

**Example Output:**
```
Workflow                       Prompt       Files    Duration    Avg/Image    Min      Max      Median  
-------------------------------------------------------------------------------------------------------------------
Claude Opus 4.1                artistic     42       5m 23s      7.68s        5.23s    12.45s   7.12s   
OpenAI GPT-4o                  colorful     42       3m 12s      4.57s        3.89s    8.23s    4.34s   
Ollama LLaVA 7B                narrative    42       12m 45s     18.21s       15.67s   25.34s   17.89s  
```

### 4. Rankings Display
**Location:** `print_rankings()` function (lines 536-573)

**Updates:**
- All three ranking categories now show prompt style in parentheses
- Speed ranking: `Claude Opus 4.1 (artistic) 7.68s/image`
- Consistency ranking: `OpenAI GPT-4o (colorful) Range: 4.34s`
- Throughput ranking: `Claude Opus 4.1 (artistic) 7.8 images/minute`

**Example Output:**
```
🏆 Fastest Average Processing Time:
  1. OpenAI GPT-4o            (colorful)   4.57s/image
  2. Claude Opus 4.1          (artistic)   7.68s/image
  3. Ollama LLaVA 7B          (narrative)  18.21s/image

📊 Most Consistent Processing Time:
  1. OpenAI GPT-4o            (colorful)   Range: 4.34s (min: 3.89s, max: 8.23s)
  2. Claude Opus 4.1          (artistic)   Range: 7.22s (min: 5.23s, max: 12.45s)
  3. Ollama LLaVA 7B          (narrative)  Range: 9.67s (min: 15.67s, max: 25.34s)
```

### 5. Individual Workflow Stats
**Location:** `print_workflow_stats()` function (lines 441-443)

**Updates:**
- Shows prompt style directly under workflow name
- Only displays if prompt detected

**Example Output:**
```
Claude Opus 4.1
Prompt: artistic
--------------------------------------------------------------------------------
  Start Time:              2025-01-07 22:38:11
  End Time:                2025-01-07 22:43:34
  Total Duration:          5m 23s (5.4 minutes)
  Files Processed:         42
  ...
```

## Use Cases

### Compare Same Model with Different Prompts
```csv
Workflow,Provider,Model,Prompt,Avg Time/Description
Claude Opus 4.1,claude,claude-opus-4-1,artistic,7.68
Claude Opus 4.1,claude,claude-opus-4-1,colorful,7.45
Claude Opus 4.1,claude,claude-opus-4-1,narrative,8.12
```

**Analysis:** Which prompt style produces faster results for a specific model?

### Compare Different Models with Same Prompt
```csv
Workflow,Provider,Model,Prompt,Avg Time/Description
Claude Opus 4.1,claude,claude-opus-4-1,artistic,7.68
OpenAI GPT-4o,openai,gpt-4o,artistic,4.57
Ollama LLaVA 7B,ollama,llava,artistic,18.21
```

**Analysis:** Which model is fastest for a specific prompt style?

### Identify Prompt Impact on Performance
- **Speed:** Is "concise" faster than "detailed"?
- **Consistency:** Does "narrative" produce more variable timing?
- **Cost:** Do longer prompts increase token usage?

## Backward Compatibility

- Scripts without prompt styles in directory name will show:
  - CSV: Empty Prompt column
  - Table: "N/A" in Prompt column
  - Rankings: No prompt shown in parentheses
- All existing functionality preserved
- No breaking changes to output format (only additions)

## Testing Recommendations

1. **Run with multiple prompts:**
   ```bash
   python analyze_workflow_stats.py
   ```

2. **Check CSV output:**
   - Verify "Prompt" column appears after "Model"
   - Confirm prompt values are correctly extracted
   - Check that workflows without prompts show empty strings

3. **Review comparison table:**
   - Verify prompt column displays correctly
   - Check table alignment with new column

4. **Examine rankings:**
   - Confirm prompt appears in parentheses
   - Verify rankings are still ordered correctly

## Files Modified

- `analysis/analyze_workflow_stats.py` - Complete prompt tracking implementation

## Related Files

- `analysis/combine_workflow_descriptions.py` - Already has prompt tracking (completed earlier)
- `analysis/analyze_description_content.py` - Works with combined CSV (includes prompts)

## Next Steps (Optional Enhancements)

1. **Prompt-based filtering:** Add `--prompt` argument to analyze only specific prompt styles
2. **Prompt comparison report:** Generate dedicated comparison of same model across prompts
3. **Statistical analysis:** Calculate if prompt style significantly affects performance
4. **Visualization:** Chart showing timing distribution by prompt style

## Example Complete Output

```
================================================================================
                            COMPARISON TABLE                            
================================================================================

Workflow                       Prompt       Files    Duration    Avg/Image    Min      Max      Median  
-------------------------------------------------------------------------------------------------------------------
Claude Opus 4.1                artistic     42       5m 23s      7.68s        5.23s    12.45s   7.12s   
Claude Opus 4.1                colorful     42       5m 18s      7.57s        5.12s    11.89s   7.01s   
OpenAI GPT-4o                  artistic     42       3m 12s      4.57s        3.89s    8.23s    4.34s   
OpenAI GPT-4o                  colorful     42       3m 8s       4.48s        3.78s    7.98s    4.21s   
Ollama LLaVA 7B                artistic     42       12m 45s     18.21s       15.67s   25.34s   17.89s  
Ollama LLaVA 7B                colorful     42       13m 2s      18.62s       16.01s   26.12s   18.23s  

================================================================================
                                RANKINGS                                
================================================================================

🏆 Fastest Average Processing Time:
  1. OpenAI GPT-4o            (colorful)   4.48s/image
  2. OpenAI GPT-4o            (artistic)   4.57s/image
  3. Claude Opus 4.1          (colorful)   7.57s/image
  4. Claude Opus 4.1          (artistic)   7.68s/image
  5. Ollama LLaVA 7B          (artistic)   18.21s/image
  6. Ollama LLaVA 7B          (colorful)   18.62s/image

📊 Most Consistent Processing Time:
  1. OpenAI GPT-4o            (colorful)   Range: 4.20s (min: 3.78s, max: 7.98s)
  2. OpenAI GPT-4o            (artistic)   Range: 4.34s (min: 3.89s, max: 8.23s)
  3. Claude Opus 4.1          (colorful)   Range: 6.77s (min: 5.12s, max: 11.89s)
  4. Claude Opus 4.1          (artistic)   Range: 7.22s (min: 5.23s, max: 12.45s)
  5. Ollama LLaVA 7B          (artistic)   Range: 9.67s (min: 15.67s, max: 25.34s)
  6. Ollama LLaVA 7B          (colorful)   Range: 10.11s (min: 16.01s, max: 26.12s)

⚡ Highest Throughput (images/minute):
  1. OpenAI GPT-4o            (colorful)   13.4 images/minute
  2. OpenAI GPT-4o            (artistic)   13.1 images/minute
  3. Claude Opus 4.1          (colorful)   7.9 images/minute
  4. Claude Opus 4.1          (artistic)   7.8 images/minute
  5. Ollama LLaVA 7B          (artistic)   3.3 images/minute
  6. Ollama LLaVA 7B          (colorful)   3.2 images/minute
```

## Conclusion

The analyze_workflow_stats.py script now provides complete prompt tracking across all output formats, enabling detailed comparison of model performance across different prompt styles. This complements the earlier update to combine_workflow_descriptions.py, providing comprehensive prompt tracking across the entire analysis toolkit.
