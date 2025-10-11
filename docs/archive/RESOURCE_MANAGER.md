# Resource Manager Documentation

## Overview

The `scripts/resource_manager.py` module is the **core solution** that enables the Image Description Toolkit to work seamlessly in both development (Python scripts) and production (PyInstaller executable) environments.

## 🎯 Purpose

**Problem Solved**: PyInstaller executables have a completely different file system structure than development environments. Files are bundled into a temporary directory (`sys._MEIPASS`) during execution, making traditional relative path approaches fail.

**Solution**: The resource manager provides a unified API that automatically detects the execution context and resolves paths correctly for:
- ✅ Configuration files (input)
- ✅ Templates and resources (input)  
- ✅ Output files and directories (output)
- ✅ Data files and logs (input/output)

## 🏗️ Architecture

### Context Detection
```python
if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable
    # Use executable-specific path resolution
else:
    # Running as Python script (development)
    # Use standard project structure
```

### Path Resolution Strategy

#### For Development Mode (`python script.py`):
```
project_root/
├── scripts/
│   ├── resource_manager.py
│   └── image_describer_config.json  
├── analysis/
│   └── results/              # ← Output goes here
└── dist/
```

#### For Executable Mode (`idt.exe`):
```
dist/
├── idt.exe                   # ← Execution location
├── analysis/
│   └── results/              # ← Output goes here  
└── _internal/                # ← PyInstaller bundle (temporary)
    ├── scripts/
    │   └── image_describer_config.json
    └── ...
```

## 📚 API Reference

### `get_resource_path(relative_path: str) -> Path`

**Primary function for all path resolution.**

```python
from scripts.resource_manager import get_resource_path

# Input files (configs, templates)
config_path = get_resource_path("scripts/image_describer_config.json")

# Output directories  
results_dir = get_resource_path("analysis/results")
```

**Logic**:
- **Executable mode**: 
  - Output paths: Relative to executable directory (`dist/analysis/results/`)
  - Input paths: Try PyInstaller bundle first, fallback to executable directory
- **Development mode**: 
  - All paths: Relative to project root

### `load_config(config_name: str = "image_describer_config.json") -> Path`

**Specialized function for configuration files.**

```python
from scripts.resource_manager import load_config

# Automatically searches multiple locations:
# 1. scripts/image_describer_config.json
# 2. image_describer_config.json  
# 3. config/image_describer_config.json
config_path = load_config()
```

**Benefits**:
- ✅ Automatic search in common locations
- ✅ Helpful error messages with search paths
- ✅ Context-aware (executable vs development)

### `get_executable_info() -> dict`

**Diagnostic function for debugging.**

```python
from scripts.resource_manager import get_executable_info

info = get_executable_info()
print(f"Running as executable: {info['is_executable']}")
print(f"Base path: {info['base_path']}")
```

## 🔧 Usage Patterns

### Reading Configuration Files
```python
# ❌ Old way (breaks in executable)
config_path = Path(__file__).parent / "config.json"

# ✅ New way (works everywhere)
from scripts.resource_manager import load_config
config_path = load_config("config.json")
```

### Creating Output Files
```python
# ❌ Old way (breaks in executable)
output_dir = Path(__file__).parent / "results"

# ✅ New way (works everywhere)
from scripts.resource_manager import get_resource_path
output_dir = get_resource_path("analysis/results")
output_dir.mkdir(parents=True, exist_ok=True)
```

### Reading Data Files
```python
# ❌ Old way (breaks in executable)
data_file = Path(__file__).parent / "data" / "templates.json"

# ✅ New way (works everywhere)
from scripts.resource_manager import get_resource_path
data_file = get_resource_path("data/templates.json")
```

## 🎯 Integration Examples

### Analysis Scripts Integration
**Before** (broken in executable):
```python
# analysis/stats_analysis.py
output_dir = Path(__file__).parent / "results"  # ❌ Fails in executable
```

