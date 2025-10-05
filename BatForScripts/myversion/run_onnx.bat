@echo off
REM ============================================================================
REM Image Description Workflow - ONNX/Enhanced Ollama Provider
REM ============================================================================
REM
REM Provider: ONNX (local, free, optimized)
REM How it works: YOLO object detection + Ollama descriptions
REM Processing: Hardware-accelerated (NPU/GPU/CPU)
REM
REM REQUIREMENTS:
REM   - Python 3.8+ with dependencies
REM   - ultralytics package: pip install ultralytics
REM   - Ollama installed and running
REM   - Ollama model: ollama pull llava
REM
REM HOW IT WORKS:
REM   1. YOLO detects objects in image (fast, local)
REM   2. Passes object data + image to Ollama
REM   3. Ollama writes enhanced description
REM   Result: More accurate than Ollama alone
REM
REM USAGE:
REM   1. Edit IMAGE_PATH below
REM   2. Run this batch file
REM   3. Find results in wf_onnx_* directory
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to your images (folder or single image file)
set IMAGE_PATH=C:\path\to\your\images

REM Ollama model for descriptions
set MODEL=llava

REM Description style
set PROMPT_STYLE=narrative

REM Workflow steps (full workflow for set-and-forget processing)
set STEPS=video,convert,describe,html

REM ======================================

echo ============================================================================
echo Image Description Workflow - ONNX/Enhanced Ollama
echo ============================================================================
echo.
echo Configuration:
echo   Provider: onnx (YOLO + Ollama hybrid)
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Image/Folder: %IMAGE_PATH%
echo   Steps: %STEPS%
echo.
echo Complete Workflow:
echo   1. Extract video frames
echo   2. Convert HEIC images to JPG
echo   3. YOLO object detection + Ollama descriptions
echo   4. Create HTML gallery
echo.
echo NOTE: First run will download YOLO model (~50MB)
echo.

REM Validate
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
    echo Please edit this batch file and set IMAGE_PATH
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

REM Check Ollama
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama not running
    echo Please start Ollama and pull a model: ollama pull %MODEL%
    pause
    exit /b 1
)

REM Check ultralytics
python -c "import ultralytics" >nul 2>&1
if errorlevel 1 (
    echo WARNING: ultralytics not found, installing...
    pip install ultralytics
)

REM Navigate
cd /d "%~dp0..\.."
if not exist "workflow.py" (
    echo ERROR: workflow.py not found
    pause
    exit /b 1
)

REM Run
echo Running ONNX workflow...
echo.
python workflow.py "%IMAGE_PATH%" --provider onnx --model %MODEL% --prompt-style %PROMPT_STYLE% --steps %STEPS%

