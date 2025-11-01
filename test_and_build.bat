@echo off
REM ============================================================================
REM Complete Test-Build-Verify Pipeline
REM ============================================================================
REM This script implements the user's #1 testing priority:
REM   1. Build the project (idt.exe)
REM   2. Run a workflow with the frozen executable using test images
REM   3. Verify that the workflow generates results
REM
REM This replaces manual testing and provides confidence that the frozen
REM executable works end-to-end.
REM
REM Usage:
REM   test_and_build.bat [--skip-unit-tests] [--skip-build] [--keep-output]
REM
REM Options:
REM   --skip-unit-tests   Skip pre-build unit tests (faster, less safe)
REM   --skip-build        Skip build step (test existing executable)
REM   --keep-output       Don't delete test workflow output
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo IDT Test-Build-Verify Pipeline
echo ============================================================================
echo.

REM Parse command line arguments
set SKIP_UNIT_TESTS=0
set SKIP_BUILD=0
set KEEP_OUTPUT=0

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--skip-unit-tests" set SKIP_UNIT_TESTS=1
if /i "%~1"=="--skip-build" set SKIP_BUILD=1
if /i "%~1"=="--keep-output" set KEEP_OUTPUT=1
shift
goto :parse_args
:args_done

REM Change to project root
cd /d "%~dp0"

REM Timestamp for unique test output directory
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set TEST_OUTPUT_DIR=%CD%\test_output_%TIMESTAMP%

echo Configuration:
echo   Skip Unit Tests: %SKIP_UNIT_TESTS%
echo   Skip Build:      %SKIP_BUILD%
echo   Keep Output:     %KEEP_OUTPUT%
echo   Test Output:     %TEST_OUTPUT_DIR%
echo.

REM ============================================================================
REM PHASE 1: Pre-Build Unit Tests
REM ============================================================================
if %SKIP_UNIT_TESTS%==0 (
    echo ============================================================================
    echo PHASE 1: Pre-Build Unit Tests
    echo ============================================================================
    echo.
    echo Running unit tests to verify code quality before building...
    echo.

    if not exist ".venv\Scripts\python.exe" (
        echo ERROR: Virtual environment not found at .venv
        echo Please run setup.bat first
        exit /b 1
    )

    REM Run unit tests using custom runner (Python 3.13 compatible)
    .venv\Scripts\python.exe run_unit_tests.py
    if errorlevel 1 (
        echo.
        echo ============================================================================
        echo FAILED: Unit tests failed!
        echo ============================================================================
        echo.
        echo Fix unit test failures before proceeding.
        echo.
        exit /b 1
    )

    echo.
    echo [OK] Unit tests passed
    echo.
) else (
    echo [SKIPPED] Pre-build unit tests
    echo.
)

REM ============================================================================
REM PHASE 2: Build Frozen Executable
REM ============================================================================
if %SKIP_BUILD%==0 (
    echo ============================================================================
    echo PHASE 2: Build Frozen Executable
    echo ============================================================================
    echo.

    REM Clean previous build artifacts
    if exist "dist\idt.exe" (
        echo Removing old executable...
        del /q "dist\idt.exe" 2>nul
    )
    if exist "build" (
        echo Cleaning build directory...
        rmdir /s /q "build" 2>nul
    )

    echo Building idt.exe with PyInstaller...
    echo.

    call BuildAndRelease\build_idt.bat
    if errorlevel 1 (
        echo.
        echo ============================================================================
        echo FAILED: Build failed!
        echo ============================================================================
        echo.
        exit /b 1
    )

    REM Verify executable was created
    if not exist "dist\idt.exe" (
        echo.
        echo ============================================================================
        echo FAILED: Build reported success but dist\idt.exe not found!
        echo ============================================================================
        echo.
        exit /b 1
    )

    echo.
    echo [OK] Build completed successfully
    echo.
) else (
    echo [SKIPPED] Build step
    echo.
    
    REM Still verify executable exists
    if not exist "dist\idt.exe" (
        echo ERROR: dist\idt.exe not found and build was skipped!
        echo Either build first or remove --skip-build flag.
        exit /b 1
    )
)

REM ============================================================================
REM PHASE 3: Smoke Tests
REM ============================================================================
echo ============================================================================
echo PHASE 3: Smoke Tests
echo ============================================================================
echo.

echo Testing: idt.exe version command...
dist\idt.exe version > nul 2>&1
if errorlevel 1 (
    echo [FAIL] idt.exe version command failed
    exit /b 1
)
echo [PASS] idt.exe version

echo Testing: idt.exe help command...
dist\idt.exe --help > nul 2>&1
if errorlevel 1 (
    echo [FAIL] idt.exe help command failed
    exit /b 1
)
echo [PASS] idt.exe --help

echo Testing: idt.exe workflow help...
dist\idt.exe workflow --help > nul 2>&1
if errorlevel 1 (
    echo [FAIL] idt.exe workflow --help failed
    exit /b 1
)
echo [PASS] idt.exe workflow --help

echo.
echo [OK] All smoke tests passed
echo.

