@echo off
REM ============================================================================
REM Build All wxPython Applications for Windows
REM ============================================================================
REM This script builds all five wxPython-based applications:
REM   1. IDT (CLI - no GUI framework)
REM   2. Viewer (wxPython)
REM   3. Prompt Editor (wxPython)
REM   4. ImageDescriber (wxPython)
REM   5. IDTConfigure (wxPython)
REM
REM NOTE: Uses .winenv virtual environments (created by winsetup.bat)
REM       This allows .venv (macOS) and .winenv (Windows) to coexist
REM ============================================================================

echo.
echo ========================================================================
echo BUILD ALL wxPython APPLICATIONS (Windows)
echo ========================================================================
echo.

cd /d "%~dp0..\.."

set BUILD_ERRORS=0

REM ============================================================================
echo [1/5] Building IDT (CLI)...
echo ========================================================================
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
echo.
echo [2/5] Building Viewer (wxPython)...
echo ========================================================================
echo.

cd viewer
call build_viewer_wx.bat
if errorlevel 1 (
    echo ERROR: Viewer build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: Viewer built successfully
)
cd ..

REM ============================================================================
echo.
echo [3/5] Building Prompt Editor (wxPython)...
echo ========================================================================
echo.

cd prompt_editor
call build_prompt_editor.bat
if errorlevel 1 (
    echo ERROR: Prompt Editor build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: Prompt Editor built successfully
)
cd ..

REM ============================================================================
echo.
echo [4/5] Building ImageDescriber (wxPython)...
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
echo.
echo [5/5] Building IDTConfigure (wxPython)...
echo ========================================================================
echo.

cd idtconfigure
call build_idtconfigure.bat
if errorlevel 1 (
    echo ERROR: IDTConfigure build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: IDTConfigure built successfully
)
cd ..

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
    
    REM Copy Viewer
    if exist "viewer\dist\Viewer.exe" (
        copy /Y "viewer\dist\Viewer.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ Viewer.exe
    ) else (
        echo   ✗ Viewer.exe NOT FOUND
    )
    
    REM Copy Prompt Editor
    if exist "prompt_editor\dist\PromptEditor.exe" (
        copy /Y "prompt_editor\dist\PromptEditor.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ PromptEditor.exe
    ) else (
        echo   ✗ PromptEditor.exe NOT FOUND
    )
    
    REM Copy ImageDescriber
    if exist "imagedescriber\dist\ImageDescriber.exe" (
        copy /Y "imagedescriber\dist\ImageDescriber.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ ImageDescriber.exe
    ) else (
        echo   ✗ ImageDescriber.exe NOT FOUND
    )
    
    REM Copy IDTConfigure
    if exist "idtconfigure\dist\IDTConfigure.exe" (
        copy /Y "idtconfigure\dist\IDTConfigure.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
        echo   ✓ IDTConfigure.exe
    ) else (
        echo   ✗ IDTConfigure.exe NOT FOUND
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
    exit /b 0
) else (
    echo ERRORS: %BUILD_ERRORS% build failures encountered
    echo.
    echo If .winenv errors, run: winsetup.bat
    exit /b 1
)