if errorlevel 1 (
    echo ERROR: Workflow failed
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed
echo ============================================================================
echo.
echo Results: wf_onnx_%MODEL%_%PROMPT_STYLE%_* directory
echo.
echo To view: python viewer/viewer.py [output_directory]
echo.
pause

REM ============================================================================REM ============================================================================

REM REM This batch file runs the image description workflow using ONNX (local AI)

REM This uses ONNX Runtime with YOLO object detection + Ollama descriptions.REM 

REM Combines FAST object detection with LLM-powered descriptions.REM Provider: ONNX (local, free, optimized)

REMREM Model: florence-2-large (Microsoft's Florence-2 vision model)

REM WHAT YOU NEED FIRST:REM Prompt: narrative (balanced detail and readability)

REM   1. Install Ollama from https://ollama.aiREM

REM   2. Pull a vision model: ollama pull llavaREM REQUIREMENTS:

REM   3. Python packages installed (pip install onnxruntime ultralytics)REM   - Python 3.8+ with required packages

REMREM   - ONNX Runtime installed (pip install onnxruntime)

REM HOW ONNX PROVIDER WORKS:REM   - Florence-2 model (auto-downloads on first use, ~700MB)

REM   - YOLO detects objects in image (super fast)REM

REM   - Passes detected objects + image to OllamaREM USAGE:

REM   - Ollama writes description based on what YOLO foundREM   1. Edit IMAGE_PATH below to point to your image or folder

REM   - Result: More accurate, detailed descriptionsREM   2. Run this batch file

REMREM   3. Find results in wf_onnx_* directory

REM HARDWARE ACCELERATION:REM

REM   - DirectML (Windows) - Uses your GPU/NPU automaticallyREM NOTE: First run will download the Florence-2 model (~700MB)

REM   - CUDA (NVIDIA) - Faster if you have NVIDIA GPUREM ============================================================================

REM   - CPU fallback - Works on any computer

REMREM ============================================

REM CUSTOMIZE BELOW: Change INPUT_DIR, MODEL, and PROMPT_STYLEREM CONFIGURATION - EDIT THESE VALUES

REM ============================================================================REM ============================================



REM ======== EDIT THESE SETTINGS ========REM Path to image or folder (use absolute path without quotes)

REM Example: C:\Users\YourName\Pictures\photo.jpg

REM Where are your images? (folder or single image)set IMAGE_PATH=C:\path\to\your\image.jpg

set INPUT_DIR=C:\Users\kelly\Pictures\TestPhotos

REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)

REM Which Ollama model to use for descriptions? set STEPS=describe

REM   llava - Most popular, good quality (4GB)

REM   llava:13b - Better quality, slower (8GB)REM AI Provider (onnx for local optimized processing)

REM   moondream - Fastest, smallest (2GB)set PROVIDER=onnx

set MODEL=llava

REM Model to use (florence-2-large for best quality, florence-2-base for faster)

REM What style of descriptions?set MODEL=florence-2-large

REM   narrative - Story-like, natural language

REM   detailed - Comprehensive, everything visibleREM Prompt style (narrative, detailed, concise, artistic, technical, colorful)

REM   concise - Short, to the pointset PROMPT_STYLE=narrative

REM   technical - Camera settings, lighting, composition

set PROMPT_STYLE=narrativeREM ============================================

REM VALIDATION AND EXECUTION

REM ======================================REM ============================================



echo.echo ============================================================================

echo ========================================echo Image Description Workflow - ONNX Provider

echo Workflow: ONNX Providerecho ============================================================================

echo (YOLO Detection + Ollama Descriptions)echo.

echo ========================================echo Configuration:

echo Input: %INPUT_DIR%echo   Provider: %PROVIDER%

echo Model: %MODEL%echo   Model: %MODEL%

echo Style: %PROMPT_STYLE%echo   Prompt Style: %PROMPT_STYLE%

echo ========================================echo   Steps: %STEPS%

echo.echo   Image/Folder: %IMAGE_PATH%

echo.

REM Check if input exists

if not exist "%INPUT_DIR%" (REM Check if image path exists

    echo ERROR: Input directory/file does not exist!if not exist "%IMAGE_PATH%" (

    echo Please edit this .bat file and set INPUT_DIR to your images folder    echo ERROR: Image path does not exist: %IMAGE_PATH%

    pause    echo Please edit this batch file and set IMAGE_PATH to a valid path

    exit /b 1    pause

)    exit /b 1

)

REM Check if Ollama is running (ONNX provider uses Ollama for descriptions)

echo Checking Ollama...REM Check if Python is available

ollama list >nul 2>&1python --version >nul 2>&1

if errorlevel 1 (if errorlevel 1 (

    echo ERROR: Ollama is not running!    echo ERROR: Python is not installed or not in PATH

    echo ONNX provider uses Ollama for text descriptions.    echo Please install Python 3.8 or higher

    echo.    pause

    echo Please:    exit /b 1

    echo   1. Start Ollama (should be in system tray))

    echo   2. Or install from https://ollama.ai

    pauseREM Check if onnxruntime is installed

    exit /b 1echo Checking ONNX Runtime availability...

)python -c "import onnxruntime" >nul 2>&1

if errorlevel 1 (

REM Check if model exists    echo WARNING: ONNX Runtime not found

ollama list | findstr /i "%MODEL%" >nul    echo Installing ONNX Runtime...

if errorlevel 1 (    pip install onnxruntime

    echo Model '%MODEL%' not found. Downloading...    if errorlevel 1 (

    ollama pull %MODEL%        echo ERROR: Failed to install ONNX Runtime

    if errorlevel 1 (        echo Please run manually: pip install onnxruntime

        echo ERROR: Failed to download model        pause

        pause        exit /b 1

        exit /b 1    )

    ))

)

REM Navigate to project root

REM Navigate to scripts directorycd /d "%~dp0"

cd /d "%~dp0\..\scripts"echo Current directory: %CD%

echo.

REM Run workflow with ONNX provider

echo.REM Check if workflow.py exists

echo Running workflow with ONNX provider...if not exist "workflow.py" (

echo NOTE: First run will download YOLO model (~50MB)    echo ERROR: workflow.py not found in current directory

echo.    echo Please run this batch file from the project root

python workflow.py "%INPUT_DIR%" ^    pause

    --steps describe,html,viewer ^    exit /b 1

    --provider onnx ^)

    --model %MODEL% ^

    --prompt-style %PROMPT_STYLE%REM Note about first-time download

echo NOTE: If this is your first time using ONNX provider:

if errorlevel 1 (echo   - Florence-2 model will be downloaded (~700MB)

    echo.echo   - This may take a few minutes depending on your internet speed

    echo ERROR: Workflow failed!echo   - Model is cached for future use

    pauseecho.

    exit /b 1

)REM Run the workflow

echo Running workflow...

echo.echo Command: python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%

echo ========================================echo.

echo SUCCESS! Workflow complete

echo ========================================python workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%

echo.

echo Viewer should have opened automatically.if errorlevel 1 (

echo Output saved to: wf_onnx_%MODEL%_%PROMPT_STYLE%_* folder    echo.

echo.    echo ERROR: Workflow failed with error code %errorlevel%

pause    pause

    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Workflow completed successfully
echo ============================================================================
echo.
echo Results saved to: wf_%PROVIDER%_%MODEL%_%PROMPT_STYLE%_* directory
echo.
echo TIP: Subsequent runs will be faster (model is now cached)
echo.
pause
