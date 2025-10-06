# Model Removal Plan - Technical Specification

**Date:** October 6, 2025  
**Goal:** Remove ONNX, HuggingFace, GroundingDINO, YOLO, and Copilot+ providers  
**Keep:** Claude, Ollama (including Ollama Cloud), OpenAI  
**Add Later:** Google Gemini (Phase 3)

---

## Providers to Remove

1. ❌ **ONNX** (ONNXProvider) - Enhanced Ollama with YOLO
2. ❌ **HuggingFace** (HuggingFaceProvider) - Local transformer models
3. ❌ **GroundingDINO** (GroundingDINOProvider) - Object detection
4. ❌ **GroundingDINO Hybrid** (GroundingDINOHybridProvider) - Detection + Description
5. ❌ **YOLO** (ObjectDetectionProvider) - Object detection
6. ❌ **Copilot+** (CopilotProvider) - NPU-based processing

---

## Files That Need Modification

### Core Provider Files

#### 1. `imagedescriber/ai_providers.py`
**Classes to Remove:**
- `HuggingFaceProvider`
- `ONNXProvider`
- `CopilotProvider`
- `ObjectDetectionProvider`
- `GroundingDINOProvider`
- `GroundingDINOHybridProvider`

**Constants to Remove:**
- `DEV_HUGGINGFACE_MODELS`
- All ONNX-related constants
- All GroundingDINO constants

**Global Instances to Remove:**
- `_huggingface_provider`
- `_onnx_provider`
- `_copilot_provider`
- `_object_detection_provider`
- `_grounding_dino_provider`
- `_grounding_dino_hybrid_provider`

**Functions to Update:**
- `get_available_providers()` - Remove registration of deleted providers
- `get_all_providers()` - Remove from dictionary

**Expected Remaining:**
```python
_ollama_provider = OllamaProvider()
_ollama_cloud_provider = OllamaCloudProvider()
_openai_provider = OpenAIProvider()
_claude_provider = ClaudeProvider()

def get_all_providers():
    return {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
    }
```

---

#### 2. `imagedescriber/imagedescriber.py`

**Imports to Remove:**
```python
# Remove from import statement:
HuggingFaceProvider, ONNXProvider, CopilotProvider, ObjectDetectionProvider,
_huggingface_provider, _onnx_provider, _copilot_provider, _object_detection_provider,
_grounding_dino_provider, _grounding_dino_hybrid_provider
```

**Hardcoded Dictionaries to Update (4 locations):**

1. **Image Tab - `populate_models()` (line ~2169)**
```python
all_providers = {
    'ollama': _ollama_provider,
    'ollama_cloud': _ollama_cloud_provider,
    'openai': _openai_provider,
    'claude': _claude_provider,
}
```

2. **Chat Tab - `populate_providers()` (line ~2448)**
```python
all_providers = {
    'ollama': _ollama_provider,
    'ollama_cloud': _ollama_cloud_provider,
    'openai': _openai_provider,
    'claude': _claude_provider,
}
```

3. **Chat Tab - `populate_models()` (line ~2476)**
```python
all_providers = {
    'ollama': _ollama_provider,
    'ollama_cloud': _ollama_cloud_provider,
    'openai': _openai_provider,
    'claude': _claude_provider,
}
```

4. **Regenerate Dialog** (line ~7457)
```python
all_providers = {
    'ollama': _ollama_provider,
    'ollama_cloud': _ollama_cloud_provider,
    'openai': _openai_provider,
    'claude': _claude_provider,
}
```

**Status Messages to Remove:**
- All references to "ONNX", "Enhanced Ollama", "YOLO"
- All HuggingFace status messages
- All Copilot+ status messages
- All GroundingDINO status messages

**Display Names to Remove:**
```python
provider_display_names = {
    "ollama": "Ollama",
    "ollama_cloud": "Ollama Cloud",
    "openai": "OpenAI",
    "claude": "Claude",
    # Remove: onnx, huggingface, copilot, object_detection, etc.
}
```

**Chat Processing to Remove:**
- `process_with_huggingface_chat()`
- Any ONNX-specific chat methods
- Any Copilot-specific chat methods

---

#### 3. `scripts/workflow.py`

**Argument Choices to Update:**
```python
parser.add_argument(
    "--provider",
    choices=["ollama", "openai", "claude"],  # Remove: onnx, copilot, huggingface, groundingdino
    default="ollama",
    help="AI provider to use for image description (default: ollama)"
)
```

