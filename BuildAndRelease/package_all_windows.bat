@echo off
REM ============================================================================
REM Package all Windows executables for installer
REM ============================================================================
REM This script collects built executables into dist_all/bin/ for Inno Setup
REM
REM Prerequisites:
REM   - Run builditall_wx.bat first to build all executables
REM ============================================================================

echo ================================================
echo Packaging Windows Executables
echo ================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Create dist_all/bin directory
if not exist "dist_all\bin" (
    echo Creating dist_all\bin directory...
    mkdir "dist_all\bin"
)

REM Copy idt.exe
if exist "..\..\idt\dist\idt.exe" (
    echo Copying idt.exe...
    copy /Y "..\..\idt\dist\idt.exe" "dist_all\bin\"
) else (
    echo ERROR: idt.exe not found at ..\..\idt\dist\idt.exe
    echo Run builditall_wx.bat first
    exit /b 1
)

REM Copy ImageDescriber.exe
if exist "..\..\imagedescriber\dist\ImageDescriber.exe" (
    echo Copying ImageDescriber.exe...
    copy /Y "..\..\imagedescriber\dist\ImageDescriber.exe" "dist_all\bin\"
) else (
    echo ERROR: ImageDescriber.exe not found at ..\..\imagedescriber\dist\ImageDescriber.exe
    echo Run builditall_wx.bat first
    exit /b 1
)

echo.
echo ================================================
echo Packaging complete!
echo ================================================
echo.
echo Files copied to: dist_all\bin\
dir dist_all\bin\
echo.
exit /b 0
