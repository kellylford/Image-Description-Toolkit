@echo off
REM ============================================================================
REM Image Description Toolkit - Build Executable
REM ============================================================================
REM This script builds a standalone executable using PyInstaller
REM
REM Prerequisites:
REM   - Python virtual environment with PyInstaller installed
REM   - If using venv: Activate it first, OR this script will auto-detect
REM
REM Output:
REM   - dist/ImageDescriptionToolkit.exe (~150-200MB)
REM ============================================================================

echo.
echo ========================================================================
echo Building Image Description Toolkit Executable
echo ========================================================================
echo.

REM Change to project root directory
cd /d "%~dp0.."

REM Detect Python executable (venv or system)
set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    echo Using virtual environment Python: .venv
    echo.
)

REM Check if PyInstaller is installed
"%PYTHON_EXE%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed
    echo.
    echo Please install it with:
    echo     pip install pyinstaller
    echo.
    echo Or if using venv:
    echo     .venv\Scripts\pip.exe install pyinstaller
    echo.
    exit /b 1
)

REM Check if spec file exists
if not exist "BuildAndRelease\final_working.spec" (
    echo ERROR: final_working.spec not found
    echo.
    echo Please ensure you are running this script from the project root directory.
    echo.
    exit /b 1
)

echo [1/4] Cleaning previous builds...
echo     Cleaning PyInstaller cache...
"%PYTHON_EXE%" -c "import shutil; from pathlib import Path; cache_dir = Path.home() / 'AppData' / 'Local' / 'pyinstaller'; shutil.rmtree(cache_dir, ignore_errors=True); print(f'    Cleaned: {cache_dir}')"
echo     Cleaning build and dist directories...
REM Preserve BUILD_TRACKER.json before cleaning
if exist "build\BUILD_TRACKER.json" (
    copy /Y "build\BUILD_TRACKER.json" "BUILD_TRACKER.json.tmp" >nul 2>&1
)
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
REM Restore BUILD_TRACKER.json after cleaning
if exist "BUILD_TRACKER.json.tmp" (
    mkdir "build" 2>nul
    copy /Y "BUILD_TRACKER.json.tmp" "build\BUILD_TRACKER.json" >nul 2>&1
    del "BUILD_TRACKER.json.tmp" >nul 2>&1
)
echo     Done.
echo.

echo [2/4] Building executable with PyInstaller...
echo     This may take 5-10 minutes...
echo.
"%PYTHON_EXE%" -m PyInstaller --clean buildandrelease\final_working.spec
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo.
    exit /b 1
)
echo     Done.
echo.

echo [3/4] Verifying build...
if not exist "dist\idt.exe" (
    echo ERROR: Executable was not created!
    echo.
    exit /b 1
)

REM Get file size
for %%A in ("dist\idt.exe") do set size=%%~zA
set /a size_mb=%size% / 1048576
echo     Executable created: dist\idt.exe
echo     Size: %size_mb% MB
echo.

echo [4/4] Testing executable...
dist\idt.exe version
if errorlevel 1 (
    echo WARNING: Executable test failed
    echo.
) else (
    echo     Test successful!
)
echo.

echo ========================================================================
echo Build Complete!
echo ========================================================================
echo.
echo Executable location: dist\idt.exe
echo.
echo Next steps:
echo   1. Test the executable: dist\idt.exe help
echo   2. Create distribution package with package_idt.bat
echo.
