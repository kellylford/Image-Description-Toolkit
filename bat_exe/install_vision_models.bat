@echo off
setlocal EnableDelayedExpansion

REM Install ALL Ollama vision models
echo.
echo ========================================
echo Installing ALL Ollama Vision Models
echo ========================================
echo.

REM Get current model status
echo.
echo Checking currently installed Ollama models...
..\idt.exe check-models --provider ollama --json > current_models.json

echo This will install the following models:
echo Core Models:

set TOTAL_NEW=0

REM Check each model individually with simple parsing
call :CheckModel "moondream" "1.7"
call :CheckModel "llava:latest" "4.7"
call :CheckModel "llava:7b" "4.7"
call :CheckModel "llava:13b" "8.0"
call :CheckModel "llava:34b" "20.0"
call :CheckModel "llava-phi3" "2.9"
call :CheckModel "llava-llama3" "5.5"
call :CheckModel "bakllava" "4.7"
call :CheckModel "llama3.2-vision:latest" "7.8"
call :CheckModel "llama3.2-vision:11b" "7.8"
call :CheckModel "llama3.2-vision:90b" "55.0"
call :CheckModel "minicpm-v" "4.0"
call :CheckModel "minicpm-v:8b" "5.0"
call :CheckModel "gemma3" "3.3"
call :CheckModel "mistral-small3.1" "15.0"
call :CheckModel "mistral-small3.2" "15.0"
call :CheckModel "qwen2.5vl" "7.0"

echo.
echo Total NEW downloads required: ~%TOTAL_NEW%GB
echo.
echo Press Ctrl+C to cancel, or
pause

REM Install missing models
call :InstallModel "moondream"
call :InstallModel "llava:latest"
call :InstallModel "llava:7b"
call :InstallModel "llava:13b"
call :InstallModel "llava:34b"
call :InstallModel "llava-phi3"
call :InstallModel "llava-llama3"
call :InstallModel "bakllava"
call :InstallModel "llama3.2-vision:latest"
call :InstallModel "llama3.2-vision:11b"
call :InstallModel "llama3.2-vision:90b"
call :InstallModel "minicpm-v"
call :InstallModel "minicpm-v:8b"
call :InstallModel "gemma3"
call :InstallModel "mistral-small3.1"
call :InstallModel "mistral-small3.2"
call :InstallModel "qwen2.5vl"

REM Clean up temporary file
del current_models.json

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Run 'idt.exe check-models' to verify installation
echo.
pause
goto :eof

:CheckModel
set MODEL_NAME=%~1
set MODEL_SIZE=%~2
findstr /C:"%MODEL_NAME%" current_models.json >nul
if %errorlevel% equ 0 (
    echo   - %MODEL_NAME% (%MODEL_SIZE% GB) - Already installed
) else (
    echo   - %MODEL_NAME% (%MODEL_SIZE% GB)
    set /a TOTAL_NEW+=%MODEL_SIZE% 2>nul
)
goto :eof

:InstallModel
set MODEL_NAME=%~1
findstr /C:"%MODEL_NAME%" current_models.json >nul
if %errorlevel% neq 0 (
    echo.
    echo Installing %MODEL_NAME%...
    ollama pull %MODEL_NAME%
)
goto :eof
