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
