@echo off
REM =========================================
REM ONNX Multi-Step Workflow Example
REM =========================================
REM
REM This batch file demonstrates using ONNX (Florence-2) as the FIRST STEP
REM in a multi-step workflow. ONNX generates initial descriptions which are
REM then enhanced by more advanced models.
REM
REM WORKFLOW STEPS:
REM 1. Extract video frames (if input is video) - OPTIONAL
REM 2. Convert images to standard format - OPTIONAL
REM 3. Generate descriptions with ONNX Florence-2 (FAST, LOCAL, FREE)
REM 4. Generate HTML report with descriptions
REM
REM WHY USE ONNX FIRST?
REM - Fast local processing (~1-2 seconds per image)
REM - No API costs or rate limits
REM - Good baseline descriptions using Florence-2
REM - Works offline after initial model download
REM - Can process hundreds of images quickly
REM
REM THEN ENHANCE WITH OTHER MODELS:
REM - Use Ollama for richer local descriptions
REM - Use OpenAI/Copilot for premium analysis
REM - Use GroundingDINO for object detection
REM
REM See docs\ONNX_GUIDE.md for more information
REM =========================================

REM ===== CONFIGURATION =====

REM Path to image, folder, or video file
REM Example: C:\Users\YourName\Pictures\photo.jpg
REM Example: C:\Users\YourName\Videos\vacation.mp4
REM Example: C:\Users\YourName\Pictures\vacation_photos
set INPUT_PATH=C:\path\to\your\images

REM Output directory (optional - defaults to input directory)
REM Leave empty to use input directory
set OUTPUT_DIR=

REM Workflow steps to execute (comma-separated, no spaces)
REM Available: video,convert,describe,html,viewer
REM
REM Common workflows:
REM   - Images only: describe,html
REM   - Video processing: video,describe,html
REM   - Full workflow: video,convert,describe,html,viewer
REM   - Just descriptions: describe
set WORKFLOW_STEPS=describe,html

REM ONNX Configuration
set PROVIDER=onnx
set MODEL=florence-2-large
set PROMPT_STYLE=narrative

REM ===== VALIDATION =====

echo.
echo =========================================
echo ONNX Multi-Step Workflow
echo =========================================
echo.

REM Check if input path is set
if "%INPUT_PATH%"=="C:\path\to\your\images" (
    echo ERROR: Please set INPUT_PATH to your actual image/video file or folder
    echo.
    echo Edit this batch file and update the INPUT_PATH variable.
    echo.
    pause
    exit /b 1
)

REM Check if input path exists
if not exist "%INPUT_PATH%" (
    echo ERROR: Input path does not exist: %INPUT_PATH%
    echo.
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later
    echo.
    pause
    exit /b 1
)

echo Configuration:
echo   Input: %INPUT_PATH%
if defined OUTPUT_DIR echo   Output: %OUTPUT_DIR%
echo   Steps: %WORKFLOW_STEPS%
echo   Provider: %PROVIDER%
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo.

REM Check if ONNX Runtime is installed
python -c "import onnxruntime" >nul 2>&1
if errorlevel 1 (
    echo WARNING: ONNX Runtime not installed
    echo.
    echo Installing ONNX Runtime...
    pip install onnxruntime
    if errorlevel 1 (
        echo ERROR: Failed to install ONNX Runtime
        echo Please run: pip install onnxruntime
        echo.
        pause
        exit /b 1
    )
    echo Installation complete!
    echo.
)

REM Check for first-time Florence-2 download
echo NOTE: Florence-2-large model will download on first use (~700MB)
echo This is a one-time download and will be cached locally.
echo.

REM ===== EXECUTION =====

echo Starting ONNX workflow...
echo.
echo STEP-BY-STEP PROCESS:
echo.

REM Build the command
set CMD=python scripts/workflow.py "%INPUT_PATH%"
if defined OUTPUT_DIR set CMD=%CMD% --output-dir "%OUTPUT_DIR%"
set CMD=%CMD% --steps %WORKFLOW_STEPS%
set CMD=%CMD% --provider %PROVIDER%
set CMD=%CMD% --model %MODEL%
set CMD=%CMD% --prompt-style %PROMPT_STYLE%

echo Running: %CMD%
echo.

REM Execute
%CMD%

if errorlevel 1 (
    echo.
    echo =========================================
    echo Workflow Failed
    echo =========================================
    echo.
    echo Common issues:
    echo   1. Missing dependencies - run: pip install onnxruntime pillow
    echo   2. Network issues during first-time model download
    echo   3. Invalid input path or unsupported file format
    echo.
    echo See docs\ONNX_GUIDE.md for troubleshooting.
    echo.
    pause
    exit /b 1
)

echo.
echo =========================================
echo Workflow Complete!
echo =========================================
echo.
echo ONNX has generated baseline descriptions.
echo.
echo NEXT STEPS - ENHANCE WITH OTHER MODELS:
echo.
echo 1. ENRICH WITH OLLAMA (Local, Free):
echo    - Run: run_ollama.bat
echo    - Uses same images, adds richer descriptions
echo    - Model: moondream (fast) or llava (detailed)
echo.
echo 2. ENHANCE WITH OPENAI GPT-4o (Premium Cloud):
echo    - Run: run_openai_gpt4o.bat
echo    - Adds professional-quality descriptions
echo    - Uses existing ONNX output as baseline
echo.
echo 3. ADD OBJECT DETECTION WITH GROUNDINGDINO:
echo    - Run: run_groundingdino.bat
echo    - Detects and locates specific objects
echo    - Complements ONNX descriptions
echo.
echo 4. VIEW RESULTS:
echo    - HTML report created in output directory
echo    - Open index.html in your browser
echo.

if defined OUTPUT_DIR (
    echo Output location: %OUTPUT_DIR%
) else (
    echo Output location: Same as input directory
)
echo.

pause
