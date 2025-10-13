@echo off
REM ============================================================================
REM Bootstrap Script - Clone Repository and Set Up Environment
REM ============================================================================
REM This script is designed to be run STANDALONE (downloaded separately).
REM It will:
REM   1. Clone the Image Description Toolkit repository
REM   2. Run the environment setup script
REM   3. Prepare the project for building
REM
REM Usage:
REM   1. Download this file to your desired parent directory
REM   2. Run it: bootstrap.bat
REM   3. Script will create "Image-Description-Toolkit" subdirectory
REM
REM Prerequisites:
REM   - Git installed and in PATH
REM   - Python 3.8+ installed and in PATH
REM
REM Note: This script will NOT work if run from inside the repository.
REM       It's meant to be downloaded separately and run from a parent directory.
REM ============================================================================

echo.
echo ========================================================================
echo IMAGE DESCRIPTION TOOLKIT - BOOTSTRAP
echo ========================================================================
echo.
echo This script will:
echo   1. Clone the repository from GitHub
echo   2. Set up virtual environments for all apps
echo   3. Install all dependencies
echo.

REM Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo.
    echo Please install Git from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Prerequisites check: OK
echo.

REM Check if directory already exists
if exist "Image-Description-Toolkit" (
    echo WARNING: Image-Description-Toolkit directory already exists!
    echo.
    echo Options:
    echo   1. Delete it and clone fresh
    echo   2. Skip clone and just run environment setup
    echo   3. Cancel
    echo.
    choice /C 123 /N /M "Choose [1, 2, or 3]: "
    
    if errorlevel 3 (
        echo Cancelled.
        exit /b 0
    )
    if errorlevel 2 (
        echo Skipping clone, running environment setup...
        goto setup_env
    )
    if errorlevel 1 (
        echo Removing existing directory...
        rmdir /s /q "Image-Description-Toolkit"
    )
)

REM Clone the repository
echo.
echo ========================================================================
echo CLONING REPOSITORY
echo ========================================================================
echo.
echo Cloning from: https://github.com/kellylford/Image-Description-Toolkit.git
echo.

git clone https://github.com/kellylford/Image-Description-Toolkit.git

if errorlevel 1 (
    echo.
    echo ERROR: Failed to clone repository
    echo.
    echo Please check:
    echo   - Internet connection
    echo   - GitHub repository URL
    echo   - Git credentials (if private repo)
    echo.
    pause
    exit /b 1
)

echo.
echo Repository cloned successfully!

REM Run environment setup
:setup_env
echo.
echo ========================================================================
echo SETTING UP ENVIRONMENTS
echo ========================================================================
echo.

cd Image-Description-Toolkit
if errorlevel 1 (
    echo ERROR: Could not enter Image-Description-Toolkit directory
    pause
    exit /b 1
)

if exist "tools\environmentsetup.bat" (
    call tools\environmentsetup.bat
) else (
    echo ERROR: environmentsetup.bat not found in tools directory
    echo.
    echo The repository may be incomplete or corrupt.
    pause
    exit /b 1
)

REM Final summary
echo.
echo ========================================================================
echo BOOTSTRAP COMPLETE!
echo ========================================================================
echo.
echo The Image Description Toolkit is ready to use.
echo.
echo Project location: %CD%
echo.
echo Next steps:
echo   1. To build all apps:        releaseitall.bat
echo   2. To build just IDT:        build_idt.bat
echo   3. To build individual app:  cd viewer ^&^& .venv\Scripts\activate ^&^& build_viewer.bat
echo.
echo All distribution packages will be created in: releases\
echo.
pause
