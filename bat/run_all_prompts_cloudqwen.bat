@echo off
SETLOCAL
REM Run qwen3-vl:235b-cloud with all prompt styles
REM Usage: run_all_prompts_cloudqwen.bat <image_directory> [workflow_name]
REM 
REM This batch file runs the cloud qwen model (qwen3-vl:235b-cloud) against
REM the specified directory with all 7 available prompt styles.
REM 
REM Examples:
REM   run_all_prompts_cloudqwen.bat c:\idt\images
REM   run_all_prompts_cloudqwen.bat c:\idt\images PromptBaseline

cd /d "%~dp0\.."

SET IMAGE_DIR=%1
IF "%IMAGE_DIR%"=="" (
    echo ERROR: No image directory specified!
    echo Usage: run_all_prompts_cloudqwen.bat ^<image_directory^> [workflow_name]
    echo Example: run_all_prompts_cloudqwen.bat c:\idt\images PromptBaseline
    pause
    exit /b 1
)

SET WORKFLOW_NAME=%2
IF "%WORKFLOW_NAME%"=="" SET WORKFLOW_NAME=PromptBaseline

SET MODEL=qwen3-vl:235b-cloud

echo.
echo ========================================
echo Testing Cloud Qwen Model with All Prompts
echo Target: %IMAGE_DIR%
echo Model: %MODEL%
echo Workflow Name: %WORKFLOW_NAME%
echo Total: 7 prompt styles
echo ========================================
echo.

echo [1/7] Running Simple prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style Simple --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo [2/7] Running artistic prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style artistic --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo [3/7] Running colorful prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style colorful --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo [4/7] Running concise prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style concise --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo [5/7] Running detailed prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style detailed --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo [6/7] Running narrative prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style narrative --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo [7/7] Running technical prompt style...
python workflow.py --provider ollama --model %MODEL% --prompt-style technical --name %WORKFLOW_NAME% --batch "%IMAGE_DIR%"

echo.
echo ========================================
echo All 7 prompt styles complete!
echo Results in: Descriptions\wf_%WORKFLOW_NAME%_*
echo ========================================
echo.
pause
ENDLOCAL
