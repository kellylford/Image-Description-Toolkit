# Models Directory Quick Reference

**Location:** `models/`

## Model Installation & Management Scripts

###  Status Checking

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_models.py` | Comprehensive model & provider status checker | `python -m models.check_models` |
| `checkmodels.bat` | Convenient wrapper for check_models.py | `models\checkmodels.bat` |
| `manage_models.py` | Model installation and management | `python -m models.manage_models` |

## Quick Commands

### Check All Providers
```bash
python -m models.check_models
# or
models\checkmodels.bat
```

### Check Specific Provider
```bash
python -m models.check_models --provider ollama
python -m models.check_models --provider ollama-cloud
python -m models.check_models --provider openai
python -m models.check_models --provider claude
```

### Detailed Information
```bash
python -m models.check_models --verbose
```

### JSON Output (for scripting)
```bash
python -m models.check_models --json
```

## Supported Providers

The check_models.py script now checks:

1. **Ollama** (Local Models) - Local AI models for image descriptions
2. **Ollama Cloud** - Cloud-based Ollama models
3. **OpenAI** - GPT-4o and other OpenAI models
4. **Claude** - Anthropic Claude models (claude-3.5-sonnet, etc.)

The manage_models.py script can install and manage:

1. **Ollama** - Pull/remove local vision models
2. **OpenAI** - Configure API keys (openai.txt)
3. **Claude** - Configure API keys (claude.txt)

## Install Providers

### Ollama (Local Models)
```bash
# Download Ollama from https://ollama.ai
# Then pull models:
ollama pull llava:7b
# or use manage_models
python -m models.manage_models install llava:7b
python -m models.manage_models install moondream
python -m models.manage_models install llama3.2-vision:11b
```

### OpenAI (Cloud)
```bash
# Create openai.txt in current directory with your API key
# or set OPENAI_API_KEY environment variable
# or pass --api-key-file <path> when running tools
```

### Claude (Cloud)
```bash
# Create claude.txt in current directory with your API key
# or set ANTHROPIC_API_KEY environment variable
# or pass --api-key-file <path> when running tools
```

## Python Module Structure

```
models/
├── __init__.py                  # Package initialization
├── check_models.py             # Status checker (all providers)
├── checkmodels.bat             # Wrapper script
├── manage_models.py           # Model management utilities
└── (legacy files removed)
```

## From Python Code

```python
# Check model availability
from models.check_models import check_ollama_status
status = check_ollama_status()
if status['status'] == 'OK':
    print(f"Ollama has {len(status['models'])} models installed")

# Run check_models programmatically
import subprocess
result = subprocess.run(
    ["python", "-m", "models.check_models", "--provider", "ollama", "--json"],
    capture_output=True, text=True
)
import json
status = json.loads(result.stdout)
```

## Output Example

```
=== Image Description Toolkit - Model Status ===

Ollama (Local Models)
  [OK] Status: OK
  Models: 8 available
    • llava:7b
    • moondream
    • llama3.2-vision:11b
    • llava:latest
    • llama3.2-vision:latest
    • llama3.1:latest
    • mistral-small3.1:latest
    • gemma3:latest

Ollama Cloud
  [--] Not signed in

OpenAI
  [--] API key not configured
  Setup: Create openai.txt or set OPENAI_API_KEY

Claude (Anthropic)
  [OK] API key configured
  Models: 7 available
    • claude-3.5-sonnet
    • claude-3-opus
    • claude-3-sonnet
    • claude-3-haiku
