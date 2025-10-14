@echo off
REM ============================================================================
REM Install Image Description Toolkit - AMD64 Architecture
REM ============================================================================
REM This script extracts all IDT release packages and creates the proper
REM directory structure for a complete installation.
REM
REM Prerequisites:
REM   - All release packages in the same directory as this script:
REM     * ImageDescriptionToolkit_v*.zip (main toolkit)
REM     * viewer_v*_amd64.zip (viewer GUI)
REM     * prompt_editor_v*_amd64.zip (prompt editor GUI)
REM     * imagedescriber_v*_amd64.zip (image describer GUI)
REM   - PowerShell available (for unzipping)
REM
REM Output:
REM   - idt/ directory with complete toolkit installation
REM ============================================================================

echo.
echo ========================================================================
echo IMAGE DESCRIPTION TOOLKIT - INSTALLER (AMD64)
echo ========================================================================
echo.
echo This will install the complete Image Description Toolkit suite.
echo.

REM Set architecture
set ARCH=amd64

REM Check for required packages
echo Checking for required packages...
echo.

set MISSING_PACKAGES=0

REM Find the main IDT package (version may vary)
set IDT_PACKAGE=
for %%f in (ImageDescriptionToolkit_v*.zip) do set IDT_PACKAGE=%%f
if "%IDT_PACKAGE%"=="" (
    echo ERROR: Main IDT package not found ^(ImageDescriptionToolkit_v*.zip^)
    set /a MISSING_PACKAGES+=1
) else (
    echo Found: %IDT_PACKAGE%
)

REM Find the viewer package
set VIEWER_PACKAGE=
for %%f in (viewer_v*_%ARCH%.zip) do set VIEWER_PACKAGE=%%f
if "%VIEWER_PACKAGE%"=="" (
    echo ERROR: Viewer package not found ^(viewer_v*_%ARCH%.zip^)
    set /a MISSING_PACKAGES+=1
) else (
    echo Found: %VIEWER_PACKAGE%
)

REM Find the prompt editor package
set PROMPT_PACKAGE=
for %%f in (prompt_editor_v*_%ARCH%.zip) do set PROMPT_PACKAGE=%%f
if "%PROMPT_PACKAGE%"=="" (
    echo ERROR: Prompt Editor package not found ^(prompt_editor_v*_%ARCH%.zip^)
    set /a MISSING_PACKAGES+=1
) else (
    echo Found: %PROMPT_PACKAGE%
)

REM Find the imagedescriber package
set DESCRIBER_PACKAGE=
for %%f in (imagedescriber_v*_%ARCH%.zip) do set DESCRIBER_PACKAGE=%%f
if "%DESCRIBER_PACKAGE%"=="" (
    echo ERROR: ImageDescriber package not found ^(imagedescriber_v*_%ARCH%.zip^)
    set /a MISSING_PACKAGES+=1
) else (
    echo Found: %DESCRIBER_PACKAGE%
)

echo.

if %MISSING_PACKAGES% gtr 0 (
    echo ERROR: %MISSING_PACKAGES% package^(s^) missing!
    echo.
    echo Please ensure all release packages are in the same directory as this script.
    echo.
    pause
    exit /b 1
)

REM Check if idt directory already exists
if exist "idt" (
    echo.
    echo WARNING: idt directory already exists!
    echo.
    choice /C YN /M "Do you want to remove it and reinstall"
    if errorlevel 2 (
        echo Installation cancelled.
        exit /b 0
    )
    echo Removing existing installation...
    rmdir /s /q "idt"
    echo.
)

REM Create directory structure
echo Creating directory structure...
mkdir "idt"
mkdir "idt\Viewer"
mkdir "idt\ImageDescriber"
mkdir "idt\PromptEditor"
echo Done.
echo.

REM Extract main IDT package to root
echo [1/4] Installing main IDT toolkit...
powershell -Command "Expand-Archive -Path '%IDT_PACKAGE%' -DestinationPath 'idt' -Force"
if errorlevel 1 (
    echo ERROR: Failed to extract main IDT package
    pause
    exit /b 1
)
echo Done.
echo.

REM Extract Viewer package
echo [2/4] Installing Viewer...
powershell -Command "Expand-Archive -Path '%VIEWER_PACKAGE%' -DestinationPath 'idt\Viewer' -Force"
if errorlevel 1 (
    echo ERROR: Failed to extract Viewer package
    pause
    exit /b 1
)
echo Done.
echo.

REM Extract Prompt Editor package
echo [3/4] Installing Prompt Editor...
powershell -Command "Expand-Archive -Path '%PROMPT_PACKAGE%' -DestinationPath 'idt\PromptEditor' -Force"
if errorlevel 1 (
    echo ERROR: Failed to extract Prompt Editor package
    pause
    exit /b 1
)
echo Done.
echo.

REM Extract ImageDescriber package
echo [4/4] Installing ImageDescriber...
powershell -Command "Expand-Archive -Path '%DESCRIBER_PACKAGE%' -DestinationPath 'idt\ImageDescriber' -Force"
if errorlevel 1 (
    echo ERROR: Failed to extract ImageDescriber package
    pause
    exit /b 1
)
echo Done.
echo.

echo ========================================================================
echo INSTALLATION COMPLETE!
echo ========================================================================
echo.
echo Image Description Toolkit has been installed to: idt\
echo.
echo Directory structure:
echo   idt\                   - Main toolkit with idt.exe
echo   idt\Viewer\            - Viewer GUI application
echo   idt\ImageDescriber\    - ImageDescriber GUI application
echo   idt\PromptEditor\      - Prompt Editor GUI application
echo.
echo NEXT STEPS:
echo.
echo 1. Install Ollama from https://ollama.com
echo 2. Pull at least one vision model:
echo      ollama pull llava
echo.
echo 3. Run the interactive guide:
echo      cd idt
echo      idt guideme
echo.
echo 4. See idt\README.txt for more information
echo.
echo Optional: Add idt\ to your PATH for easy access to idt.exe
echo.
pause
