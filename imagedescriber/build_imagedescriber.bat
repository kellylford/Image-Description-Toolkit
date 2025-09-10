@echo off
echo Building ImageDescriber GUI Application...

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

REM Detect architecture
for /f "tokens=*" %%i in ('%PYTHON_EXE% -c "import platform; print(platform.machine().lower())"') do set "ARCH=%%i"

REM Fallback if architecture detection failed
if "%ARCH%"=="" set "ARCH=amd64"

if "%ARCH%"=="amd64" (
    set "ARCH_NAME=AMD64"
) else if "%ARCH%"=="arm64" (
    set "ARCH_NAME=ARM64"
) else (
    set "ARCH_NAME=%ARCH%"
)

echo Detected architecture: %ARCH_NAME%

REM Set output directory
set "OUTPUT_DIR=%ROOT_DIR%\dist\imagedescriber_%ARCH_NAME%"

REM Clean previous build
if exist "%OUTPUT_DIR%" (
    echo Cleaning previous build...
    rmdir /s /q "%OUTPUT_DIR%"
)

REM Create output directory
mkdir "%OUTPUT_DIR%"

echo Building with PyInstaller...

REM Build the executable
"%PYTHON_EXE%" -m PyInstaller ^
    --name "ImageDescriber" ^
    --onefile ^
    --windowed ^
    --distpath "%OUTPUT_DIR%" ^
    --workpath "%ROOT_DIR%\build\imagedescriber" ^
    --specpath "%ROOT_DIR%\build\imagedescriber" ^
    --add-data "%ROOT_DIR%\scripts;scripts" ^
    --hidden-import "ollama" ^
    --hidden-import "pillow_heif" ^
    --hidden-import "cv2" ^
    --clean ^
    "%SCRIPT_DIR%\imagedescriber.py"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✓ Build successful!
    echo Single executable created at: %OUTPUT_DIR%\ImageDescriber.exe
    echo.
    echo To run the application:
    echo   "%OUTPUT_DIR%\ImageDescriber.exe"
    echo.
    echo Note: First startup may be slower as the executable extracts dependencies.
    echo.
) else (
    echo.
    echo ✗ Build failed!
    echo Check the output above for errors.
    echo.
)

pause
