@echo off
SETLOCAL
REM Run workflow with Ollama Mistral Nemo 3.1
REM Usage: run_ollama_mistral31.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\idt.exe workflow --provider ollama --model mistral-small3.1:latest --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
