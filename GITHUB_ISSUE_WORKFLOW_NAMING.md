# GitHub Issue: Restructure Workflow Directory Naming Format

**Copy and paste this content into a new GitHub issue:**

---

## 🔄 Restructure Workflow Directory Naming Format

### **Issue Type:** Enhancement
### **Priority:** Medium (Post 2.0 Release)
### **Labels:** `enhancement`, `breaking-change`, `post-2.0`, `long-term-fix`

---

### **Problem Statement**

The current workflow directory naming structure is not optimal for readability and sorting:

**Current Format:**
```
wf_<name>_<provider>_<model>_<prompt>_<date>
Example: wf_cottage_ollama_qwen3-vl_235b-cloud_technical_20251021_005858
```

**Desired Format:**
```
wf_<name>_<prompt>_<model>_<date>  
Example: wf_cottage_technical_qwen3-vl_235b-cloud_20251021_005858
```

### **Benefits of Change**
- **Better Grouping:** Related workflows (same name/prompt) will sort together
- **Improved Readability:** Prompt style is more prominent for quick identification
- **Logical Flow:** Name → Prompt → Model → Date follows workflow decision order
- **Long-term Maintainability:** Correct structure from the start, no legacy baggage

### **Impact Analysis**

#### **🚨 Breaking Changes - Tools That Will Break:**

1. **`scripts/list_results.py`** - **CRITICAL**
   - **Location:** Lines 60-140
   - **Issue:** Provider detection logic expects provider after name
   - **Current:** `parts[1]` assumed to be provider
   - **Impact:** Viewer and CLI result listing show incorrect metadata

2. **`analysis/combine_workflow_descriptions.py`** - **HIGH**
   - **Location:** Lines 230-290, function `get_workflow_label()`
   - **Issue:** `provider = parts[1].capitalize()` and `model_part = parts[2]`
   - **Impact:** CSV export shows incorrect/garbled model labels

3. **`analysis/stats_analysis.py`** - **HIGH**
   - **Location:** Around line 475
   - **Issue:** Similar parsing logic to combine_workflow_descriptions.py
   - **Impact:** Performance statistics analysis shows wrong provider/model info

4. **`tools/rename_workflows_with_paths.py`** - **MEDIUM**
   - **Location:** Lines 95-140, function `parse_workflow_dirname()`
   - **Issue:** Generic parsing that works backward from timestamp
   - **Impact:** Tool functions but output format may be confusing

5. **`tools/analyze_workflow_naming.py`** - **MEDIUM**
   - **Location:** Lines 88-147
   - **Issue:** Similar generic parsing approach
   - **Impact:** Analysis accuracy reduced but still functional

#### **✅ Tools That Will Continue Working:**

- **`viewer/viewer.py`** - Only checks `wf_` prefix
- **`workflow.py` resume** - Uses directory structure, not name parsing
- **All file operations** - Independent of naming structure

### **Implementation Plan**

**🎯 APPROACH: Clean Break - Correct Long-term Solution**

*After 2.0 release, we will implement the right solution. Existing tools breaking is acceptable for the long-term benefit.*

#### **Phase 1: Update Directory Creation**
- [ ] Modify `scripts/workflow.py` line 1960:
  ```python
  # Current
  wf_dirname = f"wf_{workflow_name}_{provider_name}_{model_name}_{prompt_style}_{timestamp}"
  
  # New (CORRECT FORMAT)
  wf_dirname = f"wf_{workflow_name}_{prompt_style}_{model_name}_{timestamp}"
  ```
  **Note:** Removing provider from directory name entirely - it's redundant with model info.

#### **Phase 2: Update All Parsing Functions (Clean Rewrite)**
- [ ] **`scripts/list_results.py`**
  - **REWRITE** `parse_directory_name()` function for new format only
  - New logic: `wf_<name>_<prompt>_<model>_<timestamp>`
  - No backward compatibility - clean implementation

- [ ] **`analysis/combine_workflow_descriptions.py`**
  - **REWRITE** `get_workflow_label()` function for new format
  - Simplified parsing without provider detection
  - Focus on model and prompt extraction

- [ ] **`analysis/stats_analysis.py`**
  - **REWRITE** parsing logic for new format
  - Clean, maintainable code without legacy support

