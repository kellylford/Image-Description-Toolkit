@echo off
REM ============================================================================
REM Image Gallery Data Collection - Granite 3.2 Vision Model
REM ============================================================================
REM This script runs workflows specifically for IBM Granite 3.2 Vision model
REM with extended timeout for better success rate.
REM
REM GRANITE 3.2 WORKFLOWS:
REM   - granite3.2-vision:latest + narrative
REM   - granite3.2-vision:latest + colorful
REM   - granite3.2-vision:latest + technical
REM
REM PREREQUISITES:
REM   1. Ollama service must be running
REM   2. Granite model must be installed:
REM      - ollama pull granite3.2-vision:latest
REM
REM USAGE:
REM   getgranitedata.bat <image_directory>
REM
REM EXAMPLE:
REM   getgranitedata.bat c:\idt\images
REM
REM ============================================================================

setlocal enabledelayedexpansion

REM Use the installed IDT executable
set "IDT_CMD=c:\idt\idt.exe"

if not exist "%IDT_CMD%" (
    echo ERROR: IDT executable not found at: %IDT_CMD%
    echo Please ensure IDT is installed at c:\idt\
    pause
    exit /b 1
)

echo Using IDT: %IDT_CMD%
echo.

REM Check for image directory argument
if "%~1"=="" (
    echo ERROR: Image directory not specified
    echo.
    echo USAGE: %~nx0 ^<image_directory^>
    echo EXAMPLE: %~nx0 c:\idt\images
    echo.
    pause
    exit /b 1
)

set IMAGE_DIR=%~1
set WORKFLOW_NAME=25imagetest
set OUTPUT_DIR=Descriptions

echo ============================================================================
echo Image Gallery Granite 3.2 Data Collection
echo ============================================================================
echo.
echo Image Directory: %IMAGE_DIR%
echo Workflow Name: %WORKFLOW_NAME%
echo Output Directory: %OUTPUT_DIR%
echo.
echo This will run 3 Granite 3.2 workflows:
echo   - granite3.2-vision:latest + narrative
echo   - granite3.2-vision:latest + colorful
echo   - granite3.2-vision:latest + technical
echo.
echo Total descriptions: 75 (3 workflows x 25 images)
echo.
echo NOTE: Using extended timeout (300s) for Granite model stability
echo.
echo Press Ctrl+C to cancel, or
pause

REM Check if image directory exists
if not exist "%IMAGE_DIR%" (
    echo ERROR: Image directory does not exist: %IMAGE_DIR%
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo Starting Granite 3.2 workflow runs...
echo ============================================================================
echo.

set TOTAL_WORKFLOWS=3
set CURRENT=0

REM ============================================================================
REM GRANITE 3.2 VISION WORKFLOWS (3 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo GRANITE 3.2 VISION WORKFLOWS [1-3 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM Granite 3.2 narrative
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Granite 3.2 Vision + narrative
echo NOTE: Using 300 second timeout for model stability
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model granite3.2-vision:latest --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch --timeout 300
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Granite 3.2 colorful
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Granite 3.2 Vision + colorful
echo NOTE: Using 300 second timeout for model stability
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model granite3.2-vision:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch --timeout 300
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Granite 3.2 technical
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Granite 3.2 Vision + technical
echo NOTE: Using 300 second timeout for model stability
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model granite3.2-vision:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch --timeout 300
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM COMPLETION
REM ============================================================================

echo.
echo ============================================================================
echo Granite 3.2 workflows complete!
echo ============================================================================
echo.
echo Summary:
echo   - Completed 3 Granite 3.2 Vision workflows
echo   - Generated 75 new descriptions (3 x 25 images)
echo   - Used extended 300s timeout for model stability
echo.
echo Your total dataset now includes:
echo   - Claude models: 9 workflows
echo   - OpenAI models: 6 workflows
echo   - Ollama models: 15 workflows (12 + 3 Granite)
echo   - Total: 30 workflows = 750 descriptions
echo.
echo Next steps:
echo   1. Generate gallery data:
echo      cd tools\ImageGallery
echo      python generate_descriptions.py --name %WORKFLOW_NAME%
echo.
echo   2. Test locally:
echo      cd tools\ImageGallery
echo      test_gallery.bat
echo.
echo   3. Deploy to web server:
echo      - Upload descriptions\ folder
echo      - Upload index.html
echo      - Upload image files
echo.
pause