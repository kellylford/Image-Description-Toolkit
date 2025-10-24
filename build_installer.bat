@echo off
REM Build Inno Setup Installer for Image Description Toolkit
REM This script compiles the installer.iss file into a Windows installer

echo ================================================
echo Building Image Description Toolkit Installer
echo ================================================
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

REM Check if required files exist
if not exist "releases\ImageDescriptionToolkit_v3.0.1.zip" (
    echo ERROR: ImageDescriptionToolkit_v3.0.1.zip not found in releases\
    echo Please run packageitall.bat first to create release packages.
    pause
    exit /b 1
)

if not exist "releases\viewer_v3.0.1.zip" (
    echo ERROR: viewer_v3.0.1.zip not found in releases\
    pause
    exit /b 1
)

if not exist "releases\imagedescriber_v3.0.1.zip" (
    echo ERROR: imagedescriber_v3.0.1.zip not found in releases\
    pause
    exit /b 1
)

if not exist "releases\prompt_editor_v3.0.1.zip" (
    echo ERROR: prompt_editor_v3.0.1.zip not found in releases\
    pause
    exit /b 1
)

echo All required files found.
echo.
echo Compiling installer...
"%INNO_PATH%" installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo SUCCESS: Installer created successfully!
    echo ================================================
    echo.
    echo Output: releases\ImageDescriptionToolkit_Setup_v3.0.1.exe
    echo.
) else (
    echo.
    echo ERROR: Installer compilation failed!
    echo.
    pause
    exit /b 1
)

pause
