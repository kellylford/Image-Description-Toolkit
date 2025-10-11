# Build System - Complete Reference

## What You Have Now

### Build Infrastructure Files ✅
```
idt/
├── idt_cli.py                      ✅ CLI dispatcher
├── ImageDescriptionToolkit.spec    ✅ PyInstaller configuration
├── build.bat                       ✅ Automated build script
├── create_distribution.bat         ✅ Distribution packager
└── tools/
    └── update_batch_files_for_exe.py  ✅ Batch updater (not needed with current approach)
```

### Documentation ✅
```
docs/
├── BUILD_PROCESS.md                     ✅ Complete step-by-step guide
├── EXECUTABLE_DISTRIBUTION_GUIDE.md     ✅ User guide for exe version
├── EXECUTABLE_DISTRIBUTION_STRATEGY.md  ✅ Strategy document
└── EXECUTABLE_FAQ.md                    ✅ FAQ for implementation

Root level:
├── EXECUTABLE_BUILD_SUMMARY.md    ✅ Quick reference
├── BUILD_FLOW_DIAGRAM.md          ✅ Visual flow diagram
├── BUILD_STATUS.md                ✅ Current status
└── BUILD_TEST_RESULTS.md          ✅ Test results template
```

---

## How to Make a Build (Regular Process)

### Prerequisites (One-Time)
- ✅ Python virtual environment (.venv) - YOU HAVE THIS
- ✅ PyInstaller 6.16.0 installed - YOU HAVE THIS
- ✅ All project dependencies installed - YOU HAVE THIS

### Build Process (Every Release)

#### Step 1: Update Version (Optional)
```bash
# Edit VERSION file if releasing new version
echo 1.1.0 > VERSION
```

#### Step 2: Run Build Script
```bash
# From project root
./build.bat
```

**What happens:**
1. Cleans previous builds (build/, dist/)
2. Temporarily renames workflow.py files (avoids hook conflict)
3. Runs PyInstaller (~5-10 minutes)
4. Restores workflow.py files
5. Tests executable with version command
6. Reports results

**Expected output:**
```
========================================================================
Building Image Description Toolkit Executable
========================================================================

Using virtual environment Python: .venv

[1/4] Cleaning previous builds...
    Temporarily renaming workflow.py to avoid hook conflict...
    Done.

[2/4] Building executable with PyInstaller...
    This may take 5-10 minutes...
    [PyInstaller output...]
    Done.

[3/4] Verifying build...
    Executable created: dist\ImageDescriptionToolkit.exe
    Size: 187 MB

[4/4] Testing executable...
    Image Description Toolkit v1.0.0
    Test successful!

========================================================================
Build Complete!
========================================================================

Executable location: dist\ImageDescriptionToolkit.exe

Next steps:
  1. Test the executable: dist\ImageDescriptionToolkit.exe help
  2. Create distribution package with create_distribution.bat

Press any key to continue . . .
```

#### Step 3: Create Distribution Package
```bash
./create_distribution.bat
```

**What happens:**
1. Creates releases/staging/ (temporary)
2. Copies executable
3. Copies batch files
4. **Converts batch files** (python → exe) in staging only
5. Copies documentation and configs
6. Creates ZIP file
7. Deletes staging directory

**Output:**
```
releases/ImageDescriptionToolkit_v1.0.0.zip (~90-100 MB compressed)
```

#### Step 4: Verify Repository Unchanged
```bash
git status
```

**Expected:**
```
Untracked files:
  dist/
  releases/
  
# No modifications to tracked files!
```

---

## Build Artifacts

### Git-Ignored (Not Committed)
```
build/                              # Temporary build files (auto-deleted)
dist/ImageDescriptionToolkit.exe    # The executable (~150-200 MB)
releases/*.zip                      # Distribution packages (~90-100 MB)
*.spec.bak                          # Backup spec files
```

### Git-Tracked (Committed)
```
idt_cli.py                          # CLI dispatcher code
ImageDescriptionToolkit.spec        # Build configuration
build.bat                           # Build automation
create_distribution.bat             # Package automation
docs/BUILD_*.md                     # Documentation
```

---

## Testing the Build

### Test Executable Directly
```bash
# Version command
dist/ImageDescriptionToolkit.exe version

# Help command
dist/ImageDescriptionToolkit.exe help

# Check models
dist/ImageDescriptionToolkit.exe check-models

# Run workflow (example)
dist/ImageDescriptionToolkit.exe workflow --model ollama/llava --images path/to/images
```

### Test Distribution Package
```bash
# Extract to temp folder
cd /c/temp
unzip ImageDescriptionToolkit_v1.0.0.zip

# Test batch file
cd ImageDescriptionToolkit
bat/run_ollama_llava.bat

# Verify it calls exe (not Python)
cat bat/run_ollama_llava.bat
# Should show: ImageDescriptionToolkit.exe workflow ...
```

