# Comprehensive Toolkit Refactoring Plan

## Overview
Major refactoring to improve organization, consistency, and functionality based on user feedback.

## Issues to Address

### 1. ✅ Copilot+ PC Support (User Has Hardware!)
**Current:** Placeholder implementation
**Target:** Full NPU acceleration support
**Priority:** HIGH

### 2. 🗂️ Model Organization
**Current:** Files scattered (check_models.py, manage_models.py in root, yolov8x.pt in root)
**Target:** All model-related files in `models/` directory
**Priority:** HIGH

### 3. 🔌 Provider Integration in Scripts
**Current:** Unknown if all providers work in scripts (OpenAI, etc.)
**Target:** All providers fully functional in scripts and GUI
**Priority:** HIGH

### 4. ❌ Remove GUI Model Manager
**Current:** ModelManagerDialog in imagedescriber.py
**Target:** Remove in-app model manager, use external tools
**Priority:** MEDIUM

### 5. 🎯 Prompt Support Consistency
**Current:** Some providers don't support prompts, UI inconsistent
**Target:** Hide prompt UI for non-prompt providers consistently
**Priority:** MEDIUM

### 6. ⚙️ Model Options/Parameters
**Current:** Limited options support, inconsistent across providers
**Target:** Generic and provider-specific options framework
**Priority:** MEDIUM

---

## Implementation Plan

### PHASE 1: File Organization (Models Directory)

#### Step 1.1: Create Models Directory Structure
```
models/
├── __init__.py
├── check_models.py (moved from root)
├── manage_models.py (moved from root)
├── model_registry.py (new - centralized registry)
├── provider_configs.py (new - provider capabilities)
├── downloads/
│   └── yolov8x.pt (moved from root)
└── onnx/
    └── (symlink to imagedescriber/onnx_models/)
```

#### Step 1.2: Update All Import Paths
- Scripts: `from models.check_models import ...`
- GUI: `from models.manage_models import ...`
- Providers: `from models.model_registry import ...`

#### Step 1.3: Update Documentation
- README.md references
- QUICK_START.md references
- All docs/ files

### PHASE 2: Copilot+ PC Full Implementation

#### Step 2.1: DirectML Setup
```python
# In models/copilot_npu.py
import onnxruntime as ort

def create_npu_session(model_path):
    providers = ['DmlExecutionProvider']  # DirectML for NPU
    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, sess_options=session_options, providers=providers)
```

#### Step 2.2: Download Florence-2 ONNX Model
```bash
# Add to models/download_florence2.py
from transformers import AutoModelForVision2Seq
import torch

model = AutoModelForVision2Seq.from_pretrained("microsoft/Florence-2-base")
# Export to ONNX format for NPU
```

#### Step 2.3: Implement Real Inference
- Load Florence-2 ONNX model
- Configure DirectML execution provider
- Process images through NPU
- Decode outputs to text

### PHASE 3: Provider Integration in Scripts

#### Step 3.1: OpenAI Integration
**File:** `scripts/image_describer.py`

Current check:
```python
# Does it support OpenAI provider?
```

Add:
```python
def get_provider_instance(provider_name):
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    # ... etc
```

#### Step 3.2: Add Provider Selection to Scripts
```bash
python scripts/image_describer.py photos/ --provider openai --model gpt-4o-mini
python scripts/image_describer.py photos/ --provider ollama --model llava:7b
python scripts/image_describer.py photos/ --provider onnx --model blip-base
```

#### Step 3.3: Workflow Provider Support
Update `workflow.py` to support all providers in config.

### PHASE 4: Remove GUI Model Manager

#### Step 4.1: Remove Code
- Remove `ModelManagerDialog` class (line ~2981)
- Remove menu action (line ~4751-4753)
- Remove `show_model_manager()` method (line ~8461)

#### Step 4.2: Add External Tool Launch
Replace with:
```python
def launch_model_manager(self):
    """Launch external model manager"""
    subprocess.Popen(['python', 'models/manage_models.py', 'list'])
```

