@echo off
REM ============================================================================
REM Environment Setup - Create Virtual Environments for All Apps
REM ============================================================================
REM This script creates separate virtual environments for all three applications
REM and installs their dependencies.
REM
REM What it does:
REM   1. Creates .winenv for main IDT (root directory)
REM   2. Creates .winenv for viewer
REM   3. Creates .winenv for imagedescriber (with integrated tools)
REM   4. Installs requirements.txt in each venv
REM
REM Prerequisites:
REM   - Python 3.8+ installed and in PATH
REM
REM Time: ~5-10 minutes (depending on internet speed)
REM ============================================================================

echo.
echo ========================================================================
echo ENVIRONMENT SETUP FOR ALL APPLICATIONS
echo ========================================================================
echo.
echo This will create virtual environments and install dependencies for:
echo   1. IDT (main toolkit)
echo   2. Viewer
echo   3. ImageDescriber (with integrated prompt editor and configuration)
echo.
echo This is a ONE-TIME setup process.
echo.

set SETUP_ERRORS=0

REM Navigate to project root (one level up from tools)
cd /d "%~dp0.."

REM ============================================================================
echo.
echo [1/4] Setting up IDT (main toolkit)...
echo ========================================================================
echo.

if exist ".venv" (
    echo WARNING: .venv already exists in root directory
    echo Skipping creation, but will update requirements...
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment for IDT
        set /a SETUP_ERRORS+=1
        goto viewer_setup
    )
    echo Virtual environment created.
)

echo.
echo Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install IDT dependencies
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: IDT environment ready
)
call deactivate

REM ============================================================================
:viewer_setup
echo.
echo [2/3] Setting up Viewer...
echo ========================================================================
echo.

cd viewer

if exist ".venv" (
    echo WARNING: .venv already exists in viewer directory
    echo Skipping creation, but will update requirements...
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment for Viewer
        set /a SETUP_ERRORS+=1
        cd ..
        goto imagedescriber_setup
    )
    echo Virtual environment created.
)

echo.
echo Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Viewer dependencies
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: Viewer environment ready
)
call deactivate

cd ..

REM ============================================================================
:imagedescriber_setup
echo.
echo [3/3] Setting up ImageDescriber...
echo ========================================================================
echo.

cd imagedescriber

if exist ".venv" (
    echo WARNING: .venv already exists in imagedescriber directory
    echo Skipping creation, but will update requirements...
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment for ImageDescriber
        set /a SETUP_ERRORS+=1
        cd ..
        goto summary
    )
    echo Virtual environment created.
)

echo.
echo Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install ImageDescriber dependencies
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: ImageDescriber environment ready
)
call deactivate

cd ..

REM ============================================================================
:summary
echo.
echo ========================================================================
echo SETUP SUMMARY
echo ========================================================================
echo.

if "%SETUP_ERRORS%"=="0" (
    echo SUCCESS: All environments set up successfully!
    echo.
    echo Virtual environments created:
    if exist ".venv" echo   - Root:              .venv
    if exist "viewer\.venv" echo   - Viewer:            viewer\.venv
    if exist "imagedescriber\.venv" echo   - ImageDescriber:   imagedescriber\.venv (with integrated Tools menu)
    echo.
    echo All dependencies installed.
    echo.
    echo Next steps:
    echo   1. Build all apps:     releaseitall.bat
    echo   2. Or build only IDT:  build_idt.bat
    echo   3. Or build only GUI:  cd viewer ^&^& .venv\Scripts\activate ^&^& build_viewer.bat
    echo.
) else (
    echo ERRORS ENCOUNTERED: %SETUP_ERRORS% setup step(s) failed
    echo.
    echo Please review the output above for error details.
    echo Common issues:
    echo   - Python not in PATH
    echo   - No internet connection (can't download packages)
    echo   - Insufficient permissions
    echo   - Disk space issues
    echo.
)

echo.
echo ========================================================================
echo.
