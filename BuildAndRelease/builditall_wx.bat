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
REM ============================================================================

echo.
echo ========================================================================
echo BUILD ALL wxPython APPLICATIONS (Windows)
echo ========================================================================
echo.

cd /d "%~dp0.."

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
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_viewer_wx.bat
    if errorlevel 1 (
        echo ERROR: Viewer build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: Viewer built successfully
    )
    call deactivate
) else (
    echo ERROR: Viewer virtual environment not found
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo [3/5] Building Prompt Editor (wxPython)...
echo ========================================================================
echo.

cd prompt_editor
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_prompt_editor_wx.bat
    if errorlevel 1 (
        echo ERROR: Prompt Editor build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: Prompt Editor built successfully
    )
    call deactivate
) else (
    echo ERROR: Prompt Editor virtual environment not found
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo [4/5] Building ImageDescriber (wxPython)...
echo ========================================================================
echo.

cd imagedescriber
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_imagedescriber_wx.bat
    if errorlevel 1 (
        echo ERROR: ImageDescriber build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: ImageDescriber built successfully
    )
    call deactivate
) else (
    echo ERROR: ImageDescriber virtual environment not found
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo [5/5] Building IDTConfigure (wxPython)...
echo ========================================================================
echo.

cd idtconfigure
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_idtconfigure_wx.bat
    if errorlevel 1 (
        echo ERROR: IDTConfigure build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: IDTConfigure built successfully
    )
    call deactivate
) else (
    echo ERROR: IDTConfigure virtual environment not found
    set /a BUILD_ERRORS+=1
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
    echo Output locations:
    echo   - idt\dist\idt.exe
    echo   - viewer\dist\Viewer.exe
    echo   - prompt_editor\dist\PromptEditor.exe
    echo   - imagedescriber\dist\ImageDescriber.exe
    echo   - idtconfigure\dist\IDTConfigure.exe
    echo.
    echo Next step: Run package_all_windows.bat to collect all executables
    exit /b 0
) else (
    echo ERRORS: %BUILD_ERRORS% build failures encountered
    exit /b 1
)
