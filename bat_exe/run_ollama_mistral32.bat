@echo off
SETLOCAL
REM Run workflow with Ollama Mistral Small 3.2
REM Usage: run_ollama_mistral32.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\dist\idt.exe workflow --provider ollama --model mistral-small3.2 --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
