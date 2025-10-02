@echo off
echo ================================================================
echo    ImageDescriber - GroundingDINO Installation Script
echo ================================================================
echo.
echo This script installs GroundingDINO for text-prompted object detection.
echo.
echo What is GroundingDINO?
echo   - Detects ANY object you describe in text
echo   - No preset limits (unlike YOLO's 80 classes)
echo   - Natural language queries: "red cars . people wearing hats"
echo   - Works in chat mode for interactive detection
echo.
echo Installation details:
echo   - Package size: ~100MB
echo   - Model size: ~700MB (downloads automatically on first use)
echo   - Time: 3-5 minutes + first-use download
echo.
echo Requirements:
echo   - Python 3.8 or higher
echo   - Internet connection (for installation and first-use model download)
echo   - ~1GB free disk space
echo.
pause

REM Check if Python is available
echo.
echo [1/5] Checking Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo.
    echo GroundingDINO requires Python to be installed.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo After installing Python, run this script again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% found ✓
echo.

REM Check if groundingdino is already installed
echo [2/5] Checking if GroundingDINO is already installed
python -c "import groundingdino" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo GroundingDINO is already installed! ✓
    echo.
    echo Checking version and dependencies
    python -c "import groundingdino; print('Version:', groundingdino.__version__ if hasattr(groundingdino, '__version__') else 'Unknown')" 2>nul
    python -c "import torch; print('PyTorch:', torch.__version__)" 2>nul
    python -c "import torchvision; print('TorchVision:', torchvision.__version__)" 2>nul
    echo.
    set /p REINSTALL="Would you like to reinstall/upgrade? (y/N): "
    if /i not "%REINSTALL%"=="y" (
        echo.
        echo Skipping installation. You're all set!
        goto :success
    )
    echo.
    echo Proceeding with reinstall/upgrade
)

REM Install PyTorch first
echo.
echo [3/5] Installing PyTorch and TorchVision
echo This may take a few minutes depending on your internet connection.
echo.

REM Check if CUDA is available for GPU support
python -c "import torch; print('CUDA Available' if torch.cuda.is_available() else 'CPU Only')" >nul 2>&1
if errorlevel 1 (
    REM PyTorch not installed, install CPU version by default
    echo Installing PyTorch ^(CPU version^)
    echo Note: If you have an NVIDIA GPU, you can install CUDA version later
    echo       for faster detection performance.
    echo.
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
) else (
    REM PyTorch exists, update it
    echo Updating PyTorch and TorchVision
    pip install --upgrade torch torchvision
)

if errorlevel 1 (
    echo.
    echo WARNING: PyTorch installation encountered issues.
    echo Continuing with GroundingDINO installation anyway.
    echo You may need to install PyTorch manually if GroundingDINO fails.
    echo.
    pause
)

REM Install GroundingDINO
echo.
echo [4/5] Installing GroundingDINO
echo.
pip install groundingdino-py

if errorlevel 1 (
    echo.
    echo ================================================================
    echo ERROR: GroundingDINO installation failed!
    echo ================================================================
    echo.
    echo Common issues and solutions:
    echo.
    echo 1. Missing Visual C^+^+ Build Tools (Windows):
    echo    - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo    - Install "Desktop development with C^+^+" workload
    echo.
    echo 2. Outdated pip:
    echo    - Run: python -m pip install --upgrade pip
    echo    - Then run this script again
    echo.
    echo 3. Permission issues:
    echo    - Try running Command Prompt as Administrator
    echo    - Or install with --user flag: pip install groundingdino-py --user
    echo.
    echo 4. Network/firewall issues:
    echo    - Check your internet connection
    echo    - Try disabling VPN temporarily
    echo    - Check firewall settings
    echo.
    pause
    exit /b 1
)

REM Verify installation
echo.
echo [5/5] Verifying installation
echo.
python -c "import groundingdino; import torch; import torchvision; print('✓ GroundingDINO installed successfully')" >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Installation completed but verification failed.
    echo Some dependencies might be missing.
    echo Try running ImageDescriber and process an image to test.
    echo.
    pause
    exit /b 1
)

:success
echo.
echo ================================================================
echo SUCCESS! GroundingDINO Installation Complete ✓
echo ================================================================
echo.
echo Next steps:
echo.
echo 1. RESTART IMAGEDESCRIBER (if it's currently running)
echo.
echo 2. Use GroundingDINO:
echo    - Select an image in your workspace
echo    - Click "Process Image"
echo    - Choose provider: "GroundingDINO" or "GroundingDINO + Ollama"
echo    - Configure detection:
echo      * Automatic: Select preset (Comprehensive, Indoor, Outdoor, etc.)
echo      * Custom: Type your query (e.g., "red cars . blue trucks")
echo    - Adjust confidence threshold (default 25%%)
echo    - Click OK
echo.
echo 3. FIRST USE ONLY: Model Download
echo    - On first detection, ~700MB model downloads automatically
echo    - This takes 2-10 minutes depending on internet speed
echo    - Progress shown in console window
echo    - After first download, everything works offline!
echo.
echo 4. Chat Integration:
echo    - Select an image in workspace
echo    - Open a chat session
echo    - Type: "find red cars" or "detect safety equipment"
echo    - GroundingDINO automatically detects and responds!
echo.
echo Example Queries:
echo   "red cars . blue trucks . motorcycles"
echo   "people wearing helmets . safety equipment"
echo   "fire exits . emergency signs"
echo   "damaged items . missing parts"
echo   "text . logos . diagrams"
echo.
echo Model Cache Location:
echo   Windows: C:\Users\%USERNAME%\.cache\groundingdino\
echo   (Model downloads automatically here on first use)
echo.
echo ================================================================
echo.
pause
