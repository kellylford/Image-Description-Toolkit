@echo off
SETLOCAL
REM Run workflow with OpenAI GPT-4o (best quality)
REM Usage: run_openai_gpt4o.bat <image_directory> [prompt_style]
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\idt.exe workflow --provider openai --model gpt-4o --prompt-style %PROMPT_STYLE% --output-dir Descriptions %1
ENDLOCAL
