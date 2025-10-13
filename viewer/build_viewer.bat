@echo off
echo ========================================================================
echo Building Image Description Viewer
echo ========================================================================
echo.

REM Detect architecture using current Python
echo Detecting system architecture...
for /f "tokens=*" %%i in ('python -c "import platform; print(platform.machine().lower())"') do set ARCH=%%i

REM Map architecture names for output filename
if "%ARCH%"=="aarch64" set ARCH=arm64
if "%ARCH%"=="arm64" set ARCH=arm64
if "%ARCH%"=="amd64" set ARCH=amd64
if "%ARCH%"=="x86_64" set ARCH=amd64

echo Building for: %ARCH%
echo.
echo NOTE: PyInstaller builds for the current Python architecture.
echo       Cross-compilation is not supported on Windows.
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller.
        pause
        exit /b 1
    )
    echo.
)

REM Check if PyQt6 is installed
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo PyQt6 not found. Installing viewer dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo.
)

REM Create output directory
if not exist "dist" mkdir dist

REM Get absolute path to scripts directory (one level up)
set SCRIPTS_DIR=%cd%\..\scripts

REM Check if scripts directory exists
if not exist "%SCRIPTS_DIR%" (
    echo WARNING: Scripts directory not found at: %SCRIPTS_DIR%
    echo.
    echo The redescribe feature will not work in the bundled executable.
    echo However, the viewer will still work for viewing HTML/Live modes.
    echo.
    echo Do you want to continue building without scripts? ^(Y/N^)
    choice /C YN /N
    if errorlevel 2 (
        echo Build cancelled.
        pause
        exit /b 1
    )
    echo.
    echo Building viewer WITHOUT scripts bundled...
    echo.
    
    pyinstaller --onefile ^
        --windowed ^
        --name "viewer_%ARCH%" ^
        --distpath "dist" ^
        --workpath "build" ^
        --specpath "build" ^
        --hidden-import PyQt6.QtCore ^
        --hidden-import PyQt6.QtGui ^
        --hidden-import PyQt6.QtWidgets ^
        viewer.py
) else (
    echo Scripts directory found: %SCRIPTS_DIR%
    echo Building viewer WITH scripts bundled ^(redescribe feature enabled^)...
    echo.
    
    pyinstaller --onefile ^
        --windowed ^
        --name "viewer_%ARCH%" ^
        --distpath "dist" ^
        --workpath "build" ^
        --specpath "build" ^
        --add-data "%SCRIPTS_DIR%;scripts" ^
        --hidden-import PyQt6.QtCore ^
        --hidden-import PyQt6.QtGui ^
        --hidden-import PyQt6.QtWidgets ^
        viewer.py
)

if errorlevel 1 (
    echo.
    echo ========================================================================
    echo BUILD FAILED
    echo ========================================================================
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo BUILD SUCCESSFUL
echo ========================================================================
echo Executable created: dist\viewer_%ARCH%.exe
echo Architecture: %ARCH%
echo.
echo To test: cd dist ^&^& viewer_%ARCH%.exe
echo.
pause
