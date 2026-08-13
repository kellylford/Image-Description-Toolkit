@echo off
REM Build IDT CLI for Windows
REM Run this from the idt directory

echo Building IDT CLI...
echo.

REM Activate this app's own .winenv (skipped gracefully when not present, e.g. CI).
REM
REM Deliberately NOT guarded by "if not defined VIRTUAL_ENV". builditall_wx.bat
REM runs all three sub-builds in one cmd session and none of them deactivate, so
REM such a guard makes the FIRST venv activated win for the whole run: every
REM later app is built against the wrong interpreter. Re-activating is safe --
REM venv's activate.bat restores %_OLD_VIRTUAL_PATH% before prepending, so the
REM activations do not stack. See build_imagedescriber_wx.bat for the full note.
if exist ".winenv\Scripts\activate.bat" (
    call .winenv\Scripts\activate.bat
) else (
    echo WARNING: .winenv not found. Proceeding with system Python...
)

REM Clean PyInstaller cache for a fresh build (same as imagedescriber build)
python -c "import shutil; from pathlib import Path; cache_dir = Path.home() / 'AppData' / 'Local' / 'pyinstaller'; shutil.rmtree(cache_dir, ignore_errors=True); print(f'Cleaned: {cache_dir}')"
echo.

REM Run PyInstaller with --clean to force full recompile (no stale bytecode)
pyinstaller --clean --noconfirm idt.spec

if errorlevel 1 (
    echo.
    echo Build FAILED!
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo Executable: dist\idt.exe
echo ========================================
