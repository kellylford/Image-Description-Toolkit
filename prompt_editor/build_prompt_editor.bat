@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Image Description Prompt Editor - Build Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

echo Checking for PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
    echo PyInstaller installed successfully!
) else (
    echo PyInstaller is already installed
)

echo.
echo Detecting system architecture...

REM Use Python to detect architecture - more reliable than wmic
for /f "usebackq tokens=*" %%i in (`python -c "import platform; print(platform.machine().lower())"`) do set ARCH=%%i
echo Detected architecture: %ARCH%

echo.
echo Building standalone executables for multiple architectures...
echo.

REM Clean up any previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM Create dist directory structure
mkdir dist

REM Always build for both AMD64 and ARM64 architectures
set BUILD_ARCHITECTURES=amd64 arm64

for %%A in (%BUILD_ARCHITECTURES%) do (
    echo.
    echo ========================================
    echo Building for %%A architecture
    echo ========================================
    
    REM Set target architecture flags
    set TARGET_FLAGS=
    if /i "%%A"=="arm64" set TARGET_FLAGS=--target-architecture arm64
    
    python -m PyInstaller ^
        --onefile ^
        --windowed ^
        --name prompt_editor-%%A ^
        --distpath dist/%%A ^
        --add-data "scripts;scripts" ^
        !TARGET_FLAGS! ^
        prompt_editor/prompt_editor.py
    
    if errorlevel 1 (
        echo.
        echo WARNING: Build failed for %%A architecture!
        echo This may be due to cross-compilation limitations.
        echo Continuing with other architectures...
    ) else (
        echo Build completed successfully for %%A!
    )
    
    REM Clean up intermediate files before next build
    if exist build rmdir /s /q build
    if exist *.spec del *.spec
    
    echo.
)

echo.
echo Creating README files for each build...

REM Create README for each architecture built
for /d %%D in (dist\*) do (
    set CURRENT_ARCH=%%~nD
    echo Creating README for !CURRENT_ARCH!...
    
    (
        echo Image Description Prompt Editor - Standalone Executable ^(!CURRENT_ARCH!^)
        echo ================================================================
        echo.
        echo This is a standalone version of the Image Description Prompt Editor
        echo built for !CURRENT_ARCH! architecture.
        echo No Python installation required!
        echo.
        echo Usage:
        echo 1. Double-click prompt_editor-!CURRENT_ARCH!.exe to launch
        echo 2. Use File menu to open different configuration files
        echo 3. Edit prompts and set default AI model
        echo 4. Save or Save As to create custom configurations
        echo.
        echo System Requirements:
        echo - Windows 10/11 ^(!CURRENT_ARCH!^)
        echo - Ollama installed ^(for model selection^)
        echo - No additional software required
        echo.
        echo For more information, see:
        echo https://github.com/kellylford/Image-Description-Toolkit
        echo.
        echo Built on: %date% %time%
        echo Architecture: !CURRENT_ARCH!
    ) > "%%D\README.txt"
)

echo.
echo Generating build summary...

REM Create a master README
(
    echo Image Description Prompt Editor - Multi-Architecture Builds
    echo ===================================================
    echo.
    echo This package contains standalone executables for different
    echo Windows architectures. Choose the correct version for your system:
    echo.
) > dist\README.txt

REM List available builds and their sizes
for /d %%D in (dist\*) do (
    set CURRENT_ARCH=%%~nD
    echo Checking build for !CURRENT_ARCH!...
    
    if exist "%%D\prompt_editor-!CURRENT_ARCH!.exe" (
        for %%I in ("%%D\prompt_editor-!CURRENT_ARCH!.exe") do set size=%%~zI
        set /a sizeMB=!size!/1048576
        echo !CURRENT_ARCH!/    - For !CURRENT_ARCH! systems ^(!sizeMB! MB^) >> dist\README.txt
        echo   Found: prompt_editor-!CURRENT_ARCH!.exe ^(!sizeMB! MB^)
    )
)

(
    echo.
    echo How to determine your architecture:
    echo - Most modern PCs: Use AMD64 version
    echo - ARM-based PCs ^(Surface Pro X, etc.^): Use ARM64 version
    echo - Older 32-bit systems: Contact support
    echo.
    echo All versions have identical functionality.
) >> dist\README.txt

echo.
echo Cleaning up temporary files...
if exist build rmdir /s /q build
if exist *.spec del *.spec

echo.
echo ========================================
echo BUILD PROCESS COMPLETED!
echo ========================================
echo.
echo Note: Cross-compilation may not work on all systems.
echo ARM64 builds typically require an ARM64 host system.
echo AMD64 builds should work on most systems.
echo.
echo Available builds in 'dist' folder:
for /d %%D in (dist\*) do (
    set CURRENT_ARCH=%%~nD
    if exist "%%D\prompt_editor-!CURRENT_ARCH!.exe" (
        echo   - !CURRENT_ARCH!/ directory
    )
)
echo.
echo Each directory contains:
echo   - prompt_editor-[arch].exe
echo   - README.txt with usage instructions
echo.
echo You can share the entire 'dist' folder or individual architecture folders.
echo Users should choose the folder matching their system architecture.
echo.
pause
