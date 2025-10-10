@echo off
SETLOCAL
REM Run workflow with Ollama mistral-small3.1:latest
REM Usage: run_ollama_mistral31.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model mistral-small3.1:latest --output-dir ..\Descriptions %*
ENDLOCAL
