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
echo   [ ] YOLO Object Detection (Optional enhancement)
echo   [ ] ONNX Models (Optional performance boost)
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
echo [3] Set up YOLO Object Detection (Optional)
echo [4] Set up GroundingDINO (Text-prompted detection - Optional)
echo [5] Download ONNX Models (Optional performance boost)
echo [6] View setup guide
echo [7] Test all providers
echo [0] Exit
echo.
set /p choice="Enter your choice (0-7): "

if "%choice%"=="0" goto end
if "%choice%"=="1" goto check_status
if "%choice%"=="2" goto setup_ollama
if "%choice%"=="3" goto setup_yolo
if "%choice%"=="4" goto setup_grounding_dino
if "%choice%"=="5" goto setup_onnx
if "%choice%"=="6" goto view_guide
if "%choice%"=="7" goto test_providers

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

echo Checking Python (needed for optional features)...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ ] Python NOT FOUND (required for YOLO and ONNX setup)
    echo     Download from: https://python.org
    set PYTHON_AVAILABLE=0
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [x] Python !PYTHON_VERSION! found
    set PYTHON_AVAILABLE=1
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

if %PYTHON_AVAILABLE%==1 (
    echo Checking YOLO (for object detection)...
    python -c "from ultralytics import YOLO" >nul 2>&1
    if errorlevel 1 (
        echo [ ] YOLO NOT INSTALLED
        echo     Setup: Choose option 3 from main menu
        set YOLO_AVAILABLE=0
    ) else (
        echo [x] YOLO is installed
        echo     Provider: "Object Detection" will appear in ImageDescriber
        set YOLO_AVAILABLE=1
    )
    echo.
    
    echo Checking GroundingDINO (for text-prompted detection)...
    python -c "import groundingdino" >nul 2>&1
    if errorlevel 1 (
        echo [ ] GroundingDINO NOT INSTALLED
        echo     Setup: Choose option 4 from main menu
        set GROUNDING_DINO_AVAILABLE=0
    ) else (
        echo [x] GroundingDINO is installed
        echo     Provider: "GroundingDINO" will appear in ImageDescriber
        echo     Note: ~700MB model downloads automatically on first use
        set GROUNDING_DINO_AVAILABLE=1
    )
    echo.
    
    echo Checking ONNX Runtime (for enhanced performance)...
    python -c "import onnxruntime" >nul 2>&1
    if errorlevel 1 (
        echo [ ] ONNX Runtime NOT INSTALLED
        echo     Setup: Choose option 5 from main menu
        set ONNX_AVAILABLE=0
    ) else (
        echo [x] ONNX Runtime is installed
        
        REM Check for downloaded models
        if exist "onnx_models\florence2" (
            echo     [x] ONNX models downloaded
            set ONNX_MODELS=1
        ) else (
            echo     [ ] ONNX models not downloaded
            echo         Download: Choose option 5 from main menu
            set ONNX_MODELS=0
        )
        set ONNX_AVAILABLE=1
    )
    echo.
)

echo ================================================================
echo Summary
echo ================================================================
echo.

