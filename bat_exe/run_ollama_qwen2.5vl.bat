@echo off
SETLOCAL
REM Run workflow with Ollama qwen2.5vl
REM Usage: run_ollama_qwen2.5vl.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\idt.exe workflow --provider ollama --model qwen2.5vl --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
