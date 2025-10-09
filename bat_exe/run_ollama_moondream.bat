@echo off
SETLOCAL
REM Run workflow with Ollama Moondream (fastest, smallest)
REM Usage: run_ollama_moondream.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\idt.exe workflow --provider ollama --model moondream:latest --prompt-style %PROMPT_STYLE% --output-dir Descriptions %1
ENDLOCAL
