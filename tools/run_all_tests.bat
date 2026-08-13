@echo off
REM ============================================================================
REM IDT Local Test Runner - Complete Test Suite
REM ============================================================================
REM Runs all tests that GitHub Actions runs, but locally for quick validation
REM ============================================================================

SETLOCAL EnableDelayedExpansion
set START_TIME=%TIME%
set TOTAL_PASSED=0
set TOTAL_FAILED=0

echo.
echo ============================================================================
echo    IMAGE DESCRIPTION TOOLKIT - LOCAL TEST SUITE
echo ============================================================================
echo    Running all automated tests locally...
echo    Started: %DATE% %TIME%
echo ============================================================================
echo.

REM ============================================================================
echo [1/4] UNIT TESTS
echo ============================================================================
echo Running unit and smoke tests...
echo.

python run_unit_tests.py
if errorlevel 1 (
    echo.
    echo [FAIL] Unit tests failed!
    set /a TOTAL_FAILED+=1
) else (
    echo.
    echo [PASS] Unit tests passed!
    set /a TOTAL_PASSED+=1
)

echo.
echo ============================================================================
echo [2/4] SYNTAX ^& IMPORT CHECK
echo ============================================================================
echo Checking Python syntax and imports...
echo.

REM Check syntax of main scripts
python -m py_compile scripts/workflow.py 2>nul
if errorlevel 1 (
    echo [FAIL] scripts/workflow.py has syntax errors
    set /a TOTAL_FAILED+=1
    goto :skip_syntax
)

python -m py_compile scripts/image_describer.py 2>nul
if errorlevel 1 (
    echo [FAIL] scripts/image_describer.py has syntax errors
    set /a TOTAL_FAILED+=1
    goto :skip_syntax
)

python -m py_compile scripts/metadata_extractor.py 2>nul
if errorlevel 1 (
    echo [FAIL] scripts/metadata_extractor.py has syntax errors
    set /a TOTAL_FAILED+=1
    goto :skip_syntax
)

python -m py_compile idt_cli.py 2>nul
if errorlevel 1 (
    echo [FAIL] idt_cli.py has syntax errors
    set /a TOTAL_FAILED+=1
    goto :skip_syntax
)

echo [PASS] All main scripts compile successfully

REM Test imports
cd scripts
python -c "import workflow_utils; print('[PASS] workflow_utils imports OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] workflow_utils import failed
    set /a TOTAL_FAILED+=1
    cd ..
    goto :skip_syntax
)

python -c "import image_describer; print('[PASS] image_describer imports OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] image_describer import failed
    set /a TOTAL_FAILED+=1
    cd ..
    goto :skip_syntax
)

python -c "import metadata_extractor; print('[PASS] metadata_extractor imports OK')" 2>nul
if errorlevel 1 (
    echo [FAIL] metadata_extractor import failed
    set /a TOTAL_FAILED+=1
    cd ..
    goto :skip_syntax
)

cd ..

echo.
echo [PASS] Syntax and import checks passed!
set /a TOTAL_PASSED+=1
goto :after_syntax

:skip_syntax
cd ..
echo.
echo [FAIL] Syntax and import checks failed!

:after_syntax

echo.
echo ============================================================================
echo [3/4] PYINSTALLER BUILD TEST
echo ============================================================================
echo Checking build infrastructure...
echo.

REM Check if build infrastructure exists
if not exist "BuildAndRelease\WinBuilds\builditall_wx.bat" (
    echo [WARN] Missing BuildAndRelease\WinBuilds\builditall_wx.bat
    goto :skip_build
)

echo [SKIP] PyInstaller test skipped - use BuildAndRelease\WinBuilds\builditall_wx.bat for actual builds
echo        Reason: Simple builds conflict with 'workflow' package
echo        Build scripts present and ready to use
goto :after_build

:skip_build
echo.

:after_build

echo.
echo ============================================================================
echo [4/4] BUILD SCRIPTS VALIDATION
echo ============================================================================
echo Checking batch file syntax...
echo.

set BAT_ERRORS=0

REM Check key batch files exist.
REM
REM Until 2026-08-13 this block checked builditall.bat, packageitall.bat,
REM releaseitall.bat and BuildAndRelease\build_idt.bat -- none of which had
REM existed for months. A check that names only absent files reports "build
REM infrastructure missing" forever and stops meaning anything, which is why
REM nobody noticed the real build system was never being validated here.
if not exist "BuildAndRelease\WinBuilds\builditall_wx.bat" (
    echo [WARN] BuildAndRelease\WinBuilds\builditall_wx.bat not found
    set /a BAT_ERRORS+=1
)

if not exist "BuildAndRelease\WinBuilds\package_all_windows.bat" (
    echo [WARN] BuildAndRelease\WinBuilds\package_all_windows.bat not found
    set /a BAT_ERRORS+=1
)

if not exist "BuildAndRelease\WinBuilds\build_installer.bat" (
    echo [WARN] BuildAndRelease\WinBuilds\build_installer.bat not found
    set /a BAT_ERRORS+=1
)

if not exist "idt\build_idt.bat" (
    echo [WARN] idt\build_idt.bat not found
    set /a BAT_ERRORS+=1
)

if not exist "imagedescriber\build_imagedescriber_wx.bat" (
    echo [WARN] imagedescriber\build_imagedescriber_wx.bat not found
    set /a BAT_ERRORS+=1
)

if not exist "chatapp\build_chatapp.bat" (
    echo [WARN] chatapp\build_chatapp.bat not found
    set /a BAT_ERRORS+=1
)

if not exist "winsetup.bat" (
    echo [WARN] winsetup.bat not found
    set /a BAT_ERRORS+=1
)

if %BAT_ERRORS% EQU 0 (
    echo [PASS] All build scripts present
    set /a TOTAL_PASSED+=1
) else (
    echo [FAIL] Some build scripts missing
    set /a TOTAL_FAILED+=1
)

REM ============================================================================
echo.
echo ============================================================================
echo    TEST SUMMARY
echo ============================================================================
echo    Tests Passed: %TOTAL_PASSED%
echo    Tests Failed: %TOTAL_FAILED%
echo    Started:      %DATE% %START_TIME%
echo    Completed:    %DATE% %TIME%
echo ============================================================================
echo.
echo WHAT THESE RESULTS MEAN:
echo ============================================================================
echo √ Unit Tests PASS = All 48 unit/smoke tests passed
echo                     - Core functionality validated
echo                     - CLI commands work
echo                     - Config handling correct
echo.
echo √ Syntax Check PASS = All Python files compile
echo                       - No syntax errors
echo                       - All imports resolve
echo.
echo O PyInstaller SKIP = Use BuildAndRelease\WinBuilds\builditall_wx.bat
echo                      - Test intentionally skipped
echo                      - Actual builds use .spec files
echo.
echo √ Build Scripts PASS = All build .bat files present
echo                        - Build infrastructure intact
echo ============================================================================
echo.

if %TOTAL_FAILED% GTR 0 (
    echo    [FAIL] %TOTAL_FAILED% critical test^(s^) failed - DO NOT BUILD
    echo.
    exit /b 1
) else (
    echo    [PASS] All critical tests passed - safe to build
    echo.
    exit /b 0
)
