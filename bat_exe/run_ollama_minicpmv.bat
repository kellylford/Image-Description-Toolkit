@echo off
SETLOCAL
REM Run workflow with Ollama MiniCPM-V (efficient Chinese model)
REM Usage: run_ollama_minicpmv.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\..\..\..\idt.exe workflow --provider ollama --model minicpm-v:latest --prompt-style %PROMPT_STYLE% --output-dir ..\..\..\Descriptions %1
ENDLOCAL