if %OLLAMA_AVAILABLE%==1 (
    if %OLLAMA_MODELS%==1 (
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

if %PYTHON_AVAILABLE%==1 (
    if %YOLO_AVAILABLE%==1 (
        echo Optional: Object Detection available ✓
    ) else (
        echo Optional: Install YOLO ^(option 3^) for object detection
    )
    
    if %ONNX_AVAILABLE%==1 (
        if %ONNX_MODELS%==1 (
            echo Optional: Enhanced ONNX available ✓
        ) else (
            echo Optional: Download ONNX models ^(option 4^) for performance boost
        )
    ) else (
        echo Optional: Install ONNX ^(option 4^) for enhanced features
    )
) else (
    echo Note: Install Python to enable optional features
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
REM Setup YOLO
REM ================================================================
:setup_yolo
cls
echo ================================================================
echo    YOLO Object Detection Setup
echo ================================================================
echo.
echo YOLO adds object detection to ImageDescriber.
echo Detects and counts: people, cars, animals, furniture, etc.
echo Recognizes 80 common object types.
echo.
echo Requirements: Python installed
echo Download size: ~50MB
echo Setup time: 2-3 minutes
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is required but not found.
    echo.
    echo Please install Python from: https://python.org
    echo Then run this setup script again.
    echo.
    pause
    goto main_menu
)

echo Python found. Installing YOLO...
echo.

pip install ultralytics
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install YOLO
    echo.
    echo Troubleshooting:
    echo   1. Check your internet connection
    echo   2. Try: pip install --upgrade pip
    echo   3. Try: pip install ultralytics --user
    echo.
    pause
    goto main_menu
)

echo.
echo ================================================================
echo SUCCESS! YOLO Installed ✓
echo ================================================================
echo.
echo Object Detection is now available in ImageDescriber!
echo.
echo Usage:
echo   1. Restart ImageDescriber (if it's running)
echo   2. Process Images → Provider: "Object Detection"
echo   3. Adjust settings: Confidence, Max Objects, Model Size
echo   4. Process your images!
echo.
echo Note: YOLO detects 80 common objects from the COCO dataset.
echo It won't recognize specialized objects like sculptures or artwork.
echo.
pause
goto main_menu

REM ================================================================
REM Setup GroundingDINO
REM ================================================================
:setup_grounding_dino
cls
echo ================================================================
echo    GroundingDINO Setup
echo ================================================================
echo.
echo GroundingDINO adds TEXT-PROMPTED object detection!
echo Detect ANY object by describing it in plain English.
echo.
echo Features:
echo   - Unlimited object types (not limited like YOLO)
echo   - Describe what to find: "red cars" "people wearing hats"
echo   - Works in chat: type "find safety equipment" and it detects!
echo   - Hybrid mode: Combines detection with Ollama descriptions
echo.
echo Requirements: Python + PyTorch
echo Download size: Dependencies ~100MB + Model ~700MB (on first use)
echo Setup time: 3-5 minutes (model downloads automatically on first use)
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is required but not found.
    echo.
    echo Please install Python from: https://python.org
    echo Then run this setup script again.
    echo.
    pause
    goto main_menu
)

echo Python found. Installing GroundingDINO...
echo.
echo Step 1/2: Installing PyTorch...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (
    echo.
    echo WARNING: PyTorch installation had issues.
    echo Continuing with GroundingDINO installation...
    echo.
)

echo.
echo Step 2/2: Installing GroundingDINO...
pip install groundingdino-py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install GroundingDINO
    echo.
    echo Troubleshooting:
    echo   1. Check your internet connection
    echo   2. Try: pip install --upgrade pip
    echo   3. Try: pip install groundingdino-py --user
    echo   4. Ensure you have Visual C++ Build Tools if on Windows
    echo.
    pause
    goto main_menu
)

echo.
echo ================================================================
echo SUCCESS! GroundingDINO Installed ✓
echo ================================================================
echo.
echo Text-prompted detection is now available in ImageDescriber!
echo.
echo NOTE: On first use, GroundingDINO will automatically download
echo a ~700MB model. This is normal and only happens once.
echo.
echo Usage:
echo   1. Restart ImageDescriber (if running)
echo   2. Process Images → Provider: "GroundingDINO" or "GroundingDINO + Ollama"
echo   3. Choose detection mode:
echo      - Automatic: Use presets (Comprehensive, Indoor, Outdoor, etc.)
echo      - Custom Query: Type what to find (e.g., "red cars . blue trucks")
echo   4. Adjust confidence threshold (default 25%%)
echo.
echo Chat Integration:
echo   - Select an image in workspace
echo   - In chat, type: "find red cars" or "detect safety equipment"
echo   - GroundingDINO will automatically detect and respond!
echo.
echo Example Queries:
echo   "red cars . blue trucks . motorcycles"
echo   "people wearing helmets . safety equipment"
echo   "fire exits . emergency signs"
echo   "damaged items . missing parts"
echo.
pause
goto main_menu

