@echo off
SETLOCAL
REM Run workflow with OpenAI GPT-5 (latest OpenAI model)
REM Usage: run_openai_gpt5.bat <image_directory> [prompt_style]
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\dist\idt.exe workflow --provider openai --model gpt-5 --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
