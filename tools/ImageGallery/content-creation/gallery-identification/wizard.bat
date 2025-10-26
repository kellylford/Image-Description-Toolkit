@echo off
REM ============================================================================
REM Gallery Content Identification Wizard
REM ============================================================================
REM 
REM Interactive wizard to help you create themed galleries from your IDT
REM workflow results using keyword matching and smart filtering.
REM 
REM ============================================================================

echo.
echo ========================================
echo   Gallery Content Identification Wizard
echo ========================================
echo.

REM Check if the wizard script exists
if not exist "gallery_wizard.py" (
    echo ERROR: Wizard script 'gallery_wizard.py' not found!
    echo Please ensure you're running this from the gallery-identification directory.
    echo.
    pause
    exit /b 1
)

REM Run the wizard
python gallery_wizard.py

REM Check if there was an error
if errorlevel 1 (
    echo.
    echo The wizard encountered an issue.
    echo.
    echo Common problems:
    echo   - Python not installed or not in PATH
    echo   - Script dependencies missing
    echo.
    pause
    exit /b 1
)

echo.
echo Thanks for using the Gallery Content Identification Wizard!
echo.
pause