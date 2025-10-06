@echo off
REM ================================================================
REM    Claude Haiku Workflow - Budget-Friendly Image Description
REM ================================================================
REM
REM This script runs the complete workflow using Claude 3.0 Haiku
REM which is the most cost-effective Claude model.
REM
REM Model: claude-3-haiku-20240307
REM Cost: $ (cheapest Claude model)
REM Speed: Fastest Claude model
REM Quality: Good for most image description tasks
REM

cd /d "%~dp0"

REM ================================================================
REM CONFIGURATION
REM ================================================================

REM Source directory (iPhone photos)
set SOURCE_DIR=\\ford\home\photos\MobileBackup\iPhone\2025\09

REM Provider and model
set PROVIDER=claude
set MODEL=claude-3-haiku-20240307

REM API key location
set API_KEY_FILE=C:\Users\kelly\onedrive\claude.txt

REM Prompt style (narrative gives detailed descriptions)
set PROMPT_STYLE=narrative

REM ================================================================
REM RUN WORKFLOW
REM ================================================================

echo.
echo ================================================================
echo    Claude Haiku Image Description Workflow
echo ================================================================
echo.
echo Provider:     %PROVIDER%
echo Model:        %MODEL% (Budget-Friendly)
echo Source:       %SOURCE_DIR%
echo Prompt Style: %PROMPT_STYLE%
echo API Key:      %API_KEY_FILE%
echo.
echo Starting complete workflow (extract frames, convert HEIC, describe, generate HTML)...
echo.

REM Run the workflow
.venv\Scripts\python.exe workflow.py "%SOURCE_DIR%" ^
    --provider %PROVIDER% ^
    --model %MODEL% ^
    --prompt-style %PROMPT_STYLE% ^
    --api-key-file "%API_KEY_FILE%"

echo.
echo ================================================================
echo    Workflow Complete
echo ================================================================
echo.
echo Check the output directory for results:
echo - Converted images
echo - Extracted video frames
echo - Image descriptions
echo - HTML report
echo.

pause
