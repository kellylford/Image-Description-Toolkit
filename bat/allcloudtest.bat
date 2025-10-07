@echo off
REM Test all cloud AI models (OpenAI and Claude) on a specific directory
REM Usage: allcloudtest.bat <image_directory>
REM Default: \\ford\home\Photos\MobileBackup\iPhone\2018\09
REM Requires: API keys configured for OpenAI and Claude

SET IMAGE_DIR=%1
IF "%IMAGE_DIR%"=="" SET IMAGE_DIR=\\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo ========================================
echo Testing ALL Cloud AI Models
echo ========================================
echo Target: %IMAGE_DIR%
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
echo [1/10] Running OpenAI GPT-4o...
call run_openai_gpt4o.bat "%IMAGE_DIR%"

echo.
echo [2/10] Running OpenAI GPT-4o Mini...
call run_openai_gpt4o_mini.bat "%IMAGE_DIR%"

echo.
echo [3/10] Running OpenAI GPT-5...
call run_openai_gpt5.bat "%IMAGE_DIR%"

echo.
echo ========================================
echo CLAUDE MODELS (7)
echo ========================================

echo.
echo [4/10] Running Claude Sonnet 4.5...
call run_claude_sonnet45.bat "%IMAGE_DIR%"

echo.
echo [5/10] Running Claude Opus 4.1...
call run_claude_opus41.bat "%IMAGE_DIR%"

echo.
echo [6/10] Running Claude Sonnet 4...
call run_claude_sonnet4.bat "%IMAGE_DIR%"

echo.
echo [7/10] Running Claude Opus 4...
call run_claude_opus4.bat "%IMAGE_DIR%"

echo.
echo [8/10] Running Claude Sonnet 3.7...
call run_claude_sonnet37.bat "%IMAGE_DIR%"

echo.
echo [9/10] Running Claude Haiku 3.5...
call run_claude_haiku35.bat "%IMAGE_DIR%"

echo.
echo [10/10] Running Claude Haiku 3...
call run_claude_haiku3.bat "%IMAGE_DIR%"

echo.
echo ========================================
echo All cloud model tests complete!
echo ========================================
echo Results in: ..\Descriptions\wf_*
echo.
echo COST WARNING: This run used API credits from both OpenAI and Claude
echo.
pause