Or simply remove entirely and rely on command-line tools.

### PHASE 5: Prompt Support Consistency

#### Step 5.1: Provider Capabilities Registry
```python
# models/provider_configs.py
PROVIDER_CAPABILITIES = {
    "Ollama": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"]
    },
    "OpenAI": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative"]
    },
    "ONNX": {
        "supports_prompts": False,  # Pure image captioning
        "supports_custom_prompts": False,
        "prompt_styles": []
    },
    "ObjectDetection": {
        "supports_prompts": False,
        "supports_custom_prompts": False,
        "prompt_styles": []
    },
    "HuggingFace": {
        "supports_prompts": False,
        "supports_custom_prompts": False,
        "prompt_styles": []
    },
    "Copilot+ PC": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "quick"]
    }
}
```

#### Step 5.2: Dynamic UI Visibility
```python
def update_prompt_ui_visibility(self):
    """Show/hide prompt UI based on selected provider"""
    provider = self.provider_combo.currentText()
    capabilities = PROVIDER_CAPABILITIES.get(provider, {})
    
    supports_prompts = capabilities.get("supports_prompts", False)
    
    # Show/hide prompt UI elements
    self.prompt_label.setVisible(supports_prompts)
    self.prompt_combo.setVisible(supports_prompts)
    self.custom_prompt_label.setVisible(supports_prompts)
    self.custom_prompt_text.setVisible(supports_prompts)
```

#### Step 5.3: Connect to Provider Selection
```python
self.provider_combo.currentTextChanged.connect(self.update_prompt_ui_visibility)
```

### PHASE 6: Model Options Framework

#### Step 6.1: Generic Options
```python
# models/model_options.py
GENERIC_OPTIONS = {
    "temperature": {
        "type": "float",
        "range": [0.0, 2.0],
        "default": 0.7,
        "description": "Controls randomness in output"
    },
    "max_tokens": {
        "type": "int",
        "range": [50, 2000],
        "default": 500,
        "description": "Maximum response length"
    },
    "top_p": {
        "type": "float",
        "range": [0.0, 1.0],
        "default": 0.9,
        "description": "Nucleus sampling parameter"
    }
}
```

#### Step 6.2: Provider-Specific Options
```python
PROVIDER_SPECIFIC_OPTIONS = {
    "Ollama": {
        "num_ctx": {
            "type": "int",
            "range": [1024, 8192],
            "default": 2048,
            "description": "Context window size"
        }
    },
    "ONNX": {
        "use_gpu": {
            "type": "bool",
            "default": True,
            "description": "Use GPU acceleration if available"
        },
        "yolo_confidence": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.35,
            "description": "YOLO detection confidence threshold"
        }
    },
    "GroundingDINO": {
        "box_threshold": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.35,
            "description": "Detection box threshold"
        },
        "text_threshold": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.25,
            "description": "Text matching threshold"
        }
    }
}
```

#### Step 6.3: GUI Options Panel
```python
class ModelOptionsPanel(QWidget):
    """Dynamic options panel based on selected provider"""
    
    def __init__(self):
        super().__init__()
        self.options_layout = QFormLayout()
        self.option_widgets = {}
    
    def update_options(self, provider_name, model_name):
        """Update options based on provider/model"""
        # Clear existing widgets
        self.clear_options()
        
        # Add generic options
        for opt_name, opt_config in GENERIC_OPTIONS.items():
            widget = self.create_option_widget(opt_name, opt_config)
            self.option_widgets[opt_name] = widget
            self.options_layout.addRow(opt_config['description'], widget)
        
        # Add provider-specific options
        if provider_name in PROVIDER_SPECIFIC_OPTIONS:
            for opt_name, opt_config in PROVIDER_SPECIFIC_OPTIONS[provider_name].items():
                widget = self.create_option_widget(opt_name, opt_config)
                self.option_widgets[opt_name] = widget
                self.options_layout.addRow(opt_config['description'], widget)
```

