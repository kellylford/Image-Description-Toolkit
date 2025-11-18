@echo off
echo ========================================================================
echo Building Image Description Viewer
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

REM Check if PyQt6 is installed
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo PyQt6 not found. Installing viewer dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        exit /b 1
    )
    echo.
)

REM Create output directory
if not exist "dist" mkdir dist

REM Get absolute path to scripts directory (one level up)
set SCRIPTS_DIR=%cd%\..\scripts

REM Check if scripts directory exists
if not exist "%SCRIPTS_DIR%" (
    echo WARNING: Scripts directory not found at: %SCRIPTS_DIR%
    echo.
    echo The redescribe feature will not work in the bundled executable.
    echo However, the viewer will still work for viewing HTML/Live modes.
    echo.
    echo Continuing to build viewer WITHOUT scripts bundled...
    echo.
    
    pyinstaller --onefile ^
        --windowed ^
        --name "viewer" ^
        --distpath "dist" ^
        --workpath "build" ^
        --specpath "build" ^
        --hidden-import PyQt6.QtCore ^
        --hidden-import PyQt6.QtGui ^
        --hidden-import PyQt6.QtWidgets ^
        viewer.py
) else (
    echo Scripts directory found: %SCRIPTS_DIR%
    echo Building viewer WITH scripts bundled ^(redescribe feature enabled^)...
    echo.
    
    pyinstaller --onefile ^
        --windowed ^
        --name "viewer" ^
        --distpath "dist" ^
        --workpath "build" ^
        --specpath "build" ^
        --add-data "%SCRIPTS_DIR%;scripts" ^
        --hidden-import PyQt6.QtCore ^
        --hidden-import PyQt6.QtGui ^
        --hidden-import PyQt6.QtWidgets ^
        viewer.py
)

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
echo Executable created: dist\viewer.exe
echo.
echo To test: cd dist ^&^& viewer.exe
echo.
