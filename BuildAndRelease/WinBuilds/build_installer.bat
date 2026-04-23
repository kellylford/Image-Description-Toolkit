@echo off
REM ============================================================================
REM Build Inno Setup Installer for Image Description Toolkit (wxPython Version)
REM ============================================================================
REM This script compiles the installer.iss file into a Windows installer
REM Works directly from dist_all directory (no zip files needed)
REM
REM Prerequisites:
REM   - Run builditall_wx.bat first to build all executables
REM   - Run package_all_windows.bat to collect them in dist_all/bin/
REM   - Inno Setup 6 installed
REM ============================================================================

echo ================================================
echo Building Image Description Toolkit Installer
echo ================================================
echo.
echo Current directory: %CD%
echo Script directory: %~dp0
echo.

REM Change to the script's directory (BuildAndRelease\WinBuilds)
cd /d "%~dp0"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to change to script directory
    pause
    exit /b 1
)

echo Changed to: %CD%
echo.

REM Read version from VERSION file
set VERSION=unknown
if exist "..\..\VERSION" (
    set /p VERSION=<..\..\VERSION
)
REM Remove any trailing whitespace or newlines
set VERSION=%VERSION: =%

echo Using version: %VERSION%
echo.

REM Check if Inno Setup is installed
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    echo ERROR: Inno Setup not found at: "%INNO_PATH%"
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

REM Check if dist_all directory exists
if not exist "dist_all\bin" (
    echo ERROR: dist_all\bin directory not found
    echo Please run package_all_windows.bat first to collect all executables.
    echo.
    pause
    exit /b 1
)

REM Check if all required executables exist
set MISSING_FILES=0

if not exist "dist_all\bin\idt.exe" (
    echo ERROR: idt.exe not found
    set MISSING_FILES=1
)

REM [DEPRECATED] Viewer - now integrated into ImageDescriber
REM if not exist "dist_all\bin\Viewer.exe" (
REM     echo ERROR: Viewer.exe not found
REM     set MISSING_FILES=1
REM )

if not exist "dist_all\bin\ImageDescriber.exe" (
    echo ERROR: ImageDescriber.exe not found
    set MISSING_FILES=1
)

if %MISSING_FILES%==1 (
    echo.
    echo Please run:
    echo   1. builditall_wx.bat
    echo   2. package_all_windows.bat
    echo.
    pause
    exit /b 1
)

echo All required files found.
echo.
echo Compiling installer...
echo Command: "%INNO_PATH%" installer.iss
echo.
"%INNO_PATH%" installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo SUCCESS: Installer created successfully!
    echo ================================================
    echo.
    echo Output: dist_all\ImageDescriptionToolkit_Setup_v%VERSION%.exe
    echo.
    echo The installer includes:
    echo   - idt.exe (CLI)
    echo   - ImageDescriber.exe (includes integrated Viewer Mode, Prompt Editor and Configure tools)
    echo   - Configuration files
    echo   - Documentation
    echo.
    pause
    exit /b 0
) else (
    echo.
    echo ================================================
    echo ERROR: Installer compilation failed!
    echo Error code: %ERRORLEVEL%
    echo ================================================
    echo.
    pause
    exit /b 1
)
