@echo off
REM Complete Release Build Script
REM Builds all executables and creates the installer

echo ================================================
echo Image Description Toolkit - Complete Build
echo ================================================
echo.

REM Step 1: Build all executables
echo [1/3] Building executables...
call builditall.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Step 2: Package into zip files
echo.
echo [2/3] Creating release packages...
call packageitall.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Packaging failed!
    pause
    exit /b 1
)

REM Step 3: Build installer
echo.
echo [3/3] Building Windows installer...
call build_installer.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Installer build failed!
    pause
    exit /b 1
)

echo.
echo ================================================
echo SUCCESS: Complete release build finished!
echo ================================================
echo.
echo Output files:
echo   - releases\ImageDescriptionToolkit_Setup_v3.0.1.exe (Windows Installer)
echo   - releases\ImageDescriptionToolkit_v3.0.1.zip (Standalone)
echo   - releases\viewer_v3.0.1.zip
echo   - releases\imagedescriber_v3.0.1.zip
echo   - releases\prompt_editor_v3.0.1.zip
echo.
pause