**After** (works everywhere):
```python
# analysis/stats_analysis.py
from scripts.resource_manager import get_resource_path
output_dir = get_resource_path("analysis/results")  # ✅ Works everywhere
```

### Workflow Scripts Integration
**Before** (broken in executable):
```python
# scripts/workflow.py
config_file = "scripts/image_describer_config.json"  # ❌ Relative path fails
```

**After** (works everywhere):
```python
# scripts/workflow.py  
from scripts.resource_manager import load_config
config_path = load_config("image_describer_config.json")  # ✅ Automatic resolution
```

## 🔍 How Output Paths Work

### Development Mode
```bash
# When running: python scripts/workflow.py
# Output created at: analysis/results/
project_root/
├── analysis/
│   └── results/
│       ├── workflow_timing_stats.csv     # ← Stats output
│       ├── combineddescriptions.csv      # ← Combined descriptions  
│       └── content_analysis.csv          # ← Content analysis
```

### Executable Mode
```bash
# When running: dist/idt.exe stats
# Output created at: dist/analysis/results/  
dist/
├── idt.exe
├── analysis/
│   └── results/
│       ├── workflow_timing_stats.csv     # ← Stats output
│       ├── combineddescriptions.csv      # ← Combined descriptions
│       └── content_analysis.csv          # ← Content analysis
```

**Why this makes sense**:
- ✅ **Portable**: Entire `dist/` folder is self-contained
- ✅ **Organized**: Output files stay with the executable
- ✅ **Predictable**: Users know where to find results
- ✅ **Clean**: No files scattered in random locations

## 🛠️ Development Guidelines

### When Adding New Scripts
1. **Always use resource_manager** for file paths
2. **Never use `__file__`** for path resolution
3. **Test in both modes** (development and executable)

### Adding Resource Manager to New Scripts
```python
# Standard import pattern
import sys
from pathlib import Path

# Add parent directory to path for resource manager import
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from scripts.resource_manager import get_resource_path, load_config
except ImportError:
    # Fallback if resource manager not available
    def get_resource_path(relative_path):
        return Path(__file__).parent.parent / relative_path
```

### Error Handling
```python
try:
    config_path = load_config("my_config.json")
except FileNotFoundError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

## 🧪 Testing Resource Manager

### Test Script Example
```python
# test_resource_manager.py
from scripts.resource_manager import get_resource_path, get_executable_info

# Check execution context
info = get_executable_info()
print(f"Execution mode: {'executable' if info['is_executable'] else 'development'}")

# Test path resolution
results_path = get_resource_path("analysis/results")
print(f"Results directory: {results_path}")
print(f"Exists: {results_path.exists()}")

# Test file creation
test_file = results_path / "test.txt"
results_path.mkdir(parents=True, exist_ok=True)
test_file.write_text("Test successful!")
print(f"Created: {test_file}")
test_file.unlink()  # cleanup
```

## 🎉 Benefits Delivered

### For Developers
- ✅ **One API** for all file operations
- ✅ **No more path headaches** when packaging
- ✅ **Clear error messages** when files missing
- ✅ **Works in both contexts** automatically

### For Users  
- ✅ **Predictable output locations** 
- ✅ **Portable executable** with organized output
- ✅ **No scattered files** across the system
- ✅ **Self-contained distribution**

### For Maintenance
- ✅ **Centralized path logic** in one module
- ✅ **Easy to debug** path issues
- ✅ **Consistent behavior** across all scripts
- ✅ **Future-proof** for packaging changes

## 🚀 The Bottom Line

The resource manager is the **invisible foundation** that makes the entire IDT executable work seamlessly. It solved the fundamental PyInstaller path resolution problem that was breaking:

- ❌ Configuration loading
- ❌ Output file creation  
- ❌ Analysis command results
- ❌ Resource bundling

Now everything **just works** in both development and production! 🎯