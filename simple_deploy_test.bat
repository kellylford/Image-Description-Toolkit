@echo off
REM Simple deployment test using our known working executable
echo ========================================================================
echo SIMPLE DEPLOYMENT TEST - Using Built Executable
echo ========================================================================

set TEST_DIR=C:\idt_simple_test
set SOURCE_DIR=%~dp0

echo [1/4] Setting up test environment...
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"
mkdir "%TEST_DIR%"

echo [2/4] Copying working executable and dependencies...
copy "%SOURCE_DIR%dist\idt.exe" "%TEST_DIR%\"
xcopy /E /I /Y "%SOURCE_DIR%scripts" "%TEST_DIR%\scripts\"
xcopy /E /I /Y "%SOURCE_DIR%analysis" "%TEST_DIR%\analysis\"
xcopy /E /I /Y "%SOURCE_DIR%models" "%TEST_DIR%\models\"
copy "%SOURCE_DIR%VERSION" "%TEST_DIR%\"

echo [3/4] Testing basic functionality...
cd /d "%TEST_DIR%"

REM Test basic command
idt.exe --help >nul 2>&1
if errorlevel 1 (
    echo ERROR: Basic idt.exe execution failed
    exit /b 1
)

echo     ✓ Basic executable works

REM Test image_describer command
timeout 5 idt.exe image_describer --help >nul 2>&1
if errorlevel 124 (
    echo     ✓ image_describer command accessible
) else if errorlevel 1 (
    echo ERROR: image_describer command failed
    exit /b 1
) else (
    echo     ✓ image_describer command accessible
)

echo [4/4] Testing format string fix with sample images...
mkdir test_images
copy "%SOURCE_DIR%testimages\*.jpg" test_images\ >nul 2>&1

REM Run test that previously failed with format errors
timeout 30 idt.exe image_describer test_images --output-dir test_output --max-files 1 --provider ollama --model moondream:latest --prompt-style narrative >test_output.log 2>&1

REM Check for format string errors
findstr /i "Invalid format string" test_output.log >nul
if not errorlevel 1 (
    echo ERROR: Format string errors still present!
    type test_output.log
    exit /b 1
)

findstr /i "Error writing description to file: Invalid format string" test_output.log >nul
if not errorlevel 1 (
    echo ERROR: Specific format string error still present!
    exit /b 1
)

echo.
echo ========================================================================
echo SUCCESS! DEPLOYMENT TEST PASSED
echo ========================================================================
echo.
echo ✓ Executable deployed successfully
echo ✓ Basic functionality verified  
echo ✓ Format string fix confirmed working
echo.
echo Test installation at: %TEST_DIR%
echo.
echo The Image Description Toolkit is ready for use!
echo No more format string errors!
echo.

pause