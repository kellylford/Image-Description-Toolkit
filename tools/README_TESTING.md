# IDT Testing Tools

Quick reference for running tests locally before pushing to GitHub.

## Quick Start

**Run all tests (recommended):**
```bash
# Windows:
tools\run_all_tests.bat

# Cross-platform:
python tools/run_all_tests.py
```

**Run just unit tests:**
```bash
python run_unit_tests.py
```

**Build with tests:**
```bash
BuildAndRelease\recommended-build-test-deploy.bat
```

---

## Test Suite Overview

The comprehensive test runner (`run_all_tests.py` / `.bat`) runs:

### 1. Unit Tests (48 tests)
- **Unit tests** (`pytest_tests/unit/`) - Core functionality
  - Workflow name sanitization
  - Config file handling
  - Metadata extraction safety
  - Status log formatting
- **Smoke tests** (`pytest_tests/smoke/`) - Entry point validation
  - CLI commands (help, version, workflow, etc.)
  - GUI apps (viewer, imagedescriber, prompteditor)
  - *GUI tests auto-skip in CI environments*

### 2. Syntax & Import Check
- Compiles all main Python scripts
- Validates imports for core modules
- Catches syntax errors before CI

### 3. PyInstaller Build Test
- Attempts to build `idt.exe`
- Validates executable size (>5MB)
- *Skips if PyInstaller not installed*

### 4. Build Scripts Validation
- Checks existence of critical batch files:
  - `BuildAndRelease/builditall.bat`
  - `BuildAndRelease/packageitall.bat`
  - `BuildAndRelease/releaseitall.bat`
  - `BuildAndRelease/build_idt.bat`
  - `tools/environmentsetup.bat`

### 5. Git Status Check
- Warns if uncommitted changes exist
- Helps avoid "forgot to commit" issues

---

## Test Output

**Example successful run:**
```
================================================================================
   IMAGE DESCRIPTION TOOLKIT - LOCAL TEST SUITE
================================================================================
   
   Tests Passed:  5
   Tests Failed:  0
   Tests Skipped: 0
   Duration:      45.2 seconds
   
   [PASS] Unit Tests
   [PASS] Syntax & Import Check
   [PASS] PyInstaller Build
   [PASS] Build Scripts
   [PASS] Git Status
   
   [PASS] All tests passed!
================================================================================
```

---

## CI/CD Integration

These tests mirror what GitHub Actions runs in `.github/workflows/test.yml`:
- Same test files
- Same validation logic
- Same build process

**Difference:** GUI tests skip automatically in CI (no display available).

---

## Troubleshooting

**"Unit tests failed"**
- Run `python run_unit_tests.py --verbose` for details
- Check pytest_tests/unit/ and pytest_tests/smoke/

**"PyInstaller not installed"**
- Test will skip automatically
- Install: `pip install pyinstaller`

**"Build failed"**
- Check that all dependencies installed: `pip install -r requirements.txt`
- Try: `BuildAndRelease\build_idt.bat` for detailed errors

**GUI tests fail locally but not in CI**
- Expected! GUI tests run locally but skip in CI
- Set `GITHUB_ACTIONS=true` environment variable to simulate CI

---

## Files

| File | Purpose |
|------|---------|
| `tools/run_all_tests.py` | Comprehensive test suite (Python) |
| `tools/run_all_tests.bat` | Comprehensive test suite (Windows) |
| `run_unit_tests.py` | Just unit/smoke tests |
| `pytest_tests/` | All test files |
| `BuildAndRelease/recommended-build-test-deploy.bat` | Build with tests |

---

## Best Practices

1. **Run tests before committing:**
   ```bash
   python tools/run_all_tests.py
   ```

2. **Run tests before building:**
   ```bash
   BuildAndRelease\recommended-build-test-deploy.bat
   ```

3. **Add tests when fixing bugs:**
   - Add to `pytest_tests/unit/` for logic tests
   - Add to `pytest_tests/smoke/` for integration tests

4. **Keep tests fast:**
   - Unit tests should complete in seconds
   - Use timeouts for subprocess tests
   - Mock external dependencies when possible

---

## GitHub Actions Status

Check: https://github.com/kellylford/Image-Description-Toolkit/actions

All tests run automatically on push to `main` or `develop` branches.
