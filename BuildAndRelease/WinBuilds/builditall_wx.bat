@echo off
REM ============================================================================
REM Build All wxPython Applications for Windows
REM ============================================================================
REM This script builds both wxPython-based applications:
REM   1. IDT (CLI - no GUI framework)
REM   2. ImageDescriber (wxPython - includes integrated Viewer Mode, PromptEditor, and IDTConfigure)
REM
REM NOTE: Uses .winenv virtual environments (created by winsetup.bat)
REM       This allows .venv (macOS) and .winenv (Windows) to coexist
REM ============================================================================

echo.
echo ========================================================================
echo BUILD ALL wxPython APPLICATIONS (Windows)
echo ========================================================================
echo This script builds IDT and ImageDescriber.
echo Viewer is now integrated into ImageDescriber (Viewer Mode).
echo.

REM Save current directory (should be BuildAndRelease\WinBuilds)
set "ORIGINAL_DIR=%CD%"

cd /d "%~dp0..\.."

set BUILD_ERRORS=0

REM ============================================================================
REM BUILD IN PARALLEL - Both apps are independent, run simultaneously
REM ============================================================================
echo Building IDT and ImageDescriber in parallel...
echo ========================================================================
echo.

REM Use temp files to capture exit codes from background processes
set "IDT_STATUS_FILE=%TEMP%\idt_build_status_%RANDOM%.txt"
set "IMAGEDESC_STATUS_FILE=%TEMP%\imagedesc_build_status_%RANDOM%.txt"
set "IDT_LOG=%TEMP%\idt_build_%RANDOM%.log"
set "IMAGEDESC_LOG=%TEMP%\imagedesc_build_%RANDOM%.log"

REM Start IDT build in background
start /B cmd /C "cd /d "%CD%\idt" && call build_idt.bat > "%IDT_LOG%" 2>&1 && echo 0 > "%IDT_STATUS_FILE%" || echo 1 > "%IDT_STATUS_FILE%""

REM Start ImageDescriber build in background
start /B cmd /C "cd /d "%CD%\imagedescriber" && call build_imagedescriber_wx.bat > "%IMAGEDESC_LOG%" 2>&1 && echo 0 > "%IMAGEDESC_STATUS_FILE%" || echo 1 > "%IMAGEDESC_STATUS_FILE%""

REM Wait for both status files to appear (poll every 5 seconds)
echo Waiting for both builds to complete...
:WAIT_LOOP
timeout /t 5 /nobreak >nul
if not exist "%IDT_STATUS_FILE%" goto WAIT_LOOP
if not exist "%IMAGEDESC_STATUS_FILE%" goto WAIT_LOOP

REM Show IDT output
echo.
echo ========================================================================
echo IDT BUILD OUTPUT
echo ========================================================================
type "%IDT_LOG%"
del /Q "%IDT_LOG%" 2>nul

REM Show ImageDescriber output
echo.
echo ========================================================================
echo IMAGEDESCRIBER BUILD OUTPUT
echo ========================================================================
type "%IMAGEDESC_LOG%"
del /Q "%IMAGEDESC_LOG%" 2>nul

REM Check results
echo.
echo ========================================================================
set /P IDT_RESULT=<"%IDT_STATUS_FILE%"
set /P IMAGEDESC_RESULT=<"%IMAGEDESC_STATUS_FILE%"
del /Q "%IDT_STATUS_FILE%" 2>nul
del /Q "%IMAGEDESC_STATUS_FILE%" 2>nul

REM Trim whitespace from results
for /f "tokens=* delims= " %%a in ("%IDT_RESULT%") do set IDT_RESULT=%%a
for /f "tokens=* delims= " %%a in ("%IMAGEDESC_RESULT%") do set IMAGEDESC_RESULT=%%a

if "%IDT_RESULT%"=="0" (
    echo SUCCESS: IDT built successfully
) else (
    echo ERROR: IDT build failed!
    set /a BUILD_ERRORS+=1
)
if "%IMAGEDESC_RESULT%"=="0" (
    echo SUCCESS: ImageDescriber built successfully
) else (
    echo ERROR: ImageDescriber build failed!
    set /a BUILD_ERRORS+=1
)

REM ============================================================================
echo.
echo ========================================================================
echo BUILD SUMMARY
echo ========================================================================
echo.

if "%BUILD_ERRORS%"=="0" (
    echo SUCCESS: All wxPython applications built successfully!
    echo.
    
    REM ========================================================================
    echo ========================================================================
    echo PACKAGING ALL APPLICATIONS
    echo ========================================================================
    echo.
    
    REM Create distribution directory in BuildAndRelease\WinBuilds
    if not exist "BuildAndRelease\WinBuilds\dist_all" mkdir BuildAndRelease\WinBuilds\dist_all
    if not exist "BuildAndRelease\WinBuilds\dist_all\bin" mkdir BuildAndRelease\WinBuilds\dist_all\bin
    
    REM Clean old files
    echo Cleaning old package...
    del /Q BuildAndRelease\WinBuilds\dist_all\bin\*.exe 2>nul
    del /Q BuildAndRelease\WinBuilds\dist_all\*.md 2>nul
    del /Q BuildAndRelease\WinBuilds\dist_all\*.txt 2>nul
    
    echo Packaging applications...
    echo.
    
    REM Copy IDT CLI
    if exist "idt\dist\idt.exe" (
        copy /Y "idt\dist\idt.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ idt.exe
    ) else (
        echo   ✗ idt.exe NOT FOUND
    )
    
    REM Copy ImageDescriber (includes Viewer Mode, PromptEditor and IDTConfigure)
    if exist "imagedescriber\dist\ImageDescriber.exe" (
        copy /Y "imagedescriber\dist\ImageDescriber.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ ImageDescriber.exe (with integrated Viewer Mode and tools)
    ) else (
        echo   ✗ ImageDescriber.exe NOT FOUND
    )
    
    REM Copy documentation
    echo.
    echo Copying documentation...
    if exist "README.md" copy /Y "README.md" "BuildAndRelease\WinBuilds\dist_all\" >nul
    if exist "LICENSE" copy /Y "LICENSE" "BuildAndRelease\WinBuilds\dist_all\" >nul
    
    echo.
    echo ========================================================================
    echo PACKAGING COMPLETE
    echo ========================================================================
    echo.
    echo All applications packaged in: BuildAndRelease\WinBuilds\dist_all\bin\
    echo.
    echo Ready for distribution or installer creation.
    echo.
    echo Next step: Run build_installer.bat to create Windows installer
    
    REM Return to original directory
    cd /d "%ORIGINAL_DIR%"
    exit /b 0
) else (
    echo ERRORS: %BUILD_ERRORS% build failures encountered
    echo.
    echo If .winenv errors, run: winsetup.bat
    
    REM Return to original directory
    cd /d "%ORIGINAL_DIR%"
    exit /b 1
)
