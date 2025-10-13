# Tools Directory - Inventory and Documentation

**Purpose**: Automation scripts and utilities for development, building, and deployment.

**Last Updated**: October 12, 2025

---

## Active Development Tools

### `bootstrap.bat` ⭐ NEW
**Purpose**: Complete first-time setup on a new machine

**Use Case**: Run this on a brand new machine where you don't have the repository yet.

**What It Does**:
1. Checks prerequisites (Git, Python)
2. Clones the repository from GitHub
3. Automatically runs `environmentsetup.bat`
4. Sets up complete build environment

**Usage**:
```batch
# Download this file to a parent directory, then:
bootstrap.bat
```

**Prerequisites**:
- Git installed and in PATH
- Python 3.8+ installed and in PATH
- Internet connection

**Output**: 
- Cloned repository in `Image-Description-Toolkit/` subdirectory
- All virtual environments created and configured
- Ready to run `releaseitall.bat`

**Time**: ~5-15 minutes (depending on internet speed)

---

### `environmentsetup.bat` ⭐ NEW
**Purpose**: Create/refresh virtual environments for all applications

**Use Case**: 
- First-time setup when you already have the repository
- Refresh environments when dependencies change
- Fix broken virtual environments

**What It Does**:
1. Creates `.venv` for main IDT (root directory)
2. Creates `.venv` for viewer
3. Creates `.venv` for prompt_editor
4. Creates `.venv` for imagedescriber
5. Installs/updates all dependencies from requirements.txt files

**Usage**:
```batch
# From project root:
tools\environmentsetup.bat

# Or from tools directory:
cd tools
environmentsetup.bat
```

**Prerequisites**:
- Python 3.8+ installed and in PATH
- Internet connection (to download packages)

