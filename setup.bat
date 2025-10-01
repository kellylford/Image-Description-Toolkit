@echo off
echo ================================================================
echo    Image Description Toolkit - Automated Setup
echo ================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://python.org
    echo.
    pause
    exit /b 1
)

echo [1/5] Python found - checking version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

echo [2/5] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

echo [3/5] Checking for Ollama...
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama is not running
    echo.
    echo Please install and start Ollama:
    echo 1. Download from: https://ollama.ai/download/windows
    echo 2. Install and run: ollama serve
    echo 3. Pull a vision model: ollama pull llava:7b
    echo.
    echo After Ollama is running, you can test with:
    echo   python workflow.py tests/test_files/
    echo.
) else (
    echo Ollama is running! ✓
    echo.
    echo [4/5] Checking for vision models...
    ollama list | findstr /i "llava\|llama.*vision\|moondream\|bakllava" >nul 2>&1
    if errorlevel 1 (
        echo No vision models found. Downloading llava:7b...
        ollama pull llava:7b
        if errorlevel 1 (
            echo ERROR: Failed to download vision model
            echo Please manually run: ollama pull llava:7b
        ) else (
            echo Vision model downloaded successfully! ✓
        )
    ) else (
        echo Vision models found! ✓
    )
    echo.
)

echo [5/5] Running basic tests...
cd tests
python run_tests.py
if errorlevel 1 (
    echo Some tests failed - check output above
) else (
    echo All tests passed! ✓
)
cd ..
echo.

echo ================================================================
echo    Setup Complete!
echo ================================================================
echo.
echo Quick Start Commands:
echo   1. Test your setup:        python workflow.py tests/test_files/
echo   2. Process your media:     python workflow.py path/to/your/media
echo   3. Launch GUI:             cd imagedescriber ^&^& python imagedescriber.py
echo   4. Test all AI models:     python comprehensive_test.py tests/test_files/images
echo.
echo Documentation:
echo   - Full guide: README.md
echo   - Configuration: docs/CONFIGURATION.md
echo   - Model testing: comprehensive_test.py --help
echo.
pause