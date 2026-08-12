@echo off
echo ========================================================================
echo Building IDT Chat for Windows
echo ========================================================================
echo.

REM Auto-activate .winenv if not already in a virtual environment
if not defined VIRTUAL_ENV (
    if exist "..\imagedescriber\.winenv\Scripts\activate.bat" (
        echo Activating imagedescriber\.winenv...
        call ..\imagedescriber\.winenv\Scripts\activate.bat
    ) else (
        echo WARNING: .winenv not found. Run winsetup.bat first.
        echo Proceeding with system Python...
    )
)
echo.

REM Clean PyInstaller cache for fresh build
echo Cleaning PyInstaller cache...
python -c "import shutil; from pathlib import Path; cache_dir = Path.home() / 'AppData' / 'Local' / 'pyinstaller'; shutil.rmtree(cache_dir, ignore_errors=True); print(f'Cleaned: {cache_dir}')"
echo.

REM ----------------------------------------------------------------------------
REM Dependency checks are deliberately flat, matching
REM build_imagedescriber_wx.bat. cmd discards the exit code of an "exit /b N"
REM issued from a block nested inside another block, so a nested guard would
REM print its error and still report success to builditall_wx.bat. Enforced by
REM pytest_tests/unit/test_batch_script_syntax.py.
REM ----------------------------------------------------------------------------

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if not errorlevel 1 goto :have_pyinstaller
echo PyInstaller not found. Installing...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller.
    exit /b 1
)
echo.
:have_pyinstaller

REM Check if wxPython is installed
python -c "import wx" 2>nul
if not errorlevel 1 goto :have_wxpython
echo wxPython not found. Installing dependencies...
pip install -r ..\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)
echo.
:have_wxpython

REM Create output directory
if not exist "dist" mkdir dist

REM Verify the engine the app is built on is importable before spending
REM minutes in PyInstaller.
python -c "import sys; sys.path.insert(0, '..'); import idt_core.chat" 2>nul
if not errorlevel 1 goto :have_engine
echo ERROR: idt_core.chat is not importable from the project root.
echo IDT Chat cannot be built without the chat engine.
exit /b 1
:have_engine

echo Chat engine found.
echo Building IDT Chat...
echo.

REM Build using the spec file
pyinstaller chatapp.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ========================================================================
    echo BUILD FAILED
    echo ========================================================================
    exit /b 1
)

if not exist "dist\IDTChat.exe" (
    echo.
    echo ERROR: PyInstaller reported success but dist\IDTChat.exe is missing.
    exit /b 1
)

echo.
echo ========================================================================
echo BUILD SUCCESSFUL
echo ========================================================================
echo Executable created: dist\IDTChat.exe
echo.
