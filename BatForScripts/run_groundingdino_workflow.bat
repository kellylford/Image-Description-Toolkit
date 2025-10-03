@echo off
REM =========================================
REM GroundingDINO Multi-Step Workflow Example
REM =========================================
REM
REM This batch file demonstrates using GroundingDINO as part of a multi-step
REM workflow for comprehensive image analysis.
REM
REM WORKFLOW PATTERN:
REM 1. GroundingDINO - Detect and locate specific objects
REM 2. Vision Model - Generate rich descriptions
REM 3. Combine outputs for comprehensive analysis
REM
REM TWO APPROACHES:
REM
REM APPROACH A: Sequential Processing
REM   Step 1: Run GroundingDINO detection
REM   Step 2: Run Ollama/GPT-4o for descriptions
REM   Step 3: Manually combine results
REM
REM APPROACH B: Hybrid Mode (Recommended)
REM   - Use "groundingdino+ollama" provider
REM   - Automatic integration of detection + description
REM   - Single workflow execution
REM
REM WHY USE GROUNDINGDINO IN WORKFLOWS?
REM - Precise object detection and localization
REM - Text-prompted (describe what to find)
REM - Complements vision models with structured data
REM - Free and runs locally
REM
REM See docs\GROUNDINGDINO_GUIDE.md for more information
REM =========================================

REM ===== CONFIGURATION =====

REM Choose workflow mode: SEQUENTIAL or HYBRID
REM SEQUENTIAL = Run detection first, then descriptions separately
REM HYBRID = Combined detection + descriptions in one run
set WORKFLOW_MODE=HYBRID

REM Path to image, folder, or video file
REM Example: C:\Users\YourName\Pictures\photo.jpg
REM Example: C:\Users\YourName\Pictures\safety_inspection
set INPUT_PATH=C:\path\to\your\images

REM Output directory (optional)
set OUTPUT_DIR=

REM Detection query - what objects to find
REM Examples:
REM   Safety: "fire extinguisher . exit signs . safety equipment . hazards"
REM   Vehicles: "cars . trucks . motorcycles . bicycles"
REM   General: "people . vehicles . furniture . electronics . text"
set DETECTION_QUERY=people . vehicles . objects . text . signs

REM Confidence threshold (1-95, default 25)
set CONFIDENCE=25

REM Workflow steps (comma-separated, no spaces)
REM Available: video,convert,describe,html,viewer
set WORKFLOW_STEPS=describe,html

REM Description model for HYBRID mode or Step 2 of SEQUENTIAL
REM Options: moondream, llava, gpt-4o, etc.
set DESCRIPTION_MODEL=moondream

REM ===== VALIDATION =====

echo.
echo =========================================
echo GroundingDINO Multi-Step Workflow
echo =========================================
echo Mode: %WORKFLOW_MODE%
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
    echo.
    pause
    exit /b 1
)

REM Check GroundingDINO installation
python -c "import groundingdino" >nul 2>&1
if errorlevel 1 (
    echo WARNING: GroundingDINO not installed
    echo.
    set /p INSTALL="Install GroundingDINO now? (y/n): "
    if /i "%INSTALL%"=="y" (
        echo Installing GroundingDINO...
        pip install groundingdino-py torch torchvision
        if errorlevel 1 (
            echo ERROR: Installation failed
            pause
            exit /b 1
        )
    ) else (
        echo Installation required. Exiting.
        pause
        exit /b 1
    )
)

echo Configuration:
echo   Input: %INPUT_PATH%
if defined OUTPUT_DIR echo   Output: %OUTPUT_DIR%
echo   Detection Query: %DETECTION_QUERY%
echo   Confidence: %CONFIDENCE%%%
echo   Steps: %WORKFLOW_STEPS%
echo.

REM ===== EXECUTION =====

if /i "%WORKFLOW_MODE%"=="HYBRID" goto HYBRID_MODE
if /i "%WORKFLOW_MODE%"=="SEQUENTIAL" goto SEQUENTIAL_MODE

echo ERROR: Invalid WORKFLOW_MODE. Use HYBRID or SEQUENTIAL
pause
exit /b 1

:HYBRID_MODE
echo =========================================
echo HYBRID MODE: Detection + Descriptions
echo =========================================
echo.
echo This mode combines GroundingDINO detection with Ollama descriptions
echo in a single workflow run for seamless integration.
echo.

REM Check Ollama if using hybrid mode
python -c "import ollama" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama not installed (required for hybrid mode)
    echo.
    echo Please install Ollama from: https://ollama.ai
    echo Then run: ollama pull %DESCRIPTION_MODEL%
    echo.
    echo Or switch to SEQUENTIAL mode to use GroundingDINO alone.
    echo.
    pause
    exit /b 1
)

