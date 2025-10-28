@echo off
REM Automated test script to verify format string fix
echo ========================================
echo AUTOMATED FIX TEST
echo ========================================

set TEST_DIR=C:\idt_test_fix
set SOURCE_DIR=%~dp0

echo [1/5] Cleaning test directory...
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"
mkdir "%TEST_DIR%"

echo [2/5] Building IDT executable with fixes...
cd /d "%SOURCE_DIR%"
python -m PyInstaller --clean --distpath "%TEST_DIR%" BuildAndRelease\final_working.spec
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

echo [3/5] Setting up test environment...
xcopy /E /I /Y scripts "%TEST_DIR%\scripts\"
xcopy /E /I /Y analysis "%TEST_DIR%\analysis\"
xcopy /E /I /Y models "%TEST_DIR%\models\"
copy VERSION "%TEST_DIR%\"

echo [4/5] Running test workflow...
cd /d "%TEST_DIR%"
echo Testing with a small subset of images...
idt.exe image_describer "C:\Users\kelly\GitHub\Image-Description-Toolkit\test_data" --output-dir "%TEST_DIR%\test_output" --max-files 2 --provider ollama --model moondream:latest --prompt-style narrative

echo [5/5] Checking results...
if exist "%TEST_DIR%\test_output\image_descriptions.txt" (
    echo SUCCESS: Descriptions file created
    echo Checking for format string errors...
    findstr /i "Invalid format string" "%TEST_DIR%\test_output\*.log" >nul
    if errorlevel 1 (
        echo SUCCESS: No format string errors found!
        echo Test completed successfully
        exit /b 0
    ) else (
        echo ERROR: Format string errors still present
        exit /b 1
    )
) else (
    echo ERROR: No descriptions file created
    exit /b 1
)