REM ============================================================================
REM PHASE 4: End-to-End Workflow Test
REM ============================================================================
echo ============================================================================
echo PHASE 4: End-to-End Workflow Test
echo ============================================================================
echo.

REM Verify test images exist
if not exist "test_data\849adfa4fe72c4fd8f6482ecfde0a4a1.jpeg" (
    echo ERROR: Test data not found at test_data\
    echo Required: test_data\849adfa4fe72c4fd8f6482ecfde0a4a1.jpeg
    exit /b 1
)

echo Test Setup:
echo   - Executable: dist\idt.exe
echo   - Test Images: test_data\
echo   - Output: %TEST_OUTPUT_DIR%
echo   - Model: moondream (fast local model)
echo   - Prompt Style: concise
echo.

REM Create test output directory
mkdir "%TEST_OUTPUT_DIR%" 2>nul

echo Running workflow with frozen executable...
echo This will process test images and generate descriptions.
echo.

REM Run workflow with frozen executable
REM Use moondream (small/fast) model with concise prompt for speed
REM Redirect output to log file for later inspection
set LOG_FILE=%TEST_OUTPUT_DIR%\workflow_test.log

dist\idt.exe workflow test_data ^
    --output "%TEST_OUTPUT_DIR%" ^
    --model moondream ^
    --prompt-style concise ^
    --steps describe,html ^
    --no-view > "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo.
    echo ============================================================================
    echo FAILED: Workflow execution failed!
    echo ============================================================================
    echo.
    echo Check log file for details: %LOG_FILE%
    echo.
    type "%LOG_FILE%"
    echo.
    exit /b 1
)

echo.
echo [OK] Workflow completed without errors
echo.

REM ============================================================================
REM PHASE 5: Verify Results
REM ============================================================================
echo ============================================================================
echo PHASE 5: Verify Results
echo ============================================================================
echo.

REM Check for workflow directory creation
set WORKFLOW_DIR_FOUND=0
for /d %%D in ("%TEST_OUTPUT_DIR%\wf_*") do (
    set WORKFLOW_DIR=%%D
    set WORKFLOW_DIR_FOUND=1
)

if %WORKFLOW_DIR_FOUND%==0 (
    echo [FAIL] No workflow directory (wf_*) created in %TEST_OUTPUT_DIR%
    echo.
    echo Directory contents:
    dir "%TEST_OUTPUT_DIR%" /b
    echo.
    exit /b 1
)
echo [PASS] Workflow directory created: %WORKFLOW_DIR%

REM Check for descriptions directory
if not exist "%WORKFLOW_DIR%\descriptions" (
    echo [FAIL] Descriptions directory not created
    exit /b 1
)
echo [PASS] Descriptions directory exists

REM Count description files
set DESC_COUNT=0
for %%F in ("%WORKFLOW_DIR%\descriptions\*.txt") do set /a DESC_COUNT+=1

if %DESC_COUNT%==0 (
    echo [FAIL] No description files generated
    echo.
    echo Workflow directory contents:
    dir "%WORKFLOW_DIR%" /s /b
    echo.
    exit /b 1
)
echo [PASS] Generated %DESC_COUNT% description file(s)

REM Check for HTML output
if not exist "%WORKFLOW_DIR%\html_reports\index.html" (
    echo [FAIL] HTML report not generated
    exit /b 1
)
echo [PASS] HTML report generated

REM Verify HTML contains expected content
findstr /i "Image Description Report" "%WORKFLOW_DIR%\html_reports\index.html" > nul
if errorlevel 1 (
    echo [FAIL] HTML report doesn't contain expected content
    exit /b 1
)
echo [PASS] HTML report contains valid content

REM Check for workflow metadata
if not exist "%WORKFLOW_DIR%\workflow_metadata.json" (
    echo [WARN] workflow_metadata.json not found (optional)
) else (
    echo [PASS] Workflow metadata file exists
)

REM Check for status log
if not exist "%WORKFLOW_DIR%\logs\status_log.json" (
    echo [WARN] status_log.json not found (optional)
) else (
    echo [PASS] Status log exists
)

echo.
echo ============================================================================
echo SUCCESS: All Tests Passed!
echo ============================================================================
echo.
echo Results Summary:
echo   - Unit Tests:      %SKIP_UNIT_TESTS:0=PASSED%
echo   - Build:           %SKIP_BUILD:0=SUCCESS%
echo   - Smoke Tests:     PASSED
echo   - E2E Workflow:    PASSED
echo   - Descriptions:    %DESC_COUNT% file(s) generated
echo   - HTML Report:     GENERATED
echo.
echo Workflow Output: %WORKFLOW_DIR%
echo Log File:        %LOG_FILE%
echo.

REM Cleanup test output unless requested to keep
if %KEEP_OUTPUT%==0 (
    echo Cleaning up test output directory...
    rmdir /s /q "%TEST_OUTPUT_DIR%" 2>nul
    echo [OK] Test output cleaned
) else (
    echo Test output preserved at: %TEST_OUTPUT_DIR%
)

echo.
echo ============================================================================
echo The frozen executable is verified and ready for deployment!
echo ============================================================================
echo.

exit /b 0
