@echo off
echo Building Image Description Prompt Editor...
echo.

REM Get architecture using Python
for /f "tokens=*" %%i in ('C:/Users/kelly/GitHub/Image-Description-Toolkit/.venv/Scripts/python.exe -c "import platform; print(platform.machine().lower())"') do set ARCH=%%i

REM Map architecture names
if "%ARCH%"=="aarch64" set ARCH=arm64
if "%ARCH%"=="arm64" set ARCH=arm64
if "%ARCH%"=="amd64" set ARCH=amd64
if "%ARCH%"=="x86_64" set ARCH=amd64

echo Detected architecture: %ARCH%
echo.

REM Check if PyInstaller is installed
C:/Users/kelly/GitHub/Image-Description-Toolkit/.venv/Scripts/python.exe -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    C:/Users/kelly/GitHub/Image-Description-Toolkit/.venv/Scripts/pip.exe install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Exiting.
        pause
        exit /b 1
    )
)

REM Create output directory
if not exist "dist" mkdir dist
if not exist "dist\prompt_editor" mkdir dist\prompt_editor

REM Build the executable
echo Building prompt editor executable...
echo.

C:/Users/kelly/GitHub/Image-Description-Toolkit/.venv/Scripts/pyinstaller.exe --onefile ^
    --windowed ^
    --name "prompt_editor_%ARCH%" ^
    --distpath "dist\prompt_editor" ^
    --workpath "build\prompt_editor_%ARCH%" ^
    --specpath "build" ^
    --add-data "C:\Users\kelly\GitHub\Image-Description-Toolkit\scripts;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    prompt_editor\prompt_editor.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable created: dist\prompt_editor\prompt_editor_%ARCH%.exe
echo.

REM Test the executable
echo Testing executable...
echo.
cd dist\prompt_editor
start "" "prompt_editor_%ARCH%.exe"
cd ..\..

echo.
echo Build and test completed!
pause
