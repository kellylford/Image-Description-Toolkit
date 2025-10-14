@echo off
echo ========================================================================
echo Building Image Description Prompt Editor
echo ========================================================================
echo.

REM Detect architecture using current Python
echo Detecting system architecture...
for /f "tokens=*" %%i in ('python -c "import platform; print(platform.machine().lower())"') do set ARCH=%%i

REM Map architecture names for output filename
if "%ARCH%"=="aarch64" set ARCH=arm64
if "%ARCH%"=="arm64" set ARCH=arm64
if "%ARCH%"=="amd64" set ARCH=amd64
if "%ARCH%"=="x86_64" set ARCH=amd64

echo Building for: %ARCH%
echo.
echo NOTE: PyInstaller builds for the current Python architecture.
echo       Cross-compilation is not supported on Windows.
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
    echo PyQt6 not found. Installing prompt editor dependencies...
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
    --windowed ^
    --name "prompteditor_%ARCH%" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    --add-data "%SCRIPTS_DIR%;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    prompt_editor.py

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
echo Executable created: dist\prompteditor_%ARCH%.exe
echo Architecture: %ARCH%
echo.
echo To test: cd dist ^&^& prompteditor_%ARCH%.exe
echo.
