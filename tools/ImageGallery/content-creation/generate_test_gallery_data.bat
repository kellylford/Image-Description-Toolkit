@echo off
REM ============================================================================
REM Image Gallery Test Data Collection
REM ============================================================================
REM This is a smaller test version that runs just a few workflows to verify
REM everything is working before running the full 27-workflow collection.
REM
REM This runs 6 workflows (one model per provider, 2 prompts each):
REM   - Claude Haiku 3.5: narrative, colorful
REM   - OpenAI GPT-4o-mini: narrative, colorful
REM   - Ollama Qwen3-VL: narrative, colorful
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
echo Image Gallery Test Data Collection
echo ============================================================================
echo.
echo Image Directory: %IMAGE_DIR%
echo Workflow Name: %WORKFLOW_NAME%
echo Output Directory: %OUTPUT_DIR%
echo.
echo This will run 6 test workflows:
echo   - Claude Haiku 3.5: narrative, colorful
echo   - OpenAI GPT-4o-mini: narrative, colorful
echo   - Ollama Qwen3-VL Cloud: narrative, colorful
echo.
pause

if not exist "%IMAGE_DIR%" (
    echo ERROR: Image directory does not exist: %IMAGE_DIR%
    pause
    exit /b 1
)

echo.
echo Starting test workflows...
echo.

REM Claude Haiku 3.5
echo [1/6] Claude Haiku 3.5 + narrative
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider claude --model claude-3-5-haiku-20241022 --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
echo.

echo [2/6] Claude Haiku 3.5 + colorful
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider claude --model claude-3-5-haiku-20241022 --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
echo.

REM OpenAI GPT-4o-mini
echo [3/6] GPT-4o-mini + narrative
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider openai --model gpt-4o-mini --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
echo.

echo [4/6] GPT-4o-mini + colorful
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider openai --model gpt-4o-mini --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
echo.

REM Ollama Qwen3-VL
echo [5/6] Qwen3-VL Cloud + narrative
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model qwen3-vl:235b-cloud --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
echo.

echo [6/6] Qwen3-VL Cloud + colorful
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model qwen3-vl:235b-cloud --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
echo.

echo ============================================================================
echo Test complete!
echo ============================================================================
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
echo If everything looks good, run generate_all_gallery_data.bat for full data.
echo.
pause
