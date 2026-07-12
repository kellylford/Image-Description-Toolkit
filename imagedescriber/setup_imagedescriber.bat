@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo    ImageDescriber - User Setup Assistant
echo ================================================================
echo.
echo This script helps you set up optional AI providers for ImageDescriber.
echo.
echo What's included in ImageDescriber.exe:
echo   [x] Core application (image management, workspaces, HTML export)
echo   [x] Image loading (JPG, PNG, HEIC, BMP, GIF support)
echo   [x] Manual description editing
echo.
echo What this script can set up:
echo   [ ] Ollama (Local AI, Free, Recommended)
echo.
echo ================================================================
echo.

REM Check if we're in the right directory (where ImageDescriber.exe should be)
if exist "ImageDescriber*.exe" (
    echo Found ImageDescriber executable in current directory.
    echo.
) else (
    echo WARNING: ImageDescriber.exe not found in current directory.
    echo Please run this script from the same folder as ImageDescriber.exe
    echo.
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

:main_menu
cls
echo ================================================================
echo    ImageDescriber Setup - Main Menu
echo ================================================================
echo.
echo Choose what you'd like to set up:
echo.
echo [1] Check current setup status
echo [2] Set up Ollama (AI descriptions - RECOMMENDED)
echo [3] View setup guide
echo [4] Test all providers
echo [0] Exit
echo.
set /p choice="Enter your choice (0-4): "

if "%choice%"=="0" goto end
if "%choice%"=="1" goto check_status
if "%choice%"=="2" goto setup_ollama
if "%choice%"=="3" goto view_guide
if "%choice%"=="4" goto test_providers

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto main_menu

REM ================================================================
REM Check Status
REM ================================================================
:check_status
cls
echo ================================================================
echo    Current Setup Status
echo ================================================================
echo.

echo Checking ImageDescriber executable...
if exist "ImageDescriber*.exe" (
    echo [x] ImageDescriber.exe found
) else (
    echo [ ] ImageDescriber.exe NOT FOUND
)
echo.

echo Checking Ollama (for AI descriptions)...
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo [ ] Ollama NOT RUNNING
    echo     Status: Either not installed or not running
    echo     Setup: Choose option 2 from main menu
    set OLLAMA_AVAILABLE=0
) else (
    echo [x] Ollama is RUNNING

    REM Check for vision models
    echo     Checking for vision models...
    ollama list 2>nul | findstr /i "llava moondream bakllava" >nul 2>&1
    if errorlevel 1 (
        echo     [ ] No vision models found
        echo         Install: ollama pull llava:7b
        set OLLAMA_MODELS=0
    ) else (
        echo     [x] Vision models found
        set OLLAMA_MODELS=1
    )
    set OLLAMA_AVAILABLE=1
)
echo.

echo ================================================================
echo Summary
echo ================================================================
echo.

if "%OLLAMA_AVAILABLE%"=="1" (
    if "%OLLAMA_MODELS%"=="1" (
        echo Status: READY TO USE AI DESCRIPTIONS! ✓
        echo You can start using ImageDescriber with Ollama provider.
    ) else (
        echo Status: Ollama running but no vision models
        echo Action: Run "ollama pull llava:7b" to download a model
    )
) else (
    echo Status: AI descriptions NOT available
    echo Action: Set up Ollama ^(option 2^) to enable AI features
)
echo.

echo ================================================================
pause
goto main_menu

REM ================================================================
REM Setup Ollama
REM ================================================================
:setup_ollama
cls
echo ================================================================
echo    Ollama Setup
echo ================================================================
echo.
echo Ollama provides LOCAL, FREE AI image descriptions.
echo No internet required after setup. Completely private.
echo.
echo Download size: ~250MB installer + ~4GB model
echo Setup time: 5-10 minutes
echo.

curl -s http://localhost:11434/api/version >nul 2>&1
if not errorlevel 1 (
    echo [x] Ollama is already running!
    echo.
    echo Checking for vision models...
    ollama list | findstr /i "llava moondream bakllava" >nul 2>&1
    if not errorlevel 1 (
        echo [x] Vision models already installed!
        echo.
        echo You're all set! Ollama is ready to use in ImageDescriber.
        echo.
        pause
        goto main_menu
    ) else (
        echo [ ] No vision models found. Installing llava:7b...
        goto install_model
    )
)

echo Step 1: Download and Install Ollama
echo.
echo Opening Ollama download page in your browser...
echo Download from: https://ollama.ai/download/windows
echo.
echo After downloading:
echo   1. Run the Ollama installer
echo   2. Wait for installation to complete
echo   3. Ollama will start automatically
echo   4. Come back to this window
echo.
start https://ollama.ai/download/windows
echo.
echo Press any key AFTER you've installed Ollama...
pause >nul

