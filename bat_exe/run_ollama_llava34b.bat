@echo off
SETLOCAL
REM Run workflow with Ollama LLaVA 34B (highest quality LLaVA)
REM Usage: run_ollama_llava34b.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\..\..\..\idt.exe workflow --provider ollama --model llava:34b --prompt-style %PROMPT_STYLE% --output-dir ..\..\..\Descriptions %1
ENDLOCAL
