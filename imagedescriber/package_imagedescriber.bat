@echo off
REM ============================================================================
REM Create Distribution Package for ImageDescriber
REM ============================================================================
REM This script creates a distributable ZIP file with the ImageDescriber
REM executable and all documentation.
REM
REM Prerequisites:
REM   - Built executable in dist/ folder (run build_imagedescriber.bat first)
REM
REM Output:
REM   - imagedescriber_releases/imagedescriber_v[VERSION].zip
REM ============================================================================

echo.
echo ========================================================================
echo Creating ImageDescriber Distribution Package
echo ========================================================================
echo.

REM Check if executable exists
if not exist "dist\imagedescriber.exe" (
    echo ERROR: Executable not found!
    echo.
    echo Expected: dist\imagedescriber.exe
    echo.
    echo Please run build_imagedescriber.bat first to create the executable.
    echo.
    exit /b 1
)

REM Get version from parent directory
set VERSION=unknown
if exist "..\VERSION" (
    set /p VERSION=<..\VERSION
)

REM Create releases directory
if not exist "imagedescriber_releases" mkdir imagedescriber_releases

REM Create temporary staging directory
set STAGE_DIR=imagedescriber_releases\staging
if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

echo [1/4] Copying executable...
copy "dist\imagedescriber.exe" "%STAGE_DIR%\imagedescriber.exe" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable
    exit /b 1
)

echo [2/4] Copying documentation...
if exist "dist_templates\USER_SETUP_GUIDE.md" copy "dist_templates\USER_SETUP_GUIDE.md" "%STAGE_DIR%\" >nul
if exist "dist_templates\WHATS_INCLUDED.txt" copy "dist_templates\WHATS_INCLUDED.txt" "%STAGE_DIR%\" >nul
if exist "dist_templates\DISTRIBUTION_README.txt" copy "dist_templates\DISTRIBUTION_README.txt" "%STAGE_DIR%\README.txt" >nul
if exist "setup_imagedescriber.bat" copy "setup_imagedescriber.bat" "%STAGE_DIR%\" >nul
if exist "..\models\download_onnx_models.bat" copy "..\models\download_onnx_models.bat" "%STAGE_DIR%\" >nul
if exist "..\models\install_groundingdino.bat" copy "..\models\install_groundingdino.bat" "%STAGE_DIR%\" >nul
if exist "test_groundingdino.bat" copy "test_groundingdino.bat" "%STAGE_DIR%\" >nul
if exist "GROUNDINGDINO_QUICK_REFERENCE.md" copy "GROUNDINGDINO_QUICK_REFERENCE.md" "%STAGE_DIR%\" >nul

echo [3/4] Creating main README...
if not exist "%STAGE_DIR%\README.txt" (
    (
    echo ImageDescriber v%VERSION%
    echo.
    echo COMPREHENSIVE IMAGE DESCRIPTION GUI
    echo.
    echo This is the standalone GUI application for processing images
    echo with AI-powered descriptions using multiple providers.
    echo.
    echo QUICK START:
    echo.
    echo 1. Double-click imagedescriber.exe to launch
    echo.
    echo 2. Configure AI providers:
    echo    - Ollama: Local AI models ^(recommended^)
    echo    - OpenAI: GPT-4 Vision API
    echo    - Anthropic: Claude Vision API
    echo.
    echo 3. Load images or folders
    echo.
    echo 4. Select provider and model
    echo.
    echo 5. Process images
    echo.
    echo FEATURES:
    echo - Multi-provider AI support ^(Ollama, OpenAI, Anthropic^)
    echo - Multiple image processing
    echo - Workspace management
    echo - Progress tracking
    echo - Real-time preview
    echo - Export to multiple formats
    echo - Screen reader accessible
    echo.
    echo OPTIONAL FEATURES:
    echo - GroundingDINO object detection
    echo - ONNX model support
    echo - Video frame extraction
    echo - HEIC/HEIF image support
    echo.
    echo REQUIREMENTS:
    echo - Windows 10 or later
    echo - AI provider ^(Ollama recommended, or OpenAI/Anthropic API keys^)
    echo.
    echo For the full Image Description Toolkit, visit:
    echo https://github.com/kellylford/Image-Description-Toolkit
    echo.
    echo License: See LICENSE file
    ) > "%STAGE_DIR%\README.txt"
)

echo [4/4] Copying license...
if exist "..\LICENSE" (
    copy "..\LICENSE" "%STAGE_DIR%\LICENSE.txt" >nul
) else (
    echo Note: LICENSE file not found, skipping
)

REM Create the ZIP file
set ZIP_NAME=imagedescriber_v%VERSION%.zip
set ZIP_PATH=imagedescriber_releases\%ZIP_NAME%

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
echo Location: imagedescriber_releases\
echo Version: %VERSION%
echo.
echo Contents:
echo   - imagedescriber.exe
echo   - README.txt
echo   - LICENSE.txt
echo   - Setup and documentation files ^(if available^)
echo.
