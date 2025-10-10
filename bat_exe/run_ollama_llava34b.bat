@echo off
SETLOCAL
REM Run workflow with Ollama llava:34b
REM Usage: run_ollama_llava34b.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model llava:34b --output-dir ..\Descriptions %*
ENDLOCAL
