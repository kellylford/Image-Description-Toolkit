@echo off
REM ============================================================================
REM Image Description Workflow - HuggingFace Provider (Local AI)
REM ============================================================================
REM
REM Provider: HuggingFace Transformers (local, free)
REM Model: BLIP image captioning (runs on your computer)
REM Processing: Local - all on your computer, no cloud, no API key
REM
REM REQUIREMENTS:
REM   - Python 3.8+ with dependencies
REM   - transformers library: pip install transformers torch pillow
REM   - Internet connection (first run only, to download model)
REM
REM HOW IT WORKS:
REM   - Downloads model to your computer (first run only, ~1GB)
REM   - Processes images locally using transformers
REM   - No API keys, no cloud, completely private
REM
REM USAGE:
REM   1. Edit IMAGE_PATH below to your folder or image
REM   2. (Optional) Edit MODEL
REM   3. Run this batch file
REM   4. Find results in wf_huggingface_* directory
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to your images (folder or single image file)
set IMAGE_PATH=C:\path\to\your\images

REM HuggingFace model (local transformers model)
REM Options:
REM   - Salesforce/blip-image-captioning-base (recommended, fast)
REM   - Salesforce/blip-image-captioning-large (better quality, slower)
REM   - microsoft/git-base-coco (alternative)
set MODEL=Salesforce/blip-image-captioning-base

REM Description style
set PROMPT_STYLE=narrative

REM Workflow steps (full workflow for set-and-forget processing)
set STEPS=video,convert,describe,html

REM ======================================

echo ============================================================================
echo Image Description Workflow - HuggingFace Provider
echo ============================================================================
echo.
echo Configuration:
echo   Provider: huggingface (local transformers)
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Image/Folder: %IMAGE_PATH%
echo   Steps: %STEPS%
echo.
echo Complete Workflow:
echo   1. Extract video frames
echo   2. Convert HEIC images to JPG
echo   3. Generate AI descriptions (local transformers)
echo   4. Create HTML gallery
echo.
echo NOTE: First run will download model to your computer (~1GB)
echo       After that, runs completely offline
echo.

REM Validate
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
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

REM Check transformers
echo Checking transformers library...
python -c "import transformers" >nul 2>&1
if errorlevel 1 (
    echo ERROR: transformers library not installed
    echo.
    echo To install:
    echo   pip install transformers torch pillow
    echo.
    pause
    exit /b 1
)

echo transformers library found
echo.

REM Navigate to project root
cd /d "%~dp0.."

REM Check workflow.py
if not exist "workflow.py" (
    echo ERROR: workflow.py not found
    pause
    exit /b 1
)

REM Run workflow
echo Running HuggingFace workflow...
echo NOTE: First run will download model (~1GB)
echo.
python workflow.py "%IMAGE_PATH%" --provider huggingface --model %MODEL% --prompt-style %PROMPT_STYLE% --steps %STEPS%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed
    echo.
    echo Common issues:
    echo   - Model download failed (check internet connection)
    echo   - Insufficient disk space for model
    echo   - Missing Python packages (transformers, torch, pillow)
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed
echo ============================================================================
echo.
echo Results: wf_huggingface_*_%PROMPT_STYLE%_* directory
echo.
echo Output files:
echo   - descriptions.txt      - All descriptions
echo   - descriptions.html     - HTML gallery (open in browser)
echo   - workflow.log          - Processing log
echo   - temp_combined_images/ - All processed images
echo.
pause

REM ============================================================================REM ============================================================================

REM REM This batch file runs the image description workflow using HuggingFace (cloud AI)

REM This uses HuggingFace transformers library for LOCAL image captioning.REM 

REM NO API KEY NEEDED - models run on your computer using transformers.REM Provider: HuggingFace (cloud, free tier available)

REMREM Model: microsoft/Florence-2-large (Microsoft's Florence-2 via HF Inference API)

REM WHAT YOU NEED FIRST:REM Prompt: narrative (balanced detail and readability)

REM   1. Python packages: pip install transformers torch pillowREM

REM   2. First run will download model (~1-2GB depending on model)REM REQUIREMENTS:

REM   3. Decent RAM (8GB+ recommended)REM   - Python 3.8+ with required packages

REMREM   - HuggingFace API token (free from huggingface.co)

REM HOW IT WORKS:REM   - Internet connection

REM   - Uses BLIP, GIT, or ViT models from HuggingFaceREM

REM   - Everything runs locally (no internet after first download)REM USAGE:

REM   - Models are cached for future useREM   1. Get HuggingFace token from https://huggingface.co/settings/tokens

REMREM   2. Create file with token OR set HUGGINGFACE_TOKEN environment variable

REM MODELS AVAILABLE:REM   3. Edit IMAGE_PATH and TOKEN_FILE below

REM   Salesforce/blip-image-captioning-base - Fast, good quality (1GB)REM   4. Run this batch file

REM   Salesforce/blip-image-captioning-large - Better quality, slower (2GB)REM   5. Find results in wf_huggingface_* directory

REM   microsoft/git-base-coco - Good general descriptions (1GB)REM ============================================================================

REM   nlpconnect/vit-gpt2-image-captioning - Fast, simple (500MB)

REMREM ============================================

REM NOTE: HuggingFace transformers does NOT support custom prompts.REM CONFIGURATION - EDIT THESE VALUES

REM       It generates captions based on how the model was trained.REM ============================================

REM

REM CUSTOMIZE BELOW: Change INPUT_DIR and MODELREM Path to image or folder (use absolute path without quotes)

REM ============================================================================REM Example: C:\Users\YourName\Pictures\photo.jpg

set IMAGE_PATH=C:\path\to\your\image.jpg

REM ======== EDIT THESE SETTINGS ========

REM Path to file containing HuggingFace API token (without quotes)

REM Where are your images? (folder or single image)REM OR leave empty to use HUGGINGFACE_TOKEN environment variable

set INPUT_DIR=C:\Users\kelly\Pictures\TestPhotosREM Example: C:\Users\YourName\huggingface_token.txt

set TOKEN_FILE=C:\path\to\huggingface_token.txt

REM Which HuggingFace model to use?

REM   Salesforce/blip-image-captioning-base - Recommended (fast, good)REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)

