@echo off
REM ============================================================================
REM Complete End-to-End Workflow (Video to Gallery)
REM ============================================================================
REM
REM This runs ALL workflow steps:
REM   1. Extract frames from videos
REM   2. Convert HEIC images to JPG
REM   3. Generate AI descriptions
REM   4. Create HTML gallery
REM
REM USE CASE:
REM   - Folder with videos and/or images
REM   - Want complete processing in one go
REM   - Get browseable HTML gallery
REM
REM REQUIREMENTS:
REM   - Ollama installed and running
REM   - Ollama model: ollama pull llava
REM   - Python 3.8+ with all dependencies
REM   - FFmpeg (for video processing)
REM
REM USAGE:
REM   1. Edit INPUT_PATH below to your folder
REM   2. Run this batch file
REM   3. Find complete results in wf_ollama_* directory
REM   4. Open descriptions.html in browser
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to folder with videos and/or images
set INPUT_PATH=C:\path\to\your\media\folder

REM Ollama model for descriptions
set MODEL=llava

REM Description style
set PROMPT_STYLE=narrative

REM ======================================

echo ============================================================================
echo Complete End-to-End Workflow
echo ============================================================================
echo.
echo Configuration:
echo   Provider: ollama
echo   Model: %MODEL%
echo   Prompt Style: %PROMPT_STYLE%
echo   Input Folder: %INPUT_PATH%
echo.
echo This will run ALL workflow steps:
echo   1. Extract video frames
echo   2. Convert HEIC images to JPG
echo   3. Generate AI descriptions
echo   4. Create HTML gallery
echo.
echo This may take a while for lots of content!
echo.
pause

REM Validate
if not exist "%INPUT_PATH%" (
    echo ERROR: Input path does not exist: %INPUT_PATH%
    echo Please edit this batch file and set INPUT_PATH
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
echo Checking Ollama...
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama not running
    echo Please start Ollama and run: ollama pull %MODEL%
    pause
    exit /b 1
)

REM Check model
ollama list | findstr /i "%MODEL%" >nul
if errorlevel 1 (
    echo WARNING: Model %MODEL% not found, installing...
    ollama pull %MODEL%
    if errorlevel 1 (
        echo ERROR: Failed to install model
        pause
        exit /b 1
    )
)

REM Navigate
cd /d "%~dp0..\.."
if not exist "workflow.py" (
    echo ERROR: workflow.py not found
    pause
    exit /b 1
)

REM Run complete workflow with all steps
echo.
echo Running complete workflow...
echo.
python workflow.py "%INPUT_PATH%" --provider ollama --model %MODEL% --prompt-style %PROMPT_STYLE%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================================
echo SUCCESS! Complete workflow finished
echo ============================================================================
echo.
echo Output directory: wf_ollama_%MODEL%_%PROMPT_STYLE%_*
echo.
echo What was created:
echo   - Extracted video frames (if videos found)
echo   - Converted images (if HEIC found)
echo   - AI descriptions for all images
echo   - descriptions.html (open in browser)
echo.
echo To view results:
echo   1. Open descriptions.html in your browser
echo   2. Or run: python viewer/viewer.py [output_directory]
echo.
pause

REM   1. Extract frames from videos
REM   2. Convert HEIC images to JPG
REM   3. Generate AI descriptions (using Ollama)
REM   4. Create HTML gallery
REM   5. Open viewer application
REM
REM USE CASE:
REM   - You have a folder with videos AND images
REM   - Want frame extraction + descriptions all in one go
REM   - Want a browseable HTML gallery of results
REM
REM WHAT YOU NEED:
REM   1. Ollama installed and running
REM   2. Vision model: ollama pull llava
REM   3. Python with all dependencies installed
REM
REM CUSTOMIZE BELOW: Set INPUT_DIR (can contain videos, images, or both)
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Where is your content? (folder with videos/images)
set INPUT_DIR=C:\Users\kelly\Videos\VacationFootage

REM Which Ollama model to use for descriptions?
set MODEL=llava

REM What style of descriptions?
set PROMPT_STYLE=narrative

REM ======================================

echo.
echo ========================================
echo Complete Workflow: Video to Gallery
echo ========================================
echo Input: %INPUT_DIR%
echo Model: %MODEL%
echo Style: %PROMPT_STYLE%
echo ========================================
echo.
echo This will:
echo   1. Extract video frames
echo   2. Convert HEIC images
echo   3. Generate AI descriptions
echo   4. Create HTML gallery
echo   5. Open viewer
echo.
echo This may take a while for lots of videos!
echo.
pause

REM Check if input exists
if not exist "%INPUT_DIR%" (
    echo ERROR: Input directory does not exist!
    echo Please edit this .bat file and set INPUT_DIR
    pause
    exit /b 1
)

REM Check if Ollama is running
echo Checking Ollama...
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama is not running!
    echo Please start Ollama or install from https://ollama.ai
    pause
    exit /b 1
)

REM Check if model exists
ollama list | findstr /i "%MODEL%" >nul
if errorlevel 1 (
    echo Model '%MODEL%' not found. Downloading...
    ollama pull %MODEL%
)

REM Navigate to scripts directory
cd /d "%~dp0\..\..\scripts"

REM Run COMPLETE workflow
echo.
echo Running complete workflow...
echo.
python workflow.py "%INPUT_DIR%" ^
    --steps video,convert,describe,html,viewer ^
    --provider ollama ^
    --model %MODEL% ^
    --prompt-style %PROMPT_STYLE%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Complete workflow finished
echo ========================================
echo.
echo Viewer should have opened automatically.
echo Check the output folder for:
echo   - Extracted frames
echo   - Converted images
echo   - Description files
echo   - HTML gallery
echo.
pause
