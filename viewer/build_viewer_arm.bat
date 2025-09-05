@echo off
echo Building Image Description Viewer for ARM64...
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
if not exist "dist\viewer" mkdir dist\viewer

REM Build the executable for ARM64
echo Building ARM64 viewer executable...
echo.

pyinstaller --onefile ^
    --windowed ^
    --name "viewer_arm64" ^
    --distpath "dist\viewer" ^
    --workpath "build\viewer_arm64" ^
    --specpath "build" ^
    --add-data "../scripts;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --target-architecture arm64 ^
    viewer.py

if errorlevel 1 (
    echo ARM64 build failed!
    echo Note: Cross-compilation to ARM64 may require an ARM64 host system.
    pause
    exit /b 1
)

echo.
echo ARM64 build completed successfully!
echo Executable created: dist\viewer\viewer_arm64.exe
echo.

REM Test the executable
echo Testing ARM64 executable...
echo.
cd dist\viewer
start "" "viewer_arm64.exe"
cd ..\..

echo.
echo ARM64 build and test completed!
pause
