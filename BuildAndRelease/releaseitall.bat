@echo off
REM ============================================================================
REM Release All Applications - Complete Build and Package
REM ============================================================================
REM This master script does everything needed for a complete release:
REM   1. Builds all five applications (builditall.bat)
REM   2. Packages all five applications (packageitall.bat)
REM   3. All distribution packages ready in releases/ directory
REM
REM Prerequisites:
REM   - Virtual environments set up for GUI apps
REM   - Dependencies installed
REM
REM Output:
REM   - releases/ImageDescriptionToolkit_v[VERSION].zip
REM   - releases/viewer_v[VERSION]_[ARCH].zip
REM   - releases/prompt_editor_v[VERSION]_[ARCH].zip
REM   - releases/imagedescriber_v[VERSION]_[ARCH].zip
REM   - releases/idtconfigure_v[VERSION].zip
REM   - releases/idt2.zip (master package containing all individual packages)
REM ============================================================================

echo.
echo ========================================================================
echo COMPLETE RELEASE BUILD
echo ========================================================================
echo.
echo This will build and package all five applications:
echo   1. IDT (main toolkit)
echo   2. Viewer
echo   3. Prompt Editor
echo   4. ImageDescriber
echo   5. IDTConfigure
echo.
echo All distribution packages will be created in releases/ directory.
echo A master package (idt2.zip) will also be created containing all packages.
echo.
echo Starting release process...
echo.

REM Change to project root directory
cd /d "%~dp0.."

REM ============================================================================
echo ========================================================================
echo PHASE 1: BUILD ALL APPLICATIONS
echo ========================================================================
echo.

call BuildAndRelease\builditall.bat
if errorlevel 1 (
    echo.
    echo ERROR: Build phase failed!
    echo Please review the errors above.
    echo.
    echo Release process aborted.
    exit /b 1
)

REM ============================================================================
echo.
echo ========================================================================
echo PHASE 2: PACKAGE ALL APPLICATIONS
echo ========================================================================
echo.

call BuildAndRelease\packageitall.bat
if errorlevel 1 (
    echo.
    echo ERROR: Package phase failed!
    echo Please review the errors above.
    echo.
    echo Release process incomplete.
    exit /b 1
)

REM ============================================================================
echo.
echo ========================================================================
echo PHASE 3: CREATE MASTER PACKAGE
echo ========================================================================
echo.

REM Check if we have any packages to bundle
if not exist releases\*.zip (
    echo ERROR: No distribution packages found in releases\ directory!
    echo Cannot create master package.
    exit /b 1
)

echo Creating master package idt2.zip with all distribution packages...
echo.

REM Delete existing idt2.zip if it exists
if exist releases\idt2.zip (
    echo Removing existing idt2.zip...
    del releases\idt2.zip
)

REM Create idt2.zip containing all individual distribution packages
REM Use PowerShell for reliable ZIP creation on Windows
powershell -NoProfile -Command "Compress-Archive -Path 'releases\*.zip', 'releases\install_idt.bat', 'releases\README.md' -DestinationPath 'releases\idt2.zip' -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create master package idt2.zip!
    echo Individual packages are still available in releases\ directory.
    exit /b 1
)

echo.
echo Master package created successfully: releases\idt2.zip
echo.

REM ============================================================================
echo.
echo ========================================================================
echo RELEASE COMPLETE!
echo ========================================================================
echo.
echo All distribution packages have been created successfully.
echo.
echo Individual packages in releases\ directory:
echo.
dir /b releases\*.zip 2>nul | findstr /V "idt2.zip"
echo.
echo Master package (contains all individual packages above):
echo   idt2.zip
echo.
echo ========================================================================
echo NEXT STEPS
echo ========================================================================
echo.
echo 1. Test the distribution packages:
echo    - Extract each ZIP and test the executables
echo    - Verify README files are correct
echo.
echo 2. Create GitHub Release:
echo    - Tag version: v[VERSION]
echo    - Upload idt2.zip (master package) OR individual ZIPs from releases\
echo    - Add release notes
echo.
echo 3. Update documentation:
echo    - Update CHANGELOG.md
echo    - Update version references
echo.
echo Release directory: %CD%\releases
echo.
