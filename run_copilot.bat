@echo off
REM ============================================================================
REM Image Description Workflow - Copilot+ PC Provider
REM ============================================================================
REM This batch file runs the image description workflow using Copilot+ PC NPU hardware
REM 
REM Provider: Copilot+ PC (local NPU hardware acceleration)
REM Model: florence2-base (Microsoft Florence-2 with DirectML)
REM Prompt: narrative (balanced detail and readability)
REM
REM REQUIREMENTS:
REM   - Copilot+ PC hardware with NPU chip:
REM     * Qualcomm Snapdragon X Elite/Plus
REM     * Intel Core Ultra (Series 2) with NPU
REM     * AMD Ryzen AI with NPU
REM   - Windows 11 (version 24H2 or later)
REM   - Python 3.8+ with required packages
REM   - DirectML support (onnxruntime-directml)
REM
REM USAGE:
REM   1. Ensure you have a Copilot+ PC with NPU hardware
REM   2. Install requirements: pip install onnxruntime-directml transformers torch
REM   3. Edit IMAGE_PATH below
REM   4. Run this batch file
REM   5. Find results in wf_copilot_* directory
REM
REM NOTE: This is for Copilot+ PC NPU hardware, NOT GitHub Copilot API
REM       For cloud AI, use run_openai_gpt4o.bat or run_ollama.bat instead
REM ============================================================================

REM ============================================
REM CONFIGURATION - EDIT THESE VALUES
REM ============================================

REM Path to image or folder (use absolute path without quotes)
REM Example: C:\Users\YourName\Pictures\photo.jpg
set IMAGE_PATH=C:\path\to\your\image.jpg

REM Steps to run (comma-separated: extract,describe,html,viewer or just describe)
set STEPS=describe

REM AI Provider (copilot for Copilot+ PC NPU hardware)
set PROVIDER=copilot

REM Model to use (florence2-base or florence2-large)
set MODEL=florence2-base

REM Prompt style (narrative, detailed, concise, artistic, technical, colorful)
set PROMPT_STYLE=narrative

REM ============================================
REM VALIDATION AND EXECUTION
REM ============================================

echo ============================================================================
echo Image Description Workflow - Copilot+ PC NPU Provider
echo ============================================================================
echo.
echo Configuration:
echo   Provider: %PROVIDER% (Copilot+ PC NPU Hardware)
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

REM Check if running on Windows 11
echo Checking Windows version...
ver | findstr /i "10.0.22" >nul
if errorlevel 1 (
    echo WARNING: Windows 11 (22H2 or later) recommended for NPU support
    echo Your version may not support Copilot+ PC NPU hardware acceleration
    echo.
)

REM Navigate to project root
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if scripts/workflow.py exists
if not exist "scripts\workflow.py" (
    echo ERROR: scripts\workflow.py not found
    echo Please run this batch file from the project root
    pause
    exit /b 1
)

REM Run the workflow
echo Running workflow...
echo Command: python scripts/workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%
echo.
echo NOTE: Using Copilot+ PC NPU hardware acceleration
echo       This requires a Copilot+ PC with NPU chip (Snapdragon/Intel/AMD)
echo       If NPU is not available, you'll get an error message
echo.

python scripts/workflow.py "%IMAGE_PATH%" --steps %STEPS% --provider %PROVIDER% --model %MODEL% --prompt-style %PROMPT_STYLE%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed with error code %errorlevel%
    echo.
    echo Common issues:
    echo   - You don't have a Copilot+ PC with NPU hardware
    echo   - DirectML is not installed (pip install onnxruntime-directml)
    echo   - Missing dependencies (pip install transformers torch)
    echo   - Florence-2 model not downloaded
    echo.
    echo If you don't have Copilot+ PC hardware, use these alternatives:
    echo   - run_onnx.bat (local CPU/GPU inference)
    echo   - run_ollama.bat (local Ollama models)
    echo   - run_openai_gpt4o.bat (cloud API)
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
