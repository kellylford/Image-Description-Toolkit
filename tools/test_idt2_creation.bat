@echo off
REM Test script for Phase 3 of releaseitall.bat
echo Testing master package creation...
echo.

REM Check if we have any packages to bundle
if not exist releases\*.zip (
    echo ERROR: No distribution packages found in releases\ directory!
    pause
    exit /b 1
)

echo Found packages in releases\ directory:
dir /b releases\*.zip 2>nul | findstr /V "idt2.zip"
echo.

echo Creating master package idt2.zip with all distribution packages...
echo.

REM Delete existing idt2.zip if it exists
if exist releases\idt2.zip (
    echo Removing existing idt2.zip...
    del releases\idt2.zip
)

REM Create idt2.zip containing all individual distribution packages
echo Running PowerShell command...
powershell -NoProfile -Command "Compress-Archive -Path 'releases\*.zip' -DestinationPath 'releases\idt2.zip' -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create master package idt2.zip!
    echo PowerShell command failed.
    pause
    exit /b 1
)

echo.
echo SUCCESS: Master package created successfully: releases\idt2.zip
echo.

echo Verifying contents...
powershell -Command "Get-ChildItem -Path 'releases\idt2.zip' | ForEach-Object { Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::OpenRead(\$_.FullName).Entries | Select-Object Name, Length }"

echo.
echo Test complete!
pause