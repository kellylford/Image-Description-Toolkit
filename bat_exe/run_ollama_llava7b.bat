@echo off
SETLOCAL
REM Run workflow with Ollama llava:7b
REM Usage: run_ollama_llava7b.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model llava:7b --output-dir ..\Descriptions %*
ENDLOCAL
