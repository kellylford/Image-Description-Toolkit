@echo off
SETLOCAL
REM Run workflow with Ollama InternVL (strong vision-language)
REM Usage: run_ollama_internvl.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model internvl:latest --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
