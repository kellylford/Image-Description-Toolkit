@echo off
setlocal EnableDelayedExpansion

REM Install ALL Ollama vision models
echo.
echo ========================================
echo Installing ALL Ollama Vision Models
REM Get current model status
python models/check_models.py --provider ollama --json > current_models.json
REM Define all available models and their sizes
set "MODELS_LIST[0]=moondream:1.7"
set "MODELS_LIST[1]=llava:latest:4.7"
set "MODELS_LIST[2]=llava:7b:4.7"
set "MODELS_LIST[3]=llava:13b:8.0"
set "MODELS_LIST[4]=llava:34b:20.0"
set "MODELS_LIST[5]=llava-phi3:2.9"
set "MODELS_LIST[6]=llava-llama3:5.5"
set "MODELS_LIST[7]=bakllava:4.7"
set "MODELS_LIST[8]=llama3.2-vision:latest:7.8"
set "MODELS_LIST[9]=llama3.2-vision:11b:7.8"
set "MODELS_LIST[10]=llama3.2-vision:90b:55.0"
set "MODELS_LIST[11]=minicpm-v:4.0"
set "MODELS_LIST[12]=minicpm-v:8b:5.0"
set "MODELS_LIST[13]=gemma3:3.3"
set "MODELS_LIST[14]=mistral-small3.1:15.0"
set "MODELS_LIST[15]=mistral-small3.2:15.0"
set "MODELS_LIST[16]=qwen2.5vl:7.0"
echo This will install the following models:
echo Core Models:
set TOTAL_NEW=0
REM First pass: check what's already installed and calculate totals
for /L %%i in (0,1,16) do (
    for /F "tokens=1,2 delims=:" %%a in ("!MODELS_LIST[%%i]!") do (
        findstr /C:"%%a" current_models.json >nul
        if !errorlevel! equ 0 (
            echo   - %%a (%%b GB) - Already installed
        ) else (
            echo   - %%a (%%b GB)
            set /a "TOTAL_NEW+=%%b"
        )
    )
)
echo Total NEW downloads required: ~%TOTAL_NEW%GB
echo Press Ctrl+C to cancel, or
pause
REM Install missing models (don't delete current_models.json yet)
set /a count=1
        if !errorlevel! neq 0 (
            echo.
            echo [!count!/17] Installing %%a...
            ollama pull %%a
            set /a count+=1
REM Clean up temporary file after installation
del current_models.json
echo Installation Complete!
echo Run 'python models/check_models.py' to verify installation
