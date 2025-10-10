@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
REM ===========================================================================
REM Automated Ollama Model Tester (No Prompts)
REM ===========================================================================
REM This script automatically detects and tests all available Ollama models
REM Usage: run_all_ollama_auto.bat <image_directory> [prompt_style]
REM Example: run_all_ollama_auto.bat C:\MyImages narrative

set IMAGE_DIR=%1
if "%IMAGE_DIR%"=="" (
    echo ERROR: No image directory specified!
    echo Usage: run_all_ollama_auto.bat ^<image_directory^> [prompt_style]
    exit /b 1
)

set PROMPT_STYLE=%2
if "%PROMPT_STYLE%"=="" set PROMPT_STYLE=narrative

REM Check if image directory exists
if not exist "%IMAGE_DIR%" (
    echo ERROR: Image directory does not exist: %IMAGE_DIR%
    exit /b 1
)

REM Check if ollama is available
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama is not available
    exit /b 1
)

echo [%date% %time%] Starting automated Ollama model testing
echo Input directory: %IMAGE_DIR%
echo Prompt style: %PROMPT_STYLE%
echo.

REM Get list of available models and test each one
echo Detecting and testing Ollama models...
set MODEL_COUNT=0
set SUCCESS_COUNT=0
set FAIL_COUNT=0

for /f "skip=1 tokens=1 delims= " %%a in ('ollama list') do (
    set /a MODEL_COUNT+=1
    echo.
    echo [!MODEL_COUNT!] Testing: %%a
    echo ----------------------------------------
    
    ..\idt.exe workflow --provider ollama --model %%a --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions "%IMAGE_DIR%" --steps describe
    
    if !errorlevel! equ 0 (
        echo ✓ SUCCESS: %%a
        set /a SUCCESS_COUNT+=1
    ) else (
        echo ✗ FAILED: %%a
        set /a FAIL_COUNT+=1
    )
)

echo.
echo ========================================
echo AUTOMATED TESTING COMPLETE
echo ========================================
echo Total models: %MODEL_COUNT%
echo Successful: %SUCCESS_COUNT%
echo Failed: %FAIL_COUNT%
echo.

ENDLOCAL