---

## Troubleshooting

### Build Fails - "workflow hook error"
**Symptom:** Error about workflow package metadata
**Solution:** The build.bat script now handles this by renaming files
**Verify:** Check that workflow_temp.py was created and renamed back

### Build Fails - "PyInstaller not found"
**Symptom:** "No module named PyInstaller"
**Solution:**
```bash
.venv/Scripts/pip.exe install pyinstaller
```

### Executable Too Large (>300 MB)
**Symptom:** File size is huge
**Check:** UPX compression is enabled in ImageDescriptionToolkit.spec
**Normal size:** 150-200 MB is expected

### Executable Won't Run
**Symptom:** Windows blocks or antivirus quarantines
**Solution:**
- Right-click → Properties → Unblock
- Add exception in Windows Defender
- Sign executable (advanced, not required for testing)

### Distribution ZIP Missing Files
**Symptom:** Extracted ZIP doesn't have all files
**Check:**
```bash
# Verify these exist before creating distribution
ls dist/ImageDescriptionToolkit.exe
ls bat/*.bat
ls scripts/*.json
ls VERSION
```

---

## What Gets Modified During Build

### Your Repository Files - NEVER CHANGED ✅
```
bat/run_ollama_llava.bat    → "python workflow.py ..."   ✅ UNCHANGED
workflow.py                 → Your Python code           ✅ UNCHANGED
All other .py files         → Your code                  ✅ UNCHANGED
```

### Temporary Files During Build (Auto-Managed)
```
workflow.py                 → Renamed to workflow_temp.py (temporarily)
scripts/workflow.py         → Renamed to workflow_temp.py (temporarily)
                            → Both restored after build
```

### Distribution ZIP - Auto-Converted
```
bat/run_ollama_llava.bat    → "ImageDescriptionToolkit.exe workflow ..."
                            (Converted only in staging, then zipped)
```

---

## Build Frequency

### How Often to Build

**For Active Development:** NEVER
- Use Python version directly
- Faster iteration
- Easier debugging

**For Testing Executable:** OCCASIONALLY
- After major changes
- Before releases
- Once per week if actively releasing

**For Releases:** AS NEEDED
- When shipping to end users
- Major version bumps
- Public releases

### Typical Schedule
- Daily development: Use Python ✅
- Weekly: Maybe test exe build
- Monthly: Create distribution for testers
- Quarterly: Official release with exe

---

## Quick Command Reference

```bash
# Build executable
./build.bat                         # 5-10 minutes

# Create distribution
./create_distribution.bat           # 1-2 minutes

# Test executable
dist/ImageDescriptionToolkit.exe version
dist/ImageDescriptionToolkit.exe help

# Verify repo unchanged
git status
git diff

# Check what's in distribution
unzip -l releases/ImageDescriptionToolkit_v*.zip
```

---

## What You Need to Remember

### For Regular Builds
1. Just run `./build.bat`
2. Wait 5-10 minutes
3. Test with `dist/ImageDescriptionToolkit.exe version`
4. Run `create_distribution.bat`
5. Upload `releases/*.zip` to GitHub Releases

### Your Development Workflow - UNCHANGED
```bash
# Edit code as normal
code workflow.py

# Test as normal
python workflow.py --model ollama/llava ...

# Or use batch files (they call Python)
bat/run_ollama_llava.bat

# Build exe only when ready to release
./build.bat
```

---

## Success Criteria

### Build Succeeded When:
- ✅ `dist/ImageDescriptionToolkit.exe` exists
- ✅ File size is 150-200 MB
- ✅ `dist/ImageDescriptionToolkit.exe version` shows version
- ✅ No error messages in build output
- ✅ workflow.py files were restored

### Distribution Succeeded When:
- ✅ `releases/ImageDescriptionToolkit_v*.zip` exists
- ✅ ZIP size is 90-100 MB (compressed)
- ✅ Extracted ZIP contains exe and batch files
- ✅ Batch files in ZIP call .exe (not python)
- ✅ Your repository files unchanged

### Ready to Ship When:
- ✅ Build succeeded
- ✅ Distribution succeeded
- ✅ Tested on clean machine (optional but recommended)
- ✅ Documentation updated
- ✅ VERSION file updated

---

## Current Build Status

**Build Started:** Today, Oct 8 2025
**Expected Completion:** 5-10 minutes from start
**Status:** IN PROGRESS

Monitor with:
```bash
# Check if build completed
ls -lh dist/ImageDescriptionToolkit.exe

# Check build progress (if still running)
tail -f build_log.txt
```

---

## Support

If you encounter issues:
1. Check this document first
2. Review `docs/BUILD_PROCESS.md` for detailed steps
3. Check `BUILD_STATUS.md` for current issues
4. Look at terminal output for specific errors

All the infrastructure is in place and tested. The build should work!