**Smart Features**:
- Detects existing venvs (won't overwrite, but will update packages)
- Error tracking (continues even if one app fails)
- Upgrades pip before installing packages
- Comprehensive error reporting

**Output**:
- `.venv/` in root directory (for IDT)
- `viewer/.venv/` (for Viewer)
- `prompt_editor/.venv/` (for Prompt Editor)
- `imagedescriber/.venv/` (for ImageDescriber)

**Time**: ~5-10 minutes

---

## Archived/Legacy Tools

These tools are kept for reference but are NOT part of the active build process.

### `build.bat` ⚠️ ARCHIVED
**Status**: Legacy version of main IDT build script

**Note**: The active build script is now `build_idt.bat` in the root directory. This version is kept for historical reference.

**Last Active**: Before October 12, 2025

---

### `create_distribution.bat` ⚠️ ARCHIVED
**Status**: Legacy version of main IDT packaging script

**Note**: The active packaging script is now `package_idt.bat` in the root directory. This version is kept for historical reference.

**Last Active**: Before October 12, 2025

---

## Complete Workflow Examples

### Scenario 1: Brand New AMD64 Machine
```batch
# Step 1: Download bootstrap.bat from GitHub
# https://raw.githubusercontent.com/kellylford/Image-Description-Toolkit/main/tools/bootstrap.bat

# Step 2: Run bootstrap
bootstrap.bat

# Step 3: Build everything
cd Image-Description-Toolkit
releaseitall.bat

# Result: All AMD64 executables in releases/
```

### Scenario 2: Already Have Repository
```batch
# Step 1: Set up environments
tools\environmentsetup.bat

# Step 2: Build everything
releaseitall.bat

# Result: All executables in releases/
```

### Scenario 3: Update Dependencies
```batch
# If requirements.txt files have changed:
tools\environmentsetup.bat

# This will update all packages in all virtual environments
```

### Scenario 4: Fix Broken Environment
```batch
# Delete broken venvs
rmdir /s /q .venv
rmdir /s /q viewer\.venv
rmdir /s /q prompt_editor\.venv
rmdir /s /q imagedescriber\.venv

# Recreate everything
tools\environmentsetup.bat
```

---

## Relationship to Master Build Scripts

The tools in this directory work **with** the master build scripts in the root directory:

### Build Pipeline:
```
1. Environment Setup (ONE TIME)
   ├── tools/bootstrap.bat (new machine)
   └── OR tools/environmentsetup.bat (existing repo)
   
2. Build & Package (EVERY RELEASE)
   ├── releaseitall.bat (complete automation)
   ├── OR builditall.bat (build only)
   ├── OR packageitall.bat (package only)
   └── OR individual scripts (build_idt.bat, etc.)
```

### File Locations:
```
idt/
├── tools/                          # This directory
│   ├── bootstrap.bat               # Clone + setup
│   ├── environmentsetup.bat        # Environment setup
│   ├── build.bat                   # ARCHIVED
│   └── create_distribution.bat     # ARCHIVED
│
├── build_idt.bat                   # Active: Build main IDT
├── package_idt.bat                 # Active: Package main IDT
├── builditall.bat                  # Active: Build all 4 apps
├── packageitall.bat                # Active: Package all 4 apps
└── releaseitall.bat                # Active: Build + package all
```

---

## Prerequisites Reference

### Required Software:
- **Python 3.8+** - https://www.python.org/downloads/
  - Must be in PATH
  - `python --version` should work from command line

- **Git** (for bootstrap.bat) - https://git-scm.com/download/win
  - Must be in PATH
  - `git --version` should work from command line

### Disk Space Requirements:
- Repository: ~100 MB
- Virtual environments (all 4): ~750 MB
- Build artifacts (all 4): ~800 MB
- Distribution packages: ~300 MB (compressed)
- **Total recommended**: 2-3 GB free space

### Network Requirements:
- Internet connection required for:
  - Cloning repository (bootstrap.bat)
  - Downloading Python packages (environmentsetup.bat)
  - First-time PyPI package downloads

---

## Troubleshooting

### "Python not found"
**Problem**: Python is not installed or not in PATH

**Solution**:
1. Install Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart terminal and try again

---

### "Git not found"
**Problem**: Git is not installed or not in PATH

**Solution**:
1. Install Git from https://git-scm.com/download/win
2. Use default installation settings
3. Restart terminal and try again

---

### "Failed to install dependencies"
**Problem**: Package installation failed

**Possible Causes**:
- No internet connection
- PyPI server issues
- Insufficient disk space
- Conflicting package versions

**Solution**:
1. Check internet connection
2. Try again (temporary PyPI issues)
3. Check disk space
4. Manually install problematic package: `pip install <package>`

---

### "Virtual environment already exists"
**Problem**: Warning message about existing .venv

**This is normal!** The script will update packages in the existing environment.

**To start fresh**:
```batch
rmdir /s /q .venv
tools\environmentsetup.bat
```

---

## Version History

**October 12, 2025**:
- ✅ Created `bootstrap.bat` - Complete first-time setup
- ✅ Created `environmentsetup.bat` - Virtual environment automation
- ⚠️ Archived `build.bat` and `create_distribution.bat` (moved to root with new names)

**Prior to October 12, 2025**:
- `build.bat` - Built main IDT executable
- `create_distribution.bat` - Packaged main IDT distribution

---

## For Developers

### Adding New Tools
When adding new automation tools to this directory:

1. **Create the script** with clear header documentation
2. **Update this inventory** with purpose, usage, and examples
3. **Test on fresh clone** to ensure it works standalone
4. **Update root README** if user-facing

### Naming Conventions
- Use lowercase with underscores: `environmentsetup.bat`
- Make names descriptive and specific
- Avoid generic names like `setup.bat` or `install.bat`

### Documentation Standards
Each script should have:
- Header block with purpose and usage
- Prerequisites clearly listed
- Error handling with helpful messages
- Success/failure summary at end
- No interactive prompts for automation (unless required for UX)

---

**End of Inventory**

For questions or issues, see main project documentation or GitHub issues.
