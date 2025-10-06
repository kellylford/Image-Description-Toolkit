@echo off
REM ============================================================================
REM Image Description Workflow - OpenAI Provider (Cloud AI)
REM ============================================================================
REM
REM Provider: OpenAI (cloud, paid)
REM Model: gpt-4o-mini or gpt-4o
REM Processing: Cloud-based via OpenAI API
REM
REM REQUIREMENTS:
REM   - OpenAI API key from https://platform.openai.com/api-keys
REM   - API key saved to a text file (one line, just the key)
REM   - Internet connection
REM   - Python 3.8+ with dependencies
REM
REM Cost Estimate:
REM   - gpt-4o-mini: ~$0.003 per image
REM   - gpt-4o: ~$0.01 per image
REM
REM USAGE:
REM   1. Get API key, save to file
REM   2. Edit IMAGE_PATH and API_KEY_FILE below
REM   3. Run this batch file
REM   4. Find results in wf_openai_* directory
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to your images
set IMAGE_PATH=C:\path\to\your\images

REM Path to file containing your OpenAI API key
REM File should contain only the key, one line
set API_KEY_FILE=C:\path\to\openai_key.txt

REM OpenAI model (gpt-4o-mini cheaper, gpt-4o better)
set MODEL=gpt-4o-mini

REM Description style
set PROMPT_STYLE=narrative

REM Workflow steps (full workflow for set-and-forget processing)
set STEPS=video,convert,describe,html

REM ======================================

echo ============================================================================
echo Image Description Workflow - OpenAI Provider
echo ============================================================================
echo.
echo Configuration:
echo   Provider: openai
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Image/Folder: %IMAGE_PATH%
echo   Steps: %STEPS%
echo   API Key File: %API_KEY_FILE%
echo.
echo Complete Workflow:
echo   1. Extract video frames
echo   2. Convert HEIC images to JPG
echo   3. Generate AI descriptions (via OpenAI API)
echo   4. Create HTML gallery
echo.
echo WARNING: This will use your OpenAI API credits!
echo.
pause

REM Validate
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
    pause
    exit /b 1
)

if not exist "%API_KEY_FILE%" (
    echo ERROR: API key file not found: %API_KEY_FILE%
    echo.
    echo To get an API key:
    echo   1. Visit https://platform.openai.com/api-keys
    echo   2. Create a new key
    echo   3. Save it to a text file (just the key, one line)
    echo   4. Update API_KEY_FILE in this batch file
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed
    pause
    exit /b 1
)

REM Navigate
cd /d "%~dp0.."
if not exist "workflow.py" (
    echo ERROR: workflow.py not found
    pause
    exit /b 1
)

REM Run
echo Running OpenAI workflow...
echo NOTE: Images will be sent to OpenAI servers
echo.
python workflow.py "%IMAGE_PATH%" --provider openai --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%API_KEY_FILE%" --steps %STEPS%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed
    echo.
    echo Common issues:
    echo   - Invalid or expired API key
    echo   - Insufficient API credits
    echo   - Network connection problem
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed
echo ============================================================================
echo.
echo Results: wf_openai_%MODEL%_%PROMPT_STYLE%_* directory
echo.
echo TIP: Check usage at platform.openai.com/usage
echo To view: python viewer/viewer.py [output_directory]
echo.
pause
