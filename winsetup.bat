@echo off
REM ============================================================================
REM Windows Environment Setup for Image Description Toolkit
REM ============================================================================
REM Creates separate Windows virtual environments (.winenv) for each GUI app
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
echo   - Viewer
echo   - ImageDescriber
echo   - Prompt Editor
echo   - IDTConfigure
echo.
pause

set SETUP_ERRORS=0

REM ============================================================================
echo.
echo [1/4] Setting up Viewer...
echo ========================================================================
echo.

cd viewer
if exist ".winenv" (
    echo Removing old .winenv...
    rmdir /s /q .winenv
)

echo Creating virtual environment...
python -m venv .winenv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment for Viewer
    set /a SETUP_ERRORS+=1
    cd ..
    goto :imagedescriber
)

echo Installing dependencies...
call .winenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies for Viewer
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: Viewer setup complete
)
call deactivate
cd ..

REM ============================================================================
:imagedescriber
echo.
echo [2/4] Setting up ImageDescriber...
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
    goto :prompteditor
)

echo Installing dependencies...
call .winenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies for ImageDescriber
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: ImageDescriber setup complete
)
call deactivate
cd ..

REM ============================================================================
:prompteditor
echo.
echo [3/4] Setting up Prompt Editor...
echo ========================================================================
echo.

cd prompt_editor
if exist ".winenv" (
    echo Removing old .winenv...
    rmdir /s /q .winenv
)

echo Creating virtual environment...
python -m venv .winenv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment for Prompt Editor
    set /a SETUP_ERRORS+=1
    cd ..
    goto :idtconfigure
)

echo Installing dependencies...
call .winenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies for Prompt Editor
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: Prompt Editor setup complete
)
call deactivate
cd ..

REM ============================================================================
:idtconfigure
echo.
echo [4/4] Setting up IDTConfigure...
echo ========================================================================
echo.

cd idtconfigure
if exist ".winenv" (
    echo Removing old .winenv...
    rmdir /s /q .winenv
)

echo Creating virtual environment...
python -m venv .winenv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment for IDTConfigure
    set /a SETUP_ERRORS+=1
    cd ..
    goto :summary
)

echo Installing dependencies...
call .winenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies for IDTConfigure
    set /a SETUP_ERRORS+=1
) else (
    echo SUCCESS: IDTConfigure setup complete
)
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
    echo   - viewer\.winenv
    echo   - imagedescriber\.winenv
    echo   - prompt_editor\.winenv
    echo   - idtconfigure\.winenv
    echo.
    echo Next steps:
    echo   1. Build all applications: BuildAndRelease\builditall_wx.bat
    echo   2. Package executables: BuildAndRelease\package_all_windows.bat
    echo   3. Create installer: BuildAndRelease\build_installer.bat
    echo.
) else (
    echo ERRORS: %SETUP_ERRORS% setup failures encountered
    echo Please review the errors above and try again.
    echo.
)

echo NOTE: These .winenv directories are separate from macOS .venv directories.
echo Both can coexist in the same project directory.
echo.

pause
exit /b %SETUP_ERRORS%
