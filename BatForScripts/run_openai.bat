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
REM COST:
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
echo   API Key File: %API_KEY_FILE%
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
python workflow.py "%IMAGE_PATH%" --provider openai --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%API_KEY_FILE%"

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
REM Processing happens in the CLOUD - you need an API key and internet.
REM
REM WHAT YOU NEED FIRST:
REM   1. OpenAI API key from https://platform.openai.com/api-keys
REM   2. Save your API key to a text file (one line, just the key)
REM   3. Set API_KEY_FILE below to point to that file
REM
REM COST:
REM   - GPT-4o-mini: ~$0.003 per image (cheap)
REM   - GPT-4o: ~$0.01 per image (better quality)
REM
REM WHAT THIS DOES:
REM   - Sends images to OpenAI servers
REM   - Gets descriptions from GPT-4o vision model
REM   - Creates HTML gallery with descriptions
REM   - Opens viewer to browse results
REM
REM CUSTOMIZE BELOW: Set API_KEY_FILE, INPUT_DIR, MODEL, PROMPT_STYLE
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Where is your OpenAI API key file? (plain text file with just your key)
set API_KEY_FILE=C:\Users\kelly\Desktop\openai_key.txt

REM Where are your images? (folder or single image)
set INPUT_DIR=C:\Users\kelly\Pictures\TestPhotos

REM Which OpenAI model to use?
REM   gpt-4o-mini - Cheapest, good quality
REM   gpt-4o - Best quality, more expensive
set MODEL=gpt-4o-mini

REM What style of descriptions?
REM   narrative - Story-like, natural language
REM   detailed - Comprehensive, everything visible
REM   concise - Short, to the point
REM   technical - Camera settings, lighting, composition
set PROMPT_STYLE=narrative

REM ======================================

echo.
echo ========================================
echo Workflow: OpenAI Provider
echo ========================================
echo Input: %INPUT_DIR%
echo Model: %MODEL%
echo Style: %PROMPT_STYLE%
echo Key File: %API_KEY_FILE%
echo ========================================
echo.
echo WARNING: This will use your OpenAI API credits!
echo Press Ctrl+C to cancel, or
pause

REM Check if API key file exists
if not exist "%API_KEY_FILE%" (
    echo ERROR: API key file not found!
    echo.
    echo Please:
    echo   1. Get an API key from https://platform.openai.com/api-keys
    echo   2. Save it to a text file (just the key, one line)
    echo   3. Edit this .bat file and set API_KEY_FILE to that file
    pause
    exit /b 1
)

REM Check if input exists
if not exist "%INPUT_DIR%" (
    echo ERROR: Input directory/file does not exist!
    echo Please edit this .bat file and set INPUT_DIR to your images folder
    pause
    exit /b 1
)

REM Navigate to scripts directory
cd /d "%~dp0\..\scripts"

REM Run workflow with OpenAI provider
echo.
echo Running workflow with OpenAI provider...
echo NOTE: Images will be sent to OpenAI servers
echo.
python workflow.py "%INPUT_DIR%" ^
    --steps describe,html,viewer ^
    --provider openai ^
    --model %MODEL% ^
    --prompt-style %PROMPT_STYLE% ^
    --api-key-file "%API_KEY_FILE%"

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed!
    echo.
    echo Common issues:
    echo   - Invalid or expired API key
    echo   - Insufficient API credits
    echo   - Network connection problem
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Workflow complete
echo ========================================
echo.
echo Viewer should have opened automatically.
echo Output saved to: wf_openai_%MODEL%_%PROMPT_STYLE%_* folder
echo.
echo TIP: Check your OpenAI usage at platform.openai.com
echo.
pause
