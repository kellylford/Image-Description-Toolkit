@echo off
SETLOCAL
REM Run workflow with Ollama Llama 3.2 Vision 11B (most accurate)
REM Usage: run_ollama_llama32vision11b.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llama3.2-vision:11b --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
