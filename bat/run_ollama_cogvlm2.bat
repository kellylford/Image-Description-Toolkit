@echo off
SETLOCAL
REM Run workflow with Ollama CogVLM2 (advanced Chinese model)
REM Usage: run_ollama_cogvlm2.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model cogvlm2:latest --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
