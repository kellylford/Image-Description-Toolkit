@echo off
REM ============================================================================
REM Build All wxPython Applications for Windows
REM ============================================================================
REM This script builds all three wxPython-based applications:
REM   1. IDT (CLI - no GUI framework)
REM   2. Viewer (wxPython)
REM   3. ImageDescriber (wxPython - includes integrated PromptEditor and IDTConfigure)
REM
REM NOTE: Uses .winenv virtual environments (created by winsetup.bat)
REM       This allows .venv (macOS) and .winenv (Windows) to coexist
REM
REM DEPRECATED (now part of ImageDescriber):
REM   - Prompt Editor (wxPython) - Tools → Edit Prompts
REM   - IDTConfigure (wxPython) - Tools → Configure Settings
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
echo [1/2] Building IDT (CLI)...
echo ========================================================================
echo.
echo.

cd idt
call build_idt.bat
if errorlevel 1 (
    echo ERROR: IDT build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: IDT built successfully
)
cd ..

REM ============================================================================
REM [DEPRECATED 2/2] Viewer (wxPython) - now integrated into ImageDescriber
REM Access via: Viewer Mode tab in ImageDescriber
REM ============================================================================
REM echo.
REM echo [2/2] Building Viewer (wxPython)...
REM echo ========================================================================
REM echo.
REM cd viewer
REM call build_viewer_wx.bat
REM if errorlevel 1 (
REM     echo ERROR: Viewer build failed!
REM     set /a BUILD_ERRORS+=1
REM ) else (
REM     echo SUCCESS: Viewer built successfully
REM )
REM cd ..

REM ============================================================================
echo.
echo [2/2] Building ImageDescriber (wxPython - includes Viewer Mode + PromptEditor + IDTConfigure)...
echo ========================================================================
echo.

cd imagedescriber
call build_imagedescriber_wx.bat
if errorlevel 1 (
    echo ERROR: ImageDescriber build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: ImageDescriber built successfully
)
cd ..

REM ============================================================================
REM [DEPRECATED 5/5] IDTConfigure (wxPython) - now integrated into ImageDescriber
REM Access via: Tools → Configure Settings in ImageDescriber
REM ============================================================================
REM echo.
REM echo [5/5] Building IDTConfigure (wxPython)...
REM echo ========================================================================
REM echo.
REM cd idtconfigure
REM call build_idtconfigure.bat
REM if errorlevel 1 (
REM     echo ERROR: IDTConfigure build failed!
REM     set /a BUILD_ERRORS+=1
REM ) else (
REM     echo SUCCESS: IDTConfigure built successfully
REM )
REM cd ..

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
    
    REM [DEPRECATED] Viewer - now integrated into ImageDescriber as Viewer Mode
    REM if exist "viewer\dist\Viewer.exe" (
    REM     copy /Y "viewer\dist\Viewer.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
    REM     echo   ✓ Viewer.exe
    REM ) else (
    REM     echo   ✗ Viewer.exe NOT FOUND
    REM )
    
    REM [DEPRECATED] Prompt Editor - now part of ImageDescriber Tools menu
    REM if exist "prompt_editor\dist\PromptEditor.exe" (
    REM     copy /Y "prompt_editor\dist\PromptEditor.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
    REM     echo   ✓ PromptEditor.exe
    REM ) else (
    REM     echo   ✗ PromptEditor.exe NOT FOUND
    REM )
    
    REM Copy ImageDescriber (includes Viewer Mode, PromptEditor and IDTConfigure)
    if exist "imagedescriber\dist\ImageDescriber.exe" (
        copy /Y "imagedescriber\dist\ImageDescriber.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ ImageDescriber.exe (with integrated Viewer Mode and tools)
    ) else (
        echo   ✗ ImageDescriber.exe NOT FOUND
    )
    
    REM [DEPRECATED] IDTConfigure - now part of ImageDescriber Tools menu
    REM if exist "idtconfigure\dist\IDTConfigure.exe" (
    REM     copy /Y "idtconfigure\dist\IDTConfigure.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
    REM     echo   ✓ IDTConfigure.exe
    REM ) else (
    REM     echo   ✗ IDTConfigure.exe NOT FOUND
    REM )
    
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
