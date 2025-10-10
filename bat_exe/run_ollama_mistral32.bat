@echo off
SETLOCAL
REM Run workflow with Ollama mistral-small3.2
REM Usage: run_ollama_mistral32.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model mistral-small3.2 --output-dir ..\Descriptions %*
ENDLOCAL
