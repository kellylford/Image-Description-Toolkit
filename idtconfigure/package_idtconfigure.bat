@echo off
REM ============================================================================
REM Create Distribution Package for IDT Configure
REM ============================================================================
REM This script creates a distributable ZIP file with the IDTConfigure
REM executable and documentation.
REM
REM Prerequisites:
REM   - Built executable in dist/ folder (run build_idtconfigure.bat first)
REM
REM Output:
REM   - idtconfigure_releases/idtconfigure_v[VERSION].zip
REM ============================================================================

echo.
echo ========================================================================
echo Creating IDTConfigure Distribution Package
echo ========================================================================
echo.

REM Check if executable exists
if not exist "dist\idtconfigure.exe" (
    echo ERROR: Executable not found!
    echo.
    echo Expected: dist\idtconfigure.exe
    echo.
    echo Please run build_idtconfigure.bat first to create the executable.
    echo.
    exit /b 1
)

REM Get version from parent directory
set VERSION=unknown
if exist "..\VERSION" (
    set /p VERSION=<..\VERSION
)

REM Create releases directory
if not exist "idtconfigure_releases" mkdir idtconfigure_releases

REM Create temporary staging directory
set STAGE_DIR=idtconfigure_releases\staging
if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

echo [1/3] Copying executable...
copy "dist\idtconfigure.exe" "%STAGE_DIR%\idtconfigure.exe" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable
    exit /b 1
)

echo [2/3] Creating README...
REM Create a distribution README
(
echo IDT Configure - Configuration Manager v%VERSION%
echo.
echo STANDALONE CONFIGURATION MANAGER
echo.
echo IDT Configure is a graphical configuration manager for the Image Description
echo Toolkit. It provides an easy-to-use interface for adjusting all configuration
echo settings without manually editing JSON files.
echo.
echo USAGE:
echo.
echo 1. Double-click idtconfigure.exe to launch
echo.
echo 2. Select a category from the Settings menu:
echo    - AI Model Settings: temperature, tokens, and other parameters
echo    - Prompt Styles: Choose default description styles
echo    - Video Extraction: Configure frame extraction modes
echo    - Processing Options: Adjust memory, delays, and optimization
echo    - Workflow Settings: Enable/disable workflow steps
echo    - Output Format: Control output file contents
echo.
echo 3. Navigate settings with arrow keys
echo 4. Press "Change Setting" or Enter to edit values
echo 5. Use File -^> Save All ^(Ctrl+S^) to save changes
echo.
echo KEYBOARD SHORTCUTS:
echo - Ctrl+R : Reload configurations from disk
echo - Ctrl+S : Save all changes
echo - F1     : Help
echo - Alt+F  : File menu
echo - Alt+S  : Settings menu
echo.
echo REQUIREMENTS:
echo - Windows 10 or later
echo - No Python installation required
echo.
echo ACCESSIBILITY:
echo - Full keyboard navigation
echo - Screen reader compatible
echo - Menu-based interface
echo.
echo CONFIGURATION FILES:
echo IDT Configure manages these files in the scripts/ directory:
echo - image_describer_config.json
echo - video_frame_extractor_config.json
echo - workflow_config.json
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
set ZIP_NAME=idtconfigure_v%VERSION%.zip
set ZIP_PATH=idtconfigure_releases\%ZIP_NAME%

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
echo Location: idtconfigure_releases\
echo Version: %VERSION%
echo.
echo Contents:
echo   - idtconfigure.exe
echo   - README.txt
echo   - LICENSE.txt
echo.
echo Ready for distribution!
echo.
