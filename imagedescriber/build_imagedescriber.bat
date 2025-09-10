@echo off
echo Building ImageDescriber GUI Application...

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."

REM Check if virtual environment exists
if not exist "%ROOT_DIR%\.venv" (
    echo Error: Virtual environment not found at %ROOT_DIR%\.venv
    echo Please create and activate the virtual environment first.
    pause
    exit /b 1
)

REM Get Python executable from virtual environment
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

REM Verify Python executable exists
if not exist "%PYTHON_EXE%" (
    echo Error: Python executable not found at %PYTHON_EXE%
    pause
    exit /b 1
)

REM Detect architecture
for /f "tokens=*" %%i in ('%PYTHON_EXE% -c "import platform; print(platform.machine().lower())"') do set "ARCH=%%i"

REM Fallback if architecture detection failed
if "%ARCH%"=="" set "ARCH=amd64"

if "%ARCH%"=="amd64" (
    set "ARCH_NAME=AMD64"
) else if "%ARCH%"=="arm64" (
    set "ARCH_NAME=ARM64"
) else (
    set "ARCH_NAME=%ARCH%"
)

echo Detected architecture: %ARCH_NAME%
echo.

REM Ask user what to build
echo What would you like to build?
echo [1] Current architecture only (%ARCH_NAME%)
echo [2] AMD64 only
echo [3] ARM64 only  
echo [4] Both AMD64 and ARM64
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto build_current
if "%choice%"=="2" goto build_amd64
if "%choice%"=="3" goto build_arm64
if "%choice%"=="4" goto build_both
goto build_current

:build_current
if "%ARCH%"=="amd64" (
    call "%SCRIPT_DIR%build_imagedescriber_amd.bat"
) else (
    call "%SCRIPT_DIR%build_imagedescriber_arm.bat"
)
goto end

:build_amd64
call "%SCRIPT_DIR%build_imagedescriber_amd.bat"
goto end

:build_arm64
call "%SCRIPT_DIR%build_imagedescriber_arm.bat"
goto end

:build_both
echo.
echo Building both architectures...
echo.
echo ========================================
echo Building AMD64...
echo ========================================
call "%SCRIPT_DIR%build_imagedescriber_amd.bat"
echo.
echo ========================================
echo Building ARM64...
echo ========================================
call "%SCRIPT_DIR%build_imagedescriber_arm.bat"
echo.
echo ========================================
echo Build Summary
echo ========================================
echo Both builds completed.
echo Check the output above for any errors.
echo.
pause
goto end

:end