echo.
echo Waiting for Ollama to start...
set RETRY=0
:wait_ollama
timeout /t 2 >nul
curl -s http://localhost:11434/api/version >nul 2>&1
if not errorlevel 1 (
    echo [x] Ollama is running!
    goto install_model
)
set /a RETRY+=1
if %RETRY% LSS 15 (
    echo Still waiting... ^(attempt %RETRY%/15^)
    goto wait_ollama
)

echo.
echo Ollama doesn't seem to be running yet.
echo Please make sure Ollama is installed and started, then try again.
echo.
pause
goto main_menu

:install_model
echo.
echo ================================================================
echo Step 2: Download Vision Model
echo ================================================================
echo.
echo Which model would you like to download?
echo.
echo [1] llava:7b (Recommended - Good balance, 4GB)
echo [2] moondream (Fastest - Smaller model, 2GB)
echo [3] llava:13b (Best quality - Larger model, 8GB)
echo [0] Skip this step
echo.
set /p model_choice="Enter your choice (0-3): "

if "%model_choice%"=="0" goto main_menu
if "%model_choice%"=="1" set MODEL=llava:7b
if "%model_choice%"=="2" set MODEL=moondream
if "%model_choice%"=="3" set MODEL=llava:13b

if not defined MODEL (
    echo Invalid choice. Defaulting to llava:7b
    set MODEL=llava:7b
)

echo.
echo Downloading model: %MODEL%
echo This will take 5-10 minutes depending on your internet speed...
echo.

ollama pull %MODEL%
if errorlevel 1 (
    echo.
    echo ERROR: Failed to download model
    echo Please check your internet connection and try again.
    echo.
    pause
    goto main_menu
)

echo.
echo ================================================================
echo SUCCESS! Ollama Setup Complete ✓
echo ================================================================
echo.
echo Model installed: %MODEL%
echo.
echo You can now use Ollama in ImageDescriber:
echo   1. Launch ImageDescriber.exe
echo   2. Create or open a workspace
echo   3. Click "Process Images"
echo   4. Select provider: "Ollama"
echo   5. Choose model: "%MODEL%"
echo   6. Process your images!
echo.
echo Enjoy AI-powered image descriptions!
echo.
pause
goto main_menu

REM ================================================================
REM View Guide
REM ================================================================
:view_guide
cls
echo Opening User Setup Guide...
echo.

if exist "dist_templates\USER_SETUP_GUIDE.md" (
    start notepad "dist_templates\USER_SETUP_GUIDE.md"
) else if exist "README.md" (
    start notepad README.md
) else (
    echo User guide not found in current directory.
    echo.
    echo Please see the documentation at:
    echo https://github.com/kellylford/Image-Description-Toolkit
    echo.
    pause
)

goto main_menu

REM ================================================================
REM Test Providers
REM ================================================================
:test_providers
cls
echo ================================================================
echo    Testing All Providers
echo ================================================================
echo.

echo This will test which AI providers are available and working.
echo.
pause

echo [1/2] Testing Ollama...
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo [ ] Ollama: NOT AVAILABLE
) else (
    ollama list 2>nul | findstr /i "llava moondream bakllava" >nul 2>&1
    if errorlevel 1 (
        echo [~] Ollama: Running but no vision models
    ) else (
        echo [x] Ollama: READY
    )
)
echo.

echo [2/2] Testing Copilot+ PC (NPU)...
REM Copilot+ detection is handled by ImageDescriber itself
echo [?] Copilot+ PC: Check ImageDescriber provider list
echo     (Requires Copilot+ PC hardware with NPU)
echo.

echo ================================================================
echo Test Complete
echo ================================================================
echo.
echo Summary:
echo   - Ollama: Best for most users (local, free, private)
echo   - Copilot+ PC: Fastest on compatible hardware
echo.
echo See dist_templates\USER_SETUP_GUIDE.md for detailed setup instructions.
echo.
pause
goto main_menu

REM ================================================================
REM End
REM ================================================================
:end
cls
echo ================================================================
echo    Thank you for using ImageDescriber!
echo ================================================================
echo.
echo Quick Reference:
echo   - Run this script anytime to check status or set up features
echo   - See dist_templates\USER_SETUP_GUIDE.md for detailed instructions
echo   - GitHub: github.com/kellylford/Image-Description-Toolkit
echo.
echo Happy describing!
echo.
pause
