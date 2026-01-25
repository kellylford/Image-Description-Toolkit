@echo off
echo ========================================================================
echo Building Image Description Prompt Editor (wxPython Version)
echo ========================================================================
echo.

REM Auto-activate .winenv if not already in a virtual environment
if not defined VIRTUAL_ENV (
    if exist ".winenv\Scripts\activate.bat" (
        echo Activating .winenv...
        call .winenv\Scripts\activate.bat
        set VENV_ACTIVATED=1
    ) else (
        echo WARNING: .winenv not found. Run winsetup.bat first.
        echo Proceeding with system Python...
    )
)
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
    echo wxPython not found. Installing prompt editor dependencies...
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
    echo The prompt editor needs scripts/image_describer_config.json to function.
    echo Build cannot continue without scripts directory.
    echo.
    exit /b 1
)

echo Scripts directory found: %SCRIPTS_DIR%
echo Building prompt editor WITH scripts bundled...
echo.

REM Build the executable
pyinstaller --onefile ^
    --noconfirm ^
    --windowed ^
    --name "prompteditor" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    --add-data "%SCRIPTS_DIR%;scripts" ^
    --paths "%cd%\.." ^
    --hidden-import shared.wx_common ^
    --hidden-import imagedescriber.ai_providers ^
    prompt_editor_wx.py

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
echo Executable created: dist\prompteditor.exe
echo.
echo To test: cd dist ^&^& prompteditor.exe
echo.

REM Deactivate venv if we activated it
if defined VENV_ACTIVATED (
    call deactivate
    set VENV_ACTIVATED=
)
