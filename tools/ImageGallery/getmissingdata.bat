@echo off
REM ============================================================================
REM Image Gallery Data Collection - Missing Workflows Only
REM ============================================================================
REM This script runs only the workflows that are missing from the comprehensive
REM data collection, based on analysis of existing workflow directories.
REM
REM MISSING WORKFLOWS IDENTIFIED:
REM   - llava:latest + colorful
REM   - llava:latest + technical
REM   - gemma3:latest + narrative
REM   - gemma3:latest + colorful
REM   - gemma3:latest + technical
REM   - moondream:latest + narrative
REM   - moondream:latest + colorful
REM   - moondream:latest + technical
REM
REM PREREQUISITES:
REM   1. Ollama service must be running
REM   2. Required models must be installed:
REM      - ollama pull llava:latest
REM      - ollama pull gemma3:latest
REM      - ollama pull moondream:latest
REM
REM USAGE:
REM   getmissingdata.bat <image_directory>
REM
REM EXAMPLE:
REM   getmissingdata.bat c:\idt\images
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
echo Image Gallery Missing Data Collection
echo ============================================================================
echo.
echo Image Directory: %IMAGE_DIR%
echo Workflow Name: %WORKFLOW_NAME%
echo Output Directory: %OUTPUT_DIR%
echo.
echo This will run 8 missing workflows:
echo   - Llava models: 2 workflows (colorful, technical)
echo   - Gemma3 models: 3 workflows (narrative, colorful, technical)
echo   - Moondream models: 3 workflows (narrative, colorful, technical)
echo.
echo Total descriptions: 200 (8 workflows x 25 images)
echo.
echo COMPLETED ALREADY (will skip):
echo   - All Claude workflows (9/9)
echo   - All OpenAI workflows (6/6)
echo   - All Qwen3-VL workflows (3/3)
echo   - Llava narrative (1/3)
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
echo Starting missing workflow runs...
echo ============================================================================
echo.

set TOTAL_WORKFLOWS=8
set CURRENT=0

REM ============================================================================
REM LLAVA MISSING WORKFLOWS (2 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo LLAVA MISSING WORKFLOWS [1-2 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM Llava colorful (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Llava + colorful
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model llava:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Llava technical (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Llava + technical
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model llava:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM GEMMA3 MISSING WORKFLOWS (3 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo GEMMA3 MISSING WORKFLOWS [3-5 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM Gemma3 narrative (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Gemma3 + narrative
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Gemma3 colorful (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Gemma3 + colorful
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Gemma3 technical (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Gemma3 + technical
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM MOONDREAM MISSING WORKFLOWS (3 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo MOONDREAM MISSING WORKFLOWS [6-8 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM Moondream narrative (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Moondream + narrative
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Moondream colorful (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Moondream + colorful
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Moondream technical (missing)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Moondream + technical
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM COMPLETION
REM ============================================================================

echo.
echo ============================================================================
echo Missing workflows complete!
echo ============================================================================
echo.
echo Summary:
echo   - Started with: 19/27 workflows complete
echo   - Ran 8 missing workflows
echo   - Should now have: 27/27 workflows complete
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