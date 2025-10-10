@echo off
SETLOCAL
REM Run workflow with OpenAI GPT-4o Mini (fast & affordable)
REM Usage: run_openai_gpt4o_mini.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_openai_gpt4o_mini.bat --prompt-style colorful test_images
REM   run_openai_gpt4o_mini.bat test_images --dry-run
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

..\idt.exe workflow --provider openai --model gpt-4o-mini --output-dir ..\Descriptions %*
ENDLOCAL
