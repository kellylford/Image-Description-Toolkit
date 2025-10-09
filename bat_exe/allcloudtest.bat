@echo off
SETLOCAL
REM Test all cloud AI models (OpenAI and Claude) on a specific directory
REM Usage: allcloudtest.bat <image_directory> [prompt_style]
REM Example: allcloudtest.bat C:\MyImages narrative
REM Requires: API keys configured for OpenAI and Claude

SET IMAGE_DIR=%1
IF "%IMAGE_DIR%"=="" (
    echo ERROR: No image directory specified!
    echo Usage: allcloudtest.bat ^<image_directory^> [prompt_style]
    echo Example: allcloudtest.bat C:\MyImages narrative
    pause
    exit /b 1
)

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

echo.
echo ========================================
echo Testing ALL Cloud AI Models
echo ========================================
echo Target: %IMAGE_DIR%
echo Prompt Style: %PROMPT_STYLE%
echo.
echo OpenAI Models: 3
echo Claude Models: 7
echo Total: 10 models
echo.
echo NOTE: This will use your API credits!
echo Press Ctrl+C to cancel, or
pause

echo.
echo ========================================
echo OPENAI MODELS (3)
echo ========================================

echo.
echo [1/10] Running gpt-4o...
call run_openai_gpt4o.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [2/10] Running gpt-4o-mini...
call run_openai_gpt4o_mini.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [3/10] Running gpt-5...
call run_openai_gpt5.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo ========================================
echo CLAUDE MODELS (7)
echo ========================================

echo.
echo [4/10] Running claude-sonnet-4-5-20250929...
call run_claude_sonnet45.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [5/10] Running claude-opus-4-1-20250805...
call run_claude_opus41.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [6/10] Running claude-sonnet-4-20250514...
call run_claude_sonnet4.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [7/10] Running claude-opus-4-20250514...
call run_claude_opus4.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [8/10] Running claude-3-7-sonnet-20250219...
call run_claude_sonnet37.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [9/10] Running claude-3-5-haiku-20241022...
call run_claude_haiku35.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo [10/10] Running claude-3-haiku-20240307...
call run_claude_haiku3.bat "%IMAGE_DIR%" "%PROMPT_STYLE%"

echo.
echo ========================================
echo All cloud model tests complete!
echo ========================================
echo Results in: Descriptions\wf_*
echo.
echo COST WARNING: This run used API credits from both OpenAI and Claude
echo.
pause
ENDLOCAL
