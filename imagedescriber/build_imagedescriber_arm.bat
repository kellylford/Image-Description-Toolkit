@echo off
echo Building ImageDescriber GUI Application for ARM64...
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."

REM Check if virtual environment exists
if not exist "%ROOT_DIR%\.venv" (
    echo Error: Virtual environment not found at %ROOT_DIR%\.venv
    echo Please create and activate the virtual environment first.
    pause
    exit /b 1
)

REM Get Python executable from virtual environment
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

REM Verify Python executable exists
if not exist "%PYTHON_EXE%" (
    echo Error: Python executable not found at %PYTHON_EXE%
    pause
    exit /b 1
)

echo Building for ARM64 architecture...

REM Set output directory
set "OUTPUT_DIR=%ROOT_DIR%\dist\imagedescriber"

REM Clean previous build
if exist "%OUTPUT_DIR%" (
    echo Cleaning previous build...
    rmdir /s /q "%OUTPUT_DIR%"
)

REM Create output directory
mkdir "%OUTPUT_DIR%"

echo Building with PyInstaller...

REM Build the executable for ARM64
"%PYTHON_EXE%" -m PyInstaller ^
    --name "ImageDescriber_arm64" ^
    --onefile ^
    --windowed ^
    --distpath "%OUTPUT_DIR%" ^
    --workpath "%ROOT_DIR%\build\imagedescriber_arm64" ^
    --specpath "%ROOT_DIR%\build\imagedescriber_arm64" ^
    --add-data "%ROOT_DIR%\scripts;scripts" ^
    --add-data "%SCRIPT_DIR%\ai_providers.py;." ^
    --add-data "%SCRIPT_DIR%\data_models.py;." ^
    --add-data "%SCRIPT_DIR%\worker_threads.py;." ^
    --add-data "%SCRIPT_DIR%\ui_components.py;." ^
    --add-data "%SCRIPT_DIR%\dialogs.py;." ^
    --hidden-import "ollama" ^
    --hidden-import "pillow_heif" ^
    --hidden-import "cv2" ^
    --hidden-import "ai_providers" ^
    --hidden-import "data_models" ^
    --hidden-import "worker_threads" ^
    --hidden-import "ui_components" ^
    --hidden-import "dialogs" ^
    --target-architecture arm64 ^
    --clean ^
    "%SCRIPT_DIR%\imagedescriber.py"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✓ ARM64 build successful!
    echo Single executable created at: %OUTPUT_DIR%\ImageDescriber_arm64.exe
    echo.
    echo Copying user documentation...
    copy "%SCRIPT_DIR%\USER_SETUP_GUIDE.md" "%OUTPUT_DIR%\" >nul 2>&1
    copy "%SCRIPT_DIR%\WHATS_INCLUDED.txt" "%OUTPUT_DIR%\" >nul 2>&1
    copy "%SCRIPT_DIR%\DISTRIBUTION_README.txt" "%OUTPUT_DIR%\README.txt" >nul 2>&1
    copy "%SCRIPT_DIR%\setup_imagedescriber.bat" "%OUTPUT_DIR%\" >nul 2>&1
    copy "%SCRIPT_DIR%\download_onnx_models.bat" "%OUTPUT_DIR%\" >nul 2>&1
    echo Documentation files copied to distribution folder.
    echo.
    echo ================================================================
    echo Distribution Package Contents:
    echo ================================================================
    echo   ImageDescriber_arm64.exe       - Main application
    echo   README.txt                     - START HERE (quick start guide)
    echo   USER_SETUP_GUIDE.md            - Detailed setup instructions
    echo   WHATS_INCLUDED.txt             - What's bundled vs optional
    echo   setup_imagedescriber.bat       - Interactive setup assistant
    echo   download_onnx_models.bat       - ONNX model downloader
    echo ================================================================
    echo.
    echo To distribute to end users:
    echo   1. Zip the entire folder: %OUTPUT_DIR%
    echo   2. Users extract and run ImageDescriber_arm64.exe
    echo   3. Users run setup_imagedescriber.bat for AI features
    echo.
    echo To run the application:
    echo   "%OUTPUT_DIR%\ImageDescriber_arm64.exe"
    echo.
    echo Note: First startup may be slower as the executable extracts dependencies.
    echo Note: Cross-compilation to ARM64 may require an ARM64 host system.
    echo.
) else (
    echo.
    echo ✗ ARM64 build failed!
    echo Check the output above for errors.
    echo Note: Cross-compilation to ARM64 may require an ARM64 host system.
    echo.
)

pause
