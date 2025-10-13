# GUI Apps Virtual Environment Setup Guide

**Date:** October 12, 2025  
**Strategy:** Separate virtual environment per app for clean isolation

---

## Setup Instructions

### 1. Viewer Virtual Environment

```bash
cd c:/Users/kelly/GitHub/idt/viewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Installs:**
- PyQt6 (GUI framework)
- Pillow (image processing)
- requests (HTTP)
- ollama (redescribe feature)
- pyinstaller (build tool)

**Build:**
```bash
# Make sure venv is activated
.venv\Scripts\activate
build_viewer.bat
```

---

### 2. Prompt Editor Virtual Environment

```bash
cd c:/Users/kelly/GitHub/idt/prompt_editor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Installs:**
- PyQt6 (GUI framework)
- ollama, openai, anthropic (AI provider support)
- requests (HTTP)
- pyinstaller (build tool)

**Build:**
```bash
# Make sure venv is activated
.venv\Scripts\activate
build_prompt_editor.bat
```

---

### 3. ImageDescriber Virtual Environment

```bash
cd c:/Users/kelly/GitHub/idt/imagedescriber
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Installs:**
- PyQt6 (GUI framework)
- Pillow, pillow-heif, opencv-python, numpy (image/video processing)
- ollama, openai, anthropic (AI providers)
- requests, tqdm (utilities)
- pyinstaller (build tool)

**Build:**
```bash
# Make sure venv is activated
.venv\Scripts\activate
build_imagedescriber.bat
```

---

## Quick Build All Three

Once virtual environments are set up:

```bash
# Viewer
cd c:/Users/kelly/GitHub/idt/viewer
.venv\Scripts\activate
build_viewer.bat
deactivate

# Prompt Editor
cd ../prompt_editor
.venv\Scripts\activate
build_prompt_editor.bat
deactivate

# ImageDescriber
cd ../imagedescriber
.venv\Scripts\activate
build_imagedescriber.bat
deactivate
```

---

## .gitignore

Make sure each app's `.venv` is ignored. Add to your `.gitignore`:

```
# Virtual environments
.venv/
*/.venv/
viewer/.venv/
prompt_editor/.venv/
imagedescriber/.venv/
```

---

## Benefits of This Approach

✅ **Clean isolation** - Each app has exactly what it needs  
✅ **No pollution** - Main Python environment stays clean  
✅ **Easy troubleshooting** - Dependency conflicts isolated per app  
✅ **Independent updates** - Update one app's deps without affecting others  
✅ **Matches distribution** - Each app is truly standalone  

---

## Disk Space Usage (Approximate)

- **viewer/.venv**: ~150MB (PyQt6 + minimal deps)
- **prompt_editor/.venv**: ~200MB (PyQt6 + AI providers)
- **imagedescriber/.venv**: ~400MB (PyQt6 + image processing + AI providers)
- **Total**: ~750MB (vs ~150MB for shared venv)

**Trade-off:** More disk space, but cleaner development environment. ✅

---

## Build Script Compatibility

The build scripts automatically use whichever Python is active:

```batch
# Uses active venv's Python
python -c "import platform; ..."
pip install ...
pyinstaller ...
```

So as long as you activate the app's venv before running `build_*.bat`, everything works perfectly!

---

## Quick Reference

### Setup All Three:
```bash
# Viewer
cd viewer && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && deactivate

# Prompt Editor
cd ../prompt_editor && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && deactivate

# ImageDescriber
cd ../imagedescriber && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && deactivate
```

### Build All Three:
```bash
cd viewer && .venv\Scripts\activate && build_viewer.bat && deactivate
cd ../prompt_editor && .venv\Scripts\activate && build_prompt_editor.bat && deactivate
cd ../imagedescriber && .venv\Scripts\activate && build_imagedescriber.bat && deactivate
```

---

**Status:** Ready to create virtual environments and build! 🚀
