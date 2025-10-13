@echo off
REM ============================================================================
REM Release All Applications - Complete Build and Package
REM ============================================================================
REM This master script does everything needed for a complete release:
REM   1. Builds all four applications (builditall.bat)
REM   2. Packages all four applications (packageitall.bat)
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
REM ============================================================================

echo.
echo ========================================================================
echo COMPLETE RELEASE BUILD
echo ========================================================================
echo.
echo This will build and package all four applications:
echo   1. IDT (main toolkit)
echo   2. Viewer
echo   3. Prompt Editor
echo   4. ImageDescriber
echo.
echo All distribution packages will be created in releases/ directory.
echo.
echo Starting release process...
echo.

REM ============================================================================
echo ========================================================================
echo PHASE 1: BUILD ALL APPLICATIONS
echo ========================================================================
echo.

call builditall.bat
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

call packageitall.bat
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
echo RELEASE COMPLETE!
echo ========================================================================
echo.
echo All distribution packages have been created successfully.
echo.
echo Packages in releases\ directory:
echo.
dir /b releases\*.zip 2>nul
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
echo    - Upload all ZIP files from releases\
echo    - Add release notes
echo.
echo 3. Update documentation:
echo    - Update CHANGELOG.md
echo    - Update version references
echo.
echo Release directory: %CD%\releases
echo.
