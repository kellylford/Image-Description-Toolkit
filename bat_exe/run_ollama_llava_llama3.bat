@echo off
SETLOCAL
REM Run workflow with Ollama LLaVA Llama3 (LLaVA with Llama 3 base)
REM Usage: run_ollama_llava_llama3.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\idt.exe workflow --provider ollama --model llava-llama3:latest --prompt-style %PROMPT_STYLE% --output-dir Descriptions %1
ENDLOCAL
