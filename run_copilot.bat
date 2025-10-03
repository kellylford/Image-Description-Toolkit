@echo off
REM ============================================================================
REM Image Description Workflow - GitHub Copilot Provider
REM ============================================================================
REM This batch file runs the image description workflow using GitHub Copilot (cloud AI)
REM 
REM Provider: Copilot (cloud, requires GitHub Copilot subscription)
REM Model: gpt-4o (OpenAI's GPT-4 Omni via GitHub Copilot)
REM Prompt: narrative (balanced detail and readability)
REM
REM REQUIREMENTS:
REM   - GitHub Copilot subscription (Individual, Business, or Enterprise)
REM   - GitHub CLI (gh) installed and authenticated
REM   - Python 3.8+ with required packages
REM   - Internet connection
REM
REM USAGE:
REM   1. Install GitHub CLI: https://cli.github.com/
REM   2. Authenticate: gh auth login
REM   3. Ensure Copilot subscription is active
REM   4. Edit IMAGE_PATH below
REM   5. Run this batch file
REM   6. Find results in wf_copilot_* directory
REM ============================================================================

REM ============================================
REM CONFIGURATION - EDIT THESE VALUES
REM ============================================

REM Path to image or folder (use absolute path without quotes)
REM Example: C:\Users\YourName\Pictures\photo.jpg
set IMAGE_PATH=C:\path\to\your\image.jpg

REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)
set STEPS=describe

REM AI Provider (copilot for GitHub Copilot)
set PROVIDER=copilot

REM Model to use (gpt-4o recommended, also: claude-3.5-sonnet, o1-preview, o1-mini)
set MODEL=gpt-4o

REM Prompt style (narrative, detailed, concise, artistic, technical, colorful)
set PROMPT_STYLE=narrative

REM ============================================
REM VALIDATION AND EXECUTION
REM ============================================

echo ============================================================================
echo Image Description Workflow - GitHub Copilot Provider
echo ============================================================================
echo.
echo Configuration:
echo   Provider: %PROVIDER%
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Steps: %STEPS%
echo   Image/Folder: %IMAGE_PATH%
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

REM Check if GitHub CLI is installed
gh --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: GitHub CLI (gh) is not installed
    echo.
    echo To install GitHub CLI:
    echo   1. Visit https://cli.github.com/
    echo   2. Download and install for your OS
    echo   3. Run: gh auth login
    echo   4. Ensure you have GitHub Copilot subscription
    pause
    exit /b 1
)

REM Check if authenticated
echo Checking GitHub authentication...
gh auth status >nul 2>&1
if errorlevel 1 (
    echo ERROR: Not authenticated with GitHub CLI
    echo Please run: gh auth login
    pause
    exit /b 1
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

REM Run the workflow
echo Running workflow...
echo Command: python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%
echo.
echo NOTE: Using GitHub Copilot (requires active subscription)
echo       Images are processed via GitHub Copilot API
echo.

python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed with error code %errorlevel%
    echo.
    echo Common issues:
    echo   - No active GitHub Copilot subscription
    echo   - GitHub CLI not authenticated (run: gh auth login)
    echo   - Network connectivity issues
    echo   - Rate limits exceeded
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed successfully
echo ============================================================================
echo.
echo Results saved to: wf_%PROVIDER%_%MODEL%_%PROMPT_STYLE%_* directory
echo.
pause
