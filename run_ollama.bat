@echo off
REM ============================================================================
REM Image Description Workflow - Ollama Provider
REM ============================================================================
REM This batch file runs the image description workflow using Ollama (local AI)
REM 
REM Provider: Ollama (local, free)
REM Model: moondream (recommended for image description)
REM Prompt: narrative (balanced detail and readability)
REM
REM REQUIREMENTS:
REM   - Ollama installed and running
REM   - moondream model pulled: ollama pull moondream
REM   - Python 3.8+ with required packages
REM
REM USAGE:
REM   1. Edit IMAGE_PATH below to point to your image or folder
REM   2. Run this batch file
REM   3. Find results in wf_ollama_* directory
REM ============================================================================

REM ============================================
REM CONFIGURATION - EDIT THESE VALUES
REM ============================================

REM Path to image or folder (use absolute path without quotes)
REM Example: C:\Users\YourName\Pictures\photo.jpg
set IMAGE_PATH=C:\path\to\your\image.jpg

REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)
set STEPS=describe

REM AI Provider (ollama for local processing)
set PROVIDER=ollama

REM Model to use (moondream is fast and accurate for images)
set MODEL=moondream

REM Prompt style (narrative, detailed, concise, artistic, technical, colorful)
set PROMPT_STYLE=narrative

REM ============================================
REM VALIDATION AND EXECUTION
REM ============================================

echo ============================================================================
echo Image Description Workflow - Ollama Provider
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

REM Check if Ollama is running
echo Checking Ollama availability...
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama is not running or not installed
    echo Please install Ollama from https://ollama.ai
    echo Then run: ollama pull moondream
    pause
    exit /b 1
)

REM Check if moondream model is installed
ollama list | findstr /i "moondream" >nul
if errorlevel 1 (
    echo WARNING: moondream model not found
    echo Installing moondream model...
    ollama pull moondream
    if errorlevel 1 (
        echo ERROR: Failed to install moondream model
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

REM Run the workflow
echo Running workflow...
echo Command: python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%
echo.

python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed with error code %errorlevel%
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
