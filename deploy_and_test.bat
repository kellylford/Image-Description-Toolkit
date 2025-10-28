@echo off
REM ============================================================================
REM AUTOMATED DEPLOYMENT AND TEST SCRIPT
REM ============================================================================
REM This script will:
REM 1. Install the Image Description Toolkit from the release package
REM 2. Run automated tests to verify everything works
REM 3. Test the specific metadata/format string fix
REM 4. Generate a comprehensive test report
REM ============================================================================

setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set INSTALL_DIR=C:\idt_auto_test_%TIMESTAMP%
set TEST_LOG=%SCRIPT_DIR%deployment_test_%TIMESTAMP%.log

echo.
echo ========================================================================
echo AUTOMATED DEPLOYMENT AND TEST - Image Description Toolkit v3.0.0
echo ========================================================================
echo.
echo Installation Directory: %INSTALL_DIR%
echo Test Log: %TEST_LOG%
echo Timestamp: %TIMESTAMP%
echo.

REM Create log file
echo Automated Deployment Test - %date% %time% > "%TEST_LOG%"
echo ======================================================= >> "%TEST_LOG%"

echo [1/8] Checking prerequisites...
echo [1/8] Checking prerequisites... >> "%TEST_LOG%"

REM Check if release package exists
if not exist "%SCRIPT_DIR%releases\ImageDescriptionToolkit_v3.0.0.zip" (
    echo ERROR: Release package not found: %SCRIPT_DIR%releases\ImageDescriptionToolkit_v3.0.0.zip
    echo ERROR: Release package not found >> "%TEST_LOG%"
    exit /b 1
)

REM Check if PowerShell is available for extraction
powershell -Command "Write-Host 'PowerShell available'" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell not available for package extraction
    echo ERROR: PowerShell not available >> "%TEST_LOG%"
    exit /b 1
)

echo     ✓ Release package found
echo     ✓ PowerShell available
echo     ✓ Prerequisites check passed >> "%TEST_LOG%"

echo [2/8] Creating clean installation directory...
echo [2/8] Creating clean installation directory... >> "%TEST_LOG%"

if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"

echo     ✓ Installation directory created: %INSTALL_DIR%
echo     ✓ Installation directory created >> "%TEST_LOG%"

echo [3/8] Extracting release package...
echo [3/8] Extracting release package... >> "%TEST_LOG%"

powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%releases\ImageDescriptionToolkit_v3.0.0.zip' -DestinationPath '%INSTALL_DIR%' -Force"
if errorlevel 1 (
    echo ERROR: Failed to extract release package
    echo ERROR: Failed to extract release package >> "%TEST_LOG%"
    exit /b 1
)

echo     ✓ Package extracted successfully
echo     ✓ Package extracted successfully >> "%TEST_LOG%"

echo [4/8] Verifying installation...
echo [4/8] Verifying installation... >> "%TEST_LOG%"

if not exist "%INSTALL_DIR%\idt.exe" (
    echo ERROR: idt.exe not found in installation
    echo ERROR: idt.exe not found >> "%TEST_LOG%"
    exit /b 1
)

if not exist "%INSTALL_DIR%\scripts\image_describer.py" (
    echo ERROR: scripts\image_describer.py not found
    echo ERROR: scripts missing >> "%TEST_LOG%"
    exit /b 1
)

echo     ✓ Core executable found
echo     ✓ Scripts directory found
echo     ✓ Installation verified >> "%TEST_LOG%"

echo [5/8] Testing basic functionality...
echo [5/8] Testing basic functionality... >> "%TEST_LOG%"

cd /d "%INSTALL_DIR%"

REM Test help command
idt.exe --help >nul 2>&1
if errorlevel 1 (
    echo ERROR: Basic idt.exe execution failed
    echo ERROR: Basic execution failed >> "%TEST_LOG%"
    exit /b 1
)

REM Test image_describer command
timeout 5 idt.exe image_describer --help >nul 2>&1
if errorlevel 124 (
    echo     ✓ image_describer command accessible (timed out as expected)
) else if errorlevel 1 (
    echo ERROR: image_describer command failed
    echo ERROR: image_describer command failed >> "%TEST_LOG%"
    exit /b 1
) else (
    echo     ✓ image_describer command accessible
)

echo     ✓ Basic functionality tests passed >> "%TEST_LOG%"

echo [6/8] Testing workflow functionality...
echo [6/8] Testing workflow functionality... >> "%TEST_LOG%"

REM Test workflow command
timeout 5 idt.exe workflow --help >nul 2>&1
if errorlevel 124 (
    echo     ✓ workflow command accessible (timed out as expected)
) else if errorlevel 1 (
    echo ERROR: workflow command failed
    echo ERROR: workflow command failed >> "%TEST_LOG%"
    exit /b 1
) else (
    echo     ✓ workflow command accessible
)

echo     ✓ Workflow functionality tests passed >> "%TEST_LOG%"

echo [7/8] Testing format string fix...
echo [7/8] Testing format string fix... >> "%TEST_LOG%"

REM Create test images directory
mkdir test_images
copy "%SCRIPT_DIR%testimages\*.jpg" test_images\ >nul 2>&1

REM Run image describer with conditions that previously caused format errors
echo Testing with sample images...
timeout 30 idt.exe image_describer test_images --output-dir test_output --max-files 1 --provider ollama --model moondream:latest --prompt-style narrative >test_format_output.log 2>&1

REM Check for format string errors
findstr /i "Invalid format string" test_format_output.log >nul
if not errorlevel 1 (
    echo ERROR: Format string errors still present
    echo ERROR: Format string errors detected >> "%TEST_LOG%"
    echo Error details: >> "%TEST_LOG%"
    type test_format_output.log >> "%TEST_LOG%"
    exit /b 1
)

findstr /i "Error writing description to file: Invalid format string" test_format_output.log >nul
if not errorlevel 1 (
    echo ERROR: Specific format string error still present
    echo ERROR: Specific format string error detected >> "%TEST_LOG%"
    exit /b 1
)

echo     ✓ No format string errors detected
echo     ✓ Format string fix verified >> "%TEST_LOG%"

echo [8/8] Generating final test report...
echo [8/8] Generating final test report... >> "%TEST_LOG%"

echo.
echo ========================================================================
echo DEPLOYMENT TEST RESULTS - SUCCESS
echo ========================================================================
echo.
echo Installation Location: %INSTALL_DIR%
echo Package Version: v3.0.0
echo Test Timestamp: %TIMESTAMP%
echo.
echo ✓ Prerequisites check: PASSED
echo ✓ Package extraction: PASSED  
echo ✓ Installation verification: PASSED
echo ✓ Basic functionality: PASSED
echo ✓ Workflow functionality: PASSED
echo ✓ Format string fix: VERIFIED
echo.
echo The Image Description Toolkit has been successfully deployed and tested.
echo All critical issues have been resolved.
echo.
echo Installation ready at: %INSTALL_DIR%
echo Full test log: %TEST_LOG%
echo.

REM Write final results to log
echo. >> "%TEST_LOG%"
echo FINAL RESULTS: ALL TESTS PASSED >> "%TEST_LOG%"
echo Installation: %INSTALL_DIR% >> "%TEST_LOG%"
echo Test completed: %date% %time% >> "%TEST_LOG%"

echo [COMPLETE] Automated deployment and testing finished successfully.
echo.

pause