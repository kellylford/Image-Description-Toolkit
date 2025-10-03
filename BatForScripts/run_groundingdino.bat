@echo off
REM =========================================
REM GroundingDINO Image Description
REM =========================================
REM
REM This batch file uses GroundingDINO for text-prompted zero-shot object detection.
REM Unlike traditional object detectors, GroundingDINO can detect ANY object you describe!
REM
REM FEATURES:
REM - Text-prompted detection (describe what you want to find)
REM - Zero-shot (no training needed for new objects)
REM - Precise bounding boxes with confidence scores
REM - Natural language queries ("red cars", "people wearing hats", etc.)
REM - ~700MB model download on first use (automatic, cached)
REM
REM USAGE:
REM 1. Set IMAGE_PATH to your image file or folder
REM 2. SET DETECTION_QUERY to describe what to detect (use " . " to separate items)
REM 3. Run this batch file
REM
REM REQUIREMENTS:
REM - Python with groundingdino-py, torch, torchvision installed
REM - ~700MB free space for model cache (one-time download)
REM
REM For setup instructions, see: docs\GROUNDINGDINO_GUIDE.md
REM =========================================

REM ===== CONFIGURATION =====

REM Path to image or folder (use absolute path without quotes)
REM Example: C:\Users\YourName\Pictures\photo.jpg
REM Example: C:\Users\YourName\Pictures\vacation_photos
set IMAGE_PATH=C:\path\to\your\image.jpg

REM Detection query - describe what objects to find (separate with " . ")
REM Examples:
REM   - Comprehensive: "objects . people . vehicles . furniture . animals . text"
REM   - Specific: "red cars . blue trucks . motorcycles"
REM   - Safety: "fire extinguisher . exit signs . safety equipment"
REM   - Custom: "people wearing helmets . safety vests"
set DETECTION_QUERY=objects . people . vehicles . furniture . animals . text

REM Confidence threshold (1-95, default 25)
REM Lower = more detections (may include false positives)
REM Higher = fewer detections (only very confident matches)
set CONFIDENCE=25

REM Provider and model (do not change for GroundingDINO)
set PROVIDER=groundingdino
set MODEL=comprehensive

REM Prompt style (not used for standalone GroundingDINO, but required parameter)
set PROMPT_STYLE=narrative

REM ===== VALIDATION =====

echo.
echo =========================================
echo GroundingDINO Object Detection
echo =========================================
echo.

REM Check if image path is set
if "%IMAGE_PATH%"=="C:\path\to\your\image.jpg" (
    echo ERROR: Please set IMAGE_PATH to your actual image file or folder
    echo.
    echo Edit this batch file and update the IMAGE_PATH variable.
    echo Example: set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg
    echo.
    pause
    exit /b 1
)

REM Check if image path exists
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
    echo.
    echo Please check the path and try again.
    echo.
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or later from https://www.python.org/
    echo.
    pause
    exit /b 1
)

echo Configuration:
echo   Image/Folder: %IMAGE_PATH%
echo   Detection Query: %DETECTION_QUERY%
echo   Confidence: %CONFIDENCE%%%
echo   Provider: %PROVIDER%
echo.

REM Check if groundingdino is installed
python -c "import groundingdino" >nul 2>&1
if errorlevel 1 (
    echo WARNING: GroundingDINO is not installed
    echo.
    echo Would you like to install it now? This will:
    echo   - Install groundingdino-py package
    echo   - Install PyTorch and torchvision
    echo   - Download ~700MB model on first use
    echo.
    set /p INSTALL="Install GroundingDINO? (y/n): "
    if /i "%INSTALL%"=="y" (
        echo.
        echo Installing GroundingDINO...
        pip install groundingdino-py torch torchvision
        if errorlevel 1 (
            echo.
            echo ERROR: Installation failed
            echo.
            echo Please see docs\GROUNDINGDINO_GUIDE.md for manual installation instructions.
            echo.
            pause
            exit /b 1
        )
        echo.
        echo Installation complete!
        echo.
    ) else (
        echo.
        echo Installation skipped. Please install GroundingDINO manually:
        echo   pip install groundingdino-py torch torchvision
        echo.
        echo See docs\GROUNDINGDINO_GUIDE.md for more information.
        echo.
        pause
        exit /b 1
    )
)

REM Check if model cache exists
set MODEL_CACHE=%USERPROFILE%\.cache\torch\hub\checkpoints\groundingdino_swint_ogc.pth
if not exist "%MODEL_CACHE%" (
    echo.
    echo NOTE: First-time model download required (~700MB)
    echo This is a one-time download and will be cached for future use.
    echo Download will start when the script runs...
    echo.
    timeout /t 3 >nul
)

REM ===== EXECUTION =====

echo.
echo Starting GroundingDINO detection...
echo.

REM Run the workflow with GroundingDINO
python scripts/workflow.py "%IMAGE_PATH%" --steps describe --provider %PROVIDER% --model "%MODEL%" --prompt-style %PROMPT_STYLE% --detection-query "%DETECTION_QUERY%" --confidence %CONFIDENCE%

REM Check result
if errorlevel 1 (
    echo.
    echo =========================================
    echo Detection Failed
    echo =========================================
    echo.
    echo Please check the error messages above.
    echo.
    echo Common issues:
    echo   1. Missing dependencies - run: pip install groundingdino-py torch torchvision
    echo   2. Out of memory - try reducing image size or using CPU mode
    echo   3. Invalid detection query - use " . " to separate items
    echo   4. Network issues during first-time model download
    echo.
    echo See docs\GROUNDINGDINO_GUIDE.md for troubleshooting help.
    echo.
    pause
    exit /b 1
)

echo.
echo =========================================
echo Detection Complete!
echo =========================================
echo.
echo Output files created in the workflow output directory.
echo Look for image_descriptions.txt with detected objects and locations.
echo.

REM If hybrid mode, mention descriptions
echo For richer descriptions, you can use hybrid mode:
echo   - Edit this batch file and set: set PROVIDER=groundingdino+ollama
echo   - Requires Ollama installed and running
echo   - Combines detection with natural language descriptions
echo.

pause