REM Build hybrid command
set CMD=python scripts/workflow.py "%INPUT_PATH%"
if defined OUTPUT_DIR set CMD=%CMD% --output-dir "%OUTPUT_DIR%"
set CMD=%CMD% --steps %WORKFLOW_STEPS%
set CMD=%CMD% --provider groundingdino+ollama
set CMD=%CMD% --model %DESCRIPTION_MODEL%
set CMD=%CMD% --detection-query "%DETECTION_QUERY%"
set CMD=%CMD% --confidence %CONFIDENCE%

echo Running: %CMD%
echo.

%CMD%

if errorlevel 1 (
    echo.
    echo Workflow failed. See error messages above.
    pause
    exit /b 1
)

goto WORKFLOW_COMPLETE

:SEQUENTIAL_MODE
echo =========================================
echo SEQUENTIAL MODE: Two-Step Process
echo =========================================
echo.
echo STEP 1: GroundingDINO Object Detection
echo.

REM Step 1: Run GroundingDINO detection
set CMD1=python scripts/workflow.py "%INPUT_PATH%"
if defined OUTPUT_DIR set CMD1=%CMD1% --output-dir "%OUTPUT_DIR%"
set CMD1=%CMD1% --steps describe
set CMD1=%CMD1% --provider groundingdino
set CMD1=%CMD1% --detection-query "%DETECTION_QUERY%"
set CMD1=%CMD1% --confidence %CONFIDENCE%

echo Running: %CMD1%
echo.

%CMD1%

if errorlevel 1 (
    echo.
    echo Detection step failed. See error messages above.
    pause
    exit /b 1
)

echo.
echo =========================================
echo STEP 2: Generate Rich Descriptions
echo =========================================
echo.
echo Now running %DESCRIPTION_MODEL% to add detailed descriptions...
echo.

REM Determine provider for description model
set DESC_PROVIDER=ollama
if /i "%DESCRIPTION_MODEL%"=="gpt-4o" set DESC_PROVIDER=openai
if /i "%DESCRIPTION_MODEL%"=="gpt-4" set DESC_PROVIDER=openai

REM Step 2: Run description model
set CMD2=python scripts/workflow.py "%INPUT_PATH%"
if defined OUTPUT_DIR set CMD2=%CMD2% --output-dir "%OUTPUT_DIR%"
set CMD2=%CMD2% --steps describe,html
set CMD2=%CMD2% --provider %DESC_PROVIDER%
set CMD2=%CMD2% --model %DESCRIPTION_MODEL%
set CMD2=%CMD2% --prompt-style narrative

echo Running: %CMD2%
echo.

%CMD2%

if errorlevel 1 (
    echo.
    echo Description step failed. See error messages above.
    pause
    exit /b 1
)

goto WORKFLOW_COMPLETE

:WORKFLOW_COMPLETE
echo.
echo =========================================
echo Workflow Complete!
echo =========================================
echo.
echo RESULTS:
echo.
echo 1. DETECTION DATA:
echo    - Object locations and bounding boxes
echo    - Confidence scores for each detection
echo    - Structured detection data in .txt files
echo.

if /i "%WORKFLOW_MODE%"=="HYBRID" (
    echo 2. INTEGRATED DESCRIPTIONS:
    echo    - Natural language descriptions
    echo    - Combined with detection results
    echo    - HTML report with visual overlays
) else (
    echo 2. SEPARATE OUTPUTS:
    echo    - Detection results from GroundingDINO
    echo    - Descriptions from %DESCRIPTION_MODEL%
    echo    - HTML report with both datasets
)

echo.
echo 3. HTML REPORT:
echo    - Visual gallery with images
echo    - Detection overlays and descriptions
if defined OUTPUT_DIR (
    echo    - Location: %OUTPUT_DIR%\index.html
) else (
    echo    - Location: Same directory as input
)
echo.

echo NEXT STEPS:
echo.
echo - Open HTML report in browser to view results
echo - Review detection accuracy and descriptions
echo - Adjust detection query or confidence if needed
echo - Process more images with same settings
echo.

echo WORKFLOW VARIATIONS TO TRY:
echo.
echo 1. Different Detection Queries:
echo    - Safety: "fire extinguisher . exit signs . hazards"
echo    - Vehicles: "cars . trucks . motorcycles"
echo    - Damage: "cracks . dents . missing parts"
echo.
echo 2. Different Description Models:
echo    - moondream (fast, local)
echo    - llava (detailed, local)
echo    - gpt-4o (premium, cloud)
echo.
echo 3. Adjust Confidence:
echo    - Lower (15-20): More detections
echo    - Higher (35-45): Fewer, more confident
echo.

pause
