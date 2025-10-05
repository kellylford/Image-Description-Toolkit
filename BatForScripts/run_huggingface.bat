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
