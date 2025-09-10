@echo off
echo Building ImageDescriber GUI Application for AMD64...
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

echo Building for AMD64 architecture...

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

REM Build the executable for AMD64
"%PYTHON_EXE%" -m PyInstaller ^
    --name "ImageDescriber_amd64" ^
    --onefile ^
    --windowed ^
    --distpath "%OUTPUT_DIR%" ^
    --workpath "%ROOT_DIR%\build\imagedescriber_amd64" ^
    --specpath "%ROOT_DIR%\build\imagedescriber_amd64" ^
    --add-data "%ROOT_DIR%\scripts;scripts" ^
    --hidden-import "ollama" ^
    --hidden-import "pillow_heif" ^
    --hidden-import "cv2" ^
    --target-architecture amd64 ^
    --clean ^
    "%SCRIPT_DIR%\imagedescriber.py"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✓ AMD64 build successful!
    echo Single executable created at: %OUTPUT_DIR%\ImageDescriber_amd64.exe
    echo.
    echo To run the application:
    echo   "%OUTPUT_DIR%\ImageDescriber_amd64.exe"
    echo.
    echo Note: First startup may be slower as the executable extracts dependencies.
    echo.
) else (
    echo.
    echo ✗ AMD64 build failed!
    echo Check the output above for errors.
    echo.
)

pause
