# macOS Setup Instructions

## Quick Start

Run this **one time** on macOS to set up all GUI applications:

**From Terminal:**
```bash
chmod +x macsetup.sh
./macsetup.sh
```

**From Finder:**
Double-click `macsetup.command`

This creates `.venv` virtual environments and installs all dependencies for:
- Root project (core dependencies for IDT CLI)
- ImageDescriber (batch processing GUI with integrated Viewer Mode, prompt editor, and configuration manager)

## What It Does

1. Creates `.venv` directory in the project root (for IDT CLI build)
2. Creates `.venv` directory in each GUI app folder
3. Installs wxPython and all dependencies from each `requirements.txt`
4. Prepares all apps for building on macOS

## Why .venv instead of .winenv?

Using `.venv` for macOS allows you to:
- ✅ Use the same project directory on both macOS and Windows
- ✅ Run Windows in a VM on Mac without conflicts
- ✅ Keep macOS `.venv` and Windows `.winenv` separate

## After Setup

Once the setup completes successfully:

```bash
# Build all applications
./BuildAndRelease/MacBuilds/builditall_macos.command

# Test the app (switch between Editor/Viewer modes with tabs)
open imagedescriber/dist/ImageDescriber.app
```

## Troubleshooting

**"python3: command not found"**
- Install Python 3.10+ from https://python.org
- Or use Homebrew: `brew install python@3.11`

**"pip install failed"**
- Check internet connection
- Try: `python3 -m pip install --upgrade pip`
- Check Xcode Command Line Tools: `xcode-select --install`

**"Permission denied" when running scripts**
- Make scripts executable: `chmod +x macsetup.sh`
- Or use the .command file which can be double-clicked in Finder

**wxPython installation fails**
- Make sure you have Xcode Command Line Tools installed
- Try installing wxPython separately first: `pip install wxPython`
- On Apple Silicon Macs, you may need to use Python 3.11+

## Coexistence with Windows

Your project structure will look like:

```
.venv/              ← macOS root virtual environment (for IDT CLI)
.winenv/            ← Windows root virtual environment (if using VM)

imagedescriber/
  .venv/          ← macOS virtual environment
  .winenv/        ← Windows virtual environment (if using VM)
  requirements.txt
  imagedescriber_wx.py
  ...
```

Both `.venv` and `.winenv` are in `.gitignore` and won't be committed.

## Re-running Setup

If you need to refresh the macOS environments:

```bash
# The script will automatically remove old .venv directories
./macsetup.sh
```

Or double-click `macsetup.command` in Finder.

## Manual Setup (if needed)

If you prefer to set up ImageDescriber manually:

```bash
cd imagedescriber
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

## Next Steps

After successful setup:

1. **Build executables**: Run `./BuildAndRelease/MacBuilds/builditall_macos.command`
2. **Test apps**: Open the `.app` bundles in `dist/` directories
3. **Read user guide**: See [docs/MACOS_USER_GUIDE.md](docs/MACOS_USER_GUIDE.md) for detailed usage

## System Requirements

- macOS 10.14 (Mojave) or later
- Python 3.10 or later (3.11+ recommended for Apple Silicon)
- Xcode Command Line Tools
- At least 2GB free disk space for all virtual environments
