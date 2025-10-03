@echo off
REM ============================================================================
REM Image Description Workflow - HuggingFace Provider
REM ============================================================================
REM This batch file runs the image description workflow using HuggingFace (cloud AI)
REM 
REM Provider: HuggingFace (cloud, free tier available)
REM Model: microsoft/Florence-2-large (Microsoft's Florence-2 via HF Inference API)
REM Prompt: narrative (balanced detail and readability)
REM
REM REQUIREMENTS:
REM   - Python 3.8+ with required packages
REM   - HuggingFace API token (free from huggingface.co)
REM   - Internet connection
REM
REM USAGE:
REM   1. Get HuggingFace token from https://huggingface.co/settings/tokens
REM   2. Create file with token OR set HUGGINGFACE_TOKEN environment variable
REM   3. Edit IMAGE_PATH and TOKEN_FILE below
REM   4. Run this batch file
REM   5. Find results in wf_huggingface_* directory
REM ============================================================================

REM ============================================
REM CONFIGURATION - EDIT THESE VALUES
REM ============================================

REM Path to image or folder (use absolute path without quotes)
REM Example: C:\Users\YourName\Pictures\photo.jpg
set IMAGE_PATH=C:\path\to\your\image.jpg

REM Path to file containing HuggingFace API token (without quotes)
REM OR leave empty to use HUGGINGFACE_TOKEN environment variable
REM Example: C:\Users\YourName\huggingface_token.txt
set TOKEN_FILE=C:\path\to\huggingface_token.txt

REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)
set STEPS=describe

REM AI Provider (huggingface for cloud processing)
set PROVIDER=huggingface

REM Model to use (microsoft/Florence-2-large recommended)
set MODEL=microsoft/Florence-2-large

REM Prompt style (narrative, detailed, concise, artistic, technical, colorful)
set PROMPT_STYLE=narrative

REM ============================================
REM VALIDATION AND EXECUTION
REM ============================================

echo ============================================================================
echo Image Description Workflow - HuggingFace Provider
echo ============================================================================
echo.
echo Configuration:
echo   Provider: %PROVIDER%
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Steps: %STEPS%
echo   Image/Folder: %IMAGE_PATH%
if defined TOKEN_FILE echo   Token File: %TOKEN_FILE%
echo.

REM Check if image path exists
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
    echo Please edit this batch file and set IMAGE_PATH to a valid path
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check for HuggingFace token
if defined TOKEN_FILE (
    if not exist "%TOKEN_FILE%" (
        echo ERROR: Token file does not exist: %TOKEN_FILE%
        echo.
        echo To get a HuggingFace token:
        echo   1. Visit https://huggingface.co/settings/tokens
        echo   2. Create a new token (read access is sufficient)
        echo   3. Save it to a file: %TOKEN_FILE%
        echo.
        echo OR set HUGGINGFACE_TOKEN environment variable
        echo OR leave TOKEN_FILE empty to use environment variable
        pause
        exit /b 1
    )
)

REM Navigate to project root
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if workflow.py exists
if not exist "workflow.py" (
    echo ERROR: workflow.py not found in current directory
    echo Please run this batch file from the project root
    pause
    exit /b 1
)

REM Build command with API key file if specified
if defined TOKEN_FILE (
    set COMMAND=python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%TOKEN_FILE%"
) else (
    set COMMAND=python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%
)

REM Run the workflow
echo Running workflow...
echo Command: %COMMAND%
echo.
echo NOTE: Using HuggingFace Inference API (cloud processing)
echo       Images are sent to HuggingFace servers for processing
echo.

%COMMAND%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed with error code %errorlevel%
    echo.
    echo Common issues:
    echo   - Invalid or expired HuggingFace token
    echo   - Rate limit exceeded (wait a few minutes)
    echo   - Model not available or loading
    echo   - Network connectivity issues
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed successfully
echo ============================================================================
echo.
echo Results saved to: wf_%PROVIDER%_*_%PROMPT_STYLE%_* directory
echo.
echo NOTE: Free tier has rate limits. If you hit limits, wait or upgrade.
echo.
pause
