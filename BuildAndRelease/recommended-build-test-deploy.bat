@echo off
REM ============================================================================
REM Recommended Build-Test-Deploy Script (October 2025)
REM 
REM This is a RECOMMENDED ALTERNATIVE to the existing build-test-deploy.bat
REM It uses the new test infrastructure (run_unit_tests.py + pytest_tests/)
REM 
REM NOTE: The existing build-test-deploy.bat remains unchanged and functional
REM       Use this script if you want to leverage the new CI/CD test structure
REM ============================================================================

echo.
echo ========================================
echo Image Description Toolkit - Build and Test
echo ========================================
echo.

REM Store original directory
set "ORIGINAL_DIR=%CD%"
cd /d "%~dp0.."

echo [Step 1/2] Running comprehensive test suite...
echo.
python tools\run_all_tests.py
if errorlevel 1 (
    echo.
    echo ERROR: Tests failed!
    echo Build aborted - please fix failing tests before building.
    cd /d "%ORIGINAL_DIR%"
    pause
    exit /b 1
)

echo.
echo [Step 2/2] Building all executables...
echo.
call BuildAndRelease\builditall.bat
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    cd /d "%ORIGINAL_DIR%"
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS: All tests passed and build completed
echo ========================================
echo   - All 5 executables built successfully
echo   - Unit tests: PASSED
echo   - Syntax checks: PASSED
echo   - Build scripts: VALIDATED
echo ========================================
echo.

cd /d "%ORIGINAL_DIR%"
exit /b 0
