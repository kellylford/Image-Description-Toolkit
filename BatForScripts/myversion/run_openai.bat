@echo off
REM ============================================================================
REM Image Description Workflow - OpenAI Provider
REM ============================================================================
REM
REM EDIT PATHS BELOW:
SET IMAGE_PATH=\\ford\home\photos\MobileBackup\iPhone\2025\09
SET API_KEY_FILE=C:\Users\kelly\GitHub\idt\BatForScripts\myversion\openai.txt
SET MODEL=gpt-4o-mini
SET PROMPT_STYLE=narrative
SET STEPS=video,convert,describe,html
REM
REM ============================================================================

echo.
echo ============================================================================
echo OpenAI Image Description Workflow
echo ============================================================================
echo.
echo Configuration:
echo   Images: %IMAGE_PATH%
echo   API Key: %API_KEY_FILE%
echo   Model: %MODEL%
echo   Style: %PROMPT_STYLE%
echo   Steps: %STEPS%
echo.
echo WARNING: This will use your OpenAI API credits!
echo.
pause

echo Running workflow...
cd /d "%~dp0..\.." && python workflow.py "%IMAGE_PATH%" --provider openai --model %MODEL% --prompt-style %PROMPT_STYLE% --api-key-file "%API_KEY_FILE%" --steps %STEPS%

if errorlevel 1 (
    echo.
    echo ERROR: Workflow failed. Check error messages above.
    echo.
) else (
    echo.
    echo SUCCESS! Check the wf_openai_* output directory.
    echo.
)
pause