---

## File Changes Summary

### Files to Create:
1. `models/__init__.py`
2. `models/check_models.py` (moved)
3. `models/manage_models.py` (moved)
4. `models/model_registry.py` (new)
5. `models/provider_configs.py` (new)
6. `models/model_options.py` (new)
7. `models/copilot_npu.py` (new)
8. `models/download_florence2.py` (new)
9. `models/downloads/` (directory)

### Files to Modify:
1. `imagedescriber/imagedescriber.py` - Remove ModelManager, add options panel, prompt visibility
2. `imagedescriber/ai_providers.py` - Add Copilot+ real implementation
3. `scripts/image_describer.py` - Add provider selection support
4. `scripts/workflow.py` - Add provider support
5. `README.md` - Update paths
6. `QUICK_START.md` - Update paths
7. All batch files - Update paths

### Files to Move:
1. `check_models.py` → `models/check_models.py`
2. `manage_models.py` → `models/manage_models.py`
3. `yolov8x.pt` → `models/downloads/yolov8x.pt`

---

## Testing Requirements

### Test 1: Model Organization
```bash
# All model commands should work from new location
python models/check_models.py
python models/manage_models.py list
```

### Test 2: Provider Integration
```bash
# OpenAI should work in scripts
python scripts/image_describer.py test.jpg --provider openai --model gpt-4o-mini

# All providers in GUI
python imagedescriber/imagedescriber.py
# Select each provider, verify it works
```

### Test 3: Prompt Visibility
```bash
python imagedescriber/imagedescriber.py
# Select ONNX → prompt UI hidden
# Select Ollama → prompt UI visible
# Select ObjectDetection → prompt UI hidden
```

### Test 4: Copilot+ PC
```bash
# On Copilot+ PC hardware
python models/check_models.py --provider copilot
# Should show: [OK] Status: NPU available

python imagedescriber/imagedescriber.py
# Select Copilot+ PC provider
# Process image → should use real Florence-2 NPU inference
```

### Test 5: Model Options
```bash
python imagedescriber/imagedescriber.py
# Select Ollama → see temperature, max_tokens, num_ctx
# Select ONNX → see use_gpu, yolo_confidence
# Change options → verify they're passed to provider
```

---

## Migration Guide for Users

### Before:
```bash
python check_models.py
python manage_models.py list
```

### After:
```bash
python models/check_models.py
python models/manage_models.py list

# Or use convenience scripts in root:
python check_models.py  # symlink to models/check_models.py
python manage_models.py  # symlink to models/manage_models.py
```

---

## Timeline

1. **Phase 1 (File Organization):** 2 hours
2. **Phase 2 (Copilot+ PC):** 4 hours
3. **Phase 3 (Provider Integration):** 3 hours
4. **Phase 4 (Remove GUI Manager):** 1 hour
5. **Phase 5 (Prompt Consistency):** 2 hours
6. **Phase 6 (Options Framework):** 3 hours

**Total:** ~15 hours of development + testing

---

## Risk Assessment

### Low Risk:
- File organization (can be reversed easily)
- Removing GUI model manager (code is still in git history)

### Medium Risk:
- Prompt visibility changes (existing users might be confused)
- Provider integration (might break existing workflows)

### High Risk:
- Copilot+ PC implementation (no hardware to test thoroughly)

### Mitigation:
- Keep comprehensive git history
- Document all changes in CHANGELOG.md
- Provide migration guide
- Test thoroughly before release

---

## Next Steps

1. **Get User Approval** on this plan
2. **Phase 1:** Start with file organization (safest)
3. **Phase 4:** Remove GUI model manager (quick win)
4. **Phase 5:** Prompt visibility (improves UX)
5. **Phase 3:** Provider integration (adds functionality)
6. **Phase 6:** Options framework (enhances flexibility)
7. **Phase 2:** Copilot+ PC (requires hardware testing)

