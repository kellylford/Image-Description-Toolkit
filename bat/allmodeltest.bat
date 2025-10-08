@echo off
SETLOCAL
REM Test all offline (Ollama) models on a specific directory
REM Usage: allmodeltest.bat <image_directory> [prompt_style]
REM Example: allmodeltest.bat C:\MyImages narrative

set IMAGE_DIR=%1
if "%IMAGE_DIR%"=="" (
    echo ERROR: No image directory specified!
    echo Usage: allmodeltest.bat ^<image_directory^> [prompt_style]
    echo Example: allmodeltest.bat C:\MyImages narrative
    pause
    exit /b 1
)

set PROMPT_STYLE=%2
if "%PROMPT_STYLE%"=="" set PROMPT_STYLE=narrative

echo.
echo ========================================
echo Testing ALL 18 Ollama Vision Models
echo ========================================
echo Target: %IMAGE_DIR%
echo Prompt Style: %PROMPT_STYLE%
echo.

echo.
echo [1/18] Running moondream:latest...
call run_ollama_moondream.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [2/18] Running llava:7b...
call run_ollama_llava7b.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [3/18] Running llava:latest...
call run_ollama_llava.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [4/18] Running llava:13b...
call run_ollama_llava13b.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [5/18] Running llava:34b...
call run_ollama_llava34b.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [6/18] Running llava-phi3:latest...
call run_ollama_llava_phi3.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [7/18] Running llava-llama3:latest...
call run_ollama_llava_llama3.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [8/18] Running bakllava:latest...
call run_ollama_bakllava.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [9/18] Running llama3.2-vision:latest...
call run_ollama_llama32vision.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [10/18] Running llama3.2-vision:11b...
call run_ollama_llama32vision11b.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [11/18] Running mistral-nemo:latest...
call run_ollama_mistral31.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [12/18] Running pixtral:12b...
call run_ollama_mistral32.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [13/18] Running gemma3:latest...
call run_ollama_gemma.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [14/18] Running minicpm-v:latest...
call run_ollama_minicpmv.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [15/18] Running minicpm-v:8b...
call run_ollama_minicpmv8b.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [16/18] Running cogvlm2:latest...
call run_ollama_cogvlm2.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [17/18] Running internvl2:latest...
call run_ollama_internvl.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [18/18] Running qwen2.5-vl:latest...
call run_ollama_qwen2.5vl.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo ========================================
echo All 18 model tests complete!
echo ========================================
echo Results in: ..\Descriptions\wf_ollama_*
echo.
pause
ENDLOCAL
