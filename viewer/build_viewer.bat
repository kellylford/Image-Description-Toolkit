@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Image Description Viewer - Build Script
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

REM Build for current architecture first
echo ========================================
echo Building for current architecture (%ARCH%)
echo ========================================

REM Determine architecture suffix
set ARCH_SUFFIX=amd64
if /i "%ARCH%"=="amd64" set ARCH_SUFFIX=amd64
if /i "%ARCH%"=="x86_64" set ARCH_SUFFIX=amd64
if /i "%ARCH%"=="x86" set ARCH_SUFFIX=x86
if /i "%ARCH%"=="i386" set ARCH_SUFFIX=x86
if /i "%ARCH%"=="i686" set ARCH_SUFFIX=x86
if /i "%ARCH%"=="arm64" set ARCH_SUFFIX=arm64
if /i "%ARCH%"=="aarch64" set ARCH_SUFFIX=arm64

echo Architecture suffix: %ARCH_SUFFIX%

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name ImageDescriptionViewer-%ARCH_SUFFIX% ^
    --distpath dist/%ARCH_SUFFIX% ^
    --add-data "../scripts;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import PyQt6.QtSvg ^
    --collect-all PyQt6 ^
    viewer.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed for %ARCH_SUFFIX%!
    pause
    exit /b 1
)

echo Build completed for %ARCH_SUFFIX%!

REM Clean up intermediate files before next build
if exist build rmdir /s /q build
if exist *.spec del *.spec

REM If we're on AMD64, also try to build for ARM64 (cross-compilation)
if /i "%ARCH_SUFFIX%"=="amd64" (
    echo.
    echo ========================================
    echo Attempting cross-compilation for ARM64
    echo ========================================
    echo Note: This may not work depending on your Python installation
    echo.
    
    REM Try to build ARM64 version (this may fail on some systems)
    python -m PyInstaller ^
        --onefile ^
        --windowed ^
        --name ImageDescriptionViewer-arm64 ^
        --distpath dist/arm64 ^
        --add-data "../scripts;scripts" ^
        --hidden-import PyQt6.QtCore ^
        --hidden-import PyQt6.QtGui ^
        --hidden-import PyQt6.QtWidgets ^
        --hidden-import PyQt6.QtSvg ^
        --collect-all PyQt6 ^
        --target-architecture arm64 ^
        viewer.py
    
    if errorlevel 1 (
        echo WARNING: ARM64 cross-compilation failed
        echo This is normal - ARM64 builds typically require an ARM64 system
        echo Only %ARCH_SUFFIX% build is available
    ) else (
        echo ARM64 cross-compilation successful!
    )
    
    REM Clean up intermediate files
    if exist build rmdir /s /q build
    if exist *.spec del *.spec
)

echo.
echo Creating README files for each build...

REM Create README for each architecture built
for /d %%D in (dist\*) do (
    set CURRENT_ARCH=%%~nD
    echo Creating README for !CURRENT_ARCH!...
    
    (
        echo Image Description Viewer - Standalone Executable ^(!CURRENT_ARCH!^)
        echo ================================================================
        echo.
        echo This is a standalone version of the Image Description Viewer
        echo built for !CURRENT_ARCH! architecture.
        echo No Python installation required!
        echo.
        echo Usage:
        echo 1. Double-click ImageDescriptionViewer-!CURRENT_ARCH!.exe to launch
        echo 2. Click 'Change Directory' to select a workflow output folder
        echo 3. Use 'Live Mode' to monitor active workflows
        echo.
        echo System Requirements:
        echo - Windows 10/11 ^(!CURRENT_ARCH!^)
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
    echo Image Description Viewer - Multi-Architecture Builds
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
    
    if exist "%%D\ImageDescriptionViewer-!CURRENT_ARCH!.exe" (
        for %%I in ("%%D\ImageDescriptionViewer-!CURRENT_ARCH!.exe") do set size=%%~zI
        set /a sizeMB=!size!/1048576
        echo !CURRENT_ARCH!/    - For !CURRENT_ARCH! systems ^(!sizeMB! MB^) >> dist\README.txt
        echo   Found: ImageDescriptionViewer-!CURRENT_ARCH!.exe ^(!sizeMB! MB^)
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
echo BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo Available builds in 'dist' folder:
for /d %%D in (dist\*) do (
    set CURRENT_ARCH=%%~nD
    if exist "%%D\ImageDescriptionViewer-!CURRENT_ARCH!.exe" (
        echo   - !CURRENT_ARCH!/ directory
    )
)
echo.
echo Each directory contains:
echo   - ImageDescriptionViewer-[arch].exe
echo   - README.txt with usage instructions
echo.
echo You can share the entire 'dist' folder or individual architecture folders.
echo Users should choose the folder matching their system architecture.
echo.
pause
