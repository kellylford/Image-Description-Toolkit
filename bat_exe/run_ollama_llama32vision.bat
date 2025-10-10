@echo off
SETLOCAL
REM Run workflow with Ollama Llama 3.2 Vision (latest)
REM Usage: run_ollama_llama32vision.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\idt.exe workflow --provider ollama --model llama3.2-vision:latest --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
