@echo off
SETLOCAL
REM Run workflow with Ollama LLaVA (latest)
REM Usage: run_ollama_llava.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\dist\idt.exe workflow --provider ollama --model llava:latest --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