**Help Text Examples to Update:**
Remove examples showing:
- `--provider onnx`
- `--provider copilot`
- `--provider huggingface`
- `--provider groundingdino`
- `--provider groundingdino+ollama`

**Provider Initialization to Update:**
Remove code blocks that initialize removed providers

---

#### 4. `models/provider_configs.py`

**Remove Provider Configurations:**
```python
# Remove entire entries for:
PROVIDER_CAPABILITIES = {
    # Keep: Ollama, OpenAI, Claude
    # Remove: ONNX, HuggingFace, Copilot, ObjectDetection, GroundingDINO
}
```

---

#### 5. `models/manage_models.py`

**Remove Provider-Specific Management:**
- ONNX model download logic
- HuggingFace model management
- GroundingDINO installation code
- Any YOLO weight management

---

#### 6. `models/check_models.py`

**Remove Detection Logic for:**
- ONNX models
- HuggingFace models
- GroundingDINO models
- YOLO weights
- Copilot+ NPU availability

---

### Batch Files

#### 7. `BatForScripts/` Directory

**Files to Delete:**
- `run_onnx.bat`
- `run_huggingface.bat`
- `run_copilot.bat`
- Any GroundingDINO-related batch files

**Files to Keep:**
- `run_ollama.bat`
- `run_openai.bat`
- `run_claude.bat`

---

### Documentation Files

#### 8. `docs/` Directory

**Files to Delete or Archive:**
- `ONNX_GUIDE.md`
- `ONNX_VS_COPILOT_PROVIDERS.md`
- `HUGGINGFACE_GUIDE.md`
- `COPILOT_PC_NPU_SETUP.md`
- `COPILOT_PC_PROVIDER_GUIDE.md`
- `COPILOT_NPU_BLIP_SOLUTION.md`
- `GROUNDINGDINO_GUIDE.md`
- `GROUNDINGDINO_IMPLEMENTATION_COMPLETE.md`
- `GROUNDINGDINO_QUICK_REFERENCE.md`
- `GROUNDINGDINO_TESTING_CHECKLIST.md`

**Files to Update:**
- `MODEL_SELECTION_GUIDE.md` - Remove ONNX, HF, Copilot sections
- `CONFIGURATION.md` - Remove provider-specific sections
- `README.md` - Update provider list
- `docs/README.md` - Update documentation index

#### 9. `imagedescriber/` Documentation

**Files to Delete:**
- `HYBRID_MODE_GUIDE.md` (GroundingDINO)
- `GROUNDINGDINO_*.md` files
- Any ONNX-specific documentation

---

### Additional Directories

#### 10. `imagedescriber/onnx_models/`
**Action:** Already in .gitignore, but add note in README that this is deprecated

#### 11. `tests/` Directory
**Remove:**
- Tests specific to removed providers
- Keep: General workflow tests, Ollama/OpenAI/Claude tests

---

## Implementation Strategy

### Recommended Order

**Step 1: Create Feature Branch**
```bash
git checkout -b simplify-providers
```

**Step 2: Remove Providers One at a Time** (Separate commits)

**Commit 1: Remove HuggingFace**
- Remove HuggingFaceProvider from ai_providers.py
- Remove all HF references from imagedescriber.py
- Remove HF from workflow.py choices
- Delete run_huggingface.bat
- Delete HUGGINGFACE_GUIDE.md
- Test: Verify app starts and other providers work

**Commit 2: Remove ONNX**
- Remove ONNXProvider from ai_providers.py
- Remove all ONNX references from imagedescriber.py
- Remove ONNX from workflow.py choices
- Delete run_onnx.bat
- Delete ONNX_GUIDE.md, ONNX_VS_COPILOT_PROVIDERS.md
- Test: Verify app starts and other providers work

**Commit 3: Remove Copilot+**
- Remove CopilotProvider from ai_providers.py
- Remove all Copilot references from imagedescriber.py
- Remove Copilot from workflow.py choices
- Delete run_copilot.bat
- Delete COPILOT_*.md files
- Test: Verify app starts and other providers work

**Commit 4: Remove GroundingDINO & YOLO**
- Remove GroundingDINOProvider, GroundingDINOHybridProvider
- Remove ObjectDetectionProvider
- Remove all detection references
- Delete GroundingDINO batch files
- Delete GROUNDINGDINO_*.md files
- Test: Verify app starts and other providers work

**Commit 5: Update Documentation**
- Update MODEL_SELECTION_GUIDE.md
- Update CONFIGURATION.md
- Update README.md
- Update docs/README.md
- Test: Verify links work, no dead references

