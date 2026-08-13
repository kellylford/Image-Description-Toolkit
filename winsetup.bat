@echo off
REM ============================================================================
REM Windows Environment Setup for Image Description Toolkit
REM ============================================================================
REM Creates Windows virtual environments (.winenv): one for the CLI, one shared
REM by the two wxPython apps (ImageDescriber and IDT Chat).
REM This allows using the same directory for both macOS (.venv) and Windows (.winenv)
REM
REM Run this on Windows to set up all GUI applications
REM ============================================================================

echo.
echo ========================================================================
echo Windows Environment Setup for Image Description Toolkit
echo ========================================================================
echo.
echo This will create .winenv directories for each GUI application and
echo install all required dependencies.
echo.
echo Applications to set up:
echo   - IDT (CLI)
echo   - ImageDescriber (with integrated Viewer Mode, prompt editor, and configuration manager)
echo   - IDT Chat (shares ImageDescriber's environment - see note below)
echo.
echo IDT Chat gets no .winenv of its own: its requirements are a strict subset
echo of ImageDescriber's, and chatapp\build_chatapp.bat activates
echo imagedescriber\.winenv directly. A third environment would mean a second
echo wxPython download for no benefit.
echo.
pause

set SETUP_ERRORS=0
REM Initialised explicitly: this script does not setlocal, so a stale
REM FAILED_APPS from the parent shell would otherwise be reported as a failure.
set "FAILED_APPS="

REM ============================================================================
echo.
echo [1/2] Setting up IDT (CLI)...
echo ========================================================================
echo.

cd idt
if exist ".winenv" (
    echo Removing old .winenv...
    rmdir /s /q .winenv
)

echo Creating virtual environment...
python -m venv .winenv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment for IDT
    set /a SETUP_ERRORS+=1
    cd ..
    goto :imagedescriber
)

echo Installing dependencies...
call .winenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :idt_failed

REM pip's exit code alone is not proof the environment is usable, and by the
REM time this scrolls past nobody is reading it. Verify the import the build
REM actually needs. On 2026-08-13 an imagedescriber\.winenv containing nothing
REM but pip -- a failed install from months earlier -- looked like a completed
REM setup and cost a full debugging session.
python -c "import PyInstaller" 2>nul
if errorlevel 1 goto :idt_verify_failed
echo SUCCESS: IDT setup complete
goto :idt_done

:idt_verify_failed
echo ERROR: IDT dependencies installed but PyInstaller is not importable
set /a SETUP_ERRORS+=1
set "FAILED_APPS=%FAILED_APPS% IDT"
goto :idt_done

:idt_failed
echo ERROR: Failed to install dependencies for IDT
set /a SETUP_ERRORS+=1
set "FAILED_APPS=%FAILED_APPS% IDT"

:idt_done
call deactivate
cd ..

REM ============================================================================
:imagedescriber
echo.
echo [2/2] Setting up ImageDescriber...
echo ========================================================================
echo.

cd imagedescriber
if exist ".winenv" (
    echo Removing old .winenv...
    rmdir /s /q .winenv
)

echo Creating virtual environment...
python -m venv .winenv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment for ImageDescriber
    set /a SETUP_ERRORS+=1
    cd ..
    goto :summary
)

echo Installing dependencies...
call .winenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :describer_failed

REM This environment builds BOTH ImageDescriber and IDT Chat, so a silent
REM failure here takes out two apps. wxPython is the one that actually breaks:
REM it is the large wheel most likely to fail, and every downstream build error
REM blames something else. See the note above.
python -c "import wx" 2>nul
if errorlevel 1 goto :describer_verify_failed
python -c "import PyInstaller" 2>nul
if errorlevel 1 goto :describer_verify_failed
echo SUCCESS: ImageDescriber setup complete (IDT Chat uses this environment too)
goto :describer_done

:describer_verify_failed
echo ERROR: ImageDescriber dependencies installed but wxPython or PyInstaller
echo        is not importable. ImageDescriber AND IDT Chat cannot be built.
set /a SETUP_ERRORS+=1
set "FAILED_APPS=%FAILED_APPS% ImageDescriber+IDTChat"
goto :describer_done

:describer_failed
echo ERROR: Failed to install dependencies for ImageDescriber
set /a SETUP_ERRORS+=1
set "FAILED_APPS=%FAILED_APPS% ImageDescriber+IDTChat"

:describer_done
call deactivate
cd ..

REM ============================================================================
:summary
echo.
echo ========================================================================
echo SETUP SUMMARY
echo ========================================================================
echo.

if "%SETUP_ERRORS%"=="0" (
    echo SUCCESS: All Windows environments set up successfully!
    echo.
    echo Virtual environments created:
    echo   - idt\.winenv                ^(IDT CLI^)
    echo   - imagedescriber\.winenv     ^(ImageDescriber AND IDT Chat^)
    echo.
    echo Next steps:
    echo   1. Build all applications: BuildAndRelease\WinBuilds\builditall_wx.bat
    echo   2. Package executables: BuildAndRelease\WinBuilds\package_all_windows.bat
    echo   3. Create installer: BuildAndRelease\WinBuilds\build_installer.bat
    echo.
) else (
    echo ERRORS: %SETUP_ERRORS% setup failure^(s^) encountered
    echo.
    echo FAILED:%FAILED_APPS%
    echo.
    echo Setup is NOT complete. Do not run builditall_wx.bat yet -- it will
    echo fail later and blame the build rather than this step.
    echo.
    echo Scroll up to the pip output for the app named above to see why.
    echo Common causes: no internet, a proxy blocking PyPI, or no matching
    echo wxPython wheel for this Python version.
    echo.
)

echo NOTE: These .winenv directories are separate from macOS .venv directories.
echo Both can coexist in the same project directory.
echo.

pause
exit /b %SETUP_ERRORS%
