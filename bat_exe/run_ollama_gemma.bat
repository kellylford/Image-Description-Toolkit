@echo off
SETLOCAL
REM Run workflow with Ollama Gemma 3 (Google's model)
REM Usage: run_ollama_gemma.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\..\..\..\idt.exe workflow --provider ollama --model gemma3:latest --prompt-style %PROMPT_STYLE% --output-dir ..\..\..\Descriptions %1
ENDLOCAL