**Commit 6: Clean Up Models Directory**
- Update manage_models.py
- Update check_models.py
- Update provider_configs.py
- Test: Model management commands work

**Step 3: Comprehensive Testing**
- Test all three providers (Claude, Ollama, OpenAI)
- Test workflow scripts
- Test ImageDescriber GUI
- Test import/resume functionality
- Test batch processing

**Step 4: Merge to Main Branch**
```bash
git checkout ImageDescriber
git merge simplify-providers
git push origin ImageDescriber
```

---

## Testing Checklist

### After Each Provider Removal
- [ ] Application starts without errors
- [ ] No import errors in console
- [ ] Remaining providers appear in dropdowns
- [ ] Can select models for remaining providers
- [ ] Can generate test description with remaining providers

### After All Removals
- [ ] Ollama provider works (local models)
- [ ] Ollama Cloud provider works
- [ ] OpenAI provider works (with API key)
- [ ] Claude provider works (with API key)
- [ ] Workflow script --provider choices correct
- [ ] Batch files work
- [ ] Import workflow functionality works
- [ ] Resume workflow functionality works
- [ ] Video extraction works
- [ ] HEIC conversion works
- [ ] HTML gallery generation works
- [ ] Chat tab works for all providers
- [ ] Regenerate dialog shows only valid providers
- [ ] No errors in console/logs

---

## Files Modified Summary

### Files to Modify (~10 files)
1. `imagedescriber/ai_providers.py` - Remove 6 provider classes
2. `imagedescriber/imagedescriber.py` - Remove imports, update 4 dictionaries
3. `scripts/workflow.py` - Update choices, remove examples
4. `models/provider_configs.py` - Remove configurations
5. `models/manage_models.py` - Remove management code
6. `models/check_models.py` - Remove detection code
7. `docs/MODEL_SELECTION_GUIDE.md` - Remove provider sections
8. `docs/CONFIGURATION.md` - Remove provider sections
9. `docs/README.md` - Update index
10. `README.md` - Update provider list

### Files to Delete (~15+ files)
- `BatForScripts/run_onnx.bat`
- `BatForScripts/run_huggingface.bat`
- `BatForScripts/run_copilot.bat`
- `BatForScripts/run_groundingdino*.bat`
- `docs/ONNX_GUIDE.md`
- `docs/ONNX_VS_COPILOT_PROVIDERS.md`
- `docs/HUGGINGFACE_GUIDE.md`
- `docs/COPILOT_PC_NPU_SETUP.md`
- `docs/COPILOT_PC_PROVIDER_GUIDE.md`
- `docs/COPILOT_NPU_BLIP_SOLUTION.md`
- `docs/GROUNDINGDINO_GUIDE.md`
- `docs/GROUNDINGDINO_IMPLEMENTATION_COMPLETE.md`
- `docs/GROUNDINGDINO_QUICK_REFERENCE.md`
- `docs/GROUNDINGDINO_TESTING_CHECKLIST.md`
- `imagedescriber/HYBRID_MODE_GUIDE.md`
- `imagedescriber/GROUNDINGDINO_*.md`

### Provider-Specific Files to Check
- Prompt editor (if it has provider-specific logic)
- Viewer (if it has provider-specific display)
- Any test files specific to removed providers

---

## Rollback Plan

If issues are discovered:

1. **Individual commit rollback:**
   ```bash
   git revert <commit-hash>
   ```

2. **Full branch rollback:**
   ```bash
   git checkout ImageDescriber
   git branch -D simplify-providers
   ```

3. **Cherry-pick specific fixes:**
   ```bash
   git cherry-pick <good-commit-hash>
   ```

---

## Estimated Lines of Code Impact

**Removed:**
- ~2,000-3,000 lines from ai_providers.py
- ~500-800 lines from imagedescriber.py
- ~200-300 lines from workflow.py
- ~100-200 lines from models scripts
- ~2,000+ lines of documentation

**Total:** ~5,000-6,500 lines of code removed

**Result:** Simpler, more maintainable codebase

---

## Success Criteria

**Definition of Done:**
1. All 6 providers removed cleanly
2. No import errors or exceptions
3. All 3 remaining providers work correctly
4. All workflow features work (import, resume, batch)
5. Documentation updated and accurate
6. Comprehensive testing completed
7. Changes merged to main branch

---

**Last Updated:** October 6, 2025  
**Status:** Ready for execution pending approval
