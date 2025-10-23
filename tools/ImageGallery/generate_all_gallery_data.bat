@echo off
REM ============================================================================
REM Image Gallery Data Collection - Comprehensive Workflow Runner
REM ============================================================================
REM This script runs all workflows needed to populate the Image Gallery demo
REM with comprehensive data across multiple providers, models, and prompts.
REM
REM PREREQUISITES:
REM   1. Set up API keys:
REM      - Claude: Run setup_claude_key.bat or set ANTHROPIC_API_KEY
REM      - OpenAI: Run setup_openai_key.bat or set OPENAI_API_KEY
REM   2. Install Ollama models:
REM      - ollama pull qwen3-vl:235b-cloud
REM      - ollama pull llava:latest
REM      - ollama pull gemma3:latest
REM      - ollama pull moondream:latest
REM   3. Ensure Ollama service is running
REM
REM USAGE:
REM   generate_all_gallery_data.bat <image_directory>
REM
REM EXAMPLE:
REM   generate_all_gallery_data.bat c:\idt\images
REM
REM ============================================================================

setlocal enabledelayedexpansion

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
echo Image Gallery Data Collection
echo ============================================================================
echo.
echo Image Directory: %IMAGE_DIR%
echo Workflow Name: %WORKFLOW_NAME%
echo Output Directory: %OUTPUT_DIR%
echo.
echo This will run 27 workflows:
echo   - Claude models: 9 workflows (3 models x 3 prompts)
echo   - OpenAI models: 6 workflows (2 models x 3 prompts)
echo   - Ollama models: 12 workflows (4 models x 3 prompts)
echo.
echo Total descriptions: 675 (27 workflows x 25 images)
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
echo Starting workflow runs...
echo ============================================================================
echo.

set TOTAL_WORKFLOWS=27
set CURRENT=0

REM ============================================================================
REM CLAUDE MODELS (9 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo CLAUDE MODELS [1-9 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM Claude Haiku 3.5
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Haiku 3.5 + narrative
idt workflow "%IMAGE_DIR%" --provider claude --model claude-3-5-haiku-20241022 --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Haiku 3.5 + colorful
idt workflow "%IMAGE_DIR%" --provider claude --model claude-3-5-haiku-20241022 --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Haiku 3.5 + technical
idt workflow "%IMAGE_DIR%" --provider claude --model claude-3-5-haiku-20241022 --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Claude Opus 4
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Opus 4 + narrative
idt workflow "%IMAGE_DIR%" --provider claude --model claude-opus-4-20250514 --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Opus 4 + colorful
idt workflow "%IMAGE_DIR%" --provider claude --model claude-opus-4-20250514 --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Opus 4 + technical
idt workflow "%IMAGE_DIR%" --provider claude --model claude-opus-4-20250514 --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Claude Sonnet 4.5
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Sonnet 4.5 + narrative
idt workflow "%IMAGE_DIR%" --provider claude --model claude-sonnet-4-5-20250929 --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Sonnet 4.5 + colorful
idt workflow "%IMAGE_DIR%" --provider claude --model claude-sonnet-4-5-20250929 --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Claude Sonnet 4.5 + technical
idt workflow "%IMAGE_DIR%" --provider claude --model claude-sonnet-4-5-20250929 --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM OPENAI MODELS (6 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo OPENAI MODELS [10-15 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM GPT-4o-mini
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] GPT-4o-mini + narrative
idt workflow "%IMAGE_DIR%" --provider openai --model gpt-4o-mini --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] GPT-4o-mini + colorful
idt workflow "%IMAGE_DIR%" --provider openai --model gpt-4o-mini --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] GPT-4o-mini + technical
idt workflow "%IMAGE_DIR%" --provider openai --model gpt-4o-mini --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM GPT-4o
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] GPT-4o + narrative
idt workflow "%IMAGE_DIR%" --provider openai --model gpt-4o --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] GPT-4o + colorful
idt workflow "%IMAGE_DIR%" --provider openai --model gpt-4o --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] GPT-4o + technical
idt workflow "%IMAGE_DIR%" --provider openai --model gpt-4o --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM OLLAMA MODELS (12 workflows)
REM ============================================================================

echo.
echo ============================================================================
echo OLLAMA MODELS [16-27 of %TOTAL_WORKFLOWS%]
echo ============================================================================
echo.

REM Qwen3-VL (Cloud)
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Qwen3-VL Cloud + narrative
idt workflow "%IMAGE_DIR%" --provider ollama --model qwen3-vl:235b-cloud --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Qwen3-VL Cloud + colorful
idt workflow "%IMAGE_DIR%" --provider ollama --model qwen3-vl:235b-cloud --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Qwen3-VL Cloud + technical
idt workflow "%IMAGE_DIR%" --provider ollama --model qwen3-vl:235b-cloud --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Llava
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Llava + narrative
idt workflow "%IMAGE_DIR%" --provider ollama --model llava:latest --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Llava + colorful
idt workflow "%IMAGE_DIR%" --provider ollama --model llava:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Llava + technical
idt workflow "%IMAGE_DIR%" --provider ollama --model llava:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Gemma3
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Gemma3 + narrative
idt workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Gemma3 + colorful
idt workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Gemma3 + technical
idt workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM Moondream
set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Moondream + narrative
idt workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style narrative --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Moondream + colorful
idt workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style colorful --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

set /a CURRENT+=1
echo [%CURRENT%/%TOTAL_WORKFLOWS%] Moondream + technical
idt workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style technical --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 echo WARNING: Workflow failed, continuing...
echo.

REM ============================================================================
REM COMPLETION
REM ============================================================================

echo.
echo ============================================================================
echo All workflows complete!
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
echo   3. Deploy to web server:
echo      - Upload descriptions\ folder
echo      - Upload index.html
echo      - Upload image files
echo.
pause
