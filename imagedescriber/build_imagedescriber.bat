@echo off
echo Building Image Describer GUI...
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
if not exist "dist\imagedescriber" mkdir dist\imagedescriber

REM Build the executable
echo Building imagedescriber executable...
echo.

C:/Users/kelly/GitHub/Image-Description-Toolkit/.venv/Scripts/pyinstaller.exe --onefile ^
    --windowed ^
    --name "imagedescriber_%ARCH%" ^
    --distpath "dist\imagedescriber" ^
    --workpath "build\imagedescriber_%ARCH%" ^
    --specpath "build" ^
    --add-data "C:\Users\kelly\GitHub\Image-Description-Toolkit\scripts;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    imagedescriber\imagedescriber.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable created: dist\imagedescriber\imagedescriber_%ARCH%.exe
echo.

REM Test the executable
echo Testing executable...
echo.
cd dist\imagedescriber
start "" "imagedescriber_%ARCH%.exe"
cd ..\..

echo.
echo Build and test completed!
pause
