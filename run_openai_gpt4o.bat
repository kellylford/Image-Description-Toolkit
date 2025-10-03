@echo off
REM ============================================================================
REM OpenAI GPT-4o Image Description Workflow
REM ============================================================================
REM This batch file runs the workflow using OpenAI's GPT-4o model with
REM narrative prompt style for generating rich, story-like image descriptions.
REM
REM BEFORE USING:
REM 1. Replace <PATH_TO_YOUR_IMAGES> with your actual image directory path
REM 2. Replace <PATH_TO_API_KEY_FILE> with path to your OpenAI API key file
REM
REM Example API key file location: C:\Users\YourName\openai_key.txt
REM Example image path: C:\Users\YourName\Photos\2025\September
REM ============================================================================

setlocal

REM Configuration - EDIT THESE VALUES
set IMAGE_PATH=<path to images>
set API_KEY_FILE=<path to OpenAI key>

REM Model Configuration
set PROVIDER=openai
set MODEL=gpt-4o
set PROMPT_STYLE=narrative

REM Workflow Steps (video, convert, describe, html)
set STEPS=video,convert,describe,html

REM ============================================================================
REM Do not edit below this line unless you know what you're doing
REM ============================================================================

REM Check if paths are still placeholders
if "%IMAGE_PATH%"=="<PATH_TO_YOUR_IMAGES>" (
    echo ERROR: Please edit this batch file and set IMAGE_PATH to your actual image directory
    echo Example: set IMAGE_PATH=C:\Users\YourName\Photos\2025
    pause
    exit /b 1
)

if "%API_KEY_FILE%"=="<PATH_TO_API_KEY_FILE>" (
    echo ERROR: Please edit this batch file and set API_KEY_FILE to your OpenAI API key file
    echo Example: set API_KEY_FILE=C:\Users\YourName\openai_key.txt
    pause
    exit /b 1
)

REM Check if image directory exists
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image directory does not exist: %IMAGE_PATH%
    pause
    exit /b 1
)

REM Check if API key file exists
if not exist "%API_KEY_FILE%" (
    echo ERROR: API key file does not exist: %API_KEY_FILE%
    pause
    exit /b 1
)

REM Display configuration
echo ============================================================================
echo OpenAI GPT-4o Image Description Workflow
echo ============================================================================
echo.
echo Configuration:
echo   Provider:      %PROVIDER%
echo   Model:         %MODEL%
echo   Prompt Style:  %PROMPT_STYLE%
echo   Image Path:    %IMAGE_PATH%
echo   API Key File:  %API_KEY_FILE%
echo   Steps:         %STEPS%
echo.
echo ============================================================================
echo.

REM Navigate to project root directory (where this batch file is located)
cd /d "%~dp0"

REM Show current directory for debugging
echo Current directory: %CD%
echo.

REM Check if workflow.py exists
if not exist "workflow.py" (
    echo ERROR: workflow.py not found in current directory: %CD%
    echo.
    echo Looking for workflow.py...
    dir workflow.py /s /b
    echo.
    pause
    exit /b 2
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python or add it to your system PATH
    pause
    exit /b 2
)

echo Python version:
python --version
echo.

REM Run the workflow
echo Starting workflow...
echo Command: python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%API_KEY_FILE%"
echo.
python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%API_KEY_FILE%"

REM Check if workflow succeeded
if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo Workflow completed successfully!
    echo ============================================================================
    echo.
    echo Check the generated workflow directory for results:
    echo   - descriptions/image_descriptions.txt
    echo   - html_reports/image_descriptions.html
    echo.
) else (
    echo.
    echo ============================================================================
    echo Workflow failed with error code: %errorlevel%
    echo ============================================================================
    echo.
)

REM Return to original directory
cd /d "%~dp0"

pause
