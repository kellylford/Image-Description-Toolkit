@echo off
REM ============================================================================
REM Image Description Workflow - Ollama Provider (Local AI)
REM ============================================================================
REM
REM Provider: Ollama (local, free, private)
REM Model: llava (recommended vision model)
REM Processing: All on your computer, no cloud, no API key
REM
REM REQUIREMENTS:
REM   - Ollama installed from https://ollama.ai
REM   - llava model: ollama pull llava
REM   - Ollama running (check system tray)
REM   - Python 3.8+ with dependencies
REM
REM USAGE:
REM   1. Edit IMAGE_PATH below to point to your folder or image
REM   2. (Optional) Edit MODEL and PROMPT_STYLE
REM   3. Run this batch file
REM   4. Find results in wf_ollama_* directory
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to your images (folder or single image file)
REM Use absolute path without quotes
REM Example: C:\MyPhotos  or  C:\MyPhotos\photo.jpg
set IMAGE_PATH=C:\path\to\your\images

REM Ollama model to use (llava recommended, moondream for speed)
set MODEL=llava

REM Description style (narrative, detailed, concise, technical, accessibility)
set PROMPT_STYLE=narrative

REM Workflow steps (full workflow for set-and-forget processing)
set STEPS=video,convert,describe,html

REM ======================================

echo ============================================================================
echo Image Description Workflow - Ollama Provider
echo ============================================================================
echo.
echo Configuration:
  echo   Provider: ollama
  echo   Model: %MODEL%
  echo   Prompt Style: %PROMPT_STYLE%
  echo   Image/Folder: %IMAGE_PATH%
  echo   Steps: %STEPS%
echo.
echo Complete Workflow:
  echo   1. Extract video frames
  echo   2. Convert HEIC images to JPG
  echo   3. Generate AI descriptions
  echo   4. Create HTML gallery
echo.REM Validate image path
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
    echo Please edit this batch file and set IMAGE_PATH to a valid path
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check Ollama
echo Checking Ollama availability...
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama is not running or not installed
    echo Please install Ollama from https://ollama.ai
    echo Then run: ollama pull %MODEL%
    pause
    exit /b 1
)

REM Check model
ollama list | findstr /i "%MODEL%" >nul
if errorlevel 1 (
    echo WARNING: Model %MODEL% not found
    echo Installing %MODEL% model...
    ollama pull %MODEL%
    if errorlevel 1 (
        echo ERROR: Failed to install model
        pause
        exit /b 1
    )
)

REM Navigate to project root
cd /d "%~dp0.."
echo Current directory: %CD%
echo.

REM Check workflow.py exists
if not exist "workflow.py" (
    echo ERROR: workflow.py not found
    echo Please run this batch file from: BatForScripts folder
    pause
    exit /b 1
)

REM Run the workflow
echo Running workflow...
echo.
python workflow.py "%IMAGE_PATH%" --provider ollama --model %MODEL% --prompt-style %PROMPT_STYLE% --steps %STEPS%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed with error code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed
echo ============================================================================
echo.
echo Results saved to: wf_ollama_%MODEL%_%PROMPT_STYLE%_* directory
echo.
echo To view results:
echo   python viewer/viewer.py [output_directory]
echo.
pause
