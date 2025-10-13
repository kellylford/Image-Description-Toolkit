@echo off
REM ============================================================================
REM Create Distribution Package for Prompt Editor
REM ============================================================================
REM This script creates a distributable ZIP file with the prompt editor
REM executable and documentation.
REM
REM Prerequisites:
REM   - Built executable in dist/ folder (run build_prompt_editor.bat first)
REM
REM Output:
REM   - prompt_editor_releases/prompt_editor_v[VERSION]_[ARCH].zip
REM ============================================================================

echo.
echo ========================================================================
echo Creating Prompt Editor Distribution Package
echo ========================================================================
echo.

REM Detect architecture
for /f "tokens=*" %%i in ('python -c "import platform; print(platform.machine().lower())"') do set ARCH=%%i
if "%ARCH%"=="aarch64" set ARCH=arm64
if "%ARCH%"=="arm64" set ARCH=arm64
if "%ARCH%"=="amd64" set ARCH=amd64
if "%ARCH%"=="x86_64" set ARCH=amd64

REM Check if executable exists
if not exist "dist\prompt_editor_%ARCH%.exe" (
    echo ERROR: Executable not found!
    echo.
    echo Expected: dist\prompt_editor_%ARCH%.exe
    echo.
    echo Please run build_prompt_editor.bat first to create the executable.
    echo.
    exit /b 1
)

REM Get version from parent directory
set VERSION=unknown
if exist "..\VERSION" (
    set /p VERSION=<..\VERSION
)

REM Create releases directory
if not exist "prompt_editor_releases" mkdir prompt_editor_releases

REM Create temporary staging directory
set STAGE_DIR=prompt_editor_releases\staging
if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

echo [1/3] Copying executable...
copy "dist\prompt_editor_%ARCH%.exe" "%STAGE_DIR%\prompt_editor.exe" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable
    exit /b 1
)

echo [2/3] Creating README...
REM Create a distribution README
(
echo Prompt Editor v%VERSION%
echo Architecture: %ARCH%
echo.
echo STANDALONE PROMPT EDITOR APPLICATION
echo.
echo This is the standalone editor for managing image description prompts
echo used by the Image Description Toolkit ^(IDT^).
echo.
echo USAGE:
echo.
echo 1. Double-click prompt_editor.exe to launch
echo.
echo 2. The editor will load scripts/image_describer_config.json
echo.
echo 3. Edit, add, or delete prompt variations
echo.
echo 4. Configure AI providers ^(Ollama, OpenAI, Anthropic, etc.^)
echo.
echo 5. Save changes to update the configuration
echo.
echo FEATURES:
echo - Visual list of all available prompts
echo - Easy editing with character count
echo - Add/delete prompt styles
echo - Set default prompt and provider
echo - Multi-provider AI support
echo - API key configuration
echo - Save/Save As/Open functionality
echo - Backup and restore
echo - Screen reader accessible
echo.
echo REQUIREMENTS:
echo - Windows %ARCH%
echo - No additional dependencies required
echo.
echo NOTES:
echo - Changes affect the bundled configuration file
echo - Use "Save As" to create custom configurations
echo - Original config backed up automatically
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
set ZIP_NAME=prompt_editor_v%VERSION%_%ARCH%.zip
set ZIP_PATH=prompt_editor_releases\%ZIP_NAME%

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
echo Location: prompt_editor_releases\
echo Architecture: %ARCH%
echo Version: %VERSION%
echo.
echo Contents:
echo   - prompt_editor.exe
echo   - README.txt
echo   - LICENSE.txt
echo.
