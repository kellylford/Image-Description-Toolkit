@echo off
echo ========================================================================
echo Building ImageDescriber (wxPython Version) for Windows
echo ========================================================================
echo.

REM Clean PyInstaller cache for fresh build
echo Cleaning PyInstaller cache...
python -c "import shutil; from pathlib import Path; cache_dir = Path.home() / 'AppData' / 'Local' / 'pyinstaller'; shutil.rmtree(cache_dir, ignore_errors=True); print(f'Cleaned: {cache_dir}')"
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller.
        exit /b 1
    )
    echo.
)

REM Check if wxPython is installed
python -c "import wx" 2>nul
if errorlevel 1 (
    echo wxPython not found. Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        exit /b 1
    )
    echo.
)

REM Create output directory
if not exist "dist" mkdir dist

REM Get absolute paths to required directories
set SCRIPTS_DIR=%cd%\..\scripts
set SHARED_DIR=%cd%\..\shared

REM Check if required directories exist
if not exist "%SCRIPTS_DIR%" (
    echo ERROR: Scripts directory not found at: %SCRIPTS_DIR%
    echo.
    echo ImageDescriber requires access to scripts directory.
    echo.
    exit /b 1
)

if not exist "%SHARED_DIR%" (
    echo ERROR: Shared directory not found at: %SHARED_DIR%
    echo.
    echo ImageDescriber requires access to shared utilities in shared/
    echo.
    exit /b 1
)

echo Scripts directory found: %SCRIPTS_DIR%
echo Shared directory found: %SHARED_DIR%
echo Building ImageDescriber with wxPython and bundled dependencies...
echo.

REM Build using the spec file
pyinstaller imagedescriber_wx.spec --clean

if errorlevel 1 (
    echo.
    echo ========================================================================
    echo BUILD FAILED
    echo ========================================================================
    exit /b 1
)

echo.
echo ========================================================================
echo BUILD SUCCESSFUL
echo ========================================================================
echo Executable created: dist\ImageDescriber.exe
echo.
