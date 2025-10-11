# IDT Executable-First Development Guide

## 🎯 CORE PRINCIPLE: Executable First

The primary use case for IDT is the `idt.exe` executable. All development should prioritize this interface.

## 🔄 DEVELOPMENT WORKFLOW

### 1. **Make Changes**
- Edit source code in `scripts/`, `models/`, etc.
- Update `final_working.spec` if adding new modules

### 2. **Test as Executable**
```bash
# Build executable
./build_executable.sh

# Test executable functionality  
python test_executable.py

# Test specific features
dist/idt.exe workflow --help
dist/idt.exe --version
```

### 3. **Validate Batch Files**
```bash
# Test Windows batch files (if on Windows)
bat_exe\run_ollama_moondream.bat --help
bat_exe\run_claude_haiku3.bat --prompt-style colorful --help
```

### 4. **Commit & Deploy**
```bash
git add .
git commit -m "Feature: description"
git push
```

## 📋 CHECKLIST FOR NEW FEATURES

- [ ] Feature works in executable context
- [ ] Updated `final_working.spec` if needed
- [ ] Ran `test_executable.py` successfully
- [ ] Tested relevant batch files
- [ ] Updated documentation
- [ ] Committed changes

## 🚫 AVOID THESE PATTERNS

### ❌ Don't develop against direct scripts
```python
# Don't do this
python scripts/workflow.py --help
```

### ✅ Do develop against executable
```python
# Do this instead  
dist/idt.exe workflow --help
```

### ❌ Don't use relative paths
```python
# Don't do this
config_path = "scripts/config.json"
```

### ✅ Do use resource manager
```python
# Do this instead
from scripts.resource_manager import load_config
config_path = load_config("config.json")
```

## 🔧 TROUBLESHOOTING

### Import Errors in Executable
1. Check `final_working.spec` hiddenimports
2. Add missing module to hiddenimports list
3. Rebuild with `./build_executable.sh`

### Config File Not Found
1. Check `scripts/resource_manager.py`
2. Ensure config is in datas section of spec
3. Use `get_resource_path()` for file access

### Batch File Issues
1. Verify working directory change: `cd /d "%~dp0\.."`
2. Test with: `idt.exe` not `python script.py`
3. Check argument passing with `%*`

## 📊 TESTING STRATEGY

### Primary Testing: Executable
- Main testing should be against `dist/idt.exe`
- Use `test_executable.py` for automated testing
- Test batch files on Windows systems

### Secondary Testing: Source Code
- Unit tests can run against source code
- Integration tests should use executable
- Performance testing should use executable

## 🎉 SUCCESS METRICS

A successful change means:
- ✅ `dist/idt.exe workflow --help` works
- ✅ `test_executable.py` passes
- ✅ Batch files support all arguments
- ✅ No regression in existing functionality
- ✅ Resource loading works in packaged context