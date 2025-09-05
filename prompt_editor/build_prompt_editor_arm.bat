@echo off
echo Building Image Description Prompt Editor for ARM64...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Exiting.
        pause
        exit /b 1
    )
)

REM Create output directory
if not exist "dist" mkdir dist
if not exist "dist\prompt_editor" mkdir dist\prompt_editor

REM Build the executable for ARM64
echo Building ARM64 prompt editor executable...
echo.

pyinstaller --onefile ^
    --windowed ^
    --name "prompt_editor_arm64" ^
    --distpath "dist\prompt_editor" ^
    --workpath "build\prompt_editor_arm64" ^
    --specpath "build" ^
    --add-data "scripts;scripts" ^
    --target-architecture arm64 ^
    prompt_editor\prompt_editor.py

if errorlevel 1 (
    echo ARM64 build failed!
    pause
    exit /b 1
)

echo.
echo ARM64 build completed successfully!
echo Executable created: dist\prompt_editor\prompt_editor_arm64.exe
echo.

REM Test the executable
echo Testing ARM64 executable...
echo.
cd dist\prompt_editor
start "" "prompt_editor_arm64.exe"
cd ..\..

echo.
echo ARM64 build and test completed!
pause
