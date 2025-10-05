@echo off
REM ============================================================================
REM Image Description Workflow - Claude Provider (Cloud AI)
REM ============================================================================
REM
REM Provider: Claude (Anthropic, cloud, paid)
REM Model: claude-3-5-sonnet-20241022 (recommended) or other Claude models
REM Processing: Cloud-based via Anthropic API
REM
REM REQUIREMENTS:
REM   - Anthropic API key from https://console.anthropic.com/
REM   - API key saved to a text file (one line, just the key)
REM   - Internet connection
REM   - Python 3.8+ with dependencies
REM
REM Available Models:
REM   - claude-sonnet-4-5-20250929 (Claude 4.5 - best for agents/coding)
REM   - claude-opus-4-1-20250805 (Claude 4.1 - specialized complex tasks)
REM   - claude-sonnet-4-20250514 (Claude 4 - high performance)
REM   - claude-3-7-sonnet-20250219 (Claude 3.7 - extended thinking)
REM   - claude-3-5-haiku-20241022 (Claude 3.5 Haiku - fastest)
REM   - claude-3-haiku-20240307 (Claude 3 Haiku - compact)
REM
REM Cost Estimate (per image):
REM   - Claude 3.5 Sonnet: ~$0.003-0.015
REM   - Claude 3.5 Haiku: ~$0.0008-0.004
REM   - Claude 3 Opus: ~$0.015-0.075
REM
REM USAGE:
REM   1. Get API key, save to file (or use ANTHROPIC_API_KEY env var)
REM   2. Edit IMAGE_PATH and API_KEY_FILE below
REM   3. Run this batch file
REM   4. Find results in wf_claude_* directory
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to your images
set IMAGE_PATH=C:\path\to\your\images

REM Path to file containing your Claude API key
REM File should contain only the key, one line
REM Default location: %USERPROFILE%\onedrive\claude.txt
set API_KEY_FILE=C:\users\%USERNAME%\onedrive\claude.txt

REM Claude model (Sonnet 4.5 recommended for best quality)
set MODEL=claude-sonnet-4-5-20250929

REM Description style
set PROMPT_STYLE=narrative

REM Workflow steps (full workflow for set-and-forget processing)
set STEPS=video,convert,describe,html

REM ======================================

echo ============================================================================
echo Image Description Workflow - Claude Provider
echo ============================================================================
echo.
echo Configuration:
echo   Provider: claude
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Image/Folder: %IMAGE_PATH%
echo   Steps: %STEPS%
echo   API Key File: %API_KEY_FILE%
echo.
echo Complete Workflow:
echo   1. Extract video frames
echo   2. Convert HEIC images to JPG
echo   3. Generate AI descriptions (via Claude API)
echo   4. Create HTML gallery
echo.
echo WARNING: This will use your Anthropic API credits!
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
    echo   1. Visit https://console.anthropic.com/
    echo   2. Create a new API key
    echo   3. Save it to a text file (just the key, one line)
    echo   4. Update API_KEY_FILE in this batch file
    echo.
    echo Alternative: Set ANTHROPIC_API_KEY environment variable
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
echo Running Claude workflow...
echo NOTE: Images will be sent to Anthropic servers
echo.
python workflow.py "%IMAGE_PATH%" --provider claude --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%API_KEY_FILE%" --steps %STEPS%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed
    echo.
    echo Common issues:
    echo   - Invalid or expired API key
    echo   - Insufficient API credits
    echo   - Network connection problem
    echo   - Model name incorrect (check available models)
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed
echo ============================================================================
echo.
echo Results: wf_claude_%MODEL%_%PROMPT_STYLE%_* directory
echo.
echo TIP: Check usage at console.anthropic.com
echo To view: python viewer/viewer.py [output_directory]
echo.
pause
