@echo off
REM ============================================================================
REM Image Description Workflow - ONNX Provider
REM ============================================================================
REM This batch file runs the image description workflow using ONNX (local AI)
REM 
REM Provider: ONNX (local, free, optimized)
REM Model: florence-2-large (Microsoft's Florence-2 vision model)
REM Prompt: narrative (balanced detail and readability)
REM
REM REQUIREMENTS:
REM   - Python 3.8+ with required packages
REM   - ONNX Runtime installed (pip install onnxruntime)
REM   - Florence-2 model (auto-downloads on first use, ~700MB)
REM
REM USAGE:
REM   1. Edit IMAGE_PATH below to point to your image or folder
REM   2. Run this batch file
REM   3. Find results in wf_onnx_* directory
REM
REM NOTE: First run will download the Florence-2 model (~700MB)
REM ============================================================================

REM ============================================
REM CONFIGURATION - EDIT THESE VALUES
REM ============================================

REM Path to image or folder (use absolute path without quotes)
REM Example: C:\Users\YourName\Pictures\photo.jpg
set IMAGE_PATH=C:\path\to\your\image.jpg

REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)
set STEPS=describe

REM AI Provider (onnx for local optimized processing)
set PROVIDER=onnx

REM Model to use (florence-2-large for best quality, florence-2-base for faster)
set MODEL=florence-2-large

REM Prompt style (narrative, detailed, concise, artistic, technical, colorful)
set PROMPT_STYLE=narrative

REM ============================================
REM VALIDATION AND EXECUTION
REM ============================================

echo ============================================================================
echo Image Description Workflow - ONNX Provider
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

REM Check if onnxruntime is installed
echo Checking ONNX Runtime availability...
python -c "import onnxruntime" >nul 2>&1
if errorlevel 1 (
    echo WARNING: ONNX Runtime not found
    echo Installing ONNX Runtime...
    pip install onnxruntime
    if errorlevel 1 (
        echo ERROR: Failed to install ONNX Runtime
        echo Please run manually: pip install onnxruntime
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

REM Note about first-time download
echo NOTE: If this is your first time using ONNX provider:
echo   - Florence-2 model will be downloaded (~700MB)
echo   - This may take a few minutes depending on your internet speed
echo   - Model is cached for future use
echo.

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
echo TIP: Subsequent runs will be faster (model is now cached)
echo.
pause
