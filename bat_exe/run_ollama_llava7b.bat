@echo off
SETLOCAL
REM Run workflow with Ollama LLaVA 7B (balanced quality & speed)
REM Usage: run_ollama_llava7b.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\idt.exe workflow --provider ollama --model llava:7b --prompt-style %PROMPT_STYLE% --output-dir Descriptions %1
ENDLOCAL
