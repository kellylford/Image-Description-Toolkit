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
cd /d "%~dp0.."
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
