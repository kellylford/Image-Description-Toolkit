@echo off
REM Build IDT CLI for Windows
REM Run this from the idt directory

echo Building IDT CLI...
echo.

REM Activate virtual environment (skipped gracefully when not present, e.g. CI)
if not defined VIRTUAL_ENV (
    if exist ".winenv\Scripts\activate.bat" (
        call .winenv\Scripts\activate.bat
    ) else (
        echo WARNING: .winenv not found. Proceeding with system Python...
    )
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
