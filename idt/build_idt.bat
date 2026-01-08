@echo off
REM Build IDT CLI for Windows
REM Run this from the idt directory

echo Building IDT CLI...
echo.

REM Activate virtual environment
call ..\.venv\Scripts\activate.bat

REM Run PyInstaller
pyinstaller --noconfirm idt.spec

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
