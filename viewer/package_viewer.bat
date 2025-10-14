@echo off
REM ============================================================================
REM Create Distribution Package for Image Description Viewer
REM ============================================================================
REM This script creates a distributable ZIP file with the viewer executable
REM and documentation.
REM
REM Prerequisites:
REM   - Built executable in dist/ folder (run build_viewer.bat first)
REM
REM Output:
REM   - viewer_releases/viewer_v[VERSION].zip
REM ============================================================================

echo.
echo ========================================================================
echo Creating Viewer Distribution Package
echo ========================================================================
echo.

REM Check if executable exists
if not exist "dist\viewer.exe" (
    echo ERROR: Executable not found!
    echo.
    echo Expected: dist\viewer.exe
    echo.
    echo Please run build_viewer.bat first to create the executable.
    echo.
    exit /b 1
)

REM Get version from parent directory
set VERSION=unknown
if exist "..\VERSION" (
    set /p VERSION=<..\VERSION
)

REM Create releases directory
if not exist "viewer_releases" mkdir viewer_releases

REM Create temporary staging directory
set STAGE_DIR=viewer_releases\staging
if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

echo [1/3] Copying executable...
copy "dist\viewer.exe" "%STAGE_DIR%\viewer.exe" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable
    exit /b 1
)

echo [2/3] Creating README...
REM Create a distribution README
(
echo Image Description Viewer v%VERSION%
echo.
echo STANDALONE VIEWER APPLICATION
echo.
echo This is the standalone viewer for browsing image descriptions created
echo by the Image Description Toolkit ^(IDT^).
echo.
echo USAGE:
echo.
echo 1. Double-click viewer.exe to launch
echo.
echo 2. Choose viewing mode:
echo    - HTML Mode: Browse completed workflow output ^(Descriptions folder^)
echo    - Live Mode: Monitor in-progress workflows in real-time
echo.
echo 3. Use the Browse button to select your Descriptions folder
echo.
echo FEATURES:
echo - View image descriptions with thumbnails
echo - Copy descriptions to clipboard
echo - Real-time monitoring of active workflows
echo - Keyboard shortcuts for easy navigation
echo - Screen reader accessible
echo.
echo REQUIREMENTS:
echo - Windows 10 or later
echo - Optional: Ollama ^(for redescribe feature^)
echo.
echo NOTES:
echo - The redescribe feature requires Ollama to be installed and running
echo - Works with output from IDT workflows
echo - No installation required - just run viewer.exe
echo.
echo For the full Image Description Toolkit, visit:
echo https://github.com/kellylford/Image-Description-Toolkit
echo.
echo License: See LICENSE file
) > "%STAGE_DIR%\README.txt"

echo [3/3] Copying license...
if exist "..\LICENSE" (
    copy "..\LICENSE" "%STAGE_DIR%\LICENSE.txt" >nul
) else (
    echo Note: LICENSE file not found, skipping
)

REM Create the ZIP file
set ZIP_NAME=viewer_v%VERSION%.zip
set ZIP_PATH=viewer_releases\%ZIP_NAME%

echo.
echo Creating ZIP archive...
echo Target: %ZIP_PATH%
echo.

REM Remove old zip if exists
if exist "%ZIP_PATH%" del "%ZIP_PATH%"

REM Create ZIP using PowerShell
powershell -Command "Compress-Archive -Path '%STAGE_DIR%\*' -DestinationPath '%ZIP_PATH%' -CompressionLevel Optimal"

if errorlevel 1 (
    echo ERROR: Failed to create ZIP file
    exit /b 1
)

REM Clean up staging directory
rmdir /s /q "%STAGE_DIR%"

echo.
echo ========================================================================
echo PACKAGE CREATED SUCCESSFULLY
echo ========================================================================
echo.
echo Package: %ZIP_NAME%
echo Location: viewer_releases\
echo Version: %VERSION%
echo.
echo Contents:
echo   - viewer.exe
echo   - README.txt
echo   - LICENSE.txt
echo.