REM   Salesforce/blip-image-captioning-large - Best qualityset STEPS=describe

REM   microsoft/git-base-coco - Alternative option

set MODEL=Salesforce/blip-image-captioning-baseREM AI Provider (huggingface for cloud processing)

set PROVIDER=huggingface

REM ======================================

REM Model to use (microsoft/Florence-2-large recommended)

echo.set MODEL=microsoft/Florence-2-large

echo ========================================

echo Workflow: HuggingFace ProviderREM Prompt style (narrative, detailed, concise, artistic, technical, colorful)

echo ========================================set PROMPT_STYLE=narrative

echo Input: %INPUT_DIR%

echo Model: %MODEL%REM ============================================

echo ========================================REM VALIDATION AND EXECUTION

echo.REM ============================================

echo NOTE: HuggingFace models don't support custom prompts

echo       They generate captions based on model trainingecho ============================================================================

echo.echo Image Description Workflow - HuggingFace Provider

echo ============================================================================

REM Check if input existsecho.

if not exist "%INPUT_DIR%" (echo Configuration:

    echo ERROR: Input directory/file does not exist!echo   Provider: %PROVIDER%

    echo Please edit this .bat file and set INPUT_DIR to your images folderecho   Model: %MODEL%

    pauseecho   Prompt Style: %PROMPT_STYLE%

    exit /b 1echo   Steps: %STEPS%

)echo   Image/Folder: %IMAGE_PATH%

if defined TOKEN_FILE echo   Token File: %TOKEN_FILE%

REM Check if transformers is installedecho.

echo Checking HuggingFace transformers...

python -c "import transformers" >nul 2>&1REM Check if image path exists

if errorlevel 1 (if not exist "%IMAGE_PATH%" (

    echo ERROR: HuggingFace transformers not installed!    echo ERROR: Image path does not exist: %IMAGE_PATH%

    echo.    echo Please edit this batch file and set IMAGE_PATH to a valid path

    echo Please install: pip install transformers torch pillow    pause

    pause    exit /b 1

    exit /b 1)

)

REM Check if Python is available

REM Navigate to scripts directorypython --version >nul 2>&1

cd /d "%~dp0\..\scripts"if errorlevel 1 (

    echo ERROR: Python is not installed or not in PATH

REM Run workflow with HuggingFace provider    echo Please install Python 3.8 or higher

echo.    pause

echo Running workflow with HuggingFace provider...    exit /b 1

echo NOTE: First run will download model (~1-2GB))

echo       This may take several minutes

echo.REM Check for HuggingFace token

python workflow.py "%INPUT_DIR%" ^if defined TOKEN_FILE (

    --steps describe,html,viewer ^    if not exist "%TOKEN_FILE%" (

    --provider huggingface ^        echo ERROR: Token file does not exist: %TOKEN_FILE%

    --model %MODEL%        echo.

        echo To get a HuggingFace token:

if errorlevel 1 (        echo   1. Visit https://huggingface.co/settings/tokens

    echo.        echo   2. Create a new token (read access is sufficient)

    echo ERROR: Workflow failed!        echo   3. Save it to a file: %TOKEN_FILE%

    echo.        echo.

    echo Common issues:        echo OR set HUGGINGFACE_TOKEN environment variable

    echo   - Model download failed (check internet)        echo OR leave TOKEN_FILE empty to use environment variable

    echo   - Out of memory (try base model instead of large)        pause

    echo   - Missing torch: pip install torch        exit /b 1

    pause    )

    exit /b 1)

)

REM Navigate to project root

echo.cd /d "%~dp0"

echo ========================================echo Current directory: %CD%

echo SUCCESS! Workflow completeecho.

echo ========================================

echo.REM Check if workflow.py exists

echo Viewer should have opened automatically.if not exist "workflow.py" (

echo Output saved to: wf_huggingface_* folder    echo ERROR: workflow.py not found in current directory

echo.    echo Please run this batch file from the project root

echo Model is now cached - next run will be faster!    pause

echo.    exit /b 1

pause)


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
