@echo off
REM ============================================================================
REM Image Gallery Data Collection - Detailed Prompt Only
REM ============================================================================
REM This script runs all workflows with the "detailed" prompt style across
REM all providers and models in the test matrix.
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
REM      - ollama pull granite3.2-vision:latest
REM   3. Ensure Ollama service is running
REM
REM USAGE:
REM   get_detailed_data.bat <image_directory>
REM
REM EXAMPLE:
REM   get_detailed_data.bat c:\idt\images
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

set "IMAGE_DIR=%~1"
set "WORKFLOW_NAME=25imagetest"
set "OUTPUT_DIR=c:\idt\Descriptions"

echo ============================================================================
echo Starting Detailed Prompt Data Collection
echo ============================================================================
echo Image Directory: %IMAGE_DIR%
echo Workflow Name: %WORKFLOW_NAME%
echo Output Directory: %OUTPUT_DIR%
echo Prompt Style: detailed
echo.
echo This will run 9 workflows (3 providers x 3 models average x 1 prompt)
echo Expected runtime: 45-60 minutes
echo ============================================================================
echo.

REM ============================================================================
REM CLAUDE MODELS - DETAILED PROMPT
REM ============================================================================
echo.
echo [1/9] Claude Haiku 3.5 - Detailed
echo ============================================================================
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider claude --model claude-3-5-haiku-20241022 --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Claude Haiku 3.5 detailed workflow failed
    pause
)

echo.
echo [2/9] Claude Opus 4 - Detailed  
echo ============================================================================
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider claude --model claude-opus-4-20250514 --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Claude Opus 4 detailed workflow failed
    pause
)

echo.
echo [3/9] Claude Sonnet 4.5 - Detailed
echo ============================================================================
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider claude --model claude-sonnet-4-5-20250929 --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Claude Sonnet 4.5 detailed workflow failed
    pause
)

REM ============================================================================
REM OPENAI MODELS - DETAILED PROMPT
REM ============================================================================
echo.
echo [4/9] OpenAI GPT-4o-mini - Detailed
echo ============================================================================
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider openai --model gpt-4o-mini --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: OpenAI GPT-4o-mini detailed workflow failed
    pause
)

echo.
echo [5/9] OpenAI GPT-4o - Detailed
echo ============================================================================
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider openai --model gpt-4o --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: OpenAI GPT-4o detailed workflow failed
    pause
)

REM ============================================================================
REM OLLAMA MODELS - DETAILED PROMPT
REM ============================================================================
echo.
echo [6/9] Ollama Qwen3-VL Cloud - Detailed
echo ============================================================================
timeout /t 30 /nobreak >nul
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model qwen3-vl:235b-cloud --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Ollama Qwen3-VL detailed workflow failed
    pause
)

echo.
echo [7/9] Ollama Llava - Detailed
echo ============================================================================
timeout /t 30 /nobreak >nul
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model llava:latest --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Ollama Llava detailed workflow failed
    pause
)

echo.
echo [8/9] Ollama Gemma3 - Detailed
echo ============================================================================
timeout /t 30 /nobreak >nul
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model gemma3:latest --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Ollama Gemma3 detailed workflow failed
    pause
)

echo.
echo [9/10] Ollama Moondream - Detailed
echo ============================================================================
timeout /t 30 /nobreak >nul
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model moondream:latest --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Ollama Moondream detailed workflow failed
    pause
)

echo.
echo [10/10] Ollama Granite 3.2 Vision - Detailed
echo ============================================================================
timeout /t 30 /nobreak >nul
"%IDT_CMD%" workflow "%IMAGE_DIR%" --provider ollama --model granite3.2-vision:latest --prompt-style detailed --name %WORKFLOW_NAME% --output-dir %OUTPUT_DIR% --batch
if errorlevel 1 (
    echo ERROR: Ollama Granite detailed workflow failed
    pause
)

echo.
echo ============================================================================
echo Detailed Prompt Data Collection Complete!
echo ============================================================================
echo All 10 detailed prompt workflows have been executed.
echo.
echo Next steps:
echo 1. Run: python generate_descriptions.py --name %WORKFLOW_NAME%
echo 2. Copy jsondata/*.json to descriptions/ directory  
echo 3. Test the Image Gallery at http://localhost:8000
echo.
echo Workflow data saved to: %OUTPUT_DIR%
echo ============================================================================
pause