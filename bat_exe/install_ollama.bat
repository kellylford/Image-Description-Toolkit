@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
REM Install Ollama for Windows
REM This script downloads and installs Ollama automatically
REM Usage: install_ollama.bat

echo ========================================================================
echo Ollama Installation Script for Windows
echo ========================================================================
echo.

REM Check if we're running on Windows
if not "%OS%"=="Windows_NT" (
    echo ERROR: This script is designed for Windows only.
    echo For other platforms, please visit: https://ollama.ai/download
    echo.
    pause
    exit /b 1
)

REM Check for required tools
where curl >nul 2>&1
if errorlevel 1 (
    echo ERROR: curl is not available.
    echo Please install curl or use Windows 10/11 which includes curl by default.
    echo.
    pause
    exit /b 1
)

REM Check if running as administrator (recommended but not required)
net session >nul 2>&1
if errorlevel 1 (
    echo WARNING: Not running as administrator.
    echo Installation may require manual approval of security prompts.
    echo For best results, run this script as administrator.
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        echo Installation cancelled.
        pause
        exit /b 1
    )
    echo.
)

REM Check if Ollama is already installed
where ollama >nul 2>&1
if not errorlevel 1 (
    echo Ollama is already installed!
    ollama --version
    echo.
    set /p reinstall="Reinstall anyway? (y/N): "
    if /i not "!reinstall!"=="y" (
        echo Installation skipped.
        echo.
        echo To get started with Ollama:
        echo   ollama pull llava
        echo   ollama pull llama3.2-vision
        echo.
        pause
        exit /b 0
    )
    echo.
)

echo [1/4] Downloading Ollama for Windows...
echo.

REM Create temp directory
set TEMP_DIR=%TEMP%\ollama_install_%RANDOM%
mkdir "%TEMP_DIR%" 2>nul

REM Download Ollama installer
set OLLAMA_URL=https://ollama.ai/download/windows
set INSTALLER_PATH=%TEMP_DIR%\OllamaSetup.exe

echo Downloading from: %OLLAMA_URL%
echo Saving to: %INSTALLER_PATH%
echo.

curl -L -o "%INSTALLER_PATH%" "%OLLAMA_URL%"
if errorlevel 1 (
    echo ERROR: Failed to download Ollama installer.
    echo Please check your internet connection and try again.
    echo.
    echo Manual download: %OLLAMA_URL%
    rmdir /s /q "%TEMP_DIR%" 2>nul
    pause
    exit /b 1
)

REM Verify download
if not exist "%INSTALLER_PATH%" (
    echo ERROR: Download failed - installer file not found.
    rmdir /s /q "%TEMP_DIR%" 2>nul
    pause
    exit /b 1
)

echo Download completed successfully!
echo.

echo [2/4] Running Ollama installer...
echo.
echo NOTE: The installer may show security warnings or UAC prompts.
echo Please approve them to complete the installation.
echo.

REM Run the installer
"%INSTALLER_PATH%"
set INSTALL_EXIT_CODE=!errorlevel!

REM Clean up temp files
rmdir /s /q "%TEMP_DIR%" 2>nul

if !INSTALL_EXIT_CODE! neq 0 (
    echo.
    echo WARNING: Installer returned exit code !INSTALL_EXIT_CODE!
    echo This may indicate the installation was cancelled or failed.
    echo.
)

echo [3/4] Verifying installation...
echo.

REM Wait a moment for installation to complete
timeout /t 3 /nobreak >nul 2>&1

REM Check if Ollama is now available
where ollama >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama command not found in PATH.
    echo.
    echo This might mean:
    echo   1. Installation was cancelled or failed
    echo   2. You need to restart your command prompt
    echo   3. You need to restart Windows
    echo.
    echo Try closing this window and opening a new command prompt.
    echo If the issue persists, visit: https://ollama.ai/download
    echo.
    pause
    exit /b 1
)

echo Ollama installation successful!
ollama --version
echo.

echo [4/4] Setting up recommended models...
echo.

echo This will download some popular vision models for image description.
echo Each model is several GB - this may take a while depending on your connection.
echo.

set /p install_models="Download recommended models now? (Y/n): "
if /i "!install_models!"=="n" (
    echo.
    echo Skipping model downloads.
    echo.
    echo To download models later, use:
    echo   ollama pull llava
    echo   ollama pull llama3.2-vision
    echo   ollama pull moondream
    echo.
    goto :success
)

echo.
echo Downloading models... This may take several minutes.
echo.

echo Downloading LLaVA (4.7GB)...
ollama pull llava
if errorlevel 1 (
    echo WARNING: Failed to download LLaVA model.
)

echo.
echo Downloading Llama 3.2 Vision (7.9GB)...
ollama pull llama3.2-vision
if errorlevel 1 (
    echo WARNING: Failed to download Llama 3.2 Vision model.
)

echo.
echo Downloading Moondream (1.7GB)...
ollama pull moondream
if errorlevel 1 (
    echo WARNING: Failed to download Moondream model.
)

:success
echo.
echo ========================================================================
echo Ollama Installation Complete!
echo ========================================================================
echo.
echo Available commands:
echo   ollama list                    - Show installed models
echo   ollama pull [model]           - Download a model
echo   ollama run [model]            - Run a model interactively
echo.
echo Popular vision models for image description:
echo   ollama pull llava             - General-purpose vision model
echo   ollama pull llama3.2-vision   - Latest Llama vision model
echo   ollama pull moondream         - Lightweight vision model
echo   ollama pull cogvlm2           - Advanced vision understanding
echo.
echo You can now use the batch files in this directory to run
echo image description workflows with Ollama models!
echo.
echo Examples:
echo   run_ollama_llava.bat images_folder
echo   run_ollama_moondream.bat photos
echo.
pause
ENDLOCAL