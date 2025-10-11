@echo off
SETLOCAL

REM Capture the original working directory before changing directories
SET ORIGINAL_CWD=%CD%
REM Run workflow with OpenAI GPT-5 (latest OpenAI model)
REM Usage: run_openai_gpt5.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_openai_gpt5.bat --prompt-style colorful test_images
REM   run_openai_gpt5.bat test_images --dry-run
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
dist\idt.exe workflow --provider openai --model gpt-5 --output-dir ../Descriptions --original-cwd "%ORIGINAL_CWD%" %*
ENDLOCAL
