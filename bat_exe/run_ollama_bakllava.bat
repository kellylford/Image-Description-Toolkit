@echo off
SETLOCAL
REM Run workflow with Ollama BakLLaVA (BakLLaVA variant)
REM Usage: run_ollama_bakllava.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\..\..\idt.exe workflow --provider ollama --model bakllava:latest --prompt-style %PROMPT_STYLE% --output-dir ..\..\..\Descriptions %1
ENDLOCAL
