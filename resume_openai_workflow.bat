@echo off
REM Resume the failed OpenAI workflow

echo ============================================================
echo Resuming OpenAI Workflow
echo ============================================================
echo.
echo Workflow directory: wf_openai_gpt-4o-mini_narrative_20251005_122700
echo Provider: OpenAI
echo Model: gpt-4o-mini  
echo Prompt Style: narrative
echo API Key: BatForScripts\myversion\openai.txt
echo.
echo This will resume the description step that failed due to missing API key.
echo.
pause

cd /d "%~dp0"

@echo off
REM Resume the specific failed OpenAI workflow
REM This batch file includes the API key file parameter that's required when resuming cloud provider workflows

cd /d "%~dp0"

REM Activate virtual environment and resume the workflow
.venv\Scripts\python.exe workflow.py --resume "wf_openai_gpt-4o-mini_narrative_20251005_122700" --api-key-file "%USERPROFILE%\onedrive\openai.txt"

pause

echo.
echo ============================================================
echo Workflow Complete!
echo ============================================================
echo.
pause
