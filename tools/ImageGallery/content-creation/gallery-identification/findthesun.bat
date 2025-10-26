@echo off
REM ============================================================================
REM Find The Sun - Sunshine Gallery Identification
REM ============================================================================
REM 
REM This script identifies sunshine-themed images from your QNAP descriptions
REM directory using the gallery content identification tool.
REM 
REM Usage: Double-click this file or run from command line
REM Output: findthesun_results.json with ranked sunshine image candidates
REM 
REM ============================================================================

echo.
echo ========================================
echo   Find The Sun - Gallery Identification
echo ========================================
echo.
echo Scanning QNAP descriptions for sunshine-themed images...
echo Directory: \\qnap\home\idt\descriptions
echo.

REM Check if the config file exists
if not exist "findthesun.json" (
    echo ERROR: Configuration file 'findthesun.json' not found!
    echo Please ensure you're running this from the gallery-identification directory.
    echo.
    pause
    exit /b 1
)

REM Check if the main script exists
if not exist "identify_gallery_content.py" (
    echo ERROR: Main script 'identify_gallery_content.py' not found!
    echo Please ensure you're running this from the gallery-identification directory.
    echo.
    pause
    exit /b 1
)

REM Run the gallery identification tool
echo Running gallery identification...
echo.
python identify_gallery_content.py --config findthesun.json --output findthesun_results.json

REM Check if the command was successful
if errorlevel 1 (
    echo.
    echo ERROR: Gallery identification failed!
    echo Check the error messages above for details.
    echo.
    echo Common issues:
    echo   - Python not installed or not in PATH
    echo   - QNAP directory not accessible (\\qnap\home\idt\descriptions)
    echo   - No workflow results found in the directory
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SUCCESS: Sunshine images identified!
echo ========================================
echo.
echo Results saved to: findthesun_results.json
echo.

REM Check if results file was created and show summary
if exist "findthesun_results.json" (
    echo Summary:
    echo   - Configuration used: findthesun.json
    echo   - Source directory: \\qnap\home\idt\descriptions
    echo   - Results file: findthesun_results.json
    echo.
    echo Next steps:
    echo   1. Open findthesun_results.json to review the candidates
    echo   2. Copy selected images to your gallery directory
    echo   3. Build your gallery using the existing ImageGallery tools
    echo.
) else (
    echo WARNING: Results file was not created.
    echo This might indicate no matching images were found.
    echo.
)

echo Press any key to view the results file...
pause >nul

REM Try to open the results file with the default JSON viewer
if exist "findthesun_results.json" (
    start notepad "findthesun_results.json"
)

echo.
echo Done! Check findthesun_results.json for your sunshine image candidates.
echo.
pause