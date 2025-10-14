@echo off
echo ========================================================================
echo Building ImageDescriber GUI Application
echo ========================================================================
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

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo Installing ImageDescriber dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        exit /b 1
    )
    echo.
)

REM Create output directory
if not exist "dist" mkdir dist

REM Get absolute paths
set SCRIPTS_DIR=%cd%\..\scripts
set MODELS_DIR=%cd%\..\models

REM Check if scripts directory exists
if not exist "%SCRIPTS_DIR%" (
    echo ERROR: Scripts directory not found at: %SCRIPTS_DIR%
    echo ImageDescriber requires the scripts directory.
    exit /b 1
)

echo Scripts directory found: %SCRIPTS_DIR%
echo Models directory: %MODELS_DIR%
echo.
echo Building ImageDescriber with all dependencies...
echo.

REM Build the executable
pyinstaller --onefile ^
    --windowed ^
    --name "imagedescriber" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    --add-data "%SCRIPTS_DIR%;scripts" ^
    --add-data "%cd%\ai_providers.py;." ^
    --add-data "%cd%\data_models.py;." ^
    --add-data "%cd%\worker_threads.py;." ^
    --add-data "%cd%\ui_components.py;." ^
    --add-data "%cd%\dialogs.py;." ^
    --hidden-import "ollama" ^
    --hidden-import "pillow_heif" ^
    --hidden-import "cv2" ^
    --hidden-import "ai_providers" ^
    --hidden-import "data_models" ^
    --hidden-import "worker_threads" ^
    --hidden-import "ui_components" ^
    --hidden-import "dialogs" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --exclude-module "onnx.reference" ^
    --exclude-module "onnx.reference.ops" ^
    --exclude-module "torch.testing" ^
    --exclude-module "pytest" ^
    --exclude-module "polars" ^
    --exclude-module "thop" ^
    --exclude-module "scipy.signal" ^
    imagedescriber.py

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
echo Executable created: dist\imagedescriber.exe
echo.
echo To test: cd dist ^&^& imagedescriber.exe
echo.
