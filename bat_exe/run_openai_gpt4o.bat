@echo off
SETLOCAL
REM Run workflow with OpenAI GPT-4o (best quality)
REM Usage: run_openai_gpt4o.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_openai_gpt4o.bat --prompt-style colorful test_images
REM   run_openai_gpt4o.bat test_images --dry-run
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

..\idt.exe workflow --provider openai --model gpt-4o --output-dir ..\Descriptions %*
ENDLOCAL
