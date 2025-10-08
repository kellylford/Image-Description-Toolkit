@echo off
SETLOCAL
REM Run workflow with Ollama LLaVA Phi3 (small but mighty)
REM Usage: run_ollama_llava_phi3.bat <image_directory> [prompt_style]

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava-phi3:latest --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
