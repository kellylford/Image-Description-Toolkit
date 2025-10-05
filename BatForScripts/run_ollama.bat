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

REM ============================================================================REM ============================================================================

REM REM This batch file runs the image description workflow using Ollama (local AI)

REM This runs the END-TO-END workflow using Ollama for image descriptions.REM 

REM Ollama is a LOCAL AI server - all processing happens on YOUR computer.REM Provider: Ollama (local, free)

REMREM Model: moondream (recommended for image description)

REM WHAT YOU NEED FIRST:REM Prompt: narrative (balanced detail and readability)

REM   1. Install Ollama from https://ollama.aiREM

REM   2. Pull a vision model: ollama pull llavaREM REQUIREMENTS:

REM   3. Make sure Ollama is RUNNING (check system tray)REM   - Ollama installed and running

REMREM   - moondream model pulled: ollama pull moondream

REM WHAT THIS DOES:REM   - Python 3.8+ with required packages

REM   - Takes images from INPUT_DIRREM

REM   - Generates AI descriptions using OllamaREM USAGE:

REM   - Creates HTML gallery with descriptionsREM   1. Edit IMAGE_PATH below to point to your image or folder

REM   - Opens viewer to browse resultsREM   2. Run this batch file

REMREM   3. Find results in wf_ollama_* directory

REM CUSTOMIZE BELOW: Change INPUT_DIR, MODEL, and PROMPT_STYLEREM ============================================================================

REM ============================================================================

REM ============================================

REM ======== EDIT THESE SETTINGS ========REM CONFIGURATION - EDIT THESE VALUES

REM ============================================

REM Where are your images? (folder or single image)

set INPUT_DIR=C:\Users\kelly\Pictures\TestPhotosREM Path to image or folder (use absolute path without quotes)

REM Example: C:\Users\YourName\Pictures\photo.jpg

REM Which Ollama model to use? set IMAGE_PATH=C:\path\to\your\image.jpg

REM   llava - Most popular, good quality (4GB)

REM   llava:13b - Better quality, slower (8GB)REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)

REM   moondream - Fastest, smallest (2GB)set STEPS=describe

set MODEL=llava

REM AI Provider (ollama for local processing)

REM What style of descriptions?set PROVIDER=ollama

REM   narrative - Story-like, natural language

REM   detailed - Comprehensive, everything visibleREM Model to use (moondream is fast and accurate for images)

REM   concise - Short, to the pointset MODEL=moondream

REM   technical - Camera settings, lighting, composition

REM   accessibility - For screen readersREM Prompt style (narrative, detailed, concise, artistic, technical, colorful)

set PROMPT_STYLE=narrativeset PROMPT_STYLE=narrative



REM ======================================REM ============================================

REM VALIDATION AND EXECUTION

echo.REM ============================================

echo ========================================

echo Workflow: Ollama Providerecho ============================================================================

echo ========================================echo Image Description Workflow - Ollama Provider

echo Input: %INPUT_DIR%echo ============================================================================

echo Model: %MODEL%echo.

echo Style: %PROMPT_STYLE%echo Configuration:

echo ========================================echo   Provider: %PROVIDER%

echo.echo   Model: %MODEL%

echo   Prompt Style: %PROMPT_STYLE%

REM Check if input existsecho   Steps: %STEPS%

if not exist "%INPUT_DIR%" (echo   Image/Folder: %IMAGE_PATH%

    echo ERROR: Input directory/file does not exist!echo.

    echo Please edit this .bat file and set INPUT_DIR to your images folder

    pauseREM Check if image path exists

    exit /b 1if not exist "%IMAGE_PATH%" (

)    echo ERROR: Image path does not exist: %IMAGE_PATH%

    echo Please edit this batch file and set IMAGE_PATH to a valid path

REM Check if Ollama is running    pause

echo Checking Ollama...    exit /b 1

ollama list >nul 2>&1)

if errorlevel 1 (

    echo ERROR: Ollama is not running!REM Check if Python is available

    echo.python --version >nul 2>&1

    echo Please:if errorlevel 1 (

    echo   1. Start Ollama (should be in system tray)    echo ERROR: Python is not installed or not in PATH

    echo   2. Or install from https://ollama.ai    echo Please install Python 3.8 or higher

    pause    pause

    exit /b 1    exit /b 1

))



REM Check if model existsREM Check if Ollama is running

ollama list | findstr /i "%MODEL%" >nulecho Checking Ollama availability...

if errorlevel 1 (ollama list >nul 2>&1

    echo Model '%MODEL%' not found. Downloading...if errorlevel 1 (

    ollama pull %MODEL%    echo ERROR: Ollama is not running or not installed

    if errorlevel 1 (    echo Please install Ollama from https://ollama.ai

        echo ERROR: Failed to download model    echo Then run: ollama pull moondream

        pause    pause

        exit /b 1    exit /b 1

    ))

)

REM Check if moondream model is installed

REM Navigate to scripts directoryollama list | findstr /i "moondream" >nul

cd /d "%~dp0\..\scripts"if errorlevel 1 (

    echo WARNING: moondream model not found

REM Run workflow with describe, html, and viewer steps    echo Installing moondream model...

echo.    ollama pull moondream

echo Running workflow (this may take a while for many images)...    if errorlevel 1 (

echo.        echo ERROR: Failed to install moondream model

python workflow.py "%INPUT_DIR%" ^        pause

    --steps describe,html,viewer ^        exit /b 1

    --provider ollama ^    )

    --model %MODEL% ^)

    --prompt-style %PROMPT_STYLE%

REM Navigate to project root

if errorlevel 1 (cd /d "%~dp0"

    echo.echo Current directory: %CD%

    echo ERROR: Workflow failed!echo.

    pause

    exit /b 1REM Check if workflow.py exists

)if not exist "workflow.py" (

    echo ERROR: workflow.py not found in current directory

echo.    echo Please run this batch file from the project root

echo ========================================    pause

echo SUCCESS! Workflow complete    exit /b 1

echo ========================================)

echo.

echo Viewer should have opened automatically.REM Run the workflow

echo Output saved to: wf_ollama_%MODEL%_%PROMPT_STYLE%_* folderecho Running workflow...

echo.echo Command: python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%

pauseecho.


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
