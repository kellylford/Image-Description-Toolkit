@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
REM Install Ollama for Windows
REM This script downloads and installs Ollama automatically
REM Usage: install_ollama.bat

echo ========================================================================
echo Ollama Installation Script for Windows
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
REM Check if running as administrator (recommended but not required)
net session >nul 2>&1
    echo WARNING: Not running as administrator.
    echo Installation may require manual approval of security prompts.
    echo For best results, run this script as administrator.
    set /p continue="Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        echo Installation cancelled.
        pause
        exit /b 1
    )
REM Check if Ollama is already installed
where ollama >nul 2>&1
if not errorlevel 1 (
    echo Ollama is already installed!
    ollama --version
    set /p reinstall="Reinstall anyway? (y/N): "
    if /i not "!reinstall!"=="y" (
        echo Installation skipped.
        echo.
        echo To get started with Ollama:
        echo   ollama pull llava
        echo   ollama pull llama3.2-vision
        exit /b 0
echo [1/4] Detecting system architecture and downloading Ollama...
REM Detect processor architecture using multiple methods
echo Detecting processor architecture...
echo Environment PROCESSOR_ARCHITECTURE: %PROCESSOR_ARCHITECTURE%
echo Environment PROCESSOR_ARCHITEW6432: %PROCESSOR_ARCHITEW6432%
REM Try to get architecture from wmic as well
for /f "skip=1 delims=" %%a in ('wmic cpu get architecture /value 2^>nul ^| findstr "="') do set "%%a"
REM Determine architecture (check multiple sources for reliability)
set DETECTED_ARCH=UNKNOWN
REM Check PROCESSOR_ARCHITEW6432 first (more reliable on 32-bit processes on 64-bit systems)
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set DETECTED_ARCH=ARM64
if /i "%PROCESSOR_ARCHITEW6432%"=="AMD64" set DETECTED_ARCH=AMD64
REM If not set, check PROCESSOR_ARCHITECTURE
if "%DETECTED_ARCH%"=="UNKNOWN" (
    if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set DETECTED_ARCH=ARM64
    if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" set DETECTED_ARCH=AMD64
    if /i "%PROCESSOR_ARCHITECTURE%"=="x86" set DETECTED_ARCH=x86
REM Check wmic result if available
if defined Architecture (
    if "!Architecture!"=="9" set DETECTED_ARCH=AMD64
    if "!Architecture!"=="12" set DETECTED_ARCH=ARM64
    if "!Architecture!"=="0" set DETECTED_ARCH=x86
echo Detected architecture: %DETECTED_ARCH%
REM Determine the correct download URL based on detected architecture
if /i "%DETECTED_ARCH%"=="ARM64" (
    set OLLAMA_URL=https://ollama.ai/download/OllamaSetup-arm64.exe
    set ARCH_NAME=ARM64
    echo Windows ARM64 detected - downloading ARM64 version
) else if /i "%DETECTED_ARCH%"=="AMD64" (
    set OLLAMA_URL=https://ollama.ai/download/OllamaSetup.exe
    set ARCH_NAME=x64
    echo Windows x64 detected - downloading x64 version
) else if /i "%DETECTED_ARCH%"=="x86" (
    set ARCH_NAME=x64 ^(32-bit compatibility^)
    echo Windows x86 detected - downloading x64 version for compatibility
) else (
    echo WARNING: Could not reliably detect architecture (%DETECTED_ARCH%)
    echo Available environment variables:
    echo   PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE%
    echo   PROCESSOR_ARCHITEW6432=%PROCESSOR_ARCHITEW6432%
    if defined Architecture echo   WMIC Architecture=!Architecture!
    echo Please choose your architecture:
    echo   1. ARM64 (for Windows on ARM devices like Surface Pro X, ARM-based PCs)
    echo   2. x64 (for standard Intel/AMD 64-bit systems)
    set /p arch_choice="Enter choice (1 or 2): "
    
    if "!arch_choice!"=="1" (
        set OLLAMA_URL=https://ollama.ai/download/OllamaSetup-arm64.exe
        set ARCH_NAME=ARM64 ^(manual selection^)
        echo ARM64 selected manually
    ) else if "!arch_choice!"=="2" (
        set OLLAMA_URL=https://ollama.ai/download/OllamaSetup.exe
        set ARCH_NAME=x64 ^(manual selection^)
        echo x64 selected manually
    ) else (
        echo Invalid choice. Defaulting to x64 version.
        set ARCH_NAME=x64 ^(default fallback^)
echo Architecture detected: !ARCH_NAME!
REM Create temp directory
set TEMP_DIR=%TEMP%\ollama_install_%RANDOM%
mkdir "%TEMP_DIR%" 2>nul
REM Set installer path
set INSTALLER_PATH=%TEMP_DIR%\OllamaSetup.exe
echo Downloading Ollama for !ARCH_NAME!...
echo URL: !OLLAMA_URL!
echo Saving to: %INSTALLER_PATH%
curl -L -o "%INSTALLER_PATH%" "!OLLAMA_URL!"
    echo ERROR: Failed to download Ollama installer.
    echo Please check your internet connection and try again.
    echo Manual download for !ARCH_NAME!: !OLLAMA_URL!
    rmdir /s /q "%TEMP_DIR%" 2>nul
REM Verify download
if not exist "%INSTALLER_PATH%" (
    echo ERROR: Download failed - installer file not found.
echo Download completed successfully!
echo [2/4] Running Ollama installer...
echo NOTE: The installer may show security warnings or UAC prompts.
echo Please approve them to complete the installation.
REM Run the installer
"%INSTALLER_PATH%"
set INSTALL_EXIT_CODE=!errorlevel!
REM Clean up temp files
rmdir /s /q "%TEMP_DIR%" 2>nul
if !INSTALL_EXIT_CODE! neq 0 (
    echo WARNING: Installer returned exit code !INSTALL_EXIT_CODE!
    echo This may indicate the installation was cancelled or failed.
echo [3/4] Verifying installation...
REM Wait a moment for installation to complete
timeout /t 3 /nobreak >nul 2>&1
REM Check if Ollama is now available
    echo WARNING: Ollama command not found in PATH.
    echo This might mean:
    echo   1. Installation was cancelled or failed
    echo   2. You need to restart your command prompt
    echo   3. You need to restart Windows
    echo Try closing this window and opening a new command prompt.
    echo If the issue persists, visit: https://ollama.ai/download
echo Ollama installation successful!
ollama --version
echo [4/4] Setting up recommended models...
echo This will download some popular vision models for image description.
echo Each model is several GB - this may take a while depending on your connection.
set /p install_models="Download recommended models now? (Y/n): "
if /i "!install_models!"=="n" (
    echo Skipping model downloads.
    echo To download models later, use:
    echo   ollama pull llava
    echo   ollama pull llama3.2-vision
    echo   ollama pull moondream
    goto :success
echo Downloading models... This may take several minutes.
echo Downloading LLaVA (4.7GB)...
ollama pull llava
    echo WARNING: Failed to download LLaVA model.
echo Downloading Llama 3.2 Vision (7.9GB)...
ollama pull llama3.2-vision
    echo WARNING: Failed to download Llama 3.2 Vision model.
echo Downloading Moondream (1.7GB)...
ollama pull moondream
    echo WARNING: Failed to download Moondream model.
:success
echo Ollama Installation Complete!
echo Available commands:
echo   ollama list                    - Show installed models
echo   ollama pull [model]           - Download a model
echo   ollama run [model]            - Run a model interactively
echo Popular vision models for image description:
echo   ollama pull llava             - General-purpose vision model
echo   ollama pull llama3.2-vision   - Latest Llama vision model
echo   ollama pull moondream         - Lightweight vision model
echo   ollama pull cogvlm2           - Advanced vision understanding
echo You can now use the batch files in this directory to run
echo image description workflows with Ollama models!
echo Examples:
echo   run_ollama_llava.bat images_folder
echo   run_ollama_moondream.bat photos
pause
ENDLOCAL
