@echo off
REM Build script for IDT Configure
REM Creates standalone executable using PyInstaller

echo ========================================
echo Building IDT Configure
echo ========================================
echo.

REM Get version
set /p VERSION=<..\VERSION

REM Check for PyInstaller
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller not found
    echo.
    echo Please install PyInstaller:
    echo   pip install pyinstaller
    echo.
    pause
    exit /b 1
)

echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo.
echo Building executable...
echo Version: %VERSION%
echo.

pyinstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "idtconfigure" ^
    --icon=NONE ^
    --add-data "../VERSION;." ^
    idtconfigure.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\idtconfigure\idtconfigure.exe
echo.
echo You can now run: dist\idtconfigure\idtconfigure.exe
echo.
pause
