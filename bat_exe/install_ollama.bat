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

echo [1/4] Detecting system architecture and downloading Ollama...
echo.

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
)

REM Check wmic result if available
if defined Architecture (
    if "!Architecture!"=="9" set DETECTED_ARCH=AMD64
    if "!Architecture!"=="12" set DETECTED_ARCH=ARM64
    if "!Architecture!"=="0" set DETECTED_ARCH=x86
)

echo Detected architecture: %DETECTED_ARCH%
echo.

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
    set OLLAMA_URL=https://ollama.ai/download/OllamaSetup.exe
    set ARCH_NAME=x64 ^(32-bit compatibility^)
    echo Windows x86 detected - downloading x64 version for compatibility
) else (
    echo WARNING: Could not reliably detect architecture (%DETECTED_ARCH%)
    echo Available environment variables:
    echo   PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE%
    echo   PROCESSOR_ARCHITEW6432=%PROCESSOR_ARCHITEW6432%
    if defined Architecture echo   WMIC Architecture=!Architecture!
    echo.
    echo Please choose your architecture:
    echo   1. ARM64 (for Windows on ARM devices like Surface Pro X, ARM-based PCs)
    echo   2. x64 (for standard Intel/AMD 64-bit systems)
    echo.
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
        set OLLAMA_URL=https://ollama.ai/download/OllamaSetup.exe
        set ARCH_NAME=x64 ^(default fallback^)
    )
)

echo Architecture detected: !ARCH_NAME!
echo.

REM Create temp directory
set TEMP_DIR=%TEMP%\ollama_install_%RANDOM%
mkdir "%TEMP_DIR%" 2>nul

REM Set installer path
set INSTALLER_PATH=%TEMP_DIR%\OllamaSetup.exe

echo Downloading Ollama for !ARCH_NAME!...
echo URL: !OLLAMA_URL!
echo Saving to: %INSTALLER_PATH%
echo.

curl -L -o "%INSTALLER_PATH%" "!OLLAMA_URL!"
if errorlevel 1 (
    echo ERROR: Failed to download Ollama installer.
    echo Please check your internet connection and try again.
    echo.
    echo Manual download for !ARCH_NAME!: !OLLAMA_URL!
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