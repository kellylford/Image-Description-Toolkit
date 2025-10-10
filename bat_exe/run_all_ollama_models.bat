@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
REM ===========================================================================
REM Dynamic Ollama Model Tester
REM ===========================================================================
REM This script automatically detects all available Ollama models and tests them
REM Usage: run_all_ollama_models.bat <image_directory> [prompt_style]
REM Example: run_all_ollama_models.bat C:\MyImages narrative

echo.
echo ========================================================================
echo Dynamic Ollama Model Testing
echo ========================================================================
echo.

REM Check parameters
set IMAGE_DIR=%1
if "%IMAGE_DIR%"=="" (
    echo ERROR: No image directory specified!
    echo.
    echo Usage: run_all_ollama_models.bat ^<image_directory^> [prompt_style]
    echo Example: run_all_ollama_models.bat C:\MyImages narrative
    echo.
    pause
    exit /b 1
)

set PROMPT_STYLE=%2
if "%PROMPT_STYLE%"=="" set PROMPT_STYLE=narrative

REM Check if image directory exists
if not exist "%IMAGE_DIR%" (
    echo ERROR: Image directory does not exist: %IMAGE_DIR%
    echo.
    pause
    exit /b 1
)

REM Check if ollama is available
ollama list >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama is not available or not installed
    echo Please make sure Ollama is running and accessible
    echo.
    pause
    exit /b 1
)

echo Input directory: %IMAGE_DIR%
echo Prompt style: %PROMPT_STYLE%
echo.

REM Get list of available models
echo Detecting available Ollama models...
ollama list > temp_models.txt

REM Parse models (skip header line)
set MODEL_COUNT=0
for /f "skip=1 tokens=1 delims= " %%a in (temp_models.txt) do (
    set /a MODEL_COUNT+=1
    set MODEL_!MODEL_COUNT!=%%a
)

REM Clean up temp file
del temp_models.txt

echo Found %MODEL_COUNT% Ollama models
echo.

REM Display models that will be tested
echo Models to test:
for /l %%i in (1,1,%MODEL_COUNT%) do (
    echo   %%i. !MODEL_%%i!
)
echo.

REM Ask for confirmation
set /p CONTINUE="Continue with testing all models? (y/N): "
if /i not "%CONTINUE%"=="y" (
    echo Testing cancelled.
    pause
    exit /b 0
)

echo.
echo ========================================================================
echo Starting batch testing of %MODEL_COUNT% models...
echo ========================================================================
echo.

REM Test each model
set SUCCESS_COUNT=0
set FAIL_COUNT=0

for /l %%i in (1,1,%MODEL_COUNT%) do (
    echo.
    echo [%%i/%MODEL_COUNT%] Testing model: !MODEL_%%i!
    echo -----------------------------------------------------------------------
    
    REM Run the workflow for this model
    ..\dist\idt.exe workflow --provider ollama --model !MODEL_%%i! --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions "%IMAGE_DIR%"
    
    if !errorlevel! equ 0 (
        echo ✓ SUCCESS: !MODEL_%%i!
        set /a SUCCESS_COUNT+=1
    ) else (
        echo ✗ FAILED: !MODEL_%%i!
        set /a FAIL_COUNT+=1
    )
    
    echo.
    echo Press any key to continue to next model...
    pause >nul
)

echo.
echo ========================================================================
echo BATCH TESTING COMPLETE
echo ========================================================================
echo.
echo Total models tested: %MODEL_COUNT%
echo Successful runs: %SUCCESS_COUNT%
echo Failed runs: %FAIL_COUNT%
echo.
echo Results saved in: ..\Descriptions\
echo.
pause

ENDLOCAL