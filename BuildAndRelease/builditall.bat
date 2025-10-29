@echo off
REM ============================================================================
REM Build All Applications - Master Build Script
REM ============================================================================
REM This script builds all five applications in the Image Description Toolkit:
REM   1. IDT (main command-line toolkit)
REM   2. Viewer (image description viewer GUI)
REM   3. Prompt Editor (prompt configuration GUI)
REM   4. ImageDescriber (batch processing GUI)
REM   5. IDTConfigure (configuration management GUI)
REM
REM Prerequisites:
REM   - Virtual environment set up for each GUI app (viewer, prompt_editor, imagedescriber, idtconfigure)
REM   - Main IDT dependencies installed in root .venv or system Python
REM
REM Output:
REM   - dist/idt.exe
REM   - viewer/dist/viewer_<arch>.exe
REM   - prompt_editor/dist/prompt_editor_<arch>.exe
REM   - imagedescriber/dist/ImageDescriber_<arch>.exe
REM   - idtconfigure/dist/idtconfigure_<arch>.exe
REM ============================================================================

echo.
echo ========================================================================
echo BUILD ALL APPLICATIONS
echo ========================================================================
echo.
REM Show composed build version and commit before starting
echo --- Build Version Banner (pre-build) ---
python idt_cli.py version
echo ----------------------------------------
echo.

REM Pre-build validation: Check spec file completeness
echo.
echo [Pre-Build Check] Verifying PyInstaller spec file...
python BuildAndRelease\check_spec_completeness.py
if errorlevel 1 (
    echo.
    echo ERROR: Spec file is incomplete! Fix the issues above before building.
    echo.
    pause
    exit /b 1
)
echo.
echo This will build all five applications:
echo   1. IDT (main toolkit)
echo   2. Viewer
echo   3. Prompt Editor
echo   4. ImageDescriber
echo   5. IDTConfigure
echo.
echo Make sure all virtual environments are set up before continuing.
echo.

REM Change to project root directory
cd /d "%~dp0.."

set BUILD_ERRORS=0

REM ============================================================================
echo.
echo [1/4] Building IDT (main toolkit)...
echo ========================================================================
echo.

call BuildAndRelease\build_idt.bat
if errorlevel 1 (
    echo ERROR: IDT build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: IDT built successfully
)

REM ============================================================================
echo.
echo [2/4] Building Viewer...
echo ========================================================================
echo.

cd viewer
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_viewer.bat
    if errorlevel 1 (
        echo ERROR: Viewer build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: Viewer built successfully
    )
    call deactivate
) else (
    echo ERROR: Viewer virtual environment not found at viewer\.venv
    echo Please run: cd viewer ^&^& python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo [3/4] Building Prompt Editor...
echo ========================================================================
echo.

cd prompt_editor
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_prompt_editor.bat
    if errorlevel 1 (
        echo ERROR: Prompt Editor build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: Prompt Editor built successfully
    )
    call deactivate
) else (
    echo ERROR: Prompt Editor virtual environment not found at prompt_editor\.venv
    echo Please run: cd prompt_editor ^&^& python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo [4/4] Building ImageDescriber...
echo ========================================================================
echo.

cd imagedescriber
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_imagedescriber.bat
    if errorlevel 1 (
        echo ERROR: ImageDescriber build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: ImageDescriber built successfully
    )
    call deactivate
) else (
    echo ERROR: ImageDescriber virtual environment not found at imagedescriber\.venv
    echo Please run: cd imagedescriber ^&^& python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo [5/5] Building IDTConfigure...
echo ========================================================================
echo.

cd idtconfigure
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    call build_idtconfigure.bat
    if errorlevel 1 (
        echo ERROR: IDTConfigure build failed!
        set /a BUILD_ERRORS+=1
    ) else (
        echo SUCCESS: IDTConfigure built successfully
    )
    call deactivate
) else (
    echo ERROR: IDTConfigure virtual environment not found at idtconfigure\.venv
    echo Please run: cd idtconfigure ^&^& python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    set /a BUILD_ERRORS+=1
)
cd ..

REM ============================================================================
echo.
echo ========================================================================
echo BUILD SUMMARY
echo ========================================================================
echo.

echo BUILD COMPLETE
if "%BUILD_ERRORS%"=="0" (
    echo SUCCESS: All applications built successfully
) else (
    echo ERRORS: %BUILD_ERRORS% build failures encountered
)

REM Show version from built CLI if available
if exist "dist\idt.exe" (
    echo.
    echo --- Built Executable Version ---
    dist\idt.exe version
    echo --------------------------------
)

REM Post-build validation: Test the built executable
if exist "dist\idt.exe" (
    echo.
    echo [Post-Build Check] Validating built executable...
    python BuildAndRelease\validate_build.py
    if errorlevel 1 (
        echo.
        echo WARNING: Build validation found issues!
        echo The executable may not work correctly in production.
        echo Review the errors above and rebuild after fixing.
        echo.
        set /a BUILD_ERRORS+=1
    )
)

echo.

if "%BUILD_ERRORS%"=="0" (
    exit /b 0
) else (
    echo.
    echo Build completed with %BUILD_ERRORS% error(s).
    exit /b 1
)