- [ ] **`tools/rename_workflows_with_paths.py`**
  - **REWRITE** for new format only
  - Simpler logic without provider handling

- [ ] **`tools/analyze_workflow_naming.py`**
  - **REWRITE** for new format
  - Clean parsing implementation

#### **Phase 3: Documentation and Examples**
- [ ] Update all help text examples
- [ ] Update documentation with new format
- [ ] Clear migration notes for users

#### **Phase 4: Testing**
- [ ] Test all tools with new format only
- [ ] Verify all analysis functions work correctly
- [ ] Validate workflow creation and resume

### **Technical Details**

#### **Current Parsing Logic Example (list_results.py):**
```python
# Find provider by scanning for known values
provider_idx = -1
for i, part in enumerate(before_timestamp):
    if part.lower() in ['ollama', 'openai', 'claude']:
        provider_idx = i
        metadata['provider'] = part
        break
```

#### **Proposed New Logic:**
```python
# More flexible parsing that doesn't assume positions
# 1. Find timestamp (works backward)
# 2. Extract prompt style (known list)
# 3. Remaining middle parts = provider + model
# 4. First part = name
```

### **Files to Update**

#### **Core Parsing Functions:**
- `scripts/list_results.py` (lines 63-130)
- `analysis/combine_workflow_descriptions.py` (lines 230-290)
- `analysis/stats_analysis.py` (around line 475)
- `tools/rename_workflows_with_paths.py` (lines 98-140)
- `tools/analyze_workflow_naming.py` (lines 88-147)

#### **Directory Creation:**
- `scripts/workflow.py` (line 1960)

#### **Documentation:**
- Help examples in various files showing old format
- Any README or documentation files with directory examples

### **Migration Strategy**

**🔥 BREAKING CHANGE APPROACH - Clean Break After 2.0**

1. **Complete format change** - no backward compatibility
2. **Clear release notes** explaining the breaking change
3. **User migration guidance** - manual directory renaming if desired
4. **Fresh start** - all new workflows use correct format immediately

**User Impact:**
- Existing workflow directories will still contain valid data
- Analysis tools will need to be run on new-format directories only
- Users can manually rename old directories if they want unified analysis
- Old workflow data remains accessible via direct file browsing

### **Testing Checklist**

- [ ] Create workflows with new naming format only
- [ ] Test `idt results-list` with new format directories
- [ ] Verify `idt combinedescriptions` works correctly with new format
- [ ] Test `idt stats` analysis accuracy with new format
- [ ] Check viewer functionality with new format
- [ ] Validate workflow resume works with new format
- [ ] Test all tools in `tools/` directory with new format
- [ ] Verify clean error messages when encountering old format directories

### **Definition of Done**

- [ ] New workflows created use the correct naming structure only
- [ ] All parsing functions rewritten for new format (clean code)
- [ ] All analysis tools work correctly with new format
- [ ] Clear error handling when encountering old format directories
- [ ] Documentation updated with new format examples
- [ ] Comprehensive testing completed with new format only
- [ ] Release notes clearly document the breaking change

### **Notes**

- **Target for post-2.0 release** - clean break approach
- **Breaking change by design** - prioritizing long-term correctness
- **No backward compatibility** - cleaner codebase and maintenance
- **User education** - clear documentation of the change and benefits
- **Fresh start** - all new code written for correct format only

### **Proposed New Format Details**

**Simplified Structure:**
```
wf_<name>_<prompt>_<model>_<date>
```

**Examples:**
```
Current: wf_cottage_ollama_qwen3-vl_235b-cloud_technical_20251021_005858
New:     wf_cottage_technical_qwen3-vl_235b-cloud_20251021_005858

Current: wf_photos_claude_claude-3-haiku-20240307_narrative_20251021_120000  
New:     wf_photos_narrative_claude-3-haiku-20240307_20251021_120000
```

**Benefits of Simplified Format:**
- **No provider redundancy** - provider info is embedded in model name
- **Cleaner parsing** - fewer components to handle
- **Better sorting** - workflows group by name, then prompt
- **Future-proof** - easier to extend without additional complexity

---

### **Related Issues/PRs**
- None currently

### **Additional Context**
This enhancement was identified during reliability improvements in October 2025. The current format works but is not optimal for workflow organization and identification.