REM ================================================================
REM Setup ONNX
REM ================================================================
:setup_onnx
cls
echo ================================================================
echo    ONNX Models Setup
echo ================================================================
echo.
echo ONNX provides optimized AI models for faster performance.
echo Works with Enhanced ONNX provider (combines YOLO + Ollama).
echo.
echo Requirements: Python installed, Ollama installed, YOLO installed
echo Download size: ~230MB
echo Setup time: 5-10 minutes
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is required but not found.
    echo.
    echo Please install Python from: https://python.org
    echo Then run this setup script again.
    echo.
    pause
    goto main_menu
)

curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama is not running.
    echo ONNX models work best with Ollama installed.
    echo.
    echo Recommendation: Set up Ollama first (option 2)
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i not "!continue!"=="y" goto main_menu
)

python -c "from ultralytics import YOLO" >nul 2>&1
if errorlevel 1 (
    echo WARNING: YOLO is not installed.
    echo ONNX models work with YOLO for enhanced detection.
    echo.
    echo Recommendation: Set up YOLO first (option 3)
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i not "!continue!"=="y" goto main_menu
)

echo Installing ONNX dependencies...
pip install onnxruntime onnx huggingface_hub requests numpy
if errorlevel 1 (
    echo ERROR: Failed to install ONNX dependencies
    echo.
    pause
    goto main_menu
)

echo.
echo Checking for download script...
if exist "download_onnx_models.bat" (
    echo Found download_onnx_models.bat, running it...
    call download_onnx_models.bat
) else (
    echo Download script not found in current directory.
    echo.
    echo Manual steps:
    echo   1. Locate download_onnx_models.bat (should be with ImageDescriber.exe)
    echo   2. Run it to download ONNX models
    echo.
)

echo.
echo ================================================================
echo ONNX Setup Complete ✓
echo ================================================================
echo.
echo Enhanced ONNX provider is now available in ImageDescriber!
echo.
echo Usage:
echo   Provider: "Enhanced ONNX" (or variants with Spatial/Comprehensive)
echo   Combines: YOLO detection + Ollama descriptions
echo   Result: Most accurate and detailed image analysis
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

if exist "USER_SETUP_GUIDE.md" (
    start notepad USER_SETUP_GUIDE.md
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

echo [1/5] Testing Ollama...
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

python --version >nul 2>&1
if errorlevel 1 (
    echo [2/5] YOLO: Cannot test (Python required)
    echo [3/5] ONNX: Cannot test (Python required)
    echo [4/5] Enhanced ONNX: Cannot test (Python required)
    echo.
    goto test_copilot
)

echo [2/5] Testing YOLO...
python -c "from ultralytics import YOLO" >nul 2>&1
if errorlevel 1 (
    echo [ ] YOLO: NOT INSTALLED
) else (
    echo [x] YOLO: READY
)
echo.

echo [3/5] Testing ONNX Runtime...
python -c "import onnxruntime" >nul 2>&1
if errorlevel 1 (
    echo [ ] ONNX: NOT INSTALLED
) else (
    if exist "onnx_models\florence2" (
        echo [x] ONNX: READY (models downloaded)
    ) else (
        echo [~] ONNX: Installed but models not downloaded
    )
)
echo.

echo [4/5] Testing Enhanced ONNX (YOLO + Ollama + ONNX)...
set ENHANCED_READY=1
python -c "from ultralytics import YOLO" >nul 2>&1
if errorlevel 1 set ENHANCED_READY=0
python -c "import onnxruntime" >nul 2>&1
if errorlevel 1 set ENHANCED_READY=0
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 set ENHANCED_READY=0

if %ENHANCED_READY%==1 (
    echo [x] Enhanced ONNX: READY (all components available)
) else (
    echo [ ] Enhanced ONNX: NOT READY (requires YOLO + Ollama + ONNX)
)
echo.

:test_copilot
echo [5/5] Testing Copilot+ PC (NPU)...
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
echo   - YOLO: Great for counting/detecting specific objects
echo   - Enhanced ONNX: Maximum accuracy (combines all features)
echo   - Copilot+ PC: Fastest on compatible hardware
echo.
echo See USER_SETUP_GUIDE.md for detailed setup instructions.
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
echo   - See USER_SETUP_GUIDE.md for detailed instructions
echo   - GitHub: github.com/kellylford/Image-Description-Toolkit
echo.
echo Happy describing!
echo.
pause
