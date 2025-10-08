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
    pause
    exit /b 1
)

REM Check if spec file exists
if not exist "ImageDescriptionToolkit.spec" (
    echo ERROR: ImageDescriptionToolkit.spec not found
    echo.
    echo Please ensure you are running this script from the project root directory.
    echo.
    pause
    exit /b 1
)

echo [1/4] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo     Done.
echo.

echo [2/4] Building executable with PyInstaller...
echo     This may take 5-10 minutes...
echo.
"%PYTHON_EXE%" -m PyInstaller --clean ImageDescriptionToolkit.spec
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo.
    pause
    exit /b 1
)
echo     Done.
echo.

echo [3/4] Verifying build...
if not exist "dist\ImageDescriptionToolkit.exe" (
    echo ERROR: Executable was not created!
    echo.
    pause
    exit /b 1
)

REM Get file size
for %%A in ("dist\ImageDescriptionToolkit.exe") do set size=%%~zA
set /a size_mb=%size% / 1048576
echo     Executable created: dist\ImageDescriptionToolkit.exe
echo     Size: %size_mb% MB
echo.

echo [4/4] Testing executable...
dist\ImageDescriptionToolkit.exe version
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
echo Executable location: dist\ImageDescriptionToolkit.exe
echo.
echo Next steps:
echo   1. Test the executable: dist\ImageDescriptionToolkit.exe help
echo   2. Create distribution package with create_distribution.bat
echo.
pause
