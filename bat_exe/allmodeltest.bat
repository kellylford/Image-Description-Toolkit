@echo off
SETLOCAL EnableDelayedExpansion
REM Test all installed Ollama vision models on a directory
REM Usage: allmodeltest.bat <image_directory> [options]
REM
REM Supports all standard workflow options:
REM   --name <name>              Custom workflow name
REM   --prompt-style <style>     Prompt style to use
REM   --output-dir <dir>         Output directory
REM   --steps <steps>            Workflow steps to run
REM   --batch                    Non-interactive mode
REM   --view-results             Auto-launch viewer
REM
REM Example: allmodeltest.bat C:\MyImages --prompt-style narrative --name "vacation"
REM Example: allmodeltest.bat C:\MyImages --batch --view-results

REM Capture the original working directory before changing directories
SET ORIGINAL_CWD=%CD%

REM Change to project root directory
cd /d "%~dp0\.."

REM Check if first argument looks like an option
set FIRST_ARG=%1
if "%FIRST_ARG%"=="" (
    echo ERROR: No image directory specified!
    echo.
    echo Usage: allmodeltest.bat ^<image_directory^> [options]
    echo.
    echo Examples:
    echo   allmodeltest.bat C:\MyImages
    echo   allmodeltest.bat C:\MyImages --prompt-style narrative
    echo   allmodeltest.bat C:\MyImages --name vacation --batch
    echo.
    pause
    exit /b 1
)

if "%FIRST_ARG:~0,2%"=="--" (
    echo ERROR: First argument must be the image directory!
    echo Usage: allmodeltest.bat ^<image_directory^> [options]
    pause
    exit /b 1
)

REM First argument is the image directory
set IMAGE_DIR=%~1

REM Shift to get remaining arguments (all options)
shift
set OPTIONS=
:parse_options
if "%~1"=="" goto :done_parsing
set OPTIONS=%OPTIONS% %1
shift
goto :parse_options
:done_parsing

echo.
echo ========================================
echo Testing All Installed Ollama Vision Models
echo ========================================
echo Target Directory: %IMAGE_DIR%
echo Additional Options: %OPTIONS%
echo.

REM Check if Ollama is installed and running
where ollama >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama is not installed or not in PATH!
    echo Please install Ollama from https://ollama.ai/download
    pause
    exit /b 1
)

REM Query installed models and filter for vision models
echo Detecting installed vision models...
echo.

REM Create temporary file for model list
set TEMP_FILE=%TEMP%\ollama_models_%RANDOM%.txt
ollama list | findstr /V "NAME" > "%TEMP_FILE%"

REM Known vision model patterns (case-insensitive)
REM These are models that support image inputs
set VISION_PATTERNS=llava llama3.2-vision llama3.3-vision moondream bakllava minicpm pixtral mistral-nemo gemma qwen

REM Count and display vision models
set MODEL_COUNT=0
set MODEL_LIST=

for /f "tokens=1" %%M in (%TEMP_FILE%) do (
    set MODEL_NAME=%%M
    set IS_VISION=0
    
    REM Check if model name contains any vision pattern
    for %%P in (%VISION_PATTERNS%) do (
        echo !MODEL_NAME! | findstr /i "%%P" >nul
        if !errorlevel! equ 0 set IS_VISION=1
    )
    
    if !IS_VISION! equ 1 (
        set /a MODEL_COUNT+=1
        set MODEL_LIST=!MODEL_LIST! !MODEL_NAME!
        echo [!MODEL_COUNT!] !MODEL_NAME!
    )
)

REM Clean up temp file
del "%TEMP_FILE%" >nul 2>&1

if %MODEL_COUNT% equ 0 (
    echo.
    echo ERROR: No vision models found!
    echo.
    echo Please install at least one vision model, for example:
    echo   ollama pull moondream
    echo   ollama pull llava
    echo   ollama pull llama3.2-vision
    echo.
    pause
    exit /b 1
)

echo.
echo Found %MODEL_COUNT% vision model(s)
echo.

REM Confirm before running
set /p CONFIRM="Run workflow on all %MODEL_COUNT% models? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo ========================================
echo Starting Multi-Model Test
echo ========================================
echo.

REM Run workflow for each detected model
set CURRENT=0
for %%M in (%MODEL_LIST%) do (
    set /a CURRENT+=1
    echo.
    echo ========================================
    echo [!CURRENT!/%MODEL_COUNT%] Running: %%M
    echo ========================================
    echo.
    
    dist\idt.exe workflow --provider ollama --model %%M --output-dir ../Descriptions --original-cwd "%ORIGINAL_CWD%" --batch %OPTIONS% "%IMAGE_DIR%"
    
    if errorlevel 1 (
        echo.
        echo WARNING: Model %%M failed or was interrupted
        echo.
        set /p CONTINUE="Continue with remaining models? (y/n): "
        if /i not "!CONTINUE!"=="y" (
            echo Multi-model test cancelled.
            pause
            exit /b 1
        )
    )
)

echo.
echo ========================================
echo All %MODEL_COUNT% Model Tests Complete!
echo ========================================
echo Results in: Descriptions\wf_*
echo.
pause
ENDLOCAL
