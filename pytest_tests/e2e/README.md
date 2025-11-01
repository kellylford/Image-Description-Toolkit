# End-to-End (E2E) Tests

This directory contains end-to-end tests that verify the **frozen executable** (`idt.exe`) works correctly.

## What E2E Tests Do

Unlike unit or integration tests that run in the Python development environment, E2E tests:

1. ✅ Test the **built executable** (PyInstaller frozen application)
2. ✅ Run complete workflows from command-line
3. ✅ Verify outputs are generated correctly
4. ✅ Test all CLI commands work

## When to Run E2E Tests

**Before running E2E tests**, you must build the executable:
```bash
BuildAndRelease\build_idt.bat
```

Or use the automated test-build script:
```bash
test_and_build.bat
```

## Running E2E Tests

```bash
# Run all E2E tests (requires built executable)
pytest pytest_tests/e2e/ -v

# Run just the critical workflow test
pytest pytest_tests/e2e/test_build_and_workflow.py::test_frozen_exe_runs_complete_workflow -v

# Skip E2E tests (for fast development cycle)
pytest pytest_tests/ -m "not e2e" -v
```

## Test Files

- **test_build_and_workflow.py** - Critical test that runs complete workflow with frozen exe
- **test_cli_commands.py** - Tests all CLI commands work correctly
- **test_frozen_executable.py** - Tests versioning and basic functionality

## Important Notes

- E2E tests are marked with `@pytest.mark.e2e` and `@pytest.mark.slow`
- Tests will **skip** if `dist/idt.exe` doesn't exist
- Tests use `test_data/` for sample images
- Tests create temporary output directories (automatically cleaned up)

## Debugging Failed E2E Tests

If E2E tests fail:

1. **Check build succeeded**: Verify `dist/idt.exe` exists and is recent
2. **Run manually**: Try the same command the test runs to see actual error
3. **Check test output**: Tests print workflow output for debugging
4. **Verify test data**: Ensure `test_data/` has sample images

Example manual test:
```bash
dist\idt.exe workflow test_data --output test_output --model moondream --steps describe,html --no-view
```

## Why E2E Tests Are Critical

E2E tests catch issues that unit/integration tests miss:
- ❌ Missing modules in PyInstaller spec
- ❌ Import errors in frozen executable  
- ❌ Path resolution differences between dev and frozen
- ❌ Resource file access issues

**These are the tests that verify your build actually works for users.**