```

## See Also

- [MODEL_SELECTION_GUIDE.md](../docs/MODEL_SELECTION_GUIDE.md) - Choosing the right model
- [OPENAI_SETUP_GUIDE.md](../docs/OPENAI_SETUP_GUIDE.md) - OpenAI configuration
- [OLLAMA_GUIDE.md](../docs/OLLAMA_GUIDE.md) - Ollama usage guide

---

# Model Configuration System

## Overview

Starting with the WXMigration update (Feb 2026), **all AI model lists are centrally managed** in this `models/` directory. This ensures consistency across all toolkit components (IDT CLI, ImageDescriber GUI, chat features, etc.).

## Critical Rule: Single Source of Truth

**P0 REQUIREMENT:** Models MUST be the same throughout all user experiences.

### DO NOT:
- ❌ Hardcode model lists in individual components
- ❌ Define models separately in IDT vs ImageDescriber
- ❌ Copy/paste model lists between files

### DO:
- ✅ Import models from `models/<provider>_models.py`
- ✅ Update model lists in ONE place only
- ✅ Use the helper functions for display formatting

## Model Configuration Files

### Claude Models
**File:** `models/claude_models.py`

**Latest models (as of Feb 2026):**
- `claude-opus-4-6` - Most intelligent (NEW!)
- `claude-sonnet-4-5-20250929` - Best balance (recommended)
- `claude-haiku-4-5-20251001` - Fastest (NEW!)
- Plus legacy 4.x, 3.5, and 3.0 models (12 total)

**Usage:**
```python
from models.claude_models import CLAUDE_MODELS, get_claude_models, format_claude_model_for_display

# Get all models
models = get_claude_models()

# Format for display with descriptions
for model_id in models:
    display_text = format_claude_model_for_display(model_id, include_description=True)
    print(display_text)
```

### OpenAI Models
**File:** `models/openai_models.py`

**Latest models:**
- `o1`, `o1-mini`, `o1-preview` - Reasoning models
- `gpt-4o`, `gpt-4o-mini` - Latest GPT-4 Omni (recommended)
- Plus GPT-4 Turbo and legacy models (10 total)

**Usage:**
```python
from models.openai_models import OPENAI_MODELS, get_openai_models, format_openai_model_for_display

# Get all models
models = get_openai_models()

# Format for display
display_text = format_openai_model_for_display("gpt-4o")
```

## Current Usage

These model files are imported by:

### ImageDescriber GUI
- `imagedescriber/ai_providers.py` - Imports models from central config
- `imagedescriber/dialogs_wx.py` - Uses models from `ai_providers`
- `imagedescriber/chat_window_wx.py` - Uses models from `ai_providers`

### IDT CLI
- `scripts/guided_workflow.py` - Imports and formats for interactive CLI selection

## Updating Models

### When new models are released:

1. **Update the central config file:**
   - Edit `models/claude_models.py` or `models/openai_models.py`
   - Add new model IDs to the list
   - Update metadata (pricing, descriptions, etc.)

2. **Test in all components:**
   - Run `idt workflow` interactive mode
   - Open ImageDescriber GUI - check workflow config dialog
   - Test chat feature
   - Rebuild and test frozen executables

3. **See full testing checklist in comments at top of each model file**

## Provider API Querying

| Provider | API Available? | Strategy | Refresh Schedule |
|----------|---------------|----------|------------------|
| **Claude** | ❌ No | Manual curation | Quarterly - check docs |
| **OpenAI** | ✅ Yes | Manual curation | As needed - better UX |
| **Ollama** | ✅ Yes | Dynamic listing | Real-time from local install |

**Why manual for OpenAI?** API returns 100+ models including non-vision, fine-tuned, and deprecated models. Manual curation provides better UX with annotations and consistent ordering.

## Migration Notes

**Before (Inconsistent):**
- IDT had different Claude models than ImageDescriber
- Users saw different options in CLI vs GUI

**After (P0 Fixed - Feb 2026):**
- Both use `models/claude_models.py`
- Includes latest: `claude-opus-4-6`, `claude-haiku-4-5-20251001`
- Identical model lists everywhere

## Build System Integration

**CRITICAL:** Model config files must be included in PyInstaller builds.

Add to `.spec` files:
```python
hiddenimports=[
    'models.claude_models',
    'models.openai_models',
    # ... other imports
]
```
