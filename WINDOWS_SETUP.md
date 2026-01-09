# Windows Setup Instructions

## Quick Start

Run this **one time** on Windows to set up all GUI applications:

```batch
winsetup.bat
```

This creates `.winenv` virtual environments and installs all dependencies for:
- Viewer
- ImageDescriber  
- Prompt Editor
- IDTConfigure

## What It Does

1. Creates `.winenv` directory in each app folder
2. Installs wxPython and all dependencies from `requirements.txt`
3. Prepares apps for building on Windows

## Why .winenv instead of .venv?

Using `.winenv` for Windows allows you to:
- ✅ Use the same project directory on both macOS and Windows
- ✅ Run Windows in a VM on Mac without conflicts
- ✅ Keep macOS `.venv` and Windows `.winenv` separate

## After Setup

Once `winsetup.bat` completes successfully:

```batch
REM Build all applications
BuildAndRelease\builditall_wx.bat

REM Collect executables
BuildAndRelease\package_all_windows.bat

REM Create installer (requires Inno Setup)
BuildAndRelease\build_installer.bat
```

## Troubleshooting

**"Python not found"**
- Install Python 3.10+ from https://python.org
- Make sure Python is in PATH

**"pip install failed"**
- Try running as Administrator
- Check internet connection
- Try: `python -m pip install --upgrade pip`

**"Virtual environment creation failed"**
- Make sure you have write permissions
- Check available disk space

## Coexistence with macOS

Your project structure will look like:

```
viewer/
  .venv/          ← macOS virtual environment
  .winenv/        ← Windows virtual environment
  requirements.txt
  viewer_wx.py
  ...

imagedescriber/
  .venv/          ← macOS virtual environment
  .winenv/        ← Windows virtual environment
  requirements.txt
  imagedescriber_wx.py
  ...
```

Both `.venv` and `.winenv` are in `.gitignore` and won't be committed.

## Re-running Setup

If you need to refresh the Windows environments:

```batch
REM The script will automatically remove old .winenv directories
winsetup.bat
```

## Manual Setup (if needed)

If you prefer to set up apps individually:

```batch
cd viewer
python -m venv .winenv
.winenv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..

REM Repeat for imagedescriber, prompt_editor, idtconfigure
```
