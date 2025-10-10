@echo off
SETLOCAL
REM Run workflow with Ollama llama3.2-vision:11b
REM Usage: run_ollama_llama32vision11b.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model llama3.2-vision:11b --output-dir ..\Descriptions %*
ENDLOCAL
