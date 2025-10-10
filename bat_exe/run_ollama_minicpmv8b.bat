@echo off
SETLOCAL
REM Run workflow with Ollama minicpm-v:8b
REM Usage: run_ollama_minicpmv8b.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model minicpm-v:8b --output-dir ..\Descriptions %*
ENDLOCAL
