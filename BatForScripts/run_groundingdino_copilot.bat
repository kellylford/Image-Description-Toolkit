@echo off
REM ============================================================================
REM GroundingDINO Object Detection - Copilot+ PC NPU Performance Test
REM ============================================================================
REM
REM Provider: GroundingDINO (zero-shot object detection)
REM Processing: Local, on Copilot+ PC NPU (if available) or CPU
REM Cost: FREE
REM
REM PURPOSE:
REM   Run complete workflow with GroundingDINO on Copilot+ PC hardware
REM   Full pipeline: video extraction, HEIC conversion, detection, HTML gallery
REM   Uses only GroundingDINO - no secondary AI model
REM
REM WHAT IT DOES:
REM   - Extracts frames from videos
REM   - Converts HEIC images to JPG
REM   - Detects objects you specify in detection query
REM   - Creates HTML gallery with detection results
REM
REM USE CASES:
REM   - Complete workflow with GroundingDINO object detection
REM   - Process videos and images together
REM   - Create browseable HTML gallery
REM   - Test NPU detection performance on full dataset
REM
REM REQUIREMENTS:
REM   - GroundingDINO installed: pip install groundingdino-py torch torchvision
REM   - Python 3.8+ with dependencies
REM   - Copilot+ PC with NPU (recommended, will fallback to CPU)
REM
REM USAGE:
REM   1. Edit IMAGE_PATH below to your folder or image
REM   2. Edit DETECTION_QUERY to specify what to detect
REM   3. Run this batch file
REM   4. Find results in wf_groundingdino_* directory
REM ============================================================================

REM ======== EDIT THESE SETTINGS ========

REM Path to your images (folder or single image file)
REM Use absolute path without quotes
REM Example: C:\MyPhotos  or  C:\MyPhotos\photo.jpg
set IMAGE_PATH=<path to images>

REM Detection query - what objects to detect
REM Separate items with ' . ' (space-dot-space)
REM Examples:
REM   - "person . car . dog . cat"
REM   - "people . furniture . electronics"
REM   - "text . signs . labels . warnings"
REM   - "vehicles . traffic signs . pedestrians"
set DETECTION_QUERY=person . car . dog . cat . furniture. building . nature . sign

REM Confidence threshold (1-95)
REM Higher = fewer but more confident detections
REM Lower = more detections but may include false positives
REM Recommended: 30-50
set CONFIDENCE=15

REM ======================================

echo ============================================================================
echo GroundingDINO Object Detection - Copilot+ PC Performance Test
echo ============================================================================
echo.
echo Configuration:
echo   Provider: GroundingDINO (detection only, no AI model)
echo   Detection Query: %DETECTION_QUERY%
echo   Confidence Threshold: %CONFIDENCE%%%
echo   Image/Folder: %IMAGE_PATH%
echo.
echo Complete Workflow (automatic):
echo   1. Extract video frames (1 FPS default)
echo   2. Convert HEIC images to JPG
echo   3. Detect objects matching your query
echo   4. Create HTML gallery with detection results
echo   5. Test NPU performance (if Copilot+ PC hardware available)
echo.

REM Validate image path
if not exist "%IMAGE_PATH%" (
    echo ERROR: Image path does not exist: %IMAGE_PATH%
    echo Please edit this batch file and set IMAGE_PATH to a valid path
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check GroundingDINO
echo Checking GroundingDINO availability...
python -c "import groundingdino" >nul 2>&1
if errorlevel 1 (
    echo ERROR: GroundingDINO is not installed
    echo.
    echo To install GroundingDINO:
    echo   pip install groundingdino-py torch torchvision
    echo.
    echo Or use the ImageDescriber installer:
    echo   cd imagedescriber
    echo   install_groundingdino.bat
    pause
    exit /b 1
)

echo GroundingDINO is installed
echo.

REM Navigate to project root
cd /d "%~dp0.."

REM Check if we're on Copilot+ PC with NPU
echo Checking for NPU hardware...
python -c "import onnxruntime; providers = onnxruntime.get_available_providers(); print('DmlExecutionProvider' if 'DmlExecutionProvider' in providers else 'CPU')" 2>nul | findstr "DmlExecutionProvider" >nul
if errorlevel 1 (
    echo NOTE: No NPU/DirectML detected - will use CPU
    echo For NPU acceleration, install: pip install onnxruntime-directml
) else (
    echo NPU/DirectML detected - will use hardware acceleration
)
echo.

echo Starting GroundingDINO detection workflow...
echo.
echo Detection query: %DETECTION_QUERY%
echo Confidence threshold: %CONFIDENCE%%%
echo.

REM Run workflow with GroundingDINO provider
python workflow.py "%IMAGE_PATH%" --provider groundingdino --detection-query "%DETECTION_QUERY%" --confidence %CONFIDENCE%

if errorlevel 1 (
    echo.
    echo ============================================================================
    echo ERROR: Workflow failed
    echo ============================================================================
    echo Check the error message above for details.
    echo.
    echo Common issues:
    echo   1. GroundingDINO not installed correctly
    echo   2. Detection query syntax (use ' . ' to separate items)
    echo   3. Invalid confidence value (must be 1-95)
    echo   4. Missing required Python packages
    echo.
    echo For help, see: docs\GROUNDINGDINO_GUIDE.md
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo GroundingDINO Workflow Complete!
echo ============================================================================
echo.
echo Your results are in: wf_groundingdino_*
echo.
echo Output files:
echo   - descriptions.txt      - List of detected objects per image
echo   - descriptions.html     - HTML gallery (open in browser)
echo   - workflow.log          - Detailed processing log
echo   - temp_combined_images/ - All processed images
echo.
echo Performance notes:
echo   - Check workflow.log for processing times
echo   - Compare NPU vs CPU performance
echo   - Open descriptions.html in your browser
echo.
echo Next steps:
echo   - Try different detection queries
echo   - Adjust confidence threshold or FPS
echo   - Use hybrid mode: --provider groundingdino+ollama
echo     (Adds AI narration to detections)
echo.
echo See docs\GROUNDINGDINO_GUIDE.md for more options
echo.

pause
